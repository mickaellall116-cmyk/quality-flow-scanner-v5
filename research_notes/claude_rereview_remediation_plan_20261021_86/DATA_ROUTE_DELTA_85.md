# DATA-ROUTE DELTA — the qualified data plan of -85, incorporated BY PIN, as amended by Claude's findings
## Part of the -86 remediation plan. -85 is NOT rewritten; this file is its delta of record.

**Incorporated by pin:** `research_notes/
ux51_data_acquisition_plan_20261021_85/` at commit **ad9fda5**
(`ACQUISITION_PLAN.md`, `COVERAGE_ARITHMETIC.md`,
`SHA256_MANIFEST.txt`). The route verdict (Twelve Data,
single-basis, seam-aligned), the bar arithmetic (5,236 1h bars
per session-bound symbol; 751 sessions), the gate graph, the
execution shape, and the earliest-dataset estimate (≈ Nov 27 –
Dec 1, 2026, ESTIMATE) stand as written in -85 **except** as
amended below.

## Deltas

- **D-85-1 — Membership pin superseded.** -85 §1 cites the -77
  definition hash `d139d7bf…` for UX51. The membership pin of
  record is now the canonical hash computed in
  UNIVERSE_OPTIONS.md §1 (`b5d8877e…`, sorted-LF serialization)
  over the identical 51 symbols. No symbol changes; the pin's
  serialization is what changed.
- **D-85-2 — Symbol count and request math are now
  OPTION-DEPENDENT on Mike's F1 ruling (G6).** -85's figures
  assume Option A (51 names):
  - **Option A (UX51 intact):** unchanged — ≈132 expected /
    ≈264 worst case; ceiling 300 stands; the ≈42-request crypto
    estimate stands (ESTIMATE, manifest convention unpinned, as
    -85 states).
  - **Option B (44):** 88 firm + 2 usage ≈ **90 expected /
    ≈180 worst case**; crypto estimate deleted; ceiling to be
    re-derived (≈200) at capture authorization.
  - **Option C (131):** 262 firm + usage ≈ **264 expected /
    ≈528 worst case**; ceiling to be re-derived (≈550); plus a
    per-name coverage risk -85 does not carry (see
    UNIVERSE_OPTIONS.md §4C) — the capture gate must refuse on
    any unserved name rather than shrink the universe silently.
  No capture manifest may freeze before G6 is ruled.
- **D-85-3 — Constructor guard: -85's gate 5 hardens.** -85
  made H3b conditional ("if validator sufficiency is NOT
  accepted" at Claude's re-review). Claude's re-review returned
  constructor **HOLD** (Slack TS 1792628218.568909) — validator
  sufficiency was not accepted on the -82 evidence. The delta:
  guard-v2 adoption + route re-proof (F3) becomes a HARD
  predecessor to **construction/consumption** of captured bytes
  (i.e., to -85's qualification gate 8 and any baseline run),
  unless Claude's review of THIS plan lifts it. Precisely:
  capture EXECUTION (raw bytes → archive) is unaffected by this
  delta; no captured byte may be constructed into a 4H frame
  for qualification or baseline purposes until the guard
  disposition resolves. -85's gate ordering otherwise stands.
- **D-85-4 — E3 wording corrected by reference.** -85 §3 gate
  2's "E3 PIT freeze" is read per F6_ERRATUM_E3_DEFINITION.md
  E-4: E3 governs the capture's split-event timing basis only.
  It has no bearing on the universe designation, which is
  decided under G6 (UPIT axis).
- **D-85-5 — The gate-2 freeze package grows.** -85 gate 2
  freezes R1–R5 after Claude's re-review. Under F2, the freeze
  package additionally contains draft amendments A1–A4
  (engine-semantics declaration, indicator-window declaration,
  gap-crossed readout treatment with tripwire, invalidation /
  re-derivation protocol) and remains gated on the S2
  disposition landing first (F2 dependency).
- **D-85-6 — Qualification gate 8's completeness instrument.**
  Gate 8 cites the -82 checker (14/14). Under F4, once checker
  v2 is built and adopted via G4, gate 8's instrument is checker
  v2; until then the -82 checker is the floor and any
  TSLA-shaped window remains DATA_UNQUALIFIED on completeness
  grounds under either instrument.
- **D-85-7 — Calendar gate 1 sibling (Option A only).** If G6
  rules Option A, gate 1 (calendar adoption) gains a sibling
  deliverable: the crypto bar-construction specification
  (UNIVERSE_OPTIONS.md §4A). Options B and C need no such spec.

**Status: DELTA DOCUMENTED.** Incorporation and deltas take
effect on adoption of this package by adjudication; -85's bytes
are untouched.
