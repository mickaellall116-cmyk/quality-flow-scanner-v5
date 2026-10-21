# -61 CLOSURE MEMO — REQ-S2 boundary shim, offline synthetic qualification

Task: QF-TD-REQ-S2-BOUNDARY-SHIM-SYNTHETIC-20261020-61 r1
Spec: Issue #1 comment 6306666287 (-60 adjudication + GO; basis -60
result 921859a / pre-result aa186b9; -59 transform cited by receipt,
commits 6da0783 / 2832d39, NOT rerun).
Budget: ≤45 min, ONE offline attempt, first-failure stop, synthetic
fixtures only, NEW files only.
Start convention: elapsed from spec fetch 2026-10-21T02:53Z.

## Terminal verdict (verbatim)

TD_REQ_S2_BOUNDARY_SHIM_HOLD__SCHEDULE_PIN_MISMATCH

(spec terminal vocabulary: HOLD__<FIRST_FAILURE>; first failure =
SCHEDULE_PIN_MISMATCH, raised by the shim's own schedule-pin gate as
the first statement of the harness run.)

## Single-dispatch + lease

- Pre-check before ANY file operation: no td61 stage dir, no td61
  worktree, no -61 commit on origin/main, no owner lease. SOLE LANE.
- Atomic owner lease (O_CREAT|O_EXCL) acquired OUTSIDE the stage at
  ~/workspace/qf_td61_owner_lease.json (owner_session a0d6f97e…);
  released LAST, after result-commit remote verification.
- New task-unique detached worktree ~/workspace/qf_td61_wt at
  origin/main 1e27203. Main working tree never touched (pre-existing
  UU forward_test/kama_shadow.json intact); no stash touched.

## What was built (pre-execution commit 8434fce)

`s2_boundary_shim_v1.py` — the -60 §4 cutpoint as a separately
versioned offline candidate: constructor-row adapter (bar_id =
symbol|bar_start ISO, session = NY date; strict tag/timestamp
alignment, 09:30/13:30 anchors, strictly-increasing starts) →
boundary gates (E3 PIT-late, E2 receipt/ledger completeness,
unmatched-event-symbol refusal, E4 span-edge / out-of-span refusals)
→ -59 transform (loaded by path, sha256-verified against its pin
7791ca91…) with entries=[] → entry recomputation stub (surviving
bars only) → folds materialized on the pre-exclusion schedule.
Calendar binding: the transform's `xnys_sessions` is replaced by an
artifact-bound function over the pinned XNYS_SESSION_SCHEDULE_V2 and
its `mcal` handle is poisoned (any runtime-PMC consultation raises
PMC_FORBIDDEN). Frozen harness: the -60 §7 eight cases unchanged,
plus the case-1b orphan negative, the case-9 index-alignment
negative, spec assertions, and the July-3 parity record.

## First failure — full characterization (verbatim key line)

    s2_boundary_shim_v1.ShimRefusal: SCHEDULE_PIN_MISMATCH:
    .../XNYS_SESSION_SCHEDULE_V2.json sha256
    3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88
    != pin

Root cause (verified read-only after the stop; NO repair, NO rerun):
the shim's SCHEDULE_SHA256_PIN literal is 65 hex characters — a
one-character transcription defect introduced when the constant was
split across two string literals in the shim source ("…ed4310" +
"0c563ac…" duplicates the `0` at index 42). The artifact itself is
NOT implicated: its sha256, recomputed independently twice, is
3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88 —
exactly the qualified -35 r2 pin. The defect is in the -61 shim
source (Muse's proof-package code), the same failure class as the
-49..-58 harness-layer defects. Per first-failure discipline the
attempt stopped here: zero of the eight §7 cases executed, the
two-run byte-identity requirement is unmet, run1_output.json is
empty (0 bytes; the traceback went to stderr), run2 never started
(run_qualification.sh `set -e`). Per-case counters: 0/13 recorded
(all NOT_RUN). The failing literal becomes a named fixture for any
successor spec; a successor should also add a pre-execution
self-check that executes every pin gate before the attempt clock.

## July-3 parity outcome — REFUSED (not established)

Recorded in the harness source and restated here, NOT reconciled:
artifact fact — 2026-07-03 is absent from the pinned schedule's
sessions (non-session), 2026-07-02 present with close 16:00.
Gate-7 lineage label — "-56 CLOSURE_MEMO: candidate 2026-07-03
early-close fact = True". Gate source fact — dispatch_gate_r4.py
derive_calendar emits 'closed_2026_07_03': xnys_schedule(
'2026-07-03') is None. Whether the label and the source fact are
the same claim is expressly NOT adjudicated in -61; the spec
assigns it to the parallel Claude CP1 continuation. The shim's
adjacency binds to the artifact only, and no §7 case depended on
the disputed label (case 2 uses the Thanksgiving-2025 boundary:
2025-11-27 non-session, 2025-11-28 close 13:00) — but no case
executed, so this design intent is unevidenced by this run.

## Index-alignment negative — NOT RUN

Case 9 was built (swapped bar_start pair → ADAPTER_INDEX_ALIGNMENT)
but never executed; it is NOT marked unresolved-by-design and NOT
silently waived — it is simply unexecuted because the attempt
stopped at the schedule-pin gate before it. A successor reruns the
frozen harness unchanged, case 9 included.

## Timing / disclosures

Elapsed ≈44 min from spec fetch to result-commit push (≤45 budget).
Repair minutes: 0. One attempt; no rerun; no in-run repair.
Disclosure: the pre-execution commit (8434fce) was pushed before
the run, as preregistered; the defective pin literal is therefore
on the record in both commits. External rehash of the package
files was performed with paths proven to exist BEFORE worktree
removal (per the -58 runner lesson).

## Controls honored

Research-only; route NOT adopted/live-designated; entries PAUSED;
no corrected performance; no vendor/API/model calls or spend
(pre-run read-only spec fetch only); no real data / SPT-08 /
holdout / backtest; no strategy, production, trading, Yahoo, or
Issue #9 work; no frozen candidate edited (new files only).
Rollback: withdraw this shim candidate package — nothing was
integrated, no designation changed; the route stays
OFFLINE_CANDIDATE_NOT_ADOPTED and REQ-S2 stays HARD HOLD.
