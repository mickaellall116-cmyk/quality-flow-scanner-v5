#!/usr/bin/env python3
"""Interval-overlap checker for the CP1 trade-intersection evidence.

Compares TWO explicitly different definitions per trade (240 trades, canonical
shard form). This script does NOT modify trade_intersection.py.

  Definition F (flag, as recorded in trade_intersection.json):
      holding_intersects_est_calendar
        = in_est_calendar(entry) OR in_est_calendar(exit) OR in_est_calendar(signal)
      where in_est_calendar(ts) is DATE membership in EST_PERIODS
      (inclusive date range; signal/entry/exit endpoint dates).

  Definition I (true holding-interval overlap):
      the [entry_time, exit_time] interval overlaps an EST period
      (periods treated as date ranges; overlap iff the interval's date span
      intersects the period's date span).

These definitions are NOT equivalent: F includes the signal date, I does not;
F is endpoint-date membership, I is interval overlap. The script reports both
columns separately and lists every trade where they differ. No general
endpoint-equivalence claim is made.

Output: interval_overlap_full_output.csv (one row per trade) + summary to stdout.
Run: python3 interval_overlap_checker.py
"""

import csv
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(
    HERE, "..", "cp1_followup", "trade_intersection.json"))

# Must match trade_intersection.py exactly.
EST_PERIODS = [
    ("2024-11-03", "2025-03-09"),  # EST 2024-25
    ("2025-11-02", "2026-03-08"),  # EST 2025-26
]


def in_est_calendar(ts):
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    d = ts.date().isoformat()
    return any(s <= d <= e for s, e in EST_PERIODS)


def interval_overlaps(entry_ts, exit_ts):
    """True interval overlap of [entry, exit] with any EST period (date spans)."""
    e0, e1 = pd.Timestamp(entry_ts).date(), pd.Timestamp(exit_ts).date()
    for s, e in EST_PERIODS:
        ps, pe = pd.Timestamp(s).date(), pd.Timestamp(e).date()
        if e0 <= pe and ps <= e1:
            return True
    return False


def main():
    d = json.load(open(DATA))
    trades = d["trades"]
    assert len(trades) == 240, f"expected 240 trades, got {len(trades)}"

    rows = []
    for t in trades:
        tid = t["trade_id"]
        sig, ent, ext = t["signal_time"], t["entry_time"], t["exit_time"]
        # Definition F: recompute from endpoints to cross-check the recorded flag
        f_recomputed = (in_est_calendar(ent) or in_est_calendar(ext)
                        or in_est_calendar(sig))
        f_recorded = t["holding_intersects_est_calendar"]
        # Definition I: true holding-interval overlap
        i_overlap = interval_overlaps(ent, ext)
        rows.append({
            "trade_id": tid,
            "symbol": t["symbol"],
            "asset_class": t["asset_class"],
            "signal_time": sig,
            "entry_time": ent,
            "exit_time": ext,
            "signal_in_period": in_est_calendar(sig),
            "entry_in_period": in_est_calendar(ent),
            "exit_in_period": in_est_calendar(ext),
            "defF_flag_recorded": f_recorded,
            "defF_flag_recomputed": f_recomputed,
            "defF_match": f_recomputed == f_recorded,
            "defI_interval_overlap": i_overlap,
            "defF_vs_defI_differ": f_recorded != i_overlap,
        })

    out_csv = os.path.join(HERE, "interval_overlap_full_output.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    n_f = sum(r["defF_flag_recorded"] for r in rows)
    n_i = sum(r["defI_interval_overlap"] for r in rows)
    n_f_mismatch = sum(not r["defF_match"] for r in rows)
    differ = [r for r in rows if r["defF_vs_defI_differ"]]
    print(f"trades examined: {len(rows)}")
    print(f"defF (recorded flag) True: {n_f}")
    print(f"defI (interval overlap) True: {n_i}")
    print(f"defF recomputed != recorded: {n_f_mismatch}")
    print(f"defF vs defI differ: {len(differ)}")
    for r in differ:
        print(f"  {r['trade_id']} {r['symbol']}: "
              f"signal_in_period={r['signal_in_period']} "
              f"entry_in_period={r['entry_in_period']} "
              f"exit_in_period={r['exit_in_period']} "
              f"defF={r['defF_flag_recorded']} defI={r['defI_interval_overlap']}")
    # The material question: interval spans a period with ALL endpoints outside
    spanned = [r for r in rows
               if r["defI_interval_overlap"]
               and not r["signal_in_period"]
               and not r["entry_in_period"]
               and not r["exit_in_period"]]
    print(f"interval spans a period with all endpoints outside: {len(spanned)}")
    print(f"wrote {out_csv}")


if __name__ == "__main__":
    main()
