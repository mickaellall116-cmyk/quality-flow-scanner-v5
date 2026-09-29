# Stage B Report — rebuild 131-symbol universe.json (rev-6.1 §5B)

**Spec:** rev-6.1 (SHA-256 `53d3a5b8309fb3832e12bdf3ede24b55214919ec79f9c53f6096cddf7f371d9e`,
git blob `0f3705b8584d01ddfa2c7fc090a6a60dd5e17026`; re-verified before starting Stage B)
**Branch:** `research/canonical-stage-a` (on top of audited Stage-A commit `81db823`)
**Run:** 2026-09-29 ~18:30 ET
**Scope:** Stage B only — universe reconstruction as a §5B consistency check. No portfolio
simulation, no Layer-2 comparator, no production V5.4 changes. The sealed comparator and all
quarantined files stayed sealed.

## 1. Rule applied (UNIVERSE.md documented steps)

1. **ADDV ranking → top-120 cutoff**, from the Stage-A *recomputed* ranking
   (`canonical_stage_a/addv_ranking_recomputed.json`, 229 names).
2. **New-listing admissions**, from the Stage-A *recomputed* listing eval
   (`canonical_stage_a/new_listings_eval_recomputed.json`, 11 admitted / 4 rejected).
3. Rebuilt universe = 120 ranked names + 11 admitted listings = **131 identities**.

Pre-assertion (before rebuilding): the recomputed top-120 identities were asserted equal to the
whitelisted `addv_ranking_20230930.json` top-120 — **passed**. (Stage A had already proven the
full 229/229 identity order; Stage B re-asserts the top-120 subset used here.)

The admitted 11 identities were asserted exact against the frozen set
{ARM, BMNR, CRWV, DRAM, GEV, GLXY, NBIS, RDDT, SNDK, SPCX, TEM} — **passed**.
Zero overlap between the top-120 and the admitted listings (all 11 listed after the
2023-09-30 ranking cutoff), so the union is exactly 131.

Per-symbol provenance is recorded in the rebuilt artifact: `stage_a_recomputed_addv_ranking`
with rank for the 120; `stage_a_recomputed_new_listing_eval` with listing date, eligibility
date, and trail-20d ADDV for the 11.

## 2. Whitelisted input hashes (SHA-256, hashed before use)

| File | SHA-256 | Role |
|---|---|---|
| `canonical_baseline/addv_ranking_20230930.json` | `a1748bf63e2ca8e03092eb4afa72b0ea533aa3b9b5a626ffa6ec03f2b1ed0e0f` | pre-assertion target for top-120 |
| `canonical_baseline/universe.json` | `fa21ca55724993fab6709ab83fef7f2001e7d7672fa9e24f97beb24066893b16` | **check target** (never a reconstruction input) |
| `canonical_baseline/universe_overlay_14.json` | `ecb124d717918ecffe453a47a5d69b9836f01b93cecf1e76a43829d09ea2c07c` | **check target** (overlay consistency) |

Also re-hashed for the record (all match Stage-A values): `candidate_pool.json` `bbd057eb…`,
`addv_unrankable.json` `9c6457cc…`, `new_listings_eval.json` `1ed4f6d3…`,
`coverage_report.json` `fdb6e33a…`.

## 3. Rebuilt artifact

- `canonical_stage_b/universe_rebuilt.json` — 131 entries
- SHA-256: `25627b138df21575a58fbe1d40b2e42efde205d9f1f997d76e4ad9bcffb82a25`
- Implementation: `canonical_stage_b/build_universe.py` (own code)
- Machine-readable comparison: `canonical_stage_b/stage_b_comparison.json`

## 4. Identity comparison vs whitelisted universe.json — EXACT MATCH

| Check | Result |
|---|---|
| Rebuilt identities | 131 |
| Target identities | 131 |
| Set equality | **131/131 exact — no divergence** |
| In rebuilt but not target | none |
| In target but not rebuilt | none |

**Stage B verdict: PASS.** No identity divergence; nothing was tuned (there was nothing to tune —
the first rebuild matched).

## 5. Metadata comparison (all fields)

For every symbol in the intersection (all 131), the exact-value fields matched with **zero**
divergences: `reason` (`top120_addv_2023-09-30` ×120, `new_listing_passed_liquidity_gate` ×11),
`eligible_from` (2023-10-01 ×120; the 11 documented eligibility dates), `eligible_to`
(2026-09-30 ×131), `addv_rank_2023_09_30` (1–120, null for listings), `listing_date` (11).

Numeric fields:
- `addv_usd_per_day` (top-120): max relative deviation **4.5e-08** — floating-point noise
  between the independent recomputation and the documented values (same magnitude as the
  Stage-A ranking reproduction, 4.5e-08). Identities and ranks are exact.
- `trail20d_addv_usd_per_day_at_elig` (listings): max relative deviation **8.4e-04** — this
  is the target's 1-decimal-$M rounding (e.g. TEM: recomputed $34.93M vs target $34.90M).
  The recomputed unrounded values match the Stage-A documented values exactly.

Target-only metadata (present in `universe.json`, not derivable from Stage-A/frozen inputs,
documented here rather than reconstructed):
- `sector` — external classification, no frozen-input source.
- `delisted` — current-status flag (all `false` in the target).
- `eligible_from_method` — documentation string on the 11 listing entries
  ("listing_date + 30 trading days (~60 4H bars); backtest must enforce >=60 4H bars from listing").

These are informational fields, not reconstruction divergences.

## 6. Overlay check (universe_overlay_14.json)

- 14 identities, all hashed-verified before use.
- **8 members** (QQQ, SMCI, PLTR, ANET, DRAM, SPCX, NIO, AMD) — all 8 present in the rebuilt 131. ✓
- **6 outsiders** (SOFI, RKLB, ONDS, ASTX, BBAI, HOOD) — all 6 absent from the rebuilt 131. ✓
- The documented "6 non-universe outsiders" claim **holds** exactly. The outsiders' documented
  reasons are independently corroborated by the Stage-A ranking: SOFI ranked #130 (below the
  top-120 cutoff), HOOD #189, RKLB #207, BBAI #220, ONDS #227, ASTX unrankable (leveraged ETF).
  DRAM and SPCX appear as overlay members via the new-listing admission path.

## 7. Stage-A report correction (Mike's audit finding)

Mike found that `STAGE_A_REPORT.md` said "all 12 invariant checks" while `gate_a_verdict.json`
contains 11 named checks (the ASTX quote-type result is stored separately in the same JSON,
not as a named check). The report has been corrected to **11** at the Gate-A verdict line,
with a dated correction note inline. The commit `81db823` itself was not altered — the
correction is part of this Stage-B commit. Substance unchanged: all checks pass; this was a
reporting-count discrepancy, not a Gate-A failure.

## 8. Discrepancies

**None.** No identity divergence, no exact-field metadata divergence, overlay claim verified,
all whitelisted hashes matched. No material mismatch occurred, so no stop-and-document path
was needed.

## 9. Reproducibility

- `canonical_stage_b/build_universe.py` — rebuild + comparison (own code).
- `canonical_stage_b/universe_rebuilt.json` — 131-symbol rebuilt universe (SHA-256 above).
- `canonical_stage_b/stage_b_comparison.json` — identity/metadata/overlay comparison.

Stage B is complete. Stage C (4H cache construction per §11, 137 symbols) is NOT started —
it awaits authorization.
