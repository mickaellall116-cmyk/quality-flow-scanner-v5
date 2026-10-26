# Preregistration v1.0 Package — README

Assembled 2026-10-26 by Muse (assembly lane) from Draft v0.3 (commit `b65696a`) and the 2026-10-26 decisions and prep packages. **Purpose: independent review (ChatGPT, checklist item C1).** This package is the freeze candidate; it is not the freeze (G5 is Mike's, after review), and **document acceptance is not authority to run — every tier opening still needs its own explicit GO from Mike (G7).** No performance test was run, no holdout data was accessed, and no vendor call was made in producing this package.

## Contents

| File | What it is |
|---|---|
| `PREREG_V10.md` | The v1.0 protocol document (SHA-256 `29a0477a13e52ff4467193f69df7ef107048a8801f64c61f43de28d40d2850c6`). v0.3 text with only the 2026-10-26 decisions and completed freeze work applied |
| `CHANGELOG_V10.md` | Evidence-linked change register, v0.3 → v1.0 (tags `[V01]`–`[V09]`) |
| `FREEZE_CHECKLIST_V10.md` | Finite freeze checklist: closed items with evidence; open items with owners; the v1.0 bootstrap seed |
| `P11_PINS_V10.json` | Immutable version pins, updated at assembly (pine_backtest pin resolved; v1.0 seed fixed; §9/Tier 3/P10/power/stage pins added) |
| `P10_AUDIT.md` | Data-rights / session / adjustment audit (P10 production) |
| `POWER_REPORT.md` | §6 outcome-blind power report (variance only) |
| `VERIFICATION_LOG.md` | Hash-verification log from the power/P10/P11 production lane |
| `S9_CONTAMINATION_AUDIT.md` | §9 audit document (outcome PARTLY CONTAMINATED, F-A2-1); full evidence files in `research_notes/s9_contamination_audit_20261026/` (commit `f7b37cc`) |
| `TIER3_RULE_FROZEN.md` | Tier 3 mechanical selection rule, frozen v1.0 |
| `REPRODUCIBILITY_RECORD.md` | Tier 3 generation reproducibility record (verdict: REPRODUCIBLE) |
| `tier3_list.json` | The frozen 12-name Tier 3 list |
| `generate_tier3_list.py` | Tier 3 generation script, v1.1 (hash `0b39e1d4…`) |
| `stage_packages/` | Stage A / Stage B execution packages + shared preconditions checklist — included **by reference**; their hashes are in `SHA256_MANIFEST.txt` and `P11_PINS_V10.json`. Under the §9 Partly outcome, the Stage A package's Partly branch governs (verdict legs Tier-3-only) |
| `bridge_record_20261026.md` | The bridge record entry for these decisions and this assembly (also appended to `research_notes/bridge_thread.md`) |
| `SHA256_MANIFEST.txt` | SHA-256 for every file in this package (except the manifest itself) |

## Open items (summary; owners in `FREEZE_CHECKLIST_V10.md`)

ChatGPT independent review (C1) · Mike's signed freeze (G5) · Mike's A5 attestation · per-tier G7 GOs (none given) · Stage B feed qualification + ongoing-collection rights basis · freeze-procedure steps: 7A paired SDs, P5 per-fill config hash, per-tier §5 pool counts.
