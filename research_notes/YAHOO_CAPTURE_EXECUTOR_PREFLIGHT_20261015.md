# Yahoo Capture Executor Preflight — QF-YAHOO-CAPTURE-EXECUTOR-PREFLIGHT-20261015-09 r1

**Verdict: `CAPTURE_EXECUTOR_PREFLIGHT_PASS`** (preflight scope only — see §5)

Spec: GitHub Issue #1 comment `6197512446` (2026-10-15T16:53:33Z), followed exactly.
Base packet: the frozen r2 preflight at commit `0d7ccfb`; manifest bound by exact
SHA256 `634c4541a8b30ade50e45898e80ee65806fa323c953020edc149530642d9bef3`.
Elapsed: ≈6 minutes total (spec fetch 17:01Z → package verified 17:07Z) of the
≤45-minute budget; repair ≈2 minutes of the ≤10-minute allowance (fixture
authoring corrections before the first full run; zero failed full-suite trials).

## 1. What was built

`execute_capture.py` — the executor the -08 preflight deliberately did not build —
proven offline against the frozen manifest and the qf-data-archive write path:

- **Bindings, checked before any transport:** manifest file SHA256 must equal the
  pinned `634c4541…` (`HOLD:MANIFEST_DRIFT`); frozen order/count verified (exact
  `i` = 1…52 sequence, 52 unique symbols, count == `max_requests_total`;
  `HOLD:ORDER_DRIFT`); runtime pins re-verified against the live environment —
  Python 3.12.3 / pandas 2.1.4 / numpy 1.26.4 / yfinance 1.7.0, with the three
  yfinance client files hashed on disk (16-hex prefixes) **without importing
  yfinance** (`HOLD:RUNTIME_DRIFT`). The live probe matches the pins exactly.
- **Mechanisms reused from the accepted r2 packet:** `os.link` atomic no-clobber
  publication (temp → fsync → link → dir fsync); fsync'd attempt journal
  committed **before** each request; restart reconciliation
  `SKIP_VERIFIED | ATTEMPT_CONSUMED_AMBIGUOUS | HOLD:FINAL_MISMATCH | ELIGIBLE`
  backed by an fsync'd per-file ledger. A restart pre-scan blocks the whole
  capture on any ambiguous/mismatched symbol **before** any new request — a
  second attempt can never be issued.
- **Frozen discipline enforced:** exact 52-symbol order; exactly one shared
  limiter (≥1.0 s between request starts); one attempt per symbol; no
  retries/fallback/pagination; row/byte/wall ceilings from the manifest;
  immediate abort on every frozen fail-closed trigger (throttle, partial,
  schema drift, meta drift, integrity, impossible OHLCV, ceiling, collision).
  Any abort retains the partial archive and marks it `INCOMPLETE_HOLD` with the
  named code.
- **Capture ≠ publication.** The executor only creates the local write-once
  archive (`raw/`, `actions/`, `meta/`, `SHA256SUMS`, `manifest.json`).
  `publish_capture()` is a separate phase that verifies the target full name
  exactly (`mickaellall116-cmyk/qf-data-archive`), requires observed
  `visibility=private`, refuses an existing `captures/<capture_id>/`, uploads
  raw bytes + manifest + SHA256SUMS, re-fetches every object and verifies
  hashes, and returns the commit SHA for the public non-data ledger. It
  refuses any remote that is not explicitly a local fake
  (`HOLD:REAL_REMOTE_FORBIDDEN`); no real remote implementation exists in the
  file.
- **No live path exists in this build:** the module imports no vendor client
  and contains no network code; the CLI binds no transport/remote — verify-only
  mode prints `BINDINGS_VERIFIED`, and `--execute`/`--publish` return
  `HOLD:EXECUTION_NOT_AUTHORIZED_IN_PREFLIGHT` (exit 3) and create nothing
  (both exercised during this preflight).

## 2. Fixture results — 21/21, twice, byte-identical

`run_executor_fixture.py` installs socket denial before any other import and
drives the executor with a fake transport and a local fake remote. All clocks
are fake; all bytes are synthetic.

| Check | Proves | Result |
|---|---|---|
| E0 | sockets denied; executor imports no vendor/network modules; yfinance never loaded | CLEAN |
| E1 | 1-byte manifest flip → `HOLD:MANIFEST_DRIFT` before transport | match |
| E2 | live runtime probe passes pins; doctored version / file-hash / missing-client probes → `HOLD:RUNTIME_DRIFT` | match |
| E3 | duplicate index / 51-count / duplicate symbol → `HOLD:ORDER_DRIFT` | match |
| E4 | complete fake 52/52: exact order, journal-before-every-request, limiter starts exactly 0…51 s, 156 data files + SHA256SUMS + manifest, sums re-verify | COMPLETE |
| E5 | restart of completed capture: `ALREADY_COMPLETE`, 0 transport calls, 156 files re-verified | match |
| E6 | crash after journal commit (3rd symbol): restart → `INCOMPLETE_HOLD` / `ATTEMPT_CONSUMED_AMBIGUOUS`, 0 new calls, symbol attempted exactly once across both runs | match |
| E7 | throttle at 2nd symbol → abort `HOLD:THROTTLED`, marker written, 1st symbol's bytes retained, calls stop | match |
| E8 | truncated final session → abort `HOLD:PARTIAL` | match |
| E9 | missing `Volume` field → abort `HOLD:SCHEMA_DRIFT` | match |
| E10a | equity meta timezone `UTC` → abort `HOLD:META_DRIFT` | match |
| E10b | returned symbol ≠ requested → abort `HOLD:SCHEMA_DRIFT` | match |
| E11 | 20,001-row response → abort `HOLD:CEILING` | match |
| E12 | foreign pre-placed final file → pre-scan `HOLD:FINAL_MISMATCH`, 0 calls, bytes unchanged; direct `archive_write` on the path raises the no-clobber collision | match |
| E13 | publish happy path vs fake remote: 158 objects uploaded under `captures/<id>/`, all re-fetched + hash-verified, commit SHA returned | PUBLISHED_FAKE |
| E14 | wrong repo full name → `HOLD:TARGET_NAME_DRIFT`, 0 uploads | match |
| E15 | `visibility=public` → `HOLD:VISIBILITY_REFUSAL`, 0 uploads | match |
| E16 | existing `captures/<id>/` → `HOLD:CAPTURE_EXISTS`, 0 uploads | match |
| E17 | corrupted object on re-fetch → `HOLD:REFETCH_MISMATCH` | match |
| E17b | missing object on re-fetch → `HOLD:REFETCH_MISMATCH` | match |
| E18 | non-fake remote → `HOLD:REAL_REMOTE_FORBIDDEN` before any other check | match |

Runs: 2 full suite runs, both 21/21, exit 0; normalized results byte-identical
(`executor_fixture_results.json` == `executor_fixture_results_run1.json`).

## 3. Exact hashes

| File | SHA256 |
|---|---|
| `execute_capture.py` | `a7ab6d0bc1578a8b63a2f18a402a1db6e0bc8f6031016a46342f5681af0ab68f` |
| `run_executor_fixture.py` | `af9aa326d4ce2b584c1f8513a201df6126cb359dd71e56e057a0a74fb90d0831` |
| `executor_fixture_results.json` (+ run1, byte-identical) | `61064126a2b4a57261990e52ee3a95588f16d55f0e648e62ac06dd88caebd0ff` |
| `capture_manifest.json` (unchanged, the binding target) | `634c4541a8b30ade50e45898e80ee65806fa323c953020edc149530642d9bef3` |
| `SHA256_MANIFEST.txt` (regenerated over the full package) | `983f5c2d2016d51c8d4977433af0a4b9c587509570f3be20f30570ac40871f9c` |

Package manifest verification: `sha256sum -c SHA256_MANIFEST.txt` — 12/12 OK
(r1/r2 files unchanged and still verified).

## 4. Scope confirmation

Zero Yahoo calls; zero vendor/API/model calls; zero sockets (denial installed
first — the only socket event is the deliberate denial probe); zero market-data
downloads (the sole network use was fetching the spec comment via the public
GitHub API before work began); zero installs; zero spend; zero capture
execution; zero writes to either GitHub repository; zero backtests; zero
sealed/holdout access; zero live/production changes. All fixture archives were
created in `/tmp` and no file outside this package and this memo was written.

## 5. What this PASS does not authorize

Per the spec: a PASS authorizes **neither** the 52 Yahoo requests **nor**
publication. Actual acquisition remains a separate explicit execution gate.
Standing caveats from the frozen manifest are unchanged: execution reaches
back only ≈729 days (≈2024-10-17 for a 2026-10-16 execution), so symbols will
be COVERAGE-LIMITED against the 2023-01-01 prereg target and fold calendars
must be re-frozen from actual pulled coverage before any performance work.
The publish phase was exercised only against a local fake remote; the real
publication step (and the transport binding) is written/bound at the
separately authorized execution task, against this fixture-proven code.

Deliverables are left uncommitted in the worktree for review:
`research_notes/YAHOO_CAPTURE_EXECUTOR_PREFLIGHT_20261015.md` (this memo) and,
under `research_notes/yahoo_clean_capture_preflight_20261015/`,
`execute_capture.py`, `run_executor_fixture.py`,
`executor_fixture_results.json`, `executor_fixture_results_run1.json`, and the
regenerated `SHA256_MANIFEST.txt`.
