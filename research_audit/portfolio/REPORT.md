# Portfolio Realism Audit — Quality Flow Scanner research
**Date:** 2026-09-24 · **Auditor subagent** · **Scope:** the 4H Hybrid baseline
(237 trades, +0.2388R @25bps, Oct 2023–Sep 2026, 14-stock watchlist) and the
portfolio sims used in the ranking studies. Audit only — no code outside
`research_audit/portfolio/` was touched; `pine_backtest.py` was imported
unmodified.

**Artifacts:** `replay_portfolio.py` (independent replay engine),
`replay_results.json` (all numbers), this report.

---

## 1. Existing-sim assumptions table (with citations)

| Assumption | `pine_backtest.py::simulate_portfolio` (lines 221–283) | Ranking sims (`pine_ranking/pine_ranking.py:135+`, `pine_ranking_backtest/run_ranking_factors.py:131+`) |
|---|---|---|
| Slot cap | 5 concurrent (`MAX_CONCURRENT=5`, line 40). Trade skipped, counted in `skipped_cap_count`, never retried (lines 257–260) | Same 5-slot cap (`pb.MAX_CONCURRENT`); adopted rule takes **top-2 by rank at contested bars** even when slots are free (`n_cap=2`) |
| Same-timestamp ordering | Events sorted `(time, kind)` → **exits processed before entries** (lines 222–226). Among simultaneous *entries*: Python stable sort on `(time, kind)` only → order = whatever `all_trades` order was. `run_fvg_robustness` sorts by `entry_time` only (line ~203), so ties fall back to **WATCHLIST loop order** (QQQ, SMCI, PLTR, …) — an undocumented artifact, not a rule | Exits first, then entries by score desc; **tie-break = original candidate order** ("UNIVERSE_X symbol order, then entry time"). `RANKING_SPEC.md:40-42` admits this was amended from "symbol name" purely to reproduce `simulate_portfolio` exactly for the fidelity check |
| Heat cap | `open_risk + risk_pct > 0.05` → skip (`skipped_cap_risk`, lines 261–264). `open_risk` = Σ initial risk_dollars / marked equity. With 5×1% slots the cap is nearly redundant — it can only bind when equity has fallen | Identical heat check |
| Capital constraint | **None.** `size = risk_dollars / risk_frac` (line 267) is fractional and unbounded — infinite liquidity assumed. No affordability check, no cash/margin cap | None |
| Sizing | `risk_dollars = 1% × marked equity` (compounds on *unrealized* gains too, line 265) | Identical |
| Theme/sector limits | **None** | None |
| Partial fills / skipped-entry handling | None — fills always complete at the synthetic blended exit; skipped signals vanish | None |
| Costs | 25bps charged **once** on blended return (`_outcome`: `net_ret = gross_ret − cost`, lines 216–219) — i.e. one leg only | Identical |
| Drawdown | Mark-to-market on every event (lines 278–283) | Identical |

**Key gaps vs production reality:** (1) fractional sizing — no whole-share rounding and no "can't afford one share" skip; (2) no cash/notional cap; (3) the tie-break for simultaneous entries is an implicit code artifact, never a stated rule; (4) single-leg costs understate a real round trip; (5) heat measured on initial risk vs marked equity is fine, but with 5 slots it almost never binds — the *research* binding constraint is the slot cap, while *production* (6 slots + 5% heat) binds on heat first.

---

## 2. Independent replay — numbers first

Engine: new event-driven replay (`replay_portfolio.py`), $75k book, 6 slots,
1%-risk **whole shares** (`floor(risk_budget/(entry−stop))`; skip if < 1 share),
5% heat cap on initial risk, **25bps round-trip on notional** (entry + exit
legs), exits fill before entries at each timestamp, primary ordering =
(timestamp, symbol alphabetical). Trade list regenerated via unmodified
`pb.gen_pine_trades` — reproduced the baseline exactly (237 trades, 0.2388R,
30.74R independent DD ✓).

| Metric | Independent (no portfolio) | Realistic replay (primary) | Δ |
|---|---|---|---|
| Trades taken | 237 | **183 (77.2%)** | −54 |
| Expectancy / trade | +0.2388R | **+0.2172R** | −0.0216R (−9%) |
| Total R | 56.59R | **39.74R** | −30% |
| Total return ($75k) | — | **+42.55%** | — |
| Max drawdown | 30.74R (fixed-1R curve) | **27.71%** (mark-to-market) | — |
| Win rate / PF | 50.6% / 1.38 | 50.8% / 1.34 | flat |

Skip reasons (primary): **heat 54, slots 0, affordability 0, theme 0, cash 0.**
Max concurrent open was **5** — the 5% heat cap blocks the 6th position, so
production's "6 slots + 5% heat" behaves as **~5 effective slots**: the research
5-slot sim turns out to be a realistic proxy, by accident of the heat rule.

Decomposition of the −0.0216R/trade gap:
- The 54 heat-skipped trades averaged **+0.108R** (research-convention R) — mildly positive. Skipping them cost 5.85R/237 = −0.025R/trade, but the taken set's mean R is *higher* (0.277R vs 0.239R): the heat constraint discards weaker trades.
- The replay charges **round-trip** costs (25bps × entry notional + 25bps × exit notional); the research convention charges one leg. The extra leg costs ≈ **0.06R/trade** on typical ~6%-risk stops. Under the research's own single-leg convention, the replay's taken set earns **+0.277R/trade** — the headline 0.239R was never a deployable per-trade number; realistic costs shave ~0.06R off it before any constraint binds.

Diagnostic variants: theme cap 2 → **identical** (max theme concurrency observed was 2 — the production rule never binds, confirming the P3 "decorative" finding); cash cap → 183 taken, +42.88% (never binds at $75k); fixed $750 sizing → 185 taken, +0.201R, +37.31%, DD 18.95% (no compounding → lower return *and* lower DD).

---

## 3. Ordering sensitivity (the tie-break is a real P&L driver)

| Ordering | Taken | Expectancy | Return | Jaccard vs primary |
|---|---|---|---|---|
| alpha (primary, documented) | 183 | **0.2172R** | 42.55% | 1.000 |
| watchlist order (research artifact) | 180 | 0.2104R | 39.80% | 0.901 |
| reverse-alpha (adversarial) | 181 | 0.1886R | 34.66% | 0.857 |
| 5 random shuffles | — | 0.2178–0.2297R | — | 0.911–0.937 |

Same-bar contested timestamps: **20** (of 48 heat-skip events; the rest are
sequential — positions still open when new signals arrive, where ordering is
irrelevant). A meaningless tie-break moves absolute expectancy by
**±0.015R (random) to −0.03R (adversarial)** and changes ~10–14% of the taken
set. Every ranking-study absolute number inherits this confound, because the
research tie-break was "whatever order the candidate list happened to be in."

**Interaction with the ADX ranking question:** the entire ranking debate (ADX
vs rs_top2 vs take-all) can only ever act at those 20 genuine same-bar
contests. A **lookahead oracle** that picks the best-R candidates at each
contested bar adds **+11.41R total (≈ +0.048R/trade)** — the absolute ceiling
for *any* same-bar ranking factor, with perfect foresight. Real factors capture
a fraction of that. The study deltas that exceed ordering noise (rs_top2
−0.061R vs take-all; ADX +0.154R vs rs_top2) survive this audit, but their
absolute levels carry ±0.02–0.03R tie-break uncertainty, and the adopted
take-top-2 rule discards more trades (~59) than production's heat constraint
would (~54) — different mechanism, similar magnitude.

---

## 4. Verdict: **WARNING** (edge is real; headline numbers overstate deployable capture)

- **Expectancy survives contact with portfolio constraints**: +0.217R/taken-trade
  vs +0.2388R headline (−9%). Not a fail.
- **But only 77% of signals get taken** (183/237), all skips from the 5% heat
  cap — the binding constraint in production, not the slot count.
- **The 0.239R headline is overstated by ~0.06R/trade from the cost convention
  alone** (single-leg vs round-trip). Deployable per-trade expectancy is
  ~0.22R, not ~0.24R.
- **Total R capture drops ~30%** (56.6R → 39.7R): 23% fewer trades × heavier costs.
- **Drawdown is worse than the research sim suggested**: 27.7% marked DD here
  vs 21.6% in the research 5-slot sim (different bases; direction is up).
- Research 5-slot assumption **vindicated**: production 6-slot+heat ≈ 5 effective
  slots. Theme cap 2, cash cap, affordability **never bind** at $75k — decorative.
- **Recommendation:** define the simultaneous-entry tie-break explicitly in the
  production spec (it's a ±0.03R/trade driver — same order as the entire
  ranking-question upside); report future expectancy with round-trip costs.

**Estimated impact on expectancy:** −0.02R/trade from constraints proper;
−0.06R/trade additional if costs are stated honestly (round-trip). Total
deployable ≈ **+0.21–0.22R/trade on ~77% of signals**, i.e. ~70% of the
headline total-R over the same period.
