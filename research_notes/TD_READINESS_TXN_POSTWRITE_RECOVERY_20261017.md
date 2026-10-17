# TD READINESS TXN POST-WRITE RECOVERY — -12 r1

Task: QF-TD-READINESS-TXN-POSTWRITE-RECOVERY-20261017-12 r1
Spec: GitHub Issue #1 comment 6235195991 (fetched via public API first, followed exactly)
Base: -11 package at commit dbecf03 — PRESERVED UNCHANGED (verified: no modifications)

## Verdict: READINESS_TXN_POSTWRITE_RECOVERY_PASS_OFFLINE

The -11 HOLD ground (`POLICY_A_R4_GATE_PASS_OFFLINE__READINESS_TRANSACTION_HOLD_POSTWRITE_RECOVERY`)
is cured in a new candidate revision: the readiness transaction now carries a
durable write-ahead journal, holds its locks through the terminal commit,
rolls back exactly on ANY post-replace failure, and supports cold-start
recovery that can never place a second status call. The revised future
proposal remains NOT AUTHORIZED. Zero live anything: no authenticated call,
no helper invocation, no credit, no real-ledger write.

## Journal design (readiness_transaction_r2.py)

- Created at `begin`, together with the one-use CONSUMED marker, BEFORE any
  durable step: binds txn id, target path (basename), original SHA-256,
  candidate SHA-256, backup path. Backup SHA is journaled at phase BACKED_UP —
  after the fsynced backup write, BEFORE the replace.
- Every phase advance is an atomic write (tmp + os.replace) with file and
  directory fsync: BEGUN → PREFLIGHT_OK → LOCKS_HELD → HELPER_OK →
  STATUS_CONSUMED (counter consumed and journaled BEFORE the status hook is
  invoked) → GATE3_OK → BACKED_UP → REPLACED → VERIFIED → REFROZEN →
  DRYRUN_OK → TERMINAL_COMPLETE / TERMINAL_ROLLED_BACK /
  TERMINAL_RECOVERED_HOLD / TERMINAL_HOLD_PRE. Full phase history is kept.
- Locks (owner lease flock, then ledger flock — the -11 order) are acquired
  at LOCKS_HELD and released only after the terminal journal state is
  durable, on every path including rollback.

## Post-replace failure rule (spec §2)

Any ordinary failure after REPLACED — post-write verification, evidence
write, card write, dry-run exception, dry-run non-12/12, terminal-record
write — restores the exact legacy bytes via atomic replace + fsync,
verifies the original hash, journals TERMINAL_ROLLED_BACK, writes the
terminal record, and only then releases locks. Proven by trials
t05–t10 (one per post-replace step), each: outcome ROLLED_BACK, target
byte-identical to legacy, journal terminal, terminal record present.

## Cold-start recovery (spec §3) — classification table

`recover(workdir, target)` accepts NO status or helper callable; recovery
structurally cannot place a status call (every recovery trial asserts
`status_calls_during_recovery == 0` and the journal's total stays 1).
It takes the same locks in the same order and classifies from journal +
filesystem bytes alone:

| Observed state | Classification | Action |
|---|---|---|
| No marker, no journal | NOT_STARTED | none |
| Nonterminal journal, target == original hash | PRE_REPLACE | finalize: journal TERMINAL_RECOVERED_HOLD + terminal record; ledger untouched |
| Nonterminal journal, target == candidate hash, backup verifies (hash == original, journal backup_sha matches) | POST_REPLACE_UNVERIFIED | restore exact legacy bytes (atomic + fsync + hash verify), journal TERMINAL_RECOVERED_HOLD (restored=true) |
| Journal TERMINAL_COMPLETE, target == candidate, terminal record + 12/12 receipt present | ADOPTED_VERIFIED | none (verified only) |
| Journal terminal rollback state, target == original | ROLLED_BACK | none (verified only) |
| Journal corrupt/unreadable, target bytes neither pin, or backup missing/mismatched | HOLD_MANUAL | ledger NEVER touched |

## Crash / fault injection (spec §4)

`os._exit(42)` injected at all six spec points; each crash ran in a child
process and recovery in a FRESH process:

| Crash point | Journal phase at kill | Recovery | Final ledger |
|---|---|---|---|
| after backup | BACKED_UP | PRE_REPLACE, finalized | exact legacy |
| after replace | REPLACED | POST_REPLACE_UNVERIFIED, restored | exact legacy |
| during evidence write | VERIFIED | POST_REPLACE_UNVERIFIED, restored | exact legacy |
| during card write | VERIFIED | POST_REPLACE_UNVERIFIED, restored | exact legacy |
| during dry-run | REFROZEN | POST_REPLACE_UNVERIFIED, restored | exact legacy |
| during terminal persistence | DRYRUN_OK | POST_REPLACE_UNVERIFIED, restored | exact legacy |

Every case ends in exactly one of the spec's two acceptable outcomes
(RECOVERED/HOLD here; COMPLETE is reachable only by an unkilled run,
t01). No ambiguous or half-written ledger state occurred. Negative
recovery cases: corrupt journal, unknown target bytes, and tampered
backup each yield HOLD_MANUAL with the ledger byte-identical to its
pre-recovery state (t17–t19).

## Matrices (twice under `unshare -n`, byte-identical)

- Transaction matrix: **22/22 trials, 100/100 checks**, run1 == run2,
  sha256 `86a063a31af6d1e422a0bb04d3ce44e7c66a4c31afabcdf35c2fba894c581f86`.
- Gate regression: the -11 r4 gate runner re-executed twice; both
  matrices sha256 `aafd4e1b13b444600eb4d13481525aac54e840416b25d73ad84db514c16e2de3`
  — byte-identical to the pinned -11 matrix (46/46 trials, 332/332
  checks). The r4 gate is unchanged.

## Repair used (1, within the ≤6-min allowance)

Attempt 0 scored 21/22 trials, 99/100 checks: a HARNESS defect — trial
t17 reused a trial directory whose recovery had already run (inside the
shared crash-trial helper), so the "corrupt journal" case saw an
already-restored ledger. The wrapper was not at fault. Fixed by giving
t17 a fresh child-only setup (same pattern as t19). Failed matrix and
trial tree preserved as `txn_matrix_attempt0_failed.json` /
`trials_attempt0_failed/`. A first background gate-regression launch also
used a wrong relative output path and stale /tmp trial roots; both
attempts failed with zero deliverable impact and were rerun clean —
recorded in FAILURE_MEMORY_20261017_12.md.

## Scope confirmation

Offline / network-denied throughout; zero authenticated or vendor calls
beyond the spec fetch; helper invocations 0; credits spent 0; ledger
writes 0 against the real ledger (re-verified `7e5ccef0…` after all
runs; all adoption on fixture copies in /tmp-style trial dirs inside the
package); zero token / armed transport / time_series / installs; no
backtest/performance/holdout/production/trading/Issue #9; no
merge/adoption — r2 wrapper remains an uncommitted candidate; -11 and
all prior packages byte-identical.

## Deliverables (package td_readiness_txn_postwrite_recovery_20261017_12/)

- readiness_transaction_r2.py — journal + rollback + recovery candidate
- run_recovery_trials.py — harness (also the crash-child/recovery entry)
- txn_matrix_run1.json / txn_matrix_run2.json — byte-identical
- gate_matrix_run1.json / gate_matrix_run2.json — == -11 pinned matrix
- txn_matrix_attempt0_failed.json / trials_attempt0_failed/ — preserved
- FUTURE_READINESS_EXECUTION_PROPOSAL_R2.md — revised, NOT AUTHORIZED
- FAILURE_MEMORY_20261017_12.md
- SHA256_MANIFEST.txt
