# 2H/3H backtest — Quality Flow signal logic on Mike's CURRENT 14-ticker watchlist (2026-09-23)

Research only; nothing frozen modified. Parked per 2026-09-23 agreement
(Mike: "Why not" → added to post-verdict research list; freeze holds).

## What this is
Unmodified-transfer test: the FIXED canonical `pine_backtest.py` (score fix
a141ca9, Hybrid `pine_buy_signal`) run on 2H and 3H bars for the current
14-ticker watchlist (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX,
ASTX, BBAI, NIO, HOOD, AMD). Indicator lookbacks kept in BARS (same as 4H).
No parameter tuned for 2H/3H.

yfinance serves no 2h/3h interval, so 1H bars (interval=1h, period=730d,
auto_adjust=False, prepost=False, regular session only) were resampled with
pandas WITHIN each trading day — no bar spans the overnight gap. Bins
anchored at the 09:30 session open per day (2H: 09:30/11:30/13:30/15:30;
3H: 09:30/12:30/15:30); the final 15:30–16:00 stub bar of each day is kept.
OHLCV: first Open, max High, min Low, last Close, sum Volume. Symbols with
<200 resampled bars fail closed (excluded) — none hit the floor.

## Files
- `fetch_watchlist_1h.py` — yfinance 1H fetch for the 14 tickers
- `fetch_watchlist_1h_log.json` — fetch log
- `cache/h1_{SYM}.pkl` — 14 symbols, 2023-10-25 → 2026-09-23
  (DRAM from 2026-04-02, SPCX from 2026-06-12, ASTX from 2025-07-11)
- `run_2h3h_watchlist.py` — driver; resample + canonical code unmodified;
  pooled stats via `pb.summarize`, per-ticker net R via `pb._outcome`
- `pine_2h3h_watchlist_results.json` — full results

## Headline

### 2H (pooled, 505 trades)
- 4bps: win 47.7%, expectancy +0.125R, PF 1.19, return +48.3%, max DD 49.0%
- 25bps: win 46.9%, expectancy +0.052R, PF 1.07, return +3.0%, max DD 54.8%

### 3H (pooled, 371 trades)
- 4bps: win 51.8%, expectancy +0.221R, PF 1.35, return +93.7%, max DD 34.9%
- 25bps: win 50.7%, expectancy +0.158R, PF 1.24, return +55.8%, max DD 39.3%

## Comparison
| TF | exp @4bps | exp @25bps | gate +0.15R @25bps |
|----|-----------|------------|--------------------|
| 1H (649 trades, 12 sym) | +0.093R | −0.020R | miss |
| 2H (505 trades, 14 sym) | +0.125R | +0.052R | miss |
| 3H (371 trades, 14 sym) | +0.221R | +0.158R | **pass (barely)** |
| 4H corrected baseline (877 trades, UX51) | +0.141R | +0.069R | miss |

## Verdict
2H improves on 1H at both costs but misses the gate at realistic 25bps
costs. 3H clears the +0.15R gate at 25bps — but only just (+0.158R), on a
small 14-ticker universe with ~30–50 trades per ticker, and it still trails
the question of whether it beats 4H on the same universe (not tested).
Per-ticker n is small; ticker-level dispersion is noise — do not optimize
per ticker.

## Data flags
- SPCX: 283 bars (2H) / 213 bars (3H) — technically clears the 200-bar
  floor, but produced 3 trades (2H) / 0 trades (3H). Effectively no signal;
  consistent with the live fail-closed handling. Treat as no-data.
- DRAM: 480/360 bars, 6/3 trades — noise-level sample.
- ASTX is a 2x daily-reset leveraged ETF, backtested here as if it were a
  stock (same simplification as the 1H run); its numbers are not comparable
  to single-stock names.
- Caveat shared with the 1H run: different universe (14 watchlist names vs
  51-symbol UX51) and window vs the 4H baseline; not an apples-to-apples
  timeframe comparison.
