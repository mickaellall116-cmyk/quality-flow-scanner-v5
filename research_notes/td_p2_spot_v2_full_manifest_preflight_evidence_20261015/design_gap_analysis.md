# Design-gap analysis — copied-state v1 → v2 transition (QF-…-05 r1)

Question (spec point 3): can the **unchanged** candidate collector
(`ab254c3`, `b683d277…`) derive a separately versioned v2 state from the
actual SPOT8 v1 state — SPT01–06 reused from durable receipts, SPT07 derived
from its preserved 180-byte rejected evidence under the NL supplement, zero
transport — so the run can proceed to REQ-SPT-08 under the frozen
eight-request manifest?

**Answer: no. The gap is exactly one missing step, proven empirically and
isolated from everything around it.**

## What was proven to work

- Every pin recomputes; the copied state is byte-identical to the original;
  the original was never written (hashes equal before/after).
- SPT01–06 durable receipts revalidate `(True, "ok")` under the candidate's
  own `_verify_receipt` inside a copy (hash/bytes/digest/meta/venue/bar
  revalidation all pass).
- The accepted NL classifier, applied directly to the preserved body
  (`3339c341…`, 180 bytes) + the actual REQ-SPT-07 object, returns a complete
  calendar proof: `2026-07-03: closed`, library `4.5.1`, mechanism
  `1b83cdcd…`, `proof_digest 92621e93…`. Negative controls (tampered body,
  wrong status, no supplement) all return None. **Classification is not the
  gap.**
- Downstream machinery past a `CLOSED_DAY_EVIDENCED` event is complete
  (synthetic control, -04 §2c/2d pattern): restart reuses 6 receipts, counts
  2 evidenced, makes zero transport calls. `_reconcile_started_without_receipt`
  already treats `CLOSED_DAY_EVIDENCED` requests as accounted (never
  AMBIGUOUS, never redispatched). **Restart/reuse is not the gap.**

## The gap (empirical + code)

A fresh `Collector.run()` on the copied v1 state returns
`HOLD (persistent): HTTP 400 for REQ-SPT-07` with **zero transport calls and
zero writes** — lifecycle and pilot-state bytes are bit-identical after the
attempt, and after a second attempt (restart control).

Code path (`td_min_collector.py`, candidate bytes unchanged):

1. `_run_locked()` opens with: if `state["status"] == "HOLD"`, return the
   persistent-HOLD summary immediately — before receipt verification, before
   the evidenced-reuse branch, before any dispatch.
2. `_reconcile_started_without_receipt()` likewise early-returns on HOLD.
3. `_classify_closed_session(req, status, body)` is a pure function whose
   **only caller** is `_handle_response`, i.e. it is reachable exclusively
   with a fresh transport response. No entry point — run path, CLI
   (`validate-manifest` / `preflight` only), or method — re-evaluates
   durable `.rejected.bin` evidence.
4. There is no state-versioning concept: `pilot_state.json` has no version
   field, and no code writes a derivation/provenance record.

Producing a v2 state anyway would require the driver to hand-write a
`CLOSED_DAY_EVIDENCED` event and flip `status` HOLD → ACTIVE — precisely the
hand-edited/fabricated state transition spec point 3 forbids. It was not
done.

## Secondary finding: verification is not read-only

`_verify_receipt` → `_validate_bars` **emits** one `CONSTRUCTION_HOLD`
lifecycle event per 1h receipt (semantics INSUFFICIENT path). A probe copy
showed exactly 6 appends (SPT01–06), pilot-state and receipts untouched. Any
derivation design must treat the lifecycle as append-only-growing even
during verification, and re-verification accumulates duplicate
`CONSTRUCTION_HOLD` events (the v1 lifecycle itself carries one per receipt
from the original run's validation).

## What a future candidate change would need (design only — NOT built here)

1. A derivation entry point under the run lock: for a HOLD state whose
   terminal cause was a rejected response, re-evaluate each preserved
   `.rejected.bin` under the pinned supplement via the existing pure
   `_classify_closed_session`, using the durable `ERROR_EVIDENCE` event's
   recorded sha256/bytes as the body binding.
2. On proof: append `CLOSED_DAY_EVIDENCED` with derivation provenance
   (source body sha, request digest, manifest digest, supplement digest,
   mechanism/library pins, proof digest), write the `.closed_day.bin`
   write-once copy of the same bytes, record the request in a new
   `closed_day_evidenced` state field, and transition the state to a
   versioned v2 ACTIVE — **retaining** the v1 HOLD event and hold record in
   the lifecycle (append-only history), never rewriting them.
3. Credit integrity: SPT07's reservation already stands spent in the v1
   state (`attempts=7`, `credit_reservations=7`); derivation must not
   reserve again, and the run must reach SPT08 with exactly one new
   reservation (total 8).
4. Fail-closed throughout: any conjunct failure (body/hash drift, supplement
   or calendar anomaly, unexpected state shape) leaves the state in its v1
   HOLD form, byte-identical, with the derivation attempt itself recorded.
5. Account for the verification-append behaviour above so derivation +
   restart cycles do not silently multiply `CONSTRUCTION_HOLD` events, or
   explicitly accept and document the duplicates.

Until such a change is separately designed, reviewed, and adopted, the
frozen eight-request manifest cannot be executed past the v1 HOLD state —
neither live nor in rehearsal — and the one-request manifest form cannot
classify a closed-session response (-04). Both execution shapes are
therefore blocked, for different, now precisely documented reasons.
