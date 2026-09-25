# Test Report: N-Wave Price-Target Hit Rates (Ichimoku Price Theory)

Date: 2026-09-25. Ordered by: Mike ("i guess test it").
Prereg: `selection_edge/nwave_targets_prereg.md` (commit `41a1229`,
frozen before execution). Verdict: **FAIL**.

## What ran

Clean-room Python (`selection_edge/nwave_targets_run.py`) — no indicator
code copied; textbook Hosoda V/E/N/NT formulas reimplemented from scratch.
Developing N-waves detected on confirmed pivot-10 swings (last 3 swings,
span >= 9 bars, 0.2*|A-B| tolerance band), targets projected at detection,
then measured over the next 30 bars: touch = HIT, C-swing-extreme violation
first = INVALIDATED, neither = MISS. Same-bar touch+violation resolved as
invalidation (conservative vs the hypothesis). Targets already touched by
the detection bar excluded (not forward projections).

Universe: 13-name watchlist × 1H / 4H / daily, reusing the validated caches
from the flip-short study. 1,471 detections total, zero data errors.

## Results (pooled across tickers)

Hit rate within 30 bars | n measured | median bars to first touch (hits)

| TF    | V                 | E                | N                  | NT               |
|-------|-------------------|------------------|--------------------|------------------|
| 1H    | 22.8% (250, 11)   | 8.5% (330, 14)   | 18.7% (246, 14.5)  | 23.5% (98, 9)    |
| 4H    | 21.0% (81, 7)     | 5.9% (102, 13)   | 24.4% (78, 10)     | 38.9% (18, 8)    |
| daily | 21.6% (102, 16)   | 5.7% (141, 9.5)  | 15.2% (99, 14)     | 25.0% (20, 8)    |

Invalidation rate (C extreme broken before target): 37–44% on every
target × timeframe — the setup's own structure fails about two times in
five before any projection can arrive. The farthest target (E) is reached
only ~6–8% of the time: essentially never. NT's best reading (38.9% on 4H)
is on n=18 — small-sample noise, and NT is the nearest target so it
*should* hit most often.

## PASS / FAIL

Pre-set bar: N or NT >= 60% hit rate on >= 2 of 3 timeframes with median
bars-to-touch <= 15. Best N/NT reading anywhere: 38.9% (4H NT, n=18).
**FAIL** — not close on any timeframe.

## Practical read

These projections miss roughly four times out of five, and the pattern's
own swing extreme breaks first ~40% of the time. As exit confluence they
would add noise, not edge: a level that arrives 15–25% of the time is a
distraction on the chart, not a magnet. Recommendation: keep the indicator
as a context toy (Kumo regime read) per the earlier guidance, and do not
use V/E/N/NT levels for exits, TP placement, or confluence. No follow-up
tuning — the FAIL stands as pre-registered.

## Implementation note

One transcription slip (bearish NT mirror formula) was caught in the
single-series smoke test and fixed *before* the full run; the frozen
prereg's "bearish mirrored" rule is what executed. No post-result changes.
