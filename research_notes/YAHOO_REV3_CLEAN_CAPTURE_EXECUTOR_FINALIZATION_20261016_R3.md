# Rev3 clean capture executor finalization (-19 r3) — REV3_CLEAN_CAPTURE_EXECUTOR_FINALIZATION_READY (candidate only)

Task: QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-FINALIZATION-20261016-19 r3.
Canonical spec: Issue #1 comment 6215975805 (fetched first via the public
API and followed exactly). Verdict: **REV3_CLEAN_CAPTURE_EXECUTOR_FINALIZATION_READY**
— offline candidate evidence only; nothing adopted. Elapsed ≈13 min of the
≤25 cap; repair ≈4 min (one executor reorder + one fixture expectation
correction, inside the one ≤5-min repair allowance). U-1 remains HOLD,
unprobed.

## Closure + proof per defect

1. **Forged COMPLETE byte-total accepted → now fails closed.** On restart
   each COMPLETE record's bytes AND hashes are recomputed from the files
   and must EQUAL the record; a mismatch is `HOLD:JOURNAL_CONFLICT`, zero
   calls — never silently corrected (R3-01: false bytes +10⁹ → CONFLICT;
   false hash → CONFLICT; restored journal verifies clean).
2. **Post-ATTEMPT failures bypassed durable HOLD → routed.** Serialization,
   ceiling, filesystem, finalization, and path-race failures after ATTEMPT
   all pass through one durable HOLD append+fsync on the locked journal fd
   (R3-02: planted temp → `HOLD:TEMP_COLLISION`, planted final →
   `HOLD:FINAL_COLLISION`, root component swap → `HOLD:PATH_RACE`; journal
   [ATTEMPT, COMPLETE, ATTEMPT, HOLD] / [ATTEMPT, HOLD]; every restart
   reproduces the exact original code AND detail with zero calls — the
   r2 degradation to generic ATTEMPT_CONSUMED_AMBIGUOUS is gone). If the
   durable append/fsync itself fails, the run returns
   `HOLD:JOURNAL_DURABILITY` and does not claim the cause was recorded.
3. **os.rename overwrote a raced destination → atomic no-replace.**
   Finalization uses renameat2(RENAME_NOREPLACE) (ctypes syscall, with a
   link()+unlink-own-temp fallback). R3-03 (real process): a watcher thread
   created the destination after the executor's temp fsync but before
   finalization → `HOLD:FINAL_COLLISION`, destination retained
   byte-identical, executor temp not deleted over the race, one durable
   terminal HOLD, restart reproduces it.
4. **Lock/journal identity → one stable journal fd.** `capture_owner.lock`
   is deleted from the design: the acquisition journal is opened ONCE
   (O_NOFOLLOW, fd-relative to the pinned control dirfd), verified a
   regular file, flocked nonblocking on that fd BEFORE any read, and held
   for every read/append/fsync through run end; the control dirfd is
   fsync'd when the journal is first created. Every record binds the fd's
   (dev, ino) identity (`journal` key). R3-04 (real processes): contender
   → `HOLD:OWNER_BUSY`, zero calls, zero journal mutation; journal path
   replaced by a symlink → `HOLD:PATH_TYPE`, no owner; journal path
   replaced by a NEW file carrying copied records (new inode) →
   `HOLD:JOURNAL_SPLIT`, zero calls — no second owner, no split records.
5. **Base path trust boundary → component-wise no-follow.** The base is
   reached from the documented trusted parent "/" by per-component
   O_DIRECTORY|O_NOFOLLOW fd-relative traversal (final component created
   by mkdirat only if absent). R3-05: base reached through a symlink →
   `HOLD:PATH_TYPE` before transport; control pre-created as a symlink →
   `HOLD:PATH_TYPE`, evil dir untouched; control swapped to a symlink
   mid-run → fail-closed `HOLD:PATH_RACE` after 1 call with all writes
   confined to the pinned dirfds/journal fd (nothing through the symlink;
   records intact on the original journal inode); post-swap contender via
   the symlinked path → `HOLD:PATH_TYPE`.
6. **Exact-key-strict schemas + transition binding.** ATTEMPT/COMPLETE/
   HOLD validate their EXACT key sets (extra or missing key →
   `HOLD:JOURNAL_CONFLICT`); a consumed HOLD must bind the currently
   pending ATTEMPT exactly; an unconsumed HOLD may not coexist with a
   pending ATTEMPT. R3-01: extra key in COMPLETE → CONFLICT; missing key
   in ATTEMPT → CONFLICT; forged HOLD with an extra key → CONFLICT.
   R3-06: the control directory contains exactly
   `acquisition_attempt_journal.qfj2` after a completed run — no lock file
   anywhere in the fixture tree — and the durable journal parses with
   exactly one terminal HOLD carrying the exact key set.

Retained smoke (R3-07, in-process virtual clock): 52 calls in frozen
order, exactly 156 payloads, deterministic twin (tree byte-identical;
journals identical modulo the journal-identity binding), restart
all-SKIP_VERIFIED with payload bytes recomputed == files. Peak RSS
22.7 MB (fixture driver).

## Trials / failures (all disclosed)

- Fixture attempt 1 crashed in R3-04 setup (the `crash` worker exits via
  os._exit(3) before writing result.json; the fixture wrongly expected
  one). Fixture-side only; no results file produced.
- Initial focused run: **FAIL, 67 checks, 3 failures** —
  (i) swaproot restart could not reproduce PATH_RACE: run_capture ensured
  the (swapped) root component before reading the journal, so restart
  died at PATH_TYPE first. Executor repair: control dir + journal are now
  opened and a durable terminal HOLD reproduced BEFORE the capture tree
  is touched. (ii)+(iii) swapctrl expectation: the fixture expected the
  mid-run control swap to complete; the executor in fact fails closed
  with a durable `HOLD:PATH_RACE`, fully confined — spec-compliant
  ("fails … or remains confined to pinned dirfds"); the fixture
  expectation was corrected to assert exactly that. NOTE: the initial
  run's results file was written to the same output path later reused by
  the repaired run and was superseded in place; its failure labels are
  recorded here verbatim.
- Repaired run: **PASS, 67 checks, 0 failures**
  (`fixture_results_run2.json`, sha256 2f608028…).

## Scope confirmation

Offline only (the spec fetch was the sole network read; sockets denied in
fixture and worker processes). Zero Yahoo/vendor/model calls, downloads,
installs, spend, authenticated GitHub operations, adoption/merge, real
capture/publication, backtest/holdout/production changes. Evidence
verified byte-identical after the run: r2 package (executor fa72e52a…),
r1 executor 1da59813…, rev3 candidate 3d3d4ef5…, accepted publisher
1d4c1923…, frozen rev2 manifest 634c4541…, parked -09 executor 8fe97abd…
(never edited/imported/run). No tracked repo file was modified by this
task. Package left uncommitted.

Package: research_notes/yahoo_rev3_clean_capture_executor_finalization_20261016_r3/
(executor clean_capture_executor_h19r3.py 10e6c07f…; fixture
run_finalization_fixture.py 1d6cdc6f…; worker proc_worker3.py 0bffc54d…;
results fixture_results_run2.json 2f608028…).
