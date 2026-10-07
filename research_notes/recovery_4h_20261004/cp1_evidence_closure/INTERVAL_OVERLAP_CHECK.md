# Interval-Overlap Check — trade_intersection.py

**Date:** 2026-10-06
**Question:** `trade_intersection.py` sets `holding_intersects_est_calendar`
from signal/entry/exit **endpoint membership**
(`in_est_calendar(sig) or in_est_calendar(ent) or in_est_calendar(ext)`),
not a general interval-overlap test. Does any trade's holding interval span
an EST shifted period with all endpoints outside it — a case the current
flag would miss?

## Method

For each of the 240 trades (canonical shard form, SHA-256 `02608fd4…`):
- Computed true interval overlap: `[entry_time, exit_time]` intersects
  `EST_PERIODS = [("2024-11-03","2025-03-09"), ("2025-11-02","2026-03-08")]`
  using date-range overlap logic.
- Compared against the recorded `holding_intersects_est_calendar` flag.
- Specifically searched for trades where the interval overlaps a period but
  signal, entry, AND exit are all outside it.

## Result: zero material cases

| Check | Count |
|-------|-------|
| Total trades examined | 240 |
| Trades with interval spanning an EST period and all endpoints outside | **0** |
| Trades where endpoint-membership flag disagrees with interval overlap | 0 (see T161 note) |

**T161 (MRNA) note:** This trade has `holding_intersects_est_calendar=True`
while its `[entry, exit]` interval (2026-03-09 → 2026-03-27) does not overlap
any EST period. This is **not** a discrepancy: the flag definition includes
`signal_in_est_calendar`, and T161's signal (2026-03-06T12:30:00-05:00) falls
inside the EST 2025-26 period (ends 2026-03-08). The flag is correct per its
definition; the interval check was deliberately narrower (entry→exit only).

## Materiality assessment

**Observed materiality: none.** No trade would change classification under a
general interval-overlap test. The endpoint-membership approach is sufficient
for this 240-trade dataset because no holding interval straddles a period
boundary with all three endpoints outside.

## Recommendation

**No code change proposed.** Per the assignment, `trade_intersection.py` was
not modified. If a future analysis extends beyond these 240 trades, a true
interval-overlap test should replace endpoint membership — but for the
current evidence set, the distinction has zero observed effect.
