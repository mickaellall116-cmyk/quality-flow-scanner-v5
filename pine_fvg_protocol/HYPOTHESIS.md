# HYPOTHESIS.md — CANONICAL-PROTOCOL STUDY B of 3: FVG-as-entry
# Written BEFORE running. Frozen. No changes after results.

## Hypothesis
FVG-as-entry (with the FIXED definition from the prior studies — no threshold
search, no changes) improves pooled expectancy over the canonical 4H Hybrid
baseline (+0.285R vs +0.239R at 25bps) because it SELECTS a better trade
sample, not because it improves entries. Prior evidence: on 203 shared setups
the entry-price/timing advantage is 0.0000R (byte-identical fills); the +0.046R
headline differential came from trade selection (63 FVG-only trades at
+0.387R, 34 weaker baseline-only trades omitted). The open question is whether
the selection differential is a robust structural effect or a one-trade
accident (RKLB 2024-09-09 +12.98R; without it FVG pooled = +0.237R vs baseline
+0.239R).

## Exact rule
- VARIANT: `make_signal(PERTURB["FVG"])` from `run_fvg_robustness.py` —
  the exact FVG definition used in all prior studies. FIXED. No perturbation
  of the FVG definition in this study.
- BASELINE: canonical 4H Hybrid (`_orig_signal` = `pb.pine_buy_signal`
  unmodified).
- MATCHING: trades matched on (symbol, signal_time). Shared setups compared
  entry-vs-entry; selection analyzed via FVG-only (added) vs BASE-only
  (omitted) buckets.

## Baseline / date range / symbols / costs
- Baseline: canonical 4H Hybrid, 237 trades, +0.239R/trade, 50.6% win, PF 1.38,
  25 bps costs, Oct 2023–Sep 2026.
- Date range: Oct 2023–Sep 2026 (4H bars, frozen Mode B exits).
- Symbols: the 14-name watchlist (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS,
  DRAM, SPCX, ASTX, BBAI, NIO, HOOD, AMD).
- Costs: 25 / 50 / 75 / 100 bps, applied via `net_r(tr, cost)` everywhere.

## The 12 steps (pre-declared)
1. This file. No rule changes after results.
2. Same trade population: matched on (symbol, signal_time). Report shared-trade
   ΔR, FVG-only bucket, BASE-only bucket separately.
3. Dev/validation: DEV Oct 2023–Dec 2024 / VALIDATION Jan 2025–Sep 2026. Rule
   already fixed; report each bucket's expectancy on dev vs validation, no
   retuning.
4. Rolling walk-forward on the selection differential: train 12mo / test 6mo /
   roll 6mo. Windows (signal_time): T1 train Oct2023–Sep2024 → test
   Oct2024–Mar2025; T2 train Apr2024–Mar2025 → test Apr2025–Sep2025; T3 train
   Oct2024–Sep2025 → test Oct2025–Mar2026; T4 train Apr2025–Mar2026 → test
   Apr2026–Sep2026. Combine only the untouched test windows. Metric per test
   window: pooled differential ΔE = E_FVG − E_BASE computed on trades in that
   window; combined = ΔE over the union of test-window trades.
5. Year splits (2023 partial Oct–Dec, 2024, 2025, 2026) + regime splits per
   bucket (QQQ 4H close vs 200-SMA at signal time: bull vs bear/sideways —
   same definition as the attribution study).
6. Cost stress 25/50/75/100 bps on the pooled differential.
7. Perturbation (NOT optimization): FVG definition is FIXED. Perturb the
   *selection* boundary instead — recompute the pooled differential with the
   top-1 trade removed and with the top-3 trades removed from the FVG-only
   bucket. This tests one-trade dependence explicitly. No other variants.
8. Concentration: contribution to the total-R differential
   Σ(FVG-only) − Σ(BASE-only) from the best 1, 3, 5 trades; best 1, 3, 5
   symbols; best 1, 3, 5 themes; best year.
9. Bootstrap: 10,000 resamples. Resample FVG-variant trades and BASE trades
   with replacement independently (n = original n each), compute
   ΔE = E_FVG_boot − E_BASE_boot per resample. Report: fraction of resamples
   with ΔE > 0 (lucky tail vs typical), fraction with ΔE > +0.02R
   (material), and the 5th/50th/95th percentiles of the ΔE distribution.
10. Leave-one-symbol-out: for each of the 14 symbols, drop all its trades
    from BOTH variants and recompute the pooled differential ΔE. A robust
    edge must not flip sign on any single-symbol removal.
11. Economic effect: Δ expectancy (pooled), Δ PF, Δ max DD (equity curves in
    entry_time order, cumulative net R), trades added/removed (FVG-only n /
    BASE-only n), opportunity cost (expectancy of the BASE-only bucket — what
    FVG gave up; and of the FVG-only bucket — what FVG gained), return per
    unit of risk (total net R / max DD) per variant.
12. The exact version is already papered live (FVG paper sidecar since
    2026-09-23). Note that; do not change it.

## Verdict gates (pre-declared)
- PASS: pooled differential positive AND survives removal of the single best
  trade AND does not flip sign under ANY single-symbol removal AND validation
  (Jan 2025–Sep 2026) differential directionally positive AND survives 100bps
  AND bootstrap ≥80% of resamples with ΔE > 0.
- MAYBE: pooled differential positive and holds on most cuts, but fragile on
  one or two robustness gates (e.g. one-trade dependent, or validation flat
  but not negative, or bootstrap 50–80% positive). Needs forward data.
- FAIL: pooled differential ≤ 0 after removing the single best trade, OR flips
  negative under any single-symbol removal, OR bootstrap <50% of resamples
  with ΔE > 0. Per Mike's standard: if the differential survives only with
  the RKLB trade included, that is a FAIL of robustness even if the pooled
  number is positive.

## Notes
- Shared-setup entry-price advantage is expected to re-verify at 0.0000R
  (third verification). It is not the decision metric; the selection
  differential is.
- Method: matched-trade framework from `pine_fvg_attribution`
  (import its helpers and `pine_backtest` unmodified). New folder only:
  `pine_fvg_protocol/`.
