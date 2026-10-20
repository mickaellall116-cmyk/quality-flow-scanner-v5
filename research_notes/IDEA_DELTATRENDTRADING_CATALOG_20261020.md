# @deltatrendtrading (Thomas Skinner) — catalog inventory and applicability review (2026-10-20)

Source: Instagram @deltatrendtrading (Thomas Skinner; Columbia finance/physics educator;
founder of QuantPad, an AI IDE with integrated market data — his content doubles as product
marketing). Account stated at 386 posts, 117,646 followers (search-index blocks say ~130K
followers; the index is stale, the brief's figure governs). Mike sent the vol-forecast reel
2026-10-20, then the profile, and directed: check out ALL his videos. One reel was intaken
separately the same day (vol-forecast stop sizing, `IDEA_VOL_FORECAST_STOPS_REEL_20261020.md`);
it appears below as entry M1 and is cross-referenced, not re-adjudicated.

## COVERAGE — read this first (the catalog is a broad sample, NOT a full enumeration)

- The canonical pull (instagram-cli `posts`, full pagination) was attempted first and hit
  **HTTP 429 on page 1**. Per the hard rate rule, ALL instagram-cli calls stopped immediately:
  0 of 386 posts retrieved through the posts command, and no fresh media-understanding was run.
- Fallback used: the social search index (not instagram-cli), six facet sweeps (methods,
  options/backtest/sizing/prop, microstructure/ML/psychology, mean-reversion/crypto/futures,
  platform/pairs/ML, personal/community). Yield: **145 unique posts, all verified authored by
  @deltatrendtrading, dated 2024-11-05 → 2026-10-20** — 145 of 386 stated posts (~38%),
  spanning the account's full visible date range. Search ranking is relevance-based, so the
  sample over-weights substantive/popular posts and under-weights minor ones; the missing
  ~241 posts are UNSEEN, and this note does not claim otherwise.
- Content evidence per sampled post = the search index's stored media summary (a
  media-understanding-grade narrative), NOT verbatim captions — unlike the QuantFinanceToGo
  inventory, whose captions carried the full lesson text. 142 of 145 sampled posts carry a
  substantive summary; 3 (2025-11-26, 2025-12-31 ×1, 2026-02-25 ×1) have none and are
  uncharacterized. Media-understanding coverage: the 1 separately-intaken reel (full MU on
  file from its own intake) + index summaries for 142 posts; fresh instagram-cli MU: 0
  (rate-blocked).
- Every number below is the CREATOR'S claim from his own posts, produced on his own data
  inside his own product. Claims, never evidence — per standing rule.

## Cluster map (145 sampled posts, each counted once)

| Cluster | n | What it is |
|---|---|---|
| Coded strategy tests & guru audits | 24 | He codes a named influencer/plainly-specified strategy and publishes the backtest, usually with costs and confidence intervals |
| Options theory, Greeks, implied distributions | 20 | Delta/gamma/theta explainers, implied PDFs, SKEW, vol surfaces, Fed-implied probabilities |
| Feature engineering / ML / regime methods | 19 | Features-as-model-inputs doctrine, regime metric suite, Markov chains, trade-log enrichment, OFI and tape-speed studies |
| Validation statistics & testing doctrine | 14 | Backtest-as-filter, CIs/bootstrap/Monte Carlo, sample-size warnings, probability course |
| Critique & commentary | 14 | Anti-guru/ICT critiques, alpha-decay commentary, industry rants, one single-stock (AEO) analysis |
| Prop-firm math & challenge EV | 13 | Challenge-as-structured-product Monte Carlo, risk geometry, his own Topstep pass series |
| QuantPad product | 9 | Launch/feature demos, vs-ChatGPT Pine comparison, data-API promotion |
| Strategy construction & philosophy | 8 | Build-your-own doctrine, strategy-decay responses, Kelly explainer, beginner onboarding |
| Personal / lifestyle / other | 8 | College-admissions advice, his MMA-shorts business, desk setup, personal story, life-EV monologue |
| Volatility forecasting | 7 | GARCH/clustering explainers and the range-forecast model family (incl. M1) |
| Market mechanics & microstructure | 6 | What moves markets, volume vs liquidity, HFT, bid-ask/market making, broker conflicts/PFOF |
| Uncharacterized (no index summary) | 3 | Counted, not classifiable from available evidence |

## Distinct methods / claims (his numbers, as posted)

**M1. Volatility forecasting → range & stop sizing** (2026-10-20, Des85-5O8hJ; separately
intaken — see `IDEA_VOL_FORECAST_STOPS_REEL_20261020.md`). NQ daily range: return persistence
≈ −0.105 vs volatility persistence ≈ 0.76; combined model (lag + week + month + VIX) range
error 62.7 pts < options-implied 67.3 < naive 83.2; application = size stops off the forecast
range. Family posts: GARCH explainer ("forecast vol like a market maker", yesterday's vol
carries 80–90% weight), IV-vs-realized explainer, "predict good price action days" via vol
autocorrelation + a vol screener, variance-forecasting theory (variance matters only for
convex payoffs). Accuracy claim, no return claim.

**M2. ICT Fair Value Gaps, cost-tested** (2026-06-02). 5 years of NQ data; round-trip cost
2.5 ticks ($12.50). Most proximal FVG taps are eaten by costs (~1.96–3.19 ticks); only the
9:30 ET hour breaks even. Entry location decides at pessimistic 4-tick costs: proximal edge
−0.069R vs displacement-candle-open entry +0.130R (a +0.199R swing); 99% of gaps fill quickly;
tapping ≈ random before costs.

**M3. ICT order blocks, grid-tested** (2026-02-14, 2 posts). Coded in TradingView + Python;
grid over zone construction × entry reference × imbalance filter, double-barrier (ATR)
outcomes, 20-bar forward returns. Only 2 parameter sets reached statistically significant
positive mean returns — both "last opposite candle" zones, entry at block open, NO imbalance
requirement.

**M4. ICT iFVG matched-control test** (2026-07-10). Inverted FVGs on 5-min NQ vs a baseline
matched on volatility, trend, and time-of-day: positive mean forward returns but confidence
intervals overlap zero — his verdict: "no detectable edge" before confluences.

**M5. SMT divergence audit** (2026-03-11). "Smart Money Technique" divergence = correlation
mistaken for cointegration; his test: alpha −0.0028% (annualized −0.71%), null not rejected.

**M6. rp.profits 8 AM ORB audit** (2026-02-25, 3 posts incl. series intro). ES futures,
2020-01-01 → 2026-02-25, 415 trades: 16% profitable, profit factor 0.87, −$11,624 (−41.23%),
max drawdown −59.96%. Topstep 50K Monte Carlo: 12.05% pass, 0% payout probability. His
verdict: "nothing special," implemented as described.

**M7. ORB + machine learning** (2025-07-03, 2025-07-26). Random-forest ORB (features: range
size, relative volume, time of day): beat S&P 500 buy-and-hold over 1 year, NO edge
2000–present, Sharpe ≈ 0.7. Viewer-request 5-year ORB: raw <10% vs buy-and-hold ~100%;
adding ML entry filters + ATR stops/targets → 32%, still trailing buy-and-hold.

**M8. Powell Trades audit** (2026-04-30, 2 posts). ICT-style day system coded from the
seller's videos (+ his own regime filter): NO statistically positive per-trade edge. Prop
framing (TopStep $150K combine MC): 22.24% pass, 54% timeout, mean payout $1,204, net EV
+$221 per account.

**M9. Zahloria volume-profile reconstruction** (2026-02-03). Session volume profile smoothed
by spline; peaks/troughs → S/R levels; ~12 tuned parameters (incl. ATR breakout conviction);
Micro NQ. Claims a 4×-the-S&P-500 return in a 1-year OUT-OF-SAMPLE backtest — at a 0.15
Sharpe. Apex challenge MC: 34.5% pass, ~$2,300 expected payout, ~+$800 net EV after fees.

**M10. TJR daily-bias state model** (2025-10-20; related 2025-07-31, 2026-05-14). His coded
reproduction of TJR's daily-bias workflow: 71.4% accuracy on ES state-transition predictions
over 227 sessions, dropping to 49.3% on the "manipulation + reversal" subset (he notes
sub-50% accuracy can still be profitable with execution/sizing). Separately: TJR's strategy
coded and shown to generate no alpha; and a critique of an influencer dashboard showing
+47.97% / 76.89% win rate / PF 2.609 over only 29 trades — his point is the sample, not the
strategy.

**M11. ICT liquidity-sweep mean reversion, explained** (2025-05-06). Sweep → reversal signal,
tight stop, 1:3 target; he characterizes the payoff as structurally short gamma (wins in
low-vol regimes, bleeds in high-vol). Education; no test numbers posted.

**M12. FVG alpha decay** (2025-12-16). ICT search interest surged end-2021; his FVG-tap
win/loss balance on hourly ES flipped from surplus wins to surplus losses over the same
window; method = López de Prado triple-barrier labeling. A decay measurement, not a strategy.

**M13. Z-score reversion walkthrough** (2025-04-29). 20-bar rolling mean/SD bands, enter
beyond ±1 SD, exit at the mean, 2× ATR protective stop. He shows a 26-day drawdown of −48.9%
before recovery to a new equity peak — presented as a lesson in what MR equity curves feel
like, not as a product.

**M14. Oil-import calendar-spread model** (2026-03-02, 2 posts). Three equal-weight factors
(import surprise, international-vs-US price differential, 2M–3M spread) on public US oil
import data; volatility-gated sizing (high vol = no trade). Backtest Jan 2022 – Jan 2026:
~+100% cumulative on margin, rolling Sharpe swinging between +2 and −1. He calls it a naive
pedagogical toy himself.

**M15. Order-flow imbalance replication** (2026-06-24, 2 posts). Reproduces Cont–Kukanov–
Stoikov (2011) on recent US equities: OFI explains ~63–65% of contemporaneous short-term
price variation (≈ the paper's two-thirds); lagged one 10-second interval, R² collapses ~78×.
His conclusion: a contemporaneous mechanism, NOT a tradable signal. Requires tick/order-book
data (Databento).

**M16. Tape-speed "intuition" feature** (2026-06-25, 2 posts). Quantifies "twitchy tape" as
price-update speed; ~5,285 NQ breakout events over 3 years of tick data: high tape speed
first-hit success 55.1% vs 55.1% at normal speed — no filter value; the earlier small-sample
impression was noise, and he says so. (Also: 84.7% of NQ prints move price; update speed
~4/sec at lunch to ~70/sec into the close.)

**M17. Fed decisions from ZQ futures** (2026-09-16, 2 posts). Reads market-implied outcome
probabilities off fed-funds futures. "97.4% accuracy" one day before decisions = 37/38
meetings over 5 years (92.1% at 5 days, 86.8% at 10 days; the one 1-day miss: Oct 29, 2025).
That is the MARKET's pricing accuracy read back, not an independent model — no edge is or
could be claimed from it.

**M18. Prop-firm challenge math** (8+ posts, 2025-02 → 2026-07). Treats a challenge as a
convex structured product: losses capped at fees, so a reshuffling Monte Carlo over a trade
log (tens/hundreds of thousands of paths, firm rules incl. trailing drawdown) yields pass
probability and net EV per attempt. Headline numbers: a coin-flip 0-EV strategy with optimal
risk geometry passes ~45% of the time, vs 12.5% of TopStep traders ever funded; pass-rate
table by geometry (R:R 0.33 @ 75% WR → 40.8%; R:R 4.0 @ 20% WR → 37.2%); a deliberately
negative-EV example (−0.12%/trade, 8% WR, 1:10 RR, 1% risk) still passes a 150K Topstep
challenge ~25% of the time in 10,000 simulations, then most such accounts die within
10–1,000 trades. Also packaged as a QuantPad feature ("Prop Firm Assistant").

**M19. His own Topstep pass** (2025-11-24, 2025-11-27 + series). Passed a Topstep $50K
challenge on the first attempt (certificate Nov 14, 2025) with a programmatic strategy he
describes as having a 93% simulated success probability (92.77% shown on screen). Personal
performance claim; the series teaches the M18 method behind it.

**M20. ICT order block, "tested properly" — the one positive result** (2026-05-15). Half a
decade of NQ front-month data, chronological train/test split, randomized-entry control,
bootstrap CIs: train −$6,850; test +$26,880 (1 contract), 199 trades averaging +0.339R,
bootstrap CI [+0.188, +0.508] (excludes zero); an optimized variant beat buy-and-hold NQ.
This is the most methodologically complete positive claim in the catalog — and it is a
5-minute-intraday NQ futures result, on his data, inside his product.

**M21. Trade-log feature enrichment** (2026-07-26 ×2 + family). Enrich a trade journal with
context features (VIX level, volatility, liquidity, trend, macro regime), compute Spearman
correlations vs P&L with confidence intervals, keep only significant + economically
meaningful factors, convert them into filters. (VIX level significant in his demo.) Same
family: "invisible factors" covariance talk, feature engineering/normalization tutorials,
event-driven sampling (model events — breakouts, sweeps, gaps, vol spikes, news — not every
bar), context-features baseball analogy, regime-segmented attribution.

**M22. Regime-filter metric suite** (2026-01-16 + family). Efficiency Ratio, Volatility
Without Direction, Autocorrelation Decay, Sign Flip Rate / Directional Entropy, Trend
Strength Normalized by Noise, Hurst exponent, spectral features — each with stated pros and
cons (lookback sensitivity, blindness to vol clustering). Plus market-regimes explainer and
Markov-chain regime lectures (3-part, steady-state math). No performance claims.

**M23. Validation doctrine** (threaded through the whole account). Backtesting is a filter
to kill bad models, not a discovery engine (López de Prado cited by name, repeatedly);
minimum viable backtest = confidence intervals (bootstrap, Newey–West mentioned); a single
+8.5% backtest whose Monte Carlo per-trade 90% CI is −0.26%..+0.47% is fragile, not good;
zero-edge strategies produce "profitable-looking" paths by variance alone (70% of 2,000-trade
zero-EV paths green in one sim); win rate and average R:R are insufficient statistics;
a strategy = entry + exit + risk protocol, replicable, tested out-of-sample or it is
"entertainment." Includes a manual bar-replay backtest protocol (Google Sheets logging,
look-ahead avoidance) and a probability-for-trading lecture series.

**M24. Options & implied-information education** (the 20-post OPT cluster + M17 mechanics).
Delta/gamma/theta from first principles; options as probability distributions (single-leg =
buying a PDF, priced to ~zero EV by firms); implied PDFs via IBKR Probability Lab; SKEW
index; IV-based standard-deviation bands vs realized-vol bands; time-evolving vol surfaces;
Black–Scholes theta misconception ("theta decay accelerates" is wrong as usually drawn);
how to read an options chain in 60 seconds. Textbook content, correctly taught.

## PERFORMANCE / RETURN CLAIMS — flagged separately from accuracy & education claims

Return/P&L claims (all his numbers, none verified): **M20** (+$26,880 OOS test, +0.339R,
CI excludes zero — positive); **M9** (4× S&P 500 over 1 OOS year at Sharpe 0.15, ~12 tuned
parameters); **M14** (~+100% on margin, Sharpe unstable +2..−1, self-described naive);
**M7** (32% ML-ORB vs ~100% buy-and-hold; RF-ORB Sharpe ~0.7 for 1 year, none 2000–present);
**M6** (−41.23% — a NEGATIVE result on someone else's strategy); **M19** (his own funded
pass; "93% simulated success"); a June 2025 dashboard post (his coded day strategy: 150
trades, 26.67% win rate, +$1,511.70 / +1.51% on $18K); a "590% move" prediction clip
(Oct 2025) that is staged entertainment, not a claim of record. Accuracy claims (not
returns): M1 (range-forecast error), M10 (71.4% / 49.3% state accuracy), M17 (97.4% = the
market's own pricing read back). One transcription caveat: a Monte Carlo illustration post
quotes his stats as win rate 45–55% with "average risk-reward 20–30" — as summarized that
ratio is implausible and is most likely 2.0–3.0; the post's point (median $141,555 from
$10K across 1,000 simulated 25-trade sequences) is a variance illustration, not a claim
about his trading.

## Overlap with our existing backlog — duplicates are NOT new ideas

- **M1 / VOL cluster ↔ ALREADY IN BACKLOG, twice over.** Harvest #1 (2026-10-13) carried an
  overnight-vol-forecast item (predicting tomorrow's volatility as a sizing input), Harvest
  #2 candidate #4 is volatility-managed exposure, and M1 itself was separately intaken
  2026-10-20 with a backlog-only disposition. Nothing in the 6 other vol posts adds a new
  mechanism — same clustering/GARCH family.
- **M23 + M21 (partially) ↔ QuantFinanceToGo A1/A5, ALREADY ADOPTED.** His Monte Carlo /
  bootstrap / CI doctrine is the same material as QFTG Parts 17/20/22, which became our
  frozen inference layer (Amendments v1/v2: demeaned block bootstrap, Holm family). His
  trade-log enrichment (M21) is the same philosophy as our parked MFE/MAE diagnostic at the
  ~50-signal checkpoint — a method reference for a stage already sequenced, not a new idea.
- **Kelly (STRAT) ↔ QFTG Part 16.** Duplicate; our sizing stays fixed-fractional 1%.
- **M2/M3/M4/M11/M12/M20 (ICT) ↔ Daily Sweep backlog family.** The ICT liquidity-sweep note
  (Facebook reel, 2026-10-16) already parks this family: its mechanics live on 5-minute
  entry refinement and we hold NO qualified intraday data — testing it on 4H bars would
  test a different strategy. His ICT posts inherit the same blocker verbatim. M2's
  entry-location measurement is the one genuinely new datum in this family (see verdict).
- **M5 (SMT) ↔ pairs/cointegration.** Same ground as the QFTG pairs standalone and its A3
  note (Dickey–Fuller bar parked with the mean-reversion family). His result is a clean
  negative on a TikTok confluence; no new testable content for us.
- **M6/M7 (ORB) ↔ a family our registry has already run and failed** (`orb` appears in the
  failure-family list used for Harvest dedupe). His 415-trade negative audit is external
  confirmation, not a new idea; the ML-filter variants are re-parameterizations of the same
  family.
- **M13 (z-score reversion) ↔ mean reversion, QFTG Part 23 discipline.** A plain
  Bollinger-style MR with the DF testing bar already parked; nothing novel.
- **M22 (regime metrics) ↔ our market-gate roadmap** (Stages 2–4: split by gate state,
  beta-scaled strictness, regime classification) and the QFTG Markov standalone. Education
  that matches a roadmap we already have.
- **M17 (Fed-implied) ↔ Harvest #2 #6 pre-FOMC drift only tangentially** (calendar vs
  prediction). Reading the market's own probabilities is not an idea we can test; the
  information is the market price itself.
- **Genuinely new to the backlog (3, all data-blocked):** M2's entry-location effect
  (proximal vs displacement-open, +0.199R after costs) — new, but 5-min NQ; M15 OFI — new,
  but tick data, and his own result says not tradable; M14 oil-import spread — new, but
  commodity futures outside our universe and data. M9's spline volume-profile levels are a
  new construction inside the old levels family, with a 0.15 Sharpe attached — not new in
  any way that matters.
- **M18/M19 prop-firm cluster: not applicable.** Mike trades his own accounts; there is no
  prop program in this operation. The transferable content (reshuffling Monte Carlo) is
  already ours via QFTG A5.

## Aggregate verdict (fractions of the 145-post sample; clusters overlap at the edges)

- (a) Established-textbook content, correctly taught: ~40% (options/Greeks, market
  mechanics, validation doctrine, probability/Markov/regime lectures).
- (b) Plausible-but-unverified claims — his own coded tests and audits: ~30% (TESTS 24 +
  PROP math). Methodologically careful by genre standards (costs charged, CIs shown,
  chronological splits, negative results published), but run on his data, in his product,
  unreplicated by anyone.
- (c) Product marketing: ~7% (QuantPad cluster) plus a marketing layer over much of (b) —
  nearly every test is also a QuantPad demo.
- (d) Genuinely novel vs our backlog: ~2% (3 items above), all blocked on data we do not
  hold. The rest of the remainder is critique/commentary (~10%), strategy philosophy (~6%),
  and personal/other (~6%).

**Draft recommendation for adjudication:** NO new candidate. This is the most
methodologically honest creator account the intake has processed — his doctrine is our
doctrine — and precisely because of that, almost everything in it either duplicates the
existing program or needs intraday/tick data we cannot qualify. File the catalog as
education/method reference. Attach ONE cross-reference to the existing Daily Sweep / ICT
backlog note: if a qualified intraday data route ever exists, M2's entry-location question
and M20's order-block protocol (chronological split + bootstrap CI + randomized-entry
control) are the pre-registered shapes to revisit — in that order. QuantPad itself is a
commercial product; this catalog records its existence and claims, and is not an
evaluation, an endorsement, or a data-route recommendation.

Intake path: Mike's reel + profile + directive 2026-10-20. Status: catalog for ChatGPT
adjudication via the parent agent; nothing tested; no vendor calls; instagram read-only
throughout (no follows/likes/saves/messages). Rate-limit caveat as stated in COVERAGE:
the full 386-post enumeration remains undone until the posts endpoint is available again.

— Muse, 2026-10-20
