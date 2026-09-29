# MONTE CARLO / SEQUENCE-RISK STUDY — SPEC (pre-registered 2026-09-18)

## Purpose
Expectation-setting only. Quantify sequence risk for the Pine V3.6 baseline trade
distribution so Mike knows what to expect trading it live. NOTHING is optimized,
retuned, or changed. No parameters move. No rules move.

## Control / inputs
- Bull window: the 263 baseline trades (UX51, 4H, 2024-09-16→2026-09-14, 4bps leg),
  `net_r` per trade from `pine_trades_4h.json`. Verified: n=263, mean +0.195R.
- Bear window: regenerate 2022 baseline trades with the MFE/MAE study's
  `gen_trades_lifecycle` (byte-identical V3.6 entries/exits) on the 2022 4H cache
  (same cache/framework as the MFE/MAE and exit-fix studies). Expected ~30 trades
  on 25 symbols (vs 39 on 32 symbols in the entry-ablation 2022 run — symbol
  availability differs; framework is identical). Fidelity check: expectancy must
  land within ±0.05R of the published 2022 baseline (+0.287R). Reported SEPARATELY;
  regimes are never pooled.
- V5.4 forward test untouched. No existing files modified. Local only.

## Method
- Empirical resampling WITH replacement (no parametric fit).
- Bull: 10,000 simulated sequences × 263 trades. Bear: 10,000 × N_2022 trades.
- RNG: `numpy.random.default_rng(20260918)`. Documented for reproducibility.
- Trade order within each simulated sequence is the resampled order (i.i.d.).

## Accounting (two spaces, both reported)
1. **R-space (exact, accounting-free):** cumulative R, max drawdown in R
   (peak-to-trough of cumulative R), losing streaks (consecutive net_r < 0).
2. **Portfolio-space (documented model):** sequential 1%-risk compounding,
   equity_{k+1} = equity_k × (1 + 0.01 × r_k), $10k start. This is NOT the
   baseline's event-driven accounting (which has 5-position / 5%-risk caps and
   marked-equity DD). Verified mapping on the realized path: sequential model
   gives +52.0% terminal / 33.9% DD vs the baseline's reported +35.3% / 35.2%.
   The terminal gap is the concurrency-cap drag (87+17 skips in regeneration);
   drawdown is close under both accountings. All "realized vs simulated"
   comparisons are made WITHIN one accounting — never mixed.

## Metrics per simulation
- Terminal R; terminal portfolio %.
- Max drawdown: in R and in portfolio %.
- Longest losing streak: in trades, and its cumulative R.
- P(max DD_R > 10), P(max DD_R > 20).
- P(ruin): portfolio equity ever < 50% of start, at 1% risk.
- 12-month rolling expectancy: 263 trades ≈ 24 months → rolling 131-trade
  windows per sim; distribution of windowed expectancy (median, p10, p25).

## Key questions (answered in ANALYSIS.md)
(a) Expected drawdown: median / p75 / p95 of max DD (R and %) vs realized 35.2%.
(b) Worst plausible losing streak (p95/p99 of longest streak, in trades and R).
(c) Risk of ruin at 1% risk (ruin = −50% portfolio).
(d) Was the realized path lucky or typical? Percentile of realized terminal R
    (+51.3R) and realized R-space max DD within the simulated distributions,
    plus the same comparison in portfolio-space under the sequential model.

## Sensitivity (NOT optimization — informs the later sizing study, changes nothing)
Repeat headline portfolio metrics (median/p95 DD%, ruin P, median terminal %)
at 0.5% and 2% risk per trade.

## Limitations (stated in the report)
- Resampling assumes the future trade distribution resembles the past.
  Regime change breaks it — hence the separate 2022 leg, which is itself only
  one bear-market sample (n≈30).
- i.i.d. resampling ignores autocorrelation: real losing streaks cluster by
  regime, so simulated streaks may UNDERSTATE realized clustering.
- Portfolio-space uses the sequential model, not the capped event-driven book.
- 2022 leg is a small sample; its quantiles are noisy — report with that caveat.
