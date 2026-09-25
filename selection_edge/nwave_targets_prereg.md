# Pre-registration: N-Wave Price-Target Hit Rates (Ichimoku Price Theory)

Date: 2026-09-25
Ordered by: Mike — "i guess test it" (N-wave V/E/N/NT price targets from the
LuxAlgo "Ichimoku Theories" indicator's Price Theory).
Status: FROZEN before execution. No changes after results are seen. No
re-tuning under any outcome.

## Licensing

Clean-room study. No LuxAlgo code is copied or referenced in the
implementation. The V/E/N/NT projection formulas are classical Ichimoku
(Hosoda) price theory — textbook math, reimplemented from scratch in Python.

## Hypothesis

Developing N-waves project price targets (V, E, N, NT) that are actually
reached often enough, and fast enough, to serve as exit confluence for the
scanner's mechanical exits. The mechanism being tested: N-wave geometry
captures real swing structure, so its measured-move projections should beat
coin-flip arrival within a reasonable window.

This is a **measurement** study, not a production proposal. A PASS does not
authorize any change to frozen V5.4, the forward test, entries, exits,
grades, or alerts. It only answers: "are these levels worth watching as
exit confluence?"

## Universe and timeframes (reuse, no new pipeline)

- 13 names: QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX, BBAI, NIO,
  HOOD, AMD (the 14-stock watchlist minus ASTX — no validated data,
  leveraged ETF, excluded exactly as in the flip-short prereg).
- Timeframes: 1H (`pine_1h/cache/h1_*.pkl`), 4H (`backtest_cache/h4_*.pkl`),
  daily (`backtest_cache/d1_*.pkl`). Same caches validated by the flip-short
  study (2026-09-25). Missing/corrupt files are dropped and reported; they
  do not block other ticker-timeframes.

## Detection rules (exact)

1. **Swings:** confirmed pivot highs/lows, length L=10. Bar i is a pivot high
   iff high[i] == max(high[i-10..i+10]); pivot low iff low[i] ==
   min(low[i-10..i+10]). Ties broken by keeping the earliest bar. The pivot
   is *confirmed* at bar i+10 (no lookahead: nothing is known before then).
   Consecutive same-side pivots are resolved by keeping the more extreme
   (higher high / lower low), so the swing sequence strictly alternates.
2. **Developing N-wave:** on the last three confirmed swings (A, B, C):
   - span: C.bar_index - A.bar_index >= 9 bars;
   - tolerance band T = 0.2 * |A.price - B.price|;
   - bullish: A.price < B.price AND C.price > A.price + T AND
     C.price < B.price - T;
   - bearish: mirror (A.price > B.price AND C.price < A.price - T AND
     C.price > B.price + T).
3. **Detection bar** d = confirmation bar of pivot C (its index + 10).
   Everything measured forward from d is strictly out-of-sample relative to
   the detection.
4. **Targets** (bullish; bearish mirrored by negating displacements):
   - V  = B.price + (B.price - C.price)
   - E  = B.price + (B.price - A.price)
   - N  = C.price + (B.price - A.price)
   - NT = C.price + (C.price - A.price)
5. **Already-hit exclusion:** any target already touched at or before the
   close of bar d is excluded from that event (it is not a forward
   projection). Excluded targets do not enter the hit-rate denominator.

## Measurement rules (exact)

- Window: bars d+1 .. d+30 (30 forward bars). Events whose window would run
  past the end of the series are excluded (incomplete window).
- Touch: bullish — bar high >= target; bearish — bar low <= target.
- Invalidation: bullish — a bar's low < C.price (the C swing extreme)
  before the target is touched; bearish — a bar's high > C.price.
- Per target, independently: scan the window in order; the first of
  {touch → HIT, invalidation → INVALIDATED} wins; neither → MISS. A nearer
  target being hit does not stop measurement of farther targets — each
  target gets its own full-window scan until it is touched or invalidated.
- bars_to_touch: number of bars from d to the touching bar (1..30), recorded
  for hits only.
- Overlapping detections are independent events (each new pivot C forms a
  new (A,B,C) triple, so no dedup needed).

## Metrics

Per target type (V, E, N, NT) × per timeframe × pooled across tickers:
- n measured, hit rate = hits / n, invalidation rate = invalidated / n,
  median bars-to-first-touch (hits only).

## PASS / FAIL (pre-set)

**PASS** only if: at least one of N/NT (the wave-completion targets) has
hit rate >= 60% within 30 bars on at least 2 of the 3 timeframes,
AND its median bars-to-touch <= 15 on those timeframes.
Otherwise **FAIL**. No partial credit, no re-tuning, no post-hoc windows.

## Known limitations (recorded before running)

- Caches end at different dates per ticker-timeframe (see flip_fetch_log.json);
  each series is analyzed over its own available bars.
- Pivot length 10 and the 30-bar window are the indicator's defaults and
  the commissioned spec — they are not tuned here.
- Thin names (DRAM, SPCX: <1y history) contribute few events; pooled rates
  are reported with per-timeframe n so small-sample timeframes are visible.
