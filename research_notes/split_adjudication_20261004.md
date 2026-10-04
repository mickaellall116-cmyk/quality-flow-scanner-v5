# Split Adjudication — TOP-50 Liquidity Ranking Input
**Status:** MECHANICAL ADJUDICATION COMPLETE, REPAIRED (2026-10-04). Frozen rule.
**Scope:** the 60-day mean dollar-volume input to the TOP-50 composite only.

## REPAIR 2026-10-04 (Mike's final source check — lookahead fix)

The earlier version classified events as "continuous" vs "discontinuous" using 5 days of **post-event** dollar-volume data. For a Jun 29 event with a Jun 30 rebalance, that uses information not available at the rebalance — **lookahead**. The classification is removed entirely.

**Frozen rule (repaired):** the 3-day exclusion applies **unconditionally** to all flagged split events. No continuity check, no post-event data, no classification. The event DATE (known at rebalance from corporate-action calendars) triggers the exclusion; nothing after the event is consulted.

Additionally: the 60-day window is fixed **first** (last 60 trading days), then split days are excluded from within it. The mean uses the remaining 57–60 days — **no backward backfill** to refill to 60.

## The 15 flagged symbols (for reference — all treated identically)

ANET, BKNG, CRWD, FDX, HON (2 events), KLAC, LCID, NFLX, NOW, PANW, PPLT, SBET (excluded from universe — moot), WDC, XLE, XLK.

Event dates in `research_notes/data_inventory_20261004.md` (splits section).

## Rule

For any quarterly rebalance where a symbol's 60-day dollar-volume lookback contains a flagged event date:
- **Exclude the 3 trading days centered on the event** (event day ±1) from the mean.
- If fewer than 50 valid trading days remain, the symbol is **excluded from TOP eligibility that quarter** (not imputed).

## Implementation

`top_broad_experiment.py` — `compute_top50(..., split_dates=...)` (authoritative module).
`tests/test_top_broad_membership_20261004.py` — fixtures R1 (no-lookahead), R2 (no backfill), R3 (dynamic rebalances).
