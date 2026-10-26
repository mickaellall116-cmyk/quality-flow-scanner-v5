# Change Register — Preregistration v1.0 → v1.0.1

Amendment package: `research_notes/prereg_v10_1_amendment_20261026/`.
Trigger: C1 independent review — **HOLD**, Issue #1 comment `6428626885`
(ChatGPT, 2026-10-26), four bounded findings against v1.0 commit
`4ffb8fb`. `PREREG_V10.md` bytes are unchanged; entries below either add
new package files or supersede named v1.0 statements by reference (full
table in `AMENDMENT_V10_1.md`). No strategy rule, threshold, δ, α, floor,
or cost value changed. No SDs or any other quantity were computed. No
network data calls were made.

| Tag | Change | Finding | Evidence |
|---|---|---|---|
| A01 | Tier 3 inputs committed: S1–S3 raw sources + `exclusion_universes.json` under `tier3_inputs/`, byte-identical to the archived originals (hashes match `REPRODUCIBILITY_RECORD.md`) | C1-1 | `tier3_inputs/INPUTS_AND_GAPS.md` inventory |
| A02 | S4 frozen as an aggregate table (`S4_FROZEN_AGGREGATES.csv`, 12 rows) built fail-closed from the captured run outputs by `build_s4_table.py`; completeness gap disclosed precisely (2,539 computed candidate aggregates never persisted; rank 13+ underivable offline) | C1-1 | `tier3_inputs/S4_FROZEN_AGGREGATES.csv` sha `d345fbab…`; `INPUTS_AND_GAPS.md` |
| A03 | Generator v1.2: local-input-only (no network/market-data imports), SHA-256-pins every input, aborts exit 2 with no output on missing/mismatched input (both failure modes exercised); step 8 reads the frozen S4 table, fail-closed for candidates with no frozen row | C1-1 | `generate_tier3_list_v1_2.py` sha `d67ded42…`; two runs byte-identical |
| A04 | Frozen issuer map built mechanically from the archived directories (`build_issuer_map.py` → `ISSUER_MAP.json`): 250 prior-study issuers covered (25 crypto symbols have no listed classes); exactly two multi-class issuers — Alphabet (GOOG/GOOGL), Berkshire Hathaway (BRK.A/BRK.B) | C1-2 | `ISSUER_MAP.json` sha `3bccdbf2…`; builder sha `b9ae9b36…` |
| A05 | Step 6b (issuer-level prior-study exclusion) added; list regenerated offline from frozen inputs only. Effect: **GOOG out** (sole step-6b removal in the funnel); **11 names** — BE, ACN, IREN, CRDO, TWLO, AAOI, MPWR, SPOT, BABA, COF, BLK; no rank-12 entrant exists in the frozen record → open item O9; universe 19 + 11 = 30 | C1-2 (+ C1-1 shortfall) | `tier3_list_v1_2.json` sha `fbb73446…` |
| A06 | Power wording reconciled honestly: checklist B9 **OPEN** (power report = partial planning grid for H-EXIT-1/3, paired SDs not on record; closes with O4); §15 G3 corrected to OPEN in its power limb; v1.0 "power report completed / both grades powered per endpoint" phrasings superseded. **No paired SDs computed** (the review authorized no computation) | C1-3 | `FREEZE_CHECKLIST_V10_1.md` B9; `AMENDMENT_V10_1.md` Finding 3 |
| A07 | Provenance erratum issued: the v1.0 "no vendor call was made" statements (PACKAGE_README.md; bridge_record_20261026.md / bridge thread) are false as applied to the package; corrected record states the Yahoo Finance daily-bar fetches for the 2,561 Tier 3 candidates on 2026-10-26, their scope and limits. No replacement calls made | C1-4 | `ERRATUM_PROVENANCE.md` |
| A08 | Reproducibility verdict qualified: v1.0's "REPRODUCIBLE" covered output repeatability over persisted artifacts during one live-feed episode; input→output reproducibility from committed inputs holds only as of this amendment, with the A02 shortfall | C1-1 | `AMENDMENT_V10_1.md` S-6 |
