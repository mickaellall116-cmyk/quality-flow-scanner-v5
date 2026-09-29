# Multiple-testing audit — Quality Flow scanner research

Audit date: 2026-09-24. Auditor scope: hypothesis-count honesty + practical
adjustment of the three candidates' headline statistics.

## 1. How many "looks" did we really take?

Counted as one "look" = one headline expectancy-delta (or equivalent
PASS/MAYBE/FAIL) comparison computed on the same 4H backtest trade population
(14-stock watchlist, Oct 2023–Sep 2026, ~237 baseline trades).

### Exploration phase (Sep 24–25 night) — 15 priorities
| Priority | Idea | ~Looks |
|---|---|---|
| P1 FVG validation | FVG-as-entry canonical + P1/P2/P3 perturbations + matched-trade attribution + walk-forward + year/regime/symbol cuts + cost stress + robustness study | ~8 |
| P2 ranking | take-all vs rs_top2 vs ADX vs rs_spy vs RS+ADX, per-contest, crowded-only, perturbation, confirmation addendum | ~7 |
| P3 correlation | CORR_07 (+variants), max-2-per-theme, theme concentration | ~3 |
| P4 regimes | year x regime grid (diagnostic) | ~2 |
| P5 volatility | ATR/price quartiles, realized-vol terciles, ATR percentile, breakout/ATR, dead-market follow-up | ~5 |
| P6 chase | extension quartiles + overlap thread | ~2 |
| P7 setup age | age-curve buckets, confirmed/ready overlap | ~3 |
| P8 volume | RVOL, expansion quartiles, dollar-volume terciles | ~3 |
| P9 gaps | gap-up buckets, gap-down buckets | ~2 |
| P10 sector-RS (lone-wolf) | 15/20/25d x sign/rel = 6 formulations, Mike TEST1 checks A–H, dev/val split | ~8 |
| P11 breadth | crowded-bar buckets | ~2 |
| P12 heat | heat levels | ~2 |
| P13 sequencing | order buckets, re-entry, overlap | ~3 |
| P14 time | calendar buckets, post-earnings thread | ~3 |
| P15 exits | diagnostics only, no filter | 0 |
| **Exploration subtotal** | | **~55** |

### Confirmatory phase (separate studies, same data)
| Study | ~New looks |
|---|---|
| lone-wolf: run_lonewolf + lonewolf_confirm + protocol (formulation SELECTION among 6 + validation) | ~3 |
| FVG: robustness + protocol + attribution | ~3 |
| ADX: protocol + addendum + selection-edge TEST3 + ranking confirm | ~4 |
| **Confirmatory subtotal** | **~10** |

### Auxiliary study folders measuring expectancy deltas on 4H data
1H, 2H/3H, 3H+FVG stack, pullback, staleFVG, mean-reversion, breakout-retest
(reel), trend filter, entry timing, entry ablation, v11, v17, expansion/universe,
execution, sizing, signal quality, mfe_mae, montecarlo, exit ablation/fix,
exposure, sensitivity, stack ≈ **~25** looks.

### Totals
- **Raw looks: ~85–90** headline comparisons on effectively the same trade data.
- **Effective independent tests: ~20–30.** Variants inside one study family
  share the same 237 trades and near-identical rules (e.g. 15/20/25d lookbacks
  are ~0.9+ correlated), so each study family contributes roughly 1–2
  effective tests for its best-variant headline. Distinct edge-claim families:
  15 priorities + ~10 auxiliary edge ideas ≈ 20–30.

The pre-registered protocols protect the *procedure inside each study*; they do
not protect against *selecting the 3 winners out of ~85 looks*. That is the
multiplicity that matters.

## 2. Naive (unadjusted) one-sided p-values from the studies' own bootstraps

| Candidate | Headline stat | Bootstrap source | Naive p |
|---|---|---|---|
| lone-wolf | P(Δ>0) = 0.9442 (10k draws) | pine_lonewolf_protocol/protocol_results.json bootstrap_primary | **0.0558** |
| ADX (selection edge) | frac>0 = 0.9508 (5k draws) | pine_adx_protocol/adx_selection_edge.json | **0.0492** |
| ADX (vs take-all, protocol) | frac>0 = 0.8786 (5k draws) | pine_adx_protocol/adx_protocol_results.json bootstrap | **0.1214** |
| FVG | frac ΔE>0 = 0.5931 (10k draws) | pine_fvg_protocol/fvg_protocol_results.json step9_bootstrap | **0.4069** |

Note: 0.0558 and 0.0492 are already on the wrong side of 0.05-before-adjustment
for any honest interpretation; they are "~1.5σ" results, not discoveries.

## 3. Practical adjustment — Holm/Bonferroni over the effective family

adjusted_p = min(1, naive_p × m), shown for plausible effective-family sizes:

| Candidate | naive p | m=15 | m=25 | m=40 |
|---|---|---|---|---|
| lone-wolf | 0.0558 | 0.84 | 1.00 | 1.00 |
| ADX (selection edge) | 0.0492 | 0.74 | 1.00 | 1.00 |
| ADX (vs take-all) | 0.1214 | 1.00 | 1.00 | 1.00 |
| FVG | 0.4069 | 1.00 | 1.00 | 1.00 |

FDR framing (Benjamini–Hochberg, family = the 3 candidates, q=0.05):
sorted p = 0.0492 (crit 0.0167 — fail), 0.0558 (crit 0.0333 — fail),
0.4069 (crit 0.05 — fail). **None pass even the most generous family.**
With the honest family (m≥15), BH critical value for the best candidate is
0.05/15 = 0.0033 — the best naive p (0.0492) misses it by ~15x.

## 4. Plain-English answer

**Could the strongest findings be false positives from repeated testing? Yes —
comfortably.** We took roughly 85–90 looks at the same 237-trade dataset
(~20–30 effective independent tests after correlation discount). The two
"passes" are ~1.5σ effects (naive p ≈ 0.05) that sit exactly where you'd expect
the luckiest draws of an 85-look fishing expedition to sit. After any honest
multiplicity correction (Holm/Bonferroni at m≥15, or FDR), adjusted p-values
are 0.74–1.00: **nothing survives.**

This does not upgrade/downgrade the mandate's MAYBE verdicts — it explains them.
The studies' pre-registration was real and valuable (it killed FVG and the
3H+FVG stack honestly), but pre-registration inside each study cannot buy back
the selection step across ~85 studies. The only thing that can resolve
lone-wolf and ADX now is untouched forward data — exactly what the mandate's
live arbiters (lone-wolf overlay, FVG sidecar, ADX shadow at the ~50-signal
checkpoint) are for.
