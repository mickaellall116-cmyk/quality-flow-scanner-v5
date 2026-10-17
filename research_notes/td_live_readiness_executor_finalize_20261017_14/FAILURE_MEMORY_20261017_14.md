# FAILURE MEMORY — QF-TD-LIVE-READINESS-EXECUTOR-FINALIZE-20261017-14 r1

## F1 — Fixture clock misalignment (attempt 0, harness defect)
The -14 runner's fixed clock (1792256400) was 3600 s ahead of the
accepted -11 fixture clock (1792224000) shared by the r4 gate runner
and the -11 transaction runner. The executor's own Policy A gate-3
passed, but the real r4 gate's dry-run evaluated the account evidence
as future-dated and returned gate 3 FAIL (11/12); the transaction
rolled back exactly as designed. Fix: align the -14 runner and child
driver clocks to 1792224000. Executor code was not at fault.
Preserved: `executor_matrix_attempt0_failed.json` (21/23, 78/82).

## F2 — /tmp tmpfs exhaustion (attempt 1, environment defect)
`/tmp` is a 512 MiB tmpfs. Regression scratch copies (~147 MiB) plus
trial roots filled it; the r4 gate's calendar re-derivation extracts
11 wheels into a `tempfile.mkdtemp` directory and failed with
`OSError: [Errno 28] No space left on device`, surfacing as gate 7
UNKNOWN / DERIVATION_UNAVAILABLE in the executor's e01 and as
nondeterministic 44–45/46 flakes in gate regression runs (including
one C01 two-process timing flake under four-way parallel load).
Fix: deleted the scratch copies; re-ran everything with `TMPDIR`
pointed at the overlay filesystem (`~/workspace/.tmp_qf14`), serially
for the confirmation runs. Serial confirmation: gate matrix
`aafd4e1b…` byte-identical twice; executor matrix 23/23 twice.
Preserved: `executor_matrix_attempt1_failed.json` (22/23, 79/82) and
`trials_attempt1_failed/`. Lesson: on this host, wheel-extraction
workloads must not share the /tmp tmpfs with bulk scratch; check
`df -h /tmp` before matrix runs.

## F3 — e06 ledger-drift check corrected (attempt 0 → 1, harness)
The first e06-ledger assertion expected the target to still equal the
candidate bytes after recovery, but the trial's own swap hook drifts
the ledger bytes between precheck and lock. The correct expectation —
recovery leaves exactly the drifted bytes in place, HOLD_MANUAL,
no restore — was asserted from attempt 1 onward.

## Timing note
Elapsed ≈30 minutes of the ≤35-minute cap (start 12:58:52 ET,
package manifest generated 13:28 ET), including the one repair
(F1+F2 diagnosis and serial re-runs). No scope was added; all
failures and failed attempts are preserved above and in the
attempt-suffixed matrices.
