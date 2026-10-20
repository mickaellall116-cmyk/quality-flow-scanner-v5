# -58 CLOSURE MEMO — final P3 binding closure

Task: QF-TD-ROUTE-TRANSACTION-P3-BINDING-FINAL-CLOSURE-20261020-58 r1
Spec: Issue #1 comment 6303549678 (adjudication of -57; basis
immutable commits 9f86d26 pre-execution / f57ed93 result /
8b4caa5 correction).
Budget: ≤35 min, ONE offline attempt, first-failure stop.
Start convention: elapsed from spec fetch 2026-10-20T23:01:00Z.

## Terminal verdict (verbatim, driver-recorded)

TD_ROUTE_TRANSACTION_PROOF_PASS__RESEARCH_ADOPTION_DESIGNATION_READY__S2_HOLD

All three P3 checks EXECUTED on the single attempt: binding
identity (corrected evidence source), CLI refusal as executed
(full-argument + bare), F1 end-to-end byte identity. Repair
minutes: 0. No second attempt. No closed suite was rerun.

## Single-dispatch + lease
- Pre-check before ANY file operation (~23:02Z): no *td58* stage
  dir, no td58 worktree, no 20261020-58 commit on origin/main, no
  owner lease. SOLE LANE confirmed (parent-verified, re-verified
  by this worker).
- Atomic owner lease (O_CREAT|O_EXCL) acquired OUTSIDE the stage
  at /home/hatch/workspace/qf_td58_owner_lease.json
  (2026-10-20T23:03:22Z, owner_session 14850ad2…); driver evidence:
  owner_lease.result = VERIFIED_SINGLE_OWNER. Released LAST,
  after the result commit is remote-verified.
- Anchor worktree /home/hatch/workspace/qf_td58_wt (detached at
  origin/main 558ae48 at creation); stage root
  /home/hatch/workspace/qf_td58_stage on the workspace disk.

## Driver v10
sha256 5c657b732f2fe300c3a3d16353ec09a4940d162b208b1faa2eeb520baf7abd8c,
derived from EXECUTED v9 (c96ef6dc…, gated byte-identical in-run
by the new HASH_GATE_FROZEN_DRIVER_V9) with ONLY: task/stage/
lease identity, the v9 hash gate, the td58_pilot_stage rename,
and the spec-§3 correction. Pre-execution self-checks 18/18 PASS,
including binding-guard negatives on synthetic mismatches
(absent _c4h_mod, non-module _c4h_mod, mismatched module, wrong
bound function — all fail closed). Pre-execution commit 4269dde
(driver, v9→v10 diff, self-checks + results, staging plan,
run_proof.sh), verified ancestor of origin/main BEFORE execution.

## Corrected digest check (receipt reuse, spec §4)
Reused as executed in -57; the 18-trial suite was NOT rerun.
- Staged supplement sha256 == full pin 55ad6f40509ac77f…;
  positive check ok=true (calendar_proofs sole key ==
  6b030c62fdaf3cd738001a438b6f6a562b381b93b29dd8b299753de6aebe4fa5;
  REQ-SPT-07/08 entry digests == same).
- Negative control: original digest 36bc3a89… substituted at both
  field paths → rejected=true.
- Canonical comparison vs accepted -04 run-2: IDENTICAL 205/205,
  first_divergence null.

## P3 binding (EXECUTED, PASS — corrected evidence source)
Evidence sourced from the entrypoint module's own `_c4h_mod`
global (v9's sys.modules lookup returned None because the pinned
entrypoint binds via module_from_spec/exec_module without
sys.modules registration — a proof-driver lookup defect, not
candidate evidence):
- c4h_mod_present: true; c4h_mod_is_module: true;
  constructor_module_name: construct_4h_v3_cliguard.
- _c4h_mod.__file__ resolves exactly to the staged pinned
  constructor candidate
  (shadow_candidate/research_notes/td58_pilot_stage/construct_4h_v3_cliguard.py);
  constructor_module_file_is_staged_candidate: true.
- Its SHA-256 == 3f432e7e30d3d962b36cb0c82cae9658cf269c3214beb918402f8645a3fe0ad1
  == PIN_CONSTRUCTOR_CAND (constructor_module_sha256_is_pin: true).
- v7.construct_4h IS v7._c4h_mod.construct_4h
  (construct_is_candidate_function: true).
- No legacy/plain construct_4h module supplied the binding:
  plain_construct_4h_module_loaded: false; the legacy
  sys.modules.get("construct_4h_v3_cliguard") is None and is
  recorded as NOT used as evidence.
- Validator module sha256 ca3bafd87e7cb4…; entrypoint module
  sha256 84ccd2c68aea… (both == pinned candidates).

## P3 CLI refusal (EXECUTED, PASS)
Both invocations of the staged CLI-guarded constructor candidate,
inside a watched tree:
- full-argument: exit 3; bare: exit 3.
- stderr (both, exact): "REFUSED: direct construct_4h CLI
  invocation is not the cleared path; use the validated
  entrypoint (pilot_build). No construction performed."
- out_csv_created: false; watch_tree_unchanged: true.

## P3 F1 end-to-end (EXECUTED, PASS)
Staged v7 entrypoint on the F1 fixture: exit 0; serialization
SHA-256 bd550433d4af504a05a84be551c45d6a6d35be35cef3f479a6acca2cdf5ce813;
serialization_matches_f46: true (byte-identical to the frozen
-46 expected serialization; PIN_F1_SER_SHA).

## Environment + integrity
unshare -n: NETWORK_DENIED probes (curl exit 7). CPython 3.12.3 /
pandas 2.2.3 / pandas_market_calendars 4.5.1; FREEZE_EQUALS_LOCK
(lock 08b38cfa…). Hash gates all PASS (incl. blob proof ==
PIN_COLLECTOR). Post-run rehash: ledger unchanged, original
constructor unchanged, candidates unchanged — all true.
Cleanup: shadow worktree removed; main working tree status
unchanged (pre-existing UU forward_test/kama_shadow.json intact);
anchor repo head unchanged across the run.

## Controls / disclosures
REQ-S2 recorded UNIMPLEMENTED__HARD_HOLD. Nothing adopted,
re-pinned, or changed in production; the LIVE chain was never
executed (candidates only inside the isolated shadow); entries
PAUSED unchanged; 0 vendor/API/model calls, 0 spend; fixtures
only; no SPT-08/backtest/holdout; no Yahoo; no Issue #9.
Elapsed: spec fetch 23:01:00Z → result-commit remote
verification (recorded in the result commit message / report);
within the ≤35-minute budget. Repair minutes: 0. No protocol
deviations.
