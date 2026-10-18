# Validation Preregistration — Fold Materializer, OOS Governance, Inference Layer

**Document:** `PREREGISTRATION_20261018_25` (pinned; supersedes by reference only — no prior frozen record is edited)
**Task:** `QF-VALIDATION-PREREG-FINALIZATION-20261018-25 r1`
**Spec:** GitHub Issue #1 comment `6254836836` (-24 review PASS, dispatching -25)
**Date frozen:** 2026-10-18
**Status:** FROZEN BEFORE ANY QUALIFIED DATA PULL. No market/OHLC data, no holdout contents, and no real strategy outcomes were accessed, supplied, or computed in the making of this preregistration. All fixtures in its test suite are synthetic and labeled as such.

This document freezes three things: (§1) the timestamp-only walk-forward fold materializer (matrix field 4.2 mechanics), (§2) the operational no-selection-on-OOS rule (matrix field 4.5, enforceable form), and (§3) the inference layer for forward-test readouts (QuantFinanceToGo A1, strengthened form as adjudicated in comment `6254836836`). Exact fold dates do not exist yet: they materialize deterministically when §1 is run on qualified SPY session timestamps at a separately authorized data pull, and must be committed before any OHLC/outcome/performance field is supplied to any computation.

---

## §1 Fold-calendar materializer (freezes field 4.2 mechanics)

**Frozen constants:**

- `HOLDOUT_WINDOW = 2023-10-19 … 2024-09-15` (sealed; re-pinned by governance record in -24). Sessions in this window are excluded from development and must never be supplied to the materializer; supplying one is a hard error (`HOLDOUT_TOUCH`), not a silent skip.
- `DEV_START = 2024-09-16`. The development calendar consists of qualified SPY regular-session dates beginning 2024-09-16. Any earlier date is a hard error (`PRE_DEV_DATE`).
- `BAR_GRID = {09:30, 13:30}` America/New_York local times — exactly two bars per session. A session missing a grid bar, or carrying any other bar time, is a hard error (`BAD_GRID`).
- `MIN_TRAIN_SESSIONS = 252` (expanding training window minimum).
- `OOS_BLOCK_SESSIONS = 63`; OOS blocks are fixed, non-overlapping, and stepped by 63 sessions. Fold *k* (1-based): train = sessions `[0, 252 + 63·(k−1))`, OOS = the next 63 sessions. A final partial block shorter than 63 sessions is **dropped**, never evaluated.
- No `pandas_market_calendars` dependency. Pure standard library.

**Input contract (timestamp-only):** the materializer accepts ONLY a list of bar timestamps (`YYYY-MM-DDTHH:MM`, America/New_York local) plus an optional declared-holiday date set. It has no parameter, field, or code path that accepts a price, volume, outcome, or performance value. Its output is produced — and must be committed — **before** any OHLC/outcome/performance field is supplied to any downstream computation.

**Fail-closed validation (any violation aborts with a named error; no partial output):**

- malformed timestamp → `MALFORMED_TIMESTAMP`
- duplicate timestamp → `DUPLICATE_TIMESTAMP`
- non-strictly-increasing sequence → `NON_MONOTONIC`
- bar time outside the grid, or a session with other than exactly the two grid bars → `BAD_GRID`
- a session date on a Saturday/Sunday → `BAD_GRID`
- a missing Mon–Fri session date not present in the declared-holiday set → `UNRESOLVED_GAP`
- any session inside the sealed holdout window → `HOLDOUT_TOUCH`
- any session before `DEV_START` → `PRE_DEV_DATE`
- fewer than 252 + 63 sessions → `INSUFFICIENT_SESSIONS`

**Output (canonical JSON, deterministic):** `input_timestamp_digest` = SHA-256 of the newline-joined input timestamps; `calendar_digest` = SHA-256 of the newline-joined session dates; per fold: `fold`, `train_start`, `train_end`, `train_sessions`, `oos_start`, `oos_end`, `oos_sessions`. Identical input ⇒ byte-identical output.

## §2 Operational no-selection-on-OOS rule (freezes field 4.5)

This is the enforceable form of the governance rule previously carried as prose (prereg rev2 §§3/9). It is stated as checkable mechanics.

**Prohibited.** After any OOS block or the sealed holdout has been evaluated for a research family, its results may not alter, select, filter, or motivate changes to any of: entries, exits, ranking, thresholds, universe, risk parameters, costs, fold definitions, or gates — for that family. "Motivate" includes indirect selection: choosing which variant to report, which fold to emphasize, or whether to continue a line of work, based on OOS outcomes.

**Family ledger (logging).** Every attempted variant in a research family is appended to the family's variant ledger with: timestamp, variant identifier, a one-line description of what changed, the information class that motivated it (`TRAIN_ONLY`, `PRIOR_THEORY`, or `OOS_INFORMED`), and its disposition. Ledger entries are append-only. **No attempted variant is ever erased, including failures.** A variant whose motivating information class is `OOS_INFORMED` is, by definition, a breach (below), never a normal ledger entry.

**Breach behavior (fail-closed).** If any change to a frozen dimension is made after OOS exposure and is motivated by OOS information: (1) the change creates a **new research family** with a new identifier; (2) the exposed OOS slice is **permanently retired from confirmation use** for both the old and the new family — it may be cited only as development/contaminated evidence, never as confirmation; (3) the breach, its motivating observation, and the retirement are recorded in the family ledger and in a memo before any further computation; (4) no result computed under the breached configuration may be reported as validation evidence.

**Sealed historical holdout.** The sealed holdout (2023-10-19 … 2024-09-15) may be opened **at most once**, only after (a) independent checkpoint approval recorded on the bridge, and (b) a pinned qualified dataset and calendar exist. The opening is logged and irreversible: once opened, the window is development data forever and can never again serve as unseen confirmation.

## §3 Inference layer (freezes readout statistics; A1 strengthened)

**Primacy.** The pre-registered economic gates remain primary. No statistic in this section can rescue a failed economic gate: `p < 0.05` with a failed economic gate is still a FAIL.

**Readouts.** Readouts occur at n = 50 (interim) and n = 100 (formal verdict point) closed forward-test trades.

- **Descriptive (both readouts):** mean net-R per trade, sample standard deviation, simple t-statistic `mean / (sd / sqrt(n))`, and the two-sided 95% t confidence interval. These are **descriptive only**: trades cluster across time and symbols, so the simple t-statistic does not support a formal claim.
- **Primary uncertainty estimate (both readouts, formal claims only at n = 100):** circular block bootstrap over the chronological series of daily portfolio returns (one value per session, in session order): block length **20 sessions**, **10,000** deterministic replications, seed derived from this preregistration's SHA-256 (first 8 bytes of the document digest, big-endian). Report: bootstrap two-sided 95% percentile CI for the mean daily return, and a one-sided edge test of H0: mean ≤ 0 with `p = (1 + #{replication means ≤ 0}) / (10000 + 1)`.
- **Multiplicity (Holm).** The registered hypothesis family **F** contains exactly six formal one-sided edge hypotheses, evaluated only at the n = 100 readout:
  1. `H_pooled` — pooled mean net-R > 0 (tested via the §3 bootstrap on the pooled chronological daily-return series);
  2. `H_cohort_UX51` — cohort UX51 mean net-R > 0;
  3. `H_cohort_X2` — cohort FROZEN X2 mean net-R > 0;
  4. `H_grade_A` — grade A mean net-R > 0;
  5. `H_grade_B` — grade B mean net-R > 0;
  6. `H_grade_C` — grade C mean net-R > 0.
  Raw one-sided p-values for F are Holm step-down adjusted as a single family; a hypothesis is supported only if its Holm-adjusted p < 0.05 **and** the corresponding economic gate passed. Per-cohort/per-grade test series are the chronological daily portfolio returns restricted to that cohort/grade's trades' sessions, per the frozen ledger accounting.
- **n = 50 status.** Interim only. Descriptive statistics and the bootstrap CI may be reported; **no formal hypothesis claim, no deployability verdict**. The interim readout exists to detect operational breakage, not edge.
- **Factor attribution** is secondary only and waits for a qualified benchmark series; it is not part of F and supports no claim in this preregistration.

## §4 Fixture discipline

All code shipped with this preregistration is proven on synthetic fixtures only: a generated session calendar (business days from a fixed start, with a fixed declared-holiday set), synthetic per-trade R values and synthetic daily returns produced by fixed arithmetic formulas. Fixtures are labeled `SYNTHETIC_FIXTURE` wherever they appear. No fixture value is a strategy outcome and none may be cited as one.
