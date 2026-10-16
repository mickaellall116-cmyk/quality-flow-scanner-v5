# Rev3 clean capture executor hardening (-19 r2) — REV3_CLEAN_CAPTURE_EXECUTOR_HARDENED_READY (candidate only)

**Task:** QF-YAHOO-REV3-CLEAN-CAPTURE-EXECUTOR-HARDENING-20261016-19 r2
**Canonical spec:** GitHub Issue #1 comment 6214564508 (fetched first via the public API and followed exactly).
**Verdict: `REV3_CLEAN_CAPTURE_EXECUTOR_HARDENED_READY`** — offline hardening scope only. Nothing adopted; no Yahoo call, capture, or publication authorized or made; U-1 remains HOLD.

## Budget

≈12 minutes elapsed of the ≤35-minute cap. **Repair minutes: 0** — the single initial fixture run passed (77/77); no repaired run was needed or made. One real-process run only, per spec.

## Inputs (all verified byte-identical before and after)

- r1 executor (commit 298a85e): `1da598136fd133ec0433eaaf456db27203624a4ec8d97f0ff4f82d505a4003bc` — preserved unchanged.
- r1 fixture results: run1 `bab5f83c…` (FAIL, preserved), run2 `20adeb60…` (103/103).
- rev3 candidate (0f562d9): `3d3d4ef51e54f9e6d9bce6119673ddd7e41825049d13c58bead3b19bf4021248` — consumed by the executor under its own pin check.
- Accepted publisher (53bdc67): `qfar1_publisher_h16.py` `1d4c192324744c77e294c0b3190e88666dce583b14ef4412b3e31f85127fdc10` — imported read-only by the fixture for the compatibility smoke only.
- Frozen rev2 manifest: `634c4541a8b30ade50e45898e80ee65806fa323c953020edc149530642d9bef3` — untouched; the live pin remains rev2.
- Parked -09 executor `execute_capture.py`: `8fe97abd0c081bf0c4269c412eb8f4e7e9f767b29a1ada362b36e4d2da16b22c` — never edited, imported, or run.

## How each adjudicated gap is closed

1. **No owner fencing (r1 gap 1)** → `_OwnerLock`: a nonblocking `flock(LOCK_EX|LOCK_NB)` on `capture_owner.lock` in the sibling control directory, acquired **before** the acquisition journal is read and held until the run ends (fd closed in `finally`). A live second process stops with `HOLD:OWNER_BUSY` before any transport call and with zero journal mutation. No age-based takeover: owner death releases the lock via the OS, and the successor reconciles the journal — a consumed attempt is never repeated (R2-01, R2-02).
2. **Pre-existing temp deleted (r1 gap 2)** → strict write-once: the r1 `os.unlink(tmp)` is gone. `_write_once_fd` never unlinks or overwrites any existing temp or final path; a pre-existing temp is retained byte-identical and raises `HOLD:TEMP_COLLISION` — detected in the pre-run census (before any call) or at the affected write. The executor performs no cleanup deletions anywhere (R2-03).
3. **Component swap (additional hardening)** → trusted dirfds for base/root/control/raw/actions/meta are pinned at setup; every file operation is fd-relative with `O_NOFOLLOW`; pre-existing symlink/non-directory components are `HOLD:PATH_TYPE`; directory identities `(st_dev, st_ino)` are re-verified after each symbol's writes and before the COMPLETE record — a swap or identity change ends in `HOLD:PATH_RACE`, and writes physically cannot escape the pinned inodes (R2-07, real process).
4. **Wall crossed after limiter sleep (r1 gap 3)** → after `limiter.wait()` returns, elapsed wall time is re-checked **before** the ATTEMPT append and the transport call; at/over 1,800 s the run ends with a durable `HOLD:WALL_CEILING` and **zero new ATTEMPT, zero new call** — the forbidden start does not consume an attempt (`attempt_consumed=false`) (R2-04).
5. **Failure cause not durable (r1 gap 4)** → every handled post-journal failure (429, transport, shape/schema/meta/partial, per-symbol/row/total ceilings, wall) appends + fsyncs one schema-strict `HOLD` record to `acquisition_attempt_journal.qfj2` — no third control file — binding capture ID, symbol (or null), exact code + detail, the consumed-attempt flag, and clock. Restart validates the record and **reproduces the original code and detail with zero calls** (R2-04, R2-05).
6. **Strict schema/order (spec item 6)** → `_validate_records` validates every ATTEMPT/COMPLETE/HOLD record: capture ID equality, symbol membership, exact rel set, 64-hex hashes, nonnegative integer byte total, numeric clock, and legal transition/order against the frozen 52 plan (strictly increasing ATTEMPT order, COMPLETE closes the pending ATTEMPT, HOLD is terminal and unique). Duplicate/conflicting/malformed HOLD records fail closed as `HOLD:JOURNAL_CONFLICT` with zero calls. Resumed total-ceiling accounting **recomputes completed payload bytes from the files on disk**; the journal's `bytes` field is never trusted (R2-06, including a journal whose COMPLETE `bytes` was inflated by 10⁹ — restart still completes with the true byte count).

## Fixture (focused, real-process, no-socket) — run 1: PASS, 77 checks, 0 failures

- **R2-01 (10)** — two simultaneous real processes on one capture: the contender got `HOLD:OWNER_BUSY` with zero calls and zero journal mutation (journal bytes compared before/after); the owner completed with exactly 52 calls, 104 journal records (one ATTEMPT per symbol in plan order, no duplicate sequences or final writes), exactly 156 payloads.
- **R2-02 (4)** — owner process killed (`os._exit(3)`) inside the first call, after the fsynced ATTEMPT: journal holds exactly that ATTEMPT; the successor acquires the OS-released lock and stops with zero-call `HOLD:ATTEMPT_CONSUMED_AMBIGUOUS`.
- **R2-03 (6)** — pre-existing temp (sentinel bytes) → `HOLD:TEMP_COLLISION`, pre-existing unjournaled final → `HOLD:FINAL_MISMATCH`; both zero calls, both files retained byte-identical.
- **R2-04 (6)** — limiter sleep crossing the wall: first call ends at elapsed 1799.0 s, second completes, the third symbol's post-sleep re-check fires at exactly 1800.0 s — journal shape is ATTEMPT/COMPLETE ×2 then the durable HOLD, no third ATTEMPT; restart reproduces `HOLD:WALL_CEILING` with zero calls.
- **R2-05 (22)** — 429 / schema / partial / total-ceiling trials: each ends `INCOMPLETE_HOLD` with exactly one terminal durable HOLD record; each restart reproduces the original code **and detail** with zero calls.
- **R2-06 (13)** — malformed HOLD (non-string detail), duplicate HOLD, HOLD-after-COMPLETE, consumed-without-ATTEMPT, record-after-HOLD: all `HOLD:JOURNAL_CONFLICT`, zero calls. False byte-total COMPLETE: restart completes with payload bytes recomputed from files, journal figure ignored.
- **R2-07 (6)** — real-process directory-component swap: during the first call, `raw/` is renamed aside and replaced by a symlink to an outside directory. Result: `HOLD:PATH_RACE`; the payload write landed in the pinned dirfd inode (`raw_moved/`), **nothing was written through the symlink**; the journal holds the ATTEMPT only — no COMPLETE blessed the raced write.
- **R2-08 (10)** — retained r1 happy-path smoke: 52 calls in frozen order, exactly 156 payloads, byte-identical deterministic twin (tree + journal); fixture-side validator pins → accepted publisher seals exactly 158 and `publish` → PUBLISHED against a fake remote; socket denial verified in-process. The unrelated r1 negative matrix was not repeated, per spec; the 64 MiB publisher/journal suites were not rerun.

**Peak RSS: 32.01 MB** (fixture driver process, `ru_maxrss`; the R2-01 owner is a separate short-lived process and is not included in that figure — no whole-fixture RSS claim beyond the driver is made).

## Machine diff r1 → r2

`executor_diff_r1_to_r2.txt` (unified diff, 727 lines; 420 additions / 192 deletions against the r1 executor). The delta is confined to: the owner lock, fd-relative filesystem layer (`_ensure_dir`, `_write_once_fd`, `_read_file_fd`, `_census_root`, identity rechecks), the post-limiter wall re-check, the durable-HOLD `fail()` path, `_validate_records` replacing `_journal_state`, record `capture_id` fields, and the module docstring/TASK_ID. `_serialize`, `load_plan`, `Limiter`, and the QFJ2 framing are unchanged from r1.

## Scope confirmation

Offline only — the spec fetch was the sole network read; sockets were denied in every fixture/worker process. Zero Yahoo/vendor/model/API calls, downloads, installs, spend, authenticated GitHub operations, adoption/merge, real capture/publication, backtest/holdout/production changes. All prior evidence verified byte-identical after the run (pins above). The r2 package is left **uncommitted** in the worktree.
