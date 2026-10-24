#!/usr/bin/env python3
"""QF-XNYS-ISOLATED-CALENDAR-GENERATION-20261019-35 r1 — dual-path emitter.

Implements GENERATION_CONTRACT.md §4 exactly:
- Path A: pandas_market_calendars keyed with the NATIVE key "NYSE" only.
  The "XNYS" key inside pandas_market_calendars (mirror module) is
  FORBIDDEN and is never used or imported here.
- Path C: exchange_calendars keyed directly with "XNYS".
- Emits sessions {date, open, close} in America/New_York local time for a
  closed window, canonical-serialized (UTF-8 JSON, sorted keys, compact
  separators, one trailing newline).
Deterministic inputs only: the pinned wheel closure, the two key strings,
and the window bounds (CLI args).
"""
import argparse
import json
import sys

TZ = "America/New_York"


def _fmt(ts):
    """pandas Timestamp (tz-aware) -> (date_str, hhmm_str) in local time."""
    local = ts.tz_convert(TZ)
    if local.second != 0 or local.microsecond != 0 or local.nanosecond != 0:
        raise ValueError(f"non-minute-precision timestamp: {local!r}")
    return local.strftime("%Y-%m-%d"), local.strftime("%H:%M")


def emit_pmc(start, end):
    import pandas_market_calendars as mcal

    cal = mcal.get_calendar("NYSE")  # native key ONLY (mirror key forbidden)
    sched = cal.schedule(start_date=start, end_date=end)
    out = []
    for _idx, row in sched.iterrows():
        d, o = _fmt(row["market_open"])
        d2, c = _fmt(row["market_close"])
        assert d == d2, (d, d2)
        out.append({"date": d, "open": o, "close": c})
    return out


def emit_ec(start, end):
    import exchange_calendars as ecals
    import pandas as pd

    cal = ecals.get_calendar("XNYS", start="2023-12-01", end="2027-02-01")
    sched = cal.schedule
    out = []
    for _idx, row in sched.iterrows():
        d, o = _fmt(row["open"])
        d2, c = _fmt(row["close"])
        assert d == d2, (d, d2)
        if start <= d <= end:
            out.append({"date": d, "open": o, "close": c})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", choices=["A", "C"], required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sessions = emit_pmc(a.start, a.end) if a.path == "A" else emit_ec(a.start, a.end)
    sessions.sort(key=lambda s: s["date"])
    dates = [s["date"] for s in sessions]
    if len(set(dates)) != len(dates):
        raise ValueError("duplicate session dates emitted")
    if any(not (a.start <= d <= a.end) for d in dates):
        raise ValueError("session outside window emitted")
    blob = (json.dumps(sessions, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True) + "\n").encode("utf-8")
    with open(a.out, "wb") as f:
        f.write(blob)
    print(f"path={a.path} window={a.start}..{a.end} sessions={len(sessions)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
