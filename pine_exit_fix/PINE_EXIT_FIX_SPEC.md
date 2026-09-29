# Pine V3.6 Exit-Fix Spec — PRE-SPECIFIED

Written 2026-09-18 BEFORE any exit-fix test ran. Frozen: no variant may be
added, removed, or re-parameterized after results are seen. If no variant
beats baseline out-of-sample, the verdict is "no fix — keep current exits"
(anti-overfit commitment; no Fix D fitted on 2022).

## Background (from pine_exit_ablation_results.json, UX51 4H 4bps)

- baseline (Pine entries + Pine exits): 263 trades, +0.195R, PF 1.27, maxDD 35.2%
- entries + dumb 20-bar exit: +0.329R  → entries carry the edge
- entries + stop/TP1-only: +0.125R, maxDD 23.9% → the structural stop is too
  tight (cuts recoveries) but buys real drawdown control

Goal: cheaper insurance, not removed insurance.

## Baseline mechanics (from pine_backtest.py / pine_exit_ablation.py)

- Entry: next 4H bar open on Pine Hybrid buy signal; skip if entry gaps below stop.
- stop0 = signal close − ATR(14) × 1.5 (SL_ATR=1.5), close-evaluated → next-bar open.
- TP1 = entry + ATR × 2.0, intrabar limit, takes 50%.
- Runner trails at close − ATR × 2.5 after TP1 (ratcheted per completed bar).
- Runner exits: close < runner, close < EMA55, or trendBear
  (e21 < e55 and close < e200) → next-bar open.
- R-denominated in each variant's own risk unit: risk_frac = (entry − stop0)/entry.
- Portfolio: $10k, 1% risk/trade, max 5 concurrent, 5% portfolio risk; costs 4bps
  (primary) and 25bps (secondary).

## Variants (entries byte-identical to baseline in all variants)

### fixA "wide_stop"
- stop0 = signal close − ATR × 2.25 (1.5× the baseline ATR multiple).
- Everything else identical to baseline: TP1 at entry + ATR×2.0 intrabar 50%,
  trail at 2.5× ATR after TP1, EMA55/trendBear exits, close-evaluated stop.

### fixB "late_arm"
- stop0 = signal close − ATR × 2.25 (wide disaster stop, always active).
- TP1 as baseline (entry + ATR×2.0, intrabar, 50%).
- MFE tracked in R units of the wide stop: mfe_r = max((High − entry)/entry/risk_frac).
- While mfe_r < 1.0: the ONLY exit is close < stop0 (reason "stop").
- Once mfe_r ≥ 1.0: baseline management verbatim — trail ratchet at
  close − ATR×2.5 after TP1, EMA55/trendBear exits — with the runner floor
  initialized at stop0 (the wide stop) instead of the 1.5-ATR stop.

### fixC "slow_trail"
- stop0 = signal close − ATR × 1.5 (baseline).
- TP1 as baseline.
- Runner trails at close − ATR × 3.5 after TP1 (vs 2.5 baseline).
- EMA55-break kept as baseline (close < EMA55 on completed bar → next-bar open).
- trendBear clause REMOVED (fewer exits = slower).

## Winner criterion (exploratory)

Highest expectancy_net_r at 4bps among variants with max_drawdown_pct ≤ 40%.

## Step 2 — exploratory

Same window/data as the ablation: backtest_cache/v3/h4_*.pkl
(2024-09-16 → 2026-09-14), UX51, 4H. Sanity: baseline rerun must reproduce
≈+0.195R. Metrics per variant: trades, win%, expectancy R, PF, total return %,
maxDD %, avg hold bars. Report 4bps primary, 25bps secondary.

## Step 3 — out-of-sample validation

- Window: signals with signal_time ≥ 2022-01-01, data through 2023-01-13
  (cache end); trades open at the end are closed at the last available close
  (documented, same rule for baseline and variants).
- Universe: 2022 4H bars. Guaranteed: 12 symbols from v6_short_v2/cache
  (NVDA, PLTR, TSLA, AMD, AAPL, MSFT, AVGO, GOOGL, AMZN, NFLX, CRM, SPY —
  Dukascopy hourly resampled with scanner_rules.resample_closed_4h, volume is
  CFD tick volume used only relatively). Best effort: extend via Dukascopy with
  the data_2022.py pipeline (fetch hourly 2021-09-01→2023-01-15, split-verify
  vs yfinance, resample identically) for liquid missing UX51 names; document
  exactly which symbols validated and which were unavailable (META not on
  Dukascopy; ARM did not exist in 2022; crypto/ETF/small-cap availability
  uncertain). Validation proceeds on documented coverage, whatever it is.
- Validate: baseline + any variant meeting the exploratory winner criterion.
  (If none meets it, validate the top-expectancy variant anyway and say so.)

## Adoption rule

A fix is ADOPTED only if, out-of-sample, it beats baseline expectancy_net_r
at 4bps with max_drawdown_pct ≤ 40%. Otherwise: no fix — keep current exits.
No further variants. Nothing here touches Mike's TradingView script, frozen
V5.4, or any live system; a win only earns a recommendation.
