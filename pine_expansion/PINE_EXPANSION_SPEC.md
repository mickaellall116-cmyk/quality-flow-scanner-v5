# PINE EXPANSION STUDIES — FROZEN SPEC

Written 2026-09-18 BEFORE any test in this batch. No definition below may be changed
after seeing results. Exploratory honesty: these are hypothesis-generating studies;
a positive result is a candidate, not a conclusion, until validated out-of-sample.

## Shared conventions (all studies)

- Pine logic imported UNMODIFIED from `pine_backtest.py`
  (`add_pine_indicators`, `pine_buy_signal`, `gen_pine_trades`,
  `simulate_portfolio`, `summarize`, `COSTS`, `RISK_PCT`, `UNIVERSE_X`).
  Indicator lookbacks kept in BARS everywhere (documented per study).
- Portfolio: $10k start, 1% risk/trade, max 5 concurrent positions, 5% portfolio-risk
  cap, next-bar-open entries, stop-first ties, gap-below-stop skips.
- Costs: 4bps and 25bps (verdict rests on 4bps; 25bps must preserve ranking).
- Metrics per variant: trades, win%, expectancy (R), PF, total return %, max DD %,
  avg hold (bars), TP1 hit %, exit-reason mix.
- Baseline for comparison: PINE_V36_hybrid:UX51:4h = 263 trades, +0.195R, PF 1.27,
  +35.3%, DD 35.2% (4bps; +0.115R at 25bps), window 2024-09-16→2026-09-14.
- Nothing existing is modified. All outputs under `pine_expansion/`.

## STUDY 1 — scanner+indicator agreement filter

Question: do Pine 4H buy signals taken ONLY when the V5 scanner agrees outperform
unfiltered Pine signals?

- Scanner agreement (mechanical): on the SAME symbol, a scanner structural-candidate
  signal bar (frozen `scanner_rules.is_structural_candidate`: entry YES + protection
  SAFE + BUY NOW state + above VWAP + in buy zone) whose bar index differs from the
  Pine signal-bar index by at most N=2 (i.e. ±2 4H bars ≈ ±8h). N=2 is the PRIMARY;
  N ∈ {0,1,3,5} reported as pre-specified sensitivity (verdict rests on N=2).
- Scanner signals regenerated with the FROZEN `backtest_v2.generate_signals` code path
  on the EXACT `backtest_cache/v3/h4_*.pkl` bars the Pine baseline used (same bars both
  sides; daily = `d1_5y` cache, weekly = empty frame → MTF fields False, which cannot
  affect structural candidacy; no gates applied — S0 structural only).
- Filter applied to Pine TRADES (not raw signals): keep a Pine trade iff ≥1 scanner
  structural signal satisfies the ±2-bar rule around its signal bar. Signal-bar index
  matched via timestamp on the shared bar grid (exact match, else nearest within 1 bar).
- Filtered trade list re-run through `pine_backtest.simulate_portfolio`/`summarize`
  with identical conventions.
- Comparisons reported: (a) agreement-filtered (N=2) vs (b) unfiltered Pine baseline
  vs (c) scanner-alone = scanner S0 structural, no gates, scanner exits, via
  `backtest_v2.gen_trades(required=set(), exit_mode="scanner")` on the same bars.
- "Strongly positive" trigger for 2022 validation: filtered expectancy ≥ baseline
  + 0.10R AND ≥30 trades AND PF ≥ baseline PF. If triggered, validate on 2022 4H
  Dukascopy bars (`v6_short_v2/cache` + `pine_exit_fix/cache_2022`, symbols available
  documented) with the SAME N=2 rule and same conventions; a claim requires beating
  the 2022 Pine baseline there too. Otherwise no claim is made.

## STUDY 2 — bigger universe (X2 cohort)

Question: does Pine V3.6 4H hold up on the broader 199-symbol X2 cohort?

- Universe: `v54_universe_x2.UNIVERSE_X2` (199 symbols).
- Data: `masterscanner_api.download_data(sym, "4h", "2y")` per symbol — the SAME
  builder (yfinance 1h → session-aligned closed 4H) that produced the h4 cache.
  Cached to `pine_expansion/cache_x2/h4_{sym}.pkl`. Symbols dropped ONLY for
  missing/empty/no-volume data; coverage count documented honestly.
- Same unmodified Pine logic, same portfolio conventions. Window = whatever the
  2y download yields (≈2024-09→2026-09); actual per-symbol window documented.
- Report: X2-only metrics vs UX51 baseline, plus pooled UX51+X2.

## STUDY 3 — daily and weekly transfer

Question: does unmodified Pine V3.6 transfer to Daily and Weekly?

- Daily: `backtest_cache/v3/d1_5y_*.pkl` (51/51 UX51 symbols, 2021-09-15→2026-09-15 —
  task asked 2020→2026 "if available"; it is not, cache starts Sep 2021, documented).
  Same `run_universe(..., tf="1d")` code path as the published Sep-15 daily run.
- Weekly: yfinance `1wk` 2020→2026 (actual range documented), 51 UX51 symbols,
  downloaded to `pine_expansion/cache_w1/`. Same logic unmodified, lookbacks in bars,
  WARMUP=215 kept (documented consequence: ~260–310 weekly bars → small post-warmup
  sample; if <20 trades, verdict = INCONCLUSIVE, no claim either way).
- Metrics vs 4H baseline. Prior Sep-15 daily file (`pine_backtest_results_daily.json`)
  noted as prior art; verdict rests on this batch's fresh runs with current code.

## Deliverables

`pine_expansion_results.json` (all three studies), `ANALYSIS.md`, per-study scripts.
Final verdicts: YES / NO / INCONCLUSIVE per study, with the numbers.
