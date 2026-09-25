# Lone-Wolf Rerun — strict point-in-time vs the corrected baseline

_Worker (e), 2026-09-24. Research only; nothing frozen was touched. All outputs
under `canonical_baseline/`._

## Frozen rule (no tuning, no variants)

For each of the 4127 v54 candidate signals, compute **stock 20-trading-day RS
vs SPY** and **sector-ETF 20-trading-day RS vs SPY**, both with strict-PIT
endpoints (last completed daily bar as of the signal-bar close —
`PIT_FEATURES.md` rules 2–3; first-4H-bar signals at 13:30 ET resolve to the
previous trading day, second-bar signals at 16:00 ET to the signal date).
**BLOCK when stock RS > 0 AND sector RS ≤ 0.** The block is applied at the
candidate stage, before the portfolio simulation. Sector map: standard
GICS→ETF (Technology→XLK, Financial Services→XLF, Consumer Cyclical→XLY,
Healthcare→XLV, Industrials→XLI, Communication Services→XLC, Energy→XLE,
Consumer Defensive→XLP, Basic Materials→XLB, Utilities→XLU, Real Estate→XLRE).
The 12 ETF symbols (SPY, QQQ, IWM, TLT, XLE, XLF, SMH, DIA, ARKK, GLD, DRAM)
have no GICS sector and pass through unfiltered (documented decision).

## Method

1. Regenerated the full 4127-candidate v54 signal set with worker (d)'s exact
   signal path (`simlib.v54_signals` per TAB131 window). **Replication check:
   running worker (d)'s unmodified `build_v5` on the full set reproduces the
   canonical book exactly (374 accepted trades).** The portfolio machinery is
   therefore byte-identical; only the candidate set differs.
2. Applied the block (strict PIT, verified by independent hand-recomputation
   on sample signals — endpoints and RS values match exactly, 0
   block-condition violations across all 4127).
3. Re-ran the identical V5 walk ($75k book, $750 risk/trade, 6 slots, 5% heat
   cap, rs_top2 ranking) on the filtered set; cost ladder 25/50/75/100bps
   round-trip leg-based; equity curve + max DD via worker (d)'s exact
   `analyze.py` construction.

## Headline: the filter hurts the corrected baseline

| Metric @50bps | Canonical V5 | V5 + lone-wolf | Delta |
|---|---|---|---|
| Expectancy (R/trade) | -0.0013 | **-0.1746** | **-0.1732** |
| Trades | 374 | 274 | -100 |
| Win rate | 39.8% | 33.2% | -6.6pp |
| Profit factor | 1.00 | 0.78 | -0.22 |
| Total R | -0.50 | -47.83 | -47.33 |
| Max drawdown | -39.8% (-$30,504) | **-63.8% (-$48,982)** | -24.0pp |
| Total portfolio return | -0.9% | **-47.8%** | -46.9pp |

### Cost sensitivity (delta in expectancy, R/trade)

| Cost | Base E | Filtered E | Delta E | Delta total R |
|---|---|---|---|---|
| 25bps | +0.1029 | -0.0504 | **-0.1533** | -52.29 |
| 50bps | -0.0013 | -0.1746 | **-0.1732** | -47.33 |
| 75bps | -0.1056 | -0.2988 | **-0.1932** | -42.36 |
| 100bps | -0.2099 | -0.4230 | **-0.2131** | -37.40 |

The degradation is consistent across all cost levels and widens with cost.

## Blocked-signal characteristics

- **Blocked: 1109 of 4127 candidates (26.9%).** Kept 3018. ETF pass-through:
  349 candidates (12 ETF symbols) never evaluated.
- Blocked by signal year: 2024 24.4%, 2025 29.3%, 2026 26.6% — no year is
  spared.
- Blocked by sector (yfinance label): Technology 330, Financial Services 181,
  Consumer Cyclical 140, Healthcare 125, Industrials 124, Communication
  Services 83, Consumer Defensive 57, Energy 48, Basic Materials 17,
  Utilities 4. The block concentrates in the sectors that produced most
  v54 signals (tech/financials), not in a defensive corner.
- Median ADX: blocked 27.0 vs kept 26.6 — the filter is not selecting on
  trend strength; it fires on ordinary v54 signals.
- Of the 374 baseline trades, **114 were blocked by the filter**. Those 114
  had total net R = **-2.22R @50bps** (mean -0.019R, win rate 43.0%) — i.e.
  mildly negative, essentially dead money. Removing them alone would have
  *helped* the baseline by +2.22R.

## Why the portfolio got worse: reshuffling, not the blocked trades

The block is applied at the candidate stage, so slot/heat/busy competition
re-runs on the filtered set. The book is not "baseline minus blocked":

- Only **142 of 374** baseline trades survive in the filtered book.
- **132 newly admitted trades** (never taken by the baseline) lost
  **-51.38R total, mean -0.389R @50bps** — this is the entire damage.
- 232 baseline trades dropped from the book: -4.05R total, mean -0.017R
  (roughly neutral).

The filter removes mildly-bad trades but the freed slots/heat are filled by
much worse replacements. Standalone trade quality of the blocked set
(-0.019R) never justified the portfolio-level cost of reshuffling.

## Concentration of the improvement (negative — concentration of the damage)

Per-symbol delta of total R (filtered − baseline @50bps), worst contributors:

| Symbol | Delta R | Base total R | Filtered total R |
|---|---|---|---|
| GOOGL | -6.67 | +5.89 | -0.78 |
| JPM | -5.70 | +3.50 | -2.20 |
| SNDK | -5.64 | +14.24 | +8.60 |
| VLO | -5.44 | +1.81 | -3.63 |
| CAT | -5.37 | +4.16 | -1.21 |

Top-5 negative contributors sum -28.83R of the -47.33R total delta (61%) —
broad-based, not one outlier. Removing the single worst contributor (GOOGL)
still leaves delta **-0.156R/trade** (filtered E -0.1736 vs base E -0.0174
ex-GOOGL). Offsetting winners exist (AMGN +6.44R, MRNA +5.44R, TXN +4.72R,
COP +4.65R, MSFT +4.04R) but do not rescue the total. **Verdict: not driven
by one symbol; the damage survives top-contributor removal.**

## Year split of the delta (exit year, @50bps)

| Year | Base n / E | Filtered n / E | Delta E | Delta total R |
|---|---|---|---|---|
| 2024 | 117 / -0.2538 | 110 / -0.3610 | -0.1072 | -10.02 |
| 2025 | 128 / +0.0610 | 99 / -0.2366 | **-0.2975** | **-31.23** |
| 2026 | 129 / +0.1658 | 65 / +0.2354 | +0.0696 | -6.08 |

The damage concentrates in **2025** (-31.2R of -47.3R). 2026 is the one
bright spot — higher expectancy (+0.2354 vs +0.1658) but on half the trades
(65 vs 129), so total R still falls.

## Sector-mapping PIT limitation (explicit)

`sectors_raw.json` is a **current-pull (2026-09-25) yfinance GICS snapshot**,
not 2023-vintage assignments — per-name PIT sector history was not available.
Why this does not threaten the result: (1) no sector-level GICS structural
change was implemented during the sample window — the March 2023 revision
(e.g. V/MA/PYPL moving IT→Financials) predates the Oct-2023 sample start,
and the July-2026 GICS consultation's decisions postdate both the sample end
(2026-09-24) and the sector pull; (2) company-level reclassifications are
rare and the delta is broad-based across 8+ symbols/sectors, so a handful of
mis-assigned tail names cannot flip the sign; (3) the block-condition audit
found zero violations and hand-verified endpoints. Residual risk is limited
to individual names reclassified mid-window — immaterial to the verdict.

## Verdict

**No — the strict-PIT lone-wolf overlay does not improve the corrected
baseline; it degrades it substantially.** Post-cost, post-portfolio, at the
50bps headline: expectancy **-0.1732R/trade worse** (-0.0013 → -0.1746),
max drawdown deepens **-39.8% → -63.8%**, total portfolio return collapses
**-0.9% → -47.8%**. The degradation holds at every cost level (25/75/100bps)
and is broad-based across symbols and years (2025 worst). The mechanism is
not that blocked trades were good — they were mildly negative dead money
(-0.019R) — but that candidate-stage filtering reshuffles slot/heat
competition and the 132 replacement trades the filtered book admits lose
-0.389R on average. This overturns the earlier P10 read: on the old
+0.2388R baseline the filter's retained-vs-blocked edge looked mildly
positive under a leaky endpoint; on the corrected ~0R baseline with strict
PIT and full portfolio competition, the overlay is a clear net negative.
**Recommendation: do not adopt the lone-wolf overlay; keep it out of
production and out of the checkpoint candidate list.**

## Files

- `canonical_baseline/lonewolf_rerun.py` — this worker's script (candidate
  regen → strict-PIT block → identical V5 walk → equity/DD)
- `canonical_baseline/lonewolf_candidates.json` — 4127 candidates (regenerated)
- `canonical_baseline/lonewolf_block_decisions.json` — per-candidate block
  decision with strict-PIT RS legs
- `canonical_baseline/lonewolf_trades.json` — 274 accepted trades, filtered set
- `canonical_baseline/lonewolf_rerun.json` — headline, sensitivity, splits,
  concentration, reshuffle decomposition
- `canonical_baseline/scripts/fetch_sector_etfs.py` +
  `canonical_baseline/fetch_sector_etfs_log.json` — daily-bar fetch for the 8
  sector ETFs missing from the cache (XLV, XLI, XLP, XLY, XLU, XLRE, XLB, XLC),
  same conventions as `scripts/fetch_daily.py`
- `canonical_baseline/data/d1_{XLV,XLI,XLP,XLY,XLU,XLRE,XLB,XLC}.pkl` — new
  daily caches (2023-06-01 → 2026-09-24)

_Guardrails honored: no frozen module modified (`v54_engine.py`,
`v54_rules.py`, `scanner_rules.py`, `masterscanner_api.py`, `v54_forward/`,
`signal_log/` untouched — verified via `git status` scope below); no
parameter perturbation or threshold search; the single frozen rule only._
