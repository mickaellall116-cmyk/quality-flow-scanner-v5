# KAMA Portfolio Warmup Correction — Preregistered Mechanical Fix

The prior KAMA portfolio screen included QF signals before the frozen 215-bar research warmup was complete. On those early bars KAMA/RS history could be unavailable, and missing KAMA was implicitly classified as not bullish.

Correction only:
- both baseline and KAMA-filter variants ignore QF signals with signal-bar index < 215;
- all other KAMA definitions, portfolio rules, costs, ranking, exits and risk limits remain unchanged;
- no retuning or new condition is allowed.

Report the same 25/50/75/100 bps outputs, with 50 bps primary.
