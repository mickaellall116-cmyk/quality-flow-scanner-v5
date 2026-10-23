# TEST EVIDENCE — QF-COINBASE-CRYPTO-ROUTE-READINESS-20261023-06

Environment: pinned venv `~/workspace/qf35_work_20261019/venv`
(CPython 3.12.3), network namespace disabled (`unshare -n`), stdlib
only. All inputs synthetic; no API/candle endpoint was called at any
point in this task.

## Commands

```
cd adapter && unshare -n ~/workspace/qf35_work_20261019/venv/bin/python test_coinbase_15m_adapter.py
cd ..      && unshare -n ~/workspace/qf35_work_20261019/venv/bin/python request_arithmetic.py
```

## Adapter fixtures — final run: 13/13 PASS (exit 0)

```
  normal canonical sha256: bd4490da0b6902e848e91df7b246601e8cd202f53bd3af5551634296ae3060b9
PASS normal_day
  spring canonical sha256: ce00f9056092560815984561cc55725b84b14e7a00151c73343d8c655f7d6608
PASS spring_dst_23h
  fall canonical sha256: dbde3d5ce8f06b6ad9e9fda43b2c00c0722f8e3db65e57aa739823d1956e07e6
PASS fall_dst_25h
PASS missing_row_gap
PASS duplicate_conflict
PASS overlap_dedupe
PASS reversed_descending_order
PASS partial_terminal_bin
PASS zero_volume_nonflat
PASS page_boundary_300
PASS volume_missing_schema
PASS misaligned_stamp
PASS out_of_span
TOTAL: 13/13 PASS
```

Fixture map to the governing task's required set: normal day
(normal_day); spring/fall DST (spring_dst_23h: 92 bars, absorbing
01:30 bin 12; fall_dst_25h: 100 bars, absorbing bin 20, both
repeated-hour bars inside it); missing row (missing_row_gap → GAP);
duplicate timestamp (duplicate_conflict → DUPLICATE; exact-identical
overlap → overlap_dedupe); reversed/descending provider order
(reversed_descending_order, canonical hash identical); overlap
dedupe (overlap_dedupe); partial terminal bin (partial_terminal_bin:
emitted flagged only under explicit allowance, refused otherwise);
zero-volume/nonflat (zero_volume_nonflat → anomaly classed, honest
aggregation continues); 300-row page boundary (page_boundary_300:
exactly 300 bars compose, terminal bin partial-flagged). Additional:
volume_missing_schema (absent/null volume → SCHEMA, the TD defect
class), misaligned_stamp (off-900s-grid → MISALIGNED), out_of_span.

## Disclosed pre-evidence corrections (2)

1. **Bin anchoring.** The first adapter draft anchored bins at
   elapsed 4h offsets from the session open. The DST fixtures failed
   (11/13): on the spring session the sixth bin overhung the span
   (24 elapsed h of bins vs a 23h span), and on the fall session the
   extra hour landed in the 05:30 bin instead of the overnight
   01:30 bin. Root cause: the adopted S-C bins are **wall-anchored**
   (boundaries are the UTC instants OF the 09:30/13:30/17:30/21:30/
   01:30/05:30 ET wall times; the 01:30 open is the fold=0
   occurrence) — six elapsed-4h bins cannot tile a 23/25h span.
   Fixed before evidence; the mechanism is documented in the adapter
   docstring. Same failure family as -94 F-2 (wall-clock vs instant
   confusion), caught by the fixtures, not by inspection.
2. **Test index.** After the fix, counts read [16,16,16,16,12,16] /
   [16,16,16,16,20,16] — the absorbing bin is index 4 (01:30), and
   the test's assertion pointed at index 3 (21:30). Test corrected;
   adapter output unchanged.

## Request arithmetic — final run: ALL ASSERTIONS PASS (exit 0)

```
== Frozen crypto scope, granularity=900, page<=300 ==
HO   per pair: dates=333 elapsed_hours=7992 bars15=31968 pages_no_overlap=107 pages_overlap1=107
DEV  per pair: dates=761 elapsed_hours=18264 bars15=73056 pages_no_overlap=244 pages_overlap1=245
FULL per pair: dates=1094 elapsed_hours=26256 bars15=105024 pages_no_overlap=351 pages_overlap1=352
Per pair total: no_overlap=351 overlap1=352
7 pairs: no_overlap=2457 overlap1=2464
Hard worst (<=1 retry per request, fail-closed after): no_overlap=4914 overlap1=4928
== BTC pilot slices (BTC-USD only) ==
S1 reach+normal 2023-10-19..2023-10-25: dates=7 hours=168 bars15=672 pages=3
S2 fall DST     2023-11-03..2023-11-05: dates=3 hours=73 bars15=292 pages=1
S3 spring DST   2024-03-08..2024-03-10: dates=3 hours=71 bars15=284 pages=1
S4 pagination   2024-01-08..2024-01-17: dates=10 hours=240 bars15=960 pages=4
Pilot candle requests expected: 9; +1 product-availability read = 10; hard ceiling with <=1 retry per request: 20
ALL ARITHMETIC ASSERTIONS PASS
```

## Documentation pins

| Source | URL | Retrieved |
|---|---|---|
| Get product candles (Exchange REST) | https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles | 2026-10-23 |
| Exchange Rate Limits Overview | https://docs.cdp.coinbase.com/exchange/introduction/rate-limits-overview | 2026-10-23 |
| Market Data Terms of Use (Last updated Aug 7, 2026) | https://www.coinbase.com/legal/market_data | 2026-10-23 |
