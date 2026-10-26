# Freeze Checklist — v1.0.2 Addendum (wording only)

This addendum amends `FREEZE_CHECKLIST_V10_1.md` (in
`research_notes/prereg_v10_1_amendment_20261026/`) in **row B10 only**,
per the C1 re-review (Issue #1 comment `6429562606`). All other rows —
including B9 **OPEN** (power report a partial planning grid for
H-EXIT-1/3; closes with O4), O1–O9, and section D — stand exactly as
written there. `PREREG_V10.md` bytes are unchanged, so the v1.0
bootstrap seed (`2999475941474119668`) stands. **Document acceptance is
not authority to run.**

## Row B10 — restated (supersedes the v1.0.1 B10 wording)

| # | Item | Evidence |
|---|---|---|
| B10 | Tier 3 rule + list (v0.3 item C5) — **amended by v1.0.1; wording-corrected by v1.0.2** | Rule sha `b4b993e8…` (unchanged). Inputs S1–S3 + exclusion committed; S4 frozen (`tier3_inputs/S4_FROZEN_AGGREGATES.csv` sha `d345fbab…`); issuer map sha `3bccdbf2…`; generator **v1.2.1** sha `5a1e0745…` (local-only, hash-pinned, aborts on missing/mismatched input; supersedes v1.2 `d67ded42…` — labels/docstrings only, selection logic unchanged); **residual list: 11 names** — BE, ACN, IREN, CRDO, TWLO, AAOI, MPWR, SPOT, BABA, COF, BLK — output sha `08b670c4…`, its `tier3_list` array byte-identical to the v1.2 output `fbb73446…`. Derivation: original proven top-12 minus GOOG (step 6b — issuer equivalent of UX51 GOOGL) = known residual top-11; **rank 12 UNKNOWN** (explicitly empty slot; fixture `test_rank12_fixture.py` 10/10 PASS); the 2,549 candidates without a persisted aggregate are `aggregate_not_persisted__not_re_evaluated` (evidence loss, not ineligibility). 12th slot: row O9 (Mike's decision; C1 re-review recommends accepting the 11). Reproducibility as qualified in `AMENDMENT_V10_1.md` S-6 and `AMENDMENT_V10_2.md` |

## Row O1 — status note (no wording change to the row itself)

C1 re-review (comment `6429562606`) **substantively closed the four
original findings** and required one evidence-label correction, which
this v1.0.2 amendment submits. Final C1 acceptance is pending the
reviewer's confirmation of this wording repair (and Mike's O9
decision, which the reviewer also names as a condition of closing C1).
