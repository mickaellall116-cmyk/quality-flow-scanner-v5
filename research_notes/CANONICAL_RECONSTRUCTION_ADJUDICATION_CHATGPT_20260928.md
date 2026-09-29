# ChatGPT Adjudication — Canonical Reconstruction Plan
**Date:** 2026-09-28  
**Plan:** `research_notes/CANONICAL_RECONSTRUCTION_PLAN_20260928.md` (commit `1da7a82`)  
**Relayed by:** Mike (ChatGPT's Issue #1 write was blocked by the safety layer)  
**Archived by:** Muse

## Verdict: MAYBE / DO NOT AUTHORIZE RECONSTRUCTION YET

The plan is directionally sound, but reconstruction must not start yet.

### Material risk identified
The plan's proposed expected-results oracle exposes the old portfolio outcomes — 374 accepted trades, the 622/744/2,387 rejection funnel, cost/year/concentration results — *before* the seven unresolved implementation ambiguities are frozen. Those historical values could unintentionally become optimization targets when choosing among ambiguous implementations.

### Required fix
Split validation into two layers:
1. **Pre-run structural/specification layer** — frozen first.
2. **Sealed post-run forensic layer** — contains historical portfolio outcomes; exposed only after layer 1 is frozen.

All seven ambiguities, numerical tolerances, provenance rules, and tests must be frozen before the sealed layer is exposed. Any mismatch afterward is a reconstruction *finding*, not permission to tweak toward the historical numbers. If historical Yahoo data has drifted, the result must be labeled **non-exact** rather than loosening tolerances afterward.

## Standing freezes reaffirmed
- V5.4 remains frozen.
- ERD remains lab-only.
- Reconstruction remains unapproved.

## Blockers before any build
1. Original-machine read-only recovery search (Mike's machine).
2. Freeze the seven portfolio ambiguities (Section 6 of plan).
3. Split the oracle into pre-run structural + sealed post-run forensic layers; freeze tolerances before unsealing.
4. Reconcile Claude's independent audit.
5. If the original trade ledger is unrecovered, add the narrow Phase-0 procedural amendment (no rule changes).
6. Mike + ChatGPT sign off on the frozen reconstruction spec.
