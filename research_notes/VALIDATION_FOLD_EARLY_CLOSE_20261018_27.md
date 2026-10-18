# Memo — Fold Early-Close Contract (-27 r1): pinned-schedule grid supersedes the fixed two-bar grid

**Task:** `QF-FOLD-EARLY-CLOSE-CONTRACT-20261018-27 r1`
**Spec:** GitHub Issue #1 comment `6255676888` (-26 review: `INFERENCE_V2_DEFINITION_ACCEPTED__EARLY_CLOSE_CALENDAR_HOLD`)
**Date:** 2026-10-18 · **Mode:** offline, static synthetic fixtures only · **Elapsed:** ~7 min of the ≤20 min cap; one pass; one fixture-construction repair (~1 min, inside the ≤5 min allowance, disclosed below); no other repairs.

## Result

Amendment v3 freezes the early-close contract and supersedes **only** the schedule/grid clauses of preregistration §1. The confirmed defect — failure key `FOLD_EARLY_CLOSE_GRID_CONFLICT`: r1 demanded exactly two grid bars per session, so a legitimate 13:00 XNYS early close (whose canonical resampler correctly emits only the 09:30 partial 4H bar) would be falsely rejected as `BAD_GRID` — is closed by construction:

- The fold materializer now consumes a **separate pinned exchange-schedule artifact** (`XNYS_SESSION_SCHEDULE_V1`: session date, regular open, regular close, source/version, consumed under its SHA-256 pin). Absent → `SCHEDULE_MISSING`; pin mismatch → `SCHEDULE_PIN_MISMATCH`; malformed → `SCHEDULE_MALFORMED`.
- Expected anchors are **derived mechanically** from each session's regular close: 09:30 iff close is after 09:30; 13:30 iff close is after 13:30. An official 13:00 close therefore expects exactly one 09:30 bar and **still counts as one fold session**.
- **Never** fabricate a second bar, **never** infer an early close from missing data, **never** treat an early close as a holiday. Missing/extra bar versus the pinned schedule → `SCHEDULE_BAR_MISMATCH`; a bar on an unscheduled date → `SESSION_NOT_IN_SCHEDULE`.
- The pinned schedule is the sole calendar authority (r1's declared-holiday input and `UNRESOLVED_GAP` are retired as subsumed). No `pandas_market_calendars` dependency; generating a real schedule artifact remains a later qualified-data input step.

## Fixture evidence (all `SYNTHETIC_FIXTURE`)

Suite `test_fold_early_close.py`: **18/18 checks pass**, and `TEST_RESULTS.json` is byte-identical across two full runs. Synthetic calendar: 400 sessions from 2024-09-16 with 3 holidays absent from the schedule (2024-11-28, 2024-12-25, 2025-01-01) and 3 official 13:00 early closes (2024-11-29, 2024-12-24, 2025-07-03). Covered, per spec item 6: full session → 09:30+13:30; official 13:00 early close → 09:30 only and counted as one session; unexplained missing 13:30 on a full session → rejected; extra 13:30 on an early close → rejected; holiday absence accepted; DST transitions (2024-11-03 fall-back, 2025-03-09 spring-forward) with local anchors unchanged; duplicate and non-monotonic timestamps rejected; absent/unpinned schedule rejected; bar on an unscheduled date rejected; holdout touch rejected; fold/session counts and all digests deterministic across two runs (2 folds: expanding train 252/315, 63-session OOS blocks, 22-session tail dropped). Preservation asserted in-suite on every run: -25 materializer `b58194b4…`, Amendment v2 `03f5a564…`, and -26 inference v2 `81b213f6…` are byte-identical to their accepted pins.

**Disclosed repair (~1 min):** the first suite run failed 1/18 — the unscheduled-date fixture prepended `2024-11-28T09:30` to the head of the bar list, breaking monotonicity, so `NON_MONOTONIC` fired instead of the targeted `SESSION_NOT_IN_SCHEDULE`. Fixture construction only (sorted insertion); no materializer code, definition, or threshold changed. Re-run: 18/18, twice byte-identical.

## Prohibitions honored

Offline only (network used solely for the read-only public spec fetch and the delivery push). Zero real market/OHLC data; zero real exchange-schedule data (fixture schedule is synthetic and labeled); zero holdout access in any form; zero performance/backtest computation; zero strategy-module execution or imports; zero vendor/helper/model/API calls; zero installs, credentials, or credits; zero tuning; zero live/production/ledger writes; zero Issue #9 work; no prior frozen record edited — Amendment v3 supersedes §1's schedule/grid clauses by reference only, and Amendment v2 inference bytes are untouched.

## Verdict retained

`PRE_DATA_PREREG_READY__EXACT_FOLDS_PENDING_QUALIFIED_TIMESTAMPS_AND_PINNED_SCHEDULE`

Exact folds still await the separately authorized qualified-data step, which must now supply **both** qualified SPY session timestamps **and** a pinned schedule artifact.
