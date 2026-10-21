# CLAUDE CP1 BOUNDED REPAIR PACKAGE — task -82

**Spec:** ChatGPT QF — CLAUDE CP1 FORENSIC ADJUDICATION / BOUNDED
REPAIR REQUEST (Slack TS 1792626235.632289, 2026-10-21 19:43:55 ET).
Claude independently verified the -78 ZIP integrity PASS (176/176
hashes; 155 Git blobs) and returned **data-qualification HOLD** and
**corrected-baseline readiness HOLD**; NO CP2, NO performance run.
Mike's standard for this deliverable (2026-10-21): a committed repair
package with test evidence — not a status memo.

**Scope honored:** offline only; documentation + isolated synthetic
fixtures with executed test evidence; no vendor calls, no spend, no
holdout access, no backtests/performance, no production changes, no
new entries, no shadow-lane activation (-80 remains inactive).
-78 (654dc0d; archive 518915a) and -79 (a08e08c) pins are referenced,
never modified; no prior package is edited — corrections are new
documents that supersede labels by reference.

## The six repairs + enumeration, with owners and order

Dependency order is the order below: 1 and 2 unblock the S2/universe
questions Claude's HOLD turns on; 3 must freeze before any qualified
frame exists; 4 and 6 are label governance (cheap, do early); 5 is
proven hardening; 7 is the review queue the other items feed.

| # | Item | Doc | Owner | Status | ETA (estimate) |
|---|---|---|---|---|---|
| 1 | Universe designation: **UX51** is the frozen corrected-baseline universe (provenance, not results); X2 = registered secondary cohort; 120-name/131 = undesignated research construction, future-family only | 01_UNIVERSE_DESIGNATION.md | Muse (memo); adoption: Mike | DOCUMENTED | Adoption: one adjudication cycle (~1 day, estimate) |
| 2 | Split-event provenance: **NO producer exists** (verified 3 ways); the required gate is -60's GATE-E1…E5; producer = new component | 02_SPLIT_EVENT_PROVENANCE.md | Muse (finding) | DOCUMENTED; producer REQUIRES_SEPARATE_GO | Producer design ~2–4 h + one review cycle once authorized (estimate) |
| 3 | Missing/excluded-session position handling: frozen-code implications [IMPLIED] + preregistration language R1–R5 [DRAFT] | 03_SESSION_HANDLING_PREREG_DRAFT.md | Muse (draft); adjudication ChatGPT+Claude; freeze Mike | DOCUMENTED (draft); freeze REQUIRES_SEPARATE_GO | Freeze: one adjudication cycle after items 2/4 land (estimate) |
| 4 | TSLA: completeness failure separated from split adjustment; "INCONSISTENT convention" label corrected (original preserved); independent single-series completeness check defined AND implemented | 04_TSLA_LABEL_CORRECTION.md; fixtures/tsla_completeness_check.py | Muse | Label DOCUMENTED; check FIXTURE_PROVEN (14/14) | Label adoption: Claude's targeted re-review (Claude's schedule; no estimate offered for another agent) |
| 5 | Constructor hardening: index-equality assertion, warnings-as-errors, duplicate-timestamp fixture — against a byte-copy of the pinned constructor (d47e8df1…) | 05_CONSTRUCTOR_HARDENING_SPEC.md; fixtures/test_constructor_hardening.py | Muse | FIXTURE_PROVEN (7/7) + FINDING (duplicates silently merged — see below); constructor guard (H3b) REQUIRES_SEPARATE_GO | H3b if authorized: ~1–2 h code + full route re-proof ~1 day (estimate) |
| 6 | -56 memo July-3 label corrected by reference (2026-07-03 = CLOSED/non-session); missing -56 fact JSON marked **UNVERIFIED**, not reconstructed; -61 instance flagged | 06_MEMO_LABEL_CORRECTION_56.md | Muse | DOCUMENTED | Effective on this package's adoption |
| 7 | Unreviewed-evidence inventory: Yahoo r2 (scoped review only), r2 observation closure + feed pin (unreviewed), -80 safety suite (unreviewed), -75 analyzer NVDA/AAPL paths (partial), SPOT8 receipts (scoped), sweep #4 + BOSWaves/SA-VWAP executions (unreviewed) | 07_UNREVIEWED_EVIDENCE_INVENTORY.md | Muse (inventory); reviews: ChatGPT/Claude | DOCUMENTED | Review scheduling is the reviewers'; the -78 bundle already feeds Claude's CP1 |

**Test evidence (executed in this task, offline, pinned env —
CPython 3.12.3 / pandas 2.2.3, `unshare -n`, repeat runs
identical):** item 4 suite 14/14 PASS; item 5 suite 7/7 PASS.
Full outputs: fixtures/TEST_EVIDENCE.md.

**FINDING carried by the evidence (not buried):** the pinned
constructor, called directly, silently MERGES duplicate 1H
timestamps (fixture bin volume 507 vs 406 — double-counted).
Deterministic, but duplicate safety is a validator-layer property
today; H3b proposes a constructor-level guard as a separate-GO change
to the pinned chain.

## What requires a separate GO (explicit list)

- **G1 — Split-event producer creation** (item 2): new component
  under its own adjudicated task; any vendor leg needs Mike's vendor
  authorization; S2 integration is a further decision after E1–E5.
- **G2 — Session-handling freeze** (item 3): Mike freezes R1–R5 (as
  amended by adjudication) as a -25 preregistration amendment.
- **G3 — Constructor duplicate guard** (item 5, H3b): modifies a
  pinned file → new pin + full route re-proof, Mike's GO.
- **G4 — Re-analysis of the -75 snapshots** under the item-4 check,
  and adoption of the corrected C2 label into future reporting:
  adjudication (ChatGPT/Claude); the snapshots are pinned evidence
  and are not re-opened by this package.
- **G5 — Universe change, if ever** (item 1): NOT requested and NOT
  recommended; under -25 §2 it would create a new research family.
- **Standing gates unchanged by this package:** calendar candidate
  adoption (8d659dde…, -81); probe R7 (eligible 2026-10-28T21:33Z) /
  R30 (2026-11-20T21:33Z) — Mike's GO each; shadow launch (-80) —
  adjudication + Mike's GO; E3 PIT freeze (A vs B) — still open and
  still required before any real-data validation.

## Shortest defensible path to Claude's targeted re-review

1. ChatGPT adjudicates this package (labels in items 4/6, draft in
   item 3, designation in item 1).
2. Claude's targeted re-review consumes: the designation (item 1),
   the corrected C2 label + the fixture-proven completeness check
   (item 4), and the corrected July-3 record (item 6) — all pinned in
   this package, all referencing -78 bytes without modifying them.
3. The two HOLDs Claude returned are NOT lifted by this package:
   data qualification still needs a qualified data route (0/51,
   -77) and the split-event producer gate (item 2); readiness still
   needs the E3 freeze and the item-3 freeze. This package removes
   the *documentation and labeling* blockers and proves the
   *fixture-level* repairs; it does not manufacture qualification.

## Disclosures

- ETAs are estimates, labeled as such; no other agent's schedule is
  estimated.
- One -56-related scope note: the -61 memo carries the same July-3
  label (its line 79); it is flagged in item 6, not corrected, as
  the spec scoped the correction to -56.
- The fixture constructor copy is included in this package
  (fixtures/construct_4h_fixture_copy.py) so the suite is runnable
  as committed; its SHA-256 equals the pin and the suite enforces
  that at runtime.
