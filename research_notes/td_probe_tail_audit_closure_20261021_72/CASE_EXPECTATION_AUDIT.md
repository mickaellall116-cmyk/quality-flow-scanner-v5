# CASE EXPECTATION AUDIT — task -72 r1 (pre-formal, source-only)

Mandated by the -72 spec (Issue #1 comment 6320693517) BEFORE
precommit: reconcile the exact expectations and injected-operation
order of every case that had never executed — U13 and P01-P11 —
against the pinned source, WITHOUT any test or dress-rehearsal
execution. Method: static reading of the -71 candidate source
(`account_preflight.py`), the -71 harness
(`tests_qualification.py`), and the SHA-pinned frozen pilot
(`research_notes/pilot_harness/pilot_acquire.py`
acf39bbd98f7174a4205019e754fc714ca420b4a7df43…, `rate_limiter.py`
06ad383d…), all at the -71 result tree (0df6cff + 1f65028 +
2338b97). No case was run, imported-and-probed, or otherwise
executed during this audit.

Shared facts the per-case entries rely on:

- Persistence syscall order in `DailyUsageSession._persist_outcome`
  (account_preflight.py, -71): pre-check `os.path.lexists` on
  both finals (collision -> OSError USAGE_PERSIST_COLLISION);
  stage body temp (`mkstemp` in the store dir, prefix
  `.usage-body-`, fchmod 0600, write-all via `_write_once`,
  `_fsync` = **fsync #1**); stage receipt temp (prefix
  `.usage-receipt-`, write-all, `_fsync` = **fsync #2**);
  `_link(body_tmp -> api_usage.<DAY>.body.bin)`, unlink temp,
  `_fsync_dir(store)` = **fsync #3**; `_link(receipt_tmp ->
  api_usage.<DAY>.receipt.json)`, unlink temp,
  `_fsync_dir(store)` = **fsync #4**. Temps are unlinked in a
  `finally` on any failure; a final already published is left
  in place. This is exactly the numbering the harness's
  `_flaky_fsync` docstring assumes — verified consistent.
- `DailyUsageSession.__call__` order: if the receipt final
  exists -> parse -> `_verify_body_file` (missing ->
  USAGE_RECEIPT_BODY_MISSING; hash/count mismatch ->
  USAGE_RECEIPT_BODY_MISMATCH) -> REFUSE branch (binding check,
  then return the recorded terminal reason) -> `_verify_cached`
  (PASS reuse) — else fresh `AccountPreflight.check()`, stamp
  bindings, `_persist_outcome`; any OSError there ->
  `[USAGE_RECEIPT_PERSIST_FAILED: ...]` and NO data transport
  (the session is the ManifestDriver preflight callable; the
  frozen wrapper raises before any request fetch on a non-empty
  failure list, pilot_acquire.py `AcquisitionWrapper.run`
  L320-325). "No-data proof" below = this preflight position:
  every audited case operates at session/preflight level or
  asserts `data.calls == 0` through `run_probe_day`.
- `AccountPreflight.check()` order on a 200 response:
  `parse_usage_body` -> `evaluate_daily_gate` ->
  `reconcile_credit_headers`. The gate therefore refuses
  BEFORE headers are consulted; headers can only refuse after
  the gate passes. Retry: max 2 attempts, only on 429/5xx/0.
- Frozen wrapper: `AcquisitionWrapper.run` calls preflight
  first (failures -> RuntimeError, zero requests), then runs
  specs in order and BREAKS at the first stop outcome
  (AUTH_STOP / SCHEMA_QUARANTINE / RETRIES_EXHAUSTED /
  LEDGER_REFUSED / RATE_STOP) — L329-332. `_run_one` retries a
  retryable status (429/502/503/504 or 0) while
  attempts < max_attempts (=2 per the manifest), consuming one
  pilot-wide RetryBudget unit per retry (cap
  PILOT_RETRY_CAP=40). A 503-then-200 leg therefore ends OK
  with attempts=2.
- Harness clocks: `FTM.FakeClock(NOW_S, 7.0)` advances 7 s per
  read; a full D1 traversal (11 acquisitions) keeps at most
  ~3-5 acquisitions inside any rolling 60 s window of the
  (8/min, 800/day) limiter, as already proven by U01/Q07/Q19
  executions in -70/-71. `GOOD_USAGE` = {current_usage:1,
  plan_limit:8, daily_usage:1, plan_daily_limit:800}.

## U13_headers_never_waive — RECONCILED, no correction

- Source/branch: `AccountPreflight.check` 200-branch through
  `_expect_preflight_refusal` (harness), three sub-bodies.
- Expectations: (1) GOOD_USAGE with daily_usage=795, headroom
  10 -> 795+10=805 > 800 -> `evaluate_daily_gate` raises
  USAGE_DAILY_HEADROOM before `reconcile_credit_headers` is
  reached, so api-credits-left=100000 is never consulted.
  (2) GOOD_USAGE, headers used=5/left=3 -> gate passes
  (1+10<=800, plan 800 pinned ok), reconcile: used 5 !=
  current_usage 1 -> USAGE_HEADER_MISMATCH. (3) GOOD_USAGE,
  headers used=1/left=999 -> used matches, 1+999=1000 !=
  plan_limit 8 -> USAGE_HEADER_MISMATCH.
- Counts: exactly 1 usage fetch per sub-case (200, no retry);
  0 data (preflight-level case; no data transport exists in
  `AccountPreflight`).
- Persistence: none (check() only; receipts ride the raised
  PreflightRefusal, and the helper asserts verdict REFUSE +
  body hash/count binding on each).
- Terminal tokens: USAGE_DAILY_HEADROOM, USAGE_HEADER_MISMATCH
  x2 — as asserted. No correction.

## P01_short_writes_completed — RECONCILED, no correction

- Source/branch: `_persist_outcome` happy path with
  `ap._write_once` patched to truncate every write to 1 byte;
  `_write_all` loops until the memoryview is consumed.
- Sequence: fsync #1 body temp, #2 receipt temp, link body,
  fsync #3, link receipt, fsync #4 — all real (unpatched)
  fsyncs; writes are ~1-byte each but complete.
- Finals: both published; temp set empty afterwards (temps
  unlinked post-link; `_no_temps` checks prefix `.usage-`).
- Counts: session 1 = 1 usage fetch, returns []; reopen
  session = 0 fetches (cached PASS reverify via
  `_verify_body_file` + `_verify_cached`, incl. UTC-date
  equality at FakeClock(NOW_S, 0.0)).
- Assertions verified against source: persisted body bytes
  equal `json.dumps(GOOD_USAGE).encode()` because
  `SeqUsageTransport._usage_resp` serializes the same dict and
  `_persist_outcome` stores the terminal attempt's exact body.
- Terminal: PASS (`[]`). No correction.

## P02_zero_progress_write_refused — RECONCILED, no correction

- Source/branch: `_write_all` — `_write_once` returns 0 ->
  `n <= 0` -> OSError("short write") inside `_stage_temp`
  (body), whose temp was already registered; `_persist_outcome`
  `finally` unlinks it.
- Sequence: write fails before fsync #1; no link calls.
- Finals/temps: none / none. Counts: 1 usage fetch.
- Terminal: `[USAGE_RECEIPT_PERSIST_FAILED: ...]` via
  `__call__`'s OSError catch. No data (session level). No
  correction.

## P03_body_write_failure — RECONCILED, no correction

- Identical path to P02 except `_write_once` raises on the
  first (body-staging) call. No fsync, no link, no finals, no
  temps. Terminal USAGE_RECEIPT_PERSIST_FAILED. No correction.

## P04_body_fsync_failure — RECONCILED, no correction

- Source/branch: `_flaky_fsync(1)` — fsync #1 is the BODY
  temp's fsync in `_stage_temp` (first fsync call of the
  transaction; nothing before it calls the seam).
- Sequence: body write completes, fsync #1 raises, temp
  cleaned in `finally`; receipt never staged; no links.
- Finals/temps: none / none. Counts: 1 usage fetch.
- Terminal: USAGE_RECEIPT_PERSIST_FAILED. No correction.

## P05_receipt_write_failure — RECONCILED, no correction

- Source/branch: `_write_once` patched to raise when the chunk
  contains b"API-USAGE-PREFLIGHT". Body bytes (GOOD_USAGE JSON)
  do not contain it -> body staging completes (fsync #1).
  Receipt bytes are `json.dumps(receipt, indent=2)` whose
  first key is `request_id: API-USAGE-PREFLIGHT` (dict built
  in `_outcome_receipt` with request_id first; stamps appended
  last) -> the first receipt-temp write raises.
- Sequence: fsync #1 only; NO link has happened yet (links
  occur only after both stagings), so nothing is published;
  body temp cleaned in `finally`.
- Finals/temps: none / none. Terminal
  USAGE_RECEIPT_PERSIST_FAILED. No correction.

## P06_receipt_fsync_failure — RECONCILED, no correction

- `_flaky_fsync(2)`: fsync #1 (body temp) succeeds, fsync #2
  (receipt temp, in the second `_stage_temp`) raises before
  any link. Finals/temps: none / none. Counts: 1 usage fetch.
  Terminal USAGE_RECEIPT_PERSIST_FAILED. No correction.

## P07_rename_link_failure — RECONCILED, no correction

- Source/branch: `ap._link` patched to always raise; both
  stagings complete (fsync #1, #2), first link (body) raises,
  `finally` unlinks both temps. Finals/temps: none / none.
- Terminal USAGE_RECEIPT_PERSIST_FAILED. No correction.

## P08_parent_dir_fsync_failure — RECONCILED, no correction

- `_flaky_fsync(3)`: fsync #1 body temp, #2 receipt temp,
  body link + temp unlink succeed, `_fsync_dir` (#3) raises.
  Receipt temp (still registered) is cleaned; the BODY final
  remains published — matches the case's assertions (body
  present and byte-exact, receipt absent, no temps).
- Second session: receipt absent -> fresh check (1 usage
  fetch) -> `_persist_outcome` pre-check finds the body final
  via `lexists` -> OSError USAGE_PERSIST_COLLISION ->
  `[USAGE_RECEIPT_PERSIST_FAILED: ...]`; body bytes untouched
  (persist never writes on collision). Matches.
- Terminal: USAGE_RECEIPT_PERSIST_FAILED in both sessions.
  No data (session level). No correction.

## P09_preexisting_orphan_body — RECONCILED, no correction

- Pre-state: store with only `api_usage.D1.body.bin` =
  b"orphan". Session: receipt absent -> fresh check (1 usage
  fetch) -> persist pre-check collision on the body final ->
  USAGE_RECEIPT_PERSIST_FAILED; body bytes never overwritten;
  no receipt created. Matches source exactly. No correction.

## P10_preexisting_receipt_without_body — RECONCILED, no correction

- Pre-state: receipt final written from `_bound_usage_receipt()`
  (a structurally valid bound PASS receipt), no body file.
- `__call__`: receipt exists -> parse ok -> `_verify_body_file`
  returns USAGE_RECEIPT_BODY_MISSING -> `[that reason]`
  returned BEFORE any verdict/binding logic and before any
  transport. Counts: 0 usage fetches (asserted), 0 data.
  Matches. No correction.

## P11_committed_outcomes_survive_reopen — RECONCILED, no correction

- PASS half: persist via the transactional path; stored
  receipt fields (bytes, sha256, manifest_sha256,
  store_marker_sha256, day) read back from the exact dict
  `_persist_outcome` serialized — all bindings are the values
  `__call__` stamped pre-persist (manifest MANIFEST_SHA,
  marker `_marker_str()` digest, day "D1"). Reopen session:
  `_verify_body_file` + `_verify_cached` pass (headroom 10 ==
  recorded 10; execution-date == UTC date of both timestamps
  == today at FakeClock(NOW_S, 0.0)) -> `[]`, 0 fetches.
- Credential scan: receipt serialization contains only the
  allowlisted fields + captured credit headers ({} here); the
  body is the GOOD_USAGE JSON. Neither contains
  b"apikey"/b"api_key"/b"secret" — verified by field
  inventory, not by running the case.
- REFUSE half: body {current_usage:1, plan_limit:8} (daily
  pair absent) -> check() refuses USAGE_DAILY_SCHEMA; the
  REFUSE outcome persists with the exact body; reopen reaches
  the sticky-REFUSE branch (bindings match) and returns the
  SAME recorded terminal_reason string the first session
  returned (the fresh path returns
  `receipt["terminal_reason"]`, the cached path returns
  `stored["terminal_reason"]` — the same persisted string) ->
  reasons equal, 0 fetches. Matches. No correction.

## U12 — CORRECTION (the adjudicated defect; spec item 1)

- The -71 case's second block is DEMONSTRABLY WRONG against
  the frozen wrapper: it asserts an all-fail Day 1 (NVDA/TSLA/
  AAPL 503 on every attempt) attempts all five legs
  (len(data.calls) == 10, total == 11). Per
  `AcquisitionWrapper.run` L329-332 the day BREAKS at the
  first stop outcome: REQ-ADJ-01 (NVDA) exhausts its 2
  attempts -> RETRIES_EXHAUSTED -> stop. Realized: 1 usage +
  2 data = 3 (exactly what the -71 run recorded). Corrected
  in the -72 harness by re-expressing U12 as the three real
  paths the spec mandates — (a) daily-gate refusal: 1 call /
  0 data (unchanged from -71 block 1); (b) first-leg retries
  exhausted: fail only NVDA -> data == 2, total == 3,
  outcomes == [REQ-ADJ-01 RETRIES_EXHAUSTED attempts=2],
  ok False; (c) worst-case successful day: a new harness
  transport (RetryOnceDataTransport) 503s the first fetch of
  each distinct URL and serves the standard 200 payload on
  the repeat — each leg ends OK attempts=2 (503 is retryable,
  retry budget 40 >= 5), data == 10, total == 11 <= 12
  (hard-ceiling assertion KEPT), ok True, 5 outcomes.
  Candidate behavior was not touched for this correction;
  only the harness case changed, as disclosed here and in
  the -72 result memo.

## P12_final_dir_fsync_failure — NEW (spec item 2)

- Branch: `_flaky_fsync(4)` — fsync #1/#2 stagings and #3
  (dir, post-body) succeed; the receipt is linked; `_fsync_dir`
  #4 raises. In -71 this leaves a fully reusable PASS receipt
  (audit concurrence with the adjudication: `_verify_cached`
  has no record of the failed barrier — a genuine candidate
  gap, and precisely the closure the spec orders implemented,
  so it is fixed here rather than reported as a stop).
- -72 candidate change (account_preflight.py only): the final
  `_fsync_dir` in `_persist_outcome` is wrapped; on OSError,
  `_tombstone_unproven_commit(receipt)` rewrites the receipt
  final IN PLACE (open O_WRONLY|O_TRUNC, `_write_all`,
  `_fsync` — fsync call #5 under single-failure injection,
  which succeeds) as a REFUSE tombstone preserving bytes /
  sha256 / day / manifest_sha256 / store_marker_sha256 /
  required_headroom, with verdict REFUSE and terminal_reason
  USAGE_COMMIT_UNCERTAIN: ...; the original OSError then
  propagates.
- Expected case outcomes, traced: session 1 -> preflight
  fetch ok (1 usage call) -> persist raises ->
  `[USAGE_RECEIPT_PERSIST_FAILED: ...]` (asserted helper);
  both finals present; body byte-exact; stored receipt
  verdict REFUSE with USAGE_COMMIT_UNCERTAIN; stored sha256 /
  bytes still match the body (tombstone preserved them); no
  temps. Session 2 (fresh, unpatched): receipt exists ->
  `_verify_body_file` passes (binding preserved) -> REFUSE
  branch bindings match -> returns
  `[USAGE_COMMIT_UNCERTAIN: ...]` with 0 usage fetches —
  never a silent PASS. Day-level block: `_run_d1` under the
  same patch -> the session's failure list makes the wrapper
  raise RuntimeError carrying USAGE_RECEIPT_PERSIST_FAILED;
  data.calls == 0, usage.calls == 1.
- Residual disclosure: if the tombstone rewrite itself fails
  (a second, independent failure), the persist still raises
  and this invocation HOLDs, but a later session could reuse
  the receipt; that double-failure residue cannot be proven
  away at this layer and is disclosed in the result memo, as
  the spec's fallback contemplates ("if receipt
  retraction/cleanup cannot itself be proven durable, later
  access must remain HOLD" — the tombstone is the mechanism;
  its own durability rests on one file fsync).

## Audit verdict

U13 and P01-P11: every expectation reconciles with the pinned
source — NO corrections, NO candidate defects found in the
audited set. The single harness correction is U12 (above,
spec-mandated). The single candidate change is the spec's
own item-2 closure (P12 branch). If the formal attempt
contradicts this audit anywhere, the run stops at that case
and the contradiction — not a repair — is the report.
