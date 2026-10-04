# RECOVERY PRE-RUN PACKAGE — Canonical 4H Recovery + Walk-Forward Stress Test
**Date:** 2026-10-04 | **Branch:** `recovery-4h-20261004` | **Authorization:** Mike, 2026-10-04
**Status:** PREREGISTRATION + FIXTURES ONLY. No corrected performance opened.
**Next gate:** ChatGPT review of this package before any performance run.

---

## Contents

| File | Phase | Description |
|------|-------|-------------|
| `spec/canonical_4h_constructor.md` | A | Exact bar boundaries, labeling/closed semantics, partial-session handling, execution timing, timezone conversions, DST invariance |
| `spec/call_site_map.md` | A | All 5 historical 4H construction paths; which evidence family each produced |
| `fixtures/test_4h_fixtures.py` | A | DST/session/holiday/forming-bar/crypto fixtures |
| `fixtures/byte_identity_report.md` | A | Byte-identity proofs across paths; every delta documented |
| `spec/c1_rebuild_spec.md` | B | Complete frozen C1 stack; side-by-side delta format (to populate post-review) |
| `spec/walkforward_prereg.md` | C | Expanding-window folds, report spec, cost legs, bootstrap plan, adjudication criteria, contamination controls |
| `spec/parameter_inventory.md` | D | Tunable parameter neighborhoods; one-at-a-time plan; combinatorial cap |
| `ADVERSARIAL_GAP_REVIEW.md` | — | Honest adversarial review of this plan (protocol v1 requirement) |
| `evidence/source_hashes.txt` | — | SHA-256 of source files used |

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
