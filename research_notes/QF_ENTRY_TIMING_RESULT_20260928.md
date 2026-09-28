# QF Entry-Timing Validation Result — 2026-09-28

Research-only. Frozen/live Quality Flow remains unchanged.

## Design
Raw 4H QF structural-core events were entered at the next 4H open and measured independently of portfolio sizing and exits. Each symbol-month was compared with 500 random draws containing the same number of non-QF bars from that same symbol/month.

Warmup: 215 bars.

## Main result
QF:
- n = 280
- 10-bar mean return = +2.28%
- 10-bar median return = +0.97%
- 10-bar hit rate = 56.79%
- 10-bar mean SPY-relative return = +1.97%

Matched random:
- mean 10-bar SPY-relative return = +1.14%
- 95% random range = +0.17% to +2.20%
- one-sided p(random >= QF) = 0.064

Interpretation: QF shows a **suggestive but not conventionally significant** 10-bar entry-timing advantage versus symbol/month-matched random bars. The result is stronger than the HEMA bullish crossover, which failed its matched-random test.

## Other horizons
QF versus matched random SPY-relative mean:
- 1 bar: +0.064% vs +0.069%, p = 0.537
- 2 bars: +0.087% vs +0.221%, p = 0.743
- 4 bars: +0.228% vs +0.484%, p = 0.798
- 6 bars: +0.966% vs +0.716%, p = 0.277
- 10 bars: +1.971% vs +1.142%, p = 0.064
- 20 bars: +2.641% vs +2.192%, p = 0.250

The possible QF timing edge appears most clearly around the 10-bar horizon rather than immediately after entry.

## By year
2024:
- n = 92
- 10-bar SPY-relative = +1.11%

2025:
- n = 111
- 10-bar SPY-relative = +2.40%

2026:
- n = 77
- 10-bar SPY-relative = +2.39%

The direction is positive in all three full calendar years represented in the recent sample.

## Concentration diagnostic
The 10-bar QF excess return is meaningfully concentrated in high-beta names.

Removing the highest total-contribution symbols:
- remove top 1 symbol: +1.65% mean excess
- remove top 3 symbols: +1.04%
- remove top 5 symbols: +0.55%
- remove top 10 symbols: -0.21%

Removing the best individual events:
- top 1 removed: +1.71%
- top 3 removed: +1.30%
- top 5 removed: +0.97%
- top 10 removed: +0.31%
- top 20 removed: -0.46%

So the signal is not one-trade-only, but it is still strongly dependent on the best symbols/events.

## Decision
- The raw QF entry is **more promising than HEMA as an entry-timing signal** on this sample.
- Evidence is suggestive, not definitive (matched-random p ≈ 0.064 and substantial concentration).
- Do not replace or delay QF entries with HEMA.
- Future improvement work should preserve the QF entry core and concentrate on robust risk controls, portfolio construction, and independent sources of information.
- Canonical 131-symbol PIT confirmation is still required before changing the frozen/live system.
