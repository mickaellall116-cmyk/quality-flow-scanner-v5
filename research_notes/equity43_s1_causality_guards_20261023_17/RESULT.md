# QF-EQUITY43-S1-CAUSALITY-GUARDS-20261023-17 r1 — RESULT

**VERDICT: HARDENING PASS** — both blockers from ChatGPT's independent
-16 adjudication (Issue #1 comment 6379306726) are closed, offline, in a
new research-only fork. The DEV decision-parity core re-derives
**DECISION_PARITY_PASS** under the hardened reporter; the observer now
emits bins causally at bin close; and the full DEV run replays
byte-identically from its journal alone.

This is NOT a validated edge, NOT S1 clearance, and NOT a launch
approval. S1/S2 remain unactivated; launch still needs Mike's separate
GO, a live feed (FEED_NOT_READY), a session-table extension beyond
2026-10-16 (not built), and the G4 adoption decision.

Governing text: Issue #1 comment 6379306726. ACK: Slack TS
1792814346.426739; bridge commit
3bd79bc8370ee4ecdcb0a57b1f1922032733362b. Single-dispatch check was
CLEAR before any file operation (no qf_td17 stage, no -17 package
path, no pre-execution commits on origin/main at head 48c8cf4).

## (A) Reporter contract hole — CLOSED

The -16 adjudication's exploit is reproduced verbatim against
report16.py: deleting `per_field.exit` and `detail.exit` from the -16
patched PASS artifact still re-derives DECISION_PARITY_PASS there
(battery check H0). Successor `report17.py` requires the COMPLETE
inventory — all 10 sections present and non-empty; inventory.pins PASS
evidence; config sha 87b8285a… + sector sha a91222c7… + frozen
constants; reference cohort 586/4/590 + skipped_gap 1 + cutoff; stream
raw_rows 157,140, rejected 0, journal verified and internally
consistent; bars 44,849; benchmark 524; closes 43 symbols exact;
field census per_field AND detail key sets exactly the 12
simulator-consumed fields, every detail.compared == 590, detail
mismatches == per_field, total == sum(per_field), the only tolerated
residual being the documented `censored` key-presence artifact;
decision parity with terminal inventories deep-equal and C0 pinned to
193/323/74 on BOTH sides; self-check clean with C0 == 193/323/74.

Battery (test_reporter17.py, 27/27): the exit-census hole (H1) plus 19
negative mutations — exit detail removed, exit per-field removed,
compared counts zeroed, section renamed, reference absent, bar cohort
emptied, benchmark sessions zeroed, inventory evidence missing, field
renamed, terminal inventory emptied, config sha zeroed, journal_info
removed, detail emptied, census section emptied, verdict flipped on a
STOP doc, reference counts zeroed, C0 altered, raw_rows altered,
recorded-verdict disagreement — EVERY one re-derives STOP; CLI exit
codes 0/2 verified. Controls on the committed artifacts under
report17: -16 patched → DECISION_PARITY_PASS (exit 0); -16 orig15 →
STOP (276 exit / 201 decision mismatches); -15 artifact → STOP
(missing sections + 201 decisions).

## (B) Fail-before on the frozen -16 observer (synthetic, timed)

- FB1 latency: feeding one full session (2024-03-07) row by row, the
  -16 observer emits **0 bars** after the last row — both 4H bars
  appear only when the NEXT session's first row arrives. The 13:30
  decision could not have been made at 13:30.
- FB2 journal insufficiency: the -16 journal over the same session
  contains **0 INPUT records** and BAR records whose payloads exclude
  the bar — journal-only replay is impossible.

## (C) Observer-only causal fix (fork of the -16 observer)

Fork: base sha256 0f5a6638… (-16 observer) → 929c1bc4….
Journal / SessionTable / CandidateMachine regions are byte-identical
to -16 (the -16 exit repair is carried verbatim; strategy sources and
frozen pins untouched). Changes are confined to SymbolFeed
finalization, ForwardObserver journaling, snapshot/restore, and an
appended replay function (observer17_vs_16.diff, 375 lines).

- A bin is emitted the moment its last member hour is admitted:
  emitted_at == bin close == decision_instant, built only from rows
  stamped before the bin close (PA1). flush() adds no bars for
  completed sessions — live decisions never depend on it (PA2).
- Early close 13:00: single bin emitted at its close with the phantom
  15:30 stamp still EXCLUDED_POSTCLOSE (PA3).
- DST both directions: sessions 2024-03-08 (EST) / 2024-03-11 (EDT) /
  2024-11-01 (EDT) / 2024-11-04 (EST) emit at close with correct UTC
  offsets −05:00/−04:00 (PA4).
- Gaps fail closed per-bin: a bin with a missing member fails the
  session when its close provably passes (a stamp at/past the bin end
  is admitted), at a post-close seal, or at the backstop — no bars for
  uncompleted bins, late members refused (PA5: missing 11:30 →
  SESSION_INCOMPLETE known at the 13:30 admission, 0 bars that date,
  late bar LATE_BAR). Disclosed semantic: a bin COMPLETED before a
  later same-session gap is discovered stands (PA6: bin1 emitted at
  13:30; bin2 missing 14:30 → incomplete, bin1 stands) — this differs
  from the batch session-atomic rule ONLY for sessions that gap
  mid-session, a fact unknowable at the completed bin's close. The DEV
  bytes contain no such session (recheck parity below is exact).
- Outage truncation: a session abandoned after 10:30 is sealed
  incomplete at the next session's first bar with the full missing
  list; backfill refused (PA7).
- One deliberate classification change, documented in the source:
  with causal finalization, DUPLICATE and the post-close EXCLUDED
  class are judged BEFORE the finalized/LATE_BAR check, restoring
  exactly the classes -15/-16 assigned before their sessions
  finalized a day late (the -15 suite's T07/T10/T11/T15 all verify
  this precedence on the fork).

Causality suite (test_causality17.py): 12/12 (FB1–FB2, PA1–PA10).

## (D) Immutable provenance + journal-only replay

Every ingested raw row is journaled first as an INPUT record
(canonical payload, hash-chained) and every BAR event journals its
full bar payload. `replay_journal` rebuilds a run from the journal
alone — INPUT payloads in order, flush() at each SEALED record — and
requires byte identity:

- Synthetic (150-session trend run): 1,047 inputs, 1,505 records,
  byte-identical, journal sha256 8a7dea451a65548f… both sides (PA8);
  tampered journal refused at verify (PA9); journaled BAR payloads are
  exactly the observer's bars, 299/299 (PA10).
- DEV recheck journal: **157,140 inputs replayed; 226,043 records
  reproduced byte-identically; journal sha256
  578eb1bb645e893072e1685dd64e42fd… on both files (88,644,343 bytes
  each)**. Cross-check: 226,043 = 68,903 (-16 journal) + 157,140 INPUT
  receipts, exactly.

## Rechecks on the fork

- -15 adversarial suite: **18/18** (test15suite_fork_stdout.txt).
- -16 regression suite: **10/10** (test16suite_fork_stdout.txt).
- DEV decision parity, single governed re-run (decision_compare17.py
  = the -16 harness with naming changes only), driving the fork:
  census 0 consumed-field mismatches (detail.compared 590 × 12;
  documented censored strict residual 586); decisions 0; RS 0;
  terminal inventories identical in all views; C0 193/323/74 both
  sides; reference self-check clean; bars 44,849 (SessionVWAP max abs
  diff 4.547e-13, identical to -15/-16); benchmark 524 equal; closes
  43/43 exact; stream raw_rows 157,140, rejected 0, excluded_postclose
  61, decision_events 1,460 (both counts identical to -15/-16);
  journal 226,043 records, verified, head 01a05d953431e2d0….
  report17.py re-derives **DECISION_PARITY_PASS** (exit 0) from the
  committed compare17_fork17.json.

## G4/VBASIS + feed facts (desk-only)

See G4_FEED_FACTS.md in this package: VBASIS mechanics (SPY 44 flags
with no basis event; flagged-ratio continuum 0.528–1.950 vs a discrete
split-factor step), the price-side STEP lane PASS, calibration options
that use event controls and corroboration rather than returns,
adjust=splits receipt facts, and the UNQUALIFIED items — live rights,
live latency (never measured), live completeness, and the unbuilt
post-2026-10-16 session table. Facts only; no adoption.

## Bounds held + environment disclosure

Offline only; 0 vendor calls / 0 credits; holdout sealed and not
accessed; no performance figures; no tuning; no production/resume
changes; -15/-16 packages untouched. PAUSED production pins identical
before/after: forward_test/PAUSE_NEW_ENTRIES present,
RESUME_NEW_ENTRIES absent, v54_forward_harness.py sha256
ce7c902ce182683c….

Environment note (reproducibility): this VM's python lacks
pandas_market_calendars (the batch reference path needs it for XNYS
session closes). It was installed STAGE-LOCALLY with --no-deps
(pandas_market_calendars 4.6.1 + exchange_calendars, pyluach,
korean_lunar_calendar, toolz, tzdata) under the task stage's pylibs/;
the system pandas 2.1.4 / numpy 1.26.4 were NOT upgraded (an earlier
full-dependency install that pulled pandas 3.1.0 was discarded unused
for exactly that reason). Session closes verified against the pinned
table (16:00 full, 13:00 early, None on holidays).

## Exact residual blockers

1. S1 activation: Mike's separate GO naming a future T0 — not given,
   not requested by this task.
2. Live feed: FEED_NOT_READY — live rights and latency UNQUALIFIED
   (facts sheet §4); no live pull has ever been run.
3. Session table ends 2026-10-16: extension not built (facts §5).
4. G4/VBASIS adoption: still UNADOPTED — calibration is an
   adjudication decision (facts §2); all DEV inputs remain
   candidate-grade.
5. The fork is a research candidate, unadopted: adoption of
   fwd_observer17.py / report17.py as the pinned S1 instruments is a
   separate decision.

Elapsed: ~42 minutes (03:57Z start, 04:39Z delivery).
