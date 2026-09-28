# Trend-Probe Tournament II — Result Note
**Date:** 2026-09-28
**Prereg:** `research_notes/TREND_PROBE_TOURNAMENT_II_PREREG_20260928.md` (frozen, unchanged)
**Status:** COMPLETE — all five candidates FAIL. Nothing promoted.

## What ran
- Branch: `research/hema-20260927`
- Script: `research_notes/trend_probe_tournament_ii.py`
- Dataset: same DST-safe 30-symbol 4H surrogate, 215-bar warmup, discovery 2024–2025, holdout 2026, 2023 excluded
- Candidates: DEMA / TEMA / ALMA(0.85, 6) / VIDYA / FRAMA, 20/40 only; KAMA frozen benchmark
- One mechanical crash-fix during the run: the month-block bootstrap hit an empty resample
  draw for a thin probe/period (VIDYA bearish, 2026, n=4) and raised ValueError. Guarded so
  degenerate draws are excluded as undefined (n_boot < 10000) instead of crashing.
  No prereg change — the specified bootstrap is unchanged; thin data now reports honestly.
- Raw outputs: `trend_probe_tournament_ii/` (results.json + 3 CSVs)

## Study A — standalone bullish crossovers, 10-bar SPY-relative vs 500 symbol/month-matched random draws

| Ind   | n    | actual ex10 | random mean | p(random ≥ actual) |
|-------|------|-------------|-------------|---------------------|
| DEMA  | 726  | +0.953%     | +1.454%     | 0.9321 |
| TEMA  | 915  | +0.676%     | +1.396%     | 0.9940 |
| ALMA  | 1042 | +0.716%     | +1.183%     | 0.9601 |
| VIDYA | 81   | +3.087%     | +5.301%     | 0.9521 |
| FRAMA | 1318 | +0.873%     | +1.474%     | 0.9940 |
| KAMA  | 448  | +1.030%     | +2.311%     | 0.9980 |

No candidate beats matched random at the 10-bar horizon. Same verdict as Tournament I.

## Study B — bullish state at raw QF signals (n=235), 10-bar SPY-relative

| Ind   | Discovery bull/bear (n, mean) | diff | 2026 bull/bear (n, mean) | diff | Same direction? |
|-------|-------------------------------|------|--------------------------|------|-----------------|
| DEMA  | 65/+0.63% vs 106/+2.63% | −1.999pp | 25/+0.29% vs 39/+2.40% | −2.105pp | yes, but bearish state better — wrong way |
| TEMA  | 22/+2.31% vs 149/+1.80% | +0.513pp | 10/−5.24% vs 54/+2.84% | −8.075pp | NO — flips sign |
| ALMA  | 74/+3.71% vs 97/+0.46%  | +3.251pp | 28/−0.49% vs 36/+3.18% | −3.664pp | NO — flips sign |
| VIDYA | 156/+1.80% vs 15/+2.53% | −0.724pp | 60/+1.39% vs 4/+4.32%  | −2.926pp | yes, but bearish better — wrong way |
| FRAMA | 118/+0.65% vs 53/+4.58% | −3.927pp | 49/+2.49% vs 15/−1.43% | +3.917pp | NO — flips sign |
| KAMA* | 137/+2.48% vs 34/−0.60% | +3.077pp | 50/+2.83% vs 14/−2.91% | +5.741pp | yes (benchmark) |

Month-block bootstrap (10k reps): no candidate's bull-minus-bear CI excludes zero in a
promotable direction. FRAMA discovery and TEMA 2026 CIs exclude zero but in the
bearish-is-better direction — not promotable, treated as chance-like.
KAMA benchmark reproduces Tournament I's directional pattern in both periods, but its
bootstrap CI also includes zero here — the "promising, unproven" read is unchanged.

## Study B — normalized gap tertiles (discovery cuts frozen → 2026), high-minus-low

| Ind   | Discovery | 2026 | Same direction? |
|-------|-----------|------|-----------------|
| DEMA  | −0.933pp | −3.098pp | yes, wrong way |
| TEMA  | −3.291pp | −7.587pp | yes, wrong way |
| ALMA  | +2.924pp | −4.420pp | NO |
| VIDYA | +2.168pp | −3.506pp | NO |
| FRAMA | −4.601pp | +5.845pp | NO |
| KAMA* | +2.648pp | +6.169pp | yes (benchmark) |

## Verdict
**FAIL for all five candidates.** No candidate meets the promotion standard (same
direction in discovery and 2026, non-tiny 2026 N, distinct from KAMA/EMA). Nothing from
this tournament goes live, nothing is tuned, nothing changes in frozen V5.4 or the KAMA
shadow. The established-trend-plus-compression read from Tournament I (KAMA bullish
state) remains the only directionally consistent signal, still unproven.

## Negative-result preservation
DEMA, TEMA, ALMA, VIDYA, FRAMA standalone crossovers and state/gap diagnostics are
closed on this dataset. Do not re-run on the same 30-symbol surrogate with tweaked
parameters — per the handoff, a second attempt needs genuinely new/held-out data.
