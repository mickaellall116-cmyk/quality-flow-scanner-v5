"""P7 synthetic fixture for the all-fire journal classification.

Scripted fires on a 12-bar frame (WARMUP=2):
  bar 2  fire -> opens standalone trade (MATCHED_CANDIDATE)
  bar 3  fire -> SUPPRESSED_OVERLAP (occupying = bar 2's candidate)
  bar 4  fire -> SUPPRESSED_OVERLAP
  bar 5  no fire; close 96 < runner 97 -> stop exit at bar 6 open
  bar 6  fire -> GAP_INELIGIBLE_ENTRY (next open 46 <= stop0 47)
  bar 8  fire -> opens; still open at series end (MATCHED, censored)
Expected: 5 fires {2 matched, 2 suppressed, 1 gap}, 1 closed trade,
1 censored candidate, skipped_gap == 1, 0 unclassified.

Run: python3 tests/test_allfire.py
"""
import os
import sys
import types

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "code"))
import allfire_journal  # noqa: E402

FIRES = {2, 3, 4, 6, 8}


def main():
    idx = pd.date_range("2025-01-06 09:30", periods=12, freq="4h",
                        tz="America/New_York")
    close = [100, 100, 100, 101, 100.5, 96, 50, 60, 100, 101, 101, 101]
    opn = [100, 100, 100, 101, 101, 100, 99, 46, 60, 101, 101, 101]
    df = pd.DataFrame({
        "Open": [float(x) for x in opn],
        "High": [float(x) + 2 for x in close],
        "Low": [float(x) - 2 for x in close],
        "Close": [float(x) for x in close],
        "atr": [2.0] * 12, "e21": [10.0] * 12, "e55": [9.0] * 12,
        "e200": [8.0] * 12}, index=idx)
    pb = types.SimpleNamespace(
        WARMUP=2, SL_ATR=1.5, TP_ATR=2.0, TRAIL_ATR=2.5,
        pine_buy_signal=lambda d, i: i in FIRES)
    fires, trades, censored, sg = allfire_journal.gen_allfire("AAA", df, pb)
    by_idx = {f["signal_idx"]: f for f in fires}
    fails = []

    def check(name, cond, detail=""):
        print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
        if not cond:
            fails.append(name)

    check("5 fires journaled", len(fires) == 5, f"got {len(fires)}")
    check("bar2 MATCHED", by_idx[2]["classification"] == "MATCHED_CANDIDATE")
    check("bar3 SUPPRESSED by 2",
          by_idx[3]["classification"] == "SUPPRESSED_OVERLAP"
          and by_idx[3]["occupying_signal_idx"] == 2)
    check("bar4 SUPPRESSED by 2",
          by_idx[4]["classification"] == "SUPPRESSED_OVERLAP"
          and by_idx[4]["occupying_signal_idx"] == 2)
    check("bar6 GAP_INELIGIBLE",
          by_idx[6]["classification"] == "GAP_INELIGIBLE_ENTRY")
    check("bar8 MATCHED", by_idx[8]["classification"] == "MATCHED_CANDIDATE")
    check("1 closed trade (stop exit at bar 6 open)",
          len(trades) == 1 and trades[0]["reason"] == "stop"
          and trades[0]["signal_idx"] == 2)
    check("1 censored candidate (bar 8)",
          len(censored) == 1 and censored[0]["signal_idx"] == 8)
    check("skipped_gap == 1", sg == 1)
    check("0 UNCLASSIFIED",
          all(f["classification"] != "UNCLASSIFIED" for f in fires))
    print("SUMMARY", "FAIL" if fails else "PASS", fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
