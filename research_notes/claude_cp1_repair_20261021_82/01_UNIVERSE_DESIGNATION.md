# ITEM 1 — UNIVERSE DESIGNATION (frozen corrected-baseline universe)

**Designation: UX51.** The frozen corrected-baseline universe is the
51-symbol UX51 cohort. This designation rests on provenance — what the
record froze, when, and for what — not on any result. No outcome of
any run was consulted in making it (the C1 baseline FAILED its
promotion bar on this universe; designating the universe that produced
a failing result is the opposite of winner selection).

## Provenance chain (evidence-pinned)

1. **The corrected baseline ran on UX51.** The C1 corrected-baseline
   script records `"universe_window": "UX51 4H 2024-09-16 ->
   2026-09-14"` (`c1_corrected_baseline_20261003.py`, sha256
   4568823cb8fe645a…, in the CP1 evidence closure). The forensic
   question CP1 adjudicates — was the baseline's data defective — is
   a question about a UX51 run.
2. **The destroyed dataset D1 was a UX51 dataset.** The 52 surviving
   SHA-256 pins cover 51 UX51 symbol files + the benchmark (per the
   -77 readiness matrix, commit 22b6903). All coverage accounting in
   -77 is over UX51 (0/51 qualified).
3. **The frozen preregistration is written over the forward cohorts,
   with UX51 primary.** `PREREGISTRATION_20261018_25` (frozen
   2026-10-18, "FROZEN BEFORE ANY QUALIFIED DATA PULL", sha256
   ccf1a988a93026a2…) registers the Holm family F = {H_pooled,
   H_cohort_UX51, H_cohort_X2, H_grade_A/B/C}. The X2 cohort file
   itself states: "Cohort 1 (UX51, 51 symbols) is unchanged and
   remains the primary cohort" (`frozen_universe_x2.py`, sha256
   44b0d8ba5a7ea641…).
4. **UX51's own definition** is the `UNIVERSE_X` list in
   `pine_backtest.py` (51 symbols; run tag "UX51"), in the record
   since the baseline era and carried byte-identical in the CP1
   archival sources.

## Why not the other two candidates

- **X2 (199 symbols, FROZEN 2026-09-15)** is a forward-test
  acceleration cohort — day-1 addition to the *forward test*, tagged
  Forward-X2, containing crypto pairs and macro ETFs. It is a
  registered secondary cohort hypothesis (H_cohort_X2), not the
  corrected-baseline universe; the baseline, the cache, and the
  holdout accounting never ran on it.
- **The 120-name candidate** (canonical baseline universe: top-120 by
  trailing-63-day ADDV as of 2023-09-30, + 11 rule-admitted new
  listings = 131 symbols; `canonical_baseline/UNIVERSE.md`, sha256
  1df084af8e9924b1…, built 2026-09-24/25) is a point-in-time research
  construction whose own document states "Research only. Nothing
  frozen was touched." Critically, the -25 preregistration was frozen
  on 2026-10-18 — three weeks AFTER this universe existed — and did
  not adopt it. Designating it now, after C1's FAIL on UX51 is known,
  would be a retrospective universe change; under the preregistration's
  own §2 breach rules, a post-exposure universe change creates a NEW
  research family and retires the exposed slices from confirmation
  use. It remains available for exactly that: a future family, under
  a future preregistration — not as a relabeling of this one.

## Selection dates

- UX51: in force as the baseline/forward primary cohort on or before
  **2026-09-15** (forward-test day 1; the X2 freeze of that date
  references it as already-unchanged cohort 1). No earlier separate
  freeze instant for UX51 is pinned in the record — stated as a bound,
  not invented as a date.
- X2: **FROZEN 2026-09-15** (file docstring, byte-pinned above).
- 120-name candidate: constructed **2026-09-24/25** (UNIVERSE.md);
  never frozen into any preregistration.

## Delisted / survivorship limitations (stated, not repaired here)

- UX51 is a curated list of names that survived to the program's
  start. It contains no delisted names by construction, so any
  UX51 result carries survivorship bias of unknown size. The record
  shows the failure mode concretely in the adjacent cohorts: CYBR
  (acquired 2025) returns no data and is absent everywhere; SQ was
  dropped from X2 on rename (SQ→XYZ) — a survivorship-handling
  decision made for data availability, not by a frozen rule.
- The canonical 131 construction documents the same limit from the
  other side: its pool is "hindsight-influenced" (the union of the
  program's 2026 lists), its selection rule is PIT, and CYBR is
  documented as unrecoverable without a survivorship-inclusive vendor
  (Norgate/CRSP class). No universe in the record is
  survivorship-complete.
- Consequence for qualification: designating UX51 does not cure its
  survivorship limitation; it records that the corrected-baseline
  family's claims, if it ever qualifies, are claims about a
  survivor-curated 51 — which is what the frozen preregistration
  registered. A survivorship-inclusive universe is future-family work
  (see REPAIR_PLAN.md, separate-GO list).

**Status: DOCUMENTED.** Owner: Muse (this memo). Designation
authority: Mike (adoption of this memo as the governing designation,
on ChatGPT/Claude review). If the designation were changed instead,
that is a separate GO and a new research family — not a repair.
