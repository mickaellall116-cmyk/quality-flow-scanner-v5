# Decision-Time Availability Audit — Amendment 4

Status: FROZEN GOVERNANCE / FAILURE-MODE CONTROL
Date: 2026-09-25
Builds on original framework + Amendments 1–3.
Purpose: close Claude combined-framework findings N-7 through N-10.

No V5.4, ERD v0.1, production logic, or killed-family change.

## 1. READY gate always follows latest frozen test suite (N-7)

Any historical wording that names a fixed subset such as "T1–T13" is superseded.

Framework specification may be called READY only when:
- every test required by the latest frozen amendment has passed;
- superseded tests are evaluated under their latest frozen semantics;
- no unresolved CRITICAL or MATERIAL audit finding remains.

Current required suite is:
- T1 through T14;
- T2C;
- T15;
with T12 evaluated under Amendment 3 §3 and T14 under Amendment 3 §1.

Future amendments automatically extend or revise this list; READY always points to the version-controlled current suite, never to a stale historical enumeration.

## 2. Independent preregistration anchor and commit-integrity rule (N-8)

Git commit dates alone are not accepted as proof that a preregistration existed before performance inspection.

For every family availability manifest, before the first performance artifact is generated:

1. Commit the machine-readable manifest and record:
   - repository;
   - branch;
   - commit SHA;
   - manifest path;
   - manifest content SHA256;
   - framework/amendment version.

2. Publish an independent anchor message outside the manifest commit itself containing the exact commit SHA and manifest SHA256. The standing GitHub Issue #1 research bridge is the minimum accepted anchor because its issue-comment record is separately timestamped from the manifest commit and already serves as the project’s coordination ledger. An external mail/thread timestamp or third-party timestamp service may be added but is not required.

3. The replay artifact must embed the anchored manifest SHA256 and anchor reference/ID. A replay lacking a valid pre-result anchor is non-confirmatory.

4. If repository branch protection/no-force-push is available, enable it for the branch holding frozen manifests. However, branch protection is defense-in-depth, not the sole provenance proof. The independent anchor remains mandatory.

5. Signed commits are permitted as additional evidence but are not required if the independent anchor is present. A signature authenticates a commit; it does not by itself prove that the commit predated performance inspection.

6. History rewrite, force-push, branch recreation, or manifest replacement after anchoring cannot silently preserve confirmatory status. The anchored SHA/manifest hash must still resolve to the exact committed content referenced by the replay. Any mismatch = provenance FAIL.

### T15 — provenance-anchor tamper test

Create a frozen manifest M1, commit it, and publish its independent anchor with commit SHA H1 and manifest SHA256 S1.

Then simulate one of:
- replace manifest content on rewritten history;
- point the branch at a new commit with altered manifest;
- create a new manifest with an earlier-looking commit date;
- delete/recreate branch history.

Expected:
- replay validation checks anchor reference + H1 + S1;
- if current/reconstructed content does not match anchored S1 at H1, confirmatory provenance fails;
- a new dated amendment may create H2/S2, but it does not rewrite or erase H1/S1 or reset multiple-testing history.

The test validates detectability, even where repository permissions do not technically prevent force-push.

## 3. Corporate-action numerical tolerance is frozen (N-9)

Add required manifest field:

`corporate_action_float_tolerance`

Rule:
- default = exact/bitwise equality where the implementation is deterministic;
- if nonzero tolerance is technically necessary, the manifest must state the exact absolute and/or relative tolerance, numeric datatype/library context, and justification before performance inspection;
- the tolerance may cover floating-point serialization/rounding only;
- it may not be selected based on whether a future-corporate-action invariance test passes.

T12 fails if any pre-T difference exceeds the frozen tolerance.

## 4. Minimum evidentiary bar for vendor delivery sequence and matching fallback (N-10)

### Vendor-native delivery sequence

A field qualifies as a historical delivery-order field only if at least one frozen source of evidence explicitly describes it as ordering publication, transmission, delivery, update sequence, or vendor-version chronology for the specific feed used.

Accepted evidence:
- vendor API/schema documentation;
- vendor data dictionary/specification;
- written vendor support statement retained as an artifact;
- captured feed protocol documentation.

Not accepted:
- lexicographic ordering of IDs/hashes;
- row order in downloaded files;
- local ingestion order alone;
- monotonic-looking values inferred from the historical sample;
- researcher judgment based on observed performance.

The evidence artifact/reference and interpretation are frozen in the manifest.

If no qualifying evidence exists, same-timestamp conflicting versions remain AMBIGUOUS_CONFLICT and unavailable.

### Sparse-stratum fallback

The missingness-placebo sparse-stratum fallback must be fully specified before results in the family manifest:
- minimum observations per stratum;
- exact deterministic merge order for sparse strata;
- maximum allowed merge distance/breadth;
- whether sector is dropped before size/liquidity strata are broadened;
- hard condition under which matching is declared infeasible and status becomes REVIEW.

No fallback may be invented interactively after observing actual placebo outcomes.

## 5. Human-influence limitation

Preregistration cannot mechanically prove that a human was never influenced by a prior failed run.

Therefore:
- any post-REVIEW design amendment stays in the same family_id;
- prior inspected results remain in the family ledger;
- the reason for each amendment must be recorded without deleting earlier versions;
- independent adversarial review remains required before a revised design can regain confirmatory status.

This is treated as an irreducible governance limitation, not as evidence that the statistical framework itself is invalid.

## 6. Current framework gate

At the specification level, the framework may be called READY only after:
- an independent auditor confirms no unresolved CRITICAL/MATERIAL specification gaps remain;
- Amendments 1–4 are frozen;
- the current required test suite definition is internally consistent.

At the implementation level, no candidate receives an availability PASS until:
- the complete latest test suite passes;
- its family manifest is complete;
- its manifest is independently anchored before performance;
- all candidate-specific PIT/provenance/missingness controls pass.

Specification READY is not implementation PASS and is not an economic trading PASS.
