# QF-YAHOO — Task -18: Rev3 Ledger Separation — HOLD

**Verdict: HOLD** (delivered inside the ≤15-minute cap; not a late completion).
**Task:** -18, dispatched 2026-10-16 ~03:00 EDT with the -17 adjudication
(readiness HOLD/PARK — ledger-location contradiction), plus a bounded-ACK
reminder ~03:23 EDT.
**Scope honored:** offline only. Zero authenticated GitHub operations, zero
vendor/model/API calls, zero downloads, zero installs, zero spend, zero
adoption/merge/capture/publication/backtest/holdout/production changes.
Nothing in this memo adopts, amends, or supersedes any prior package.

## Blocker (concrete, encountered in this run)

The canonical -18 spec comment on GitHub Issue #1 could not be fetched in
this run: the single permitted fetch attempt failed at the source-fetch
stage, and retrying it — by any route — is barred. The spec is therefore
unavailable, which means the following spec-owned items **could not be
confirmed and were not guessed**:

- the exact contradictory statements the -18 spec names, verbatim;
- the spec's directed resolution (which document it designates as owning the
  ledger location);
- the spec's deliverable file names, package layout, and verdict vocabulary
  for a PASS (only the HOLD branch is safe to emit without the spec).

A resolution written without the spec's direction would risk separating the
ledger into the wrong home and calling it compliance. That is precisely the
failure this task exists to prevent, so the verdict is HOLD, with the
locally verifiable evidence below preserved for the re-dispatch.

## What was verified locally (offline, read-only)

Pins re-verified after the run; all byte-identical, none edited:

- Frozen rev2 manifest `capture_manifest.json` —
  sha256 `634c4541a8b30ade50e45898e80ee65806fa323c953020edc149530642d9bef3`
- -17 normalized candidate —
  sha256 `fe3611e78347806a19d9810a3c141bab5225f2b0785d38e1ba6f013c76d76c5e`
- -17 memo `YAHOO_REV3_MANIFEST_ADOPTION_READINESS_20261016.md` —
  sha256 `d3b3b3e582eb1311be7c45fc0970736bc1ca7f6b9d697f6acbf67bccdbf78250`
- Design r3 `YAHOO_SINGLE_BLOB_ARCHIVE_DESIGN_20261015.md` —
  sha256 `cd9ef36da512185781d2bf6376d1a8848ba62cbf134aec922566aec518f71470`
- `git status` clean for the -17 package, the frozen-manifest directory, and
  the -13 package.

## The locally demonstrable ledger tangle (evidence for re-dispatch)

Two distinct objects are both called "ledger" across the bound documents,
and the -17 candidate's verification list is circular about one of them:

1. **Design r3 (accepted)** separates publication into: §6 step 8 "Verify,
   then record — §7 must pass in full; only then is `PUBLISHED` written to
   the journal and the public ledger anchor committed"; §7 step 7 "Ledger
   anchor — **only after 1–6 pass**: commit a non-data record to the **public
   scanner repo's `research_notes/`** naming {designated repo, ref, commit C,
   tree T, blob id, CONTAINER_SHA256, capture ID, capture-manifest rev.3 pin,
   member count 158, verification transcript hash} — hashes and identifiers
   only, never payload bytes"; §8 consumer validity starts from that anchor.
   The design's anchor has exactly one home: the public scanner repo.
2. **The -17 candidate's `publication_binding.final_verification`** both
   consumes and produces the anchor in one list: step 2 "fetch the blob and
   recompute CONTAINER_SHA256; **must equal the ledger anchor**" (anchor as
   verification *input*) and the final step "**record** a hashes-only public
   ledger anchor" (anchor as verification *output*) — with **no location
   stated anywhere in the candidate**. As written, verification requires an
   anchor that the same procedure only creates after verification passes.
3. **A second "ledger"** runs through the same documents with a different
   home and different contents: the local capture/attempt ledger —
   `archive.attempt_journal` ("an fsync'd attempt record is appended to the
   capture ledger", local, under `archive.root`), execution stage 1 ("it
   stages the 156 payloads and the capture ledger under archive.root"), and
   the container's own `manifest.json` described as carrying an "acquisition
   ledger". Local, per-attempt, operational — nothing to do with the public
   hashes-only anchor, but sharing its name.

Whether item 2/3 is the contradiction the -18 spec names — and which
document the spec designates as the owner of the anchor's location — cannot
be confirmed without the spec. The separation, when re-dispatched with the
spec readable, should at minimum: give the public anchor exactly one named
home (design r3: public scanner repo `research_notes/`), state the
candidate's verification as verify-against-pins → then record anchor (no
anchor-as-input step), and rename/disambiguate the local capture ledger so
the two objects never share a bare name again.

## Minutes

Elapsed ≈ 11 minutes of the ≤15 cap (incl. the failed spec fetch, local
pin verification, and this write-up). No repair was attempted; no file from
any prior package was modified.

— Muse
