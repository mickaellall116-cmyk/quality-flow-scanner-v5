# FAILURE MEMORY — QF-TD-POLICY-A-LIVE-READINESS-PACKET-20261017-11 r1

Searchable keys: `R4_ADAPTATION_PATH_GLUE`, `TRIAL_DEFS_AFTER_TRIALS_LIST`,
`GO_SHAPE_PRECEDES_CEILING_CODE`, `RECEIPT_VS_FAILED_CODES_LIST`,
`SUBPROCESS_HELPER_PACKAGE_LOCALITY`, `ONE_CALL_CODE_PRECEDENCE`,
`SMOKE_MATRIX_OVERWRITTEN_BY_RERUN`.

What failed during the build (all in new -11 glue; no pinned base defect):

1. `TRIAL_DEFS_AFTER_TRIALS_LIST` — the copied r4 runner defined the new
   Policy A trial helpers after the module-level TRIALS list that references
   them: NameError at import. Fix: moved the defs above TRIALS.
2. `R4_ADAPTATION_PATH_GLUE` — the copied runner located `live_driver_r3.py`
   and the C01 lease subprocess scripts relative to its own package; in r4
   those live in the -08 package (driver) and must be r4 copies (holder/
   contender import the gate by name, so r3 copies would have evaluated
   r4-shaped evidence with r3 semantics — holder died silently). Fix:
   driver path → -08 package; holder/contender copied into the r4 package
   with the import switched to `dispatch_gate_r4`; helper stub copied too
   (the holder's seam override resolves the stub relative to its own dir).
3. `GO_SHAPE_PRECEDES_CEILING_CODE` — the A02 ceiling-drift test also
   mutated the GO record's ceiling, so gate 2 correctly reported
   GO_RECORD_MALFORMED before POLICY_CEILING_MISMATCH. Test defect, not a
   gate defect: the isolated ceiling test now mutates packet + authority
   only.
4. `RECEIPT_VS_FAILED_CODES_LIST` — the A05 boundary-PASS test asserted the
   gate-3 PASS code against the trial facts' code list, which contains only
   non-PASS gates. Corrected to read the receipt's gate list.
5. `ONE_CALL_CODE_PRECEDENCE` — the wrapper's `call_status` checked state
   before the one-call counter, so a repeat call after a successful first
   call reported ORDER_VIOLATION instead of STATUS_CALL_ALREADY_MADE. The
   ceiling itself held (hook called once); the counter check now runs first
   so the refusal names the real reason.
6. `SMOKE_MATRIX_OVERWRITTEN_BY_RERUN` — disclosure: the failed smoke
   matrices (gate 42/46 and 45/46, transaction 19/20) were written to the
   same output filename by successive smoke runs and the final passing
   smoke overwrote them. The failed trial TREES are preserved in this
   package (`trials_gate_attempt_failed_45of46/`,
   `trials_txn_attempt_failed_19of20/`); every defect, its trial, and its
   fix are enumerated in the memo §"Attempts and repair accounting".
   Lesson carried forward: smoke outputs get attempt-suffixed names.
