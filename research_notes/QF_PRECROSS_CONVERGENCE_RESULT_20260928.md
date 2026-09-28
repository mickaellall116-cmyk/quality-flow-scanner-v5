# QF Pre-Cross Convergence Result — 2026-09-28

Research-only. Frozen/live Quality Flow remains unchanged.

## Rule tested
Among QF signals that were HEMA-bearish on the completed signal bar, PRE_CROSS_CONVERGING required:
- HEMA20 rising versus the prior 4H bar; and
- the bearish HEMA gap (HEMA40 - HEMA20) narrowing versus the prior bar.

No future bars were used in the classification.

## All-period result
BEAR_NOT_CONVERGING:
- n = 226
- 10-bar mean return = +3.89%
- hit rate = 60.62%
- SPY-relative = +3.35%
- future HEMA cross within 4 bars = 7.08%

PRE_CROSS_CONVERGING:
- n = 43
- 10-bar mean return = +0.14%
- hit rate = 60.47%
- SPY-relative = +0.02%
- future HEMA cross within 4 bars = 6.98%

Converging minus non-converging 10-bar SPY-relative difference:
- -3.33 percentage points
- bootstrap 95% interval: -5.56 to -1.24 percentage points

## 2026 holdout
BEAR_NOT_CONVERGING:
- n = 50
- 10-bar mean return = +4.30%
- SPY-relative = +3.72%

PRE_CROSS_CONVERGING:
- n = 9
- 10-bar mean return = +1.49%
- SPY-relative = +1.92%

Difference:
- -1.80 percentage points
- bootstrap range includes zero because n=9

## Interpretation
The simple no-lookahead HEMA convergence state **does not identify** the strong future-crossover QF subset. It is materially worse than other HEMA-bearish QF setups in the full sample, and it does not validate in 2026.

Therefore the attractive n=19 "QF first, HEMA crosses within four bars" pattern remains a **lookahead description**, not an actionable entry rule.

## Decision
- PRE_CROSS_CONVERGING: FAIL.
- Do not continue threshold-searching the HEMA gap on this 30-name sample; that would become data mining.
- The correct next question is whether the raw QF entry event itself beats symbol/month-matched random timing independently of portfolio sizing and exits.
