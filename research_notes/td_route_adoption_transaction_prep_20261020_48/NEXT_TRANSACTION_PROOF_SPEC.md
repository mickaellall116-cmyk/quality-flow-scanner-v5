# NEXT TRANSACTION-PROOF SPEC (smallest) — returned under task -48 r1 §5, NOT executed

Purpose: prove, offline and before any adoption designation, that the candidate
chain in this package behaves identically to the accepted r4 chain wherever the
two must agree, and correctly wherever the route changed (validator candidate).
One offline attempt per element; first failure stops; zero repairs.

## P0 — static re-verification (prerequisite, no execution)
- Recompute every pin in ROUTE_MANIFEST_CANDIDATE.json and dag.json against
  committed bytes (the -48 linter, extended to run against the committed
  package). All must match; supplement file must be canonical bytes.

## P1 — readiness-chain offline regression (gate/adapter/executor candidates)
- Run the candidate gate's OWN trial suite shape (the r4 trials pattern,
  incl. F12 Gate-7 mechanism agreement) against the candidate files at their
  package paths, in the pinned wheelhouse environment, network-denied:
  - Gate 5/6/7 must PASS with PIN_MECHANISM == ca3bafd8… and
    PIN_CALENDAR_PROOF == 6b030c62… (Gate 7 re-derives closed 2026-07-03 via
    the candidate validator's xnys_schedule and matches the re-keyed proof).
  - The full -19 clock/path/placement/txn regression matrices re-run against
    the candidate adapter+executor pair; outcomes byte-identical to the r4
    matrices except fields that legitimately name the new pins/revision.
- The original validator (1b83cdcd…) run of Gate 7 must produce the same
  derivation facts (closed_2026_07_03 true, closed_2026_07_02 false,
  pmc_version 4.5.1) — a mechanism-equivalence spot check on the exact
  Gate-7 dates, complementing E1's 761/761.

## P2 — driver classification regression (driver candidate)
- The -04 driver trial suite re-run against live_driver_r5_candidate.py +
  fresh_supplement_v2_candidate.json: reconcile_supplement accepts the
  candidate supplement (id/status/base binding/proof digests), the byte pin
  accepts only 55ad6f40…, and classify_closed returns the NEW proof digest
  6b030c62… on the preserved REQ-SPT-07-shaped closed response, None on every
  negative control, exactly as the original pair behaved with 36bc3a89….

## P3 — route leg (already proven; binding confirmation only)
- No re-run of E1/A/D/B/C (accepted: commits 01af2fee, d0fef7c/8cd6b8f,
  ce1adf5/df9b1de). Static confirmation that the entrypoint candidate's
  loaded validator/constructor bytes are ca3bafd8…/d47e8df1… at their
  committed paths (the -46 Family A binding method, read-only).

## P4 — open governance requirements (must be closed by the TRANSACTION, not P0–P3)
- REQ-CLI: produce either (a) a CLI-refusing constructor candidate + a
  fixture proving direct CLI invocation fails closed while the entrypoint
  path succeeds, or (b) an adjudicated deployment-terms record that the
  adopted route exposes no direct-constructor path. Adoption may not be
  designated while REQ-CLI is open.
- REQ-S2: the 4H assembly component implementing the D-1..D+1 split
  exclusion (bars AND candidate entries, recompute, no imputation) is a
  separate future candidate + proof; the adoption transaction for THIS
  chain neither implements nor waives it — it binds data production only,
  and no corrected-performance use may start until REQ-S2 is proven.

## Terminal labels (proposed)
- TD_ROUTE_TRANSACTION_PROOF_PASS__ADOPTION_DESIGNATION_READY
- TD_ROUTE_TRANSACTION_PROOF_HOLD__<first-failure-key>

## Explicitly out of scope for the proof
Any live designation, vendor/API call, credit spend, real market data,
SPT-08 dispatch, holdout access, performance/backtest work, production or
ledger/state change, Issue #9, Yahoo work.
