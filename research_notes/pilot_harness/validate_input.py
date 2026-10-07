#!/usr/bin/env python3
"""
validate_input.py — Fail-closed 1H input validator, v2
(ChatGPT 6037625281 blockers 2–3; repair per 6037842097).

v2 repairs (ChatGPT 6037842097 probes):
  R1 MISSING-SESSION BLINDNESS: v1 returned PASS on an empty frame with
     days_validated=0 and had no request-window parameter — entirely missing
     sessions were undetectable. v2 REQUIRES a request window
     (--window-start/--window-end, session dates) and enumerates every
     expected session over the whole range:
       - exchange-CLOSED day + 0 bars  → PASS (verified closed, V8a)
       - exchange-OPEN day   + 0 bars  → FAIL  (missing retrieval, V8b)
       - empty frame + window containing open days → FAIL (V8c)
  R2 INTERVAL ENDS IGNORED: v1 derived ends from its own grid; an explicit
     interval_end column with wrong ends passed V7. v2 compares a
     supplied/documented interval_end column against expected boundaries
     (next bar start, or session close for the last bar) — mismatch → FAIL
     (V9). Without the column, derived ends must still be well-formed.
     Vendor interval semantics are NOT manufactured: an UNKNOWN contract
     scope is preserved, never defaulted.
  R4 OHLCV SCHEMA: required columns, finite values, High >= max(Open,Close),
     Low <= min(Open,Close), Volume >= 0 (V10).

Kept from v1:
  V1 tz-aware America/New_York index
  V2 strictly increasing, no duplicates
  V3 [start,end) lies within a single session bin (no straddles)
  V4 no bars on exchange-closed days
  V5 session-date close resolved from XNYS calendar (no 16:00 fallback)
  V6 expected 1H constituents complete per session type
  V7 interval durations well-formed (60min; 30-min partial only as session's
     last bar with confirming close)

Usage:
  python3 validate_input.py --input 1h.csv --symbol AAPL \
      --window-start 2026-09-08 --window-end 2026-09-08 [--interval-end-col interval_end]
"""
import argparse
import sys

import numpy as np
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


def expected_end(ts: pd.Timestamp, exp_starts: list[pd.Timestamp],
                 session_close: pd.Timestamp) -> pd.Timestamp:
    idx = exp_starts.index(ts)
    return exp_starts[idx + 1] if idx + 1 < len(exp_starts) else session_close


def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    return df


def validate(df: pd.DataFrame, symbol: str,
             window_start: str, window_end: str,
             interval_end_col: str | None = None,
             as_of: pd.Timestamp | None = None) -> dict:
    """Run all checks. Returns a report dict; raises ValidationError on failure.

    window_start/window_end: session dates 'YYYY-MM-DD' (inclusive).
    interval_end_col: optional column name carrying the vendor's documented
        interval end per bar; compared against expected boundaries.
    as_of: MANDATORY tz-aware causal cutoff (ChatGPT 6039806101, finding 1).
        Expected constituents are those whose (documented or derived)
        interval end is <= as_of. Any supplied bar with start or end after
        as_of is REJECTED (V11) — future data is never silently discarded.
        An open session whose constituents are incomplete because as_of has
        not passed is allowed to be causally partial; sessions complete
        before as_of must be fully present; verified closed days must have
        zero bars.
    """
    if as_of is None:
        raise TypeError("as_of is mandatory: validation is causal, "
                        "pass a tz-aware cutoff")
    as_of = pd.Timestamp(as_of)
    if as_of.tz is None:
        raise TypeError("as_of must be tz-aware")
    as_of_ny = as_of.tz_convert(NY)

    report = {"symbol": symbol, "checks": {}, "partials": [],
              "window": [window_start, window_end],
              "as_of": str(as_of_ny)}

    ws = pd.Timestamp(window_start).tz_localize(NY).normalize()
    we = pd.Timestamp(window_end).tz_localize(NY).normalize()
    if we < ws:
        raise ValidationError("V8: window_end before window_start")

    df = _norm_cols(df)
    if interval_end_col is not None:
        interval_end_col = interval_end_col.lower()

    # V10: OHLCV schema (applies even to empty frames with columns).
    required = {"open", "high", "low", "close", "volume"}
    missing_cols = required - set(df.columns)
    if missing_cols and not df.empty:
        raise ValidationError(
            f"V10: missing OHLCV columns: {sorted(missing_cols)}")
    if not df.empty:
        for c in ["open", "high", "low", "close", "volume"]:
            vals = pd.to_numeric(df[c], errors="coerce")
            if vals.isna().any():
                raise ValidationError(f"V10: non-numeric/NaN in column {c}")
            if not np.isfinite(vals.to_numpy(dtype=float)).all():
                raise ValidationError(f"V10: non-finite value in column {c}")
        bad_hl = df[(df["high"] < df[["open", "close"]].max(axis=1))]
        if not bad_hl.empty:
            raise ValidationError(
                f"V10: High < max(Open,Close) on {len(bad_hl)} bars")
        bad_ll = df[(df["low"] > df[["open", "close"]].min(axis=1))]
        if not bad_ll.empty:
            raise ValidationError(
                f"V10: Low > min(Open,Close) on {len(bad_ll)} bars")
        if (df["volume"] < 0).any():
            raise ValidationError("V10: negative volume")
    report["checks"]["V10_ohlcv_schema"] = "pass"

    # Index checks (skip if empty — handled by V8 below).
    local = None
    if not df.empty:
        # V1: tz-aware
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValidationError("V1: index is not a DatetimeIndex")
        if df.index.tz is None:
            raise ValidationError(
                "V1: index is tz-naive; refusing to silently localize "
                "(declare an explicit timezone policy instead)")
        local = df.index.tz_convert(NY)
        report["checks"]["V1_tz_aware"] = "pass"

        # V2: strictly increasing, no duplicates
        if local.duplicated().any():
            dups = local[local.duplicated()].tolist()
            raise ValidationError(f"V2: duplicate timestamps: {dups[:5]}")
        if not local.is_monotonic_increasing:
            raise ValidationError("V2: index is not strictly increasing")
        report["checks"]["V2_ordered_unique"] = "pass"

    # V11: causal input (ChatGPT 6039806101, finding 1). No supplied bar
    # may carry information from after as_of. Reject any bar whose start
    # OR interval end is after as_of — future rows are never silently
    # discarded; they are a hard failure.
    bar_end: dict = {}
    if local is not None:
        doc_ends = None
        if interval_end_col is not None:
            doc_ends = pd.to_datetime(df[interval_end_col])
            if doc_ends.dt.tz is None:
                raise ValidationError(
                    "V9: interval_end column is tz-naive; refusing to "
                    "silently localize")
            doc_ends = doc_ends.dt.tz_convert(NY)
        for i, ts in enumerate(local):
            if ts > as_of_ny:
                raise ValidationError(
                    f"V11: bar start {ts} is after as_of {as_of_ny}; "
                    f"future data rejected, not discarded")
            end = doc_ends.iloc[i] if doc_ends is not None else None
            if end is None:
                # Derived end: next expected start, else session close.
                # (Bars off the expected grid are caught by V6 below;
                # bars on closed days by V4.)
                day = ts.normalize()
                sched = xnys_schedule(day)
                if sched is not None:
                    s_open, s_close = sched
                    exp = expected_1h_starts(s_open, s_close)
                    if ts in exp:
                        end = expected_end(ts, exp, s_close)
            if end is not None and end > as_of_ny:
                raise ValidationError(
                    f"V11: bar at {ts} has interval end {end} after as_of "
                    f"{as_of_ny}; the interval has not closed — future "
                    f"data rejected, not discarded")
            bar_end[ts] = end
    report["checks"]["V11_causal_input"] = "pass"

    # V8: enumerate expected sessions over the WHOLE request window.
    by_day: dict[pd.Timestamp, list] = {}
    if local is not None:
        for ts in local:
            by_day.setdefault(ts.normalize(), []).append(ts)

    open_days, closed_days = [], []
    day = ws
    while day <= we:
        sched = xnys_schedule(day)
        if sched is None:
            closed_days.append(day)
        else:
            open_days.append((day, sched))
        day += pd.Timedelta(days=1)
    report["expected_open_days"] = len(open_days)
    report["expected_closed_days"] = len(closed_days)

    # V8c: empty frame with open days in window → missing retrieval.
    # V8c: empty frame. Missing retrieval only if some session in the
    # window has DUE constituents (interval end <= as_of). An empty frame
    # with no due constituents is a causally-consistent partial capture
    # (e.g. a 10:00 capture on a regular day: no 1H bar has closed yet).
    if df.empty:
        due_days = []
        for day, (s_open, s_close) in open_days:
            exp = expected_1h_starts(s_open, s_close)
            due = [s for s in exp
                   if expected_end(s, exp, s_close) <= as_of_ny]
            if due:
                due_days.append(day.strftime("%Y-%m-%d"))
        if due_days:
            raise ValidationError(
                f"V8: empty input but {len(due_days)} exchange-OPEN sessions "
                f"have due constituents (interval end <= as_of {as_of_ny}): "
                f"{due_days[:5]}; missing retrieval, not a verified "
                f"closed window")
        report["checks"]["V8_window_coverage"] = \
            ("pass (empty input, no due constituents as of "
             f"{as_of_ny}; causally partial or all closed)")
        report["days_validated"] = 0
        report["bars_validated"] = 0
        report["due_constituents"] = 0
        report["causally_partial_days"] = [
            d.strftime("%Y-%m-%d") for d, _ in open_days]
        return report

    report["causally_partial_days"] = []
    total_due = 0
    for day, (session_open, session_close) in open_days:
        starts = by_day.get(day, [])

        exp_starts = expected_1h_starts(session_open, session_close)
        exp_set = set(exp_starts)
        got_set = set(starts)

        # Due constituents: expected starts whose interval end <= as_of.
        # Sessions complete before as_of have ALL constituents due;
        # a session open at as_of may be causally partial (only due
        # constituents required); sessions entirely after as_of have
        # none due (any supplied bars already failed V11).
        due_set = {s for s in exp_starts
                   if expected_end(s, exp_starts, session_close) <= as_of_ny}
        total_due += len(due_set)
        if not due_set and not starts:
            report["causally_partial_days"].append(day.strftime("%Y-%m-%d"))

        # V8b: open day with zero bars but due constituents → missing.
        if not starts and due_set:
            raise ValidationError(
                f"V8: exchange-OPEN session {day.date()} has 0 bars but "
                f"{len(due_set)} constituents are due as of {as_of_ny}; "
                f"missing retrieval (verified open via XNYS calendar)")
        # (V8a: closed days are validated separately below.)

        # V6: due-completeness + no extras. Gaps must be observable,
        # never filled; off-grid bars are rejected, not ignored.
        missing = sorted(due_set - got_set)
        if missing:
            raise ValidationError(
                f"V6: missing due 1H constituents on {day.date()} "
                f"(as_of {as_of_ny}): "
                f"{[t.strftime('%H:%M') for t in missing]}; "
                f"gaps must be observable, never filled")
        extra = sorted(got_set - exp_set)
        if extra:
            raise ValidationError(
                f"V6: unexpected 1H bars on {day.date()}: "
                f"{[t.strftime('%H:%M') for t in extra]}")

        # V9: interval-end contract. If a vendor interval_end column is
        # supplied, compare every bar's documented end against the expected
        # boundary. A calendar-derived end is not proof of vendor coverage.
        if interval_end_col is not None:
            ends = pd.to_datetime(df[interval_end_col])
            if ends.dt.tz is None:
                raise ValidationError(
                    "V9: interval_end column is tz-naive; refusing to "
                    "silently localize")
            ends = ends.dt.tz_convert(NY)
            for ts in starts:
                exp_end = expected_end(ts, exp_starts, session_close)
                got_end = ends.loc[local == ts]
                if len(got_end) != 1:
                    raise ValidationError(
                        f"V9: ambiguous interval_end lookup for {ts}")
                got_end = got_end.iloc[0]
                if got_end != exp_end:
                    raise ValidationError(
                        f"V9: interval_end mismatch at {ts}: vendor documents "
                        f"{got_end.strftime('%H:%M')}, expected boundary "
                        f"{exp_end.strftime('%H:%M')}; refusing to "
                        f"manufacture vendor semantics")
            report["checks"].setdefault("V9_interval_end_contract", "pass")

        # V3 + V7: per-bar interval validation (derived ends, well-formed).
        for ts in starts:
            end = expected_end(ts, exp_starts, session_close)
            duration_min = (end - ts).total_seconds() / 60
            if duration_min not in (60, 30):
                raise ValidationError(
                    f"V7: malformed interval at {ts}: duration {duration_min}min")
            if duration_min == 30:
                if ts != exp_starts[-1]:
                    raise ValidationError(
                        f"V7: 30-min partial at {ts} is not the session's last bar")
                report["partials"].append(
                    f"{day.date()} {ts.strftime('%H:%M')} 30-min partial "
                    f"(session close {session_close.strftime('%H:%M')})")

            s_min = ts.hour * 60 + ts.minute
            e_min = end.hour * 60 + end.minute
            in_first = (s_min >= SESSION_OPEN_MIN and e_min <= FIRST_BIN_CUTOFF_MIN
                        and s_min < FIRST_BIN_CUTOFF_MIN)
            in_second = (s_min >= FIRST_BIN_CUTOFF_MIN)
            if not (in_first or in_second):
                raise ValidationError(
                    f"V3: interval [{ts.strftime('%H:%M')},{end.strftime('%H:%M')}) "
                    f"on {day.date()} straddles a session-bin boundary; rejected")

    # V4: no bars on any closed day (window or otherwise).
    closed_with_bars = sorted(set(by_day) - {d for d, _ in open_days}
                              - {d for d in closed_days})
    for day in closed_days:
        if day in by_day and by_day[day]:
            raise ValidationError(
                f"V4: bars present on exchange-closed day {day.date()} "
                f"({len(by_day[day])} bars); closed days must have zero bars")
    # Bars on dates outside the window entirely.
    ws_n, we_n = ws.normalize(), we.normalize()
    for day in by_day:
        d = day.normalize()
        if d < ws_n or d > we_n:
            raise ValidationError(
                f"V8: bars on {d.date()} outside request window "
                f"[{window_start},{window_end}]")

    report["checks"]["V3_no_straddles"] = "pass"
    report["checks"]["V4_no_closed_day_bars"] = "pass"
    report["checks"]["V5_calendar_resolved"] = "pass"
    report["checks"]["V6_due_constituents_complete"] = "pass"
    report["checks"]["V7_intervals_wellformed"] = "pass"
    report["checks"]["V8_window_coverage"] = "pass"
    if interval_end_col is None:
        report["checks"]["V9_interval_end_contract"] = \
            "not supplied (UNKNOWN vendor contract scope preserved)"
    report["days_validated"] = len(open_days)
    report["bars_validated"] = len(df)
    report["due_constituents"] = total_due
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail-closed 1H input validator (v2)")
    ap.add_argument("--input", required=True)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--window-start", required=True,
                    help="request window start, session date YYYY-MM-DD")
    ap.add_argument("--window-end", required=True,
                    help="request window end, session date YYYY-MM-DD")
    ap.add_argument("--interval-end-col", default=None,
                    help="optional column carrying the vendor's documented "
                         "interval end per bar")
    ap.add_argument("--as-of", required=True,
                    help="MANDATORY causal cutoff, ISO tz-aware "
                         "(e.g. 2026-09-08T16:00:00-04:00)")
    args = ap.parse_args()

    df = pd.read_csv(args.input, parse_dates=["timestamp"], index_col="timestamp")
    df.index = pd.DatetimeIndex(df.index)
    try:
        report = validate(df, args.symbol, args.window_start, args.window_end,
                          args.interval_end_col, as_of=args.as_of)
    except ValidationError as e:
        print(f"VALIDATION FAILED: {e}", file=sys.stderr)
        return 2
    print(f"VALIDATION PASSED: {report['bars_validated']} bars, "
          f"{report['days_validated']} open days validated "
          f"(+{report['expected_closed_days']} verified closed), "
          f"symbol {report['symbol']}")
    for k, v in report["checks"].items():
        print(f"  [{v}] {k}")
    for p in report["partials"]:
        print(f"  [partial] {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
