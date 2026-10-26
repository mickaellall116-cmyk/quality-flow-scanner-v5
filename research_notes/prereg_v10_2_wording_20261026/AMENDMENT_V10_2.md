# Preregistration v1.0.2 — Wording Amendment (Evidence-Label Repair)

**Amends:** Preregistration v1.0 (`research_notes/prereg_v10_20261026/`,
commit `4ffb8fb`) as amended by v1.0.1
(`research_notes/prereg_v10_1_amendment_20261026/`, commit `247a1c7`).
**Trigger:** C1 re-review of v1.0.1 — GitHub Issue #1 comment
`6429562606` (ChatGPT, 2026-10-26). The re-review **closed the four
original C1 findings substantively** (manifest 17/17 recomputed; the
selection funnel and the 11-name output independently reconstructed
from the committed inputs) and required **one narrow evidence-label
correction** before final C1 acceptance, plus Mike's O9 decision.
**Nature of this amendment:** wording and labels only. No numeric
output changes, no list change, no rule change, no computation of any
new quantity, **no network data call of any kind**, no holdout access,
no performance run. `PREREG_V10.md` bytes are unchanged; the v1.0
bootstrap seed (`2999475941474119668`, contract `fc17041`) stands.

---

## The repair the review required

The re-review's objection, in its operative terms: the 2,549 candidates
lacking a persisted S4 aggregate were **not feed failures or
rule-ineligible symbols** — their aggregates were computed but not
retained — yet generator/result language
(`s8_candidates_without_frozen_aggregate_fail_closed`, and the claim
that this is "the same treatment" as a fetch failure) conflated
evidence loss with eligibility. The review requires: rename/restate
those 2,549 as `aggregate_not_persisted__not_re_evaluated`; describe
the v1.2 derivation as what it defensibly is —

> "original proven top-12 minus the issuer-ineligible GOOG = a known
> residual top-11, with rank 12 unknowable"

— a residual-list derivation rather than a complete step-8 eligibility
rerun; and add a fixture asserting the unknown rank-12 slot remains
empty. Numeric output and list do not change.

## Disposition — CLOSED (wording only)

1. **Generator corrected (v1.2 → v1.2.1).**
   `tier3_inputs/generate_tier3_list_v1_2.py` in this package
   (SHA-256 `5a1e0745…`) supersedes the v1.0.1 copy (`d67ded42…`):
   the stage-count key is renamed to
   `s8_aggregate_not_persisted__not_re_evaluated`; the docstring's
   step-8 paragraph is rewritten (no "ineligible", no "same treatment
   as a fetch failure"); the output records a `derivation` statement
   (residual list, not a step-8 rerun), `rank_12: null`, and a
   `rank_12_status` of UNKNOWN. Selection logic is byte-for-byte the
   same logic; only labels, docstrings, version strings, and the three
   added descriptive output fields changed. (The word "fail-closed"
   survives in exactly one place — the input-verification docstring,
   where it accurately describes aborting on a missing or
   hash-mismatched pinned input. It no longer describes any candidate.)
2. **Output regenerated offline; the list is unchanged.** Two
   consecutive v1.2.1 runs against the frozen inputs produced
   byte-identical output (SHA-256 `08b670c4…`). The container hash
   differs from the v1.0.1 output (`fbb73446…`) **only** because of the
   renamed stage key, the bumped version strings, and the added
   descriptive fields: the `tier3_list` array itself is byte-identical
   (canonical-array SHA-256 `6468dc73…` in both versions), every numeric
   stage count is identical, and `parameters` / `input_hashes` are
   identical. Verification record: `VERIFICATION_V10_2.md`.
3. **Fixture added and passing.** `tier3_inputs/test_rank12_fixture.py`
   asserts: exactly 11 entries with contiguous ranks 1..11 and no
   rank-12 entry; `rank_12` recorded as null with an UNKNOWN status;
   the corrected label present (= 2549) and the superseded label absent
   from the output; the residual-list derivation recorded; the 11
   symbols exactly BE, ACN, IREN, CRDO, TWLO, AAOI, MPWR, SPOT, BABA,
   COF, BLK. Result: **10/10 PASS** (`VERIFICATION_V10_2.md`).
4. **`INPUTS_AND_GAPS.md` corrected in full** (corrected copy in this
   package): the Consequence paragraph is rewritten per the review;
   the inventory carries generator v1.2.1 and the regenerated output
   hash; the 2,549 count is decomposed (2,539 computed-but-not-retained
   + 10 original fetch-failed-or-short; all 2,549
   `aggregate_not_persisted__not_re_evaluated`).

## v1.0.1 statements superseded by this amendment (wording only)

| # | v1.0.1 location | Superseded wording | Corrected restatement |
|---|---|---|---|
| W-1 | `tier3_inputs/generate_tier3_list_v1_2.py` (v1.2) docstring + stage key; output JSON stage key | `s8_candidates_without_frozen_aggregate_fail_closed`; "a candidate with no frozen row is ineligible (fail-closed, counted) — the same fail-closed treatment the frozen rule gives a symbol whose bars cannot be fetched" | `s8_aggregate_not_persisted__not_re_evaluated`; the 2,549 were computed but not retained (evidence loss) — not ineligible, not a fetch failure (generator v1.2.1, this package) |
| W-2 | `tier3_inputs/INPUTS_AND_GAPS.md` § Consequence | "Under generator v1.2, a candidate with no frozen aggregate row is ineligible (fail-closed — the same treatment rule v1.0 gives a symbol whose bars cannot be fetched)" | Residual-list derivation: proven top-12 minus issuer-ineligible GOOG = known residual top-11; rank 12 unknowable; the 2,549 are `aggregate_not_persisted__not_re_evaluated` (corrected copy, this package) |
| W-3 | `AMENDMENT_V10_1.md` Finding 2 disposition; `CHANGELOG_V10_1.md` A05; `bridge_record_20261026_v10_1.md` Finding 2; `README.md` (v1.0.1) | "Regenerated Tier 3 list (11 names)" / "list regenerated offline from frozen inputs only" (unqualified) | Steps 1–7 are a complete re-derivation from the frozen inputs; the step-8 output is a **residual list** (proven top-12 minus GOOG), **not** a complete step-8 eligibility rerun. The 11 names, order, and aggregates are unchanged |
| W-4 | `CHANGELOG_V10_1.md` A03 | "step 8 reads the frozen S4 table, fail-closed for candidates with no frozen row" | Step 8 reads the frozen S4 table; candidates with no frozen row are `aggregate_not_persisted__not_re_evaluated` and are not re-evaluated (generator v1.2.1) |
| W-5 | `FREEZE_CHECKLIST_V10_1.md` row B10 | "generator v1.2 sha `d67ded42…` (local-only, hash-pinned, fail-closed); regenerated list: 11 names, sha `fbb73446…`" | Generator **v1.2.1** sha `5a1e0745…` (local-only, hash-pinned, aborts on missing/mismatched input); **residual list: 11 names**, output sha `08b670c4…` with the `tier3_list` array byte-identical to `fbb73446…` (see `FREEZE_CHECKLIST_V10_2_ADDENDUM.md`) |

**Preserved unchanged:** A5 (Mike, outstanding), G5 (Mike's signed
freeze, after final C1 acceptance), G7 per-tier GOs (none given), O4
paired SDs (not computed — no computation was authorized or performed),
P5, per-tier §5 pool counts, Stage B feed-qualification verdict and
ongoing-collection rights basis, the holdout seal, and all PAUSE /
HOLD states. **O9 remains Mike's decision** (the re-review recommends
accepting the 11-name Tier 3; this amendment takes no position and
fills nothing). Nothing here authorizes a holdout opening, a
performance run, a strategy change, or a tier opening.
