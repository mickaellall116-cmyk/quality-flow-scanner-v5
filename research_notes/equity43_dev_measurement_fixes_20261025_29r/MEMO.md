# -29 narrow repair — session-time causality (P1/P8)

QF-EQUITY43-DEV-MEASUREMENT-FIXES-20261025-29r · 2026-10-25

Governing text: ChatGPT's independent -29 verdict (Slack thread TS
1792935577.054259, 2026-10-25 09:39 ET). The verdict was a partial
PASS — 25bps reconciliation, P4 docstring, P7 all-fire census
(2,892), P1 series arithmetic, and ledger/decision parity all stand
unchanged — with P1 and P8 HELD on session-time causality. This
package is exactly the verdict's narrow repair request, items 1–5.
The -29 package is not edited; the repaired modules succeed it here
(the same succession pattern as the P4 docstring successor).

## The defect (as held)

Both -29 modules derived bar completion by duration arithmetic:

* `mtm_allbar.py`: `BAR = 4h`; every completion = bar start + 4h.
  The committed series proved it: 826 bar-close marks per view — 415
  stamped 13:30 and 411 stamped 17:30. The equity grid is
  session-aware: bins are 09:30→13:30 and 13:30→16:00 ET, with
  calendar-specific early closes. The DD magnitude happened to equal
  bar-close-only arithmetic, but the causal timestamps were invalid.
* `qf_telemetry.py`: `BAR_DURATION_HOURS = 4`;
  `decision_time = signal_time + 4h` — rejecting a valid 13:30→16:00
  signal and accepting an invalid 17:30 completion. BAR_PATH and
  EXIT_DECISION carried only `bar_finalized=True`: no session-table
  bin-end guard, no `recorded_at >= decision_time` guard. And the
  schemas mandated fields not yet knowable at their event times
  (actual next-open entry + entry-derived TP1 on SIGNAL_FIRE; the
  next-open fill on EXIT_DECISION) — look-ahead inside the telemetry
  schema itself.

## Repair item 1 — pinned session-table bin_end (both modules)

New shared module `code/session_bins.py`. All bin resolution goes
through the pinned adopted session table of record —
`XNYS_SESSION_TABLE_751_UNION` (751 sessions, 2023-10-19..2026-10-16;
committed at `research_notes/equity43_feed_source_review_20261024_22/
bundle/calendar/session_table_751_qualified.json`), sha256
`00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f`,
verified on every load (missing or altered bytes refuse).

Bin convention: bin 1 = session open (09:30 ET) → min(13:30, session
close); bin 2 = 13:30 → session close, present only when the close
is later than 13:30. The table's closes are 744 × 16:00 and 7 ×
13:00, so durations are 4h / 2.5h on regular sessions and a single
3.5h bin (09:30→13:00) on early closes — no duration is a constant
of the repaired system, and no completion is computed arithmetically.
Fail-closed on: a session date absent from the table, a start that
is not a table bin start, a duplicate (ambiguous) session row, and
naive timestamps. DST transitions resolve through the table rows and
the America/New_York zone rules (bin ends carry −05:00 before the
2025-03-09 transition and −04:00 after, same wall clock).

Pre-flight evidence on the recorded DEV grid: all 1,043 union
(date, bin-start) pairs across the 43 symbols' closes resolve through
the table (0 outside), and the five DEV early-close sessions
(2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28, 2025-12-24) carry
exactly the single 09:30 bar — the convention matches the recorded
grid, not just the calendar.

`mtm_allbar.py` (repaired successor): the fork's accounting loop is
byte-for-byte the -29 logic; only the completion source changed —
`_ends_for()` resolves each series' bin ends through the table
(cached per series), `_bar_completion_times()` unions bin ends, and
both entry points validate the whole grid up front (any non-table
bar raises SessionTableError before any marking). The as-of mark at
event times selects the same completed bar as before (event times
are bin starts; the bin ending AT a 13:30 event is bin 1 under both
schemes, and the bin ending before a 09:30 event is the prior
session's last bin under both), which is why decisions and the
event-sampled track are provably unchanged — confirmed empirically
below.

## Repair item 2 — bin-end / recorded-at guards + availability split

`qf_telemetry.py` (repaired successor):

* SIGNAL_FIRE, BAR_PATH, EXIT_DECISION: `decision_time` must EQUAL
  the pinned bin_end of the record's bin (instant equality — a
  decision stamped with a stale UTC offset across a DST transition
  is a different instant and refuses), and `recorded_at >=
  decision_time` is now enforced for all three (BAR_PATH and
  EXIT_DECISION had no recorded-at guard in -29).
* Availability split. SIGNAL_FIRE no longer carries `tp1_level` or
  `intended_entry` (strict schema refuses them as unknown fields):
  the actual entry and the entry-derived TP1 arrive via the new
  ENTRY_OBSERVED record (observed next-bin open + ATR in force +
  derived TP1). EXIT_DECISION no longer carries `fill_time` /
  `fill_price`: the fill arrives via the new EXIT_FILL_OBSERVED
  record (observed next-bin open after the decision bar). Both
  observed records carry `recorded_at >= event instant` guards, and
  the journal enforces the cross-record link: the observed instant
  must be the start of the bin immediately following the fire /
  decision bin (the table's `next_bin_start`) — 13:30 for a
  first-bin fire (the same instant as its decision_time) and the
  next session's 09:30 for a second-bin fire. Neither observed
  record is an execution fill; EXECUTION remains refused in
  signal-only mode.
* Append order is causal, as in -29's no-backfill design: appends
  arrive in event order (an observation written at its instant
  precedes any later bin's fire in the journal); the per-symbol
  stream monotonicity track now keys on each record type's event
  instant (decision_time / entry_time / fill_time), and a late
  duplicate observation is refused as backfill (battery fixture).

## Repair item 3 — negative fixtures (all fail closed)

Refusal behavior: `append()` / grid validation raises
(TelemetryError / SessionTableError) and leaves state unchanged;
each battery exits 0 only if every expected refusal fires and every
valid record appends. Batteries: `test_session_bins.py` 20 checks,
`test_mtm_allbar.py` 18 checks (the -29 fixtures A–D retained with
unchanged expectations, plus repair fixtures E–H), `test_telemetry.py`
42 checks. The verdict's five fixture classes:

* 13:30→16:00 bin end: SIGNAL_FIRE and BAR_PATH stamped 17:30
  refused; stamped 16:00 accepted (battery + mtm fixture E, where
  the regenerated grid stamps second-bin completions 16:00).
* Early-close session (2025-07-03): decision stamped 13:30 refused,
  stamped 13:00 accepted; a 13:30 bin start on that session refused
  (gapped bin); mtm fixture F marks a held position through the
  session with the completion stamped 13:00-04:00 (DD 2.0% vs the
  event grid's 0).
* DST transition session (2025-03-10, EDT): decision stamped with
  the pre-transition −05:00 offset refused (wrong instant); 17:30
  refused; 16:00-04:00 accepted; table-level checks cover both 2025
  transitions; mtm fixture G stamps Fri 16:00-05:00 and Mon
  16:00-04:00 in one grid.
* Missing/gapped bin: non-session date (Sat 2025-01-04),
  beyond-table date (2026-11-02), and non-bin start (10:30) refused
  in telemetry and at table level; mtm fixture H refuses grids
  carrying a non-session bar, a 10:30 bar, and a phantom second bin
  on an early-close session.
* Retro-stamped (backdated) records: recorded_at before the event
  instant refused for SIGNAL_FIRE (retained from -29), BAR_PATH,
  EXIT_DECISION, ENTRY_OBSERVED, and EXIT_FILL_OBSERVED.

Plus pin enforcement: a byte-altered session table and a missing
table both refuse at load; a duplicate session row refuses as
ambiguous.

## Repair item 4 — P1 regeneration: DD unchanged, stamps repaired

Regenerated on the same recorded inputs (the -29 lane's
pipeline.pkl: canonical trades, closes, feats, cutoff) with the
repaired fork; the strategy / signal generation was NOT re-run
(measurement regeneration only). Harness `code/harness_repair.py`,
29/29 checks PASS (`artifacts/parity_repair.json`):

| view | event-sampled DD | held -29 all-bar DD | regenerated all-bar DD | Δ |
|---|---|---|---|---|
| gross | 23.97% | 25.575570% | 25.575570% | 0.000000 pp |
| 4bps | 24.61% | 26.183969% | 26.183969% | 0.000000 pp |
| 25bps | 25.40% | 26.703466% | 26.703466% | 0.000000 pp |

**The held 4bps figure 26.18397% stands exactly** — the verdict's
expectation is confirmed: the +4h defect corrupted the causal
timestamps, not the magnitudes, because each mis-stamped mark
carried the same completed bar's close and no event falls between
16:00 and 17:30. What changed is the stamps, now all pinned table
bin ends: per view, 827 bar_close marks = 412 @ 13:30 + 412 @ 16:00
+ 3 @ 13:00 (the early-close sessions inside the marked window);
zero 17:30 stamps remain. Census reconciliation vs the -29 series
(826 marks): the old count folded the three early-close bin-1 marks
into its 415 @ 13:30 (stamped 13:30 by arithmetic instead of 13:00)
and counted 411 @ 17:30 because the final session's second-bin end
coincided with the recorded cutoff (2026-10-16 17:30-04:00) and was
emitted only as the terminal event mark; the repaired series emits
that bin's own bar_close at 16:00 AND retains the terminal mark —
one inserted point (index 1302, value equal to the terminal value),
1,304 points total, every other mark value identical in order and
value to the -29 series (harness-verified per view). The drawdown
trough stamp is unchanged: 2026-03-27 13:30-04:00 (a first-bin end).

Parity (verdict item 4, second half): decisions/outputs identical
to the frozen baseline on every field, per view; event track ==
committed results.json; independent interval reconstruction agrees
with the fork (DD < 1e-9, 0 mark mismatches); phase5 under the
repaired fork reproduces the committed ledger byte-identically
(sha256 267e794c…) and the views differ only in max_drawdown_pct.

## Repair item 5 — P2/P3/P6/P9

Untouched, exactly as the verdict leaves them: this package contains
no source or test artifact advancing P2, P3, P6, or P9 semantics.

## Bounds

Measurement/telemetry code only. No BUY/EXIT logic changes, no
performance tests, no holdout access, no vendor calls. The -29
package, the committed -13 ledger/results, production (PAUSED), the
pilot, S1, and G4 are all untouched. Original C1 FAIL; no validated
edge.

## Files

* `code/session_bins.py` — pinned-table bin resolution (shared).
* `code/mtm_allbar.py` — repaired P1 measurement fork (successor).
* `code/qf_telemetry.py` — repaired P8 telemetry (successor).
* `code/harness_repair.py` — DEV regeneration + parity harness.
* `code/verify_package.py` — independent package verifier (PASS).
* `tests/test_session_bins.py` (20), `tests/test_mtm_allbar.py`
  (18), `tests/test_telemetry.py` (42).
* `artifacts/mtm_dev.json`, `artifacts/equity_series_allbar.json`
  (regenerated), `artifacts/parity_repair.json`.
* `SHA256_MANIFEST.txt`.
