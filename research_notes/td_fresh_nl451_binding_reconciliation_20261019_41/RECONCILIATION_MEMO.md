# RECONCILIATION MEMO — QF-TD-FRESH-NL451-BINDING-RECONCILIATION-20261019-41 r1

Spec: Issue #1 comment 6279832275 (the -40 review's "Next bounded offline
task"). Static / read-only pass; no tests run; no repairs; nothing executed.

## RETURN VERDICT: `FRESH_NL451_BINDING_RECONCILED__NO_RUNTIME_ACTION`

The FRESH chain is already exact and complete at every edge the spec
enumerates — manifest → supplement → collector/driver → validator/calendar
→ lock/environment → readiness executor — with every operative pin
recomputed from committed bytes and matching. No binding is missing and
none conflicts. No runtime action is taken or needed from this pass.

## The FRESH-manifest binding answer (the standing open question)

A FRESH-bound supplement EXISTS and governs the FRESH manifest today:
`fresh_supplement.json` (sha256 `3cbdbf63…`, id
`TD-FRESH-FM-SUPPLEMENT-NL-20261016`, from the -03 fresh full-manifest
preflight). It binds the FRESH manifest digest `71aade8b…` directly, and
its calendar block is the NL451 lineage: PMC **4.5.1**, lock `08b38cfa…`,
mechanism `1b83cdcd…` — field-identical to the -40-accepted NL451
candidate on every operative field. It was derived from that candidate
(`9c712330…`, SPOT8-scoped) by value with only the base binding changed,
exactly the "new supplement version" the -40 adoption record said FRESH
use would need. The conflated 5.5.0 pin exists nowhere in this chain.

## How classification actually binds in the live chain (precisely)

- The live driver (5fed4524…) pins the supplement BYTES (sha `3cbdbf63…`)
  and checks the hash before parsing; it classifies closed sessions from
  the supplement's pre-computed, digest-checked `calendar_proofs` record.
  The driver imports no calendar library.
- The live calendar re-derivation is the GATE's job: gate r4 executes the
  pinned validator's `xnys_schedule` inside the pinned 4.5.1 environment
  and matches the supplement's proof record (Gate 7), after recomputing
  every hash in the chain (Gate 6) and requiring the lock's PMC line to
  read exactly `pandas_market_calendars==4.5.1`.
- The candidate collector's live-mechanism path (version gate :527,
  mechanism-hash gate :531 @ab254c3) is bound into the chain by hash pins
  (driver reconcile :356-357; gate PIN_COLLECTOR) but is not the live
  execution path.
- The readiness executor binds the gate by hash and is fully decoupled
  from the classifier/calendar (zero references) — decoupling by design.

## Findings / scope facts (none is a binding gap; all already recorded in
the chain's own documents, restated here so adjudication sees them in one place)

F1. The FRESH supplement's own `status` is `OFFLINE_CANDIDATE_NOT_ADOPTED`
    — a governance state, identical in kind to the -40 candidate's.
    Adoption remains a separate adjudicated act; this reconciliation does
    not adopt anything.
F2. The supplement's classifier ENTRIES cover REQ-SPT-07/08 only — by
    design: those are the only closed-day (expected-0-bar) requests in
    the 51-request FRESH manifest, and both point at the single
    2026-07-03 proof record.
F3. `pilot_harness/construct_4h.py` (:49-50) imports PMC and calls
    `get_calendar("XNYS")` outside any readiness-chain pin. It is the
    post-acquisition construction component, outside the chain this task
    swept; recorded for awareness. The -40 P8 probe verified the
    registered-XNYS semantics under 4.5.1 that this import relies on.
F4. Labeling clarification: "manifest ef82fb37" in circulation is the r2
    preflight PACKAGE manifest hash, not the manifest file (the file
    hashes to its canonical digest 71aade8b…). No bytes disagree.

## Failures / unknowns

- None encountered. Every pin named in the tasking and every internal pin
  in the chain verified byte-exact. Chain head commit `3932903` verified
  as an ancestor of origin/main. The -20 transaction, ledgers, Policy A,
  and the paused V5.4 harness were not touched (read-only throughout).

## Elapsed / repairs

Elapsed ~17 min of the ≤35 cap. Repair minutes: 0. Attempts: 1.
