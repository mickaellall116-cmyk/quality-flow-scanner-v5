# TD PROBE TAIL-AUDIT CLOSURE — task -72 r1 RESULT

Task: QF-TD-PROBE-TAIL-AUDIT-CLOSURE-20261021-72 r1
Spec: Issue #1 comment 6320693517 (-71 adjudication: HOLD
accepted; U12 diagnosis independently confirmed; additional
finding — the persistence tail omits the fsync-#4 branch,
parent-directory fsync AFTER receipt publication).
Basis: -71 package (precommit 06a86fa, result 0df6cff,
corrective 1f65028, elapsed correction 2338b97), immutable.
-68/-69/-70 likewise untouched. Scope: ONE bounded OFFLINE
successor, new additive package only. ONE formal execution
attempt after a pushed precommit; first-failure stop. No
vendor/API/data calls (the only network use was the read-only
spec fetch), no credentials, zero credits, synthetic data
only. Day 1 NOT re-run. REQ-S2 HOLD; entries PAUSED.

Precommit: fcb5a1056d2aab3219af2be91c7ce171eed8bd8c
(pushed and ancestry-verified against origin/main BEFORE
execution; includes CASE_EXPECTATION_AUDIT.md).
Desk audit: CASE_EXPECTATION_AUDIT.md, SHA-256
8beb2e13fb85a243e4bc42c1a6e0a15654c3e923ad7f6dc59ee8360dc010e4ec.

## TERMINAL

TD_PROBE_TAIL_AUDIT_CLOSURE_READY__FRESH_USER_GO_REQUIRED

The single formal attempt PASSED the complete ordered suite:
**63/63 cases, exit 0, stderr empty**, and the permitted
byte-identity repeat reproduced the run exactly (stdout
SHA-256 identical across both runs:
468e2b9c40e1ca83c5d35744e48b46472f47a8c2d170ee9d4fa17c196f836993;
stderr empty, e3b0c442…). QUALIFICATION_RESULTS.json is the
first run's exact stdout. This is offline readiness only:
Day 1 still requires Mike's fresh GO after independent
review, per the terminal itself.

Elapsed ≈26 min of the ≤35 cap (spec fetch → result commit);
repair minutes 0 — no in-run repair occurred.

## Pre-formal desk audit (spec-mandated, source-only)

CASE_EXPECTATION_AUDIT.md reconciles every never-executed
case — U13 and P01-P11 — against the pinned source (candidate
account_preflight.py; frozen pilot_acquire.py / rate_limiter.py
by SHA): per case, source function/branch, expected
call/attempt counts, the write/fsync/link sequence
(fsync #1 body temp, #2 receipt temp, #3 dir post-body, #4 dir
post-receipt), expected final/temp paths, expected terminal
token, and the no-data proof (preflight position: the session
is the driver preflight; any failure list aborts the wrapper
before any request fetch). NO test or dress-rehearsal
execution was performed during the audit.

Audit outcome: U13 and P01-P11 — every expectation reconciles
with the pinned source; **no corrections, no candidate
defects found in the audited set**. The audit concurred with
the adjudication's fsync-#4 reading (see below) — that gap is
the spec's own closure item 2, so it was implemented, not
reported as a stop. The one harness correction is U12.

## U12 re-expression (spec item 1) — PROVEN

The -71 case's all-fail block expected all five D1 legs
attempted (10 data calls, total 11); the frozen
AcquisitionWrapper.run (pilot_acquire.py L329-332) breaks the
day at the first stop outcome, so that expectation was
demonstrably wrong (the -71 run recorded total 3). The -72
case proves the three real paths on frozen semantics, with
the hard-ceiling assertion kept:

- (a) daily-gate refusal: usage body daily_usage=795 ->
  USAGE_DAILY_HEADROOM aborts in preflight: exactly 1 call,
  0 data.
- (b) first-leg retries exhausted: only NVDA fails (503) ->
  REQ-ADJ-01 consumes its 2 attempts, outcome
  RETRIES_EXHAUSTED, the run stops immediately: 1 usage +
  2 data = 3 total, outcomes list length 1, ok False.
- (c) worst-case SUCCESSFUL Day 1: new harness transport
  RetryOnceDataTransport 503s the first fetch of each
  distinct URL and serves the standard 200 payload on the
  repeat -> every leg ends OK at attempts=2 (pilot-wide
  retry budget cap 40 >= 5 retries): 1 usage + 10 data =
  11 <= 12, ok True, 5 outcomes.

## Fsync-#4 closure (spec item 2) — MECHANISM AND PROOF

Gap (adjudication + audit concurrence): in -71, if the final
`_fsync_dir` (after the receipt — the commit point — was
published) failed, `_persist_outcome` raised and the
invocation HOLDed, BUT both finals remained visible and the
receipt passed every later integrity check — a subsequent
session would silently reuse the outcome as PASS although
the transaction's last durability barrier had failed.

Mechanism (minimal, fail-closed; account_preflight.py only):
the final `_fsync_dir(self.store_dir)` in `_persist_outcome`
is wrapped; on OSError, `_tombstone_unproven_commit(receipt)`
rewrites the just-published receipt IN PLACE — open the
existing final path (O_WRONLY|O_TRUNC), write-all, file
fsync; a file-CONTENT operation that does not depend on the
directory barrier that just failed — as a REFUSE tombstone
preserving the original binding (bytes / SHA-256 / day /
manifest_sha256 / store_marker_sha256 / required_headroom)
with terminal reason `USAGE_COMMIT_UNCERTAIN: final directory
fsync failed after receipt publication; ...`. The original
OSError then propagates, so the current invocation still
returns USAGE_RECEIPT_PERSIST_FAILED and HOLDs. A later
session verifies the body (binding preserved), reaches the
sticky-REFUSE branch, and returns the recorded
USAGE_COMMIT_UNCERTAIN reason with zero transport. Later
access remains HOLD; the unproven outcome can never be
silently reused as PASS. Retraction was NOT chosen: unlinking
the finals has the same unproven-durability problem (name
removal rides the same directory barrier), whereas the
in-place rewrite's durability rests on a single file fsync.

Proof — new case P12_final_dir_fsync_failure (case 63),
passed in the formal attempt: fsync #4 injected via the
`_flaky_fsync(4)` seam -> session returns
USAGE_RECEIPT_PERSIST_FAILED after exactly 1 usage call; both
finals present; body byte-exact; stored receipt verdict
REFUSE with USAGE_COMMIT_UNCERTAIN and its sha256/bytes still
matching the body; no temp litter; a subsequent unpatched
session returns the USAGE_COMMIT_UNCERTAIN reason with ZERO
transport calls; and at day level (`run_probe_day` under the
same injection) the run aborts in the preflight with
data.calls == 0, usage.calls == 1.

Residual (disclosed, per the spec's fallback): the tombstone
rewrite is best effort — if it ITSELF fails (a second,
independent failure on top of fsync #4), the persist still
raises and this invocation HOLDs, but a later session could
reuse the receipt. That double-failure residue cannot be
proven away at this layer; P12 injects the single failure
the spec names.

## Full case outcomes (63, in order — all PASS)

1-20 Q01-Q20 (-68 regression block), 21-30 A01-A10,
31-38 B01-B08, 39 U01, 40 U02 (midnight-aligned fix from
-71, re-verified), 41-49 U03-U11, 50 U12 (re-expressed,
above), 51 U13 (headers never waive; gate refuses before
reconciliation), 52-62 P01-P11 (transactional persistence
failure set — first execution), 63 P12 (new, above).
Per-case detail strings are in QUALIFICATION_RESULTS.json.

## Changed files vs -71 (everything else byte-identical)

- account_preflight.py — docstring -72 section; the final
  `_fsync_dir` wrapped with the tombstone call;
  `_tombstone_unproven_commit` added. Quota semantics,
  limiter interaction, ceiling, retry, pagination and
  /splits rules untouched.
- tests_qualification.py — docstring -72 section; U12
  re-expressed (three paths) + RetryOnceDataTransport added;
  P12 appended; harness label td72_qualification_r1. U13 and
  P01-P11 functions byte-identical to -71.
- CASE_EXPECTATION_AUDIT.md — NEW (the mandated audit).
- BUILD_RESULT.md / QUALIFICATION_RESULTS.json /
  SHA256_MANIFEST.txt — new/regenerated for this package.
- Byte-identical to -71 (cmp/diff-verified, incl. all 56
  fixture files): probe_runner.py, probe_analyzer.py,
  temporal_gate.py, make_fixtures.py, probe_manifest.json,
  fixtures/ (entire tree).

## Disclosures

1. During precommit preparation the first generated
   SHA256_MANIFEST.txt briefly contained a bogus self-entry
   (the manifest hashed while being written); it was
   regenerated excluding itself and verified `sha256sum -c`
   clean BEFORE the precommit was pushed. No execution had
   occurred; this was a build correction, not a run repair
   (repair minutes remain 0).
2. The desk audit is source-reading only, as mandated. Its
   per-case traces agreed with the formal run at every case,
   including the previously unexecuted tail (U13, P01-P11)
   and the new P12.
3. Result hygiene: this result is a SINGLE commit containing
   the memo, the results JSON and the refreshed pyc-free
   manifest; the commit's file list was verified against the
   package manifest before pushing (67 files: 66 manifest
   entries + the manifest itself). No partial-index
   correction was needed.
4. Day 1 was NOT re-run; no live call of any kind was made.
   The probe's live state is unchanged (program total 2
   credits, all from -18 and -69).
5. The formal run's imports created __pycache__/*.pyc in the
   package (the same sweep -71 disclosed); they were removed
   BEFORE the result manifest was finalized, and the
   committed manifest is pyc-free (66 entries, sha256sum -c
   clean).
