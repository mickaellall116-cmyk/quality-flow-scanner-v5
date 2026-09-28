# KAMA Shadow Validation Protocol — Frozen 2026-09-28

Purpose: forward-test the already-selected KAMA20>KAMA40 state on genuinely unseen V5.4 Quality Flow signals without changing signal generation, entry, sizing, ranking, or exits.

## Start
- Shadow cohort starts at **2026-09-28T13:46:00Z**.
- No signals with an earlier signal timestamp are eligible.
- No historical backfill is allowed into the primary forward cohort.

## Frozen KAMA definition
Exactly the research definition:
- KAMA20 and KAMA40.
- Efficiency-ratio window equals the line length.
- Fast smoothing constant = 2.
- Slow smoothing constant = 30.
- State = **BULL** iff KAMA20 > KAMA40 on data available at the signal decision time.
- No slope, gap, crossover, or parameter tuning.

## Logging only
KAMA is observational. It MUST NOT:
- veto or add a QF signal;
- change rank/slot selection;
- change sizing, stop, TP1, exits, or alerts;
- change the V5.4 forward state.

For every eligible live V5.4 signal, record signal_id, symbol, signal time, source, KAMA20, KAMA40, state, validity/warmup, and an immutable hash of the signal-time fields.

## Bar-clock transparency
Historical KAMA research used DST-safe US session buckets (09:30-13:30 and 13:30-16:00 ET). The current production helper can use a different 4H anchor around DST.

Therefore the shadow log records TWO states:
1. **tested_session_state** — KAMA on the DST-safe session-aligned bars used by the corrected research. This is the primary KAMA definition for research continuity.
2. **live_grid_state** — KAMA on the current production 4H grid, diagnostic only.

No choice between these may be made after outcomes are seen. The primary forward read is tested_session_state; live_grid_state exists only to quantify clock disagreement.

## Review point
- Data-quality checkpoint: first 50 eligible signals. No performance verdict and no parameter changes.
- Primary forward cohort: the **first 100 eligible signals** after the start timestamp.
- Freeze those 100 signal IDs when reached.
- Performance review only after all 100 have a resolved V5.4 outcome (or an explicitly documented terminal state under the frozen forward rules).

Primary comparison:
- tested_session_state BULL vs not-BULL on per-signal V5.4 blended R.
- Also report counts, mean/median R, PF where meaningful, win rate, month/episode clustering, symbol concentration, and block/bootstrap uncertainty.
- Keep the all-QF baseline visible; KAMA cannot rescue a core signal that has no independent edge.

## Canonical requirement
Even a favorable 100-signal shadow result does not authorize a live filter. The exact KAMA rule still requires canonical 131-symbol PIT confirmation before changing frozen/live QF.
