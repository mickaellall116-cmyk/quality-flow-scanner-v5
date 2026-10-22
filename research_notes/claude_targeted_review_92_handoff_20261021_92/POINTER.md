# POINTER — CLAUDE TARGETED REVIEW EVIDENCE HANDOFF -92 (task -92)

**Status: `HANDOFF_PUBLISHED__REVIEW_NOT_CONFIRMED`** — this pointer records that the evidence bundle was published to the private archive. It does NOT claim Claude has received or seen it; receipt and the PASS/HOLD review are confirmed only through the desk, later.

**Authority:** ChatGPT dispatch, Slack TS 1792640832.841789 (2026-10-21 23:47 ET): assemble a minimal immutable targeted-review handoff for CH-1, R1–R5, guard/checker repairs, credit scheme, and pilot readiness — assembly only. The dispatch follows ChatGPT's independent -91 review (Issue #1 comment 6332189179): candidate logic PASS; **adoption/capture remain HOLD**.

## The bundle (private archive — raw evidence stays private)

- **Repo:** `mickaellall116-cmyk/qf-data-archive` (PRIVATE), commit `6de1517774bb204c4a77fae5d7d4afe74dbd76e2`
- **Path:** `captures/claude_targeted_review_92_handoff_20261021/` — ZIP + `BUNDLE_INVENTORY.json` + `capture_manifest.json` + `SHA256SUMS`
- **ZIP:** `claude_targeted_review_92_handoff_20261021_r1.zip` — 226,494 bytes, **SHA-256 `d29fd2186255a8d3dc24a8d9a537e0744ed5f38ce3812a280164945e1baf670e`**, 73 entries
- **Contents:** `HANDOFF.md` + `BUNDLE_INVENTORY.json` at the root; byte-exact committed packages at their repo paths: -82 (`d2cca9c` + correction/extraction pin `43bb235`), -86 (`62aab52`), -87 three-gate packet (`186aa0a`), three-gate freeze (`a126ce5`), universe freeze Option A (`2705c02`), -90 CH-1 evidence (`b30ea93`), -88 capture manifest + provenance + R1–R5 freeze text (`6b0f5d0`), -89 guard/checker v2 (`959d61e`), -91 repair (`db9e0f3`). The CH-1 archived PDFs stay in `qf-data-archive` at `captures/ch1_core_hours_evidence_20261021_90/` (commits `f47823b` + `4f6d470`); their SHA256SUMS are reproduced in HANDOFF.md Q1.
- **Verification:** every payload file byte-compared against its Git blob at its pin during assembly; inventory hashes recomputed (72/72 listed entries OK); after the archive push, a fresh re-fetch passed `sha256sum -c` 3/3, the ZIP sha matched exactly, and the fetched ZIP re-verified against the inventory (73 entries, 0 mismatches).
- **Retrieval route (Mike):** clone/pull the private `qf-data-archive` repo and open `captures/claude_targeted_review_92_handoff_20261021/`; hand Claude the ZIP (its root `HANDOFF.md` poses the six review questions with in-ZIP file paths, pins, runnable verification, and the PASS/HOLD response template).

## The questions posed to Claude (summaries; full text in HANDOFF.md)

**Q1 — CH-1 retirement.** Does the in-era NYSE-issued evidence in -90 (RB-23-043 Apr/May 2023; RB-23-116 Nov 2, 2023, inside the 2023 segment; Jan-2023 Annual Guidance Letter — Core Trading Session 9:30 a.m.–4:00 p.m. ET under Rule 7.34) retire the CH-1 disclosed assumption carried by the adopted 751-session calendar? PASS (retire) or HOLD.

**Q2 — R1–R5 freeze text.** Is the -88 `R1R5_FREEZE_TEXT.md` (rule-exclusion set EMPTY per the S2 rejection; C1 no-max-hold; GAP_CROSSED + SPLIT_SPANNING subset accounting; GAP_DOMINATED tripwire 20%/25%; invalidation registry) ready to adopt verbatim as the session-handling freeze (G2-extended)? PASS or HOLD.

**Q3 — Guard v2 + -91 exact-index repair.** Is the -89 guard v2 candidate as repaired by -91 (15/15; sabotage 8/8 — permuted/shifted/dropped/off-grid indexes refused, constructor never invoked on refusal) adoption-ready for G3-v2, subject to minting unique successor version IDs/pins and the full route re-proof? PASS or HOLD.

**Q4 — Checker v2 + -91 session-table repair + the -82 fixture divergence.** (a) Is checker v2 as repaired by -91 (38/38; repair suite 11/11 — fully-missing first/middle/last sessions now COMPLETENESS_FAIL via the required session table) adoption-ready for G4? (b) Does the disclosed -82-fixture divergence (the byte-unchanged -82 v1 floor suite reads 10/14 under v2 because the -82 fixture builder embeds a second undeclared 3:1-shaped step at 2024-06-13, caught by v2's STEP-ALL lane; FI-A…FI-E reproduce the -82 intents on a corrected builder) change any -82 conclusion? PASS or HOLD on each part.

**Q5 — BLOCK-BRACKET-10 credit scheme + corrected totals.** Is the -91 accounting scheme (per-leg credit_delta abolished; sequential blocks of ≤10 attempts bracketed by chained /api_usage reads; exact reconciliation Δu = attempts + 1 or halt) auditable, and is the proposed 300 ceiling sound against the corrected totals (program 146 expected / 289 worst; pilot 19 / 37; margin 11)? PASS or HOLD on each part.

**Q6 — Pilot readiness.** Is the -88 pilot (16 legs: 5 session-bound symbols full-span + BTC-USD's 6 chunks), as amended by -91 accounting (19 expected / 37 worst), ready to be put to Mike for his capture GO — specification, accounting, provenance, and stop rules complete — or is a predecessor still missing? PASS or HOLD. A PASS certifies readiness for the decision; it does not authorize the pilot.

## Files in this pointer package

- `POINTER.md` — this file (summary + retrieval route + questions; no raw evidence).
- `BUNDLE_INVENTORY.json` — the bundle inventory metadata (per file: bundle path, bytes, SHA-256, Git blob SHA, commit pin; 72 listed entries).

Boundaries: assembly only — no package was created or edited beyond byte-exact extraction; all adoptions and the capture remain HOLD; no performance run, shadow activation, holdout access, vendor call, or trading action is requested or implied.
