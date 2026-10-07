# Sources: Harvey–Liu "Backtesting" haircuts + PBO/CSCV mechanics — index, 2026-10-07

A. Harvey, C.R. & Liu, Y. (2015), "Backtesting", Journal of Portfolio Management, Fall 2015 (SSRN https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2345489; 32 pages; INQUIRE Europe/UK 1st prize).
- Industry convention: discount reported backtest Sharpe ratios by 50% ("haircut"), justified by inevitable data mining.
- Propose principled haircut Sharpe ratios via multiple-testing corrections (Bonferroni, Holm, BHY/FDR); implemented in R quantstrat as SharpeRatio.haircut / haircutSharpe (rdrr.io, rdocumentation.org pages).
- Key nonlinearity finding (via ilasek/trading-autoresearch note, tier-A rated): t = SR·√T, so a Sharpe is a p-value in disguise → apply multiple-testing corrections to the p-value, map back. Across adjustment methods: haircut is MUCH larger than 50% for annualized SR below ~0.4, and at most ~25% for SR above 1.0. The flat 50% rule is simultaneously too lenient for weak strategies and too harsh for strong ones.
- Companion: Harvey, Liu & Zhu (2016), "... and the Cross-Section of Expected Returns" — 316 published factors; proper multiple-testing significance threshold is t > 3.0, not t > 2.0; roughly half of published factors fail. (via smalda/finance-stuff note)

B. PBO / CSCV mechanics (howard-lynn-ye/fin-skills SKILL.md — verified against authors' preprint at davidhbailey.com/dhbpapers/backtest-prob.pdf):
- Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting", Journal of Computational Finance 20(4), 2016 (preprint circulated 2014).
- CSCV Algorithm 2.3: T×N matrix (N configs); split rows into even S blocks; all C(S,S/2) symmetric IS/OOS partitions; n* = best IS config; relative rank w = rank/(N+1) (the N+1 keeps logit finite); lambda = log(w/(1−w)); PBO = share of splits with lambda ≤ 0.
- S=16 is the authors' recommendation (on ~4y daily data each block ≈ a quarter, preserving serial correlation).
- Rejection threshold is much stricter than "below 0.5": paper says reject PBO > 0.05. Worked examples: overfit seasonal rule on random walk → 55%; planted monthly effect → 13%.
- Preprint typo: prints C(16,8)=12,780 twice; correct is 12,870.
- Noise calibration: PBO on pure noise sits ≈0.5 by construction (planting one real strategy with true SR 0→2 pulls PBO from 0.501 to 0.194).
- cybertraderx/overfit-detector: expected best Sharpe with NO edge on 3-year daily backtest: N=10→0.9, 50→1.3, 200→1.6, 1000→1.9, 10000→2.2. At 1000 trials and claimed SR 1.0, need 10+ years before claimed SR stops being explainable by search (MinBTL).

C. DSR mechanics (ibrahimshere/QMX research note, quoting Bailey & López de Prado 2014 + LBNL deck):
- PSR(SR*) = Z[(SR̂−SR*)·√(T−1) / √(1−γ₃·SR̂+((γ₄−1)/4)·SR̂²)], γ₃ skew, γ₄ kurtosis (not excess), T obs, Z normal CDF (Mertens 2002 variance; valid under stationarity/ergodicity).
- DSR ≡ PSR(SR̂₀) with SR̂₀ = √V[SR_n]·((1−γ)Z⁻¹[1−1/N]+γZ⁻¹[1−1/(N·e)]), γ=Euler–Mascheroni; V[SR_n] = variance of Sharpe ratios ACROSS the trials you actually ran (empirical; must be recorded during search — most-missed input).
- Deck's worked example: daily SR 2.5 annualized, N=100 trials, V=1/2, T=1250, skew −3, kurt 10 → DSR ≈ 0.90 (fails 95%); with N=46 it passes. Same strategy passes/fails purely on how many things were tried.
- Threshold convention: DSR ≥ 0.95.
