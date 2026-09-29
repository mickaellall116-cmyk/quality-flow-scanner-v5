# Mean-reversion entry backtest: "buy the dip to the long-term mean"

**Date:** 2026-09-24. **Status:** research, local-only. Modifies nothing frozen.
**Origin:** Mike-approved follow-up to the Overkill Trading reel (4-year average
line). Adapted to the 4H system, pre-defined, no tuning.

## Signal definitions

- Long-term mean = **200-bar SMA on 4H**, point-in-time (no lookahead).
  - Timeframe adaptation, stated explicitly: on 4H, 200 bars ≈ 100 trading days
    ≈ **5 months, not 4 years**. A true 4-year line would need ~2000 4H bars;
    that history is not available. The reel's exact line is NOT reproduced.
- **MR_GUARD**: bar's low touches/crosses below the 200SMA **and** the bar closes
  back above it (the bounce), **while EMA21 > EMA55** (uptrend intact — the
  value-trap guard). No other entry conditions.
- **MR_RAW**: low ≤ 200SMA and close > 200SMA, **no guard** (pure mean touch).
- **BASE**: standard Hybrid `pine_buy_signal`, rerun in this study.

## Method

- `pine_backtest.py` imported UNMODIFIED; only `pb.pine_buy_signal` monkey-patched
  per variant. Exits = identical Mode B stack, entry = next-bar open, stop =
  signal-bar close − 1.5·ATR (same mechanics for all variants — only *which bars
  fire* changes).
- Universe: 14-stock watchlist (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM,
  SPCX, ASTX, BBAI, NIO, HOOD, AMD). 4H session bars (09:30/13:30 ET), Oct 25
  2023 → Sep 23 2026, resampled from the `pine_2h3h_backtest` 1H cache (same
  cache as the entry-timing study; DRAM/SPCX/ASTX have shorter histories).
- Portfolio: 4bps + 25bps costs, $10k, 1%/trade, max 5 concurrent, 5% risk,
  stop-first ties, gap-below-stop skips.
- Deployment gate: +0.15R at 25bps. Variants judged against the in-study BASE.

## Results (pooled, 14 names)

| Variant | Trades | Win% @25bps | Exp @4bps | **Exp @25bps** | PF | MaxDD |
|---|---|---|---|---|---|---|
| BASE (in-study Hybrid) | 237 | 50.6 | +0.290R | **+0.239R** | 1.38 | 21.63% |
| MR_GUARD | 91 | 41.8 | +0.172R | **+0.127R** | 1.28 | 11.03% |
| MR_RAW (no guard) | 227 | 44.5 | −0.548R | **−0.615R** | 0.41 | 170.94% |

- BASE reproduces the entry-timing study's all-off baseline exactly (237 trades,
  +0.239R @25bps) — the comparison is valid, not a data artifact.
- Signal overlap: 159 guarded mean-reversion bars, 140 of which were NOT
  canonical Hybrid signals (vs 1200 canonical bars). It is a genuinely different
  signal set, not a subset.

## Verdict

1. **MR_GUARD does NOT clear the +0.15R gate** (+0.127R @25bps — misses by
   0.023R) and does NOT beat BASE (+0.239R). Positive expectancy, but not
   deployable on its own. Notable positives: maxDD only 11% (half of BASE's),
   avg hold 10.8 bars (vs 18.6) — a faster, shallower profile. Best per-ticker
   pockets: SOFI +0.727R, AMD +0.536R, QQQ +0.365R @25bps (thin samples).
2. **The guard earns its keep enormously.** MR_RAW is portfolio suicide:
   −0.615R/trade, PF 0.41, maxDD **171%** (equity destroyed; HOOD printed
   −7.9R/trade — gap-downs through the stop on broken names). The EMA21>EMA55
   guard is worth roughly **0.74R per trade**. This is the value-trap warning
   from the reel discussion demonstrated in numbers: buying every dip to the
   mean without a trend guard loses catastrophically.
3. Standing consequence: mean-reversion stays a research candidate, not a
   system addition. The guarded version's low-drawdown profile could make it a
   diversifying second signal type post-verdict, but it needs out-of-sample
   confirmation and does not clear the gate.

## Caveats

- Single backtest, in-sample, 14-ticker universe, thin per-ticker counts
  (2–28 trades per name).
- 200SMA-on-4H ≈ 5 months, not the reel's 4-year line — the adaptation is
  directional, not faithful.
- ASTX backtested as a stock (it is a 2× daily-reset ETF); DRAM/SPCX have
  <1y of history.

## Files

- `run_meanrev.py` — the study script (imports `pine_backtest` unmodified).
- `meanrev_results.json` — pooled + per-ticker stats per variant.
- Reused 4H cache from `../pine_entry_timing_backtest/cache/` (no new download).
