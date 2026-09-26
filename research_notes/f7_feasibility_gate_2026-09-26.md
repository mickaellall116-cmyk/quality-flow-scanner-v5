# F7 feasibility gate report — 2026-09-26

**Family:** FAM-UNIVERSE-FACTOR-MINING / F7. **Verdict: FEASIBILITY GATE PASS**
(infra only). No score computed, no return inspected, no vendor data accessed.
Lab-only; V5.4 frozen, ERD v0.1 lab-only, nothing merged, nothing published.

## What was implemented (ChatGPT REVIEW DECISION checklist, 2026-09-26)

1. **Rename:** `structurally_eligible_rows` → `structurally_valid_rows` in
   `research_notes/fundamental_data_intake_audit.py`. Verified zero remnants
   of the old name across all four F7 files. "Eligible" remains reserved for
   the frozen availability+latency decision-time rule.
2. **Synthetic adversarial controls** — new module
   `research_notes/fundamental_version_selection.py` (pure decision-clock
   version selection: strict `available_at + buffer < decision_at`, latest
   eligible wins, same-instant conflicts fail closed, grouping by permanent
   security_id, frozen completeness rule, corporate-action invariance) plus
   `research_notes/test_f7_adversarial_controls.py` with 22 tests:
   - equality boundary (available+buffer == decision → not eligible; 1s inside → eligible; available == decision at zero buffer → not eligible)
   - future delivery / lookahead (post-decision versions never selected)
   - late revisions (per-decision-time correct version; latest eligible, not latest overall)
   - permanent-ID/ticker reuse (same ticker, two security_ids → independent groups; missing key fails closed)
   - delisted names (selectable by security_id)
   - vendor-sequence conflicts (same instant + different values → SAME_TIME_CONFLICT, incl. timezone-equivalent instants; identical duplicates select fine)
   - coverage/missingness boundaries (all present → COMPUTABLE; one missing → UNKNOWN, never renormalized; 0.0 is a real value; NaN/"UNKNOWN"/empty → UNKNOWN)
   - ≤T corporate-action invariance (versions at or before T never rewritten; only strictly-after-T adjusted; unparseable inputs fail closed)
   - timestamp parsing (rejects dates, naive, offsetless, non-strings)
3. **Environment freeze:** `research_notes/f7_env_freeze_2026-09-26.md` —
   Python 3.12.3, Linux x86_64, system zoneinfo (NY 2026-01-15 → UTC−05:00
   check), NYSE 13:30/16:00 ET decision bars, canonical JSON serialization,
   frozen seeds (synthetic 20260926), SHA-256 file hashes below.
4. **One frozen primary formulation:**
   `research_notes/f7_primary_formulation_frozen_2026-09-26.md` — six
   components (30/20/15/15/10/10), frozen field IDs, denominator/lookback/
   currency/corporate-action rules, UNKNOWN-on-missing (no renormalization),
   cross-sectional z→0–100 map, 131-name PIT cohort with the 14 masked names
   excluded from construction, coverage gate (≥80%), full evaluation order,
   numeric PASS (≥+0.15R net, ≥100 untouched-holdout trades, survives
   falsification) / MAYBE / FAIL. Written only — never evaluated.
5. **Multiple-testing history retained:** FACTOR_MENU.md F7 prereg (2026-09-24)
   + research_mandate.md family ledger (FAM-UNIVERSE-FACTOR-MINING closed) +
   the 2026-09-26 proposal + this frozen formulation, all cross-referenced in
   the formulation spec §5. No new family ID minted.

## Test results

- `test_fundamental_data_intake_audit.py`: 4/4 pass
- `test_f7_adversarial_controls.py`: 22/22 pass
- One genuine defect found and fixed during implementation: `completeness({})`
  returned COMPUTABLE for zero supplied components; the frozen rule now returns
  UNKNOWN (nothing computable).

## Frozen file hashes (SHA-256, at gate time)

- `fundamental_data_intake_audit.py`: 2b2da116815c2a2938a60d1c239e0ad86dd4e9fc86a0c725adc6edd0c54358f6
- `fundamental_version_selection.py`: e787e06343119400495d58f43840e5e91498ffa50971d074cbcc423a1136d57e
- `test_fundamental_data_intake_audit.py`: aa4a5e31285715ba083d235f1f440bf8178be9acdf84bd3c8363a1ffd78304ae
- `test_f7_adversarial_controls.py`: b47eda8db96b43c83eed50377fde3474c861e6b179cbab0d724f425506498409

## Verdict

**FEASIBILITY GATE: PASS.** The pre-returns checklist is complete and
executable. F7 remains MAYBE/feasibility-only: blocked on a qualifying as-seen
feed, anchored manifest, framework implementation-audit PASS, untouched
confirmatory sample, and Claude's independent audit — until then UNTESTABLE,
not approximated. Next step belongs to the parent agent (publish + bridge
update); no returns are opened by this report.
