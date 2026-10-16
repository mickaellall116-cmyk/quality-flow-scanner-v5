# Rev3 manifest ledger separation (-18 r2) — candidate only

**Task:** QF-YAHOO-REV3-MANIFEST-LEDGER-SEPARATION-20261016-18 r2 (spec: Issue #1 comment 6211520590, fetched and followed exactly)
**Verdict: REV3_LEDGER_SEPARATION_READY** (candidate only — nothing adopted, merged, captured, or published)

## What was wrong (the two defects from the r1 review)

1. **Control-file membership conflict:** the -17 candidate (fe3611e7…) placed the local acquisition attempt ledger under the capture root, while the accepted publisher's census rejects every capture-root entry except `raw/`, `actions/`, `meta/`, and optional canonical `manifest.json` / `SHA256SUMS` (`HOLD:MEMBERSHIP`).
2. **Public-anchor circularity:** `publication_binding.final_verification` required the fetched container digest to "equal the ledger anchor" *before* the sequence's own final step created that anchor. Verification compared against a thing that did not exist yet, and the anchor had no single named location in the candidate.

## The separation (new candidate, built programmatically from fe3611e7…)

Three distinct objects, exact names/locations/roles, defined in `archive.ledger_objects`:

- **`acquisition_attempt_journal`** — fsync'd, write-once, restart-authoritative *local* control evidence; lives at `<control_directory>/acquisition_attempt_journal.qfj2`, where the control directory is the strict-capture-ID **sibling** `~/workspace/data_archive/yahoo_1h_clean/<capture_id>.control/`, **outside** `cap_dir`/`archive.root`. The rev2 attempt semantics (ATTEMPT_CONSUMED_AMBIGUOUS, SKIP_VERIFIED, HOLD:FINAL_MISMATCH) are preserved verbatim in substance; only the location moved.
- **`qfj2_publication_journal`** — the accepted publisher's QFJ2 intent/published journal; a **separate file** in the same sibling control directory (`qfj2_publication_journal.qfj2`), also outside `cap_dir`. Its intent record pins parent, `CONTAINER_SHA256`, blob id, and member pins before any remote write.
- **`public_archive_anchor`** — hashes/identifiers only; one deterministic home: public scanner repo `research_notes/archive_anchors/<capture_id>.json`; created **only after** final remote verification succeeds. Contents: designated repo/ref, exact commit/tree/blob ids, `CONTAINER_SHA256`, capture ID, adopted rev3 manifest pin, member count 158, verification transcript hash.

**Membership contract** (new `archive.membership_contract`, reconciled in `archive.layout`/`archive.root`): the capture root contains exactly `raw/`, `actions/`, `meta/`, plus optional canonical `manifest.json` and `SHA256SUMS`; QFAR1 seals exactly **156 payloads + 2 bookkeeping = 158**. No control journal and no public anchor is a QFAR1 member, and none counts toward the 67,108,864-byte physical-member ceiling.

**Anchor sequence repaired** (`publication_binding.final_verification`): before anchor creation, remote re-fetch verification compares commit/tree/blob/container/member results against the **QFJ2 intent/published records, the sealed `CONTAINER_SHA256`, exact commit/blob ids, and the independent validation pins**. Only after all of that passes is the anchor created. Later consumers start from the anchor and independently re-verify; no branch-tip-only trust. `execution_packet.handoff_contract` reconciled: the executor stages payloads only under `archive.root` (its journal lives in the control directory), the publisher journal likewise, and a new stage 4 records the anchor step.

## Machine diff (fe3611e7… → new candidate 261a7557…)

50 leaf changes, **0 unclassified/unallowed** — every change is inside the allowed field set (archive.root / attempt_journal / layout / control_directory / membership_contract / ledger_objects / handoff_contract / final_verification / public_archive_anchor / provenance). Preservation reproven by canonical-JSON deep equality: all 52 requests in order and parameters, runtime pins, session-construction freeze, G1–G11, limiter/call budget and ceilings, symbol mapping, universe source, target repo/ref/path, member accounting, design pin, and publisher pin are **byte-identical in substance** (hashes in `semantic_diff_rev3_candidate_to_r2.json`).

## Fixture (narrow, no-socket, pinned publisher imported read-only)

`run_ledger_separation_fixture.py` against a local fake Git Data remote — **17/17 checks PASS, 0 failures, one run, no repairs**:

- **L-01** correct 156-member synthetic root with both journals in the sibling control directory → census/build/publish **PUBLISHED**; capture-root top level is exactly the member dirs; sealed set exactly 158.
- **L-02** acquisition journal placed inside the capture root → **HOLD:MEMBERSHIP**.
- **L-03** QFJ2 publication journal placed inside the capture root → **HOLD:MEMBERSHIP**.
- **L-04** with **no anchor in existence**, remote re-fetch verification succeeds from the sealed container / QFJ2 intent / independent pins alone; transcript matches the journal's published record.
- **L-05** anchor emitted only after verification; a consumer starting from the anchor re-verifies commit/tree/blob ids, recomputes `CONTAINER_SHA256` from fetched bytes, and matches all 158 members against the sealed pins.

Accepted corruption/crash/ceiling/concurrency suites were **not** rerun (evidence reused from pins 1778dba / cf929e0 / 53bdc67, per spec).

## Trials, failures, minutes

Elapsed ≈9 minutes of the ≤20 cap. Trials: one spec fetch (succeeded); one candidate build (50 classified changes, 0 violations); one fixture run (17/17 PASS). Failures: none. Repair minutes: **0** (no repair allowance used; the publisher candidate was not modified).

## Scope confirmation

Offline/no-socket throughout (the spec fetch was the sole network read). Zero authenticated GitHub operations, vendor/model calls, downloads, installs, spend, adoption/merge, capture, real publication, backtests, holdout access, or production changes. U-1 unprobed (HOLD). Evidence base verified byte-identical before and after: frozen rev2 manifest `634c4541…`, -17 candidate `fe3611e7…`, -18 r1 memo `01301bb2…`, design r3 `cd9ef36d…`, accepted publisher file `1d4c1923…` (commit 53bdc67). All deliverables left uncommitted.

## Deliverables

Package `research_notes/yahoo_rev3_ledger_separation_20261016_r2/` — corrected candidate, machine diff, fixture driver, fixture results, SHA256 manifest; this memo.
