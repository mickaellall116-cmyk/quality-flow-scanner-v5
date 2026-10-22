# F6 — DEFINITION RECORD + ERRATUM: WHAT "E3" DENOTES
## (EXECUTED in this package — definition corrected of record; errata are by reference; no prior package is edited)

## The corrected definition

**E3 denotes split-event TIMING.** It originates as GATE-E3 (PIT
availability) in the -60 boundary-coverage contract
(`td_req_s2_boundary_coverage_contract_20261020_60/CONTRACT_MEMO.md`,
sha256 c42a6b1642bf8c98…): each split event carries an
`announced_at` / `as_of`; assembly must refuse an event whose
availability postdates the basis it would alter. The freeze
question E3 poses (the -84 producer core's switch, modes per the
standing adjudication record) is:

- **Mode A (decision-time):** a split event may affect a decision
  only if `announced_at` ≤ the instant of the earliest decision it
  affects.
- **Mode B (retrospective):** events are applied retrospectively
  for data-quality purposes and the affected basis is labeled
  non-tradable.

**E3 does NOT denote point-in-time universe selection.** Whether a
universe's membership is valid point-in-time for a historical
window (no hindsight selection, delisted names handled) is a
separate axis. It has no gate number in the -60 contract and no
frozen rule anywhere in the record. For future documents this
plan names that axis **UPIT (universe point-in-time)** so the two
questions can never again share a label. UPIT is a proposed label
of this plan, not an adopted term.

Claude's -82 re-review (Slack TS 1792628218.568909) caught the
conflation; this record corrects it.

## Erratum list — every place the conflated usage appears (by reference; originals untouched)

- **E-1 — CONFLATED.** `-82` item 1
  (`research_notes/claude_cp1_repair_20261021_82/
  01_UNIVERSE_DESIGNATION.md`, package d2cca9c) and the -82
  REPAIR_PLAN's adjudication framing: the UX51 designation's
  review path was tied to "the E3 PIT freeze", importing
  split-timing language into the universe-designation question.
  Correction: the designation stands or falls on provenance and
  Mike's ruling (see UNIVERSE_OPTIONS.md); the E3 freeze has NO
  bearing on it. The universe's point-in-time problem is UPIT,
  and it is adjudicated under F1, not E3.
- **E-2 — CONFLATED.** `-83` HANDOFF.md, question Q1
  (`qf-data-archive@75673f8`, ZIP sha256 8f562381…; scanner
  pointer e3d3e0e): posed to Claude as "UX51 designation vs the
  E3 PIT freeze… given that the E3 PIT rule (decision-time
  `announced_at` vs retrospective exclusion) is not yet frozen".
  The announced_at rule stated there is the correct E3 rule —
  for split events. Applied to the universe designation it is
  the conflation, and it was Claude's re-review of that very
  handoff that identified it. Correction as E-1.
- **E-3 — CORRECT USAGE (verified; no erratum).** `-84`
  `SPEC_SPLIT_PRODUCER.md` (package f7725bf): the producer's E3
  switch refuses when unset and implements modes A/B over
  `announced_at`. That IS E3 as defined here. Listed so the
  audit trail shows the usage was checked, not assumed.
- **E-4 — PARTIALLY CONFLATED (language correct, scope
  ambiguous).** `-85` `ACQUISITION_PLAN.md` §3 gate 2 (commit
  ad9fda5): "E3 PIT freeze (A: decision-time `announced_at`
  rule, vs B: retrospective exclusion labeled non-tradable)". The
  rule stated is the correct split-timing rule; its placement as
  a baseline-readiness freeze in the same gate as the R1–R5
  freeze, downstream of the universe designation, perpetuated
  the reading that E3 adjudicates the universe. Correction:
  read -85's E3 strictly as governing the capture's split-event
  basis (which events the dataset's S2 treatment may use, and
  when) — nothing about universe membership.
- **Origin check.** The -60 contract itself and the -62 audit
  use E3 correctly (split-event PIT availability). The conflation
  entered at the -82/-83/-85 reporting layer, not at the source.

## Standing-language consequence

Any standing instruction or desk shorthand that reads "E3 PIT
freeze" as a universe question (including the framing under
which the -82 Q1 adjudication was requested) is superseded by
this record: **E3 = split-event timing freeze (Mike, after
adjudication); UPIT = the universe point-in-time question,
decided under F1 by Mike's universe ruling.** The two freezes
are independent and neither implies the other.

**Status: EXECUTED (documentation).** Owner: Muse. No separate
GO is required for a definition correction of record, and none
was taken.
