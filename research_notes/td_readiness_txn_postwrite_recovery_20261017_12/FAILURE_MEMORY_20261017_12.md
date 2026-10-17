# FAILURE MEMORY — 20261017-12

Searchable keys: POSTWRITE_RECOVERY, JOURNAL_CORRUPT_HOLD_MANUAL,
TXN_MATRIX_ATTEMPT0, GATE_REGRESSION_PATH_ERROR

1. TXN_MATRIX_ATTEMPT0 (harness defect, wrapper not at fault): t17
   "corrupt journal" trial reused the shared crash-trial helper, which
   runs recovery BEFORE returning — so by the time the journal was
   corrupted, the ledger had already been legitimately restored to
   legacy and the check `target_untouched_candidate` failed (21/22,
   99/100). Lesson: a negative test that mutates state must own its
   fixture end-to-end; never corrupt evidence in a directory whose
   recovery already ran. Preserved: txn_matrix_attempt0_failed.json,
   trials_attempt0_failed/.

2. GATE_REGRESSION_PATH_ERROR (operator error, zero deliverable
   impact): the first background launch of the -11 gate runner used a
   `../../` output path from the package dir (one level too many) and
   both launches collided with stale /tmp trial roots left by that
   attempt (the -11 runner does not clean its trials root). Both runs
   failed noisily (FileNotFoundError / FileExistsError) and were rerun
   clean in the foreground; final matrices are byte-identical to the
   pinned -11 matrix. Lesson: clean the trials root before re-running
   the r4 gate harness, and resolve output paths absolutely.
