# Journal counts — offline clearance simulation (Option B successor)

Source journal: live `state/pilot_state.json` copied read-only
(757 actions; the simulation never writes the live stage).

## Before (live journal, as copied)

| status | count |
|---|---|
| done | 1 (`tripwire|2026-10-26`) |
| pending | 756 |
| **total** | **757** |

`desk_calls = 0`, `desk_calls_by_day = {}`. Monday 2026-10-26 pending:
149 (105 ladder, 35 finalization, 5 revision, 3 usage, 1 archive_push).

## After simulated clearance processing only (Scenario A, Tue 09:20 ET)

| status | count |
|---|---|
| done | 1 |
| missed_late (cause `tripwire_hold`) | 149 |
| pending | 607 |
| **total** | **757** |

Changed set = exactly the 149 past-session pending actions; zero
current-session actions changed; `desk_calls = 0`; hold lifted; the
pending reply filed exactly once.

## After the full simulated clearance tick (Scenario B, Tue 09:20 ET)

| status | count |
|---|---|
| done | 3 (Mon tripwire + Tue `usage|…|pre_revision` + Tue `tripwire`) |
| missed_late (cause `tripwire_hold`) | 149 |
| pending | 605 |
| **total** | **757** |

Monday census terminal: 1 done + 149 missed_late. The tick's only TD
transport call is Tuesday's own `pre_revision` usage snapshot:
`desk_calls_by_day = {"2026-10-27": 1}` — **no `2026-10-26` key; the
Oct-26 zero-call fact is preserved.** Tuesday's 105 ladder polls remain
pending/live. A post-clearance restart changes nothing.

## Control (Scenario C, pre-fix runner, same inputs)

Simulated clearance executes **9 Monday-session actions** (3 usage,
5 revision, 1 archive_push) with **9 TD transport calls** — the defect
the successor removes.
