# CANDIDATES_FROZEN.md — Exposure study

**Frozen 2026-09-18, BEFORE touching 2022. No refit on 2022.**

## Research-window results @4bps (control = take-all V0)

| Variant | Trades | Exp R | PF | Ret % | DD % | Calmar | Gate skip |
|---|---|---:|---:|---:|---:|---:|---:|
| V0 control | 160 | 0.239 | 1.35 | 35.30 | 35.17 | 1.004 | 0 |
| E1 sector2 | 143 | 0.299 | 1.44 | 42.29 | 29.68 | 1.425 | 20 |
| E2 mega3 | 162 | 0.212 | 1.31 | 30.32 | 33.84 | 0.896 | 3 |
| E3 corr70 | 146 | 0.281 | 1.41 | 40.29 | 31.30 | 1.287 | 32 |
| E4 cap3 | 111 | 0.437 | 1.65 | 50.79 | 32.51 | 1.562 | 0 |

Note on the expectancy bar: the spec pre-registered "≥80% of control (≥0.156R)"
from the documented candidate-level 0.195R. The simulator's taken-trade control
expectancy is 0.239R (the 0.195R figure averages over all 263 candidates,
including 103 skipped by cap/risk). 80% of the taken-trade figure is 0.191R.
E1 passes under either interpretation (0.299R).

## Gate-by-gate vs the pre-registered bar (DD cut ≥5pp AND exp ≥80% AND n≥50)

- **E1 sector2 (max 2 concurrent per sector): DD 29.68% vs 35.17% = −5.49pp ✓;
  exp 0.299R ✓; n=143 ✓ → FROZEN as C1.**
- E2 mega3 (max 3 in MEGA_AI): DD cut only 1.33pp ✗ → rejected. (Gate bound
  just 3 times — MEGA_AI rarely had 3 concurrent.)
- E3 corr70 (skip if 60d-corr > 0.7 with any open): DD cut 3.87pp ✗ → rejected.
  (32 gate skips; helped expectancy +0.04R but not enough DD cut.)
- E4 cap3 (max 3 positions): DD cut only 2.66pp ✗ → rejected, despite the best
  expectancy (0.437R) and return (50.79%). Notably the DD cut is small because
  the baseline's max DD was a low-concurrency grind (see diagnostics), not a
  crowded-portfolio event.

## Frozen candidate

**C1 = E1_sector2**: at each entry event (after same-timestamp exits), skip the
candidate if ≥2 positions in its sector (per the EXPOSURE_SPEC.md map) are
already open. All other portfolio rules unchanged (max 5 positions, 5% risk).

Caution carried into 2022: at 25bps the DD cut shrinks to 1.7pp
(35.46% vs 37.16%), so the DD benefit is cost-sensitive.

## 2022 adoption bar (pre-registered)
Expectancy ≥ (2022 control − 0.05R) AND max DD ≤ (2022 control + 3pp).
2022 control reference (ranking study): 37 trades, +0.376R, DD 20.42% @4bps.
