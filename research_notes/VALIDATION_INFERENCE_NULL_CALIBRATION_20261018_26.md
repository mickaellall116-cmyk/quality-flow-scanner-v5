# Validation Inference Null Calibration — -26 r1 Memo

**Task:** `QF-VALIDATION-INFERENCE-NULL-CALIBRATION-20261018-26 r1`
**Spec:** GitHub Issue #1 comment `6255324442` (-25 independent review: `QF_VALIDATION_25_FOLD_GOVERNANCE_ACCEPTED__INFERENCE_HOLD`)
**Date:** 2026-10-18
**Package:** `research_notes/validation_inference_null_calibration_20261018_26/`
**Elapsed:** ~17 minutes total of the ≤25-minute hard cap (spec fetch, build, and fixture proof through the first full pass ≈ 8 minutes; the balance is the repair re-run, packaging, and verified delivery). **Repair used:** one repair, ~1 minute (within the ≤5-minute allowance) — see Fixture proof.
**Offline:** synthetic fixtures only. No market data, no real outcomes, no holdout access, no vendor/helper/model/API calls (network only for the read-only public spec fetch and this delivery push), no credentials, no installs, no ledger/live writes, no strategy execution, no Issue #9 work, no prior frozen record edited. TD -20 remains UNUSED and untouched.

## Verdict

`INFERENCE_NULL_CALIBRATION_PROOF_READY_FOR_INDEPENDENT_REVIEW__READINESS_NOT_AUTHORIZED`

The defective -25 formal p-value is corrected prospectively by preregistration amendment; the corrected machinery is proven on deterministic synthetic fixtures. **No readiness is claimed by this package** — the inference field's disposition is the independent reviewer's call.

## What was wrong (failure memory)

Failure key **`BOOTSTRAP_P_NOT_NULL_CALIBRATED`**. Immutable source: commit `fc17041`, `research_notes/validation_prereg_finalization_20261018_25/inference_layer.py`, `circular_block_bootstrap`: resamples of the **unmodified observed series**, `p_one = (1 + #{rep means ≤ 0}) / (reps + 1)`. Those resamples are centered on the observed sample mean, not the null boundary 0, so the quantity is a bootstrap sign probability (percentile-CI tail), not a calibrated null-distribution p-value. Preserved, not erased: the -25 bytes are untouched (verified byte-identical below) and the defective value is reproduced and reported alongside the corrected one.

## The correction (AMENDMENT v2, prospective)

`PREREGISTRATION_AMENDMENT_V2.md` supersedes **only** §3's formal p-value definition in `PREREGISTRATION_20261018_25`. It freezes:

- **Test:** one-sided H0: mean ≤ 0 at boundary 0, over the chronological daily-return series.
- **Null distribution:** circular block bootstrap (20-session blocks, 10,000 reps, SplitMix64, concatenated blocks truncated to n — sampling and summation identical to -25) of the **demeaned** series `x_i − x̄`.
- **p-value:** `p = (1 + #{null rep means ≥ observed mean}) / (10000 + 1)` (upper tail, plus-one).
- **Seed:** first 8 bytes (big-endian) of the amendment document's own SHA-256.
- **Retained, relabeled:** the uncentered percentile 95% CI is a confidence interval only; its tail mass at 0 is the defective quantity and must never be reported as a p-value.
- **Structural guarantee:** observed mean ≤ 0 ⇒ null reps centered at 0 ⇒ p > 0.05 always; the code also reports `edge_claim_possible = (x̄ > 0)`.
- **Unchanged:** descriptive statistics (DESCRIPTIVE_ONLY), the six-hypothesis Holm family F (formal only at n = 100), economic-gate primacy, §1 folds, §2 OOS governance.
- **Refusals (fail-closed):** family missing/extra hypothesis, NaN/infinite/out-of-[0,1] p-values, empty series, series shorter than one block (n < 20), non-finite series values — all raise named errors in `inference_layer_v2.py` and are exercised in the suite.

## Fixture proof (all SYNTHETIC_FIXTURE; suite run twice, byte-identical)

Suite: `test_inference_null_calibration.py` — **33/33 checks pass**, full computation run twice byte-identical, result digest `aa13d56473c50752eb842c5059e5daad8c69accabc1d4280d0536ddbd8817bd8` (`TEST_RESULTS.json`).

**Shared -25 fixture, -25 vs -26 (same series, same seed 14767771057543718562):**

| Quantity | Value |
|---|---|
| Observed mean (synthetic 300-session series) | 0.02849548645937816 |
| Uncentered percentile 95% CI (retained, identical in v2) | [−0.030297559344700745, 0.08825810765630226] |
| **-25 defective p** `(1+#{uncentered reps ≤ 0})/(B+1)` | **0.16998300169983002** |
| **-26 corrected p** `(1+#{null-centered reps ≥ x̄})/(B+1)` | **0.17738226177382263** |
| Independent reference recomputation of the corrected tail | 0.17738226177382263 (exact match) |

The v2 reproduction of the defective quantity equals the -25 output exactly, so the comparison isolates the definition change: on this near-null fixture the defective value *understates* p (0.1700 vs 0.1774) — it is anti-conservative in the direction that matters, because its resamples are centered on the positive observed mean rather than on 0. The explicit check `corrected_p_differs_from_defective` passes.

**Known-behavior scenarios (amendment seed):**

| Scenario | Observed mean | Corrected p | Expected behavior |
|---|---|---|---|
| Null (zero-mean construction) | −1.2e-18 | 0.5089491050894911 (reference recompute: exact match) | no edge claim; plausible null p ✓ |
| Negative | −0.05 | 0.9539046095390461, `edge_claim_possible = false` | p > 0.5, edge structurally impossible ✓ |
| Strong positive | +0.10 | 0.00039996000399960006 | power sanity: detected ✓ |

Also verified: descriptive statistics byte-identical to the -25 implementation at n = 50/100 and cross-checked against stdlib `statistics`; `t_ppf(0.975, 49) = 2.0096`; Holm hand example and the -25 family example reproduce exactly; all refusal cases raise their named errors.

**The one repair (~1 minute, disclosed):** the first suite run failed 2 of 33 checks on last-ulp float differences — v2's hand accumulation loop summed rep samples in a different rounding regime than CPython's compensated built-in `sum()` used by -25, flipping one boundary rep in the null scenario's reference comparison (p 0.5088491150884912 vs 0.5089491050894911, exactly one rep) and the shared fixture's CI upper bound in the last digit. Repair: v2's resampler now builds the sample list and uses built-in `sum()` exactly as -25 does. Re-run: 33/33, twice byte-identical. This is a summation-order parity fix only; no definition, fixture, or threshold changed.

## Static preservation check (spec item 3)

SHA-256 of the -25 package files in the working tree equals the `fc17041` git blobs exactly: `fold_materializer.py` `b58194b4…`, `inference_layer.py` `64e8ec1b…`, `PREREGISTRATION.md` `ccf1a988…` — fold-calendar and §2 OOS-governance bytes are unchanged, and the suite asserts these hashes on every run. `DIFF_VS_25.txt` in the package is the full unified diff of the inference module (-25 → v2).

## Updated inference-readiness proposal — NOT AUTHORIZED

Proposal to the reviewer (no claim made by this package): on acceptance of the amendment, mathematics, and fixtures, the inference definition becomes the frozen v2 form above and field disposition can move to PASS **for definition-readiness only**. Two honest limits stand regardless: (1) bootstrap calibration is asymptotic — the fixtures prove construction, known-behavior scenarios, and exact independent recomputation, not an exhaustive finite-sample Monte-Carlo type-I study; if the reviewer requires that study, the verdict should remain HOLD and it becomes a separately scoped task; (2) even a definition-ready inference layer evaluates nothing until a separately authorized qualified dataset and the forward-test readouts exist. Exact fold dates still await qualified SPY timestamps. No holdout, real outcomes, market data, or performance run is authorized by this package.
