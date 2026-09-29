# Lone-wolf CONFIRMATORY study (2026-09-25): structural effect or 20-day accident?

## Predeclared family (no optimization, no extra variants)
- **L15**: block when stockRS(15d)>0 and sectorRS(15d)<=0
- **L20**: block when stockRS(20d)>0 and sectorRS(20d)<=0 (original, predeclared)
- **L25**: block when stockRS(25d)>0 and sectorRS(25d)<=0
- **CONT_REL**: block when stockRS(20d)>0 and sectorRS(20d) < trailing-1y median
  of sectorRS(20d) at the signal date (point-in-time). One predeclared
  relative/continuous formulation of "sector not participating".

Main question: is "stock strength without sector participation" genuinely lower
quality? PASS required the directional effect to hold across the family,
not just at 20d.

## Method
Canonical 4H Hybrid entries, 14-stock watchlist, Oct 2023-Sep 2026, frozen Mode
B exits, portfolio sim with admission hook (faithful copy of
pb.simulate_portfolio, same pattern as pine_lonewolf_backtest). pine_backtest
imported unmodified. L20@25bps reproduces the original study exactly
(137 taken, +0.3797R vs +0.2721R control).

## Comparison table (25bps, taken-trade basis)

| Variant   | Taken | Exp R  | Delta  | Win% | PF   | DD%   | Blocked | Blocked exp |
|-----------|-------|--------|--------|------|------|-------|---------|-------------|
| CONTROL   | 180   | +0.272 |  --    | 50.6 | 1.43 | 21.63 | --      | --          |
| L15       | 136   | +0.292 | +0.020 | 51.5 | 1.48 | 16.03 | 72      | +0.172      |
| L20       | 137   | +0.380 | +0.108 | 54.0 | 1.65 | 18.86 | 74      | +0.064      |
| L25       | 135   | +0.256 | -0.016 | 51.1 | 1.41 | 15.98 | 77      | +0.262      |
| CONT_REL  | 133   | +0.369 | +0.097 | 52.6 | 1.64 | 18.12 | 82      | -0.005      |

## Year consistency (expectancy, 25bps)

| Variant   | 2024            | 2025            | 2026             |
|-----------|-----------------|-----------------|------------------|
| CONTROL   | +0.420 (n=59)   | +0.425 (n=68)   | -0.089 (n=53)    |
| L15       | +0.233 (n=46)   | +0.534 (n=56)   | -0.026 (n=34)    |
| L20       | +0.445 (n=49)   | +0.482 (n=56)   | +0.101 (n=32)    |
| L25       | +0.458 (n=49)   | +0.317 (n=54)   | -0.157 (n=32)    |
| CONT_REL  | +0.443 (n=48)   | +0.494 (n=52)   | +0.066 (n=33)    |

L20 and CONT_REL win in all 3 years. L15/L25 do not.

## Walk-forward (train entries <=2024 / test >=2025), 25bps

| Variant   | Train exp | Test (OOS) exp | OOS delta vs ctrl |
|-----------|-----------|----------------|-------------------|
| CONTROL   | +0.420 (59) | +0.200 (121) | --                |
| L15       | +0.233 (46) | +0.322 (90)  | +0.123            |
| L20       | +0.445 (49) | +0.344 (88)  | +0.144            |
| L25       | +0.458 (49) | +0.141 (86)  | -0.059            |
| CONT_REL  | +0.443 (48) | +0.328 (85)  | +0.128            |

## Cost sensitivity (delta exp vs control)

| Costs  | L15    | L20    | L25    | CONT_REL |
|--------|--------|--------|--------|----------|
| 25bps  | +0.020 | +0.108 | -0.016 | +0.097   |
| 50bps  | +0.024 | +0.106 | -0.025 | +0.097   |
| 100bps | +0.007 | +0.086 | -0.047 | +0.081   |

All formulations improve drawdown vs control at all costs (DD benefit is the
most family-stable property: L15 16.0-20.0%, L20 18.9-22.5%, L25 16.0-23.8%,
CONT_REL 18.1-21.3% vs control 21.6-30.7%).

## Symbol concentration
Blocked sets span 12 symbols for every formulation; no name >15 of ~75.
No concentration.

## Why it worked or failed
The family test confirmed the lookback sensitivity: across 10d/15d/20d/25d/40d
the deltas are -0.048 / +0.020 / +0.108 / -0.016 / -0.036 -- only the
predeclared 20d is meaningfully positive. The directional effect does NOT hold
across the lookback family. The lookback is load-bearing.

Against that, the CONT_REL check is a genuine (if partial) upgrade to the
story: the SAME 20d base with a different, relative sector cutoff (trailing
median instead of sign) reproduces the effect almost exactly (+0.097R vs
+0.108R, all 3 years, OOS +0.128R). This rules out "the sign cutoff is a
knife-edge". It does NOT rule out "the 20d lookback is the accident", because
CONT_REL still uses the 20d base -- the two formulations share the same
load-bearing parameter and their blocked sets overlap heavily.

Note also the mechanism check under CONT_REL passes in a way the original
didn't: blocked trades are genuinely dead money (-0.005R, and -0.19R at
100bps), vs +0.064R under the L20 sign cut. L15/L25 blocked clearly positive
trades (+0.17R / +0.26R) -- they blocked winners, which is why they fail.

## Verdict: MAYBE

The study did not promote the filter: the effect requires the 20-day lookback
-- 15d/25d/10d/40d do not replicate it, so the mandate's "survives nearby
parameter values" gate still fails and PASS is blocked. But it did not kill
it either: at the predeclared 20d the effect is unchanged in every strength
(out-of-sample delta LARGER than in-sample, wins all 3 years, broad symbols,
survives costs, improves drawdown), and a different cutoff formulation of the
same idea reproduces it with an even cleaner blocked bucket. This is a
20-day-window-specific effect, not proven generalizable -- the live paper
overlay remains the arbiter.

Recommended next experiment: none in the lab. The forward-test paper overlay
(`v54_lonewolf_overlay.py`, hourly) decides this at the ~50-signal checkpoint.

## Files
- `run_confirm.py` -- study script (pine_backtest imported unmodified)
- `confirm_results.json` -- all variants, costs, yearly, walk-forward, blocked analysis
- `README.md` -- this file

Guardrails respected: research only. V5.4, Mode B, production alerts, grades,
exits, market gate, AI Observer untouched; new files only in this folder.
