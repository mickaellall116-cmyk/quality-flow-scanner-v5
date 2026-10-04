# RECOVERY PRE-RUN PACKAGE — Canonical 4H Recovery + Walk-Forward Stress Test
**Date:** 2026-10-04 | **Branch:** `recovery-4h-20261004` | **Authorization:** Mike, 2026-10-04
**Status:** PREREGISTRATION + FIXTURES ONLY. No corrected performance opened.
**Revision:** REV 2 — closes ChatGPT review 5985221338 (7 gaps)
**Next gate:** ChatGPT review of REV 2 before any performance run.

---

## Contents

| File | Phase | Description |
|------|-------|-------------|
| `spec/canonical_4h_constructor.md` | A | Exact bar boundaries, labeling/closed semantics, partial-session handling, execution timing, timezone conversions, DST invariance |
| `spec/call_site_map.md` | A | All 5 historical 4H construction paths; **rev 2 corrects Path 3 error** |
| `spec/cache_provenance_forensic.md` | A | **NEW (Gap 1):** forensic trace of actual v3 cache generator |
| `spec/cache_contamination_audit.md` | A | **NEW (Gap 2):** per-symbol off-grid audit, 45 files, trade impact |
| `fixtures/test_4h_fixtures.py` | A | DST/session/holiday/forming-bar/crypto fixtures |
| `fixtures/byte_identity_report.md` | A | Byte-identity proofs across paths; every delta documented |
| `spec/c1_rebuild_spec.md` | B | Complete frozen C1 stack; side-by-side delta format (to populate post-review) |
| `spec/walkforward_prereg_rev2.md` | C | **REV 2 (Gaps 4-7):** LIMITED data tier, continuous fold state, PIT regime labels, tightened adjudication |
| `spec/walkforward_prereg.md` | C | Rev 1 (superseded — retained for audit trail) |
| `spec/parameter_inventory.md` | D | Tunable parameter neighborhoods; one-at-a-time plan; combinatorial cap |
| `ADVERSARIAL_GAP_REVIEW.md` | — | **REV 2:** gap closure table + 4 new adversarial concerns (B1-B4) |
| `evidence/source_hashes.txt` | — | SHA-256 of 2 source files (rev 1) |
| `evidence/complete_manifest_rev2.json` | — | **NEW (Gap 3):** full hash/input manifest |
| `evidence/offgrid_audit_rev2.json` | — | **NEW (Gap 2):** machine-readable audit data |

## Hard constraints (frozen)

- Frozen V5.4 production semantics/state: UNTOUCHED.
- Sealed holdouts (4H UX51, 11-month): UNTOUCHED.
- 4 legacy affected open positions: pinned legacy evaluation path preserved.
- QF-R2-BRK-VOL-4H-001: HELD at PRE-RUN. Not touched by this package.
- No rescue tuning. No performance reads until ChatGPT reviews this package.

## Phase summary

- **A — Constructor proof:** session-anchored 4H designated canonical; spec +
  fixtures + byte-identity vs all historical paths; legacy preserved for forensics.
- **B — C1 rebuild spec:** full frozen stack documented; delta format defined;
  execution gated on review.
- **C — Walk-forward prereg:** ≥5 six-month OOS folds (expanding window);
  pooled OOS + bootstrap + regime slices; PASS/MAYBE/FAIL/STOP adjudication
  pre-registered; contamination controls specified.
- **D — Fragility inventory:** ~40 one-at-a-time variants max; surface only,
  no winner selection.

## STOP

Per the task: after this package is committed, STOP. Do not open corrected
performance. Await ChatGPT review.
