# V3.7 "Use X as Real Entry" toggle-combination backtest

**Date:** 2026-09-24. **Status:** research, local-only. Modifies nothing frozen.

## What the toggles actually do (read from the V3.7 Pine source)

Source: `~/workspace/goals/masterscanner-v3-6-production-stack-and-live-parity-build/files/Quality-Flow-System-V3.7.pine`, lines 200-207, 224-226.

Critical finding: **the toggles do NOT redefine the entry price or bar.** They add
*extra entry signals* OR'd into `buySignal`:

```pine
sweepBuy    = trendBull and bullSweep and close > ema21 and volumeOK and safeToEnter
fvgBuy      = trendBull and inBullFvgSupport and close > ema21 and volumeOK and safeToEnter
pullbackBuy = trendBull and nearBuyZone and close >= ema21 and adx > 18 and volumeOK and safeToEnter

extraEntry = (usePullbackAsEntry and pullbackBuy)
           or (useFvgAsEntry and fvgBuy)
           or (useSweepAsEntry and sweepBuy)

// Hybrid mode:
buySignal = confirmedBuy or breakoutBuy or readyBuy or extraEntry
```

- There is **no priority order** between the three — pure boolean OR. Each toggle
  gates its own sub-signal independently.
- Entry mechanics (next-bar-open fill, stop = signal-bar close − 1.5·ATR, TP1 =
  entry + 2.0·ATR, Mode B exit stack) are **identical** for extraEntry signals.
  Only *which bars fire signals* changes.
- Definitions ported 1:1:
  - `bullSweep = low < lowest(low,20)[1] and close > lowest(low,20)[1]`
  - `bullFVG = low > high[2]`; `lastBullFvgLow/High` persist (var) until the next
    bull FVG; `inBullFvgSupport = low <= lastBullFvgHigh and close >= lastBullFvgLow`
  - Buy zone = EMA21 ± 0.35·ATR, widened to include a nearby bull FVG
    (`|close − fvgHigh| ≤ 3·ATR and fvgHigh ≤ close·1.08`) — this widening is NOT
    gated by any toggle (per tv_option_audit F3); `nearBuyZone` = within 0.5·ATR
    of the zone edges or inside it.
  - `volumeOK = volume > SMA(volume,20)`; `safeToEnter = not (close > ema9 + 1.5·ATR)`
    (both filters on, matching Mike's live inputs).

## Method

- 8 combos = 2^3 of {pullback, fvg, sweep}; all-off = canonical Hybrid baseline.
- `pine_backtest.py` imported UNMODIFIED; only `pb.pine_buy_signal` is
  monkey-patched per combo to `canonical OR extraEntry(combo)` (same pattern as
  `pine_sensitivity/run_liveconfig.py`). Exits, costs, portfolio sim untouched.
- Universe: 14-stock watchlist (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM,
  SPCX, ASTX, BBAI, NIO, HOOD, AMD). Timeframe 4H, session-aligned bars
  (09:30/13:30 ET), resampled within-day from the `pine_2h3h_backtest` 1H cache
  (same convention as the canonical v3 h4 cache: 2 bars/day, no overnight span).
- Portfolio: 4bps + 25bps costs, $10k, 1%/trade, max 5 concurrent, 5% risk,
  next-bar-open entries, stop-first ties, gap-below-stop skips.
- Deployment gate: +0.15R at 25bps. Combos are judged against the **all-off
  combo run in this test**, not against other studies' numbers.

## Files

- `fetch_resample_4h.py` — builds `cache/h4_{sym}.pkl` from the 1H cache.
- `run_entry_timing.py` — runs all 8 combos, writes `entry_timing_results.json`.
- `entry_timing_results.json` — pooled + per-ticker stats per combo, marginal
  signal attribution per toggle.
