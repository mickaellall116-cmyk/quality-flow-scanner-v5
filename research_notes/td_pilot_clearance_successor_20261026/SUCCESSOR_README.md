# TD Pilot Clearance Successor — Option B (2026-10-26)

Implements ChatGPT's approved **option B** for the Twelve Data feed-measurement
pilot clearance (approval: GitHub Issue #1 comment `6432130873`; Slack thread
TS `1793069014.798409`). **Build + test + commit only.** This package does NOT
lift the tripwire hold, does NOT write `state/tripwire_clear.json`, does NOT
deploy to the live daemon, and made **zero Twelve Data calls**. The live
daemon keeps running the current (pre-fix) code, held, `desk_calls = 0`.

## The defect (found 2026-10-26 during clearance prep)

`process_tripwire_clear` lifts the tripwire hold and calls `mark_stale`, but
the pre-fix `mark_stale` covered **only ladder/finalization** actions. On
clearance, the same tick's `run_due` loop would therefore execute Monday
Oct 26's leftover non-ladder actions seconds after the lift — the three
`/api_usage` actions (`usage|2026-10-26|start/midday/end`), the five revision
re-polls (`rev|2026-10-26|*`), and the archive push — journaling real TD calls
against a session the concurrence record states was **missed with zero
calls** (Issue #1 comment `6431629522`: "The Oct 26 session was missed with
zero calls; preserve that fact rather than retroactively polling").

The control run in the fixtures reproduces this exactly: against the pre-fix
runner, simulated clearance executes **9 Monday actions / 9 TD calls**.

## The fix (surgical, clearance mechanics only)

In `pilot_runner.py` (see `pilot_runner_optionB.diff`):

1. **`mark_stale` is now scoped strictly by session date.** Every pending
   action of **any kind** (usage, revision, archive_push, ladder,
   finalization, tripwire — any kind present in the journal) whose
   `session` date is strictly before the current ET date **and** whose due
   time has passed is marked terminal `missed_late` with cause
   `tripwire_hold` **before** the hold lifts (the finalization bar
   bookkeeping of the original is preserved). Actions of the current
   session are **never** stale-marked — in particular the current
   session's 09:15 ET tripwire action and that session's polls stay live —
   so the fix is safe whenever clearance lands.
2. **Repeat-clear idempotence guard** in `process_tripwire_clear`: verdicts
   for message ids no longer in `pending_review` (already filed, or
   unknown) are skipped — a repeated clearance file is a strict no-op (no
   duplicate filed entry, no re-fire).

Nothing else changes: `run_manifest.json` untouched (frozen), schedule,
symbols, and caps (149/day, 800 total) untouched.

- Pre-fix `pilot_runner.py` SHA-256: `63e2ccbfe836b5f81e1d8285dff7626e28f6f8936fa5ce32cbf712268dd1e8f2`
- Successor `pilot_runner.py` SHA-256: `5d5e386080bc7a67d1cc69bf6cbfbdc12c4eb8bb8dddbd0b8f5e7628f8362436`
- Pre-fix backup kept at stage `work/pilot_runner.py.bak_20261026_optionB_prefix`
  (alongside the earlier `work/pilot_runner.py.bak_20261026_prefix`).

## Fixtures (offline, against a copy of live state; stub transport/Gmail)

`test_clearance_fixtures.py`, recorded in `fixtures_output.txt` /
`fixtures_results.json` — **all checks pass**, including:

- Clearance processing changes **exactly** the 149 past-session pending
  actions → `missed_late`/`tripwire_hold` (the 3 `usage|2026-10-26`
  actions among them); zero current-session actions touched; zero
  transport calls made by clearance itself.
- Full simulated clearance tick (Tue 09:20 ET): the only executions are
  Tuesday's own `usage|2026-10-27|pre_revision` snapshot and
  `tripwire|2026-10-27`; `desk_calls_by_day = {"2026-10-27": 1}` — **no
  2026-10-26 entry: Monday's zero-call fact is preserved**. Tuesday's 105
  ladder polls stay live.
- Repeat-clear and restart-after-clearance are strict no-ops (nothing
  resurrects, nothing re-executes).
- Journal reconciles at 757 total in every scenario (see
  `JOURNAL_COUNTS.md`).
- Control (pre-fix runner): the defect reproduces — 9 Monday actions
  execute, 9 TD calls — proving the fixtures detect the bug.

## Ordering requirement (encoded + binding for tomorrow)

Clearance on **Tue Oct 27** proceeds in this order:

1. **Deploy** the fixed runner (install this package's `pilot_runner.py`
   over the stage file; verify SHA-256 `5d5e3860…` after install) and
   **restart** the daemon. Verify from the heartbeat: alive, status
   `held`, `desk_calls = 0`, journal census unchanged (757; 1 done,
   756 pending).
2. Let Tuesday's **09:15 ET tripwire action** come due first — it is the
   session's gate: in the clearance tick it executes (Gmail check)
   **before** any Tuesday TD action, and a dirty check re-raises the
   hold with zero TD calls.
3. **Then** write `state/tripwire_clear.json` containing exactly
   `{"verdicts": {"1a174da9074a6edf": "confirmed"}}` — **before 09:25
   ET**.
4. **Verify**: hold lifted; Oct-26 census terminal (1 done +
   149 `missed_late`, cause `tripwire_hold`); `desk_calls_by_day` has
   **no** `2026-10-26` key; Tuesday polls live and proceeding.

## Review gate

This successor is committed for **ChatGPT's independent inspection
before any clearance**. If that review cannot complete before the next
permitted clearance window, the pilot **skips / STOPs — it never
backfills**. Missed sessions stay missed; the Nov 2 finalization and
revision re-poll proceed only for sessions actually captured.
