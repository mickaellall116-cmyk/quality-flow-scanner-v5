# Split Adjudication — TOP-50 Liquidity Ranking Input
**Status:** MECHANICAL ADJUDICATION COMPLETE (2026-10-04). Frozen rule for the experiment.
**Scope:** the 60-day mean dollar-volume input to the TOP-50 composite only. No price adjustment. No imputation.

## The 15 flagged symbols

Continuity check: 5-day average dollar volume (raw close × raw volume) before vs after each Yahoo-flagged event. Within [0.8, 1.25] = continuous.

| Symbol | Event date | Factor | DV ratio | Verdict |
|--------|-----------|--------|----------|---------|
| ANET | 2024-12-04 | 4.0 | 0.99 | Real split; continuous — use as-is |
| BKNG | 2026-04-06 | 25.0 | 0.84 | Continuous — use as-is |
| CRWD | 2026-07-02 | 4.0 | 0.70 | Discontinuous — 3-day exclusion |
| FDX | 2026-06-01 | 1.241 | 1.26 | Likely special distribution — 3-day exclusion |
| HON | 2025-10-30 | 1.061 | 0.64 | Likely spinoff adjustment — 3-day exclusion |
| HON | 2026-06-29 | 0.9535 | 1.10 | Continuous — use as-is |
| KLAC | 2026-06-12 | 10.0 | 1.44 | Discontinuous — 3-day exclusion |
| LCID | 2025-09-02 | 0.1 | 1.94 | Reverse split; discontinuous — 3-day exclusion |
| NFLX | 2025-11-17 | 10.0 | 1.10 | Real split; continuous — use as-is |
| NOW | 2025-12-18 | 5.0 | 0.81 | Real split; continuous — use as-is |
| PANW | 2024-12-16 | 2.0 | 1.73 | Discontinuous — 3-day exclusion |
| PPLT | 2026-05-18 | 10.0 | 0.38 | Discontinuous — 3-day exclusion |
| SBET | 2025-05-06 | 0.0833 | 3.77 | **Excluded from universe** (warmup failure) — moot |
| WDC | 2025-02-24 | 1.323 | 1.08 | Likely spinoff adjustment; continuous — use as-is |
| XLE | 2025-12-05 | 2.0 | 0.98 | Real split; continuous — use as-is |
| XLK | 2025-12-05 | 2.0 | 0.83 | Real split; continuous — use as-is |

## Frozen rule

For any quarterly rebalance where a symbol's 60-day dollar-volume lookback contains a flagged event date:
- **Exclude the 3 trading days centered on the event** (event day ±1) from the mean.
- If fewer than 50 valid trading days remain, the symbol is **excluded from TOP eligibility that quarter** (not imputed).
- Symbols with continuous dollar volume use the full 60-day mean unadjusted.

This is mechanical (no discretion), uses only contemporaneous data (no lookahead), and does not adjust prices. The 60-day average absorbs the exclusion; ranking impact is negligible.

## Implementation

`tests/test_top_broad_membership_20261004.py` — `compute_top50(..., split_dates=...)`, fixture M4 verifies the exclusion mechanics.
