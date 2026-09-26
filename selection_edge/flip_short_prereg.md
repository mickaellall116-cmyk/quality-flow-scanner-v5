# Pre-registration: Long→Short Flip Test (buy signals, flip to short at exit)

Date: 2026-09-25
Ordered by: Mike — "what if we bought buy signals and then short exit... on all time frames, also combo, to see."
Status: FROZEN before execution. No changes after results are seen. No re-tuning under any outcome.

## Hypothesis

Buying validated buy signals and then reversing to SHORT at the long leg's
exit (one combined system, not two books) produces higher expectancy than
the long-only baseline. The mechanism being tested: long exits on this
framework cluster at stops and timeouts (prior work: ~95% of 1H exits were
stops; 4H runner rides ~15 bars) — if post-exit drift continues against the
original direction, a mirrored short leg harvests it.

This is a **systems-comparison** test, not a production proposal. A PASS does
not authorize any change to frozen V5.4, the forward test, entries, exits,
grades, or alerts. Short-signal research was CLOSED 2026-09-17/18 (no short
edge: V1 −0.08R/trade, 2022-bear V2 −0.056R/trade); this test flips AFTER a
long entry rather than shorting signals outright, which is the only reason it
is not redundant with that closure.

## Universe

13 names: QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX, BBAI, NIO,
HOOD, AMD (the 14-stock watchlist minus ASTX).

**ASTX excluded:** it is a 2x daily-reset leveraged ETF on ASTS with no
validated bar data in any local cache, and no prior watchlist backtest study
kept it as a backtested name. A leveraged-reset product would also need its
own decay-aware handling; out of scope.

## Timeframes and data (reuse, no new pipeline)

- **1H:** `pine_1h/cache/h1_*.pkl` (yfinance 1h, regular session, 730d window).
- **4H:** `backtest_cache/h4_*.pkl` (session-aligned 4H via
  `masterscanner_api.download_data(..., "4h", "2y")`).
- **Daily:** `backtest_cache/d1_*.pkl` (via
  `masterscanner_api.download_confirmation_data(..., "1d", "5y")`).

Ticker-timeframes missing from the caches are fetched with the EXISTING
scripts/functions above (no new pipeline): 1H via `pine_1h/fetch_1h.fetch()`,
4H via `masterscanner_api.download_data`, daily via
`masterscanner_api.download_confirmation_data`. Any ticker-timeframe that
fails to fetch cleanly (empty, no volume) is dropped and reported; it does
not block the other timeframes.

Known imperfection (recorded before running): pre-existing caches end
~2026-09-14/17; newly fetched files extend to ~2026-09-25. Per-timeframe
analysis uses each ticker's available bars; all features are strict
point-in-time, so there is no lookahead from the window mismatch.

## Entry (both arms, identical)

- `pine_buy_signal` imported UNMODIFIED from `pine_backtest.py`
  (with `add_pine_indicators`; bar-based lookbacks EMA 9/21/55/200, ATR 14,
  vol SMA 20, breakout 10 — applied as-is per timeframe, i.e. an honest
  unmodified transfer on 1H and daily, not a re-tuned system).
- Signal on completed bar `i` (i ≥ WARMUP = 215). Entry fills at the next
  bar's open (`i+1`).
- Initial stop: `stop_L = signal_close − ATR(14)_signal × 1.5`.
- If entry ≤ stop (gapped below stop): signal skipped (pine convention).
- **Eligibility:** a signal is taken only if at least 61 bars follow the
  signal bar (entry bar + 60), guaranteeing both legs complete inside the
  data. Same signal population for both arms.

## Arm A — long-only baseline

`canonical_baseline.modeb_engine.run_trade` imported UNMODIFIED:
`run_trade(entry_bar_idx=i+1, entry_price=open[i+1], stop=stop_L,
tp1=entry+ATR×2.0, bars_df, scanner_states=None, realistic_gaps=True)`.
Mode B management: 50% at TP1, +1R arms profit-protect (fills next bar open),
runner keeps the structural stop, 30-bar timeout, stop wins ties.
`realistic_gaps=True` (gap-through-stop fills at the open) per the research
convention — the live tracker's at-stop fill is optimistic.

## Arm B — combo (long, then flip short at the long's exit)

1. Long leg identical to Arm A (same entry, same management, same engine).
2. Let `e` = the long leg's exit bar (positional). Short entry:
   `entry_S` = open of bar `e+1`.
3. Mirrored geometry, same risk distance as the long leg:
   `risk_L = entry_L − stop_L`;
   `stop_S = entry_S + risk_L` (stop above entry);
   `tp1_S = entry_S − (tp1_L − entry_L)` (reward distance mirrored below).
4. The short leg is executed by running the UNMODIFIED Mode B engine on the
   price-inverted bar series (`−Open/−High/−Low/−Close`, high/low swapped
   after negation) with `(entry' = −entry_S, stop' = −stop_S, tp1' = −tp1_S)`.
   This is an exact mirror: R multiples, TP1/stop touches, gap fills,
   profit-protect arming (−1R = price 1R below entry), and the 30-bar clock
   are all preserved by the negation (verified algebraically in the run
   script's comments).
5. One combined trade record per signal: `R_total = R_long + R_short`
   (risk distances are equal by construction, so R units are additive).
   If the long leg cannot produce a short entry (cannot happen under the
   60-bar eligibility rule; asserted), the trade is long-only and flagged.

## Costs

50 bps round-trip per leg (BPS = 0.005, the prior-studies headline
assumption), deducted in R terms per leg:
`cost_R_leg = 0.005 / (risk_distance_leg / entry_price_leg)`.
Arm B pays it twice (two legs) — the flip's turnover cost is charged honestly.
Net R per leg = blended_R − cost_R_leg. No cost-sensitivity sweep is required.

## Metrics

Per arm, per timeframe, and pooled (all trades across the three timeframes,
native windows): trade count, expectancy (mean net R/trade), win rate
(net R > 0), profit factor (gross profit R / gross loss R), max drawdown on
the cumulative net-R equity curve in exit-time order, total net R.
Also reported: long-leg-only expectancy inside Arm B (what the flip adds),
short-leg win rate, average bars held.

This is a **trade-level** replay: no portfolio sizing, no position limits, no
overlap handling. It compares systems, not portfolios.

## Pre-registered decision rule

PASS iff ALL of:
1. Arm B expectancy > Arm A expectancy on at least 2 of 3 timeframes
   (a timeframe with <30 trades in either arm is reported for information
   only and does not count toward the 2-of-3);
2. Pooled Arm B expectancy > 0;
3. Pooled Arm B max drawdown ≤ 1.20 × pooled Arm A max drawdown.

Otherwise: FAIL. No partial credit, no re-tuning, no parameter search after
seeing results. A FAIL closes the flip idea alongside the 2026-09-17/18
short-side closure. A PASS qualifies the flip for further research only —
never for production without Mike's explicit approval and a forward paper
overlay.

## Honesty caveats (recorded before running)

- The entry logic was tuned on 4H. 1H unmodified transfer is already known
  ~zero expectancy (2026-09-18 transfer test: +0.009R at 4bps); the flip is
  tested there anyway per the order, comparatively (Arm B vs Arm A).
- Shorting is modeled frictionless: no borrow fees, no hard-to-borrow, no
  dividends, no corporate-action handling beyond adjusted bars. This
  overstates real short-leg economics, especially on hard-to-borrow small
  caps (SMCI, ONDS, BBAI). A PASS would need borrow-cost modeling before any
  production conversation.
- The 60-bar eligibility rule drops late-window signals; both arms share the
  identical population, so the comparison stays paired.
- Pooled metrics mix different native windows per timeframe; per-timeframe
  tables are the primary comparison, pooled is the summary gate.
