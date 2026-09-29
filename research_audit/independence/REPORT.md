# Audit: Trade Independence + Profit Concentration

**Repo:** `~/workspace/quality-flow-scanner-v5` · **Date:** 2026-09-24
**Subject:** the 237-trade baseline (canonical 4H Hybrid entries, per-trade net R @25bps costs,
Oct 2023–Sep 2026, 14-stock watchlist: QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX, ASTX, BBAI, NIO, HOOD, AMD)
and the lone-wolf retained set (154 trades).

**Method:** Baseline trade list regenerated deterministically by importing `pine_backtest.py`
**unmodified** (`pb.gen_pine_trades` on `pine_entry_timing_backtest/cache/h4_{sym}.pkl`,
`pb.add_pine_indicators`, sorted by entry_time) and cross-checked against the study record:
n=237, expectancy=**0.2388R** @25bps — exact match to
`pine_lonewolf_protocol/mike_validation_results.json` → `first_report.baseline`.
Retained set rebuilt by replicating the SIGN20 flag logic from
`pine_lonewolf_protocol/run_mike_validation.py` verbatim: n=154, expectancy=**0.3773R** —
exact match to `first_report.retained`. No new edge proposed or tested.
Files: `audit.py`, `audit_results.json`, `audit_supplement.json`, `baseline_trades.csv`,
`retained_trades.csv` (all in this folder).

---

## 1. TRADE INDEPENDENCE

### Overlap in holding periods (`audit_results.json` → `independence`)

| Measure | Value |
|---|---|
| Trades whose holding period overlaps ≥1 other trade | **229 / 237 (96.6%)** |
| Trades with ≥50%-shared holding vs ≥1 other trade ("heavy overlap") | **228 / 237 (96.2%)** |
| Mean overlaps per trade | **7.76** |
| Max concurrent open positions (portfolio-wide) | **11** |
| Concurrent open at a trade's entry — median / mean / p90 | **5 / 5.08 / 8** |
| Only 15 trades ever entered with nothing else open; 3 entered with 11 open | — |
| Time-connected "episodes" (overlap-graph components), n=237 | **18** (largest holds **76** trades) |
| Heavy-overlap episodes | **21** (largest holds **51** trades) |

### Correlation of R by shared holding time (`audit_supplement.json` → `overlap_bucket_r_corr`)

Fraction of max holding shared → Pearson r of per-trade net R:

| Shared holding | n pairs | r |
|---|---|---|
| 0 (no overlap) | 27,046 | −0.01 |
| (0, 25%] | 462 | −0.07 |
| (25%, 50%] | 269 | **0.43** |
| (50%, 75%] | 133 | **0.48** |
| (75%, 100%] | 56 | **0.74** |

Trades that share most of their holding period move together strongly (r up to 0.74).
Same-entry-bar pairs: r=0.26 (46 pairs, p≈0.08 vs shuffle null).
Notably, heavy-overlap **same-theme** pairs correlate *less* (r=0.10, 77 pairs) than
heavy-overlap **different-theme** pairs (r=0.23, 674 pairs) — the correlation is a
**market/timing** effect, not a theme effect.

### Theme/sector split (`audit_results.json` → `independence.theme_breakdown`)

| Theme | Trades | Share of trades | Share of P&L |
|---|---|---|---|
| AI software (PLTR, BBAI) | 37 | 15.6% | **+34.5%** |
| Fintech (SOFI, HOOD) | 46 | 19.4% | **+30.3%** |
| Space (RKLB, ASTX, SPCX) | 30 | 12.7% | **+29.1%** |
| Drones/IoT (ONDS) | 16 | 6.8% | **+18.7%** |
| EV/consumer (NIO) | 12 | 5.1% | +2.9% |
| AI infra/semis (SMCI, AMD, DRAM, ANET) | 67 | 28.3% | **−7.1%** |
| Tech index (QQQ) | 29 | 12.2% | **−8.4%** |

So the answer to "is it one AI/tech bet?": **not quite** — the largest sleeve
(AI infra/semis, 28% of trades) actually *loses* money, and QQQ is negative too.
The P&L comes from software, fintech, and space names. But it **is** largely one
**market-regime bet**: the winners are the trades that cluster in broad-rally
episodes. Heavy-overlap trades average **+0.83R**; isolated trades average **−0.95R**
(`audit_supplement.json` → `heavy_overlap_vs_isolated`). This is the same
phenomenon the P11 breadth study found from the other side (6–10-signal crowded
bars: +0.379R).

### Effective independent sample size

| Method | Effective n |
|---|---|
| Empirical correlation matrix (bucket ρ by shared holding, n²/ΣΣρ) | **≈83** |
| Design effect on heavy-overlap episodes (ICC≈0.023, DEFF≈1.21) | ≈196 |
| Collapsing same-entry-bar trades into one "bet" | 199 |
| Connected time episodes (hard upper bound on independent chunks) | **18–21** |

The correlation-matrix estimate is the honest one: **≈80–130 effective bets, roughly
one-third to one-half of 237**. Standard errors on expectancy are understated by
√(237/83) ≈ **1.7×** under i.i.d. assumptions. Consequence: the studies'
bootstrap CIs and t-style gates (e.g. lone-wolf's 94.42% vs the 95% bootstrap
gate — already a near-miss) are materially narrower than the data justify.

**Is this 237 independent bets? No.** It is effectively ~80-odd independent
outcomes riding on ~18–21 market episodes. **Is the portfolio one AI/tech bet
repeated?** No on theme (semis lose; software/fintech/space win), but yes on
timing — it is effectively **one broad-risk-regime bet repeated**: the edge
appears almost exclusively in crowded bull episodes and vanishes in quiet or
bearish stretches.

---

## 2. PROFIT CONCENTRATION

Baseline = 56.59R total over 237 trades (0.2388R expectancy).

| Cut | Share of total P&L | Expectancy without it |
|---|---|---|
| Best 1 trade (HOOD, 2025-04, +8.67R) | 15.3% | 0.2030R |
| Best 3 trades (HOOD +8.67, RKLB +6.69, ONDS +6.68) | 38.9% | 0.1477R |
| Best 5 trades | **59.7%** | 0.0984R |
| Best 10 trades | **99.9%** (56.51 of 56.59R) | **0.0004R** |
| Best 1 month (2025-06, 13 trades, +22.89R) | 40.5% | 0.1504R |
| Best 3 months (2025-06, 2026-04, 2024-10) | **83.7%** | 0.0452R |
| Best year (2025: +45.07R) | **79.6%** | 0.0853R |
| Best 1 symbol (RKLB, +19.94R) | 35.2% | — |
| Best 3 symbols (RKLB, PLTR, HOOD) | **83.8%** | — |
| Best theme (AI software) | 34.5% | — |

The remaining **227 trades net +0.08R — essentially zero**. Without the best 3
months, expectancy falls to **0.045R** (one-fifth of headline). Without 2025,
**0.085R**. The >50%-from-≤3-trades red flag does not fire at exactly 3 trades
(38.9%), but its spirit fires everywhere: top-5 = 60%, top-10 = 100%, top-3
months = 84%. Year 2026 (n=60) ran at **−0.2423R** — a year without rally months
is a losing year.

### Lone-wolf retained set (154 trades, total 58.11R, expectancy 0.3773R)

| Cut | Share of retained P&L | Expectancy without it |
|---|---|---|
| Best 3 trades | 37.9% | 0.2389R |
| Best 5 trades | 56.4% | — |
| Best 10 trades | **88.2%** | — |
| Best 3 months | **62.2%** | 0.1628R |
| Best year (2025) | **62.1%** | 0.2593R |
| Top symbols (ONDS, HOOD, RKLB, PLTR) | ~80% | — |

The retained set is **less concentrated than baseline but still heavily
concentrated**: 10 trades carry 88% of its P&L, 3 months carry 62%. Its headline
+0.3773R leans on the same rally episodes as the baseline. (Note: retained
expectancy *excluding its own best 3 months* is 0.163R — still positive, which is
genuinely better than baseline's 0.045R, but the concentration is not cured.)

### ADX-selected set
**Not audited at trade level.** None of `pine_adx_protocol/adx_protocol_results.json`,
`adx_selection_edge.json`, `adx_protocol_addendum.json`, or `pine_fvg_protocol/fvg_protocol_results.json`
contain trade lists (only aggregate stats), and the runs that produced them were
not re-executed (writes outside this folder are out of scope). What is known from
the records: the ADX selection differs from take-all only on 21 crowded bars
(`n_genuine_crowded_bars`), and its selection-edge bootstrap has p5 ≈ 0.002 —
barely positive. The ADX-selected pool is the same trade universe, so the same
episode-concentration applies; its MAYBE verdict already flags 2025-concentration
("112.7% of edge in 2025"). Treat its concentration as **at least as severe as
baseline until proven otherwise**.

---

## 3. VERDICTS

### Trade independence: **FAIL**
- 237 is not the effective sample. The honest effective n is ≈80–130
  (correlation-matrix estimate ≈83), with outcomes arriving in ~18–21 market
  episodes and per-pair correlation up to r=0.74 for co-held trades.
- Estimated impact: i.i.d.-based uncertainty (bootstrap CIs, t-stats) understates
  true standard error by ~1.4–1.7×. For the **baseline**, the true 95% interval on
  +0.2388R is roughly 1.7× wider than reported. For **lone-wolf**, the already
  near-miss bootstrap gate (94.42% vs 95%) is on the wrong side of any honest
  gate — its PASS should be read as "passes the i.i.d. bar, fails an
  episode-clustered bar." Any live checkpoint decision must use
  **episode-clustered resampling**, not trade-level i.i.d. bootstrap.

### Profit concentration: **FAIL**
- Baseline: top-10 trades = 99.9% of P&L; remaining 227 trades net ≈ 0.
  Best 3 months = 83.7% of P&L; without them expectancy is 0.045R; without 2025
  it is 0.085R; 2026 ran at −0.242R.
- Estimated impact: the +0.2388R baseline is not a per-trade edge so much as
  **10 trades in 3 rally months of 2025-style markets**. Forward expectations
  should be anchored to the *episode* base rate (~18–21 episodes in 3 years, most
  negative-or-flat), not to 237 "independent" 0.24R bets.
- For **lone-wolf retained**: concentration improves (top-10 = 88%, best-3mo =
  62%) but does not clear; its edge story ("blocked trades are dead money") is
  intact, but the retained edge is equally episode-dependent.
- For **ADX**: unauditable at trade level; assume baseline-like concentration
  until a trade list is produced; its MAYBE verdict already encodes the
  2025-concentration risk.

### Plain-English bottom line
This is not 237 independent 0.24R bets. It is roughly **80 independent-ish
outcomes riding ~20 market episodes**, and essentially all the profit came from
**10 trades in 3 good months**. The scanner's edge, if real, is a
right-tail/episode edge — it works when many signals fire together in a rally
and bleeds the rest of the time. The reported numbers (+0.2388R baseline,
+0.3773R retained, ADX +0.314R) are best read as *episode-weighted* estimates
with roughly 1.7× wider uncertainty than the studies quote. Nothing in the
frozen systems needs to change, but no go-live sizing or checkpoint verdict
should treat these as 237 independent draws.
