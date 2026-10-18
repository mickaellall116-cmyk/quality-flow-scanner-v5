# Validation Preregistration Finalization — Folds, OOS Rule, Inference Layer

**Task:** `QF-VALIDATION-PREREG-FINALIZATION-20261018-25 r1`
**Spec:** GitHub Issue #1 comment `6254836836` (-24 review PASS `GOVERNANCE_CLOSURE_PASS__25_OF_27_PASS__PRE_DATA_PREREG_REMAINS`, dispatching -25)
**Predecessor records:** -21 consolidation (matrix `d913ce6a…`) · -22 recovery (commit `8e0a187`) · -23 adoption (commit `a81e1c3`) · -24 governance closure (memo `dbc37618…`, matrix `dd0c2673…`, commit `a600940`)
**Mode:** OFFLINE, static/synthetic fixtures only. One pass, no repair/rerun.
**Date:** 2026-10-18

## Verdict: `PRE_DATA_PREREG_READY__EXACT_FOLDS_PENDING_QUALIFIED_TIMESTAMPS`

All 27 matrix fields now PASS. The last two open fields are closed at the only level closable before data exists: 4.2's fold **mechanics** are frozen in executable bytes and fixture-proven (exact fold dates materialize deterministically at a separately authorized pull — they cannot exist before qualified timestamps do), and 4.5 is frozen in **operational** (checkable) form. Nothing here computes, implies, or previews any validation result.

**Package** (`research_notes/validation_prereg_finalization_20261018_25/`): `PREREGISTRATION.md` (sha256 `ccf1a988…`) · `fold_materializer.py` (`b58194b4…`) · `inference_layer.py` (`64e8ec1b…`) · `test_prereg_finalization.py` (`3d22a717…`) · `TEST_RESULTS.json` (`8db456ba…`) · `READINESS_MATRIX.json` (supersedes -24's) · `SHA256_MANIFEST.txt`.

---

## 1. Fold materializer (field 4.2 — mechanics frozen)

`fold_materializer.py` is a pure-stdlib, **timestamp-only** procedure (no `pandas_market_calendars`). It accepts only bar timestamps (`YYYY-MM-DDTHH:MM`, America/New_York) plus an optional declared-holiday set — its signature and import surface are machine-checked in the test suite, and a non-string "timestamp" (e.g. a dict carrying price fields) is rejected. Frozen constants: sealed holdout `2023-10-19 … 2024-09-15` hard-excluded (`HOLDOUT_TOUCH` if supplied, never silently skipped); development calendar = qualified SPY regular sessions from `2024-09-16`; grid exactly `{09:30, 13:30}`; expanding train minimum **252 sessions**; fixed non-overlapping OOS blocks of **63 sessions**, stepped by 63; a final partial block is **dropped**. Output is canonical JSON carrying `input_timestamp_digest` and `calendar_digest` (SHA-256) and must be committed **before** any OHLC/outcome/performance field is supplied downstream. Fail-closed named errors: `MALFORMED_TIMESTAMP`, `DUPLICATE_TIMESTAMP`, `NON_MONOTONIC`, `BAD_GRID` (off-grid bar, incomplete session, weekend session), `UNRESOLVED_GAP` (missing weekday not in the declared-holiday set), `HOLDOUT_TOUCH`, `PRE_DEV_DATE`, `INSUFFICIENT_SESSIONS`.

Fixture proof (synthetic calendar: business days from 2024-09-16, 3 declared holidays, 481 sessions): exactly 3 folds materialize (train 252/315/378 sessions; OOS 2025-09-08→2025-12-03, 2025-12-04→2026-03-02, 2026-03-03→2026-05-28), the 40-session tail is dropped, digests recompute independently, and every fail-closed case fires with its named code.

## 2. Operational no-selection-on-OOS rule (field 4.5 — frozen)

Frozen in preregistration §2 as mechanics, not intent. **Prohibited:** after OOS/holdout evaluation in a research family, its results may not alter, select, filter, or motivate changes to entries, exits, ranking, thresholds, universe, risk, costs, folds, or gates — indirect selection (which variant to report, which fold to emphasize, whether to continue) is explicitly included. **Logged:** every attempted variant is append-only recorded in the family ledger with timestamp, variant id, change description, motivating information class (`TRAIN_ONLY` / `PRIOR_THEORY` / `OOS_INFORMED`), and disposition; no failure is ever erased. **Breach (fail-closed):** an OOS-informed change creates a new research family, permanently retires the exposed OOS slice from confirmation use in both families, and must be recorded in the ledger and a memo before any further computation; results under a breached configuration are not validation evidence. **Holdout:** the sealed window may be opened at most once, only after independent checkpoint approval plus a pinned qualified dataset/calendar; the opening is logged and irreversible.

## 3. Inference layer (A1 strengthened — frozen before readouts)

Frozen in preregistration §3. Economic gates remain primary; `p < 0.05` cannot rescue a failed economic gate.

- **Descriptive (n = 50 and n = 100):** mean net-R, sample sd, simple t-stat, two-sided 95% t CI on per-trade R — labeled `DESCRIPTIVE_ONLY` in code, because trades cluster across time/symbols.
- **Primary uncertainty:** circular block bootstrap over the chronological daily-portfolio-return series — **20-session blocks, 10,000 deterministic replications**, seed = first 8 bytes (big-endian) of the preregistration's SHA-256 (fixture value `14767771057543718562`). Outputs: two-sided 95% percentile CI for the mean and a one-sided edge test, `p = (1 + #{rep means ≤ 0}) / (10000 + 1)`.
- **Holm family F (exactly 6, formal only at n = 100):** `H_pooled`, `H_cohort_UX51`, `H_cohort_X2`, `H_grade_A`, `H_grade_B`, `H_grade_C`. Raw one-sided p-values are Holm step-down adjusted as one family; support requires adjusted p < 0.05 **and** the corresponding economic gate passed.
- **n = 50** is interim only: descriptive statistics and the bootstrap CI may be reported; no formal hypothesis claim and no deployability verdict.
- **Factor attribution** is secondary only and waits for a qualified benchmark series; it is not part of F.

Fixture proof (all values SYNTHETIC_FIXTURE, from fixed arithmetic formulas — not strategy outcomes): descriptive stats cross-checked against the stdlib `statistics` module at n = 50 (mean R 0.1722, t 2.912) and n = 100 (mean R 0.1735, t 4.169); `t_ppf(0.975, 49)` reproduces the known 2.0096; the bootstrap on the synthetic 300-session series returns CI [−0.0303, +0.0883] with one-sided p = 0.1700 (the machinery reports a non-significant synthetic series as non-significant); the Holm implementation reproduces a hand-computed example and is monotone over the registered family. **31/31 checks pass; the full fixture computation run twice is byte-identical** (result digest `269ba6e9bb720c4d439d1a5c20a1bc1fb2ffb93d8c565ce0089f9b750fcc0e35`).

## 4. Matrix delta (updated matrix in the package)

| Field | Was (-24) | Now | Provenance |
|---|---|---|---|
| 4.2 Walk-forward fold calendar | PROSE_ONLY | **PASS** | Mechanics frozen in executable bytes + fixture-proven (-25); exact dates pending qualified timestamps by design (verdict string carries this) |
| 4.5 No-selection-on-OOS rule | PROSE_ONLY | **PASS** | Operational form frozen in preregistration §2 (-25): prohibitions, family-ledger logging, fail-closed breach behavior, one-time holdout opening gate |

All other 25 fields unchanged from -24. **New totals: 27 PASS / 0 PROSE_ONLY / 0 MISSING / 0 CONFLICT.**

## 5. Scope confirmation

No market/OHLC data was fetched, read, or supplied; no holdout contents were accessed in any form; no performance or backtest was computed on real outcomes (fixtures are synthetic formulas, labeled); no restored strategy module was imported or run; no vendor/helper/model/API call was made (the only network use was the read-only spec fetch and the delivery push); no installs, credentials, or credits; no strategy tuning; no live/ledger/production writes; no Issue #9 work; no prior frozen record was edited — this package supersedes by reference only. TD -20 remains UNUSED and untouched.
