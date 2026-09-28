# QF Pre-Cross Convergence Test — Preregistration (2026-09-28)

Research-only. Frozen/live Quality Flow remains unchanged.

## Motivation
The clean timing study found a small set of QF setups that fired while HEMA was still bearish and then received a bullish HEMA crossover within four 4H bars. Those QF entries performed very strongly, while waiting for the actual crossover entered much later. Because "future crossover within four bars" is lookahead, it cannot be used as a rule.

This test asks whether an **observable pre-cross state at the QF signal** contains the same information.

## Fixed no-lookahead rule
Only consider raw QF events with HEMA20 < HEMA40 on the completed QF signal bar.

Call the state **PRE_CROSS_CONVERGING** when, on that same completed bar:
1. HEMA20 is rising versus the prior 4H bar; and
2. the bearish HEMA gap (HEMA40 - HEMA20) is smaller than on the prior 4H bar.

No threshold, no parameter search, no future bars used in the classification.

All other HEMA-bearish QF events are **BEAR_NOT_CONVERGING**.

## Outcomes
Using the normal QF next-bar-open entry, measure:
- 4-, 6-, 10- and 20-bar stock return;
- SPY-relative return;
- hit rate;
- whether a HEMA bullish crossover occurs within the next four completed 4H bars (diagnostic only, never used for classification);
- MAE/MFE through 10 bars.

## Validation structure
- 2023-2025: discovery/descriptive.
- **2026: primary holdout check.**
- Also report all-period results and symbol concentration.

Use bootstrap confidence intervals for PRE_CROSS_CONVERGING minus BEAR_NOT_CONVERGING at 10 bars, both all-period and 2026 where sample size permits.

## Interpretation
This hypothesis is only useful if the observable convergence state improves QF forward performance without needing the future crossover itself, and the relationship remains directionally favorable in 2026.

A positive 30-symbol result is still only a screening result and requires canonical 131-symbol PIT confirmation before any system change.
