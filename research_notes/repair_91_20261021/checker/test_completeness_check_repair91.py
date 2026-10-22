#!/usr/bin/env python3
"""
test_completeness_check_repair91.py — REPAIR -91 FIX 1 fixtures.

The -89 checker iterated only days PRESENT in the bars, so an
expected session with zero rows escaped COUNT entirely. These
fixtures prove the repaired lane: the session table is iterated,
a fully-missing session is a first-class COUNT finding
(missing_sessions) -> COMPLETENESS_FAIL, at mid-window and at both
boundaries, with a clean control. Synthetic bars only.
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from tsla_completeness_check import run_check  # noqa: E402

NY = "America/New_York"
DAYS = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
SESSIONS = {pd.Timestamp(d).date(): 16 * 60 for d in DAYS}

RESULTS = []


def case(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name, detail if not cond else "")


def build(days):
    rows = []
    price = 100.0
    for d in days:
        day = pd.Timestamp(d, tz=NY)
        for k in range(7):
            ts = day + pd.Timedelta(minutes=570 + 60 * k)
            o = price
            c = price + 0.10
            rows.append((ts, o, max(o, c) + 0.05, min(o, c) - 0.05, c, 1000))
            price = c
    df = pd.DataFrame(rows, columns=["ts", "Open", "High", "Low",
                                     "Close", "Volume"])
    return df.set_index("ts")


def main():
    # R91-C1 clean control: all sessions present -> QUALIFIED_CLEAN
    r = run_check(build(DAYS), SESSIONS, [])
    case("R91_C1_clean_control_overall", r["overall"] == "QUALIFIED_CLEAN",
         r["overall"])
    case("R91_C1_clean_control_no_missing_sessions",
         r["count"]["missing_sessions"] == [], str(r["count"]))

    # R91-C2 mid-window session dropped entirely -> flagged by date
    r = run_check(build(["2024-01-02", "2024-01-04", "2024-01-05"]),
                  SESSIONS, [])
    got = [m["session"] for m in r["count"]["missing_sessions"]]
    case("R91_C2_mid_session_missing_flagged", got == ["2024-01-03"],
         str(got))
    case("R91_C2_count_fail", r["count"]["verdict"] == "FAIL")
    case("R91_C2_overall_completeness_fail",
         r["overall"] == "COMPLETENESS_FAIL", r["overall"])
    case("R91_C2_expected_bar_starts_named",
         len(r["count"]["missing_sessions"][0]["expected_bar_starts"]) == 7)

    # R91-C3 first (boundary) session dropped -> flagged
    r = run_check(build(["2024-01-03", "2024-01-04", "2024-01-05"]),
                  SESSIONS, [])
    got = [m["session"] for m in r["count"]["missing_sessions"]]
    case("R91_C3_first_session_missing_flagged", got == ["2024-01-02"],
         str(got))
    case("R91_C3_overall_completeness_fail",
         r["completeness_verdict"] == "FAIL", r["overall"])

    # R91-C4 last (boundary) session dropped -> flagged
    r = run_check(build(["2024-01-02", "2024-01-03", "2024-01-04"]),
                  SESSIONS, [])
    got = [m["session"] for m in r["count"]["missing_sessions"]]
    case("R91_C4_last_session_missing_flagged", got == ["2024-01-05"],
         str(got))
    case("R91_C4_overall_completeness_fail",
         r["completeness_verdict"] == "FAIL", r["overall"])

    # R91-C5 no session table -> hard refusal, never a silent pass
    try:
        run_check(build(DAYS), None, [])
        case("R91_C5_session_table_required", False, "no exception")
    except ValueError as e:
        case("R91_C5_session_table_required",
             "SESSION_TABLE_REQUIRED" in str(e), str(e))

    n = sum(1 for _, ok in RESULTS if ok)
    print(f"\n{n}/{len(RESULTS)} checks passed")
    return 0 if n == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
