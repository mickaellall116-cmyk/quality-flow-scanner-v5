# QF-YAHOO-QFAR1-TRUST-HARDENING-20261015-14 r1 — Work Result

**Verdict: `QFAR1_TRUST_HARDENING_PASS`** (offline scope only — see §6)

- Spec: GitHub Issue #1 comment `6206830409` (the -13 adjudication), followed exactly.
- Subject of hardening: the isolated -13 package at commit `1bb9b92`
  (publisher sha256 `d73000dd…`, 63/63 twice byte-identical, formal state
  `QFAR1_OFFLINE_PREFLIGHT_HOLD`). The -13 package is **immutable evidence**:
  it was not edited; the hardened publisher is a new pinned candidate file in
  a new package directory.
- Governing design: `YAHOO_SINGLE_BLOB_ARCHIVE_DESIGN_20261015.md` r3
  (commit `d7dc58b`, sha256 `cd9ef36d…`).
- Budget: ≤45 min total incl. one ≤8-min repair. **Elapsed ≈13 min.**
  Trial/failure ≈2 min (one crashed driver run + one wrong fixture
  expectation, both driver-side). **Repair used ≈2 min of the ≤8 allowance,
  one round, fixture-driver only — the publisher candidate was not repaired.**

## 1. The gaps, as the spec names them, and how each is closed

### Gap 1 — "Independent validation is caller-optional" (req 1)

-13's `publish(..., validation_pins=None)` / `build_container(...,
validation_pins=None)` compared member hashes **only when pins were
supplied**; omitting the argument made the publisher trust and pin whatever
bytes were on disk.
- **Closed:** `validation_pins` is now a required parameter of both
  `publish()` and `build_container()` (no default). `_require_pins()` runs
  before any disk read of payloads and before any remote call, and demands:
  a mapping whose key set is **exactly** the 156 payload rels of the pinned
  frozen manifest (`634c4541…`), every value a 64-character **lowercase**
  hex sha256. `None`, a missing pin, an extra pin, an uppercase-hex pin or a
  short pin all raise `HOLD:PINS_INVALID`. The per-member comparison against
  the pins is unconditional.
- **Fixtures (H1, 8 records):** omission → `TypeError` with 0 remote writes;
  the five malformed-pin variants → `HOLD:PINS_INVALID`, 0 writes; a
  one-byte current-disk substitution against correct pins →
  `HOLD:MEMBER_DRIFT`, 0 writes; correct pins → `PUBLISHED`.

### Gap 2 — "The journal is not crash-framed" (req 2)

-13's `_journal_append()` did one unchecked `os.write` (short writes never
completed) and `_journal_read()` silently stopped at the first malformed
line, so interior corruption could hide later durable records.
- **Closed:** the journal is now an append-only sequence of **length+hash
  framed** records — `u32be length ‖ canonical JSON payload ‖
  SHA-256(payload)` — written by a write-all loop, fsync'd per append (plus
  a directory fsync on creation). Every record carries a `seq` equal to its
  frame index. The reader tolerates **only** an incomplete final frame
  (truncated length/payload/tag at EOF). A complete frame with a bad
  checksum, bad JSON, or wrong sequence raises `HOLD:JOURNAL_CORRUPT` —
  including when later frames exist — and append refuses to write onto a
  corrupt journal.
- **Fixtures (H2, 6 records):** 4-frame round-trip (seq 0..3); **byte-cut
  at every one of the 358 offsets** of the journal file returns exactly the
  complete-frame prefix and never raises; interior payload corruption in
  frame 0 of 4 → `HOLD:JOURNAL_CORRUPT`; tag corruption in frame 2 of 4 →
  `HOLD:JOURNAL_CORRUPT`; a sequence forgery with a *valid* checksum
  (seq 99 in frame 1) → `HOLD:JOURNAL_CORRUPT`; append onto a corrupt
  journal → `HOLD:JOURNAL_CORRUPT`.

### Gap 3 — "The ceiling-size publication path is untested and its RSS claim is incomplete" (req 6)

-13's step 4 reads the full container, joins it, base64-encodes it and
stringifies it; the disclosed 19.19 MiB figure measured streaming **build
only**, and protocol fixtures exercised ~350 KB.
- **Closed by measurement, not by claim:** a ceiling-size capture was
  solved so that Σ over all 158 physical members == `67,108,864` exactly
  (A-10 record), materialized, and published **end to end** in a clean
  subprocess against the fake remote — seal → base64 blob creation →
  tree → commit → single ref update → re-fetch with full DAG verification.
  Result: `PUBLISHED`, container length exactly `67,118,605` bytes (the
  adjudicated maximum; base64 form `89,491,476`).
- **Honest numbers for the complete publisher path** (worker process
  `ru_maxrss`, volatile, in META): elapsed **2.173 s / 1.998 s** and peak
  RSS **305.31 MiB / 314.11 MiB** across the two suite runs. The 19.19 MiB
  build-only number is **not** claimed as publisher peak; the complete path
  at the admitted maximum peaks at ≈305–314 MiB on this host (7.9 GB RAM),
  dominated by the in-memory base64 assembly, which remains as designed.
  Ceiling+1 still `HOLD:CEILING` with 0 remote writes (A-10).

### Additional hardening (spec) — staging names and module-global state (reqs 4, 5)

- **Fixed `spool.tmp`/`container.tmp`:** replaced by **attempt-unique**
  O_EXCL staging names (`<kind>.<pid>.<counter>.<random>.tmp`). Both files
  are unlinked on controlled completion (after the seal self-check; the
  open fds remain valid) and on controlled failure. A name collision maps
  to `HOLD:STAGING_COLLISION`; an unlink failure maps to
  `HOLD:STAGING_CLEANUP`. Fixtures (H4, 4 records): a pre-intent crash
  (BaseException at the prescribed phase) leaves the staging directory
  **empty**; the clean retry publishes with a container hash identical to a
  fresh build (no stale bytes reused); stale fixed-name files from the old
  scheme are ignored; a forced name collision → `HOLD:STAGING_COLLISION`.
- **Module-global `_MSG_ID`:** removed entirely. The capture ID is passed
  explicitly through `_verify_remote(...)`; verification is safe under
  concurrent calls with different IDs. Fixtures (H5, 2 records): source
  contains no `_MSG_ID`; a second capture under a different ID on the same
  remote/journal verifies independently → `PUBLISHED`.

### Req 3 — interprocess intent fencing

- **Closed:** `publish()` runs under a per-journal interprocess fence —
  an `flock(LOCK_EX)` on `<journal>.lock` held for the whole protocol; the
  OS releases it if the holder dies. A second process cannot create a first
  intent; it reconciles from the framed journal instead.
- **Fixture (H3, 1 record):** two real OS processes invoke `publish()`
  concurrently for the same capture against a shared directory-backed fake
  remote, sharing journal and staging. Outcome: statuses
  `{PUBLISHED, ALREADY_PUBLISHED_VERIFIED}` (sorted), the journal contains
  **exactly 1 intent frame and 1 published frame**, and the remote contains
  **exactly 1 commit** for the capture.

### Req 7 — affected cases re-run

A-01 (determinism twin: independently materialized trees, permuted
order/mtimes → byte-identical container, blob id and container hash),
A-07 (crash after blob/tree/commit → restart `HOLD:ID_CONSUMED`; lost
ref-update response → `HOLD:API`, restart `PUBLISHED_BY_RECORDING` with
exactly one commit), A-10 (exact-ceiling seal + full publication; ceiling+1
HOLD), A-12 (raw JSON error body / encoding lie / bad padding →
`HOLD:ENCODING`), A-14 (W1/W2 → `HOLD:PARENT_DRIFT` with zero
publisher-created objects; W3 → `HOLD:REF_RACE`) — all re-run inside the
hardening suite. Unaffected -13 evidence is preserved by immutable pin
(§5) rather than re-run.

## 2. Results

**35 records, 35/35 PASS in both runs; `results_run1.json` and
`results_run2.json` are byte-identical** (independently materialized trees
per run). Volatile measurements (ceiling elapsed / peak RSS, suite RSS)
are in `meta_run1.json` / `meta_run2.json` only.

## 3. Package (all hashes in `SHA256_MANIFEST.txt`)

`research_notes/yahoo_qfar1_trust_hardening_20261015/`:

- `qfar1_publisher_h14.py` — hardened publisher candidate (new file;
  public surface unchanged: `publish` / `HoldError`)
- `run_trust_hardening_fixture.py` — suite driver (in-memory fake remote)
- `shared_remote.py` — directory-backed fake remote for multi-process cases
- `fence_worker.py`, `ceiling_worker.py` — subprocess entries (reqs 3, 6)
- `results_run1.json`, `results_run2.json` — byte-identical
- `meta_run1.json`, `meta_run2.json` — volatile measurements

## 4. Scope confirmation

Offline only: zero Yahoo/vendor/model/API calls, zero downloads beyond the
spec-comment fetch, zero installs, zero spend, zero authenticated GitHub
operations, zero real publication, zero capture/backtest/holdout/production
changes. U-1 was **not** probed and remains **HOLD**; rev.3 adoption,
Yahoo authority, data qualification and corrected performance remain
**HOLD** regardless of this verdict, per the spec.

## 5. Immutability verification (post-run)

- Parked executor `execute_capture.py`: `8fe97abd…` — byte-identical,
  never edited, imported or run.
- Parked -11 `publish_snapshot.py`: `1b50db56…` — byte-identical.
- -13 package: publisher `d73000dd…`, driver `a57518f7…`,
  results (both runs) `e5a5c0a4…`, memo `4a21243e…`,
  `SHA256_MANIFEST.txt` `749e75a7…` — all byte-identical to the pins taken
  before the hardening work began.
