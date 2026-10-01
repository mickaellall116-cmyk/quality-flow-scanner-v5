# PR #7 live verification — first merged-code cycle (2026-09-30)

Archival record of the first hourly V5.4 forward-test cycle running merged
PR #7 code, plus the pre-cycle state migration that made the pending-entry
containment work. Published to the GitHub research record 2026-09-30.

## 1. Merge under test

- PR #7: "protect V5.4 exits during Yahoo degradation"
- Merge SHA: `76cf0a0f0039e8ef934bbe00f334425ea2700e0d`
- Merged into main 2026-09-30 13:05:59Z (Mike)
- Local working tree synced the two changed files
  (`v54_forward_harness.py`, `tests/test_v54_forward_harness.py`) from
  origin/main at ~09:15 ET; the canonical
  `scanner_rules.bar_close_at()` dependency was already on main.
- Cycle under test: the 09:41 ET hourly forward-test cycle
  (first cycle executing the merged code).

## 2. Pre-cycle migration (09:38 ET, Mike-authorized)

**Problem found during acceptance-check prep:** the merged void logic in
`_process_symbol` keys off `data_missed_while_pending`, a flag only the
*new* code sets on deferral. CRWD/OKTA/RBRK had been deferred 44 times
each under pre-merge code, so their flags were empty. On data recovery the
merged code would have skipped the void check and filled them at the
2026-09-28 next-bar open — a two-day-old retrospective fill, exactly what
the amendment was built to prevent.

**Action:** armed the flags to reflect what actually happened:

| signal_id | data_missed_while_pending | last_defer_time_utc (from log) |
|---|---|---|
| v54:CRWD:4h:2026-09-28T10:30:00-04:00:2026-09-15-v54 | true | 2026-09-30T12:51:10.180991+00:00 |
| v54:OKTA:4h:2026-09-28T10:30:00-04:00:2026-09-15-v54 | true | 2026-09-30T12:51:10.181185+00:00 |
| v54:RBRK:4h:2026-09-28T10:30:00-04:00:2026-09-15-v54 | true | 2026-09-30T12:51:10.181220+00:00 |

Timestamps are the actual latest pre-merge `entry_data_deferred`
`logged_at` values per signal_id from `v54_forward/forward_test.jsonl`
(44 deferrals each) — not invented. Before/after state snapshots and a
machine-readable audit note are preserved alongside this report:

- `research_notes/pr7_migration_audit_20260930_0938.json`
- (local) `v54_forward/state.json.pre_pr7_migration_20260930_0938`
- (local) `v54_forward/state.json.post_pr7_migration_20260930_0938`

## 3. 09:41 ET cycle verdict (Mike's four acceptance criteria)

Evidence: `v54_forward/forward_test.jsonl` events with
`logged_at` in 2026-09-30T13:41:00Z–14:05:00Z (append-only log; the
per-cycle `last_cycle_summary.json` is overwritten hourly and no longer
holds this cycle).

- **C1 — open-position priority: PASS.** 13 open positions, zero
  `exit_data_deferred` events of any reason. The priority prefetch
  (open positions + market symbols before the 250-symbol scan) held; no
  exit was starved by `cycle_budget_exhausted`.
- **C2 — pending-entry disposition: CONTAINED (2 of 3 resolved).**
  - CRWD and OKTA: `entry_unexecutable_after_outage`
    (`stale_basis=newer_completed_bars`, 4 newer completed bars beyond
    the intended fill bar, `fill_bar_end=2026-09-28T18:30:00+00:00`).
    No retrospective fill. This is the armed migration working as
    designed — without it both would have filled at the 9/28 open.
  - RBRK: `entry_data_deferred` (`reason=cycle_budget_exhausted`) —
    still pending, flags armed, awaiting Yahoo data. Correctly
    contained, not filled.
- **C3 — degraded discipline: PASS.** Cycle reported DEGRADED
  (~110 of 250 symbols lacking fresh primary data), new entries
  suppressed, GitHub publish skipped per the safety rule.
- **C4 — chronological catch-up + recovery record: PASS.** All 13
  open-position symbols logged `data_outage_recovered` with 5 bars
  caught up each (44 prior outage cycles, prior reason
  `cycle_budget_exhausted`); CRWD/OKTA recovery records complete
  (`bars_caught_up=0` is correct for a voided entry — no bars walked).

The 10:20 ET read-only check
(`check_first_merged_cycle.py`, kept in the goal workspace) confirmed
the same verdict; its two FAIL flags were script strictness, not
integrity findings (`last_defer_time_utc` is only emitted on the
single-new-bar void path; `bars_caught_up=0` is correct for voids).

## 4. Open items

- **RBRK** remains pending with armed flags. On data return it is
  expected to void via `newer_completed_bars`, like CRWD/OKTA. Worth a
  glance on the next cycle where its data recovers.
- **Count note:** the acceptance brief said "18 open positions"; state,
  status snapshot, and the event log all agree the actual open count was
  13. Flagged, not assumed — Mike to reconcile if his 18 counted
  something else.

## 5. Evidence inventory

| artifact | location |
|---|---|
| this report | `research_notes/pr7_live_verification_20260930.md` |
| migration audit (machine-readable) | `research_notes/pr7_migration_audit_20260930_0938.json` |
| before/after state snapshots | (local) `v54_forward/state.json.{pre,post}_pr7_migration_20260930_0938` |
| cycle events (append-only) | (local) `v54_forward/forward_test.jsonl` ≥ 2026-09-30T13:41:00Z |
| acceptance check script | (goal workspace) `v5-4-forward-test/hidden_files/check_first_merged_cycle.py` |

No harness, test, scanner-rule, or strategy code was modified for this
verification. Read-only with respect to production.
