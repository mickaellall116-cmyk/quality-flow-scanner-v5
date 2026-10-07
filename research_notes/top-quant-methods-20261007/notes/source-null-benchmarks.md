# Sources: null-hypothesis & benchmark testing — index, 2026-10-07

A. Validation toolbox (pandejesal/wsb-alpha-system web-research/quant-validation-best-practices.md; also sjparthi/brutexold TRACK1_SPA_COMPARISON.md; agarwalchirag535-lab/quant-research-os M6.7 notes — all mutually consistent):
- White's Reality Check (White 2000, Econometrica 68(5)): tests whether the best-of-all-candidates beats a benchmark; multiplicity-corrected p-value via stationary bootstrap; honest but conservative (underperformers still contribute to null bound).
- Hansen's SPA (Hansen 2005, JBES 23(4)): same joint null H₀: max_m E[d_m] ≤ 0 (d = strategy minus benchmark excess return), but recenters only "good enough" strategies (sample mean above data-driven threshold ∝ √(var·log log T / T)); drops nuisance underperformers → more power; studentized; reports 3 p-values, "consistent" one recommended.
- Romano–Wolf stepdown (2005/2016): answers "which strategies are real" (per-strategy list), not just yes/no.
- Sullivan, Timmermann & White (1999/2002, J. Finance): canonical precedent — Reality Check on ~7,800 technical rules over a century of Dow data; apparent profitability largely evaporates after snooping correction.
- Hsu & Kuan (2005); Park & Irwin (2010): RC and SPA on technical-rule universes; apparent best rules lose significance after correction.
- Politis & Romano (1994) stationary bootstrap underlies RC/SPA/DSR resampling; respects autocorrelation.

B. Permutation nulls (MCPT):
- Build Alpha docs (buildalpha.com/category/uncategorized): Monte Carlo Permutation Test — rebuilds synthetic price paths by shuffling the return series, re-runs whole strategy; 1,000 permutations standard (per Timothy Masters). Interpretation: p-value above ~0.10 is a red flag (strategy performs about as well on shuffled data as real data → edge not dependent on real serial structure). "MCPT operates on the price series before the backtest... the only Monte Carlo variant that tests the strategy's discovered patterns rather than its realized outcomes." Complementary: Noise Test (perturb prices, keep sequence — catches fitting to exact bar values).
- Caveat from wsb-alpha-system note: permutation null "destroys the intra-bar autocorrelation a mean-reversion edge depends on" — naive full shuffle is the wrong null for mean-reversion. Fix: block permutation / stationary block bootstrap preserves dependence.
- Implementation pitfall (ksamsoe/strategy-lab docs/mcp.md): shuffling each ticker independently is wrong for portfolios — measured: mean pairwise correlation 0.41→0.0003, equal-weight vol 18.6%→4.9%, shuffled Sharpe 3.1 beat real every time, p=1.000. Synchronized block shuffles keep correlation 0.39, vol 17.3% — close to real 0.41/18.6%.
- Jigsaw Trading (jigsawtrading.com/blog/random-entry-trading): random-entry philosophy — after entry, what you do (exits) is the strategy too; risk/target asymmetry can manufacture win-rate illusions (e.g., 9-tick stop/1-tick target ≈ 90% win rate, no edge).

C. Random benchmarks for single strategies:
- fabian-n8n/ai-quant CLAUDE.md (retail-grade but sound): benchmark vs 200-day SMA trend following AND random entry under identical risk rules; beats buy-and-hold on total return AND Sharpe net of costs; log every variant tested ("count your attempts" — the honest N for DSR).
- medium.com Alex Mountain piece: Donchian strategy — 0.3% of permuted paths beat real (good); but walk-forward profit factor dropped to 1.04, and walk-forward permutation test gave 22% chance of same results by luck (~1-in-5 worthless).
