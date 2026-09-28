# Trend-Probe Tournament II — Preregistration (2026-09-28)

Research-only. Frozen/live Quality Flow remains unchanged.

## Purpose
Continue using moving-average families as diagnostic probes, not as automatic additions to QF. This second batch tests five distinct smoothing mechanisms that were not in Tournament I.

Candidates (all frozen at 20/40, no length search):
- **DEMA20/40** — double exponential moving average.
- **TEMA20/40** — triple exponential moving average.
- **ALMA20/40** — Arnaud Legoux MA, offset=0.85, sigma=6.
- **VIDYA20/40** — Chande VIDYA, alpha=2/(n+1)*abs(CMO_n), with CMO length equal to the line length.
- **FRAMA20/40** — fractal adaptive MA using the standard half-window fractal-dimension estimate, alpha=exp(-4.6*(D-1)) clipped to [0.01,1].

KAMA20/40 is carried only as the already-frozen benchmark; it is not retuned.

## Dataset / split
Same DST-safe 30-symbol 4H surrogate.
- 2024-2025 = discovery/descriptive.
- 2026 = untouched holdout for this batch.
- 2023 partial period excluded from discovery/holdout comparisons.
- 215-bar warmup required.

## Study A — standalone bullish crossovers
For each new candidate:
- bullish crossover = fast crosses above slow on a completed 4H bar;
- next-4H-open entry;
- forward stock and SPY-relative returns at 1/2/4/6/10/20 bars;
- 500 symbol/month-matched random non-event draws preserving event counts;
- report n, mean/median, hit rate, excess return and one-sided random-control p-values.

This is a 30-test family (5 indicators × 6 horizons). A lone p<0.05 is not treated as evidence; family-wise context must be reported.

## Study B — QF signal diagnostics
At each raw QF signal, using only the completed signal bar, record for each candidate:
1. bullish state: fast > slow;
2. normalized fast-slow gap: (fast-slow)/price.

Primary outcome: QF next-bar-open 10-bar SPY-relative return.

For bullish-state:
- compare bull vs bear in 2024-2025 and separately in 2026;
- report counts and mean/median excess;
- month-block bootstrap the bull-minus-bear difference.

For normalized gap:
- freeze discovery tertile cut points from 2024-2025;
- apply unchanged to 2026;
- report low/mid/high counts and mean/median excess;
- report high-minus-low direction.

## Interpretation
A candidate is only worth further work if:
- the relationship points the same way in 2024-2025 and 2026;
- 2026 is not supported by only a tiny number of observations;
- it adds information materially different from KAMA/EMA rather than reproducing the same state.

This tournament is exploratory screening on the same 30-name universe. Nothing advances to live use from this test alone.
