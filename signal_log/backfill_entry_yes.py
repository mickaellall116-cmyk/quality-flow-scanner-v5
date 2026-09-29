#!/usr/bin/env python3
"""Backfill entry_yes/entry_why for existing v37_signals.jsonl events.

Re-downloads 4H bars per symbol, matches each logged event to its bar via the
stored signal_bar_close, and recomputes the dashboard entry verdict with
signal_log.dashboard_entry.EntryAssessor. Rewrites the JSONL in place (same
order, no duplicates — dedup keys unchanged). Run:

    cd ~/workspace/quality-flow-scanner-v5 && python3 signal_log/backfill_entry_yes.py
"""

from __future__ import annotations

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pine_backtest import add_pine_indicators  # noqa: E402
from pine_live.decompose import decompose_signal  # noqa: E402
from scanner_rules import bar_close_at  # noqa: E402
from signal_log.dashboard_entry import EntryAssessor  # noqa: E402

SIGNAL_DIR = os.path.join(REPO_ROOT, "signal_log")
JSONL_PATH = os.path.join(SIGNAL_DIR, "v37_signals.jsonl")


def main() -> None:
    with open(JSONL_PATH, encoding="utf-8") as fh:
        events = [json.loads(l) for l in fh if l.strip()]

    by_sym: dict[str, list[dict]] = {}
    for e in events:
        by_sym.setdefault(str(e["symbol"]), []).append(e)

    updated = 0
    for sym, evs in sorted(by_sym.items()):
        from masterscanner_api import download_data

        df = add_pine_indicators(download_data(sym, "4h", "2y"))
        if df is None or df.empty:
            print(f"{sym}: download failed, skipped")
            continue
        # Map stored signal_bar_close -> bar index.
        bar_idx: dict[str, int] = {}
        for i in range(len(df)):
            bar_idx[bar_close_at(df.index[i], sym).isoformat()] = i
        assessor = EntryAssessor(df)
        for e in evs:
            key = str(e["signal_bar_close"])
            if key not in bar_idx:
                print(f"{sym} {key}: bar not found, skipped")
                continue
            i = bar_idx[key]
            d = decompose_signal(df, i)
            a = assessor.assess(df, i, d)
            e["entry_yes"] = bool(a["entry_yes"])
            e["entry_why"] = str(a["entry_why"])
            updated += 1
        print(f"{sym}: assessed {len(evs)} events")

    with open(JSONL_PATH, "w", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")
    print(f"backfilled {updated}/{len(events)} events -> {JSONL_PATH}")


if __name__ == "__main__":
    main()
