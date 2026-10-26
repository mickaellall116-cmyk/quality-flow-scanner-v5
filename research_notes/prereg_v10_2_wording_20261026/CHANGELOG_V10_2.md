# Change Register — Preregistration v1.0.1 → v1.0.2 (wording amendment)

Amendment package: `research_notes/prereg_v10_2_wording_20261026/`.
Trigger: C1 re-review of v1.0.1 — Issue #1 comment `6429562606`
(ChatGPT, 2026-10-26): the four original C1 findings substantively
closed; one narrow evidence-label correction required before final C1
acceptance. **Wording and labels only** — no numeric output changed,
no list changed, no rule changed, no quantity computed, no network
data calls made, no holdout access, no performance run.
`PREREG_V10.md` bytes unchanged.

| Tag | Change | Source | Evidence |
|---|---|---|---|
| W01 | Stage-count label renamed in generator + output: `s8_candidates_without_frozen_aggregate_fail_closed` → `s8_aggregate_not_persisted__not_re_evaluated` (value unchanged: 2549) | C1 re-review `6429562606` | `tier3_inputs/generate_tier3_list_v1_2.py` (v1.2.1) sha `5a1e0745…`; output sha `08b670c4…` |
| W02 | Step-8 derivation restated as a **residual list** (original proven top-12 minus issuer-ineligible GOOG = known residual top-11; rank 12 unknowable), explicitly **not** a complete step-8 eligibility rerun — in the generator docstring, a new output `derivation` field, and the corrected `INPUTS_AND_GAPS.md` Consequence section | C1 re-review `6429562606` | `AMENDMENT_V10_2.md` W-2/W-3 |
| W03 | Output records `rank_12: null` + `rank_12_status: UNKNOWN — explicitly empty slot`, and fixture `test_rank12_fixture.py` added asserting the slot stays empty, the corrected label is used, and the list is exactly the residual top-11 — **10/10 PASS** | C1 re-review `6429562606` | `tier3_inputs/test_rank12_fixture.py`; `VERIFICATION_V10_2.md` |
| W04 | Fetch-failure conflation removed everywhere in the operative artifacts: the 2,549 are evidence loss (2,539 computed-but-not-retained + 10 original fetch-failed-or-short), not ineligibility; "fail-closed" retained only for input-hash verification | C1 re-review `6429562606` | Corrected `generate_tier3_list_v1_2.py` + `INPUTS_AND_GAPS.md` in this package |
| W05 | Freeze checklist row B10 restated by addendum (generator v1.2.1, residual list, new output hash; list array byte-identical to `fbb73446…`); v1.0.1 prose supersessions tabulated (W-1…W-5) | C1 re-review `6429562606` | `FREEZE_CHECKLIST_V10_2_ADDENDUM.md`; `AMENDMENT_V10_2.md` |
