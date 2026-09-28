# Position-Sizing Constraint Test — Preregistration (2026-09-28)

Research-only. Frozen/live Quality Flow signal logic remains unchanged.

## Trigger
The DST-corrected 30-symbol surrogate exposed pathological position sizing when a structural stop is extremely close to the next-bar fill. The documented portfolio simulator sizes shares as risk budget divided by entry-minus-stop and has no capital-availability constraint.

## Primary rule (chosen from risk mechanics, not historical return)
**NO_LEVERAGE_1PCT_STOP**
- Keep the structural stop unchanged.
- Reject an entry when the actual next-bar fill is less than **1.00%** above its structural stop.
- Otherwise size from the existing 1% equity risk budget, but cap entry notional at **100% of current equity**.
- Do not widen the stop to make a trade qualify.
- Use actual capped shares when computing planned dollars-at-risk and heat.
- Existing QF entries, rs ranking, max-six slots, 5% heat, TP1, Profit Protect, timeout, next-bar execution, and gap-stop handling remain unchanged.

Rationale: with a 1% risk budget, a 1% stop naturally corresponds to approximately 1.0x book notional. This prevents the extreme leverage created by sub-1% stops without selecting a threshold from the best historical outcome.

## Predeclared sensitivity checks
These are diagnostics, not candidates to choose by whichever backtests best:
- RAW: no notional cap, no minimum stop.
- NO_LEVERAGE_1PCT_STOP: 1.0x book cap, 1.00% minimum stop (primary).
- HALF_BOOK_1PCT_STOP: 0.5x book cap, 1.00% minimum stop.
- NO_LEVERAGE_2PCT_STOP: 1.0x book cap, 2.00% minimum stop.

## Costs
Run 25, 50, 75 and 100 bps round trip.

## Required outputs
For every scenario:
- accepted/closed trades and rejected-tight-stop count;
- cap-bind count;
- missing-RS accepted count;
- total net R, net expectancy, PF, win rate;
- marked portfolio return and maximum marked drawdown;
- results by year, including 2026;
- top-1/3/5/10 removal;
- result excluding APLD 2024-01-03;
- stop-distance and notional/equity diagnostics.

## Interpretation
The purpose is to determine whether the apparent edge survives basic executable risk constraints. A result is not considered robust if it disappears after removing a few trades or only survives through leverage that exceeds the declared cap.

This remains a 30-symbol recent-history structural-core surrogate, not the canonical 131-symbol PIT test.
