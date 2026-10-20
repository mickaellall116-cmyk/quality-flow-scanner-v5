# -58 STAGING PLAN — final P3 binding closure

Task: QF-TD-ROUTE-TRANSACTION-P3-BINDING-FINAL-CLOSURE-20261020-58 r1
Spec: Issue #1 comment 6303549678 (adjudication of -57; basis
immutable commits 9f86d26 pre-execution / f57ed93 result /
8b4caa5 correction).
Budget: ≤35 min, ONE offline attempt, first-failure stop. Start
convention: elapsed measured from spec fetch (2026-10-20T23:01:00Z).

## Single-dispatch (spec §1; standing rule from the -55 incident)
- Pre-check BEFORE any file operation: no *td58* stage dir, no
  td58 worktree, no 20261020-58 commit on origin/main, no owner
  lease — PASS (sole lane; parent-verified, re-verified by this
  worker ~23:02Z).
- Atomic owner lease acquired OUTSIDE the stage via O_CREAT|O_EXCL
  BEFORE any staging: /home/hatch/workspace/qf_td58_owner_lease.json
  (acquired 2026-10-20T23:03:22Z; task_id + stage_root_planned +
  owner_session recorded). Driver v10 verifies it first; a
  missing/foreign/mismatched lease fails
  DUPLICATE_DISPATCH_REFUSED before any cleanup/copy/removal.
  The lease is released LAST, after the result commit is on
  origin/main and read back.
- Stage root is task-unique: /home/hatch/workspace/qf_td58_stage.
  Anchor worktree: /home/hatch/workspace/qf_td58_wt (detached at
  origin/main 558ae48 at creation). Only paths created by this run
  are removed by this run.

## Capacity (recorded pre-staging, 2026-10-20T23:02Z)
filesystem: /home/hatch (workspace disk), 100G total, 81G free.
requirement: shadow worktree ~506MB + venv ~174MB + margin << free.
PASS.

## Driver
proof_driver_v10.py (sha256 5c657b732f2fe300c3a3d16353ec09a4940d162b208b1faa2eeb520baf7abd8c),
derived from the EXECUTED driver v9 (c96ef6dc…, -57 commit
f57ed93) with ONLY: (a) task/stage/lease identity; (b) a
frozen-driver-v9 byte-identity hash gate (PIN_DRIVER_V9);
(c) pilot stage dir renamed td58_pilot_stage; (d) the spec-§3
substantive correction — P3 binding evidence sourced from the
entrypoint module's own `_c4h_mod` global, fail-closed before
dereference. Exact v9→v10 diff ships in this package
(driver_v9_v10.diff). Pre-execution self-checks:
td58_self_checks.py — 18/18 PASS (derivation confinement,
digest-checker reuse positive/negative, binding guard predicate
on synthetic mismatches: absent _c4h_mod, non-module _c4h_mod,
mismatched module, wrong bound function — all fail closed).

## Sequence (driver main — the v9 sequence, unchanged)
lease verify → hash gates (all inherited pins/receipts + frozen
v9 + adapter + supplement full pin) → git-aware shadow build
(detached worktree on the workspace disk) + §B preflight +
collector-blob proof → corrected P2 digest check REUSED as
executed in -57 (spec §4: receipt reuse; the 18-trial suite is
NOT rerun; accepted-matrix comparison demonstrated on committed
artifacts) → P3, corrected per spec §3/§5:
  binding identity — staged v7 entrypoint's `_c4h_mod.__file__`
  resolves exactly to the staged pinned constructor candidate;
  its sha256 == 3f432e7e30d3d962b36cb0c82cae9658cf269c3214beb918402f8645a3fe0ad1
  (PIN_CONSTRUCTOR_CAND); v7.construct_4h IS
  v7._c4h_mod.construct_4h; plain construct_4h NOT in sys.modules;
  the legacy sys.modules lookup is recorded as NOT used as
  evidence → CLI refusal AS EXECUTED (full-arg + bare invocations:
  exit 3, REFUSED on stderr, no out.csv, watch tree
  byte-unchanged) → F1 end-to-end (staged entrypoint on the F1
  fixture; serialization byte-identical to the -46 expected
  string, sha bd550433…) → post-run rehash → shadow removal.
CLOSED, NOT RERUN (receipts only): hash-gate/P0 closures, P1
gate suite + gate567, branch-isolated clock proof, Gate-7 spot,
P2 18-trial suite, NLQUAL, E1, A/D/B families.

## Environment
run_proof.sh under `unshare -n` (caller, cwd = anchor worktree
qf_td58_wt): network probes must FAIL; offline venv from the
pinned wheelhouse (td_nl_wheelhouse_20261016); pip freeze must
equal the TD lock (08b38cfa…) or the run stops before the driver.
Stage support files (network_probe.py, requirements_hashes.txt,
integration_requirements.lock) copied from the committed -46
package. Fixtures only; no live file executed or written; main
tree (incl. pre-existing UU forward_test/kama_shadow.json)
untouched; publishing via temp-index commits based on
origin/main, ancestry-verified. Raw outputs are preserved into
this package BEFORE stage cleanup; the owner lease is released
only after the result commit is durably on origin/main and read
back.

## Terminal
PASS: TD_ROUTE_TRANSACTION_PROOF_PASS__RESEARCH_ADOPTION_
DESIGNATION_READY__S2_HOLD; else TD_ROUTE_TRANSACTION_PROOF_
HOLD__<FIRST_FAILURE>. REQ-S2: UNIMPLEMENTED__HARD_HOLD
(recorded, not implemented). No adoption, no live repin, no
production change; entries PAUSED unchanged.
