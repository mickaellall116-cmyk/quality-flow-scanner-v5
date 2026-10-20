# -56 STAGING PLAN — collision-safe transaction remainder

Task: QF-TD-ROUTE-TRANSACTION-COLLISION-SAFE-REMAINDER-20261020-56 r1
Spec: Issue #1 comment 6300344562 (adjudication of -55; the -55
executed record 1942b41 + reconciliation bb6fd8f).
Budget: ≤45 min, ONE offline attempt, first-failure stop. Start
convention: elapsed measured from spec fetch (2026-10-20T20:37Z).

## Single-dispatch (spec §1; standing rule from the -55 incident)
- Pre-check BEFORE any file operation: no *td56* stage dir, no
  td56 worktree, no 20261020-56 commit on origin/main — PASS (sole
  lane; parent-verified and re-verified by this worker).
- Atomic owner lease acquired OUTSIDE the stage via O_CREAT|O_EXCL:
  /home/hatch/workspace/qf_td56_owner_lease.json (owner, timestamp,
  path recorded in the result package). Driver v8 verifies the
  lease before staging; a missing/foreign/mismatched lease fails
  DUPLICATE_DISPATCH_REFUSED before any cleanup/copy/removal.
- Stage root is task-unique: /home/hatch/workspace/qf_td56_stage.
  No -55 path is touched, cleaned or reused (the qf-td55 worktree
  and any -55 stage remnants are left exactly as found).

## Driver
proof_driver_v8.py (sha256 recorded in the manifest), derived from
the EXECUTED driver v7 (bb375b76…; restored by bb6fd8f; the
never-executed 279db80 variant a3d39347… is not used) with ONLY the
spec-§3 changes: (a) task/stage identity + lease enforcement;
(b) Gate-7 spot with ABSOLUTE mechanism paths (each gate's own
P_MECHANISM resolved vs the repo root — original
research_notes/pilot_harness/validate_input.py 1b83cdcd…, candidate
research_notes/td_validator_dst_repair_requalification_20261019_44/
validate_input_v3_dstfix.py ca3bafd8…); (c) P2 stages the
candidate-aware runner adapter. v7's clock functions are retained
byte-identical and NEVER invoked (main() calls no
build_original_worktree/stage_transition_clock/branch_provenance).
Exact v7→v8 diff ships in this package (driver_v7_v8.diff).
Pre-execution self-checks: td56_self_checks.py — 21/21 PASS
(unsanctioned functions byte-identical; critical adjudication
functions identical; p1 receipt head identical; lease-first main).

## P2 runner adapter (spec §3/§4)
run_integration_trials_candidate_aware.py (sha256
e08e33c2335df756488c7c566149638792018fd3c064a48b51eec4c8bcdc0c8c)
= the frozen -04 runner with EXACTLY ONE line changed (diff ships:
adapter_frozen_diff.diff): I01's validate_input source path from
"pilot_harness/validate_input.py" to the candidate validator path.
The frozen runner deterministically failed pin_validate_input
because it read the original mechanism (1b83cdcd…) while the staged
candidate driver pins ca3bafd8… — adjudicated harness-context
mismatch, not a candidate defect. Adjudication unchanged: I01 must
PASS reporting the candidate hash; I02–I18 exact after the
inherited canonical path/hash token mapping (which already maps
the mechanism hash/path pair); only I01's sanctioned token may
differ. The inherited proof-digest staging substitution
(36bc3a89…→6b030c62…, count==1 in the adapter) is applied at
staging exactly as in -50..-55.

## Sequence (driver main)
lease verify → hash gates (all inherited pins/receipts + frozen
v7 + adapter) → P0 receipt (reuse, no rerun) → candidate shadow
build (detached git worktree on the workspace disk) + §B preflight
+ collector-blob proof → P1 remainder: pinned -52 receipt canonical
comparison (751/751 reuse; gate suite NOT rerun) → corrected
gate567 extractor on the receipt (reuse) → Gate-7 spot (facts
identical; candidate 2026-07-03 early-close True) → P2 (adapter,
once) → P3 (binding identity; CLI refusal AS EXECUTED full-arg +
bare: exit 3, REFUSED on stderr, no out.csv, watch tree unchanged;
F1 byte identity vs the -46 expected serialization bd550433…) →
post-run rehash → shadow removal.
CLOSED, NOT RERUN: gate suite, clock suites (either branch form),
NLQUAL, E1, A/D/B families.

## Environment
run_proof.sh under `unshare -n` (caller, cwd = anchor worktree
td56_wt @ the pre-execution commit): network probes must FAIL;
offline venv from the pinned wheelhouse (td_nl_wheelhouse_20261016);
pip freeze must equal the TD lock (08b38cfa…) or the run stops
before the driver. Stage support files (network_probe.py,
requirements_hashes.txt, integration_requirements.lock) copied
from the committed -46 package. Fixtures only; no live file
executed or written; main tree (incl. pre-existing UU
forward_test/kama_shadow.json) untouched; publishing via commits
from the anchor worktree, ancestry-verified. Raw outputs are
preserved into this package BEFORE stage cleanup; the owner lease
is released only after the result commit is durably on origin/main
and read back (spec §8).

## Terminal
PASS: TD_ROUTE_TRANSACTION_PROOF_PASS__RESEARCH_ADOPTION_
DESIGNATION_READY__S2_HOLD; else TD_ROUTE_TRANSACTION_PROOF_HOLD__
<FIRST_FAILURE>. REQ-S2: UNIMPLEMENTED__HARD_HOLD (recorded, not
implemented). No adoption, no live repin, no production change;
entries PAUSED unchanged.
