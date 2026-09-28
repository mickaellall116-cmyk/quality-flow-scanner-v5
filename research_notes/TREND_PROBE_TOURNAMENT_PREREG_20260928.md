# Trend-Probe Tournament — Preregistration (2026-09-28)

Research-only. Frozen/live Quality Flow remains unchanged.

## Goal
Use several trend estimators as **diagnostic probes** to learn what information, if any, distinguishes strong QF entries from weak ones. The goal is not to add an indicator simply because its chart looks good.

Indicators:
- EMA20/40 — simple control.
- HEMA20/40 — already studied.
- HMA20/40 — Hull moving average.
- KAMA20/40 — Kaufman adaptive moving average, ER length equal to the line length, fast=2, slow=30.
- ZLEMA20/40 — zero-lag EMA using lag floor((n-1)/2).

No length search, no parameter optimization, no alternate smoothing definitions after results are seen.

## Dataset
Same DST-safe 30-symbol recent-history 4H research set used in the HEMA work.
- 2024-2025 = discovery/descriptive period.
- 2026 = holdout check.
- 2023 is reported separately as a short partial period only.
This is not the canonical 131-symbol PIT validation.

## Study A — standalone bullish crossover timing
For each indicator, define bullish crossover = fast line crosses above slow line on a completed 4H bar.
- Enter at next 4H open.
- Measure stock return and SPY-relative return at 1, 2, 4, 6, 10 and 20 completed 4H bars.
- Compare to 500 symbol/month-matched random non-event draws preserving each indicator's event count by symbol/month.
- Report n, mean, median, hit rate, excess return, random percentile/p-value, yearly splits and symbol concentration.

## Study B — what QF looks like at the signal
For every raw QF event, record only information available on the completed QF signal bar for each indicator:
1. state: fast > slow;
2. fast-line 1-bar slope, normalized by price;
3. fast-slow gap, normalized by price;
4. one-bar change in the normalized gap (positive = separation/acceleration, negative = convergence);
5. price distance from the fast line, normalized by price.

Primary outcome: normal QF next-bar-open 10-bar SPY-relative return.
Secondary: 4-, 6-, and 20-bar excess return and 10-bar MAE/MFE.

For each continuous feature:
- split the 2024-2025 discovery sample into fixed tertiles;
- apply those exact discovery cut points to 2026;
- report QF count and mean/median 10-bar excess in each tertile;
- do not choose a 'winner' threshold after seeing 2026.

For each binary fast>slow state:
- compare bullish vs bearish QF events in discovery and holdout.

## Cross-indicator learning
Report:
- pairwise correlation of probe features at QF signals;
- whether adaptive/low-lag measures are largely redundant with EMA;
- which relationships are directionally consistent from discovery to 2026;
- whether any apparent effect depends on a few symbols or top events.

## Decision standard
A probe is informative only if the same directional relationship appears in 2026 and is not obviously driven by a tiny number of observations. This experiment produces hypotheses for later canonical validation; it does not change QF.
