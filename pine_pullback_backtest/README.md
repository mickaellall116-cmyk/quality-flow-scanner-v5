# Pullback-entry backtest: does waiting for a retest beat chasing the breakout?

**Date:** 2026-09-24. **Status:** research, local-only. Modifies nothing frozen.
**Origin:** Mike-approved follow-up to the shadowinteltrades reel ("don't chase the
breakout — wait for the pullback to the high-volume level, then enter").

## What was tested

The reel's entry concept, adapted to the 4H system, pre-defined, no tuning:

- The reel uses the Fixed Range Volume Profile **Point of Control** as the pullback
  level. Adapted here as the **signal bar's close** — the level the breakout printed
  from (a volume-profile POC is not available point-in-time in the canonical engine;
  the adaptation is stated explicitly).
- **BASE**: standard Hybrid `pine_buy_signal`, entry at next-bar open, rerun
  in-study (never reuse numbers across studies).
- **RETEST_SKIP (Variant A)**: on a signal, work a limit at the signal bar's close
  for up to 5 bars. Touch (bar low ≤ level ≤ bar high) → fill at the level, stop =
  fill − 1.5·ATR, TP1 = fill + 2.0·ATR (same risk definition as BASE, signal-bar
  ATR). No touch within 5 bars → skip the trade entirely.
- **RETEST_CHASE (Variant B)**: same wait, but if no touch within 5 bars, enter at
  the 5th bar's close with levels recomputed from the actual entry (entry-bar ATR).

## Method

- `pine_backtest.py` imported UNMODIFIED. Signal detection uses the original
  `pb.pine_buy_signal`; only entry timing changes. The Mode B management block
  (TP1 limit intrabar, runner trail after +1R, close-evaluated exits filled at next
  bar open, stop wins ties) is mirrored bar-for-bar in a local helper.
- Universe: 14-stock watchlist (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM,
  SPCX, ASTX, BBAI, NIO, HOOD, AMD). 4H bars, Oct 25 2023 → Sep 23 2026 (same
  cache as prior studies; DRAM/SPCX/ASTX have shorter histories).
- Portfolio: 4bps + 25bps costs, $10k, 1%/trade, max 5 concurrent, 5% risk,
  stop-first ties, gap-below-stop skips.
- Deployment gate: +0.15R at 25bps; a challenger must also beat the incumbent by
  >0.02R to be worth the added complexity.

## Results (pooled, 14 names)

| Variant | Trades | Win% @25bps | Exp @4bps | **Exp @25bps** | PF | MaxDD |
|---|---|---|---|---|---|---|
| BASE (in-study Hybrid) | 237 | 50.6 | +0.290R | **+0.239R** | 1.38 | 21.63% |
| RETEST_SKIP (A) | 235 | 50.2 | +0.312R | **+0.262R** | 1.42 | 22.08% |
| RETEST_CHASE (B) | 237 | 50.6 | +0.323R | **+0.272R** | 1.44 | 24.34% |

- BASE reproduces the mean-reversion study's baseline exactly (237 trades,
  +0.239R @25bps) — the comparison is valid.
- **Attribution (Variant A): 245 signals → 238 filled (97.1%), 7 skipped (2.9%).**
  Variant B: 241 signals → 234 filled, 7 chased late, 0 skipped.

## The surprising part (mechanism analysis)

**On 4H bars, "waiting for the retest" is mostly an illusion — the retest is
already there.** 230 of 238 fills (96.6%) happened on the very next bar; only 8
fills needed bars 2–5. Breakouts on 4H almost always trade back through the
signal close within one bar.

And the entry-price edge vs baseline is **+0.001R — effectively zero**. The
+0.023R expectancy tilt does NOT come from systematically cheaper entries. It
comes from path dependency: nearly-identical entries with slightly different
TP1 levels flip a handful of trades between "TP1 hit" and "stopped" (±1R swings
each). Paired t-test on 229 matched trades: t = +2.13 (nominally p≈0.03) — but
trades are not independent, multiple variants were tried, and the mechanism shows
no entry edge, so this is suggestive at best, not convincing.

The 7 skipped signals (price never came back within 5 bars = strongest momentum)
averaged −0.15R in baseline — curious, but n=7 is meaningless.

## Verdict

1. **The reel is directionally right but practically irrelevant on 4H.** Entering
   at the breakout level instead of chasing the next open is a sound instinct —
   and the current system is *already effectively doing it*, because the retest
   arrives within one bar 97% of the time.
2. **Neither variant clears the bar for a change.** The +0.023R/+0.033R tilts are
   within noise, driven by a handful of path-dependent flips rather than a real
   entry edge. Working limit orders for up to 5 bars adds operational complexity
   (missed fills, gap-down fill modeling flatters the backtest) for no reliable
   gain.
3. **No change to entries.** The frozen breakout entry stands. This joins the
   tested-and-parked list, not the candidate board.

## Files

- `run_pullback.py` — study script (imports `pine_backtest` unmodified)
- `pullback_results.json` — pooled + per-ticker results, attribution
- `README.md` — this file
