# FAILURE MEMORY — QF-TD-CONSTRUCTOR-EQUIVALENCE-PROOF-20261019-43 r1

## Searchable keys

- `TD_CONSTRUCTOR_EQUIVALENCE_PROOF_HOLD__E2_CLEARED_ROUTE_ERROR` — the
  terminal verdict of this task. First failure at E2 fixture F3.
- `VALIDATOR_DAY_ENUMERATION_DST_DRIFT` — NEW. `validate_input.validate`
  enumerates request-window days with absolute 24 h increments
  (`day += pd.Timedelta(days=1)`) on tz-aware America/New_York
  timestamps; after a DST transition the enumerated day key is 01:00
  (spring) / 23:00-prior-day (fall) local instead of midnight, so the
  `by_day.get(day)` lookup against normalized bar-date keys misses and
  the validator false-raises V8 "missing retrieval" for the first open
  session after the transition. Consequence: the cleared TD route as
  shipped (validate_input `1b83cdcd…`) cannot validate any request
  window spanning a DST transition. Observed live at F3 (window
  2025-03-07 → 2025-03-14, session 2025-03-10). Fall-side behavior is a
  static prediction of the same defect class, not an observation (F4
  never ran — first-failure stop).
- Instance record (verbatim): `V8: exchange-OPEN session 2025-03-10 has
  0 bars but 7 constituents are due as of 2025-03-14 16:00:00-04:00;
  missing retrieval (verified open via XNYS calendar)`.

## Closed by this run (evidence, despite the HOLD terminal)

- `DIRECT_PMC_CLOSE_RESOLUTION_OUTSIDE_ARTIFACT_CONTRACT` (-42 B-2) is
  now HALF-closed: the direct-PMC closes are PROVEN equal to the
  qualified artifact over its full coverage (E1 761/761: 524 closes +
  237 closed-date raises). The remaining half is governance only (the
  construction leg still sits outside the reconciled pin chain).
- `CONSTRUCTOR_PRECEDENCE_EQUIVALENCE_UNPROVEN` (-42 B-1) remains OPEN
  and is now sharper: equivalence HOLDS on regular + early-close
  single-day fixtures (F1/F2 byte-identical) and DIVERGES behaviorally
  on DST-spanning windows (cleared route fails at validation;
  resampler has no such gate). F4–F8 cells remain unproven.

## Standing context

- `ORIGIN_START_DAY_ANCHOR_DRIFT` (2026-10-03) — the reason anchor/DST
  semantics are proven, never assumed; this run is that discipline
  working as intended: the frozen DST fixtures caught a real defect
  before any acquired data depended on the route.
