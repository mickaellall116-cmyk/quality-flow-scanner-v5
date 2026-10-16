# QF-YAHOO-REV3-VERIFICATION-PIN-SEPARATION-20261016-18 r3 — WORK RESULT

**Verdict: `REV3_VERIFICATION_PIN_SEPARATION_READY`** (candidate only; nothing adopted)
Spec: GitHub Issue #1 comment `6212959600`, fetched first via the public API and followed exactly.
Input pins: r2 commit `5931dbd0fa81f68be903b673fa5773ff1bf8bb06`, r2 candidate sha256 `261a75574cfcc27757ef363af6a5bb1d36f0c37c4b9bbd45740b5f5914772b49`, accepted publisher commit `53bdc672e609791dc55277023dd984cd8727f3c3`.
Elapsed ~15 minutes of the ≤20 cap; **repair minutes: 0**; trials/failures: none (build + fixture passed on first run).

## The defect (from the r3 adjudication)

r2 conflated three pin domains: `final_verification` asserted the container digest must equal "the independent validation pins" (which contain no container digest and no bookkeeping members), and the anchor carried no member pins — its L-05 consumer silently compared members against in-memory `intent["pins"]`, i.e. out-of-band trust that vanishes with the journals/process state.

## What the r3 delta does (programmatic, minimal — 31 leaf changes, 0 outside the allowed set)

1. **`publication_binding.pin_domains`** (new) defines the three domains without overlap:
   - **independent validation pins** — exactly 156 payload rel→SHA-256, produced by the independent validator *before* publication (the `_require_pins` input); never derived from the container; excludes bookkeeping members and the container digest.
   - **sealed member pins** — exactly 158 rel→{length, SHA-256} sealed in the QFJ2 intent record; its 156-payload projection must equal the independent set exactly; the two bookkeeping entries are canonical under the acyclic binding graph.
   - **container pin** — `CONTAINER_SHA256` (trailer digest), publisher-derived, sealed in the QFJ2 intent, verified only by recomputation from the exact fetched blob; belongs to neither pin map.
   - A `non_substitution_rule` forbids cross-domain equalities.
2. **`final_verification` steps 2–3 rewritten**: fetched-container recompute == sealed intent container pin only; parsed 158 members == sealed 158 pins; parsed 156-payload projection == independent pins; commit/tree/blob/ref comparisons unchanged and exact.
3. **Anchor self-sufficiency**: `public_archive_anchor.contents` now includes the exact sealed 158 pin map, the exact independent 156 pin map, and a canonical digest (SHA-256 of canonical JSON) of each map; the role states the consumer needs only the anchor bytes + designated-repo objects — canonical digests make any pin-map alteration detectable. No resolver indirection, no branch-tip trust.

## Fixture (narrow, no-socket; pinned publisher imported read-only) — 11/11 checks, 0 failures, one run

- **P-01** — domains exact/disjoint (independent = 156 payloads only; sealed = 158 = 156+2; container pin is a single digest in neither map); pre-anchor verification receives the independent 156 set *separately* from the QFJ2 sealed 158 pins and proves all three domains; publisher `_verify_remote` transcript cross-check matches the journal published record.
- **P-02** — anchor serialized carrying both pin maps + canonical digests; **both control journals then deleted and all in-memory intent/pin variables discarded**; a fresh consumer given *only* anchor bytes + the fake remote re-verified ref/commit/tree/blob, recomputed the container pin, checked all 158 members against the anchor's sealed map and the 156 projection against the anchor's independent map — PASS.
- **P-03** altered sealed member pin → consumer HOLD. **P-04** missing sealed member pin → HOLD. **P-05** altered independent pin → HOLD.

Accepted corruption/crash/ceiling/concurrency suites not rerun, per spec.

## Preservation proof

Semantic diff (r2→r3) confined to: `publication_binding.pin_domains` (new), `publication_binding.final_verification`, `archive.ledger_objects.public_archive_anchor`, `revision`/`status`/`task` provenance — 31 leaf changes, **0 unallowed**. Named deep-equality checks all pass: 52 requests/order, request params, runtime pins, session-construction freeze, G1–G11, call budget (limiter/ceilings), target repo/ref/path, accepted publisher pin `53bdc672…`, member accounting, archive journals/membership contract.

## Scope confirmation

Offline only (spec fetch the sole network read). Zero authenticated GitHub ops, vendor/model/Yahoo calls, downloads, installs, spend, adoption/merge, capture, publication, backtest/holdout/production changes. U-1 unprobed (HOLD). Evidence base verified byte-identical after the run: r2 candidate `261a7557…`, -17 candidate `fe3611e7…`, -18 r1 memo `01301bb2…`, design r3 `cd9ef36d…`, accepted publisher file `1d4c1923…`, frozen rev2 manifest `634c4541…`. No tracked repo file was modified by this task; the new package is left uncommitted for the main agent's single immutable commit.
