# HEMA Entry-Timing Test — Preregistration (2026-09-28)

Research-only. Frozen/live Quality Flow remains unchanged.

## Goal
Separate two questions that prior HEMA tests mixed together:

1. Does the HEMA bullish crossover ("big blue"/big green) itself contain entry-timing information?
2. For an already-valid Quality Flow setup, does waiting for a nearby HEMA bullish crossover improve the entry price/path?

This is **not** another HEMA hard-gate test.

## Dataset
Use the same DST-safe 30-symbol recent-history 4H research set already used in the HEMA work. This remains a surrogate, not the canonical 131-symbol PIT dataset.

## Study A — standalone crossover timing
Signal: completed 4H HEMA20/40 bullish crossover.
Execution timestamp: next 4H bar open.
Measure forward stock return and SPY-relative return at 1, 2, 4, 6, 10 and 20 completed 4H bars after entry.

Controls:
- ordinary 4H EMA20/40 bullish crossover, same next-bar execution;
- symbol-month matched random non-event bars. Each random draw preserves the number of HEMA events in every symbol-month bucket. Fixed seeds 0-499.

Report:
- n, mean, median and hit rate at every horizon;
- SPY-relative mean at every horizon;
- year splits;
- concentration by symbol at 10 bars;
- matched-random percentile / one-sided p-value for mean 10-bar SPY-relative return;
- HEMA versus EMA descriptive difference.

No HEMA length search and no alternate crossover window search.

## Study B — QF entry timing, same setup
For every raw 4H QF event:

Baseline:
- enter next 4H open.

Actionable HEMA-wait subset:
- only examine QF signals where HEMA is **not bullish** on the QF signal bar;
- look forward at most four completed 4H bars for the first HEMA bullish crossover;
- if one occurs, the alternative entry is the open of the next 4H bar after that crossover;
- if none occurs within four bars, label the setup "no nearby cross" and do not pretend it was improved.

For the subset with a crossover, compare baseline entry versus delayed HEMA entry using the **same terminal close** 10 QF bars after the original QF signal. Also report entry-price improvement, MAE and MFE over the common remaining window.

This paired subset answers whether HEMA improves timing for the same QF setup. It does **not** by itself justify skipping the no-cross setups.

Also report raw QF forward returns by HEMA state at signal:
- HEMA already bullish;
- HEMA bearish with crossover within next 4 bars;
- HEMA bearish with no crossover within next 4 bars.

## Decision standard
HEMA timing is interesting only if:
- standalone crossovers beat matched random bars and are at least competitive with the simpler EMA crossover;
- paired QF waiting improves the same setups on a meaningful sample, not just a few outliers;
- results are not confined to the short 2023 tail or one/two symbols.

Any positive result remains research-only and still requires canonical 131-symbol validation before a system change.
