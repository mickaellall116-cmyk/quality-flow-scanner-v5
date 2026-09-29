# ANALYSIS.md — Execution / slippage sensitivity on the locked stack

Spec: EXECUTION_SPEC.md (frozen before runs). Engine: pine_stack's
`simulate_stack` reused verbatim; only execution assumptions vary.
Locked stack C1 = V3.6 signals/exits + rs_top2 ranking + E1 sector cap.
Fidelity: E0 C1 reproduces pine_stack C1@4bps exactly
(143 / 0.337R / 52.25% / 31.63%) — PASS. E2 C1 reproduces C1@25bps exactly
(0.28R / 39.64% / 33.79%) — consistent.

## Bull window scenario table (UX51 4H 2024-09-16→2026-09-14)

| Scenario | Case | Trades | Exp R | PF | Ret % | DD % | Calmar |
|---|---|---:|---:|---:|---:|---:|---:|
| E0 4bps | C0 | 160 | 0.239 | 1.35 | 35.30 | 35.17 | 1.00 |
| E0 4bps | **C1** | 143 | **0.337** | 1.49 | **52.25** | 31.63 | 1.65 |
| E1 10bps | C0 | 160 | 0.218 | 1.31 | 30.73 | 35.66 | 0.86 |
| E1 10bps | **C1** | 143 | **0.316** | 1.45 | **47.69** | 32.06 | 1.49 |
| E2 25bps | C0 | 160 | 0.165 | 1.23 | 19.92 | 37.16 | 0.54 |
| E2 25bps | **C1** | 142 | **0.280** | 1.39 | **39.64** | 33.79 | 1.17 |
| E3 50bps | C0 | 160 | 0.076 | 1.10 | 3.80 | 43.49 | 0.09 |
| E3 50bps | **C1** | 142 | **0.185** | 1.24 | **21.91** | 38.02 | 0.58 |
| E4 adv entry | C0 | 160 | 0.195 | 1.28 | 26.75 | 35.07 | 0.76 |
| E4 adv entry | **C1** | 142 | **0.306** | 1.46 | **45.68** | 31.06 | 1.47 |
| E6 100bps | C0 | 160 | −0.102 | 0.89 | −22.29 | 54.31 | −0.41 |
| E6 100bps | **C1** | 141 | **0.027** | 1.03 | **−3.22** | 46.12 | −0.07 |

E5 missed-10%-of-signals, C1, 20 seeded reps (bull):
expectancy median **0.306R** (p10 0.223 / p90 0.409) vs 0.337 full-signal;
return median **43.67%** (p10 28.38 / p90 65.60) vs 52.25%.

## 2022 window scenario table (37 trades; C0 = C1, gates never engage)

| Scenario | Exp R | PF | Ret % | DD % |
|---|---|---:|---:|---:|---:|
| E0 4bps | 0.376 | 1.47 | 11.21 | 21.28 |
| E1 10bps | 0.352 | 1.44 | 10.27 | 21.79 |
| E2 25bps | 0.293 | 1.35 | 7.95 | 23.07 |
| E3 50bps | 0.195 | 1.22 | 4.19 | 25.16 |
| E4 adv entry | 0.287 | 1.36 | 8.14 | 21.32 |
| E6 100bps | −0.002 | 1.00 | −3.00 | 29.19 |

E5 2022 (20 reps): expectancy median 0.417 (p10 0.122 / p90 0.547);
return median 12.0% (p10 2.52 / p90 15.98). Small-sample bands are wide;
no median penalty, but p10 shows real downside when a winner is skipped.

## The three key answers

### 1. Break-even friction (headline number): 107.6 bps — bull; 99.5 bps — 2022

Grid scan 0–150bps in 5bp steps, interpolated zero crossing, per case per
window. The locked stack absorbs **~108bps of total round-trip
friction** before expectancy hits zero — roughly 27× the 4bps modeled
cost, 4× the 25bps realistic-retail leg. Baseline C0 breaks even at
71.3bps. In the 2022 bear window the raw edge breaks even at ~100bps.

Verdict vs threshold: break-even ≫ 15bps → **not fragile**.

### 2. The stack's edge over baseline survives every cost leg

C1 beats C0 on expectancy, return, drawdown, and Calmar at 10/25/50/100bps
alike. At 100bps C1 is still expectancy-positive (+0.027R) while C0 is
deeply negative (−0.102R, −22%). The ranking + sector-cap complexity earns
its keep precisely when fills are bad — the overlays add the most value
under stress.

Vs threshold "survives realistic costs": at 25bps, bull expectancy 0.280R
(> 0.15 ✓), Calmar 1.17 (> 1.0 ✓), 2022 expectancy 0.293R (> 0 ✓).

### 3. Cherry-picking costs ~17bps-equivalent — material, but less than 25bps fees

Skipping 1-in-10 signals at random: median −0.031R expectancy (−9.2%) and
−8.58pp return vs taking everything. Return penalty > 5pp → **material**
per threshold. But it is NOT worse than transaction costs: the 25bps leg
costs −12.61pp return / −0.057R; the skip penalty sits between the 10bps
(−4.56pp) and 25bps legs, ≈ **17bps-equivalent**.

The MFE-study thesis is visible in the bands, not the median: p10
expectancy 0.223R vs p90 0.409R — when the randomly dropped 10% contains a
monster winner, it hurts a lot; when it contains losers, it helps. The
median cost is moderate; the *variance* cost is the real danger of
discretion. Note p90 (0.409R) exceeds full-signal (0.337R): random skipping
can luck into dropping losers — that is not a strategy.

E4 adverse-entry (+10bps on entry): expectancy −9.2% vs E0, far below the
40% fragility bar. Entry timing within 10bps does not threaten the edge.

## Discovered mechanism: costs feed back through the 5% risk gate

Taken-set drift (bull C1): 143 → 143 → 142 → 142 → 141 trades as costs go
4 → 10 → 25 → 50 → 100bps; 5%-gate skips 10 → 10 → 11 → 11 → 12. Higher
costs lower realized equity, which tightens the portfolio-risk gate via
lower marked equity — a small self-protective feedback (≤2 trades over the
whole range). This is why the taken set is near-invariant but not exactly;
the grid-scan break-even handles it honestly. No drift in 2022 (gate never
binds; 37/37 at every leg).

## Bottom line

- **Break-even: ~108bps bull / ~100bps 2022.** The edge is not fill-fragile.
- **Realistic 25bps costs:** 0.28R, +39.6%, Calmar 1.17 bull; +8.0% 2022.
  Comfortably survives.
- **Stack vs baseline:** C1 beats C0 at every cost leg, most decisively
  under stress (100bps: C1 +0.027R vs C0 −0.102R).
- **Skipping signals:** median cost ≈ 17bps-equivalent — material, less
  than 25bps fees, but with wide bands driven by monster-winner luck.
  Taking every signal remains the right behavior.
- No execution "improvements" proposed — none authorized, none needed.
  The approved research sequence is complete.

## Files

- EXECUTION_SPEC.md (pre-registered, incl. Mike's 100bps / headline
  break-even / headline cherry-picking scope addition)
- ANALYSIS.md (this file)
- execution_results.json (bull: cases, E5 reps, break-even grids, taken drift)
- execution_results_2022.json (2022 leg)
- pine_execution.py, pine_execution.log
