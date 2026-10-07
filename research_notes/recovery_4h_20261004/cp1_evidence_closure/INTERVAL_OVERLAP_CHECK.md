# Interval-Overlap Check — trade_intersection.py (CORRECTED 2026-10-07)

**Date:** 2026-10-06 (corrected 2026-10-07 per ChatGPT amendment 6028744990)
**Checker code:** `interval_overlap_checker.py` (published, runnable)
**Full per-trade output:** `interval_overlap_full_output.csv` (240 rows)
**Question:** `trade_intersection.py` sets `holding_intersects_est_calendar`
from signal/entry/exit **endpoint membership**, not a general interval-overlap
test. Does any trade's holding interval span an EST shifted period with all
endpoints outside it — a case the current flag would miss?

## Two definitions, reported separately (correction 2026-10-07)

The 2026-10-06 version blurred these. They are **different definitions** and
are reported as separate columns; no endpoint-equivalence claim is made.

- **Definition F (flag, as recorded):**
  `holding_intersects_est_calendar = in_est_calendar(entry) OR
  in_est_calendar(exit) OR in_est_calendar(signal)`, where `in_est_calendar`
  is **date** membership in `EST_PERIODS = [("2024-11-03","2025-03-09"),
  ("2025-11-02","2026-03-08")]`. Note: the **signal date is included**.
- **Definition I (true holding-interval overlap):** the `[entry_time,
  exit_time]` interval's date span intersects an EST period's date span.
  The signal date is **not** included.

## Method

For each of the 240 trades (canonical shard form, SHA-256
`02608fd49331e5d795ac678440c7d9792f74d577eeb454d7bd68686b234fd872`):
- Recomputed Definition F from the raw signal/entry/exit timestamps and
  cross-checked it against the recorded flag (0 mismatches — the flag was
  computed correctly per its definition).
- Computed Definition I independently.
- Searched for trades where the interval overlaps a period but signal, entry,
  AND exit dates are all outside it.

## Result

| Check | Count |
|-------|-------|
| Total trades examined | 240 |
| Definition F (recorded flag) True | 88 |
| Definition I (interval overlap) True | 87 |
| Definition F recomputed ≠ recorded | **0** |
| Definition F vs Definition I differ | **1** (T161, see below) |
| Interval spans a period with all endpoints outside | **0** |

## T161 (MRNA) — corrected entry

T161: signal `2026-03-06T12:30:00-05:00`, entry `2026-03-09`, exit `2026-03-27`.

| Definition | Value | Reason |
|------------|-------|--------|
| **F** (recorded flag) | **True** | signal date 2026-03-06 falls in EST period 2025-11-02…2026-03-08 |
| **I** (interval overlap) | **False** | [2026-03-09, 2026-03-27] starts after the period ends 2026-03-08 |

This is **not a data error**: the two definitions legitimately disagree
because F includes the signal date and I does not. The 2026-10-06 note called
this "not a discrepancy," which was imprecise — it **is** a definitional
difference (1 of 240 trades), and it is reported as such here. Neither
definition is claimed equivalent to the other in general.

## Materiality assessment

**Observed materiality: none.** Zero trades have a holding interval spanning
an EST period with all three endpoint dates outside it — the case a pure
endpoint-membership flag would miss. The endpoint-membership approach is
sufficient **for this 240-trade dataset** because no holding interval
straddles a period boundary with all endpoints outside. This is an observed
property of the dataset, not a general equivalence claim.

## Recommendation

**No code change proposed.** Per the assignment, `trade_intersection.py` was
not modified. If a future analysis extends beyond these 240 trades, a true
interval-overlap test should replace endpoint membership — but for the
current evidence set, the distinction has zero observed effect beyond the
single definitional T161 difference documented above.
