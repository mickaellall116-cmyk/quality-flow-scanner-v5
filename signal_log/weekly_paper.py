#!/usr/bin/env python3
"""Weekly-entry + daily-exit paper tracker (forward out-of-sample record).

Paper-trades the weekly_entry_exit diagnostic's best-looking combo:
weekly ENTRY-YES entries, canonical exits managed on daily bars.
Observability only: touches no strategy code, no paper-engine state,
no watcher dedup files. State lives in signal_log/weekly_paper.json.

Runs weekday evenings after the close:
  1. Finds fresh ENTRY-YES on the latest CLOSED weekly bar per ticker
     (own seen_weeks, seeded from the Sunday watcher's weekly_seen.json
     so already-pinged signals are never re-opened).
  2. Opens a paper position at the first trading day's open after the
     signal week (skipped if that window was missed).
  3. Manages open positions on daily bars with the canonical exit stack:
     ATR stop, 50% at TP1 (intrabar limit), trail runner after TP1,
     close<runner / close<e55 / trend-bear exits filled at next open.
  4. Prints a JSON summary; the cron worker pings Mike only when a
     position opens or closes, and stays silent otherwise.

Entry/exit math reuses the canonical SL_ATR / TP_ATR / TRAIL_ATR
constants from pine_backtest. No invented formulas.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
SIGNAL_DIR = os.path.join(REPO_ROOT, "signal_log")
if SIGNAL_DIR not in sys.path:
    sys.path.insert(0, SIGNAL_DIR)

from pine_backtest import (  # noqa: E402
    SL_ATR,
    TP_ATR,
    TRAIL_ATR,
    WARMUP,
    add_pine_indicators,
)
from masterscanner_api import download_data  # noqa: E402
import weekly_watcher  # noqa: E402  (signal_log/weekly_watcher.py)

WATCHLIST_PATH = os.path.join(SIGNAL_DIR, "watchlist.txt")
STATE_PATH = os.path.join(SIGNAL_DIR, "weekly_paper.json")
WATCHER_SEEN_PATH = os.path.join(SIGNAL_DIR, "weekly_seen.json")

ET = ZoneInfo("America/New_York")
MAX_OPEN_LAG_DAYS = 5  # open only within 5 days of the signal week's Friday


def _today_et():
    return datetime.now(ET).date()


def _naive(ts):
    return ts.tz_localize(None) if getattr(ts, "tzinfo", None) is not None else ts


def load_watchlist() -> list[str]:
    syms: list[str] = []
    with open(WATCHLIST_PATH, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip().upper()
            if s and not s.startswith("#"):
                syms.append(s)
    return syms


def load_state(path: str | None = None) -> dict:
    path = path or os.environ.get("WEEKLY_PAPER_STATE", STATE_PATH)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                st = json.load(fh)
            st.setdefault("open", [])
            st.setdefault("closed", [])
            st.setdefault("seen_weeks", [])
            return st
        except Exception:
            pass
    # seed seen_weeks from the Sunday watcher's dedup so already-pinged
    # signals are never opened as paper positions
    seed: list[str] = []
    if os.path.exists(WATCHER_SEEN_PATH):
        try:
            with open(WATCHER_SEEN_PATH, encoding="utf-8") as fh:
                seed = sorted(set(json.load(fh)))
        except Exception:
            pass
    return {"open": [], "closed": [], "seen_weeks": seed}


def save_state(st: dict, path: str | None = None) -> None:
    path = path or os.environ.get("WEEKLY_PAPER_STATE", STATE_PATH)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=1)


def blended_r(entry: float, stop: float, tp1: float,
             tp_hit: bool, exit_px: float) -> float:
    risk_frac = (entry - stop) / entry
    r1 = (tp1 - entry) / entry / risk_frac if tp_hit else None
    r2 = (exit_px - entry) / entry / risk_frac
    return (0.5 * r1 + 0.5 * r2) if r1 is not None else r2


def fresh_weekly_yes(symbol: str, seen_weeks: set[str], today):
    """ENTRY-YES events on the latest fully-closed weekly bar."""
    try:
        events, warnings = weekly_watcher.evaluate_symbol(symbol, 2, set())
    except Exception as exc:  # noqa: BLE001
        return [], [f"{symbol}: signal check failed: {type(exc).__name__}"]
    out = []
    for e in events:
        if not e.get("entry_yes"):
            continue
        week_mon = datetime.strptime(e["week_of"], "%Y-%m-%d").date()
        friday = week_mon + timedelta(days=4)
        if friday >= today:
            continue  # weekly bar not fully closed yet
        key = f"{symbol}|{e['week_of']}"
        if key in seen_weeks:
            continue
        e["_friday"] = friday.isoformat()
        out.append(e)
    return out, warnings


def open_position(symbol: str, event: dict, warnings: list[str]):
    """Open a paper position at the first trading day's open after Friday.

    Returns (pos, retry): pos is the position dict or None; retry is True
    when the failure is transient (try again tomorrow) and False when the
    signal week should be marked seen and never reconsidered.
    """
    friday = datetime.strptime(event["_friday"], "%Y-%m-%d").date()
    try:
        df = download_data(symbol, "1d", "2y")
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"{symbol}: daily download failed: {type(exc).__name__}")
        return None, True
    if df is None or len(df) < WARMUP + 2:
        warnings.append(f"{symbol}: insufficient daily data")
        return None, True
    df = add_pine_indicators(df)
    dates = [_naive(t).date() for t in df.index]
    # Friday's bar (last trading day of the signal week on/before Friday)
    fri_idx = max((k for k, d in enumerate(dates) if d <= friday), default=None)
    if fri_idx is None:
        warnings.append(f"{symbol}: no Friday bar found")
        return None, True
    fri = df.iloc[fri_idx]
    fri_atr = float(fri["atr"])
    # first trading day strictly after Friday
    ent_idx = next((k for k in range(fri_idx + 1, len(df))
                    if dates[k] > friday), None)
    if ent_idx is None:
        return None, True  # market hasn't reopened yet; retry tomorrow
    ent_date = dates[ent_idx]
    if (ent_date - friday).days > MAX_OPEN_LAG_DAYS:
        warnings.append(f"{symbol}: entry window missed for {event['week_of']}")
        return None, False
    entry = float(df["Open"].iloc[ent_idx])
    stop = float(fri["Close"]) - fri_atr * SL_ATR
    if entry <= stop:
        warnings.append(f"{symbol}: gapped below stop at open, skipped")
        return None, False
    tp1 = entry + fri_atr * TP_ATR
    return {
        "ticker": symbol,
        "signal_week": event["week_of"],
        "entry_date": ent_date.isoformat(),
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "tp1": round(tp1, 2),
        "tp_hit": False,
        "runner": round(stop, 2),
        "pending_exit": None,
        "last_bar": ent_date.isoformat(),  # entry bar not yet managed
        "score": event.get("score"),
        "adx": event.get("adx"),
    }, False


def manage_positions(state: dict, warnings: list[str]):
    """Advance every open position over newly closed daily bars."""
    closed_now: list[dict] = []
    for pos in list(state["open"]):
        symbol = pos["ticker"]
        try:
            df = download_data(symbol, "1d", "2y")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{symbol}: daily download failed: {type(exc).__name__}")
            continue
        if df is None or len(df) < WARMUP + 2:
            warnings.append(f"{symbol}: insufficient daily data")
            continue
        df = add_pine_indicators(df)
        dates = [_naive(t).date() for t in df.index]
        date_strs = [d.isoformat() for d in dates]
        try:
            start = date_strs.index(pos["last_bar"]) + 1
        except ValueError:
            warnings.append(f"{symbol}: last_bar {pos['last_bar']} not in data")
            continue
        for j in range(start, len(df)):
            bar = df.iloc[j]
            if pos["pending_exit"]:
                exit_px = float(bar["Open"])
                r = blended_r(pos["entry"], pos["stop"], pos["tp1"],
                              pos["tp_hit"], exit_px)
                state["open"].remove(pos)
                state["closed"].append({
                    **{k: pos[k] for k in ("ticker", "signal_week", "entry_date",
                                          "entry", "stop", "tp1", "tp_hit")},
                    "exit_date": dates[j].isoformat(),
                    "exit": round(exit_px, 2),
                    "reason": pos["pending_exit"],
                    "r": round(r, 3),
                })
                closed_now.append(state["closed"][-1])
                break
            hi, close = float(bar["High"]), float(bar["Close"])
            if not pos["tp_hit"] and hi >= pos["tp1"]:
                pos["tp_hit"] = True
            if pos["tp_hit"]:
                pos["runner"] = round(max(pos["runner"],
                                          close - float(bar["atr"]) * TRAIL_ATR), 2)
            trend_bear = bar["e21"] < bar["e55"] and close < bar["e200"]
            if close < pos["runner"]:
                pos["pending_exit"] = "stop"
            elif close < bar["e55"] or trend_bear:
                pos["pending_exit"] = "ema55-bear" if trend_bear else "ema55-break"
            pos["last_bar"] = dates[j].isoformat()
    return closed_now


def run_once(today) -> dict:
    if today.weekday() >= 5:
        return {"ran_at": datetime.now(ET).isoformat(timespec="seconds"),
                "note": "weekend — no-op", "opened": [], "closed": []}
    state = load_state()
    seen_weeks = set(state["seen_weeks"])
    warnings: list[str] = []
    opened: list[dict] = []

    for sym in load_watchlist():
        fresh, w = fresh_weekly_yes(sym, seen_weeks, today)
        warnings.extend(w)
        for e in fresh:
            key = f"{sym}|{e['week_of']}"
            pos, retry = open_position(sym, e, warnings)
            if pos:
                state["open"].append(pos)
                opened.append({k: pos[k] for k in
                               ("ticker", "signal_week", "entry_date", "entry",
                                "stop", "tp1")})
                seen_weeks.add(key)
            elif not retry:
                seen_weeks.add(key)  # hard skip: never reconsider
    state["seen_weeks"] = sorted(seen_weeks)

    closed_now = manage_positions(state, warnings)
    save_state(state)

    closed = state["closed"]
    rs = [c["r"] for c in closed]
    # unrealized R on open positions at last close
    open_view = []
    for pos in state["open"]:
        risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]
        open_view.append({**{k: pos[k] for k in
                             ("ticker", "signal_week", "entry_date", "entry",
                              "stop", "tp1", "tp_hit", "runner", "last_bar")},
                          "risk_frac": round(risk_frac, 4)})
    summary = {
        "ran_at": datetime.now(ET).isoformat(timespec="seconds"),
        "opened": opened,
        "closed": closed_now,
        "open_positions": open_view,
        "stats": {
            "closed_n": len(closed),
            "open_n": len(state["open"]),
            "avg_r": round(sum(rs) / len(rs), 3) if rs else None,
            "total_r": round(sum(rs), 2) if rs else 0.0,
            "win_rate": round(sum(1 for r in rs if r > 0) / len(rs), 3) if rs else None,
        },
        "warnings": warnings,
    }
    return summary


def main() -> int:
    today = _today_et()
    print(json.dumps(run_once(today), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
