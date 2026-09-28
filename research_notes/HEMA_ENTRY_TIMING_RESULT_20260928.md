# HEMA Entry-Timing Result — 2026-09-28

Research-only. Frozen/live Quality Flow remains unchanged.

## Study A — standalone 4H bullish crossover
DST-safe 30-symbol recent-history sample, next-4H-open execution.

HEMA 4H bullish crossover:
- n = 1,054
- 10-bar mean return = +1.895%
- 10-bar hit rate = 55.31%
- 10-bar mean SPY-relative return = +1.314%

EMA20/40 bullish crossover control:
- n = 425
- 10-bar mean return = +2.027%
- 10-bar hit rate = 55.53%
- 10-bar mean SPY-relative return = +1.295%

Symbol-month matched random non-HEMA bars:
- mean 10-bar SPY-relative return across 500 matched draws = +1.557%
- 95% random range = +1.029% to +2.108%
- one-sided p(random >= HEMA) = 0.792

Interpretation: the 4H HEMA bullish crossover looks good in absolute terms, but it does **not** beat matched random bars from the same symbols/months and is essentially tied with the simpler EMA20/40 crossover. Much of the visual attractiveness is consistent with the bullish stocks/periods in which the signal occurs rather than unique crossover edge.

The 2026 HEMA crossover result is notably weaker:
- n = 257
- 10-bar mean return = +0.473%
- hit rate = 45.14%
- SPY-relative = +0.058%

## Study B — same QF setup, normal entry vs waiting for HEMA
Raw QF 4H events were split by HEMA state at the QF signal.

QF already HEMA-bullish:
- n = 113
- 10-bar mean return = +2.73%
- SPY-relative = +1.66%

QF HEMA-bearish, no bullish cross in next 4 bars:
- n = 248
- 10-bar mean return = +2.40%
- SPY-relative = +1.97%

QF HEMA-bearish, bullish HEMA cross within next 4 bars:
- n = 19
- baseline QF next-bar entry mean 10-bar return = +15.26%
- hit rate = 94.74%
- SPY-relative = +14.33%

For those same 19 setups, **waiting for the HEMA crossover made the entry much worse**:
- mean delay = 3.26 4H bars
- delayed entry price was ~7.39% higher on average
- baseline common-terminal return = +15.26%
- HEMA-delayed common-terminal return = +6.10%
- paired difference = -9.16 percentage points
- paired bootstrap 95% interval = -12.98 to -5.71 percentage points

Interpretation: in this small subset, QF was early and HEMA crossed only after the move had already started. This is a plausible reason the crossover looks excellent visually while failing as an entry gate: it often acts as **confirmation of a move already underway**, not as the earliest actionable entry.

The n=19 future-cross subset is too small and uses future information for classification, so it is **not** an actionable rule. The next legitimate question is whether an observable pre-cross state at the QF signal (HEMA gap narrowing / HEMA20 rising while still bearish) can identify those setups without lookahead.

## Current decision
- HEMA hard gate: FAIL.
- Small-green entry requirement: FAIL.
- HEMA crossover as standalone entry edge: NOT SUPPORTED versus matched random / EMA control.
- Waiting for HEMA crossover after QF: FAIL; materially later/worse entry in the paired subset.
- Pre-cross convergence at QF time: untested hypothesis; requires a no-lookahead test.
