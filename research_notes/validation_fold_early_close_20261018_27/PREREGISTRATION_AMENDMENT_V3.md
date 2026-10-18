# Preregistration Amendment v3 — Early-Close / Pinned-Schedule Contract for the Fold Materializer

**Document:** `PREREGISTRATION_AMENDMENT_V3_20261018_27` (supersedes by reference only — no prior frozen record is edited)
**Task:** `QF-FOLD-EARLY-CLOSE-CONTRACT-20261018-27 r1`
**Spec:** GitHub Issue #1 comment `6255676888` (-26 independent review PASS, dispatching -27)
**Date frozen:** 2026-10-18
**Status:** FROZEN BEFORE ANY QUALIFIED DATA PULL. No real market/OHLC data, no real exchange schedule, no holdout contents, and no real strategy outcomes were accessed, supplied, or computed. All fixtures are synthetic and labeled `SYNTHETIC_FIXTURE`.

## What this amendment supersedes — and only this

This amendment supersedes **only the schedule/grid clauses of §1** of `PREREGISTRATION_20261018_25`:

- the frozen clause "`BAR_GRID = {09:30, 13:30}` — exactly two bars per session; a session missing a grid bar … is a hard error (`BAD_GRID`)"; and
- the §1 input contract's optional declared-holiday date set, together with the `UNRESOLVED_GAP` check that depended on it.

Everything else stands unchanged: §1's holdout window (2023-10-19 … 2024-09-15, `HOLDOUT_TOUCH`), `DEV_START = 2024-09-16`, `MIN_TRAIN_SESSIONS = 252`, `OOS_BLOCK_SESSIONS = 63` with expanding train and dropped partial tail, output digests and commit-before-OHLC rule; §2 (no-selection-on-OOS) in full; §3 (inference layer) **as amended by Amendment v2** — Amendment v2's bytes are preserved unchanged (SHA-256 `03f5a56444d1f3436270c863b85078dcbd924a441702e57b1a76d237eeee578a`) and are asserted byte-identical by this task's test suite on every run. The -25 materializer file itself is preserved unedited (SHA-256 `b58194b40b8871581af5aa1135243630b557037917ec76d300579871707c1a4e`); the superseding consumer is the new versioned artifact `fold_materializer_v2.py` in this package.

## Defect closed

**Failure key: `FOLD_EARLY_CLOSE_GRID_CONFLICT`.** Under the superseded clause, every session had to contain both 09:30 and 13:30 bars. The canonical resampler (SHA-256 `2a4994a2…`) drops empty bins, so a legitimate 13:00 XNYS early close correctly yields only the 09:30 partial 4H bar — and the r1 materializer would falsely reject it as `BAD_GRID`.

## Frozen early-close contract (v2)

**Pinned schedule artifact.** The materializer accepts, in addition to the timestamp-only bar list, a separate exchange-schedule artifact and its expected SHA-256 pin. Artifact kind `XNYS_SESSION_SCHEDULE_V1`, canonical JSON: `artifact`, `source`, `version`, and `sessions[]`, each session carrying `date` (YYYY-MM-DD), `open` (HH:MM, regular open), `close` (HH:MM, regular close). An absent artifact fails closed (`SCHEDULE_MISSING`); a SHA-256 that does not match the pin fails closed (`SCHEDULE_PIN_MISMATCH`); a malformed artifact (bad kind, missing/empty source or version, unparseable or duplicate session, `close ≤ open`, or a session closing at/before the first anchor) fails closed (`SCHEDULE_MALFORMED`). No `pandas_market_calendars` dependency. Runtime generation of a real schedule artifact remains a later qualified-data input step; this amendment freezes only the artifact contract and its deterministic consumer.

**Mechanical anchor derivation.** For each scheduled session, the expected bar anchors are derived from its regular close and from nothing else:

- include anchor **09:30** when the regular close is after 09:30;
- include anchor **13:30** only when the regular close is after 13:30;
- therefore an official **13:00** close expects **exactly one 09:30 bar** and the session **still counts as exactly one fold session** in the 252/63 counts.

**Fail-closed bar conformance.** The bars supplied for a session must equal its derived anchor set exactly:

- a missing bar or an extra bar versus the pinned schedule → `SCHEDULE_BAR_MISMATCH` (no output);
- a scheduled session inside the supplied calendar span with no bars at all → `SCHEDULE_BAR_MISMATCH`;
- a bar on a date absent from the pinned schedule → `SESSION_NOT_IN_SCHEDULE`;
- a bar time outside {09:30, 13:30} → `BAD_GRID` (retained from r1);
- duplicate / non-monotonic timestamps → `DUPLICATE_TIMESTAMP` / `NON_MONOTONIC` (retained);
- a session inside the sealed holdout window, or before `DEV_START`, or on a weekend → `HOLDOUT_TOUCH` / `PRE_DEV_DATE` / `BAD_GRID` (retained).

**Prohibitions (never, under any input).**

- Never fabricate a second bar for an early-close session.
- Never infer an early close from missing data: an early close exists only because the pinned schedule declares that session's regular close. Missing data is a mismatch, not a schedule.
- Never treat an early-close session as a holiday: it is a session, it carries its 09:30 bar, and it counts once.
- Never silently drop a scheduled session.

**Calendar authority.** The pinned schedule is the sole calendar authority. A weekday absent from it is definitionally a non-session (holiday/closure) — this subsumes r1's declared-holiday input and `UNRESOLVED_GAP` check, which are retired. Conformance runs the other way than r1: instead of explaining absences, v2 forbids inventing presence — any bar on an unscheduled date fails closed.

**Output.** Canonical JSON as in r1, plus: `schedule_sha256` (the pin consumed), `schedule_source`, `schedule_version`, and `early_close_sessions` (the session dates whose derived anchor set is exactly {09:30}). Identical inputs ⇒ byte-identical output, verified across two runs by the fixture suite.

## Verdict retained

`PRE_DATA_PREREG_READY__EXACT_FOLDS_PENDING_QUALIFIED_TIMESTAMPS_AND_PINNED_SCHEDULE`

Exact fold dates still do not exist. They materialize deterministically only when the v2 materializer runs, at a separately authorized step, on (a) qualified SPY session timestamps and (b) a pinned schedule artifact produced by that later qualified-data step — and the output must be committed before any OHLC/outcome/performance field is supplied to any computation.
