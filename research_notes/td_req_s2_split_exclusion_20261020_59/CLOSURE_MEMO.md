# -59 CLOSURE MEMO — REQ-S2 split exclusion, offline implementation + synthetic qualification

Task: QF-TD-REQ-S2-SPLIT-EXCLUSION-OFFLINE-IMPLEMENTATION-20261020-59 r1
Spec: Issue #1 comment 6304679072 (adjudication of -58; transaction
proof PASS, commits 4269dde / 036abe7).
Budget: ≤45 min, ONE offline attempt, first-failure stop, synthetic
fixtures only.

## Terminal verdict (verbatim)

TD_REQ_S2_OFFLINE_IMPLEMENTATION_PASS__INDEPENDENT_REVIEW_PENDING

## Single-dispatch + lease

- Pre-check before ANY file operation: no td59 stage dir, no td59
  worktree, no -59 commit on origin/main, no owner lease. SOLE LANE
  confirmed (parent pre-check re-verified by this worker).
- Atomic owner lease (O_CREAT|O_EXCL) acquired OUTSIDE the stage at
  ~/workspace/qf_td59_owner_lease.json (owner_session da57e53d…);
  released LAST, after result-commit remote verification.
- New task-unique detached worktree ~/workspace/qf_td59_wt at
  origin/main 852227f. Main working tree never touched (pre-existing
  UU forward_test/kama_shadow.json intact); no stash touched.

## Component placement decision

Inventory (CONTRACT.md): constructed bars are produced per symbol by
the constructor candidate `construct_4h` (-49 package, pin 3f432e7e…)
behind the validator candidate and entrypoint candidate v7; folds
(`fold_materializer_v3`, -28) and indicators consume bars downstream.
NO existing module assembles constructed bars + candidate entries at
one named boundary. Per spec §1 fallback, REQ-S2 is implemented as a
SEPARATELY VERSIONED offline candidate module —
`s2_split_exclusion_v1.py` (sha256 7791ca91…) in this package — placed
by contract at that boundary (post-construction, pre-indicator,
pre-fold) and NOT integrated into any chain.

## Implementation

Pure deterministic transform `apply_split_exclusion(bars, entries,
split_events, acquisition_receipt, calendar_start, calendar_end)`:
XNYS session adjacency via pandas_market_calendars NYSE (never
civil-day arithmetic); per-symbol windows {prev(D), D, next(D)} unioned
with a deduplicated removed-session ledger citing every causing event;
bars AND candidate entries removed together; output is an exact subset
of inputs (no imputation/replacement/fill/synthetic bars); inputs
never mutated; acquisition-completeness receipt carried through
byte-identical (an INCOMPLETE fixture receipt stays INCOMPLETE).
Fail-closed codes: NON_SESSION_EFFECTIVE, MISSING_FIELD, EMPTY_FIELD,
DUPLICATE_CONFLICTING_EVENT, TZ_NAIVE, SESSION_LABEL_MISMATCH,
WINDOW_EDGE, BAD_DATE.

## Qualification (frozen synthetic harness, precommitted 6da0783)

Environment: unshare -n; CPython 3.12.3 / pandas 2.2.3 / PMC 4.5.1 /
numpy 1.26.4, venv built offline from the pinned 11-wheel wheelhouse
(env_receipt.txt; freeze == the -29 lock closure package set).

Test matrix: **16/16 PASS** —
calendar_facts, midweek_split, monday_holiday_boundary,
civil_day_negative, overlapping_union, two_symbol_isolation,
entry_removal_matches_bars, non_session_refusal (holiday),
non_session_refusal_sat, provenance_missing_refusal,
provenance_conflict_refusal, tz_naive_refusal, session_label_refusal,
receipt_unchanged, zero_imputation_ordering, no_input_mutation.

Key evidence:
- Midweek D=2026-07-08 → removed AAA sessions exactly
  {07-07, 07-08, 07-09} (6 bars).
- Holiday boundary D=Mon 2026-07-06 → window {Thu 07-02, 07-06, 07-07}
  by session adjacency (Fri 07-03 is an XNYS holiday). Negative test:
  civil-day arithmetic gives {07-05, 07-06, 07-07} — it would MISS
  07-02 and target nonexistent Sun 07-05; transform output differs and
  is the session-correct set.
- Overlap: events 07-07 + 07-09 → union {07-06..07-10}, ledger deduped,
  session 07-08 cites both causing events.
- Zero imputation: output bar ids a strict subset of input ids; counts
  reconcile exactly; post-exclusion rolling-mean recomputed from
  bars_out equals an independent from-scratch recomputation; session
  sequence strictly increasing with no placeholders.
- Inputs deep-hash identical before/after (no mutation).

Two runs: byte-identical outputs, sha256
af9f5ccb830d1e53910ac261711d188514c82647533d5e6900109d02f6084edd
(run1_output.json == run2_output.json).

## Timing / disclosures

Elapsed ≈22 min from spec fetch to result-commit push (≤45 budget).
Repair minutes: 0. One attempt; no rerun; no protocol deviations.
External rehash of committed files was performed with paths proven to
exist BEFORE worktree removal (per the -58 runner lesson); failed
shell lines are nowhere cited as evidence.

## Controls honored

Research-only; route NOT adopted/live-designated; entries PAUSED; no
corrected performance; no vendor/API/model calls or spend (pre-run
read-only spec fetch only); no real data / SPT-08 / holdout /
backtest; no strategy, production, trading, Yahoo, or Issue #9 work.
REQ-S2 implementation is an offline candidate pending independent
review — it is not merged into the route chain by this task.
