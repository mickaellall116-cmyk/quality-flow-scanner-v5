# -55 STAGING PLAN — branch-isolated final closure

Task: QF-TD-ROUTE-TRANSACTION-BRANCH-ISOLATED-FINAL-CLOSURE-20261020-55 r1
Spec: Issue #1 comment 6297990771 (adjudication of -54; Slack TS 1792520398.891029).
Budget: ≤45 min, ONE offline attempt, first-failure stop. Start
convention: elapsed measured from spec fetch (2026-10-20T18:26Z).

## Driver
proof_driver_v7.py, derived from FROZEN driver v6 (sha256
3d02de026938c2a8f05a8ad7fee35f96b6d2bfd5eb7a6dadf9dd86090bb3bcf6;
hash-gated in-run) with ONLY: identity/stage/path strings; an added
v6 hash gate; and the ONE authorized logic change — the
branch-isolated clock stage (build_original_shadow +
branch_provenance + adjudicate_clock_branches/branch_clock_proof
replacing the single whole-matrix clock comparison). The exact
v6→v7 diff ships in this package (driver_v6_v7.diff): removals are
only the docstring, identity strings, the pilot-stage dir name, and
the old p1 clock block. canonicalize/token_map/first_divergence,
extract_gate567, stage_transition_clock, P2 and P3 are byte-identical
v6 code. Pre-execution self-checks: td55_self_checks.py, 14/14 PASS
(partition positives incl. the real -54 candidate matrix; partition/
repro/rollup negatives; provenance pin prefixes; extractor
positive/negative; v6 pin).

## Branch map (fixed before execution; spec S.3/S.4/S.5)
- CANDIDATE branch: STAGE/shadow — detached git worktree of the run
  repo (td55_wt @ origin/main), -54 staging byte-identical
  (candidate substitution at PKG11/PKG04/R1/PKG19 paths, pilot stage
  td55_pilot_stage) + the retained -54 stage transition (legacy
  PKG11 gate slot restored to ORIGINAL r4 bytes b5399645… for the
  -17 loader contract; candidate gate stays at its -48 path).
  Membership: the 19 candidate adapter/executor clock trials, then
  Gate-7 spot, P2, P3.
- ORIGINAL branch: STAGE/shadow_original — second detached git
  worktree, PRISTINE (zero substitution). Membership: ONLY the
  accepted runner's repro_old historical branch.
- Provenance (fail-closed, before any suite): original pins gate
  b5399645…/driver 5fed4524…/supplement 3cbdbf63…/mechanism
  1b83cdcd…/proof 36bc3a89…; candidate pins gate 94ef967c…/driver
  d11c6b58…/supplement 55ad6f40…/mechanism ca3bafd8…/proof
  6b030c62…/adapter 6980b5b3…/executor bbc23616…; both runner
  copies byte-identical to the accepted runner; paths distinct, no
  containment, neither a symlink; collector-blob proof in BOTH
  worktrees (b683d277… == PIN_COLLECTOR).
- Adjudication: unchanged runner once per branch; ORIGINAL
  repro_old compared exactly; CANDIDATE other-19 compared exactly
  with repro_old explicitly excluded (recorded, not adjudicated);
  exact 20-name partition; combined rollup reconstructed
  arithmetically (per-trial check counts) and compared to accepted
  (checks_passed 31 / checks_total 31 / summary). No matrix is
  fabricated or altered. Real pilot ledger must be unchanged after
  each branch run.

## Sequence (driver main)
hash gates (incl. frozen v6 + all inherited pins/receipts) → P0
receipt (no rerun) → candidate shadow build + blob proof →
original shadow build + preflight → branch provenance → P1:
pinned -52 receipt canonical comparison (751/751 reuse, suite NOT
rerun) → corrected gate567 extractor on the receipt → branch-
isolated clock proof → Gate-7 spot check (candidate branch) → P2 →
P3 → post-run rehash → cleanup of BOTH worktrees.

## Environment
run_proof.sh under `unshare -n` (caller): network probes must FAIL;
offline venv from the pinned wheelhouse (td_nl_wheelhouse_20261016);
pip freeze must equal the TD lock (08b38cfa…) or the run stops
before the driver. Fixtures only; no live file executed or written;
main tree (incl. its pre-existing UU forward_test/kama_shadow.json)
untouched; publishing via temp-index commits, ancestry-verified.

## Terminal
PASS: TD_ROUTE_TRANSACTION_PROOF_PASS__RESEARCH_ADOPTION_
DESIGNATION_READY__S2_HOLD; else TD_ROUTE_TRANSACTION_PROOF_HOLD__
<FIRST_FAILURE>. REQ-S2: UNIMPLEMENTED__HARD_HOLD (recorded, not
implemented). No adoption, no live repin, no production change.
