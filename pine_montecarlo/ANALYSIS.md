# Monte Carlo / Sequence-Risk Study — ANALYSIS (2026-09-18)

Expectation-setting only. 10,000 resampled sequences (seed 20260918), empirical
R-multiples with replacement, no parametric fit, nothing optimized.
Bull leg: 263 trades (UX51 4H 2024-09-16→2026-09-14, 4bps). Bear leg: 39 trades
(2022 4H, 32 symbols — exact reproduction of the published 2022 baseline:
n=39, +0.287R). Regimes never pooled.

## Headline numbers — bull window

| Metric | Median | p75 | p95 | Realized path |
|---|---|---|---|---|
| Terminal R | 48.7R | 81.2R | 131.1R | 51.3R (52nd pct — typical) |
| Max drawdown (R) | 26.1R | 33.9R | 51.1R | 40.8R (87th pct — unlucky ride) |
| Longest losing streak | 8 trades | 10 | 12 | 8 (exactly median) |
| Worst streak (R) | −10.4R | −8.6R | −6.5R | — |
| P(drawdown > 10R) | 99.9% | — | — | — |
| P(drawdown > 20R) | 75.6% | — | — | — |

Portfolio-space (sequential 1%-risk compounding — documented model, see spec):

| Risk/trade | Median terminal | Median max DD | p95 max DD | P(ruin, −50%) |
|---|---|---|---|---|
| 0.5% | +24.8% | 12.4% | 23.0% | 0% |
| 1% | +49.2% | 23.7% | 41.2% | 0.35% |
| 2% | +91.1% | 42.8% | 67.1% | **10.9%** |

12-month rolling expectancy (131-trade windows): median +0.17R, p25 +0.02R,
p10 −0.10R. Roughly one year in four is flat-or-negative.

## The four key answers

**(a) What drawdown should Mike expect?** Median ~24% at 1% risk; plan for ~30%
(p75); the bad tail (1-in-20) reaches ~41%. In R terms a 10R+ drawdown is
essentially certain (99.9%) and a 20R+ drawdown happens three times out of four.
The realized 35.2% was an 85th-percentile drawdown — worse than the typical ride.

**(b) Worst plausible losing streak?** Median 8 consecutive losers (the realized
path had exactly 8). Expect 10–12 in a rough sequence (p75–p95); 15 is the
1-in-100 case. The typical worst streak costs about −10R.

**(c) Risk of ruin at 1%?** 0.35% — negligible. This is the strongest argument in
the whole program for keeping size at 1%: the edge survives. At 2% risk, ruin
jumps to 10.9% (about 1 in 9) with a median drawdown of 43% — that is a
different game and not one the backtest supports.

**(d) Was the realized path lucky or typical?** The OUTCOME was typical:
terminal 51.3R sits at the 52nd percentile — a coin flip. The RIDE was unlucky:
max drawdown at the 85–87th percentile. Net: the +35.3% headline does not
overstate the median outcome, but anyone anchoring on the realized smoothness
is anchoring on a worse-than-typical drawdown path. The median simulated path
makes ~+49% with a ~24% drawdown.

## Bear-window leg (2022, reported separately)

Median terminal 9.4R (+8.2% at 1% risk); median max DD 12.1R (11.6%);
p95 DD 21.7%; ruin 0%. Realized 2022: terminal at the 55th percentile (typical),
drawdown at the 91st (unlucky ride again — same pattern as the bull window).
Two-thirds of bear-year sequences see a 10R+ drawdown. n=39 makes these
quantiles noisy — treat as directional.

## What this means for the sequence

- The sizing study (next) has its key input: 1% risk → ~0.3% ruin, ~24%
  median DD; 2% risk → ~11% ruin, ~43% median DD. Size is the dominant
  determinant of survival, not entries or exits.
- Expectation to carry into live trading: ~8-trade losing streaks are normal,
  ~1-in-4 years is flat-or-down, and a 30%+ drawdown should be treated as
  "within the plan," not as evidence the edge broke.
- The realized backtest was an honest outcome on a rough ride. Do not expect
  the future to draw down less than the median 24% — expect the median, plan
  for the p75.

## Limitations
Resampling assumes the future trade distribution resembles the past; regime
change breaks it. i.i.d. draws ignore autocorrelation, so real streaks may
cluster harder than simulated ones. Portfolio-space uses the sequential
compounding model, not the baseline's capped event-driven book (the realized
+35.3% vs the model's +52.0% on the same trades is the documented
concurrency-cap drag). The 2022 leg is one small bear sample.
