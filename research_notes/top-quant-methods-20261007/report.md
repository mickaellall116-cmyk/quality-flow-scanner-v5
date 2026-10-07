# How Top Quant Firms Structure Strategy Research & Testing
Research date: 2026-10-07. Audience: sophisticated retail systematic trader (already uses frozen systems, walk-forward testing, holdouts, point-in-time discipline, cost modeling). Beginner material skipped throughout.

**Key honesty note up front:** the inner workings of Renaissance, D.E. Shaw, Two Sigma, Citadel, and AQR are proprietary. Almost nothing below about *their internal* gates is verifiable from the firms themselves. What is publicly documented: (a) organizational culture/structure from rare interviews (Simons, Zuckerman, Asness), (b) the academic/statistical apparatus that professional quant research has converged on (largely published by de Prado and collaborators, Harvey/Liu, White/Hansen), and (c) the multi-manager "pod" risk architecture described in institutional research (Morgan Stanley). I mark each claim accordingly: `[known]` = publicly documented, `[inferred]` = reasonable inference from practitioner literature, flagged as such.

---

## Summary

The differentiator between top firms and disciplined retail is not any single statistic — it is (1) treating **the number of things tried (N)** as a first-class input to every significance calculation (DSR, haircuts, MinBTL), which most retail never logs; (2) replacing single-split walk-forward with **symmetric combinatorial validation** (CSCV/PBO, CPCV with purging+embargo) because single splits are high-variance and gameable; (3) testing "did I find *anything*?" rather than "is *this* strategy significant?" via **data-snooping-corrected joint tests** (White's Reality Check, Hansen's SPA, Romano–Wolf); (4) organizational defenses — no-silo collaboration, shared P&L incentives, and hard **drawdown/correlation/capacity limits** at the portfolio level; and (5) a **research→incubation→live pipeline where ~60% of strategies die in paper trading** and position sizing is earned only through surviving live track records. Renaissance's specific edge is described by competitors as organizational (open research, no silos, comp tied to one fund) more than technological.

---

## Findings

### 1. RESEARCH PROCESS STRUCTURE

#### 1a. How firms organize quant research

- **Renaissance Technologies — open, academic, non-siloed.** Per Zuckerman's interview (verified live via page text, https://www.businessofbusiness.com/articles/jim-simons-renaissance-technologies-rentech-gregory-zuckerman-quant/, read 2026-10-07): research groups present to each other; "If one group has a problem, they shut their computers. The other groups can see the work they've done and they pick up on it and they improve on it." Competitors at D.E. Shaw and Two Sigma told Zuckerman they "wish we could be organized like Renaissance, in terms of no silos, in terms of rewarding people based on the one fund" — but that silos evolved "for a reason" and are hard to unwind once established. Simons hires only scientists (physicists, mathematicians, astronomers, computer scientists) who "typically know nothing about finance," per Simons' 2006 IAFE keynote (Reuters via https://quantnet.com/threads/renaissance-hedge-fund-only-scientists-need-apply.555/, index). `[known: organizational culture]`
- **Incentive design as research infrastructure.** Renaissance comp is tied to the Medallion fund. Ex-employee quote to Zuckerman: "Greg, I don't mind getting a cup of coffee for somebody if it means helping Medallion improve." The takeaway for a retail trader is less "hire astronomers" than: your research process's *incentives* should reward killing bad ideas, not just finding pretty backtests. `[known]`
- **Data posture.** Zuckerman's source at Renaissance: "just assume we've tested everything." Early on (1980s–90s) it was hand-collected pricing data (e.g., gold prices from the Fed); since ~2000 it's "everything else" — but the firm acknowledges competitors have caught up on data, and current staff are "not 100% sure why they're so much better than everybody else." `[known]`
- **Multi-manager platforms (Citadel, Millennium, Point72, D.E. Shaw's multi-strat, Balyasny) — pod architecture.** Per Morgan Stanley institutional research (https://www.morganstanley.com/im/en-gb/intermediary-investor/insights/articles/how-multi-manager-platforms-find-strength-in-numbers, index): dozens–hundreds of independent PMs, each with target dollar-volatility budgets, volatility-based drawdown triggers, gross/net exposure limits, position-concentration limits as % of trading levels; a central desk hedges unwanted factor risk via overlays, monitors overlaps in country/industry/style factors and crowded trades, and enforces at-the-touch liquidity. A second Morgan Stanley piece notes platforms monitor *inter-manager correlation* and quant strategies are diversified across horizons with dollar-volume and VaR limits. Per quantlabsnet (index, practitioner account): drawdown limits are often 5–7% of allocated capital; breach → automatic liquidation by the central risk desk, PM frequently removed. Surviving PMs target Sharpe > 2.5 to use leverage safely and manage cross-model correlation. `[known: platform risk architecture; inferred: specifics of each firm's exact thresholds]`
- **AQR — academic, hypothesis-driven at scale.** Asness (Institutional Investor interview, https://www.institutionalinvestor.com/article/2dqsr456gmu55p19gxiio/corner-office/cliff-asness-has-steered-hedge-fund-aqr-through-not-one-not-two-but-three-quant-crises, index): AQR "went through hundreds of hypotheses generated by the outside" to explain value's 2018–2020 drought and could find no reason to abandon the models — the firm *tests hypotheses against data rather than mining data for hypotheses* when defending existing strategies. Separately, Asness admitted the firm got "way too big," said yes to every new strategy team, became "flabby," and had to shrink ~40% of ~1,000 staff — i.e., research *capacity and focus* are themselves a risk to manage. `[known: quotes; inferred: internal gate specifics]`
- **De Prado's industrialized alternative — the "strategy factory."** AFML ch.1 (summarized at https://medium.com/@caneradilirfanoglu/advances-in-financial-machine-learning-part-0-intro-af18a8a295d5, index): split research into specialized roles — Data Curators, Feature Analysts, Strategists, Backtesting Team, Deployment Team, Portfolio Managers — so no single researcher owns idea→backtest→deployment (which is exactly the path that manufactures overfit backtests). This is the formalized version of what Renaissance does culturally and pods do organizationally. `[known: de Prado's prescription; inferred: firms' actual use]`

#### 1b. Hypothesis generation vs data mining

- **Firms test everything but require theory for promotion.** The consistent pattern: *exploration is data-driven and broad* (Renaissance "assume we've tested everything"; AQR tests "hundreds of hypotheses"), while *allocation requires a defensible mechanism*. De Prado's "10 Reasons Most Machine Learning Funds Fail" (JPM 44(6), 2018, pp. 120–133; SSRN https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3104816; via https://github.com/tradingstrategy-ai/docs/blob/HEAD/source/learn/machine-learning.rst and https://github.com/hudson-and-thames/secondbrain/blob/HEAD/Marys%20Room/📕Sources/10%20Reasons%20Most%20Machine%20Learning%20Funds%20Fail.md, index) frames the failure mode as the "Sisyphus paradigm" — siloed quants each pushing their own rock — with the fix being the **meta-strategy paradigm**: researchers collaborate on features and models that feed a common portfolio, so discoveries compound instead of competing. `[known: the paper's argument]`
- **Research through backtesting is itself listed as a failure reason** (#2 in the paper; solution: feature-importance analysis). The professional shift: test whether *features* predict, not whether *strategies* backtest — because backtests are the last, most gameable step. `[known]`
- **Asness on not confusing narrative with evidence:** "the world's very good at explaining why whatever's been happening is just and true and will happen forever" — AQR's process stress-tested explanations for value's drawdown and rejected them all. `[known]`

#### 1c. Idea-to-production pipeline: gates, reviews, kill criteria

- **Documented institutional gate sequence** (from pod-shop and practitioner literature; no firm publishes its full internal checklist — `[inferred]` as industry synthesis): (1) economic/financial rationale gate; (2) statistical gate — multiplicity-adjusted significance (DSR ≥ 0.95 / haircut Sharpe), PBO; (3) robustness gate — parameter plateau, purged/embargoed CV, regime stability; (4) implementability gate — transaction-cost and market-impact modeling at realistic size; (5) portfolio-fit gate — correlation to existing book, crowdedness; (6) incubation — paper/live-small track record before capital. See §5 for what kills strategies at each step.
- **Kill criteria are quantitative and pre-committed:** drawdown limits (5–7% of pod capital), volatility-of-volatility triggers, correlation-to-book caps, and capacity estimates — not "the PM lost confidence." `[known: platform-level; inferred: per-strategy specifics]`
- **Retail-relevant note:** the quant community's own quality-gate examples are explicit where firms' are not, e.g. https://github.com/hzminhzz/quant-research/blob/HEAD/AGENTS.md (index): signal IC ≥ 0.02 with p < 0.05 → DSR ≥ 0.95 → PBO < 0.50 via combinatorial CV → >60% of parameter neighborhood profitable → net-positive after costs. Treat as community practice, not a firm leak.

---

### 2. BACKTEST RIGOR BEYOND BASICS (López de Prado et al.)

#### 2a. Backtest overfitting & the Deflated Sharpe Ratio

- **The core result (False Strategy Theorem).** Bailey, Borwein, López de Prado & Zhu showed that if you try N strategy configurations with zero true edge, the expected *best* Sharpe is positive and grows with N. Calibrated numbers (via https://github.com/cybertraderx/overfit-detector, index): on a 3-year daily backtest with **no edge at all**, expected best annualized Sharpe is ≈0.9 for N=10, ≈1.3 for N=50, ≈1.6 for N=200, ≈1.9 for N=1,000, ≈2.2 for N=10,000. *The retail implication: any grid search producing "Sharpe 1.5" after hundreds of configurations has found approximately what pure noise produces.*
- **The Deflated Sharpe Ratio** — Bailey & López de Prado (2014), *Journal of Portfolio Management* 40(5), pp. 94–107 (verified live via SSRN page https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551, read 2026-10-07): corrects for (1) selection bias under multiple testing and (2) non-normal returns, separating "legitimate empirical findings from statistical flukes" (abstract, verbatim concept).
- **Mechanics** (via https://github.com/ibrahimshere/qmx/blob/HEAD/workroom/research/09-experimentation-search-overfitting.md, index): DSR ≡ PSR(SR̂₀), where the benchmark SR̂₀ is the *expected maximum Sharpe under the null* computed from the number of trials N and the **empirical variance of Sharpe ratios across the trials you actually ran** (V[SR_n]) — the single most-missed input; it requires the search framework to log every trial's Sharpe. PSR itself uses Mertens' (2002) variance, valid under stationarity/ergodicity, correcting for skew and (non-excess) kurtosis. Convention: **DSR ≥ 0.95** to proceed.
- **The worked example from de Prado's own deck** (same source): daily strategy, annualized SR = 2.5, N=100 trials, T=1,250, skew −3, kurtosis 10 → DSR ≈ 0.90 — **fails** at 95% confidence. With N=46 identical strategy → DSR ≈ 0.95, passes. **The identical strategy passes or fails purely on how many things were tried.** This is the professional insight retail almost never implements: significance is a function of the *search*, not the *strategy*.
- **Harvey & Liu's rival formalization** — "Backtesting" (2015), JPM Fall 2015 (SSRN https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2345489, index): the industry's flat "50% haircut" on backtest Sharpes has "good economic and statistical reasons," but they derive a *principled* haircut via Bonferroni/Holm/BH multiple-testing corrections (implemented in R's quantstrat as `SharpeRatio.haircut`: https://rdrr.io/github/braverock/quantstrat/man/SharpeRatio.haircut.html). Key nonlinearity (via https://github.com/ilasek/trading-autoresearch/blob/HEAD/research/notes/2026-08-24-multiple-testing-haircut.md, index): since t = SR·√T, a Sharpe *is* a p-value in disguise. The haircut is **much larger than 50% for annualized SR below ~0.4 and at most ~25% for SR above 1.0** — the flat 50% rule is simultaneously too lenient for weak strategies and too harsh for strong ones.
- **Harvey, Liu & Zhu (2016), "…and the Cross-Section of Expected Returns"**: after multiple-testing correction over 316 published factors, the proper significance bar is **t > 3.0, not t > 2.0** — roughly half of published "factors" fail. (via https://github.com/smalda/finance-stuff/blob/HEAD/legacy/first_draft_weeks/week18_backtesting_capstone/README.md, index)

#### 2b. Combinatorially Symmetric Cross-Validation (CSCV) / PBO

- **Paper:** Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting," *Journal of Computational Finance* 20(4), 2016 (preprint 2014; preprint verified against at davidhbailey.com/dhbpapers/backtest-prob.pdf via https://github.com/howard-lynn-ye/fin-skills/blob/HEAD/fin_skills/_skills/backtest-overfitting/SKILL.md, index).
- **Algorithm 2.3:** build a T×N matrix (one column per configuration tried); split rows into an even number S of contiguous blocks; form **all C(S, S/2) symmetric IS/OOS partitions**; in each, take the best-IS configuration and record its relative rank among OOS performances as w = rank/(N+1); logit λ = log(w/(1−w)); **PBO = fraction of splits with λ ≤ 0** (i.e., how often the IS winner is below-median OOS).
- **The professional details retail implementations get wrong** (same source): (i) **S = 16 is the authors' recommendation** — on ~4 years of daily data each block is a quarter, preserving serial correlation; (ii) the paper's recommended **rejection threshold is PBO > 0.05**, not 0.5 — pure noise sits at ≈0.5 by construction, so "below 0.5" is meaningless as a pass criterion; (iii) the preprint twice prints C(16,8) = 12,780 — the correct value is **12,870** (any implementation hard-coding 12,780 copied the typo); (iv) w = rank/**(N+1)**, not rank/N — the N+1 keeps the logit finite.
- **Calibration:** overfit seasonal rule on a random walk → PBO 55%; genuinely planted monthly effect → 13% (paper's own examples). Independent verification (https://github.com/howard-lynn-ye/fin-skills/commit/a471bd7a4270d6be2761921435815f41f9fbf926, index): planting one real strategy with true SR 0→2 pulls PBO from 0.501 to 0.194; growing the grid around one real strategy (N=2→200) drops the IS winner's median OOS Sharpe from 0.99 to 0.23 and the chance the winner *is* the real strategy from 84% to 14%.
- **Minimum backtest length / minimum track-record length (MinBTL/MinTRL)** — Bailey & López de Prado (2012), "The Sharpe Ratio Efficient Frontier," *J. Risk* 15(2): the sample length required before an observed Sharpe clears the deflated threshold at confidence α. At 1,000 trials and claimed SR 1.0, that's **10+ years** of data (via cybertraderx/overfit-detector, index). Professionals compute how much history a claim *requires*; retail computes what history it *has*.

#### 2c. "7 reasons most machine learning funds fail"

- Paper: "The 10 Reasons Most Machine Learning Funds Fail," JPM 44(6), 2018, pp. 120–133 (SSRN abstract_id=3104816; via tradingstrategy-ai docs + secondbrain note, index). The Cornell ORIE 5256 lecture version presents 7 core pipeline reasons (coursehero deck, ssrn.com/abstract=3447398):
  1. **Sisyphus paradigm** (siloed quants) → meta-strategy paradigm
  2. **Integer differentiation** (stationarity-vs-memory dilemma) → fractional differentiation
  3. **Chronological sampling** → volume/information-driven bars
  4. **Fixed-horizon labeling** → triple-barrier method
  5. **Learning side and size simultaneously** → meta-labeling (primary model predicts side; secondary model sizes — only bet when confident)
  6. **Weighting non-IID samples equally** → uniqueness weighting + sequential bootstrapping
  7. **Cross-validation leakage** → purging + embargoing
- The 2018 paper adds: walk-forward backtesting → **combinatorial purged CV**; research-through-backtesting → feature importance; backtest overfitting → DSR. (Total 10.)
- The through-line: *financial ML fails because researchers use ML as a black-box optimizer on backtests*; de Prado's position is that ML should be applied to **discovering economic theories**, not to maximizing backtest performance (mathinvestor.org, Quant-of-the-Year 2019 note, index).

#### 2d. Techniques professionals use that retail usually skips

1. **Logging N (every trial's Sharpe) as a first-class research artifact** — without it, DSR and haircuts cannot be computed honestly. One retail-grade implementation explicitly "stamps the true trial count on every producer path" (ashmoonori-afk/trading-agent-evolution-lab docs, index).
2. **Purged + embargoed CV instead of naive K-fold** — purge training labels whose horizon overlaps test labels; embargo a gap after each test set to kill serial-correlation leakage (AFML ch.7). The wsb-alpha-system note warns some implementations "purge without an embargo" — an incomplete fix.
3. **Combinatorial Purged CV (CPCV):** enumerate all C(N,k) train/test splits over purged blocks; look at the *distribution* of OOS performance paths, not one split's number.
4. **Meta-labeling:** separate the side bet from the size bet — most retail tunes entries and exits in one optimization, which multiplies degrees of freedom.
5. **Uniqueness weighting:** overlapping labels = the same bet counted many times; weight samples by 1/(number of concurrent labels).
6. **PSR instead of naive Sharpe t-stats:** skew/kurtosis-aware significance as the default Sharpe test.

---

### 3. NULL HYPOTHESIS & BENCHMARK TESTING

#### 3a. Random-entry / permutation benchmarks, bootstraps

- **The right question is "does my strategy beat its own null?", not "is it profitable?"** Professional practice: compare against (i) buy-and-hold of the universe, (ii) a dumb benchmark (200-day SMA trend), (iii) **random entry under identical risk/exit rules**, and (iv) permuted-price-path versions of itself.
- **MCPT (Monte Carlo Permutation Test, after Timothy Masters):** shuffle the price/return series into thousands of synthetic paths preserving statistical properties, re-run the *entire* strategy on each, and compare real performance to the permuted distribution. "The only Monte Carlo variant that tests the strategy's discovered patterns rather than its realized outcomes" (Build Alpha docs, https://www.buildalpha.com/category/uncategorized/, index). Standards: **≥1,000 permutations**; a permutation p-value above **~0.10 is a red flag** — the strategy performs about as well on shuffled data as on real data, i.e., its edge doesn't depend on real serial structure. Complement with a **Noise Test** (perturb prices, keep sequence — catches strategies fit to exact bar values).
- **Two implementation pitfalls that invert the test:**
  - For portfolios, **shuffling each ticker independently is wrong** — measured effect: mean pairwise correlation 0.41→0.0003, equal-weight vol 18.6%→4.9%, shuffled Sharpe 3.1 beat the real run every time (p = 1.000). Fix: **synchronized block shuffles** keep correlation ≈0.39 and vol ≈17.3%, close to real (ksamsoe/strategy-lab docs/mcp.md, https://github.com/ksamsoe/strategy-lab/blob/HEAD/docs/mcp.md, index).
  - Naive full shuffle **destroys the intra-bar autocorrelation a mean-reversion edge depends on** — the wrong null for mean-reversion. Fix: block permutation / stationary bootstrap (Politis & Romano 1994), which preserves dependence (pandejesal/wsb-alpha-system note, index).
- **What "beat random" looks like in practice:** a Donchian strategy where only 0.3% of permuted paths beat real data looked strong — but walk-forward profit factor then collapsed to 1.04 and the walk-forward *permutation* test showed a 22% chance of those results by luck (medium.com account, index). Lesson: pass the null test first, then it still has to survive walk-forward.

#### 3b. White's Reality Check / Hansen's SPA

- **White (2000), "A Reality Check for Data Snooping," *Econometrica* 68(5):** tests the joint null H₀: max_m E[d_m] ≤ 0 — whether the *best of all M candidate strategies* beats a benchmark, with the null distribution built by stationary bootstrap. One p-value for the whole searched universe. Honest but **conservative**: underperforming strategies still contribute to the null bound.
- **Hansen (2005), "A Test for Superior Predictive Ability," *JBES* 23(4):** recenters only the "good enough" strategies (sample mean above a data-driven threshold ∝ √(var·log log T / T)), dropping nuisance underperformers from the null bound → strictly more power; studentized; reports lower/consistent/upper p-values, the **consistent** one recommended.
- **Romano–Wolf stepdown (2005/2016):** answers "which strategies are real" — a per-strategy survivor list — rather than the joint yes/no.
- **Canonical precedent:** Sullivan, Timmermann & White (1999/2002, *J. Finance*) applied the Reality Check to **~7,800 technical trading rules over a century of Dow data** — apparent profitability largely evaporated once snooping over the full universe was corrected. Follow-ups (Hsu & Kuan 2005; Park & Irwin 2010) show best-rule profits losing significance after RC/SPA correction. (All via https://github.com/vishnuvcr/mc-ml_scalping-intraday-btst-swing/blob/HEAD/docs/LITERATURE_REVIEW.md and related notes, index.)
- **Relationship to DSR:** RC/SPA are the *resampling* counterpart to DSR's *closed form* — instead of an analytic expected-maximum, they bootstrap the null distribution of the best strategy's performance. Use both: they fail for different reasons, and agreement is the signal.

#### 3c. When "beating random" is meaningful vs misleading

- **Meaningful:** when the null preserves everything except the thing being tested. Synchronized block shuffles (preserving cross-sectional correlation and autocorrelation), stationary bootstraps, and random-entry benchmarks with identical position-sizing/exit rules isolate *timing/prediction* from *risk-premium harvesting*.
- **Misleading when:** (i) the null destroys the dependence the strategy exploits (mean-reversion vs full shuffle); (ii) a long-only strategy is tested against random *timing* while the return comes from market drift — "a long-only strategy inherits the market's drift under this null, so a high p-value is meaningful: it says the signal isn't doing the work" (strategy-lab docs, index); (iii) trade-list Monte Carlo (reshuffling *trades* after the backtest) is mistaken for strategy validation — it only shows alternate histories of trades you already got, not whether the pattern is real (Build Alpha, index).
- **Entry vs exit nuance:** as the random-entry literature notes (https://www.jigsawtrading.com/blog/random-entry-trading/, index), a large share of a strategy's edge can live in exits/position management rather than entries — test entry filters by ablation (e.g., the fabian-n8n/ai-quant case where a regime classifier scored *identically* to shuffled labels, proving it contributed no timing; https://github.com/fabian-n8n/ai-quant/blob/HEAD/docs/phases/11-evidence-and-ablation.md, index).

---

### 4. OVERFITTING DEFENSES

#### 4a. Beyond train/test splits — what top shops actually do

The professional stack, in order of decision value:
1. **Count trials honestly (N)** and apply DSR (≥0.95) or Harvey–Liu haircut Sharpe to the winner.
2. **CSCV/PBO** on the full trial matrix (reject PBO > 0.05), and **CPCV with purging + embargo** for model selection.
3. **Parameter plateau requirement:** the optimum must sit on a broad profitable plateau (>60% of the parameter neighborhood profitable — community gate standard; de Prado's point is that knife-edge optima are selection artifacts).
4. **Multiple benchmarks:** must beat buy-and-hold on return *and* Sharpe net of costs, a 200-day SMA trend system, and random entry under identical risk rules (fabian-n8n/ai-quant validation standard, index).
5. **Feature-level validation before strategy-level:** feature importance and IC significance before any backtest (de Prado "10 Reasons" #2).

#### 4b. Haircut Sharpe ratios, minimum track-record length

- See §2a for the nonlinear haircut result: haircuts **exceed 50% for annualized SR < ~0.4** and are **≤ ~25% for SR > 1.0**. A retail trader applying a flat 50% haircut is being too kind to marginal strategies and too cruel to exceptional ones.
- MinTRL (Bailey & López de Prado 2012): compute the track record your Sharpe *requires* before it is statistically significant; if required > actual, the Sharpe is not yet trustworthy.
- Institutional reality check on "long enough": pod shops effectively demand multi-year Sharpe > 2.5 histories before scaling PMs (quantlabsnet, index); The Hedge Fund Journal's post-2007-quant-crisis guidance recommends **5+ year track records across bull, bear, and ranging markets** (https://thehedgefundjournal.com/the-case-for-re-evaluating-quant/, index).

#### 4c. Strategy correlation limits, ensembles, limiting researcher degrees of freedom

- **Correlation limits:** platforms actively monitor inter-manager and inter-strategy correlation, partition trading universes, and cap crowded trades (Morgan Stanley, index). The portfolio-level defense: no single strategy or correlated cluster may dominate risk. For retail: cap pairwise strategy correlation in your book and measure marginal contribution to portfolio Sharpe, not standalone Sharpe.
- **Ensembles:** top PMs "run dozens of models simultaneously" with explicit cross-model correlation management (quantlabsnet, index). De Prado's meta-strategy paradigm is the research-side version: many weak, uncorrelated bets > one overfit hero strategy.
- **Limiting researcher degrees of freedom:** the three organizational solutions documented — (i) Renaissance's no-silo + shared-fund incentives, (ii) the strategy-factory role split (no one owns idea→deployment), (iii) the pod's hard stop-losses that remove the researcher's discretion to "wait it out." The statistical versions: log every trial (honest N), pre-commit kill criteria, and require plateau robustness so a researcher cannot tune their way to significance.
- **AQR's cautionary tale:** Asness's admission that saying "yes to everything" made the firm "fat and happy" and forced a 40% headcount cut is the organizational analogue of overfitting — too many trials, too little discipline, and the portfolio paid. `[known: Asness quotes]`

---

### 5. FROM RESEARCH TO PRODUCTION

#### 5a. Paper-trading protocols, incubation periods

- **Industry/practitioner standard: 6–12 months of paper trading minimum** before meaningful capital, with some sources insisting on 6 months *in a demo account* explicitly as an "incubation period" (QuantifiedStrategies: https://www.quantifiedstrategies.com/does-quant-trading-work/; fabian-n8n/ai-quant: https://github.com/fabian-n8n/ai-quant/blob/HEAD/CLAUDE.md; maxkru92 RL-trading skill: minimum 3–6 months; all index).
- **Attrition is the point:** QuantifiedStrategies' journal statistics — ~29 of 30 ideas are discarded in research; of the survivors, ~4 in 10 go live; **~60% of strategies fail the six-month incubation**. "Most trading strategies fail during the incubation period. But the good thing is that no money was lost."
- **Ernest Chan's formulation** (https://www.composer.trade/learn/ernest-chan-on-trading-with-composer, index): paper trading *is* walk-forward testing — its purpose is detecting backtest overfit. "If you find that your paper trading account's performance is far below your backtest performance over a significant period, then you have likely overfitted." (See *Quantitative Trading*, 2nd ed., ch. 3 for his "how long is significant" treatment.)
- **The live protocol** (ivrwealth-ui/trading-library, https://github.com/ivrwealth-ui/trading-library/blob/HEAD/Quant-Trading/chapters/10-backtest-to-live.md, index): (1) paper trade weeks→months — execution, cost, and data gaps surface cheaply; (2) go live *small* — live reveals what paper cannot; (3) **reconcile live vs. backtest-predicted performance for the same period** — a persistent gap is a modeling error, not bad luck; (4) monitor for decay; (5) pre-commit retirement conditions (drawdown threshold, tracking-error threshold, regime change). "The strategy is the least important part of it; the discipline… is what determines whether any strategy actually makes money."

#### 5b. Capacity estimation, market impact modeling

- **Capacity is a first-order strategy property, not an afterthought.** Medallion is the canonical example: capped at ~$10 billion and returns distributed annually because "when you get too big, returns suffer" (Zuckerman interview, verified live; note the transcript's "$10 million" is a transcription error — the reported figure is ~$10B, corroborated by https://github.com/smalda/finance-stuff/blob/HEAD/legacy/first_draft_weeks/week18_backtesting_capstone/README.md: 'manages "only" $10 billion — because capacity constraints limit its strategies').
- **The estimation apparatus:** **Almgren–Chriss (2000)** optimal-execution framework — minimize E[cost] + λ·Var[cost], decomposing market impact into permanent vs. temporary components — is the industry standard for pre-trade cost estimation and TCA conditioning (https://dev.cube.exchange/what-is/almgren-chriss-model; https://en.wikipedia.org/wiki/Almgren%E2%80%93Chriss_model; index). Implementation shortfall (slippage vs. arrival price) is the measurement counterpart.
- **Asness's warning:** "factors can get arbitraged away if too much money pours in, but AQR watches for that" (Morningstar 2019 via ai-cio.com, index) — crowding monitoring is part of the production risk function.
- **Retail practice:** estimate capacity as the size at which modeled market impact (even a simple square-root or linear model) consumes a fixed fraction (e.g., half) of expected edge; if your intended size exceeds it, the strategy is not production-ready regardless of Sharpe.

#### 5c. What kills a strategy between research and live

In rough order of frequency (synthesis across sources; `[inferred]` ordering):
1. **Incubation failure** (~60% per QuantifiedStrategies) — live/paper divergence from backtest.
2. **Cost/impact reality** — edge doesn't survive realistic slippage at real size.
3. **Correlation/crowding** — strategy duplicates existing book risk; central risk rejects it.
4. **Alpha decay** — competition, regime change, or capacity limits erode the edge (DWongResearch: https://medium.com/@dwongresearch0/alpha-decay-what-it-is-and-3-reasons-it-occurs-6cf942d916b4, index). Note: decay is distinct from overfitting — real edges die too.
5. **Operational failure** — data breaks, corporate-action bugs, execution gaps that only appear live (the "reconcile live vs backtest" step exists precisely for this).
6. **Drawdown kill-switches** — at pods, 5–7% drawdown of allocated capital ends the book automatically, regardless of the researcher's conviction.

---

### 6. PRACTICAL TAKEAWAYS (prioritized by impact)

For a trader who already has frozen systems, walk-forward, holdouts, PIT discipline, and cost modeling:

1. **[Highest impact] Log every trial's Sharpe and compute the Deflated Sharpe Ratio (≥0.95 bar).** Your walk-forward and holdouts are still selecting the best of N — DSR is the only common statistic that prices the *search*. The worked example proves the point: SR 2.5 annualized can fail DSR at N=100 and pass at N=46. Without an honest N, every other test is decorative. (Bailey & López de Prado 2014.)
2. **Replace "did my walk-forward pass?" with PBO via CSCV (reject > 0.05) and CPCV with purging + embargo.** A single walk-forward split is high-variance and easily gamed; the combinatorial distribution over all symmetric splits is the professional standard. Remember S=16, w = rank/(N+1), and the 12,870 correction. (Bailey et al. 2016.)
3. **Apply nonlinear haircuts, not flat 50%.** Convert Sharpe → t-stat → multiplicity-corrected p-value → back (Harvey & Liu 2015). Marginal strategies (SR < 0.4) need *more* than 50% haircuts; strong ones (SR > 1) need less. Also compute MinTRL — know how much history your claim requires.
4. **Run the strategy against its own null: synchronized block-permuted price paths (≥1,000), and demand a permutation p-value ≤ 0.10.** Shuffle blocks synchronously across tickers (preserving correlation and autocorrelation), never tickers independently. Then ablate: if a component (regime filter, entry signal) scores the same on shuffled labels as real ones, delete it. (MCPT/Build Alpha; strategy-lab pitfall note.)
5. **Test the joint null, not just the single strategy.** When you've searched a universe, run White's Reality Check / Hansen's SPA over the *full candidate matrix* vs. a benchmark — "is there any edge here?" is a different and stricter question than "is this strategy significant?" Use Romano–Wolf stepdown when you want the survivor list. (White 2000; Hansen 2005.)
6. **Enforce the plateau + multi-benchmark rule before any capital.** Require >60% of the parameter neighborhood to be profitable net of costs, and require beating buy-and-hold (return *and* Sharpe), a 200-day trend baseline, and random entry under identical risk rules. Log all variants — that log *is* your N for takeaway #1.
7. **Institutionalize the pipeline: 6-month incubation, live-small, reconcile, pre-committed kill criteria.** Paper-trade with real-time data; then trade small; continuously reconcile live P&L against what the backtest *predicted* for the same window (persistent gap = model bug); pre-commit drawdown/tracking-error retirement thresholds *before* going live. Expect ~60% of candidates to die here — that's the process working.
8. **Estimate capacity and monitor correlation at the book level.** Size at which modeled market impact eats half your edge = your capacity; cap pairwise strategy correlations; treat a strategy that duplicates book risk as rejected no matter its Sharpe. (Almgren–Chriss framework; pod-shop risk architecture.)

---

## Could Not Verify / Open Questions

- **Internal gate specifics at Renaissance, D.E. Shaw, Two Sigma, Citadel, AQR** are not public. Everything about their idea-to-production checklists, exact DSR/PBO thresholds, and kill criteria is inferred from practitioner literature and organizational reporting — flagged `[inferred]` above. No mission parameter was missing; this is a limit of public information.
- **Whether top firms literally use DSR/PBO/CPCV internally** vs. proprietary equivalents: de Prado's program ran inside AQR (he was principal/head of ML there — mathinvestor.org), which strongly suggests AQR-adjacent adoption; for others it is inference from the fact that these are the published state of the art.
- **The Zuckerman transcript's "$10 million" Medallion cap** is a transcription error; the widely reported figure is ~$10 billion (corroborated by a second source).
- **D.E. Shaw specifics** were thin in search results — covered via the multi-manager/pod literature rather than firm-specific reporting.
- Medallion return figures (66% gross/39% net 1988–2018) appear in secondary notes only; not independently verified for this report and not load-bearing.

## Sources

### Papers (primary)
- Bailey, D.H. & López de Prado, M. (2014). "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality." *J. Portfolio Management* 40(5), 94–107. SSRN page verified live: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551 (read 2026-10-07). → notes/source-dsr-paper.md
- Bailey, D.H., Borwein, J., López de Prado, M. & Zhu, Q.J. (2016). "The Probability of Backtest Overfitting." *J. Computational Finance* 20(4). Preprint: http://davidhbailey.com/dhbpapers/backtest-prob.pdf (verified against via index source below).
- Bailey, D.H. & López de Prado, M. (2012). "The Sharpe Ratio Efficient Frontier." *J. Risk* 15(2). [PSR, MinTRL]
- Harvey, C.R. & Liu, Y. (2015). "Backtesting." *J. Portfolio Management*, Fall 2015. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2345489 (index).
- Harvey, C.R., Liu, Y. & Zhu, H. (2016). "…and the Cross-Section of Expected Returns." *Rev. Financial Studies* 29(1). [t > 3.0]
- López de Prado, M. (2018). "The 10 Reasons Most Machine Learning Funds Fail." *J. Portfolio Management* 44(6), 120–133. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3104816 (index).
- White, H. (2000). "A Reality Check for Data Snooping." *Econometrica* 68(5). (index)
- Hansen, P.R. (2005). "A Test for Superior Predictive Ability." *J. Business & Economic Statistics* 23(4). (index)
- Sullivan, R., Timmermann, A. & White, H. (1999). "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap." *J. Finance* 54(5). (index)
- Politis, D.N. & Romano, J.P. (1994). "The Stationary Bootstrap." *JASA* 89(428). (index)
- Almgren, R. & Chriss, N. (2000). "Optimal Execution of Portfolio Transactions." *J. Risk* 3(2). (index)

### Books (key texts)
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
- López de Prado, M. (2020). *Machine Learning for Asset Managers*. Cambridge UP.
- Chan, E. (2008). *Quantitative Trading*. Wiley. / (2013). *Algorithmic Trading*. Wiley. / (2017). *Machine Trading*. Wiley.
- Zuckerman, G. (2019). *The Man Who Solved the Market*. Portfolio. (reporting basis for Renaissance material)

### Interviews / institutional research (index unless noted)
- Zuckerman interview (Thinknum webinar), verified live: https://www.businessofbusiness.com/articles/jim-simons-renaissance-technologies-rentech-gregory-zuckerman-quant/ (read 2026-10-07). → notes/source-zuckerman-rentech.md
- Reuters/Simons IAFE keynote (2006): https://quantnet.com/threads/renaissance-hedge-fund-only-scientists-need-apply.555/
- Asness / AQR (Institutional Investor): https://www.institutionalinvestor.com/article/2dqsr456gmu55p19gxiio/corner-office/cliff-asness-has-steered-hedge-fund-aqr-through-not-one-not-two-but-three-quant-crises
- Asness (Morningstar 2019, via ai-cio.com): https://www.ai-cio.com/print-page/?url=https%3A%2F%2Fwww.ai-cio.com%2Fnews%2Fmorningstar-asness-no-simple-answer-quant-strategy-losses%2F&cid=41226
- Morgan Stanley multi-manager research: https://www.morganstanley.com/im/en-gb/intermediary-investor/insights/articles/how-multi-manager-platforms-find-strength-in-numbers
- The Hedge Fund Journal ("The Case for Re-Evaluating Quant"): https://thehedgefundjournal.com/the-case-for-re-evaluating-quant/
- Medium (Blotnick, "Death of the Single-Manager Hedge Fund"): https://medium.com/gregory-blotnick/the-death-of-the-single-manager-hedge-fund-how-pod-shops-are-consuming-the-industry-70f2af23824d
- Ernie Chan interview (Composer): https://www.composer.trade/learn/ernest-chan-on-trading-with-composer
- De Prado Quant-of-the-Year note: https://mathinvestor.org/2019/01/marcos-lopez-de-prado-named-2019-quant-of-the-year-by-journal-of-portfolio-management/
- quantlabsnet pod-shop career/risk post: https://www.quantlabsnet.com/post/the-21-million-for-multi-strategy-portfolio-manager-vs-other-quant-positions-the-ultimate-salary-a

### Practitioner/technical notes (index; secondary but mechanically detailed)
- PBO/CSCV implementation verified vs preprint: https://github.com/howard-lynn-ye/fin-skills/blob/HEAD/fin_skills/_skills/backtest-overfitting/SKILL.md → notes/source-harvey-liu-haircuts.md
- Harvey–Liu haircut nonlinearity: https://github.com/ilasek/trading-autoresearch/blob/HEAD/research/notes/2026-08-24-multiple-testing-haircut.md
- DSR mechanics + deck example: https://github.com/ibrahimshere/qmx/blob/HEAD/workroom/research/09-experimentation-search-overfitting.md
- Expected-max-Sharpe table / MinBTL: https://github.com/cybertraderx/overfit-detector
- Validation toolbox (WRC/SPA/DSR/PBO/CPCV): https://github.com/pandejesal/wsb-alpha-system/blob/HEAD/web-research/quant-validation-best-practices.md → notes/source-null-benchmarks.md
- SPA vs WRC comparison: https://github.com/sjparthi/brutexold/blob/HEAD/docs/TRACK1_SPA_COMPARISON.md
- MCPT / permutation practice: https://www.buildalpha.com/category/uncategorized/ ; synchronized-shuffle pitfall: https://github.com/ksamsoe/strategy-lab/blob/HEAD/docs/mcp.md ; random-entry philosophy: https://www.jigsawtrading.com/blog/random-entry-trading/
- "10 Reasons" study notes: https://github.com/hudson-and-thames/secondbrain/blob/HEAD/Marys%20Room/📕Sources/10%20Reasons%20Most%20Machine%20Learning%20Funds%20Fail.md ; https://github.com/tradingstrategy-ai/docs/blob/HEAD/source/learn/machine-learning.rst → notes/source-ml-funds-fail.md
- Incubation statistics: https://www.quantifiedstrategies.com/does-quant-trading-work/ ; live protocol: https://github.com/ivrwealth-ui/trading-library/blob/HEAD/Quant-Trading/chapters/10-backtest-to-live.md → notes/source-firms-production.md
- Almgren–Chriss explainer: https://dev.cube.exchange/what-is/almgren-chriss-model ; https://en.wikipedia.org/wiki/Almgren%E2%80%93Chriss_model
- Alpha decay (3 reasons): https://medium.com/@dwongresearch0/alpha-decay-what-it-is-and-3-reasons-it-occurs-6cf942d916b4
- quantstrat haircutSharpe docs: https://rdrr.io/github/braverock/quantstrat/man/SharpeRatio.haircut.html

### Research notes in this directory
- notes/source-dsr-paper.md, notes/source-zuckerman-rentech.md, notes/source-ml-funds-fail.md, notes/source-harvey-liu-haircuts.md, notes/source-null-benchmarks.md, notes/source-firms-production.md
