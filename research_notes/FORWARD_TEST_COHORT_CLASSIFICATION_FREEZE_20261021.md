# FORWARD-TEST COHORT CLASSIFICATION FREEZE — 2026-10-21

**Authority:** Mike's ruling, delivered in chat 2026-10-21 19:13 ET, verbatim:

> "COUNT for audit, EXCLUDE for validation. Preserve all three gap-window fills as actual executions, flag them as unauthorized post-pause entries, and exclude them from the authorized-entry performance cohort. Freeze the classification and evidence pins. No deletion, strategy restart, or new entries."

**Reconciliation basis:** research_notes/FORWARD_TEST_RECONCILIATION_20261021.md (commit 6af7632cec2b6fcd3d7bba6ca0bb8420c4de4617), all figures recomputed trade-by-trade from state.json `exit.blended_r`.

## The frozen classification

**AUDIT LEDGER (all actual executions, preserved — nothing deleted):**
24 closed trades, **+10.0547R** cumulative (per-trade blended R at 1R risk each; not compounded). Win rate 41.67%. This is the complete record of what the system actually did.

**VALIDATION COHORT (authorized entries only — the performance record for any validation use):**
21 closed trades, **+13.0547R** cumulative. This cohort EXCLUDES the unauthorized post-pause entries below.

**FLAGGED: UNAUTHORIZED POST-PAUSE ENTRIES** (filled during the enforcement-absence window, Oct 4–19, 2026, while the Oct 3 entries pause existed without mechanical enforcement; see the -36 audit verdict PAUSE_SCOPE_MISMATCH__GOVERNANCE_DEFECT and the -37 gate record):

| Symbol | Grade | Entry | Status at freeze | Blended R |
|---|---|---|---|---|
| GOOGL | B | (gap-window fill) | closed 2026-10-16, stop | −1.0000R |
| MELI | A | (gap-window fill) | closed 2026-10-16, stop | −1.0000R |
| RBRK | C | (gap-window fill) | closed 2026-10-16, stop | −1.0000R |
| SHOP | B | 171.45 | OPEN (open_full) at freeze | pending |

The three closed fills above are the entire arithmetic difference between the two ledgers (24/+10.0547R counted vs 21/+13.0547R validation). SHOP is the same class — a gap-window fill — still open at freeze; when it closes, its result joins the AUDIT ledger and is EXCLUDED from the validation cohort under this same frozen rule. No further ruling is needed for SHOP's accounting.

**PAUSE_CONTAMINATED (separate existing label, unchanged by this ruling):** MRNA (B, 217.27, open_runner, TP1 taken 2026-10-21) and TEAM (B, 208.11, open_runner, TP1 taken 2026-10-20) — signaled Fri Oct 16, filled Mon Oct 19 via the ordinary pending path ~4h before the -37 gate deployed; MSFT (B) — pending, never filled, blocked 53 cycles (679→731). MRNA/TEAM remain IN both ledgers above (they are not gap-window fills); their PAUSE_CONTAMINATED label is preserved for any future cohort decision, which would require a new ruling.

## Evidence pins at freeze (2026-10-21 ~19:14 ET, state runs=731, last_run 2026-10-21T22:50:08Z)

- v54_forward/state.json — sha256 663480593712b436a9fb7ebc7923d6ae1fcf1b975670e0440666a1becc3578ce
- v54_forward/forward_test.jsonl — sha256 53f5fb72b3edca56e5ec4b17d40bb490612ece16bb708f7aadfce48bec89f4a2
- forward_test/v54_status.json — sha256 f32eb5a4d6ef5a5c6a83db214b75ca34a85a85d248dddba829260477f22dc8cd (closed_trades 24, cumulative_r 10.0547 at pin time)
- forward_test/PAUSE_NEW_ENTRIES — sha256 3f4b7811a577cc989438edc568d40d739281f76bcfbb0d0f36b900b2ccaa3ea2 (present; RESUME_NEW_ENTRIES absent)
- Deployed harness — sha256 ce7c902ce182683c… (the -37 pin; package commit 97bb3a5)
- Reconciliation memo — commit 6af7632cec2b6fcd3d7bba6ca0bb8420c4de4617

Note: the ledger files keep moving after this freeze because SHOP/MRNA/TEAM remain under live exit management. The pins above fix the evidence AS OF the ruling; the frozen classification rules above govern how every later close is booked (audit: everything; validation: authorized entries only, gap-window fills excluded).

## What this ruling does NOT do

No deletion of any record. No strategy restart. No new entries — the -37 gate remains in force, entries remain PAUSED. No change to the V5.4 research verdict (closed FAIL for promotion, 2026-10-03). Any future prospective cohort remains a separate decision, gated per the reconciliation memo §4.
