# Erratum — Guard Evidence (commit 9a00f74) clearance description

The committed guard-evidence package
(`research_notes/td_pilot_guard_evidence_20261026/`, commit `9a00f74`)
describes tripwire clearance as marking aged-out actions `missed_late`
with cause `tripwire_hold`, without stating a kind limitation. That
description was **incomplete, and as a description of pre-fix behavior,
wrong in scope**:

- **Pre-fix truth:** `mark_stale` (as run by the live daemon through
  2026-10-26) stale-marked **only `ladder` and `finalization`** actions.
  A past session's `usage`, `revision`, and `archive_push` actions were
  **not** stale-marked on clearance and would have executed in the
  clearance tick's `run_due` loop. No clearance was ever performed under
  the pre-fix code, so no journal entry was ever affected by this gap;
  the Oct-26 session stands in the live journal exactly as the evidence
  package recorded it (1 tripwire action done, 149 actions pending,
  `desk_calls = 0`).
- **Post-fix behavior (this successor, Option B):** stale-marking is
  scoped by **session date** and covers **every action kind**: on
  clearance, all pending actions whose session date is strictly before
  the current ET date and whose due time has passed become terminal
  `missed_late` (cause `tripwire_hold`) before the hold lifts.
  Current-session actions are never stale-marked.

All other statements in the guard-evidence package (six guards PASS,
pins, quota behaviour, restart lineage, fail-closed record) are
unaffected by this erratum.
