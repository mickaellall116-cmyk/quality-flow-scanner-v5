#!/usr/bin/env python3
"""
request_arithmetic.py — task -06: exact request arithmetic for the
frozen crypto scope at Coinbase granularity=900 (15m), <=300 candles
per response (documented ceiling). ARITHMETIC ONLY — nothing executed.

Spans are the frozen S-C session-date ranges (manifest candidate
QF-CAPTURE-MANIFEST-CANDIDATE-20261023-01): HO session dates
2023-10-19..2024-09-15 (the dates under the 227-session XNYS HO
window), DEV session dates 2024-09-16..2026-10-16 (under the
524-session DEV window); the two spans abut exactly at
2024-09-16 09:30 ET. Chunks follow the -88/-01 rule: <=208
consecutive ET dates per chunk, 6 chunks per pair for HO+DEV.

Elapsed bars are computed from absolute UTC spans (zoneinfo), so DST
sessions contribute 23/25 elapsed hours exactly. Stdlib only.
"""
import math
from datetime import date, timedelta

from adapter.coinbase_15m_adapter import session_span_utc

PAGE = 300           # documented max candles per response
BARS_PER_HOUR = 4    # granularity 900s


def span_stats(d0, d1):
    """(dates, elapsed_hours, bars15) for session dates d0..d1 incl."""
    s, _ = session_span_utc(d0)
    _, e = session_span_utc(d1)
    hours = (e - s) / timedelta(hours=1)
    assert hours == int(hours)
    return (d1 - d0).days + 1, int(hours), int(hours) * BARS_PER_HOUR


def pages_no_overlap(n):
    return math.ceil(n / PAGE)


def pages_overlap(n):
    """1-candle overlap at each page seam (dedupe-safe variant)."""
    if n <= PAGE:
        return 1
    return 1 + math.ceil((n - PAGE) / (PAGE - 1))


HO = (date(2023, 10, 19), date(2024, 9, 15))
DEV = (date(2024, 9, 16), date(2026, 10, 16))
PAIRS = 7

ho = span_stats(*HO)
dev = span_stats(*DEV)
full = (ho[0] + dev[0], ho[1] + dev[1], ho[2] + dev[2])

# Cross-checks against independently derived values.
assert ho == (333, 7992, 31968), ho
assert dev == (761, 18264, 73056), dev
assert full == (1094, 26256, 105024), full
assert math.ceil(full[0] / 208) == 6  # -88 chunk rule -> 6 chunks/pair

print("== Frozen crypto scope, granularity=900, page<=300 ==")
for name, st in (("HO  ", ho), ("DEV ", dev), ("FULL", full)):
    print(f"{name} per pair: dates={st[0]} elapsed_hours={st[1]} "
          f"bars15={st[2]} pages_no_overlap={pages_no_overlap(st[2])} "
          f"pages_overlap1={pages_overlap(st[2])}")
per_pair_no = pages_no_overlap(ho[2]) + pages_no_overlap(dev[2])
per_pair_ov = pages_overlap(ho[2]) + pages_overlap(dev[2])
print(f"Per pair total: no_overlap={per_pair_no} overlap1={per_pair_ov}")
print(f"7 pairs: no_overlap={per_pair_no * PAIRS} "
      f"overlap1={per_pair_ov * PAIRS}")
print(f"Hard worst (<=1 retry per request, fail-closed after): "
      f"no_overlap={2 * per_pair_no * PAIRS} "
      f"overlap1={2 * per_pair_ov * PAIRS}")
print("Receipt/status reads: Coinbase public REST has no usage/"
      "credit endpoint (documented); receipt discipline models +1 "
      "product-availability read per pair per execution day (not a "
      "provider credit). Cost: $0 (public endpoints, no key required "
      "per docs rate-limit page: 10 req/s per IP, burst 15).")
print("Pacing: at the program's conservative 1 request / 2 s, "
      f"no-overlap full coverage = {per_pair_no * PAIRS * 2} s "
      f"(~{per_pair_no * PAIRS * 2 / 60:.0f} min) of pacing; at "
      "5 req/s (half the documented public limit) = "
      f"{per_pair_no * PAIRS / 5 / 60:.1f} min pure request time.")

print()
print("== BTC pilot slices (BTC-USD only) ==")
SLICES = [
    ("S1 reach+normal 2023-10-19..2023-10-25",
     date(2023, 10, 19), date(2023, 10, 25)),
    ("S2 fall DST     2023-11-03..2023-11-05",
     date(2023, 11, 3), date(2023, 11, 5)),
    ("S3 spring DST   2024-03-08..2024-03-10",
     date(2024, 3, 8), date(2024, 3, 10)),
    ("S4 pagination   2024-01-08..2024-01-17",
     date(2024, 1, 8), date(2024, 1, 17)),
]
tot_pages = 0
for name, d0, d1 in SLICES:
    st = span_stats(d0, d1)
    p = pages_no_overlap(st[2])
    assert p == pages_overlap(st[2])
    tot_pages += p
    print(f"{name}: dates={st[0]} hours={st[1]} bars15={st[2]} pages={p}")
print(f"Pilot candle requests expected: {tot_pages}; "
      f"+1 product-availability read = {tot_pages + 1}; "
      f"hard ceiling with <=1 retry per request: "
      f"{2 * (tot_pages + 1)}")
assert tot_pages == 9
print("ALL ARITHMETIC ASSERTIONS PASS")
