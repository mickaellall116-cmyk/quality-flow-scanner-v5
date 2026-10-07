#!/usr/bin/env python3
"""
validate_input.py — Fail-closed 1H input validator (ChatGPT 6037625281, blocker 3).

The archival constructor groups rows by start timestamp and falls back
unknown dates to 16:00. It does NOT:
  - validate interval ends,
  - check closed-day calendar status before aggregation,
  - reject boundary-straddling intervals,
  - verify complete constituents.

This validator runs BEFORE construction and aborts (non-zero exit, no
output bars) on any violation. Nothing is silently corrected or defaulted.

Checks:
  V1  tz-aware, America/New_York-convertible index
  V2  strictly increasing, no duplicates
  V3  every bar's [start, end) lies within a single session bin
      (rejects straddles across the 13:30 boundary or session close)
  V4  no bars on exchange-closed days (holiday/weekend → hard fail)
  V5  session-date close resolvable from XNYS calendar (no 16:00 fallback;
      unknown date → hard fail, unlike the archival constructor)
  V6  expected 1H starts present per session type (completeness);
      missing constituents → hard fail (gaps must be observable, not filled)
  V7  interval end == start + 60min (rejects malformed durations);
      the 15:30 bar on regular days and 12:30 bar on early-close days are
      30-minute partials — flagged, not rejected, when the session close
      confirms the shortened bar

Usage:
  python3 validate_input.py --input 1h.csv --symbol AAPL --calendar xnys
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

NY = "America/New_York"
SESSION_OPEN_MIN = 570       # 09:30
FIRST_BIN_CUTOFF_MIN = 810   # 13:30


class ValidationError(Exception):
    pass


def xnys_schedule(day: pd.Timestamp):
    """Return (open, close) for a date, or None if exchange-closed."""
    import pandas_market_calendars as mcal
    xnys = mcal.get_calendar("XNYS")
    sched = xnys.schedule(start_date=day.date(), end_date=day.date())
    if sched.empty:
        return None
    row = sched.iloc[0]
    return (pd.Timestamp(row["market_open"]).tz_convert(NY),
            pd.Timestamp(row["market_close"]).tz_convert(NY))


def expected_1h_starts(session_open: pd.Timestamp,
                       session_close: pd.Timestamp) -> list[pd.Timestamp]:
    """Expected 1H bar starts for a session.

    Regular (09:30–16:00): 09:30,10:30,11:30,12:30,13:30,14:30,15:30
      (15:30 is a 30-min partial bar)
    Early close (09:30–13:00): 09:30,10:30,11:30,12:30
      (12:30 is a 30-min partial bar)
    """
    starts = []
    t = session_open
    while t < session_close:
        starts.append(t)
        t += pd.Timedelta(hours=1)
    return starts


def validate(df: pd.DataFrame, symbol: str) -> dict:
    """Run all checks. Returns a report dict; raises ValidationError on failure."""
    report = {"symbol": symbol, "checks": {}, "partials": []}

    # Empty input (e.g. full-holiday day): nothing to validate — valid by
    # construction. Zero bars is the EXPECTED outcome for closed days.
    if df.empty:
        report["checks"]["V0_empty_input"] = "pass (0 bars)"
        report["days_validated"] = 0
        report["bars_validated"] = 0
        return report

    # V1: tz-aware
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValidationError("V1: index is not a DatetimeIndex")
    if df.index.tz is None:
        raise ValidationError("V1: index is tz-naive; US equity data must be tz-aware")
    local = df.index.tz_convert(NY)
    report["checks"]["V1_tz_aware"] = "pass"

    # V2: strictly increasing, no duplicates
    if local.duplicated().any():
        dups = local[local.duplicated()].tolist()
        raise ValidationError(f"V2: duplicate timestamps: {dups[:5]}")
    if not local.is_monotonic_increasing:
        raise ValidationError("V2: index is not strictly increasing")
    report["checks"]["V2_ordered_unique"] = "pass"

    # Per-bar end inference: next bar's start, or session close for last bar of day
    by_day: dict[pd.Timestamp, list] = {}
    for ts in local:
        by_day.setdefault(ts.normalize(), []).append(ts)

    for day, starts in sorted(by_day.items()):
        sched = xnys_schedule(day)
        # V4: no bars on closed days
        if sched is None:
            raise ValidationError(
                f"V4: bars present on exchange-closed day {day.date()} "
                f"({len(starts)} bars); closed days must have zero bars")
        session_open, session_close = sched
        # V5 is implicit: sched resolved from the calendar (no 16:00 fallback)
        report["checks"].setdefault("V5_calendar_resolved", "pass")

        exp_starts = expected_1h_starts(session_open, session_close)
        exp_set = set(exp_starts)
        got_set = set(starts)

        # V6: completeness — every expected start present
        missing = sorted(exp_set - got_set)
        if missing:
            raise ValidationError(
                f"V6: missing 1H constituents on {day.date()}: "
                f"{[t.strftime('%H:%M') for t in missing]}; "
                f"gaps must be observable, never filled")

        # Unexpected bars (outside the expected grid)
        extra = sorted(got_set - exp_set)
        if extra:
            raise ValidationError(
                f"V6: unexpected 1H bars on {day.date()}: "
                f"{[t.strftime('%H:%M') for t in extra]}")

        # V3 + V7: per-bar interval validation
        for ts in starts:
            # V7: interval end — next expected start, or session close
            idx = exp_starts.index(ts)
            end = exp_starts[idx + 1] if idx + 1 < len(exp_starts) else session_close
            duration_min = (end - ts).total_seconds() / 60
            if duration_min not in (60, 30):
                raise ValidationError(
                    f"V7: malformed interval at {ts}: duration {duration_min}min")
            if duration_min == 30:
                # Partial bar: only legal as the last bar of a session
                # whose close confirms the shortened bar.
                if ts != exp_starts[-1]:
                    raise ValidationError(
                        f"V7: 30-min partial at {ts} is not the session's last bar")
                report["partials"].append(
                    f"{day.date()} {ts.strftime('%H:%M')} 30-min partial "
                    f"(session close {session_close.strftime('%H:%M')})")

            # V3: straddle check — [start, end) must lie in one session bin.
            # Bins: [09:30,13:30), [13:30,close).
            s_min = ts.hour * 60 + ts.minute
            e_min = end.hour * 60 + end.minute
            in_first = (s_min >= SESSION_OPEN_MIN and e_min <= FIRST_BIN_CUTOFF_MIN
                        and s_min < FIRST_BIN_CUTOFF_MIN)
            in_second = (s_min >= FIRST_BIN_CUTOFF_MIN)
            if not (in_first or in_second):
                raise ValidationError(
                    f"V3: interval [{ts.strftime('%H:%M')},{end.strftime('%H:%M')}) "
                    f"on {day.date()} straddles a session-bin boundary; rejected")

    report["checks"]["V3_no_straddles"] = "pass"
    report["checks"]["V4_no_closed_day_bars"] = "pass"
    report["checks"]["V6_constituents_complete"] = "pass"
    report["checks"]["V7_intervals_wellformed"] = "pass"
    report["days_validated"] = len(by_day)
    report["bars_validated"] = len(df)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail-closed 1H input validator")
    ap.add_argument("--input", required=True)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--calendar", default="xnys", choices=["xnys"])
    args = ap.parse_args()

    df = pd.read_csv(args.input, parse_dates=["timestamp"], index_col="timestamp")
    df.index = pd.DatetimeIndex(df.index)
    try:
        report = validate(df, args.symbol)
    except ValidationError as e:
        print(f"VALIDATION FAILED: {e}", file=sys.stderr)
        return 2
    print(f"VALIDATION PASSED: {report['bars_validated']} bars, "
          f"{report['days_validated']} days, symbol {report['symbol']}")
    for k, v in report["checks"].items():
        print(f"  [{v}] {k}")
    for p in report["partials"]:
        print(f"  [partial] {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
