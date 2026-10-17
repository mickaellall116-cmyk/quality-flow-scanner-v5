# FAILURE MEMORY — 20261017-13

Searchable defect classes closed by QF-TD-READINESS-TXN-EXCEPTION-BINDING-20261017-13 r1.
Base defect record: the -12 independent review (Issue #1 comment 6235656978),
verdict POSTWRITE_RECOVERY_TARGETED_PARTIAL_PASS__LIVE_HOLD_EXCEPTION_AND_BINDING.

## REAL_EXCEPTIONS_BYPASS_ROLLBACK
-12: run() caught only Refusal. An OSError from atomic evidence/card/
receipt/terminal persistence, or a RuntimeError from the dry-run hook,
escaped to finally, released both locks and could leave the candidate
ledger adopted. The -12 "ordinary faults" were all Refusal via
_maybe_fail(); they never proved real Python/I/O exception handling.
Cure (-13 r3): run() catches every Exception under the same discipline
as Refusal, locks held: post-replace failures attempt an exact
hash-verified rollback and a durable TERMINAL_ROLLED_BACK journal
state before lock release; an unverifiable rollback is journaled
TERMINAL_HOLD_MANUAL and reported HOLD_MANUAL /
ROLLBACK_UNVERIFIED — ROLLED_BACK is never claimed falsely.
Proof: trials x01-x07 (real OSError at evidence write/fsync, card
fsync, receipt write, terminal fsync, terminal journal advance;
RuntimeError from the dry-run hook) all ROLLED_BACK with exact legacy
bytes; x08 (rollback write itself fails) is HOLD_MANUAL with the
candidate still in place, explicitly not claimed rolled back.

## TERMINAL_COMPLETE_EXISTENCE_ONLY
-12: recover() classified TERMINAL_COMPLETE as ADOPTED_VERIFIED when
the target matched the candidate and the terminal-record and
dry-run-receipt files merely EXISTED. Empty, stale or tampered files
could be over-accepted.
Cure (-13 r3): strict parse + verify of the terminal record (txn id,
outcome COMPLETE, status-call count == journal), the receipt
(txn-bound, gates exactly 12 x PASS, counts 12/12), the
evidence/token-card cross-digests (card evidence_sha == sha256 of the
evidence bytes; candidate_sha bound to the journal), the candidate
target hash, and journal phase/history consistency. Any mismatch is
HOLD_MANUAL with no ledger touch. Proof: trials b01-b07 (empty
receipt, 11-of-12 receipt, wrong receipt txn, wrong terminal id,
wrong terminal outcome, tampered evidence, tampered card).

## RECOVERY_PATHS_NOT_BOUND
-12: the journal stored only target/backup basenames; recover(workdir,
target_path) accepted a caller-supplied target, never compared it to
the journal, ignored the journal's backup path and used a constructed
path. A same-hash wrong target could be finalized or restored.
Cure (-13 r3): the journal binds canonical absolute target/backup
paths, target realpath and workdir at BEGUN. Recovery validates
caller path, marker txn id, journal txn id, path bindings, hash
formats and phase/history BEFORE locks or any ledger touch; the
restore source is the journal's bound backup path. Symlink
substitution, relocated/edited journal, wrong workdir/target,
marker/journal mismatch, nonmonotonic history and a second journal
for the same target all fail closed HOLD_MANUAL. Proof: trials
b08-b15.

## ROLLBACK_TERMINAL_WRITE_FAULT (attempt 0 of this task, harness-side)
Attempt 0 ran 44/45 trials, 191/193 checks: trial x06 (OSError at
terminal:fsync) failed because _rollback reused the fault-injected
_write_terminal for its ROLLED_BACK record, so the verified rollback
was reclassified HOLD_MANUAL when the auxiliary record write hit the
same injected fsync fault. Cure: the terminal-record write inside
_rollback is best-effort; the ROLLED_BACK claim rests on the verified
ledger bytes + the durable TERMINAL_ROLLED_BACK journal advance,
which precede it. Failed matrix and trial tree preserved
(txn_matrix_attempt0_failed.json, trials_attempt0_failed/). One
repair used (~1 min of the <=6-minute allowance).
