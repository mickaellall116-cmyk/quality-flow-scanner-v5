# TD READINESS TXN EXCEPTION + BINDING — -13 r1

Task: QF-TD-READINESS-TXN-EXCEPTION-BINDING-20261017-13 r1
Spec: GitHub Issue #1 comment 6235656978 (fetched via public API first, followed exactly)
Base: -12 package at commit fc1879f — PRESERVED UNCHANGED (verified: readiness_transaction_r2.py still sha256 167ffe23…)

## Verdict: READINESS_TXN_EXCEPTION_BINDING_PASS_OFFLINE

The -12 verdict (POSTWRITE_RECOVERY_TARGETED_PARTIAL_PASS__LIVE_HOLD_EXCEPTION_AND_BINDING)
named three source-level gaps. All three are closed in a new candidate
revision, `readiness_transaction_r3.py`, proven offline on fixture
copies only. The revised execution proposal (r3) remains
**NOT AUTHORIZED**; no live step of any kind was taken or cleared.

## Defect 1 — real exceptions bypass rollback → CLOSED

-12's `run()` caught only `Refusal`; a real `OSError`/`RuntimeError`
after the replace escaped to `finally`, released the locks and could
leave the candidate adopted. In r3, `run()` catches every `Exception`
under the same discipline while locks remain held: exact rollback
(atomic restore + fsync + hash verify) and a durable
`TERMINAL_ROLLED_BACK` journal state precede lock release. If the
rollback itself cannot be verified, the journal records
`TERMINAL_HOLD_MANUAL` and the outcome is `HOLD_MANUAL`
(reason `ROLLBACK_UNVERIFIED`) — ROLLED_BACK is never claimed falsely.
Real-exception injection is via a fault hook inside the atomic-write
path at the `write` and `fsync` stages of each artifact, plus a
journal-advance fault at TERMINAL_COMPLETE:

- x01 OSError evidence write → ROLLED_BACK, exact legacy, locks released
- x02 OSError evidence fsync → ROLLED_BACK
- x03 OSError card fsync → ROLLED_BACK
- x04 RuntimeError from dry-run hook → ROLLED_BACK
- x05 OSError receipt write → ROLLED_BACK
- x06 OSError terminal-record fsync → ROLLED_BACK
- x07 OSError terminal journal advance → ROLLED_BACK
- x08 rollback write also fails → HOLD_MANUAL, candidate left in
  place, journal TERMINAL_HOLD_MANUAL, never claimed ROLLED_BACK

## Defect 2 — terminal COMPLETE under-validated → CLOSED

`recover()` no longer accepts existence. For TERMINAL_COMPLETE it
parses and verifies: terminal record (exact txn id, outcome COMPLETE,
status_calls equal to the journal's); dry-run receipt (txn-bound,
gates exactly 12 × PASS, gates_passed/gates_total 12/12); evidence
(txn id + candidate_sha bound to the journal); token card
(evidence_sha == sha256 of the evidence bytes, candidate_sha bound);
target hash == candidate hash; journal phase/history consistency.
Tamper negatives, all HOLD_MANUAL with no ledger touch:
b01 empty receipt, b02 11-of-12 receipt, b03 receipt wrong txn,
b04 terminal wrong id, b05 terminal wrong outcome, b06 evidence
tampered, b07 card tampered.

## Defect 3 — recovery paths not exactly bound → CLOSED

The r3 journal binds, at BEGUN: canonical absolute `target_path`,
`target_realpath`, absolute `backup_path`, and `workdir`. `recover()`
validates — before acquiring locks or touching the ledger — marker
txn id vs journal txn id, caller target vs journal target binding,
symlink/realpath agreement, journal backup path vs the canonical
workdir path, sha256 formats, phase/history monotonic validity, and
status_calls ∈ {0,1}; a second journal artifact binding the same
target is ambiguity → fail closed. The restore source is the
journal's bound backup path, not a constructed one. Negatives, all
HOLD_MANUAL: b08 marker/journal txn mismatch, b09 nonmonotonic phase
history, b10 journal target path edited, b11 journal backup path
edited, b12 caller-supplied wrong target (decoy untouched, no lock
files created on it), b13 symlink substitution of the target (decoy
untouched, symlink left in place), b14 journal relocated to a copied
workdir, b15 second journal for the same target.

## Matrices (twice under `unshare -n`, byte-identical)

- Recovery/exception/binding matrix (the -12 matrix carried forward
  adapted to r3 — happy path, one-use, scope refusals, gate-3 HOLD,
  six Refusal faults, six os._exit(42) crash points with fresh-process
  recovery, corrupt journal, unknown target bytes, tampered backup,
  recover COMPLETE / ROLLED_BACK / NOT_STARTED — plus the 23 new
  trials above): **45/45 trials, 193/193 checks**, both runs sha256
  `56084b752a74a8f394f2beae2eae9357d8a35b636a414279fc455587c5c5e748`.
- Unchanged r4 gate regression, re-run twice: **46/46 trials,
  332/332 checks**, both runs sha256
  `aafd4e1b13b444600eb4d13481525aac54e840416b25d73ad84db514c16e2de3`
  — byte-identical to the pinned -11/-12 matrix; the r4 gate is
  unregressed.

Attempt 0 ran 44/45 (191/193): trial x06 exposed that `_rollback`
reused the fault-injected terminal writer, so a verified rollback was
reclassified when the auxiliary record write hit the same injected
fsync fault. Repair (the one allowed, ~1 min of ≤6): the
terminal-record write inside `_rollback` is best-effort; the
ROLLED_BACK claim rests on the verified ledger bytes + the durable
journal advance that precede it. Failed matrix + trial tree preserved
(`txn_matrix_attempt0_failed.json`, `trials_attempt0_failed/`);
failure memory published (`FAILURE_MEMORY_20261017_13.md`,
classes REAL_EXCEPTIONS_BYPASS_ROLLBACK,
TERMINAL_COMPLETE_EXISTENCE_ONLY, RECOVERY_PATHS_NOT_BOUND,
ROLLBACK_TERMINAL_WRITE_FAULT).

## Pins

- readiness_transaction_r3.py — db93f07ee057b731528a231e836e67c791a01ab779c6893fe1bda6c258a5c79a
- run_exception_binding_trials.py — 02a901eab9d5d58e9135dbf87d6787cdd77e540cc95ca7b67d5c537ad7a6effc
- txn_matrix_run1.json = txn_matrix_run2.json — 56084b752a74a8f394f2beae2eae9357d8a35b636a414279fc455587c5c5e748
- gate_matrix_run1.json = gate_matrix_run2.json — aafd4e1b13b444600eb4d13481525aac54e840416b25d73ad84db514c16e2de3
- FUTURE_READINESS_EXECUTION_PROPOSAL_R3.md — 7e391e5078d51a74d9fb97b571705b17ed8afc868c1db56999e744c0ad885592 (NOT AUTHORIZED)
- Package: research_notes/td_readiness_txn_exception_binding_20261017_13/ (SHA256_MANIFEST.txt inside)

## Scope confirmation

Offline / network-denied throughout (matrices under `unshare -n`);
zero authenticated/vendor/helper calls (spec fetch only); zero
credits; zero real-ledger writes — the pilot ledger
`research_notes/pilot_harness/credit_ledger.json` re-verified
byte-identical at sha256 7e5ccef0… after all runs, and its 0-byte
`.lock` sidecar is a pre-existing 2026-10-14 artifact, untouched;
all adoption/rollback activity on fixture copies only; zero token,
armed transport, time_series, installs, backtest/performance,
holdout, production/trading, Issue #9; -11 and -12 packages
byte-identical; deliverables UNCOMMITTED. Elapsed ≈13 min of the
≤20 cap, including the one ~1-minute repair.
