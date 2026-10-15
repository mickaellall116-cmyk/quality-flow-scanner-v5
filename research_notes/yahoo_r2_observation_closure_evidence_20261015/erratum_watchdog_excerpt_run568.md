# ERRATUM — watchdog_excerpt_run568.txt is mislabeled (correction, not a rewrite)

Issued by QF-YAHOO-R2-OBSERVATION-CLOSURE-20261015-03 r1, 2026-10-15.

The file `research_notes/yahoo_feed_recovery_raw_20261014/watchdog_excerpt_run568.txt`
(commit `895dd59`) is **mislabeled**. Its two lines were extracted from the
"V5.4 forward-test cycle — 2026-10-15 00:41 EDT run" section of
`~/memory/2026-10-15.md` and describe **run 569**, not run 568:

- heading in the pinned file says "run 568", but the body records
  `state runs=569`, `last_run 2026-10-15T04:49:00Z`, and `cycle_duration 468.2s`
  — the run-569 interval (run 569's raw body: coverage duration 466.6s,
  finished 2026-10-15T04:49:02Z).

Disposition:

- The pinned file at `895dd59` is immutable history and is **not** rewritten or
  deleted by this closure; this erratum is the correction of record.
- The run-569 data in that file must never be cited as run-568 evidence.
- The authentic contemporaneous run-568 record is pinned in this package as
  `run568_authentic_record.txt` (from `~/memory/2026-10-14.md`, 23:41 + 23:50 EDT
  watchdog/cycle sections).
- The README of `yahoo_feed_recovery_raw_20261014/` repeats the mislabel
  ("watchdog log lines for run 568 (23:41 ET cycle…)"); the same correction
  applies to that sentence. The 23:41 ET cycle was indeed run 568 and was
  HEALTHY — but the excerpt pinned under its name is run 569's.
