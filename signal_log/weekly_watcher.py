#!/usr/bin/env python3
"""Weekly watchlist signal check — observability only.

Runs once per week (Sunday evening, after the weekly bar closes Friday):
for each symbol in signal_log/watchlist.txt, downloads weekly bars and
evaluates the CANONICAL pine_buy_signal (same import path the 4H watcher
uses). New ENTRY-YES signals are reported for pinging; ENTRY-NO events are
log-only. Dedupes via signal_log/weekly_seen.json so nothing re-pings.

Hard rules (do not weaken):
  * The decision ALWAYS comes from ``pine_backtest.pine_buy_signal``.
    No copied logic, no invented formulas. Entry/stop/TP1 reuse the
    canonical SL_ATR / TP_ATR constants.
  * Nothing here modifies pine_backtest.py, pine_live/*, V5.4 files, the
    Quality-Flow-System-V3.7.pine script, the 4H watcher's log/snapshot, or
    the paper engine's universe/state. This module only READS the frozen
    signal, on a different timeframe.
  * Fail-closed per symbol: a download or evaluation failure skips that
    symbol this run and is reported; it never kills the run.

Caveat (surface in the ping, not the code): the signal logic was built and
validated on 4H bars. Weekly-timeframe application is UNVALIDATED — same
code, different bar dynamics. Paper/observation only.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pine_backtest import (  # noqa: E402
    SL_ATR,
    TP_ATR,
    WARMUP,
    add_pine_indicators,
    pine_buy_signal,
)
from pine_live.decompose import decompose_signal  # noqa: E402
from signal_log.dashboard_entry import (  # noqa: E402
    EntryAssessor,
    format_alert,
    load_positions,
)
from masterscanner_api import download_data  # noqa: E402

SIGNAL_DIR = os.path.join(REPO_ROOT, "signal_log")
WATCHLIST_PATH = os.path.join(SIGNAL_DIR, "watchlist.txt")
SEEN_PATH = os.path.join(SIGNAL_DIR, "weekly_seen.json")

LOOKBACK_BARS = 4  # re-check the last 4 closed weekly bars (catch-up)
DOWNLOAD_PERIOD = "5y"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_watchlist() -> list[str]:
    syms: list[str] = []
    with open(WATCHLIST_PATH, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip().upper()
            if s and not s.startswith("#"):
                syms.append(s)
    return syms


def load_seen() -> set[str]:
    if not os.path.exists(SEEN_PATH):
        return set()
    try:
        with open(SEEN_PATH, encoding="utf-8") as fh:
            return set(json.load(fh))
    except Exception:
        return set()


def save_seen(seen: set[str]) -> None:
    with open(SEEN_PATH, "w", encoding="utf-8") as fh:
        json.dump(sorted(seen), fh, indent=1)


def evaluate_symbol(symbol: str, lookback: int, seen: set[str]):
    """Return (new_events, warnings). Fail-closed: raises nothing."""
    warnings: list[str] = []
    try:
        df = download_data(symbol, "1wk", DOWNLOAD_PERIOD)
    except Exception as exc:  # noqa: BLE001
        return [], [f"{symbol}: download failed: {type(exc).__name__}"]
    if df is None or df.empty or len(df) < WARMUP + 2:
        n = 0 if df is None else len(df)
        return [], [f"{symbol}: insufficient weekly data ({n} bars)"]
    try:
        df = add_pine_indicators(df)
        assessor = EntryAssessor(df)
    except Exception as exc:  # noqa: BLE001
        return [], [f"{symbol}: indicator/assessor failed: {type(exc).__name__}"]
    n = len(df)
    events: list[dict] = []
    for i in range(max(WARMUP, n - lookback), n):
        try:
            fired = bool(pine_buy_signal(df, i))
        except Exception:  # noqa: BLE001
            continue
        if not fired:
            continue
        try:
            d = decompose_signal(df, i)
        except Exception:  # noqa: BLE001
            continue
        if bool(d["decision"]) != bool(d["reference_decision"]):
            warnings.append(f"{symbol}: decompose/canonical mismatch — skipped")
            continue
        r = df.iloc[i]
        week_of = df.index[i].strftime("%Y-%m-%d")
        key = f"{symbol}|{week_of}"
        if key in seen:
            continue
        close = float(r["Close"])
        atr = float(r["atr"])
        adx = float(r["adx"])
        try:
            assessment = assessor.assess(df, i, d)
            entry_yes = bool(assessment["entry_yes"])
            entry_why = str(assessment["entry_why"])
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{symbol}: entry assess failed: {type(exc).__name__}")
            continue
        events.append({
            "detected_at": _utcnow_iso(),
            "signal_bar_close": df.index[i].isoformat(),
            "week_of": week_of,
            "symbol": symbol,
            "timeframe": "1wk",
            "entry_px": round(close, 2),
            "stop_px": round(close - atr * SL_ATR, 2),
            "tp1_px": round(close + atr * TP_ATR, 2),
            "score": int(d["trend_score"]),
            "adx": round(adx, 1),
            "entry_yes": entry_yes,
            "entry_why": entry_why,
            "source": "watchlist-weekly",
        })
        seen.add(key)
    return events, warnings


def main() -> int:
    watchlist = load_watchlist()
    seen = load_seen()
    positions = load_positions()
    new_yes: list[dict] = []
    new_no: list[dict] = []
    warnings: list[str] = []
    for sym in watchlist:
        events, w = evaluate_symbol(sym, LOOKBACK_BARS, seen)
        warnings.extend(w)
        for e in events:
            e["alert_text"] = format_alert(e, positions)
            (new_yes if e["entry_yes"] else new_no).append(e)
    save_seen(seen)
    summary = {
        "ran_at": _utcnow_iso(),
        "timeframe": "1wk",
        "watchlist": watchlist,
        "new_entry_yes_signals": new_yes,
        "new_no_signals": [
            {"symbol": e["symbol"], "week_of": e["week_of"],
             "entry_px": e["entry_px"], "adx": e["adx"],
             "entry_why": e["entry_why"]} for e in new_no
        ],
        "warnings": warnings,
    }
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
