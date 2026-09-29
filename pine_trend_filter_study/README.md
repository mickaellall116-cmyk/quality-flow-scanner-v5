# Trend-filter study (2026-09-23)

Research question from Mike: is `trendBull = ema21 > ema55 and close > ema200`
the best bull-trend definition, or does a better drop-in replacement exist?

## Anti-overfit discipline

- Candidate set was **frozen up front** (6 variants, listed below) before any
  results were seen. No candidates added after results, no parameter tuning.
- Each variant tested **exactly once** on one window.
- Bar for adoption: beat CURRENT on 25bps expectancy by a **clear margin**
  (within ±0.02R = noise) AND not blow up drawdown vs baseline.
- Even a winner is a **candidate for post-verdict consideration**, not a live change.

## Candidates (each replaces trendBull wholesale)

| # | Variant | Definition |
|---|---------|------------|
| 1 | CURRENT (baseline) | `ema21 > ema55 and close > ema200` |
| 2 | FULL_STACK | `ema9 > ema21 > ema55 and close > ema200` (stricter stack) |
| 3 | PRICE_STRUCTURE | `close > ema55 and ema55 rising (ema55 > ema55[10]) and close > ema200` |
| 4 | DONCHIAN | `close >= highest(high, 55)` over prior 55 bars (breakout regime) |
| 5 | SUPERTREND_DIR | `close > supertrend_line(10, 3.0)` (ATR(10), Wilder RMA like Pine `ta.atr`) |
| 6 | LOOSE | `close > ema55` only (tests whether current is over-strict) |

## Method

- Canonical `pine_backtest.py` imported **unmodified**; only the trendBull
  computation is swapped per variant (same monkey-patch pattern as
  `pine_entry_timing_backtest/run_entry_timing.py`).
- Universe/window: UX51 4H cache, 2024-09-16 → 2026-09-14 (same as the entry ablation).
- Exits **identical** across variants, including the `trend_bear`
  (`e21<e55 and close<e200`) exit mirror, which is deliberately NOT varied —
  clean isolation of the entry-filter effect.
- Portfolio: 4bps and 25bps costs, $10k, 1%/trade, max 5 concurrent,
  5% portfolio risk, next-bar-open entries, stop-first ties, gap-below-stop skips.
- CURRENT fidelity-verified bar-for-bar against `pb.pine_buy_signal` on all
  51 symbols before the variant runs.

## Files

- `run_trend_study.py` — the study
- `trend_filter_results.json` — pooled + per-ticker (25bps) stats per variant
- `cache/` — reserved (reuses the shared `backtest_cache/v3` h4 files read-only)

## Caveats

- Single window, in-sample; 6 candidates = mild selection pressure.
- Judge variants against **in-test CURRENT only**, not against other studies'
  numbers (different universe/window).
- UX51 4H window; results may not transfer to other universes/timeframes.
