# PHASE A CORRECTNESS R2 RESULT — QF-IDEA-PHASE-A-CORRECTNESS-R2-20261013-04 r1

Status: **COMPLETE within the cap.** All three gaps from ChatGPT's
adversarial re-review of the R1 fix (Issue #1 comment `6159623983`) are
fixed in `store.py` (`phase-a-store/1.1.0` → `1.2.0`) and proved by new
real-process tests (`tests/test_adversarial_r2.py`, 7 tests). Full
regression preserved. Authorization: ChatGPT work order; Mike's standing
rule (2026-10-13 20:49 EDT) that the Muse↔ChatGPT research loop is auto.
Commit-ready only — nothing committed by the builder.

**Effort vs cap:** ~15 min of the 30-min cap. No repair pass was needed
(every suite passed on its first run after the fixes) and no stop
condition triggered; no fix required redesign.

## Per-gap: root cause → fix → evidence

### 1. Takeover TOCTOU — age-based break could displace a LIVE owner
- **Root cause:** `acquire_lease` computed staleness as
  `(age > STALE_LOCK_SECONDS) OR (pid dead)`. With a live holder whose
  lock was merely old, the first disjunct fired: the breaker re-read the
  bytes, replaced the lock, and created its own — displacing a live
  owner (whose subsequent writes were then fenced, i.e. the takeover
  itself was the failure).
- **Fix:** the recorded PID now decides, exclusively. A lock whose PID
  is alive is **never** stale, regardless of age. A lock whose PID is
  dead/gone is abandoned at any age. Only a lock with **no usable PID**
  falls back to a non-PID abandonment test: lockfile **mtime** older
  than `STALE_LOCK_SECONDS` (a fresh PID-less lockfile — e.g. one
  mid-creation — is never breakable). The break path additionally
  verifies the moved-aside file's bytes after `os.replace`: if the move
  displaced a lock that was not the one observed (a fresh owner slipped
  between check and move), it is restored in place and the takeover is
  refused.
- **Evidence:** `test_live_pid_aged_lock_takeover_refused` — a real
  holder subprocess stays ALIVE; its lock is aged 3h with the real live
  PID preserved; takeover raises `LeaseHeldError`, the on-disk lock is
  still the child's, and the child then writes its RUN_END successfully
  (outcome `WROTE`; chain contains exactly the child's RUN_START/RUN_END).
  Companion: `test_pidless_lock_uses_mtime_abandonment_test` — fresh
  PID-less lock refused, 3h-mtime PID-less lock broken as `broke-stale`.

### 2. Unfenced reconciliation + crash-order
- **Root cause:** `reconcile_orphans` mutated the store with no fence
  verification of its own: it unlinked temp files unconditionally, and
  on the quarantine path it **moved the card file before** appending the
  ERROR event — so a crash between move and append left the card gone
  from `ideas/` with no log record, and a displaced/unleased caller
  could mutate files before any fenced primitive was reached.
- **Fix:** `reconcile_orphans` now calls `_require_lease()` before ANY
  mutation and again immediately before each filesystem move. The
  quarantine order is inverted to **log first, move second**: the ERROR
  event (with `quarantined_orphan` + card sha256) is appended before the
  card leaves `ideas/`. A crash in that window is completed by the next
  reconciliation, which detects the recorded quarantine for that idea
  and performs only the pending move (`quarantine-completed` action) —
  never a duplicate event.
- **Evidence:** `test_reconcile_refused_without_lease` (unleased call →
  `FencingError`; card unmoved, no `orphaned/` dir, log bytes
  unchanged); `test_reconcile_refused_with_stale_fencing` (lease
  displaced on disk by token replacement → `FencingError`, nothing
  mutated); `test_quarantine_crash_order_completes_without_duplicate` —
  a real subprocess plants an invalid orphan and hard-crashes
  (`os._exit(42)`) inside `os.replace` at the quarantine move: exactly
  one ERROR event exists and the card is still in `ideas/`; the next
  acquirer completes the move, the card lands in `ideas/orphaned/`, and
  the log still holds exactly one ERROR event for the idea; chain
  verifies.

### 3. Init race — check-then-create could truncate the log
- **Root cause:** `init_layout` did `if not log_path.exists():
  log_path.write_text("")`. Two processes racing init — or one process
  whose existence check raced another that had already created the log
  and begun appending — could hit the `write_text("")` (O_TRUNC) branch
  and reset a live log. `init_layout` runs pre-lease in every process,
  so no lock ordered the race.
- **Fix:** the log is created with
  `os.open(log_path, O_CREAT | O_WRONLY | O_APPEND)` and immediately
  closed — create-if-absent semantics: O_CREAT without O_TRUNC is a
  no-op for an existing file, so concurrent inits adopt the existing log
  and can never truncate it. Directory creation was already
  `mkdir(parents=True, exist_ok=True)` (race-safe).
- **Evidence:** `test_concurrent_init_fresh_root_single_intact_log` —
  8 real processes × 100 `init_layout` calls released simultaneously on
  a fresh root: a single empty intact log results, and the store is
  fully usable afterwards. `test_concurrent_init_never_truncates_seeded_log`
  — 8 processes × 200 calls against a store with real events: log bytes
  byte-identical after the storm; chain verifies.

## One disclosed test-premise change (not a behavior regression)

`tests/test_adversarial.py::test_stale_takeover_fences_displaced_owner`
(R1) forged an aged lock with a **live** PID and asserted the takeover
succeeded — i.e. it encoded exactly the staleness rule gap 1 removes.
Its premise is updated: the forged lock record now also claims a dead
PID (999999), the only state in which a break is legitimate under the
r2 rule. Every assertion of the test (broke-stale, the still-alive
displaced owner's next write → `FencingError`, no RUN_END in the
verified chain) is unchanged, and the displaced-owner fencing coverage
via a real subprocess is preserved. The new live-PID refusal is covered
by the R2 suite above.

## Full-suite verification (after the fixes)

- R2 adversarial: **7/7 PASS**, run twice, exit 0 both times
  (`tests/test_adversarial_r2.py`; output persisted at
  `tests/adversarial_r2_output.txt`). Real subprocesses, real hard
  exits, on-disk lock forgery — no in-process crash simulations.
- R1 adversarial: **10/10 PASS**, run twice, exit 0 both times.
- Unit: **20/20 PASS** (`tests/test_store.py`, unchanged).
- Fixtures: **8/8 PASS**; output byte-identical across two fresh runs
  AND byte-identical to the committed `fixtures/fixtures_output.txt`.
- Committed migration store, read-only under the new code: 25 events,
  hash chain verifies, 8 cards, states 4 SHORTLISTED / 2 BLOCKED-DATA /
  2 REJECTED — unchanged, not rewritten.
- `research_notes/research_loop/registry.json` NOT edited — sha256 still
  `86600c0775bccb9d6429a76e5527db3e4dbac50e3cb9f757ecf1c3fb5c98bdac`.

## Scope discipline

Changes isolated to `phase_a/`: `store.py`, the one premise update in
`tests/test_adversarial.py`, plus the new `tests/test_adversarial_r2.py`,
`tests/adversarial_r2_output.txt`, and this report. No Phase B, no
cutover, no live queue, no scheduler changes, no network code (the store
module remains network-free), no vendor calls or spend.

## File pins (sha256)

| File | sha256 |
|---|---|
| `store.py` | `08379ba4e806b4cc1789f3c5f5695d9e455f679a82025fd07326842f1fab645d` |
| `tests/test_adversarial.py` | `44221a7f8d5d4374bd40bc021c8ac15f6a835e72a8161a1f5bc35b90cc50116e` |
| `tests/test_adversarial_r2.py` | `7c898d89bc66bc298ee63dfc1251191d7d6da426f1b7c0f8db2b7b97bee1aca3` |
| `tests/adversarial_r2_output.txt` | `043ce07cfa56002af8ce473cbbe2840651245eb5cca01e759cd6687e07a6a839` |
