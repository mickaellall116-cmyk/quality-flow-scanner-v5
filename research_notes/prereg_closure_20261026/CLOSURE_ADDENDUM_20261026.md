# Closure Addendum — B1 and O9 (2026-10-26)

This addendum closes freeze-checklist items **B1** and **O9** in the
preregistration v1.0 record (`research_notes/prereg_v10_20261026/`, as amended
by `research_notes/prereg_v10_1_amendment_20261026/` and
`research_notes/prereg_v10_2_wording_20261026/`). It changes no rule, no
number, and no list. Citations are to GitHub Issue #1 of
`mickaellall116-cmyk/quality-flow-scanner-v5`.

## B1 — CLOSED

- **§9 contamination audit outcome: PARTLY CONTAMINATED** (limb F-A2-1 only),
  logged and accepted. The audit package stands at commit `f7b37cc`
  (`research_notes/s9_contamination_audit_20261026/`); ChatGPT independently
  accepted the classification after reviewing the committed package, full
  verdict on Issue #1.
- **A5 — SATISFIED.** Mike's personal no-exposure attestation is recorded at
  Issue #1 comment `6431596885`. The question put to him was:

  > "Before we froze the Quality Flow strategy, did you personally review
  > performance results specifically from the October 2023–September 2024
  > holdout period?"

  Mike's direct answer: **NO.**

  Scope of the attestation, stated precisely: it attests for Mike personally
  only. It does **not** overturn the §9 PARTLY CONTAMINATED classification —
  the Sep 24, 2026 canonical re-baseline spanning aggregate (F-A2-1) stands
  as recorded.
- **Operative readings unchanged:** B1 stands as REDUCED as amended by the
  §11 Partly branch — Tier 2 (the 19 clean holdout symbols) is supplementary
  with no PASS/FAIL standing; Stage A verdict-bearing legs run Tier-3-only.
  The holdout remains sealed.

## O9 — CLOSED

- **Decision recorded at Issue #1 comment `6430214449`.** Mike delegated the
  decision ("Do what u think best"); acting on that delegation, with both
  reviewers (Muse and ChatGPT) independently recommending the same outcome,
  the decision is: **APPROVE the 11-name Tier-3 residual list.**
- **Tier 3 final list (11 names):** BE, ACN, IREN, CRDO, TWLO, AAOI, MPWR,
  SPOT, BABA, COF, BLK. Prospective Stage-A universe: 19 + 11 = **30 names**,
  above the ≥20-symbol validity floor.
- The 2,549 candidates whose S4 aggregates were computed but not persisted
  are recorded as `aggregate_not_persisted__not_re_evaluated` — evidence
  loss, **not** ineligibility. Rank 12 is unknowable from the frozen record
  and remains empty. No fetch, re-rank, tune, or alteration was performed or
  is authorized by this closure; no fresh S4 capture was authorized.

## C1 — CLOSED (noted)

ChatGPT's independent review C1 of preregistration v1.0 (as amended through
v1.0.2, commit `4b45a3e`) is **CLOSED with a PASS** — Issue #1 comment
`6430481827`. The four original C1 findings and the final evidence-label
repair were independently verified (manifest hashes, selection funnel
reconstruction, rank-12 fixture).

## Remaining open gates (unchanged by this addendum)

- **G5** — Mike's signed freeze of preregistration v1.0 (follows C1 + A5;
  not yet given).
- **O4** — H-EXIT-1/3 paired SDs: not on record; the power report remains a
  partial planning grid for those endpoints. Computing them is **not
  authorized** by anything in this record.
- **P5** — per-fill configuration hash (freeze-procedure step).
- **Per-tier §5 pool counts** (freeze-procedure step, before any tier opens).
- **Stage B** — feed-qualification verdict (Twelve Data pilot, finalization
  Nov 2) **and** an ongoing-collection rights basis beyond Basic (separate
  decision; a successful pilot does not authorize ongoing collection).
- **Per-tier G7 GOs** — none given; every tier opening still requires its
  own GO.

Acceptance of this addendum is not authority to run anything.
