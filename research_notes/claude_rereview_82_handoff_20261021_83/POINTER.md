# POINTER — CLAUDE TARGETED RE-REVIEW EVIDENCE HANDOFF FOR PACKAGE -82 (task -83)

**Status: `HANDOFF_PUBLISHED__REVIEW_NOT_CONFIRMED`** — this pointer records that the evidence bundle was published to the private archive. It does NOT claim Claude has received or seen it; receipt and the PASS/HOLD review are confirmed only through the desk, later.

**Authority:** ChatGPT QF NEXT ACTION, Slack TS 1792627306.219339 (2026-10-21 20:01:46 ET): package -82 ACCEPTED FOR CLAUDE TARGETED RE-REVIEW — not as data qualification, not as a baseline GO. Claude's two HOLDs (data qualification; corrected-baseline readiness) stand.

## The bundle (private archive — raw evidence stays private)

- **Repo:** `mickaellall116-cmyk/qf-data-archive` (PRIVATE), commit `75673f8`
- **Path:** `captures/claude_rereview_82_handoff_20261021/` — ZIP + `BUNDLE_INVENTORY.json` + `capture_manifest.json` + `SHA256SUMS`
- **ZIP:** `claude_rereview_82_handoff_20261021_r1.zip` — 91,225 bytes, **SHA-256 `8f562381335e06adf5b60f91e1436e48fa6a6ec01ad3b9af90adc814e263ddd2`**, 16 entries
- **Contents:** `HANDOFF.md` + `BUNDLE_INVENTORY.json` at the root; the complete package -82 at `research_notes/claude_cp1_repair_20261021_82/` exactly as committed (byte-exact `git archive` extraction).
- **Package pins:** package commit `d2cca9c`; correction commit `43bb235` (extraction pin for every file). The -82 `REPAIR_PLAN.md` inside the ZIP is the plan of record (six dispositions, separate-GO list G1–G5).
- **Verification:** inventory hashes recomputed before handoff (15/15 files OK); after the archive push, a fresh re-fetch passed `sha256sum -c` 3/3 and the ZIP byte-compares identical to the assembled artifact.
- **Retrieval route (Mike):** clone/pull the private `qf-data-archive` repo and open `captures/claude_rereview_82_handoff_20261021/`; hand Claude the ZIP (its root `HANDOFF.md` poses the five questions with in-ZIP file paths and pins).

## The five questions posed to Claude (verbatim from HANDOFF.md)

**Q1 — UX51 designation vs the E3 PIT freeze.** Does the designation of UX51 as THE frozen corrected-baseline universe — survivor-curated, with selection provenance and survivorship limitations documented — stand as the baseline universe, given that the E3 PIT rule (decision-time `announced_at` vs retrospective exclusion) is not yet frozen? Answer PASS or HOLD, and if HOLD, state whether the blocker is the designation itself or the open E3 freeze.

**Q2 — R1–R5 session handling vs preregistered engine semantics.** Do draft rules R1–R5 — fills only at next-present-bar opens, hold counted in constructed bars, GAP_CROSSED flagging with disclosed subset counts, exclusion symmetry, no silent repair — preserve the preregistered engine semantics for positions crossing missing/excluded sessions? Answer PASS or HOLD, per rule or for the set, naming any rule that would change engine semantics.

**Q3 — TSLA C2 NOT_EVALUABLE completeness classification.** Is the corrected TSLA classification — "C2 NOT_EVALUABLE — VOLUME COMPLETENESS FAILURE" (166 zero-volume price-moving pre-split bars; the volume convention uniformly ×3 on the 668 evaluable pairs; the window remains DATA_UNQUALIFIED on completeness grounds; the original C2 verdict text preserved untouched) — correct, and is the independent completeness check (single-series COUNT/ANOMALY/STEP lanes, no C2 pairing logic; fixture-proven 14/14) an adequate independent check? Answer PASS or HOLD.

**Q4 — July-3 label correction (-56 memo).** Is the July-3 correction — the -56 memo's "candidate 2026-07-03 early-close fact = True" corrected BY REFERENCE to CLOSED/non-session (the -56 memo's bytes untouched, its equality result not impugned), with the missing -56 fact JSON marked UNVERIFIED (verified absent from all four -56 package JSONs) and NOT reconstructed — correct and sufficient? Answer PASS or HOLD.

**Q5 — Constructor duplicate merge (507 vs 406) and upstream validator sufficiency.** Given the fixture-proven finding that the pinned constructor does NOT reject duplicate timestamps — it silently merges them, deterministically double-counting volume (fixture bin volume 507 vs the correct 406) — is the upstream validator layer sufficient protection for a corrected baseline run, or is a constructor-level fail-closed duplicate guard (H3b, a pinned-chain change requiring full route re-proof) required first? Answer PASS (validator sufficient) or HOLD (guard required), with the basis.

## Files in this pointer package

- `POINTER.md` — this file (summary + retrieval route + questions; no raw evidence).
- `BUNDLE_INVENTORY.json` — the bundle inventory metadata (per file: bundle path, bytes, SHA-256, Git blob SHA, commit pin; 15 files).

Boundaries: no data qualification is claimed; no corrected-baseline run is authorized; R1–R5 and E3 remain unfrozen; no prior package or pin was modified.
