# Preregistration Amendment v4 — Calendar Coverage-Boundary Contract for the Fold Materializer

**Document:** `PREREGISTRATION_AMENDMENT_V4_20261018_28` (supersedes by reference only — no prior frozen record is edited)
**Task:** `QF-FOLD-CALENDAR-COVERAGE-BOUNDARY-20261018-28 r1`
**Spec:** GitHub Issue #1 comment `6256681829` (-27 independent review PASS: `EARLY_CLOSE_CONTRACT_ACCEPTED__QUALIFIED_CALENDAR_COVERAGE_HOLD`, dispatching -28)
**Date frozen:** 2026-10-18
**Status:** FROZEN BEFORE ANY QUALIFIED DATA PULL. No real market/OHLC data, no real exchange schedule, no holdout contents, and no real strategy outcomes were accessed, supplied, or computed. All fixtures are synthetic and labeled `SYNTHETIC_FIXTURE`.

## What this amendment supersedes — and only this

This amendment supersedes **only the calendar-span completeness clauses** implied by §1 of `PREREGISTRATION_20261018_25` as amended by Amendment v3 (`PREREGISTRATION_AMENDMENT_V3_20261018_27`): v2 established which sessions must be present *inside the span delimited by the first and last supplied bar dates*, but it did not bind that span to the frozen development interval. Everything else stands unchanged:

- §1's holdout window (2023-10-19 … 2024-09-15, `HOLDOUT_TOUCH`), `DEV_START = 2024-09-16`, `MIN_TRAIN_SESSIONS = 252`, `OOS_BLOCK_SESSIONS = 63` with expanding train and dropped partial tail, output digests and commit-before-OHLC rule;
- Amendment v3 in full: the pinned `XNYS_SESSION_SCHEDULE_V1` artifact contract, mechanical anchor derivation from the regular close (an official 13:00 early close expects exactly one 09:30 bar and counts as exactly one fold session), fail-closed bar conformance (`SCHEDULE_MISSING` / `SCHEDULE_PIN_MISMATCH` / `SCHEDULE_MALFORMED` / `SCHEDULE_BAR_MISMATCH` / `SESSION_NOT_IN_SCHEDULE` / `BAD_GRID` / `DUPLICATE_TIMESTAMP` / `NON_MONOTONIC` / `HOLDOUT_TOUCH` / `PRE_DEV_DATE` / `INSUFFICIENT_SESSIONS`), the prohibitions on fabricating bars, inferring early closes, or treating an early close as a holiday, and the pinned schedule as sole calendar authority;
- §2 (no-selection-on-OOS) in full;
- §3 (inference layer) **as amended by Amendment v2** — Amendment v2's bytes are preserved unchanged (SHA-256 `03f5a56444d1f3436270c863b85078dcbd924a441702e57b1a76d237eeee578a`).

The preserved prior consumers are asserted byte-identical by this task's test suite on every run: the -25 materializer (SHA-256 `b58194b40b8871581af5aa1135243630b557037917ec76d300579871707c1a4e`) and the -27 v2 materializer (SHA-256 `b969fc852c074e771a339da8bcf3ad79abd597c0b2e7c933b31fe8ae06bbc35b`). The superseding consumer is the new versioned artifact `fold_materializer_v3.py` in this package.

## Defect closed

**Failure key: `FOLD_DEV_PREFIX_SUFFIX_NOT_BOUND`.** The accepted v2 checks only that supplied dates are not *before* `DEV_START`, and checks missing scheduled sessions only between the first and last supplied bar dates. A silently truncated input beginning after 2024-09-16 — or ending before the intended as-of boundary — can therefore still pass and produce shifted folds. That conflicts with the frozen instruction to use qualified SPY sessions **beginning 2024-09-16**. A SHA-256 pin makes the supplied schedule immutable; it does not prove requested-interval completeness.

## Frozen coverage-boundary contract (v3)

**Extended pinned schedule contract.** The schedule artifact kind becomes `XNYS_SESSION_SCHEDULE_V2`: canonical JSON carrying `artifact`, `source`, `version`, `exchange` (must be exactly `XNYS`), `timezone` (must be exactly `America/New_York`), `coverage_start` (must be exactly `2024-09-16`), `coverage_end` (a valid calendar date **on/after** `coverage_start`), and `sessions[]` as in v1 (each `date`, regular `open`, regular `close`). The v1 kind no longer satisfies the consumer: a v1 artifact fails closed as `SCHEDULE_MALFORMED`, so coverage bounds can never be silently absent. Absent artifact → `SCHEDULE_MISSING`; SHA-256 pin mismatch → `SCHEDULE_PIN_MISMATCH`; any contract violation above (wrong/missing exchange, timezone, or frozen coverage_start; unparseable or inverted coverage_end; any v1 defect retained) → `SCHEDULE_MALFORMED`.

**Coverage interval.** `coverage_start` is frozen at **2024-09-16**, the first development session after the sealed holdout ends (2024-09-15). `coverage_end` is a separately supplied, **pre-outcome as-of boundary**: it is a field of the pinned schedule artifact itself, hence fixed by the artifact's SHA-256 pin and committed before any OHLC, outcome, or performance field exists anywhere in the pipeline. The closed requested interval is `[coverage_start, coverage_end]`. A scheduled session whose date falls inside the artifact's own declared coverage bounds but which the artifact does not list → `SCHEDULE_COVERAGE_DEFICIT` (see below).

**Endpoint mapping — through the schedule only.** The first required session is the first scheduled session **on/after** `coverage_start`; the last required session is the last scheduled session **on/before** `coverage_end`. If an endpoint is a weekend or holiday, it maps to the neighbouring scheduled session **only** through the pinned schedule — endpoints are never inferred from bar data.

**Completeness — fail closed.** The supplied bars must cover **every** scheduled session in the closed requested interval, each with exactly its derived anchor set (Amendment v3 rules unchanged):

- the first bar date is not the first required session (a missing prefix — the input begins late) → **`COVERAGE_PREFIX_MISSING`**;
- the last bar date is not the last required session (a missing suffix — the input ends early) → **`COVERAGE_SUFFIX_MISSING`**;
- any required session inside the span has no bars, or an incomplete anchor set → **`COVERAGE_INTERIOR_MISSING`** (this supersedes v2's span-relative `SCHEDULE_BAR_MISMATCH` for absent sessions; a *present* session with a wrong anchor set still fails as `SCHEDULE_BAR_MISMATCH`);
- a bar date after the last required session (input reaching past the frozen `coverage_end`) → **`COVERAGE_OVERSHOOT`**;
- the schedule artifact lists no session at all inside its own declared coverage interval → **`SCHEDULE_COVERAGE_DEFICIT`** (the artifact does not cover what it declares; note the pinned schedule is by definition the session authority, so artifact-side incompleteness beyond this case is not consumer-decidable — it is exactly the authenticity/completeness question reserved to the qualified-source gate below);
- a bar on a date absent from the schedule at all → `SESSION_NOT_IN_SCHEDULE` (retained).

**Output.** Canonical JSON as in v2, plus: `coverage_start`, `coverage_end` (the declared bounds consumed), `coverage_first_session`, `coverage_last_session` (the mapped first/last required sessions), and the retained `input_timestamp_digest`, `calendar_digest`, and `schedule_sha256` — so the output binds the requested interval, the mapped included sessions, and both digests. Identical inputs ⇒ byte-identical output, verified across two runs by the fixture suite.

**Scope limit — stated explicitly.** This contract proves **consumer interval completeness relative to the pinned artifact only**. The authenticity and completeness of a **real** exchange schedule remain a separate qualified-source gate; synthetic fixtures cannot prove them, and nothing in this amendment asserts them.

## Verdict retained

`PRE_DATA_PREREG_READY__EXACT_FOLDS_PENDING_QUALIFIED_TIMESTAMPS_AND_PINNED_SCHEDULE`

Exact fold dates still do not exist. They materialize deterministically only when the v3 materializer runs, at a separately authorized step, on (a) qualified SPY session timestamps and (b) a pinned schedule artifact produced by that later qualified-data step — and the output must be committed before any OHLC/outcome/performance field is supplied to any computation.
