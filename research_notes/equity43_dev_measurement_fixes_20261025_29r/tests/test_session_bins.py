"""29r fixtures for session_bins (pinned session-table bin resolution).

Run: python3 tests/test_session_bins.py  (exit 0 = all assertions hold)

Every expectation is read off the adopted calendar itself: regular
sessions carry bins 09:30->13:30 and 13:30->16:00 ET; the seven
13:00 early-close sessions carry the single bin 09:30->13:00; DST
transitions change the UTC offset of the same wall-clock bin ends.
Refusals raise session_bins.SessionTableError (fail-closed).
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "code"))
import session_bins as sb  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        FAILURES.append(name)


def expect_refusal(name, fn, needle=""):
    try:
        fn()
    except sb.SessionTableError as e:
        check(name, needle in str(e), f"({e})")
        return
    check(name, False, "no SessionTableError raised")


def main():
    t = sb.load_pinned_table()
    check("pinned table loads (sha verified), 751 sessions",
          len(t) == 751, f"n={len(t)}")

    # Regular session: bins 09:30->13:30 (4h) and 13:30->16:00 (2.5h).
    e1 = t.bin_end("2025-01-06T09:30:00-05:00")
    check("regular bin1 end 13:30-05:00",
          e1.isoformat() == "2025-01-06T13:30:00-05:00", e1.isoformat())
    e2 = t.bin_end("2025-01-06T13:30:00-05:00")
    check("regular bin2 end 16:00-05:00 (not 17:30)",
          e2.isoformat() == "2025-01-06T16:00:00-05:00", e2.isoformat())
    check("bin durations 4h / 2.5h (no constant duration)",
          sb.bin_duration("2025-01-06T09:30:00-05:00", t)
          == timedelta(hours=4)
          and sb.bin_duration("2025-01-06T13:30:00-05:00", t)
          == timedelta(hours=2, minutes=30))

    # Early close (2025-07-03, close 13:00): single bin 09:30->13:00;
    # a 13:30 bin start does not exist on that session.
    bins = t.bins_for_date("2025-07-03")
    check("early-close session has exactly one bin",
          len(bins) == 1, f"{bins}")
    e = t.bin_end("2025-07-03T09:30:00-04:00")
    check("early-close bin end 13:00-04:00",
          e.isoformat() == "2025-07-03T13:00:00-04:00", e.isoformat())
    expect_refusal("early-close 13:30 start refused (gapped bin)",
                   lambda: t.bin_end("2025-07-03T13:30:00-04:00"),
                   "not a bin start")

    # DST transitions: same wall-clock ends, shifted UTC offset.
    check("pre-transition Fri 2025-03-07 bin2 end -05:00",
          t.bin_end("2025-03-07T13:30:00-05:00").isoformat()
          == "2025-03-07T16:00:00-05:00")
    check("post-transition Mon 2025-03-10 bin2 end -04:00",
          t.bin_end("2025-03-10T13:30:00-04:00").isoformat()
          == "2025-03-10T16:00:00-04:00")
    check("fall-back Mon 2025-11-03 bin2 end -05:00",
          t.bin_end("2025-11-03T13:30:00-05:00").isoformat()
          == "2025-11-03T16:00:00-05:00")

    # Missing / ambiguous / malformed lookups fail closed.
    expect_refusal("non-session date refused (Sat 2025-01-04)",
                   lambda: t.bin_end("2025-01-04T09:30:00-05:00"),
                   "absent from pinned session table")
    expect_refusal("beyond-table date refused (2026-11-02)",
                   lambda: t.bin_end("2026-11-02T09:30:00-05:00"),
                   "absent from pinned session table")
    expect_refusal("non-bin start refused (10:30)",
                   lambda: t.bin_end("2025-01-06T10:30:00-05:00"),
                   "not a bin start")
    expect_refusal("naive timestamp refused",
                   lambda: t.bin_end(datetime(2025, 1, 6, 9, 30)),
                   "naive")
    expect_refusal("duplicate session row refused (ambiguous table)",
                   lambda: sb.SessionTable.from_sessions(
                       [{"date": "2025-01-06", "open": "09:30",
                         "close": "16:00"},
                        {"date": "2025-01-06", "open": "09:30",
                         "close": "16:00"}]),
                   "ambiguous")

    # Next-bin-start resolution (incl. across an early close + holiday
    # weekend: Thu 2025-07-03 -> Mon 2025-07-07).
    check("next bin start within session",
          t.next_bin_start("2025-01-06T09:30:00-05:00").isoformat()
          == "2025-01-06T13:30:00-05:00")
    check("next bin start across sessions",
          t.next_bin_start("2025-01-06T13:30:00-05:00").isoformat()
          == "2025-01-07T09:30:00-05:00")
    check("next bin start after early close",
          t.next_bin_start("2025-07-03T09:30:00-04:00").isoformat()
          == "2025-07-07T09:30:00-04:00")

    # Pin enforcement: altered bytes and a missing file both refuse.
    raw = open(sb.default_table_path(), "rb").read()
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "tampered.json")
        with open(p, "wb") as f:
            f.write(raw[:-2] + b"9}")
        expect_refusal("tampered table refused (hash pin)",
                       lambda: sb.load_pinned_table(p), "hash mismatch")
        expect_refusal("missing table refused",
                       lambda: sb.load_pinned_table(
                           os.path.join(d, "nope.json")), "missing")

    print("SUMMARY", "FAIL" if FAILURES else "PASS", FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
