# QuantFinanceToGo — full methods inventory and applicability review (2026-10-18)

Source: Instagram @quantfinancetogo ("Quantitative Finance from A to Z", creator account, DE,
~30.1K followers, 34 posts). Mike sent the Part 22 reel 2026-10-18 and directed: check out ALL
their methods, then work with ChatGPT on whether it can help us. Inventory built from the full
caption text of every post (the captions carry the complete lesson text). Every number in the
series is SIMULATED with assumed parameters — the account says so in every caption. It teaches
methods; it claims no live edge and sells no signals in this content.

## The series: "Quantitative Finance From Scratch", Parts 1–27

Foundations (Season 1, Parts 1–12, one continuous story about a bet with an edge):
1. Edge & expected value — law of large numbers; edge grows linearly, luck with sqrt(n); ~1,400 bets for a 2.7-cent edge to exceed 1 SD of luck.
2. Random walk & drift — eyes find patterns in pure chance; drift vs sqrt-spread crossover.
3. Square root rule — spread grows with sqrt(time); basis of vol annualization and t-stat scaling.
4. Bell curve / CLT — 68/95/99.7.
5. Measuring returns — percent moves multiply; log returns add.
6. Present value / discounting.
7. Risk & volatility — SD of returns; loss-year frequency at equal mean return.
8. Sharpe ratio — excess return per unit vol; invariant to cash mixing.
9. Volatility drag — growth ≈ mean − vol²/2; 5x the swing = 25x the drag.
10. Correlation — shared hidden factor stretches the cloud; correlation is not causation.
11. Diversification — portfolio vol floor = s·sqrt(c); idiosyncratic risk averages out, factor risk stays.
12. Season 1 recap.

Risk & portfolio (Parts 13–19):
13. Efficient frontier — 5,000 random mixes; min-var portfolio; dominated assets sit below the edge.
14. Market beta — Cov/Var; slope of the return cloud.
15. CAPM — expected return linear in beta; single-factor, debated.
16. Position sizing & Kelly — 55% even-money game: median outcome peaks at the Kelly 10%; 20% sizing ruins 25% of players >99%; overestimating your edge = overbetting.
17. Monte Carlo — 10,000 paths; median vs mean (drag); precision improves with sqrt(runs).
18. Fat tails — Student-t(3) vs normal at equal vol: >5% days 74 vs 0 per 100y; Black Monday is ~1-in-216y under fat tails, ~never under normal.
19. VaR — 99% 1-day VaR understates the tail: beyond the line the average loss was 4.2%, worst 21.5% (expected-shortfall point, made without the name).

Validation & factors (Parts 20–27):
20. Backtesting — in/out-of-sample split; 498 no-edge rules: best in-sample +11% → −28% out-of-sample, rank 460/498; top-10 in-sample average −18.5% OOS. Data mining named plainly.
21. Linear regression — beta/alpha/R²; estimation error over 2y of data (true beta 1.2 recovered as 1.26, within chance).
22. Hypothesis testing — t ≈ Sharpe·sqrt(years); a TRUE Sharpe-1 edge over 5y still gives t=1.50, p=13.3%, CI includes zero; test 100 no-edge rules, ~5 pass at 5% (7 did); p is not P(strategy works); independence/stationarity assumptions; costs can kill a real-but-small edge.
23. Mean reversion — half-life model; test = regress change on distance; TRAP: 34% of pure random walks pass the naive −2 t-limit, so use the Dickey-Fuller limit ≈ −2.9/−3.
24. Momentum — classic 12-minus-1-month; long-short sim: 5.9%/yr, t=6.00, beta −0.01; long-only 13.7% but beta 0.99 (mostly market).
25. Value factor — book-to-market long-short; sim premium 4.7%/yr, t=4.29; value/momentum near-uncorrelated, mix is smoother.
26. Size factor — SMB; sim premium ON: 3.0%/yr, t=2.21; switched OFF post-"publication": −0.2%, t=−0.11; real-world note: the effect weakened after publication.
27. Fama-French 3-factor — market+SMB+HML regression; small-value alpha 7.9%/yr under market-only → −0.9% with all three factors; R² 46% → 90%. Alpha = what factors cannot explain.

Standalone reels (not numbered):
- Portfolio optimization (Markowitz random portfolios, 3,000 mixes of 7 assets).
- "2 million backtests" landscape — expected Sharpe of a mean-reversion strategy across its parameter grid (a data-mining / parameter-mining visual).
- Pairs spread ("rubber band") — two stocks sharing a common trend; trade the spread.
- Geometric Brownian motion visualization.
- Kalman filter — price = truth + noise; state estimation separating the two.
- Correlated assets / Markov visualization.
- FF3 trading-challenge throwback post.
- "Ask chart gurus for proper evidence" — anti-guru post; chart trading called out.

## Applicability to our program (Muse first pass — for ChatGPT adjudication)

Our binding constraints (standing): (a) no qualified PIT-clean historical dataset yet (TD screen
is vendor qualification for a 20-symbol subset; 51-symbol baseline separately authorized, data
still the blocker); (b) validation statistics are informal — frozen economic bars, no formal
t-stats/CIs, no multiple-testing correction; (c) the V5.4 forward test is the arbiter, ~50-signal
interim / ~100-signal verdict; (d) research sequence already fixed: MFE/MAE diagnostic at the
~50-signal checkpoint, then Monte Carlo, sizing, exposure/correlation, execution.

DIRECTLY APPLICABLE (methods, not strategies):
- A1 (Part 22): a formal inference layer for forward-test readouts — precomputed t-stat / CI on
  per-trade R at n=50 and n=100, frozen BEFORE the readouts, so "edge vs luck" is answered with
  the reel's own arithmetic (t grows with sqrt(n); at our observed R dispersion, small true edges
  will NOT reach t=2 at n=50 — the interim readout must be framed as such in advance).
- A2 (Part 20): their 498-rule demo is the canonical statement of our existing data-mining
  discipline (preregistration, frozen bars, sealed holdout, killed-idea registry). No change —
  external confirmation of current practice.
- A3 (Part 23): IF any mean-reversion/spread idea is ever tested (Daily Sweep backlog family,
  pairs standalone), the Dickey-Fuller −2.9 threshold and the 34%-false-pass rate are the correct
  test bar — the naive −2 limit is a known trap. Also applies to the liquidation/sweep family if
  it is ever unsealed.
- A4 (Parts 21/24/27): factor attribution at forward-test verdict time — regress pooled forward
  returns on market (and, if data allows, size/value/momentum proxies) to answer "is the pooled
  result just beta?" Part 24's long-only warning (13.7% at beta 0.99) is precisely our pooled
  long-only book's confound. Needs a benchmark series — SPY identity is PROSE_ONLY in our
  contract (field 1.2) and benchmark loader bytes were recovered in -22/-23, so this is feasible
  once a qualified SPY series exists; it is NOT feasible on current data.
- A5 (Parts 17/16): Monte Carlo and Kelly are already in our sequence (Monte Carlo after
  MFE/MAE; sizing review after that). Their treatments match standard practice; useful as
  method references when those stages are preregistered. Our live sizing is fixed-fractional
  1% — Kelly's overbetting warning supports keeping it fractional and below full Kelly.
- A6 (Parts 18/19): the weekly portfolio stress check uses fixed −20%/−30% shocks. A fat-tail
  framing (Part 18) and an "average loss beyond the line" (Part 19) would make the stress
  snapshot more honest without changing any position rule. Cosmetic-to-modest value.

NOT APPLICABLE / NO ACTION:
- Parts 1–15, 25, 26: foundations and factor-premium surveys. Correct, standard, honestly
  caveated (publication decay in Part 26 is a genuinely good caveat) — but they propose no test
  we can run and no data we lack less after watching. The size/value premiums are daily/annual
  factor phenomena, not our 4H signal family.
- Kalman standalone: state estimation is not on our roadmap; our bottleneck is data and
  validation, not filtering.
- GBM/Markov/correlation visuals: illustrations of Parts 3/10 content.

VERDICT (Muse, for ChatGPT to adjudicate): no edge, no data, no new strategy — and the account
does not pretend otherwise, which puts it above most of the reel intake. Its real value to us is
a short statistical checklist that names gaps we already carry: A1 (formal inference for the
forward test — the one gap Mike has now asked about twice) and A3 (the DF bar, parked with the
MR family), with A4 as a verdict-time attribution once a qualified benchmark series exists.
Recommend: adopt A1 as a preregistration drafting task for ChatGPT review; park A3/A4 with
their lanes; no tests on this content itself.

Intake path: Mike's reel + directive 2026-10-18. Status: posted to Slack + bridge for ChatGPT
adjudication; nothing tested; no data called.
