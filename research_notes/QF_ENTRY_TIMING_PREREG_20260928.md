# QF Entry-Timing Validation — Preregistration (2026-09-28)

Research-only. Frozen/live Quality Flow remains unchanged.

## Question
Do raw 4H Quality Flow entry events themselves identify better entry timing than ordinary bars from the same stocks and market periods?

This deliberately ignores portfolio sizing and exit mechanics so the entry signal can be judged on its own.

## Signal and execution
- Signal: raw QF structural-core event on a completed 4H bar.
- Entry timestamp: next 4H bar open.
- Measure forward stock return and SPY-relative return at 1, 2, 4, 6, 10 and 20 completed 4H bars after entry.

## Matched control
For every symbol-month, draw the same number of **non-QF-event** eligible bars as QF events in that symbol-month.
- 500 fixed random seeds (0-499).
- Same next-bar execution and horizons.
- This controls for the fact that the hand-selected 30-name universe and particular months can have strong drift.

## Required outputs
- QF n, mean/median return, hit rate and SPY-relative mean at every horizon;
- matched-random distribution and one-sided p-value at every horizon;
- year splits, especially 2026;
- symbol concentration at 10 bars;
- 2023 identified as a short partial period, not a full-year validation.

## Interpretation
If QF does not beat matched random bars, the apparent portfolio edge should not be attributed to entry timing.
If QF does beat matched random bars, entry timing is supported independently of the sizing/outlier problem, and research should focus more on risk/exit/portfolio execution than replacing the entry signal.

This remains a 30-symbol surrogate and does not replace the canonical 131-symbol PIT validation.
