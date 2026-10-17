# FUTURE ONE-USE READINESS-EXECUTION PROPOSAL — QF-TD-POLICY-A-LIVE-READINESS-PACKET-20261017-11 r1

## STATUS: NOT AUTHORIZED — PROPOSAL ONLY

This proposal is the exact packet a later, separately accepted adjudication
would clear for the live readiness sequence. Nothing in it is authorized by
the -11 round, by Mike's Policy A ceiling GO (comment 6234434220, a ceiling
decision only), or by this document. It spends **none** of the 52 credits
until a separate execution clearance names it.

## What the future step would authorize — and ONLY this

1. **One** authenticated `GET /api_usage` status request (1 credit), made
   through the pin-bound credential helper via the -08 verified resolver,
   after all preflight pins verify and after the owner lease + ledger lock
   are held (in that order).
2. **Conditional** adoption of the accepted conservative ledger candidate
   (sha256 `79ff4844…`), and only if the fresh Policy A gate-3 evaluation
   PASSes: fsynced exact backup of the legacy ledger first, atomic replace,
   post-write re-read through gate + driver, atomic rollback on any
   post-write failure.
3. Refreeze of the canonical evidence + derived token card, and a 12/12
   gate dry-run against the r4 gate candidate.

## Explicitly EXCLUDED (not part of this proposal under any reading)

- The 51 market-data (`time_series`) requests — the data screen itself.
- Dispatch-token issuance or use; armed transport construction.
- Any second or retry status request; the transaction is one-use and a
  consumed/failed transaction id cannot be re-run.
- Any manifest, policy, ceiling, or pin substitution at execution time:
  drift from the pins below HOLDs before the helper is used.

## Ceilings

- Credits: **1** (status) in this step; the 51 data credits remain unspent
  and require their own later clearance. Day total if both steps were ever
  cleared for the same day: 52 of 800, $0.
- Rate limits: 8/min and 800/day account-shared limiter, unchanged.
- Time: single execution window, evidence freshness 3600 s; stale evidence
  aborts with no retry under the same transaction id.

## Source pins the future clearance must name exactly

| Artifact | sha256 |
|---|---|
| Policy A object (canonical digest) | `5d9d82ca3e1c867e3f38dcb7f50cd7f372c793048d21232608f7835467d26cde` |
| GO record | Issue #1 comment 6234434220, id `QF-TD-POLICY-A-52-CREDIT-CEILING-GO-20261017` |
| r4 gate candidate | `b53996454650dafc77e647a8497eba91beb3785fb52c13d70fa81768fd370117` |
| Readiness transaction wrapper | `7ced79221b0156d4111f7d93e03cc05577eb9c2272d433ae6013335b583b78f3` |
| Gate-3 Policy A candidate (-10) | `7e44a2e0d0a3b32dfd6fb7f93f04a224f935310a6e71dfe06ea83008595eb3f9` |
| Credential resolver (-08) | `c8271193c97713f72b59af2377989362750142eda36940fa0be71cf6de8a911c` |
| Credential helper (sanctioned path) | `8b1f42e80a76710edf0ff2abf8a51b0cde35b06474af865de108a7ca27d6728d` |
| r3 driver candidate (-08) | `b83b97d7f76a4125abfd68dcff77b8efd2ccc7e4cb3fe80d621a8776042c9464` |
| Manifest (51 requests, ordered) | `71aade8bfbb1f94b25d780bdf68f08f7f127740fc745c1755432acc5f74044db` |
| Manifest ordered-sequence digest | `07bb811b0e4092c66ea36172fec8341822c39092c3f05af53a0b26b472b20618` |
| Supplement | `3cbdbf63fd49b021dc74f63727098551753949f8684967981c65f66101f95a86` |
| Legacy source ledger (pre-adoption) | `7e5ccef0e5fd7e2faa744c8fe7ee646c3162fa4f72fc4a9a85317d52b5d890ed` |
| Ledger candidate (adoption target) | `79ff48444d9f05c1272bfbeec2376b8065f4c22dc97b86f657e2ad15495e846b` |
| Bases | commits `b8651a0` (Policy A), `9474400` (-08), `2f312a1` (-07), `0a410ab` (-09) |

## Abort conditions (any one stops the step, fail-closed)

GO record absent/malformed at execution time; any pin drift; manifest
reordered/dropped; locks unavailable; helper origin/hash mismatch; status
response error body, stale (>3600 s), schema-incomplete, wrong tier limits
(not 8/800), counters inconsistent with the ledger, minute capacity
exhausted, or reported daily remaining < 52; backup/fsync/replace failure
(ledger left byte-identical); post-write consumer failure (atomic rollback
to the exact legacy bytes, verified by hash).

## Evidence the future step must return

Terminal transaction record (ordered step log, exactly one status call),
the raw status response preserved, gate-3 verdict, backup hash + adopted
ledger hash (or rollback proof), refrozen evidence digest + derived card,
and the 12/12 dry-run receipt — all committed for independent review before
any token or data-screen step is proposed.
