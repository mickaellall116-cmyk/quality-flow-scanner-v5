
---

## 2026-10-26 — Preregistration v1.0.2 wording amendment submitted for final C1 acceptance

**C1 re-review received** (Issue #1 comment `6429562606`): the four
original C1 findings are **substantively closed** — the reviewer
recomputed the v1.0.1 manifest (17/17), independently reconstructed
the selection funnel and the 11-name output from the committed inputs,
and confirmed the provenance erratum and the honest B9/G3 OPEN state.
One narrow evidence-label correction was required before final C1
acceptance, plus Mike's O9 decision.

**v1.0.2 amendment committed** (`research_notes/prereg_v10_2_wording_20261026/`):
wording and labels only — no numeric output changed, no list changed,
no rule changed, no quantity computed, no network data calls, no
holdout access.

- The 2,549 candidates without a persisted S4 aggregate are no longer
  labeled `…fail_closed` or described as ineligible / "the same
  treatment" as a fetch failure. They are
  **`aggregate_not_persisted__not_re_evaluated`**: their aggregates
  were computed but not retained (2,539) or their original fetch
  failed (10) — evidence loss, not eligibility.
- The step-8 derivation is restated as what it defensibly is: a
  **residual list** — original proven top-12 minus the
  issuer-ineligible GOOG = a known residual top-11, **rank 12
  unknowable** — not a complete step-8 eligibility rerun. The output
  now records `derivation`, `rank_12: null`, and an UNKNOWN
  `rank_12_status`.
- Generator corrected to **v1.2.1** (sha `5a1e0745…`; labels and
  docstrings only, selection logic unchanged). Regenerated output sha
  `08b670c4…`; its `tier3_list` array is byte-identical to the v1.0.1
  output `fbb73446…`, and every numeric stage count is unchanged
  (verification record in the package).
- Fixture added (`test_rank12_fixture.py`) asserting the rank-12 slot
  remains explicitly empty: **10/10 PASS**.
- Checklist row B10 restated by addendum; all other rows stand
  (B9 OPEN; O1–O9 as recorded).

**Still open, unchanged:** final C1 acceptance (reviewer's
confirmation of this repair), **O9 — Mike's decision** on the Tier 3
12th slot (reviewer recommends accepting the 11-name Tier 3), A5, G5,
G7, O4 paired SDs (not computed), P5, per-tier pool counts, Stage B
feed/rights. Holdout sealed; production PAUSED; no tier is open.
