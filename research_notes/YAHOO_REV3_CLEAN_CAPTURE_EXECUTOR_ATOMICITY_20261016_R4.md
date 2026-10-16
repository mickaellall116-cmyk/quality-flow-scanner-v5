# QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-ATOMICITY-20261016-19 r4 — atomicity correction

**Verdict: `REV3_CLEAN_CAPTURE_EXECUTOR_ATOMICITY_READY`** (candidate only; nothing adopted;
no Yahoo authority; U-1 remains HOLD).

Canonical spec: Issue #1 comment `6217441495`, fetched via the public API before any work and
followed exactly. Budget ≤20 min incl. one ≤4-min repair: **elapsed ~7 min, repair 0 min** —
the single fixture trial passed on its first run, so no repaired trial exists.

## Inputs (verified byte-identical before and after)

- r3 executor `10e6c07f2b850bc10d7b9d852ce1fc13fd9eec87ae8017e4e69fd6be7f01c242` (commit 0cdc8cf) — delta base, unmodified.
- rev3 candidate `3d3d4ef51e54f9e6d9bce6119673ddd7e41825049d13c58bead3b19bf4021248` — consumed by hash pin.
- r1 executor `1da59813…`, r2 executor `fa72e52a…`, frozen rev2 manifest `634c4541…`,
  accepted publisher `1d4c1923…`, parked -09 executor `8fe97abd…` (never edited/imported/run).

## Delta (executor `clean_capture_executor_h19r4.py`)

**A. Coordination fence (defect 1 — empty-file journal split).** The pinned per-capture
control-directory fd is now flocked nonblocking (`HOLD:OWNER_BUSY` for a contender) BEFORE the
journal is opened/read, and held through run end, in addition to the r3 journal-fd flock. A new
`_assert_fences()` runs before every ATTEMPT append, transport call, and COMPLETE append: the
control path and the journal pathname must still resolve (no-follow) to the pinned control-dir
identity and the locked journal fd's (dev, ino). An empty, copied, or symlinked journal-path
replacement can therefore never produce a second transport owner, and the live owner fails
closed (`HOLD:JOURNAL_SPLIT` / `HOLD:PATH_RACE`) before its next call. No lock file, no third
control artifact.

**B. Temp identity through publication (defect 2 — temp fd closed early).** `_write_once_fd`
keeps the O_EXCL temp fd OPEN from creation through publication, pins its (dev, ino), and
requires the temp pathname to still name that inode immediately before publishing. Publication
is a same-directory hard link with `follow_symlinks=False`; the final path must then name the
pinned inode (a raced link naming another inode is removed — it is a dirent this call created —
and yields `HOLD:FINAL_COLLISION`); directory fsync; only the still-verified same-run temp is
unlinked; directory fsync again. Substituted temps (regular file or symlink) are retained
untouched and durably HOLD.

**C. No durable-handling bypass (defect 3 — OSError escapes).** Ordinary `OSError` from payload
write/fsync/link/unlink/finalization/path-recheck after ATTEMPT is routed through the durable
`fail()` path as `HOLD:FILESYSTEM`. ATTEMPT and COMPLETE append failures are centralized in
`durability_result()`: no transport call follows a failed ATTEMPT append, and the run returns
`HOLD:JOURNAL_DURABILITY` without claiming any cause was recorded (the pre-existing `fail()`
durability branch likewise names the original cause as NOT recorded).

**D. All-trials evidence (defect 4).** Exactly one fixture trial was run; its results file
(`fixture_results_run1.json`) is preserved as-is in this package. No trial was overwritten,
superseded, or deleted. (Two authoring corrections to the fixture were made before the first
trial ran; no trial was consumed by them.)

## Evidence — `fixture_results_run1.json`: PASS, 58 checks, 0 failures (one run)

- **R4-01 (7)** real processes: journal pathname replaced with an EMPTY file while the owner
  holds the fences → contender `HOLD:OWNER_BUSY`, 0 calls; owner detects the split before its
  next call, ends `HOLD:JOURNAL_SPLIT` with exactly 1 call total; the durable HOLD landed on
  the pinned journal inode (the renamed-aside original); the empty replacement was never written.
- **R4-02 copy (4) / R4-03 symlink (5)**: mid-run journal-path replacement → owner
  `HOLD:JOURNAL_SPLIT`, 0 further calls; copied file and symlink target received no owner appends.
- **R4-04 file (6) / R4-05 symlink (7)**: temp substituted in the finalize window →
  `HOLD:FINAL_COLLISION`; foreign bytes never published at the final path, foreign temp/symlink
  and target retained byte-identical; durable HOLD recorded; restart reproduces it, 0 calls.
- **R4-06a–d (3/2/2/2)**: injected write/fsync/link/unlink `OSError` after ATTEMPT → exactly one
  durable terminal `HOLD:FILESYSTEM`; restart reproduces it with 0 calls (06a).
- **R4-06e (4)**: ATTEMPT append failure → `HOLD:JOURNAL_DURABILITY`, 0 transport calls, empty
  journal, no persistence claimed. **R4-06f (4)**: COMPLETE append failure → durability verdict,
  journal holds only the ATTEMPT (no fabricated HOLD). **R4-06g (5)**: HOLD append failure behind
  a transport failure → exactly one HOLD append attempt, no retry, cause explicitly NOT recorded.
- **R4-07 (7)** retained smoke: full 52-call run COMPLETE; control dir contains exactly the
  acquisition journal (no lock artifact anywhere); restart all SKIP_VERIFIED, 0 calls;
  156 payloads on disk. Peak RSS 20.07 MB (fixture driver).

Determinism: the r4 scope per spec is the focused cases + retained smoke above; the
byte-identical twin evidence of r2/r3 is retained by reference, not rerun.

## Scope

Offline only (spec fetch the sole network read; sockets denied in fixture and workers). Zero
Yahoo/vendor/model calls, downloads, installs, spend, authenticated GitHub operations,
adoption/merge, real capture/publication, qualification, backtest/holdout/production changes.
All prior packages and pins verified byte-identical after the run; the parked -09 executor was
never edited, imported, or run. Package left uncommitted in the worktree.
