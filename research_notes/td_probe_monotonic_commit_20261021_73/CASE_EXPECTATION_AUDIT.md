# CASE EXPECTATION AUDIT — task -73 r1 (pre-formal, source-only)

Written BEFORE the formal attempt, from reading the -73 source
only — no dress-rehearsal execution. Scope: every case whose
expectations changed vs -72 (P12, the _bound_usage_receipt
fixture) and every new case (M01–M04). All other cases are
byte-identical to -72 and their receipts reach the reader only
via (a) the real writer, which now activates commit_state to
"1" before returning, or (b) _bound_usage_receipt, updated
below — so no other expectation changes.

## Source facts relied on (account_preflight.py, -73)

- `_persist_outcome` fsync order (via the `ap._fsync` seam):
  #1 body temp file, #2 receipt temp file, #3 parent dir after
  body hard-link, #4 parent dir after receipt hard-link.
  Activation is NOT an `_fsync` call: `_activate_commit` opens
  the published receipt O_RDWR|O_SYNC and flips the commit
  byte through the `_write_once` seam via `_write_all`, so the
  -71/-72 fsync numbering (P04=#1, P06=#2, P08=#3, P12=#4) is
  unchanged.
- The receipt is serialized with `commit_state: "0"`; the
  commit byte offset is located by the unique raw marker
  `"commit_state": "0"` in the staged bytes (inside a JSON
  string value a quote is escaped, so the raw marker can only
  be the field itself; the code asserts count == 1 and that
  the byte at the offset is "0").
- `_activate_commit` runs ONLY after fsync #4 returns. Any
  OSError from lseek/write propagates — no try/except in the
  activation path swallows anything (the finally only closes
  the fd). `_write_all` raises OSError on a write returning
  <= 0.
- Reader (`DailyUsageSession.__call__`): parse stored receipt
  -> commit gate (`commit_state != "1"` ->
  USAGE_COMMIT_UNCERTAIN) -> body verify -> REFUSE branch ->
  `_verify_cached`. The commit gate is FIRST, before any
  transport (the cached path never calls the transport).
- Activation payload is exactly b"1" (one byte). Every other
  `_write_once` payload in the persist path is a full staging
  buffer (body JSON or receipt JSON), so a fake that
  discriminates on `bytes(data) == b"1"` hits activation only.

## Fixture change: _bound_usage_receipt

- Change: gains `"commit_state": "1"`. Rationale: the helper
  models an already-COMMITTED stored receipt — under the -73
  reader invariant it must carry the committed state or every
  case using it would stop at the commit gate instead of the
  branch it exercises. Expectations UNCHANGED for A05
  (USAGE_CACHE_BODY_ALTERED), A06/A07 (USAGE_CACHE_BINDING),
  A08/A09 (USAGE_CACHE_TIMESTAMP), B07 (USAGE_CACHE_PARAMS),
  P10 (USAGE_RECEIPT_BODY_MISSING): each fixture's commit_state
  is "1", so the commit gate passes and the original branch
  fires. No-data proof: unchanged (-72 audit) — all refusals
  occur in the cached path with 0 data + 0 usage calls.

## P12 (re-expressed) — fsync #4 failure

- Source/branch: `_persist_outcome`, second `_fsync_dir`
  raises after `_link(receipt_tmp, receipt_path)`. -73 code
  has NO except branch there (the -72 tombstone is deleted):
  the OSError propagates; temps list is already empty.
- Expected calls: 1 usage call (the preflight's own), 0 data
  calls (session level); day level: 1 usage, 0 data, run
  aborts with USAGE_RECEIPT_PERSIST_FAILED.
- Expected finals: body file present, bytes == the exact
  GOOD_USAGE JSON, sha256/bytes binding in the receipt
  intact; receipt present with verdict "PASS",
  commit_state "0", terminal_reason null (the PENDING
  publication, byte-untouched — no rewrite exists). No temps.
- Reopen: commit gate fires first -> USAGE_COMMIT_UNCERTAIN,
  0 usage calls. Terminal token (invocation):
  USAGE_RECEIPT_PERSIST_FAILED.

## M01 — double failure (fsync #4 + all post-failure writes dead)

- Injection: an fsync fake that counts like _flaky_fsync and
  raises on call #4 while setting a tripped flag; a
  _write_once fake that delegates to os.write until tripped,
  then raises on ANY write. Staging (fsync #1/#2, writes)
  precedes the trip, so the transaction reaches the barrier
  normally; after the trip, any hypothetical retraction write
  would raise — the design attempts none (activation is
  unreachable: it runs only after fsync #4 RETURNS).
- Expected: identical observable state to P12 (invocation
  USAGE_RECEIPT_PERSIST_FAILED, 1 usage call, 0 data; finals
  body-exact + receipt PENDING commit_state "0"; no temps);
  reopen -> USAGE_COMMIT_UNCERTAIN, 0 calls. This is the
  branch -72's P12 could not prove.

## M02 — activation write raises

- Injection: `_write_once` fake delegating everything except
  payload b"1", which raises OSError. Fsyncs #1–#4 all real,
  so `_activate_commit` is reached; `_write_all` propagates
  the raise out of `_persist_outcome`.
- Expected: invocation USAGE_RECEIPT_PERSIST_FAILED (via
  _persist_failed_reasons), exactly 1 usage call; receipt on
  disk verdict PASS with commit_state still "0" (the write
  raised before landing); no temps; reopen ->
  USAGE_COMMIT_UNCERTAIN, 0 calls.

## M03 — activation write returns zero

- Injection: same discriminator, returns 0 for payload b"1".
  `_write_all` treats <= 0 as a short write and raises
  OSError — no spin, no retry.
- Expected: identical to M02 in every observable.

## M04 — missing / malformed / tampered commit state

- Construction: a genuine committed PASS store from the real
  writer (`_pass_store`), copied; the stored receipt JSON is
  edited to (vm) delete commit_state, (vz) "0", (vw) "yes",
  (vt) integer 1, (vx) "10". Only the exact string "1" is
  interpretable, so each variant must stop at the commit
  gate — which precedes the body/binding checks, so no other
  tag can fire first.
- Expected per variant: reasons[0] contains
  USAGE_COMMIT_UNCERTAIN, 0 usage calls (asserted by
  _reuse_reasons), 0 data (session level never reaches data).

## Regression sweep (why nothing else moves)

- Cases whose cached receipts come from the real writer
  (Q07, Q19, B06, U08, U11, P01, P08-second-half, P11) see
  commit_state "1" after successful activation — the commit
  gate passes and the -72 branches fire unchanged.
- P02–P09 fail before publication or at fsync #1–#3 / link:
  activation is never reached; expectations unchanged.
- U09 (body path is a directory): the persist refuses at the
  collision check before staging; unchanged.
- REFUSE outcomes (U08 refuse store, P11 refuse store) are
  persisted through the same _persist_outcome and activated
  identically; the sticky-REFUSE branch sits AFTER the commit
  gate, and a committed REFUSE passes the gate — reopen
  semantics unchanged.
