# -57 STAGING PLAN — corrected digest check + P3 closure

Task: QF-TD-ROUTE-TRANSACTION-DIGEST-P3-CLOSURE-20261020-57 r1
Spec: Issue #1 comment 6302105446 (adjudication of -56; basis
immutable result commit 686ac81, memo and driver v8).
Budget: ≤45 min, ONE offline attempt, first-failure stop. Start
convention: elapsed measured from spec fetch (2026-10-20T21:59:15Z).

## Single-dispatch (spec §1; standing rule from the -55 incident)
- Pre-check BEFORE any file operation: no *td57* stage dir, no
  td57 worktree or stage, no 20261020-57 commit on origin/main, no
  owner lease — PASS (sole lane; parent-verified and re-verified
  by this worker at 21:59Z). The -55 dirs (qf-td55, qf_td55_stage)
  and the -56 lease/stage names are NOT touched.
- Atomic owner lease acquired OUTSIDE the stage via O_CREAT|O_EXCL
  BEFORE any staging: /home/hatch/workspace/qf_td57_owner_lease.json
  (acquired 2026-10-20T22:00:15Z; owner_session, task_id,
  stage_root_planned recorded). Driver v9 verifies it first; a
  missing/foreign/mismatched lease fails
  DUPLICATE_DISPATCH_REFUSED before any cleanup/copy/removal.
  The lease is released LAST, after the result commit is on
  origin/main and read back.
- Stage root is task-unique: /home/hatch/workspace/qf_td57_stage.
  Anchor worktree: /home/hatch/workspace/td57_wt (detached at the
  pre-execution commit). Only paths created by this run are
  removed by this run.

## Capacity (recorded pre-staging, 2026-10-20T22:05Z)
filesystem: /home/hatch (workspace disk), btrfs (dynamic inodes)
free_bytes: 86,059,511,808 (~86 GB) at pre-check
requirement: repo worktree ~506MB + shadow worktree ~506MB +
venv ~174MB + margin 2GiB = ~3.3GB << free. PASS.

## Driver
proof_driver_v9.py (sha256 c96ef6dc9c81cb718431dbbfe4688ddb8467bc844b8535bc8d638240666aacbe),
derived from the EXECUTED driver v8 (aad2e97c…, -56 commit
686ac81) with ONLY: (a) task/stage identity + lease-field
adaptation; (b) replacement of the defective P2 reporting check
(see below); (c) main() sequence executing ONLY the spec-§3
steps. Exact v8→v9 diff ships in this package
(driver_v8_v9.diff, 11 hunks). Pre-execution self-checks:
td57_self_checks.py (derivation confinement, digest-checker
unit tests, comparator demonstration + mutation negative,
matrix schema fact, lease/pin resolution).

## The corrected digest check (spec §2/§3) — exact field paths
RETIRED: v8's substring search of the candidate matrix raw text
for the full 64-hex digest. Schema-invalid: the matrix format
contains NO 64-hex strings at all (regex-verified on both the
-56 candidate matrix and the accepted -04 matrix); the full
digest lives only in the supplement JSON.
CORRECTED (driver function proof_digest_check, pure):
- Object under check: the STAGED candidate supplement bytes at
  shadow research_notes/td_fresh_full_manifest_preflight_
  evidence_20261016/fresh_supplement.json (staged byte-for-byte
  from PKG48 fresh_supplement_v2_candidate.json), hash-gated to
  the full pin sha256
  55ad6f40509ac77f0634b8ab4208bf39017219ae065e240af852ac581c1acca5.
- POSITIVE requires BOTH:
  (1) field path `calendar_proofs.<sole key>`: the
      calendar_proofs object holds EXACTLY ONE key and it equals
      6b030c62fdaf3cd738001a438b6f6a562b381b93b29dd8b299753de6aebe4fa5;
  (2) field path `entries.*.calendar_proof_digest`: every entry
      (REQ-SPT-07, REQ-SPT-08) carries the same digest.
- NEGATIVE (must be REJECTED by the same function or the run
  fails P2_PROOF_DIGEST_NEGATIVE): the original supplement's
  digest 36bc3a89bd266b9d7478d7f6082addd7b764a824bac45afdcbe534eb1d37f21a
  substituted at both field paths.
- Receipt demonstration (no suite rerun): the inherited
  comparator is applied to the committed -56 candidate matrix
  (PKG56 run_artifacts/driver_matrix.json) vs the accepted -04
  run-2 matrix; the -56 run's negative-control receipt is cited
  into the results.

## Sequence (driver main)
lease verify → hash gates (all inherited pins/receipts + frozen
v8 + adapter + supplement full pin) → git-aware shadow build
(detached worktree on the workspace disk) + §B preflight +
collector-blob proof → corrected P2 digest check (above) → P3:
binding identity (staged v7 entrypoint loads the CLI candidate
by exact path; constructor module sha == 3f432e7e…; validator
sha == ca3bafd8…; plain construct_4h NOT in sys.modules;
v7.construct_4h IS the candidate's function) → CLI refusal AS
EXECUTED (full-arg + bare invocations: exit 3, REFUSED on
stderr, no out.csv, watch tree byte-unchanged) → F1 end-to-end
(staged entrypoint on the F1 fixture; serialization byte-
identical to the -46 expected string, sha bd550433…) →
post-run rehash → shadow removal.
CLOSED, NOT RERUN (receipts only): hash-gate/P0 closures, P1
gate suite + gate567, branch-isolated clock proof, Gate-7 spot,
P2 18-trial suite, NLQUAL, E1, A/D/B families.

## Environment
run_proof.sh under `unshare -n` (caller, cwd = anchor worktree
td57_wt @ the pre-execution commit): network probes must FAIL;
offline venv from the pinned wheelhouse
(td_nl_wheelhouse_20261016); pip freeze must equal the TD lock
(08b38cfa…) or the run stops before the driver. Stage support
files (network_probe.py, requirements_hashes.txt,
integration_requirements.lock) copied from the committed -46
package. Fixtures only; no live file executed or written; main
tree (incl. pre-existing UU forward_test/kama_shadow.json)
untouched; publishing via commits from the anchor worktree,
ancestry-verified. Raw outputs are preserved into this package
BEFORE stage cleanup; the owner lease is released only after
the result commit is durably on origin/main and read back.

## Terminal
PASS: TD_ROUTE_TRANSACTION_PROOF_PASS__RESEARCH_ADOPTION_
DESIGNATION_READY__S2_HOLD; else TD_ROUTE_TRANSACTION_PROOF_
HOLD__<FIRST_FAILURE>. REQ-S2: UNIMPLEMENTED__HARD_HOLD
(recorded, not implemented). No adoption, no live repin, no
production change; entries PAUSED unchanged.
