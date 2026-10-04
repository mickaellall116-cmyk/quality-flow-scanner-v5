# PARAMETER FRAGILITY INVENTORY
**Recovery pre-run package — Phase D**
**Date:** 2026-10-04 | **Branch:** `recovery-4h-20261004`
**Status:** INVENTORY ONLY — no optimization, no winner selection.
Robustness surface mapping only.

---

## 1. Rule

For each tunable parameter: define a small bounded neighborhood around the
canonical (frozen) setting. Vary ONE parameter at a time first. Cap total
combinatorial variants. Report the full surface — no selecting the best.

## 2. Inventory

### Signal generation

| Param | Canonical | Neighborhood | Rationale |
|-------|-----------|--------------|-----------|
| EMA lengths (9/21/55/200) | 9, 21, 55, 200 | ±2 bars each (one-at-a-time) | Tests indicator-length sensitivity |
| Warmup bars | 215 | 200, 230 | Tests warmup dependence |
| ADX threshold (strong_trend) | 20 | 18, 22 | |
| ADX threshold (trendScore) | 25 | 23, 27 | |
| ATR ratio (strong_trend) | 0.85 | 0.80, 0.90 | |
| ATR ratio (trendScore) | 1.0 | 0.95, 1.05 | |
| trendScore (confirmed) | ≥4 | ≥3, ≥5 | |
| trendScore (ready) | ≥3 | ≥2, ≥4 | |
| Breakout lookback | 10 bars | 8, 12 | |
| Volume filter | > vol_ma(20) | vol_ma(15), vol_ma(25) | |
| HOT_ATR | 1.5 | 1.25, 1.75 | |

### Trade management

| Param | Canonical | Neighborhood | Rationale |
|-------|-----------|--------------|-----------|
| SL_ATR | 1.5 | 1.25, 1.75 | |
| TP_ATR | 2.0 | 1.75, 2.25 | |
| TRAIL_ATR | 2.5 | 2.0, 3.0 | |
| TP1 fraction | 50% | 40%, 60% | |

### Portfolio stack

| Param | Canonical | Neighborhood | Rationale |
|-------|-----------|--------------|-----------|
| Max concurrent | 5 | 4, 6 | |
| Sector cap | 2 | 1, 3 | |
| Risk per trade | 1% | 0.75%, 1.25% | |
| RS rank top-N (contested) | 2 | 1, 3 | |
| S4 halt (DD_HALT) | 0.90 | 0.88, 0.92 | |
| S4 resume (DD_RESUME) | 0.95 | 0.93, 0.97 | |

### NOT tunable (structural — excluded from inventory)

- Entry at next bar open (execution model, not a parameter)
- Blended R accounting (accounting definition)
- 4H bar constructor (subject of Phase A, not a tuning dial)
- Sector map assignments (frozen mapping)
- Cost levels (reported as legs, not tuned)

## 3. Execution plan (after authorization)

1. One-at-a-time: each parameter varied to its neighborhood bounds with all
   others at canonical. Record pooled OOS expectancy @25bps per variant.
2. Cap: max ~40 one-at-a-time variants. No full grid search.
3. Report: full table of variant → expectancy delta vs canonical.
   Flag any variant where |Δ| > 0.05R as FRAGILE (sensitive).
   Flag any discontinuous sign flip at adjacent settings as CLIFF.
4. **No winner selection.** The canonical setting stays canonical regardless
   of the surface. The surface informs the PASS/FAIL "no parameter cliff"
   criterion in Phase C adjudication.

## 4. Combinatorial cap

If one-at-a-time shows no cliffs, STOP — no combinatorial runs.
If a cliff is found, at most 8 two-way combinations around the cliff
parameters to characterize it. Never to select a better setting.
