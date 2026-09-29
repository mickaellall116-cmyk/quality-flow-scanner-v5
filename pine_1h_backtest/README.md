# 1H backtest — Quality Flow signal logic on Mike's watchlist (2026-09-20)

Owed 1H backtest, delivered. Research only; nothing frozen modified.

## What this is
Unmodified-transfer test: the FIXED canonical `pine_backtest.py` (score fix
a141ca9, Hybrid `pine_buy_signal`) run on 1H bars for the 12 watchlist
tickers (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX, ASTX, BBAI,
NIO). Indicator lookbacks kept in BARS (same as 4H) — ~4x less clock time
per lookback. No parameter tuned for 1H.

Supersedes `pine_1h/` (2026-09-18), which ran on the BUGGY boolean-collapsed
score code — its numbers (+0.009R @4bps / −0.167R @25bps) are invalid.

## Files
- `fetch_watchlist_1h.py` — yfinance 1H fetch (interval=1h, period=730d,
  prepost=False), same convention as `pine_1h/fetch_1h.py`
- `fetch_watchlist_1h_log.json` — fetch log
- `cache/h1_{SYM}.pkl` — 12 symbols, 2023-10-20 → 2026-09-18 (DRAM/SPCX/ASTX
  shorter: listed later)
- `run_1h_watchlist.py` — driver; imports canonical code unmodified; pooled
  stats via `pb.summarize` (identical accounting to corrected 4H baseline),
  per-ticker net R via `pb._outcome`
- `pine_1h_watchlist_results.json` — full results

## Headline (pooled, 649 trades)
- 4bps: win 48.7%, expectancy +0.093R, PF 1.14, return +29.9%, max DD 52.0%
- 25bps: win 47.0%, expectancy −0.020R, PF 0.97, return −30.9%, max DD 59.3%

## Comparator — corrected 4H baseline (Hybrid, UX51, 877 trades)
- 4bps: win 44.9%, expectancy +0.141R, PF 1.21, return +36.3%, max DD 42.3%
- 25bps: win 44.4%, expectancy +0.069R, PF 1.10, return +11.8%, max DD 45.0%

## Verdict
1H underperforms 4H at both costs; negative at realistic 25bps costs.
Misses the +0.15R deployment gate at both costs. The edge does not transfer
to 1H unmodified. Caveat: different universes (12 vs 51 symbols) and
slightly different windows; per-ticker n is small (~50–75), so ticker-level
dispersion is noise.
