"""V5.4 multi-timeframe paper tests (1h / 1d / 1w) — RESEARCH ONLY.

Parallel paper experiments answering one question: does the frozen V5.4
system transfer across timeframes? Approved by Mike 2026-09-17 after he
asked whether smaller timeframes (1-5% day-trade style) or larger ones
(daily/weekly) are worth learning.

HARD ISOLATION: the 4H forward test is UNTOUCHED. This script never reads
or writes v54_forward/*, forward_test/*.json, or latest_v54_signals.json.
Separate state dirs (v54_forward_1h/, v54_forward_1d/, v54_forward_1w/),
separate append-only logs, local status JSON only — no GitHub publishing,
no AI observer (AI-OBS-v1 belongs to the 4H test).

Frozen pieces reused VERBATIM (this file modifies none of them):
  - v54_engine.v54_scan_symbols / v54_qualified_signals: structural
    contract (entry==YES, protection==SAFE, above VWAP, buy zone),
    ADX>=20, completed bars only; A/B/C grading. MTF inputs are the
    engine's standard daily+weekly downloads — identical to the 4H test.
  - v54_exit_tracker.ModeBTracker: Mode B exits (structural stop always
    active, 50% at TP1, +1R arms Profit Protect, runner keeps original
    stop, 30-bar max hold, stop wins same-bar ties, idempotent).
  - v54_forward_log.ForwardLog: append-only JSONL audit log.

Per-timeframe MTF semantics (engine inputs are daily+weekly in all cases;
meaning shifts by signal timeframe — documented, not hidden):
  - 1h:  daily/weekly are HIGHER timeframes (same semantics as 4H test).
  - 1d:  daily == signal timeframe (trend alignment), weekly higher.
  - 1w:  daily is a LOWER timeframe (confirmation), weekly == signal TF.
Grades stay internally consistent per timeframe. The question under test
is expectancy per timeframe, not cross-timeframe grade purity.

Usage:
  python3 v54_mtf_paper.py --timeframe 1h   # hourly cron
  python3 v54_mtf_paper.py --timeframe 1d   # daily cron (after close)
  python3 v54_mtf_paper.py --timeframe 1w   # weekly cron (weekend)
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

import v54_engine as eng
import v54_forward_harness as h
from v54_exit_tracker import ModeBTracker, close_summary
from v54_forward_log import ForwardLog

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TF_CONFIG: Dict[str, Dict[str, str]] = {
    # tf: yfinance interval, history period, isolated state dir, label
    "1h": {"interval": "1h", "period": "60d",
           "state_dir": "v54_forward_1h", "label": "1H"},
    "1d": {"interval": "1d", "period": "2y",
           "state_dir": "v54_forward_1d", "label": "Daily"},
    "1w": {"interval": "1wk", "period": "5y",
           "state_dir": "v54_forward_1w", "label": "Weekly"},
}

UNIVERSE: List[str] = h.UX51_UNIVERSE + list(
    __import__("v54_universe_x2", fromlist=["UNIVERSE_X2"]).UNIVERSE_X2)
THEME_MAP: Dict[str, str] = dict(h.THEME_MAP)


# --------------------------------------------------------------------------
# Cycle machinery (mirrors v54_forward_harness.run_cycle/_process_symbol,
# parameterized by timeframe; the frozen originals are not modified).
# --------------------------------------------------------------------------

def v53_state_for_bar(symbol: str, df_full: pd.DataFrame,
                      market_full: Optional[pd.DataFrame],
                      regime: Dict[str, Any], bar_ts: pd.Timestamp,
                      interval: str) -> Optional[str]:
    """V5.3 scanner state as of one completed bar (for EXIT detection)."""
    try:
        d = df_full[df_full.index <= bar_ts]
        m = market_full[market_full.index <= bar_ts] if market_full is not None else None
        row = eng.m53.classify_symbol(symbol, THEME_MAP.get(symbol, "Watchlist"),
                                      d, m, regime, interval)
        return (row or {}).get("state")
    except Exception:
        return None


def _process_symbol(sym: str, df: pd.DataFrame, interval: str,
                    regime: Dict[str, Any], market_full: pd.DataFrame,
                    state: Dict[str, Any], log: ForwardLog,
                    tracker: ModeBTracker, summary: Dict[str, Any]) -> None:
    entry_bars: Dict[str, Any] = {}
    for sid, pend in list(state["pending"].items()):
        if pend["symbol"] != sym:
            continue
        sig_start = pd.Timestamp(pend["signal_bar_start"])
        newbars = df[df.index > sig_start]
        if newbars.empty:
            continue
        ts = newbars.index[0]
        snap = state["snapshots"][sid]
        pos = tracker.open_position(snap, float(newbars.iloc[0]["Open"]),
                                    ts.isoformat())
        if pos is None:
            log.log_event(sid, {"event": "entry_skipped",
                                "reason": "entry <= structural stop"})
        else:
            summary["opened"] += 1
            entry_bars[sid] = ts
        del state["pending"][sid]

    for sid, pos in list(tracker.positions.items()):
        if pos["symbol"] != sym or pos["status"] == "closed":
            continue
        if sid in entry_bars:
            newbars = df[df.index >= entry_bars[sid]]
        else:
            last = pos.get("last_processed_bar") or pos.get("entry_bar")
            newbars = df[df.index > pd.Timestamp(last)] if last else df
        for ts, bar in newbars.iterrows():
            scanner_state = v53_state_for_bar(sym, df, market_full, regime,
                                              ts, interval)
            tracker.process_bar(sid, {
                "bar_id": ts.isoformat(),
                "open": float(bar["Open"]), "high": float(bar["High"]),
                "low": float(bar["Low"]), "close": float(bar["Close"]),
                "scanner_state": scanner_state,
            })


def run_cycle_tf(tf: str, state: Dict[str, Any], log: ForwardLog,
                 tracker: ModeBTracker) -> Dict[str, Any]:
    cfg = TF_CONFIG[tf]
    interval, period = cfg["interval"], cfg["period"]
    seen = set(state["seen_signal_ids"])
    summary: Dict[str, Any] = {"timeframe": tf, "new_signals": 0,
                               "new_signal_ids": [], "opened": 0,
                               "closed": [], "errors": []}

    rows, regime = eng.v54_scan_symbols(UNIVERSE, THEME_MAP, interval, period)
    dl_cache: Dict[str, pd.DataFrame] = {}

    def _get_bars(symbol: str) -> pd.DataFrame:
        if symbol not in dl_cache:
            dl_cache[symbol] = eng.m53.download_data(symbol, interval, period)
        return dl_cache[symbol]

    for row in eng.v54_qualified_signals(rows):
        sid = row["signal_id"]
        if sid in seen:
            continue
        seen.add(sid)
        state["snapshots"][sid] = row
        log.log_signal(row)
        summary["new_signals"] += 1
        summary["new_signal_ids"].append(sid)
        sym = row["symbol"]
        if h._busy(state, tracker, sym):
            log.log_event(sid, {"event": "signal_skipped",
                                "reason": "position already open/pending",
                                "symbol": sym})
        else:
            state["pending"][sid] = {"symbol": sym,
                                     "signal_bar_start": row["signal_bar_start_at"]}
            log.log_event(sid, {"event": "pending_entry",
                                "signal_bar_start": row["signal_bar_start_at"]})
    state["seen_signal_ids"] = sorted(seen)

    symbols = ({p["symbol"] for p in state["pending"].values()}
               | {p["symbol"] for p in tracker.positions.values()
                  if p["status"] != "closed"})
    market_full = _get_bars(eng.m53.MARKET_SYMBOL)
    for sym in sorted(symbols):
        try:
            df = _get_bars(sym)
            if df is None or df.empty:
                continue
            _process_symbol(sym, df, interval, regime, market_full,
                            state, log, tracker, summary)
        except Exception as exc:
            summary["errors"].append({"symbol": sym, "error": str(exc)[:200]})

    for sid, pos in tracker.positions.items():
        if pos["status"] == "closed" and not state["close_logged"].get(sid):
            snap = state["snapshots"].get(sid) or log.get_signal(sid) or {}
            log.log_close(close_summary(pos, snap))
            state["close_logged"][sid] = True
            summary["closed"].append(sid)

    state["runs"] = state.get("runs", 0) + 1
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    return summary


# --------------------------------------------------------------------------
# Status payload (local only — never published to GitHub).
# --------------------------------------------------------------------------

def build_status(state: Dict[str, Any], log: ForwardLog,
                 tracker: ModeBTracker, tf: str,
                 summary: Dict[str, Any]) -> Dict[str, Any]:
    closed = []
    for sid in state.get("close_logged", {}):
        c = log.get_close(sid)
        if c:
            closed.append(c)
    cum_r = round(sum((c.get("blended_r") or 0) for c in closed), 4)
    wins = sum(1 for c in closed if (c.get("blended_r") or 0) > 0)
    opens = [
        {"signal_id": sid, "symbol": p.get("symbol"), "grade": p.get("grade"),
         "entry": p.get("entry"), "stop": p.get("stop"), "tp1": p.get("tp1"),
         "status": p.get("status"), "bars_held": p.get("bars_held", 0)}
        for sid, p in tracker.positions.items() if p["status"] != "closed"
    ]
    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "experiment": "V5.4 multi-timeframe paper test (research only)",
        "timeframe": tf,
        "label": TF_CONFIG[tf]["label"],
        "rule_set": "V5.4 frozen 2026-09-15 (structural + ADX>=20 entries, "
                    "Mode B exits, A/B/C grading) — same as 4H forward test",
        "isolation": "separate state/log; 4H forward test untouched; "
                     "no observer; local only, never published",
        "universe": f"UX51+X2 ({len(h.UX51_UNIVERSE)}+199 symbols)",
        "last_successful_cycle": state.get("last_run"),
        "signals_logged": len(state.get("seen_signal_ids", [])),
        "grade_counts": log.grade_counts(),
        "pending_entries": len(state.get("pending", {})),
        "open_positions": opens,
        "closed_trades": len(closed),
        "cumulative_r": cum_r,
        "avg_r_per_trade": round(cum_r / len(closed), 4) if closed else 0.0,
        "win_rate": round(wins / len(closed), 4) if closed else 0.0,
        "cycles_run": state["runs"],
        "last_cycle": summary,
    }


def run_once(tf: str) -> Dict[str, Any]:
    if tf not in TF_CONFIG:
        raise ValueError(f"unknown timeframe {tf!r}; choose 1h, 1d, or 1w")
    state_dir = os.path.join(BASE_DIR, TF_CONFIG[tf]["state_dir"])
    os.makedirs(state_dir, exist_ok=True)
    state_path = os.path.join(state_dir, "state.json")
    log = ForwardLog(os.path.join(state_dir, "forward_test.jsonl"))
    state = h.load_state(state_path)
    def _sink(event: Dict[str, Any]) -> None:
        event = dict(event)
        sid = event.pop("signal_id")
        log.log_event(sid, event)
    tracker = ModeBTracker(event_sink=_sink)
    # restore positions (event_sink re-attached above)
    tracker.positions = state.get("positions", {})

    summary = run_cycle_tf(tf, state, log, tracker)
    state["positions"] = tracker.positions
    h.save_state(state, state_path)

    status = build_status(state, log, tracker, tf, summary)
    status_path = os.path.join(state_dir, f"v54_mtf_{tf}_status.json")
    with open(status_path, "w", encoding="utf-8") as fh:
        json.dump(status, fh, default=str, indent=2)
    summary["status_file"] = status_path

    with open(os.path.join(state_dir, "last_cycle.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"finished_at": datetime.now(timezone.utc).isoformat(),
                   "timeframe": tf,
                   "new_signals": summary["new_signals"],
                   "opened": summary["opened"],
                   "closed": summary["closed"],
                   "errors": summary["errors"]}, fh, default=str)
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeframe", required=True, choices=["1h", "1d", "1w"])
    args = ap.parse_args()
    print(json.dumps(run_once(args.timeframe), default=str, indent=2))
