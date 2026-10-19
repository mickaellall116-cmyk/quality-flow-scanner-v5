# Memo — Fold Calendar Coverage Boundary (-28 r1): the bar span is now bound to the frozen coverage interval

**Task:** `QF-FOLD-CALENDAR-COVERAGE-BOUNDARY-20261018-28 r1`
**Spec:** GitHub Issue #1 comment `6256681829` (-27 independent review PASS: `EARLY_CLOSE_CONTRACT_ACCEPTED__QUALIFIED_CALENDAR_COVERAGE_HOLD`)
**Date:** 2026-10-18 · **Mode:** offline, static synthetic fixtures only · **Elapsed:** ~9 min of the ≤20 min cap; one pass; zero repairs (no predeclared fixture failed; two authoring-time clarifications — ordering of the artifact-deficit check before bar-side checks, and the deficit definition aligned to what a consumer can decide — were made before the first suite run and are recorded in the amendment and code comments).

## Result

Amendment v4 freezes the calendar coverage-boundary contract and supersedes **only** the calendar-span completeness clauses of preregistration §1 as amended by Amendment v3. The isolated gap — failure key `FOLD_DEV_PREFIX_SUFFIX_NOT_BOUND`: v2 checked missing scheduled sessions only between the first and last *supplied* bar dates, so a silently truncated input beginning after 2024-09-16, or ending before the intended as-of boundary, could pass and produce shifted folds — is closed by construction:

- The pinned schedule contract is extended (`XNYS_SESSION_SCHEDULE_V2`): `exchange=XNYS`, `timezone=America/New_York`, `coverage_start` frozen at **2024-09-16**, and `coverage_end` as a separately supplied, pre-outcome as-of boundary — a field of the pinned artifact itself, hence fixed by its SHA-256 pin and committed before any OHLC/outcome/performance field exists. A v1 artifact (no coverage fields) now fails closed as `SCHEDULE_MALFORMED`; wrong/missing exchange, timezone, or frozen start, and inverted bounds, fail the same way.
- The closed requested interval is `[coverage_start, coverage_end]`. Endpoints map **through the pinned schedule only**: the first required session is the first scheduled session on/after `coverage_start`; the last required session is the last scheduled session on/before `coverage_end` — a weekend/holiday `coverage_end` maps to the preceding scheduled session, never inferred from bars.
- Supplied bars must cover **every** scheduled session in the closed interval: missing prefix → `COVERAGE_PREFIX_MISSING`; missing interior session → `COVERAGE_INTERIOR_MISSING`; missing suffix → `COVERAGE_SUFFIX_MISSING`; a bar past the frozen `coverage_end` → `COVERAGE_OVERSHOOT`; an artifact listing no session inside its own declared interval → `SCHEDULE_COVERAGE_DEFICIT`. All -27 early-close rules, schedule-pin checks, holdout exclusion and 252/63 fold logic are retained unchanged; a present session with a wrong anchor set still fails as `SCHEDULE_BAR_MISMATCH`.
- Output adds `coverage_start`, `coverage_end`, `coverage_first_session`, `coverage_last_session` alongside the retained `input_timestamp_digest`, `calendar_digest` and `schedule_sha256`.
- **Scope limit (explicit):** this proves consumer interval completeness **relative to the pinned artifact only**. Authenticity/completeness of a **real** exchange schedule remains a separate qualified-source gate; fixtures cannot prove it.

## Fixture evidence (all `SYNTHETIC_FIXTURE`)

Suite `test_fold_coverage_boundary.py`: **25/25 checks pass**, and `TEST_RESULTS.json` is byte-identical across two full runs (SHA-256 `40e5d0d15d4693d3abaf58e2f2a00b0574519c52881736cc8072da1a2e648853`). Synthetic calendar: the -27 fixture's 400 sessions from 2024-09-16 (3 holidays absent from the schedule; 3 official 13:00 early closes), now declared under V2 bounds. Covered, per spec item 6: exact full interval PASS (output binds bounds, first/last included session, both digests); delayed first session FAIL (`COVERAGE_PREFIX_MISSING`); missing final scheduled session FAIL (`COVERAGE_SUFFIX_MISSING`); missing interior session FAIL (`COVERAGE_INTERIOR_MISSING`); weekend `coverage_end` mapping to the preceding scheduled session; a holiday inside the interval never becoming a session (calendar digest independently recomputed); early close remaining exactly one session; bad exchange / timezone / coverage_start / inverted bounds FAIL (`SCHEDULE_MALFORMED`); bars past the frozen `coverage_end` FAIL (`COVERAGE_OVERSHOOT`); artifact coverage deficit FAIL; v1 artifact rejected; retained absent/unpinned schedule and missing/extra-bar rejections; two-run byte identity; fold counts unchanged (2 folds: train 252/315, 63-session OOS blocks). Preservation asserted in-suite on every run: -25 materializer `b58194b4…`, -27 v2 materializer `b969fc85…`, Amendment v3 `26f7ad4f…`, Amendment v2 `03f5a564…`, and -26 inference v2 `81b213f6…` are byte-identical to their accepted pins.

## Prohibitions honored

Offline only (network used solely for the read-only public spec fetch and the delivery push). Zero real market/OHLC data; zero real exchange-schedule data (fixture schedule is synthetic and labeled); zero holdout access in any form; zero performance/backtest computation; zero strategy-module execution or imports; zero vendor/helper/model/API calls; zero installs, credentials, or credits; zero tuning; zero live/production/ledger writes; zero Issue #9 work; no prior frozen record edited — Amendment v4 supersedes §1's coverage-boundary clauses by reference only, and all -25/-26/-27 bytes are untouched.

## Verdict retained

`PRE_DATA_PREREG_READY__EXACT_FOLDS_PENDING_QUALIFIED_TIMESTAMPS_AND_PINNED_SCHEDULE`

Exact folds still await the separately authorized qualified-data step, which must supply qualified SPY session timestamps **and** a pinned V2 schedule artifact whose coverage bounds are frozen pre-outcome.
