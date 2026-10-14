# PHASE A CORRECTNESS RESULT — QF-IDEA-PHASE-A-CORRECTNESS-20261013-02 r1

Status: **COMPLETE within the cap.** All four adversarial failures proved by
ChatGPT against `phase-a-store/1.0.0` (Issue #1 comment `6158529341`) are
fixed, plus the UUID ID amendment. Store is now `phase-a-store/1.1.0`.
Authorization: ChatGPT work order; Mike's standing rule (2026-10-13 20:49
EDT) that the Muse↔ChatGPT research loop is auto. Commit-ready only —
nothing committed by the builder.

**Effort vs cap:** ~30 min of the 60-min cap, including one repair pass
(~2 min: an f-string syntax error in the new reconciliation code, caught by
the first test run). No redesign was needed; no stop condition triggered.

## Per-failure: root cause → fix → evidence

### 1. Unlocked writes
- **Root cause:** `append_event`, `write_card`, and the materializers never
  checked lease ownership. Any `Store` instance — including one in a second
  process that never acquired, or whose lease was never taken — could
  mutate cards, the log, drafts, and the ledger.
- **Fix:** a single fencing primitive, `Store._require_lease()`, now guards
  every mutation entry point: `append_event` and `write_card` (which also
  covers `ingest` and `transition` — their first mutation hits a fenced
  primitive) and `materialize_drafts` / `materialize_ledger`. The check
  re-reads the lockfile on disk on every call. `init_layout` remains
  pre-lease bootstrap by design: it only creates empty directories / an
  empty log file and cannot alter any record. One call-site reorder was
  required: `migration/migration_events.py` now materializes BEFORE
  `release_lease()` (outputs byte-identical — materializers are pure
  functions of the completed log, which already includes RUN_END).
- **Evidence:** `test_mutations_require_lease_in_process` (append, card,
  ingest, and draft materialization all raise `FencingError` unleased;
  release revokes write access) and
  `test_unleased_process_cannot_write_while_holder_active` (a real second
  process holds the lease; the unleased writer is refused with
  `FencingError`, a competing acquire is refused with `LeaseHeldError`,
  and the legitimate holder's write lands).

### 2. Lock takeover race
- **Root cause:** stale-break replaced the lockfile but left the displaced
  owner's in-memory `self._lease` untouched — the old owner could keep
  appending, and its `release_lease()` could even unlink the NEW owner's
  lock (it matched on `run_id` only in the file it found).
- **Fix:** fencing token. The lock payload now carries
  `fence_token = uuid4().hex`; `_require_lease()` requires the on-disk
  token to equal the token this instance captured at acquisition, so a
  displaced owner fails its very next write. `release_lease()` unlinks
  only when run_id AND token still match. The break path also re-reads the
  lockfile bytes immediately before `os.replace` and refuses to displace a
  lock that changed since it was observed (two breakers can't move each
  other's fresh lock aside).
- **Evidence:** `test_stale_takeover_fences_displaced_owner` — a real
  holder subprocess stays ALIVE; its lock is aged 3h (stale by age, live
  PID, token preserved — the hardest case); the new owner breaks it and
  writes; the displaced owner's next append returns `FencingError` and no
  RUN_END from it exists in the verified chain. Companion in-process test
  `test_displaced_owner_release_cannot_delete_new_lock`: the displaced
  owner's `release_lease()` leaves the new owner's lockfile in place.

### 3. Orphan card
- **Root cause:** `ingest()` wrote the card, then appended INGESTED. A
  crash in between left a durable card with no event — invisible to state
  replay, counted by no sequence, and a retry collided with the immutable
  file.
- **Fix:** the write ordering (card fsynced + atomically renamed BEFORE
  its event) is kept and now documented as the recovery contract, and
  `acquire_lease()` runs `reconcile_orphans()` under the new lease before
  returning. Deterministic, in idea_id order: a card with no
  INGESTED/MIGRATED event that still re-validates and whose `dedup_key`
  recomputes is ADOPTED — the lost INGESTED event is appended with
  `recovered_orphan: true` and the card's sha256 recorded. A card failing
  re-validation is QUARANTINED to `ideas/orphaned/` with an ERROR event
  recording why. Leftover `write_card` temp files are removed (they are
  never valid cards).
- **Evidence:** `test_kill9_orphan_card_adopted` — a subprocess writes a
  real card, then is SIGKILLed inside the crash window; the next acquirer
  (dead-PID stale break) reports exactly one adoption, the card replays to
  INGESTED with the marked recovery event, chain verifies.
  `test_kill9_during_ingest_loop_keeps_invariant` — a subprocess is
  SIGKILLed mid ingest-loop; after reconciliation every durable card has
  its INGESTED event and the chain verifies. (If a kill ever lands inside
  the single write+fsync and tears the final line, the test instead
  asserts the loud-abort behavior of fix 4 — either outcome is a pass,
  never a silent merge.)

### 4. Missing-newline append corruption
- **Root cause:** appends wrote `line + "\n"` unconditionally; if the
  log's last line lacked its trailing newline, the new record merged into
  it, corrupting both lines and the chain.
- **Fix:** `append_event` now calls `_terminate_tail_if_needed()` after
  the chain verifies and before appending: if the file is non-empty and
  its last byte is not `\n`, the missing newline is written and fsynced
  first. Because verification runs first, termination only ever completes
  a line already proven to be a whole valid event; a genuinely torn
  (unparsable) tail aborts in `read_events` — which now raises
  `ChainVerificationError` with the line number instead of a raw
  `JSONDecodeError` — before any byte is written.
- **Evidence:** `test_unterminated_valid_tail_is_terminated_not_merged`
  (strip only the final newline on disk → next append lands as its own
  record; count +1; chain verifies) and
  `test_torn_tail_aborts_loudly_and_writes_nothing` (tail truncated
  mid-line → `ChainVerificationError`; log bytes byte-identical after the
  attempt).

### 5. ID amendment — UUID run/event IDs
- **Root cause:** IDs were sequenced from log state
  (`RUN-YYYYMMDD-NNN`, `EVT-YYYYMMDD-NNNNN`). Two attempts starting from
  the same log state minted the SAME run ID, and event IDs were positional
  rather than unique per attempt.
- **Fix:** `new_run_id()` returns `RUN-<yyyymmdd>-<uuid4 hex[:12]>` (date
  prefix retained for `_run_date()` / draft naming); `append_event` mints
  `event_id = "EVT-" + uuid4().hex`. Uniqueness no longer depends on any
  shared counter. The run association of every event continues to be
  RECORDED in the event's `run_id` field (the amendment's "encoded or
  recorded"). Idea IDs are unchanged (they are sequence-allocated under
  the lease, which is now fenced).
- **Evidence:** `test_run_ids_unique_across_processes_same_log_state` —
  six concurrent subprocesses against the same empty store mint 18 run
  IDs, zero collisions, all matching the UUID format;
  `test_event_ids_are_uuids_and_record_their_run` — all event IDs match
  `EVT-[0-9a-f]{32}`, are distinct, and group exactly by their producing
  run.

## Full-suite verification (clean independent rerun after the fixes)

- Unit tests: **20/20 PASS** (`tests/test_store.py`, unchanged) — run
  twice, exit 0 both times.
- Fixtures: **8/8 PASS**, and the output is **byte-identical** across two
  fresh runs AND byte-identical to the r1 committed
  `fixtures/fixtures_output.txt` (UUID IDs appear in no fixture output
  line; fixture semantics unchanged).
- Adversarial tests: **10/10 PASS**, run twice, exit 0 both times
  (`tests/test_adversarial.py`; full output persisted at
  `tests/adversarial_output.txt`). Real subprocesses, real SIGKILLs,
  on-disk pre-corruption — no in-process crash simulations.
- Committed migration store, read-only under the new code: 25 events,
  hash chain verifies, 8 cards, states 4 SHORTLISTED / 2 BLOCKED-DATA /
  2 REJECTED — unchanged. (Its events keep their r1 sequential IDs; that
  store is a historical artifact and was NOT rewritten.)

## Scope discipline

- Changes are isolated to `phase_a/`: `store.py`,
  `migration/migration_events.py` (call-order only), plus the new
  `tests/test_adversarial.py`, `tests/adversarial_output.txt`, and this
  report. No changes to `tests/test_store.py` or the fixtures were needed.
- `research_notes/research_loop/registry.json` NOT edited — verified:
  sha256 still matches the pin recorded in
  `migration/registry_backfill.json` (`86600c0775bccb9d…`).
- No Phase B, no cutover, no live queue, no scheduler changes, no network
  code (the store module remains network-free), no vendor calls or spend.

## File pins (sha256)

| File | Bytes | sha256 |
|---|---|---|
| `store.py` | 45,815 | `e8583eb720256811c77bb38ce8966c56b1e19b1fa43864aff247376c6d40d968` |
| `migration/migration_events.py` | 20,067 | `0632f8fd6ec01ea4fde57a43b7c5b2b84d32ff872e004834b29d6f9432e11de2` |
| `tests/test_adversarial.py` | 16,507 | `00a465a6d9d0af9e2f15359c91cd6b269a2aa9ad7aff133ffeea98425ab97b54` |
| `tests/adversarial_output.txt` | 1,393 | `01386dc8540dae454e90fa052ea008fbee92b1a3859018faf21ec0ed152e3c6f` |

## Notes for the reviewer

- Reconciliation events precede the new run's RUN_START / LOCK_BROKEN in
  the log (they are appended inside `acquire_lease`); they carry the
  acquiring `run_id`, so attribution is unambiguous.
- A card orphaned by a crash during MIGRATION would be adopted via an
  INGESTED (not MIGRATED) recovery event — the log stays truthful about
  how the card entered, via the `recovered_orphan` marker and reason.
- `S._write_deterministic` called directly by the migration script for
  `registry_backfill.json` is a build-script artifact write outside any
  store root; the lease fence governs all mutations under a store root
  (ideas/, queue/, drafts/, ledger/), which is the store's system of
  record.
