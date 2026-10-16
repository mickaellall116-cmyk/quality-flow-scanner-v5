# QF-YAHOO-QFAR1-RECOVERY-ATOMICITY-20261015-15 r1 — memo

**Verdict: `QFAR1_RECOVERY_ATOMICITY_PASS`** (offline scope only; per the spec,
even PASS leaves U-1, rev.3 adoption, Yahoo authority, data qualification and
corrected performance on HOLD).

Spec: GitHub Issue #1 comment `6207508054` (the -14 adjudication,
`QFAR1_TRUST_HARDENING_HOLD_PARK` at immutable commit `cf929e0`), followed
exactly. New isolated candidate derived from the pinned -14 source
(`qfar1_publisher_h14.py`, sha256 `074ade29…`); the -13 package (commit
`1bb9b92`) and the -14 package (commit `cf929e0`) are immutable evidence and
were not edited or run from their directories. Budget ≤30 min, no repair
allowance; elapsed ≈9 min (spec fetch 03:57Z → packaging ≈04:06Z). One
fixture-driver mechanical fix is disclosed below; the candidate publisher was
not repaired in-round.

## The three -14 blockers and how each is closed

### 1. Torn final journal frame ignored, then appended behind (req 1/2/3)

The -14 journal tolerated a torn tail on read but appended new frames behind
the torn bytes, so the next read could never reach the durable replacement
record. The -15 journal makes recovery part of the append itself:

- `_journal_append()` opens the journal `O_RDWR|O_CREAT` and first runs
  `_journal_recover_fd()`: parse, and if the file extends past the exact
  verified end, `ftruncate` to that offset and `fsync` — **before** any new
  bytes are written. Recovery + append are one unit under the per-capture
  fence (`publish()` holds `_Fence` for every call). A failed
  truncate/fsync is a named `HOLD:JOURNAL_RECOVERY`; corruption raises
  `HOLD:JOURNAL_CORRUPT` before any truncation.
- Evidence (req 3): **cut→append→reopen at every byte offset** of a 4-frame
  journal (394 cuts): after recovery+append the journal reads back as exactly
  the verified prefix plus the one new record, and the file ends exactly at
  the new verified end.

### 2. Unauthenticated, unbounded frame length (req 1/3)

The -14 `_parse_frames()` trusted the u32 length: a flipped interior length
silently truncated the parse, hiding later durable frames. The -15 frame
protects the boundary itself:

```
header(13) = magic "QFJ1" (4) || version u8 (1) || length u32be (4)
             || length complement u32be (4)
frame      = header || payload || tag(32),  tag = SHA-256(header || payload)
```

- Length is bounded by `MAX_FRAME_PAYLOAD = 1,048,576` and cross-checked
  against its complement **before** it may size any read or drive control
  flow. Magic/version mismatch, complement mismatch, or an out-of-bound
  length raises `HOLD:JOURNAL_CORRUPT` **wherever it occurs** — a corrupt
  length is never accepted as an ordinary torn tail. Only a byte-prefix tear
  of a well-formed frame (valid header, incomplete payload/tag) is a torn
  tail. The tag covers the framing fields plus the payload.
- Evidence: all **32 length/complement bit-corruption variants** (frames 0
  and 2, every byte of both fields, low and high bit, later valid frames
  present) → `HOLD:JOURNAL_CORRUPT`; a fully self-consistent forged length
  above the bound (valid complement **and** valid tag), as sole frame and as
  an interior frame, → `HOLD:JOURNAL_CORRUPT`. Retained -14 H2 coverage under
  the new frame: interior payload flip, tag flip, sequence forgery with valid
  tag, append-onto-corrupt — all `HOLD:JOURNAL_CORRUPT`.

### 3. Spool-then-staging collision leaked the first fd/file (req 5)

In -14 `build_container`, if the spool `O_EXCL` succeeded and the container
`O_EXCL` then collided, the exception was raised before the cleanup scope was
entered: the first fd and file leaked. In -15 the two creates are wrapped in
an all-or-nothing rollback: on any allocation failure, whatever this attempt
created is closed and unlinked before the failure surfaces; a rollback
failure is its own named `HOLD:STAGING_CLEANUP`, and a name collision remains
`HOLD:STAGING_COLLISION`.

- Evidence: forced **second-name collision** (spool succeeds, container name
  pre-occupied) → `HOLD:STAGING_COLLISION`, staging afterwards contains
  **only** the pre-existing file (the rollback never unlinks what it did not
  create), **open-fd delta 0**, and a clean retry builds with the fresh
  deterministic container hash. Forced same-name collision → staging empty,
  fd delta 0. Forced rollback-unlink failure → `HOLD:STAGING_CLEANUP`, fd
  delta 0, and the leftover file remains visible in staging (the failure is
  surfaced, not masked).

## Req 4 — real-process partial-frame crash/restart

`crash_worker.py tear` appends an intent-shaped record through the real
`qp._journal_append` with `os.write` capped at half the frame, then dies via
`os._exit(3)`: the journal on disk is exactly the first 64 bytes of the real
frame, and a read returns the empty verified prefix. A fresh process then
publishes against the shared directory-backed remote: recovery truncates the
torn intent, and the run ends `PUBLISHED` with the journal containing exactly
**one intent and one published record** (no torn bytes, no `torn_marker`;
file size == verified end) and exactly **one reachable commit**. A second
restart returns `ALREADY_PUBLISHED_VERIFIED` with the journal and commit
count unchanged.

## Req 6 — re-runs (only the affected cases, twice)

- H2 (journal) — as extended above for req 1/2/3.
- H3 (two-process intent fencing, shared remote): statuses
  `[ALREADY_PUBLISHED_VERIFIED, PUBLISHED]`, exactly 1 intent frame,
  1 published frame, 1 commit.
- H4 (staging) — pre-intent crash leaves staging empty; clean retry publishes
  with hash == fresh build; plus the req-5 collision cases above.
- A-07 — crash after blob / tree / commit → restart `HOLD:ID_CONSUMED`;
  lost ref-update response → `HOLD:API`, restart `PUBLISHED_BY_RECORDING`
  with exactly 1 commit.
- The accepted pin/ceiling/global-state evidence from `cf929e0` is reused;
  the 64 MiB ceiling fixture was **not** repeated, per spec.

## Results and determinism

**23 records, 23/23 PASS in both runs; `results_run1.json` and
`results_run2.json` are byte-identical** (sha256 `2dac2660…` each;
independently materialized trees). Per-case detail is in the results files.

## Disclosure

One mechanical fixture-driver fix was needed before run 1: the carried-over
fake-remote slice referenced `base64`, which the new driver's import header
omitted; one import line was added to the driver. The candidate publisher
(`qfar1_publisher_h15.py`) was not modified after its initial derivation, and
no publisher defect was found in-round.

## Scope confirmation

Offline / no-socket throughout: the spec-comment fetch was the only network
read. Zero Yahoo/vendor/model/API calls, zero downloads, zero installs, zero
spend, zero authenticated GitHub operations, zero real publication, zero
capture/backtest/holdout/production changes. U-1 unprobed (HOLD). Verified
byte-identical after the runs: parked executor `execute_capture.py`
`8fe97abd…` (untouched, unrun), -14 publisher `074ade29…`, and both prior
packages verify `OK` against their own `SHA256_MANIFEST.txt`; `git status`
shows no modification to either prior package.

## Package

`research_notes/yahoo_qfar1_recovery_atomicity_20261015/` — new candidate
`qfar1_publisher_h15.py`, fixture driver `run_recovery_atomicity_fixture.py`,
`crash_worker.py`, `fence_worker.py`, `shared_remote.py`,
`results_run1.json` / `results_run2.json`, `meta_run1.json` / `meta_run2.json`,
`SHA256_MANIFEST.txt`. Left uncommitted in the worktree.
