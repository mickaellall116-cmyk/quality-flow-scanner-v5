#!/usr/bin/env python3
"""Path C emission for -18 with widened calendar-construction bounds.

The pinned -35 generator (sha 2995b124…) constructs the
exchange_calendars XNYS calendar with start=2023-12-01, end=2027-02-01,
which truncates the materialized schedule outside that window. The
library itself is rule-based; widening ONLY the construction bounds
(start=2023-01-01, end=2028-06-30) materializes the same rules over
the -18 window. The row formatting below is byte-identical to the
pinned generator's _fmt/emit loop. This deviation is disclosed in the
-18 RESULT and provenance record; library and version are unchanged
(exchange_calendars 4.13.2, wheel sha fc5a2ad0…).
"""
import argparse
import json

TZ = "America/New_York"


def _fmt(ts):
    local = ts.tz_convert(TZ)
    if local.second != 0 or local.microsecond != 0 or local.nanosecond != 0:
        raise ValueError(f"non-minute-precision timestamp: {local!r}")
    return local.strftime("%Y-%m-%d"), local.strftime("%H:%M")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import exchange_calendars as ecals
    cal = ecals.get_calendar("XNYS", start="2023-01-01", end="2028-06-30")
    sched = cal.schedule
    out = []
    for _idx, row in sched.iterrows():
        d, o = _fmt(row["open"])
        d2, c = _fmt(row["close"])
        assert d == d2, (d, d2)
        if a.start <= d <= a.end:
            out.append({"date": d, "open": o, "close": c})
    out.sort(key=lambda s: s["date"])
    dates = [s["date"] for s in out]
    assert len(set(dates)) == len(dates)
    blob = (json.dumps(out, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True) + "\n").encode("utf-8")
    with open(a.out, "wb") as f:
        f.write(blob)
    print(f"path=C(wide) window={a.start}..{a.end} sessions={len(out)}")


if __name__ == "__main__":
    main()
