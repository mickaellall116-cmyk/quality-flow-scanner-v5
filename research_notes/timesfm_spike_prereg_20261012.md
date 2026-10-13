# TimesFM spike — PRE-REGISTRATION (written before any run)

Authorized: Mike, main chat, 2026-10-12 22:37 EDT ("Note + run the small test").
Question: does Google's TimesFM (zero-shot) forecast our tickers' prices
better than dumb baselines, out-of-sample, honestly scored?

## Design (frozen by this document)

- Universe: the 14 watchlist tickers (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS,
  DRAM, SPCX, ASTX, BBAI, NIO, HOOD, AMD). Daily bars from Yahoo (yfinance) —
  the feed we already use. NO Tiingo data (compliance hold).
- Task: 1-trading-day-ahead close forecast. Context: prior 256 daily closes.
  Forecast origins: every trading day in the scoring window.
- Scoring window: 2026-04-01 through 2026-10-09 (most recent complete data;
  chosen to sit after TimesFM 2.x's public release to reduce — not eliminate —
  pretraining-contamination. Contamination caveat stands regardless: the exact
  training cutoff is not public, so a PASS here is provisional, not proof).
- Model: TimesFM 2.0 500M checkpoint (google/timesfm-2.0-500m-pytorch) via the
  `timesfm` pip package, CPU inference, point forecast = median/mean output.
- Baselines (same origins, same scoring):
  1. No-change: tomorrow's close = today's close.
  2. Drift: tomorrow's close = today's close × (1 + mean daily return of the
     prior 20 trading days).

## Metrics

- RMSE and MAE of the 1-day close forecast, per ticker and pooled.
- Directional accuracy: fraction of origins where sign(forecast − today)
  matches sign(actual − today). No-change has no direction; excluded there.
- Tradable check: pooled — go long 1 day when TimesFM forecast return > +0.2%,
  flat otherwise; mean return per trade after 25 bps round-trip cost. (A
  forecasting edge that cannot survive costs is not an edge.)

## PASS gate (all three required; set before the run, will not move)

1. Pooled RMSE at least 5% lower than the no-change baseline's RMSE.
2. Directional accuracy ≥ 53% pooled.
3. Tradable check mean per-trade return > 0 after 25 bps costs.

Anything else is FAIL. A FAIL closes the idea (no retuning of horizon,
context, threshold, or universe against this data). A PASS earns only a
proposal for a second, harder test — never production use.

## Budget and bounds

One run, ~1 hour wall-clock. Local CPU only, no purchases, no vendor API
calls beyond the Yahoo bars we already pull. Results (pass or fail) are
recorded verbatim; adverse results are evidence and stay.

— Muse, 2026-10-12
