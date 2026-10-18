# Preregistration Amendment v2 — Null-Calibrated Formal Edge Test

**Document:** `PREREGISTRATION_AMENDMENT_V2_20261018_26` (versioned, prospective)
**Task:** `QF-VALIDATION-INFERENCE-NULL-CALIBRATION-20261018-26 r1`
**Spec / review:** GitHub Issue #1 comment `6255324442` (-25 independent review: fold/governance PASS, inference HOLD)
**Date frozen:** 2026-10-18
**Status:** PROSPECTIVE. Written before any real outcomes exist. The corrected test defined here has only ever been executed on labeled synthetic fixtures. Inference readiness under this amendment is **NOT AUTHORIZED** — it takes effect for any claim only after independent review of the amended code, mathematics, and immutable fixtures.

## Supersession scope (narrow)

This amendment supersedes **only** the formal one-sided p-value definition inside §3 ("Primary uncertainty estimate") of `PREREGISTRATION_20261018_25` (SHA-256 `ccf1a988a93026a2032f5cb94f6c6d9e78705e5121ca049d60ec2a1272473c24`, commit `fc17041`). The -25 preregistration document and the -25 code are **not edited**; their bytes are preserved and verified byte-identical to `fc17041` in the -26 package. Everything else stands unchanged: §1 fold materializer, §2 no-selection-on-OOS governance, §3 descriptive statistics, the bootstrap percentile confidence interval, the six-hypothesis Holm family F, economic-gate primacy, and the n = 50 interim status.

## Failure memory — `BOOTSTRAP_P_NOT_NULL_CALIBRATED`

- **Immutable source:** commit `fc17041`, file `research_notes/validation_prereg_finalization_20261018_25/inference_layer.py` (SHA-256 `64e8ec1bec536e4b9bf040cbc467541b2102058b42e6b67f04d620a28ff91e17`), function `circular_block_bootstrap`, lines: `le_zero = sum(1 for m in means if m <= 0.0)`; `p_one = (1 + le_zero) / (reps + 1)` — where `means` are circular-block-bootstrap resamples of the **unmodified observed series**.
- **Defect:** those resamples are centered around the observed sample mean, not around the null boundary mean 0. The reported quantity is therefore a bootstrap sign probability / percentile-CI tail measure, not a calibrated null-distribution p-value for H0: mean ≤ 0. The -25 deterministic synthetic fixture and Holm example cannot establish type-I error calibration. **The -25 formal p-value (e.g., 0.16998300169983002 on the -25 shared synthetic fixture) must not be used for any validation, edge, or deployability claim.**
- **What was NOT defective:** the fold materializer and §2 governance (independently PASS), the descriptive statistics, and the uncentered percentile bootstrap CI *as a confidence interval*.
- **Repair:** this task (-26 r1), executed inside its single ≤25-minute offline window; measured elapsed and repair minutes are recorded in this package's `TEST_RESULTS.json` and memo `VALIDATION_INFERENCE_NULL_CALIBRATION_20261018_26.md`. One ≤5-minute repair allowance per spec; the package records whether it was used.

## Corrected formal test (frozen by this amendment)

**Hypothesis.** One-sided test of H0: mean ≤ 0 for the chronological series of daily portfolio returns, evaluated at the boundary mean = 0.

**Null distribution.** Let `x` be the observed series of length `n` with sample mean `x̄`. Form the demeaned series `x_i − x̄`, which imposes the null boundary while preserving the series' dependence shape. Draw **10,000** circular-block-bootstrap replications of the demeaned series with block length **20 sessions** (concatenated circular blocks truncated to exactly `n`, identical sampling mechanics to -25), using SplitMix64 with seed = first 8 bytes (big-endian) of **this amendment document's** SHA-256.

**Formal p-value (upper tail, plus-one correction):**

```
p = (1 + #{null replication means >= x̄}) / (10000 + 1)
```

**Structural guarantee.** For `x̄ ≤ 0` the null replications are centered at 0, so at least roughly half of them are ≥ `x̄` and `p > 0.05` always: the procedure cannot claim positive edge for a non-positive observed mean. The implementation additionally reports `edge_claim_possible = (x̄ > 0)`.

**Confidence interval (retained, relabeled).** The two-sided 95% percentile CI from circular block bootstrap resamples of the **observed** series is retained as a confidence interval only. Its tail mass at 0 is the defective -25 quantity and must never be reported as a p-value; code and documents must label the distinction.

**Multiplicity and primacy (unchanged).** The registered family F is exactly the six hypotheses of -25 §3 (`H_pooled`, `H_cohort_UX51`, `H_cohort_X2`, `H_grade_A`, `H_grade_B`, `H_grade_C`), formal only at the n = 100 readout, Holm step-down adjusted as a single family. Economic gates remain primary: no p-value, adjusted or not, can rescue a failed economic gate.

**Refusals (fail-closed).** The formal path refuses: a hypothesis set with any missing or extra member of F; any p-value that is NaN, infinite, or outside [0, 1]; an empty return series; a series shorter than one block (n < 20); any non-finite value in the series.

**Calibration honesty.** This amendment claims the standard null-centered bootstrap construction, verified on deterministic synthetic fixtures with known null / negative / strong-positive behavior, an independent reference recomputation of the null-centered tail, and an explicit numerical proof that the corrected p differs from the defective -25 quantity on the shared -25 fixture. It does **not** claim an exhaustive finite-sample Monte-Carlo type-I study; bootstrap calibration is asymptotic. If independent review judges finite-sample calibration unjustified, the correct verdict remains HOLD. Inference readiness is therefore proposed as **NOT AUTHORIZED** pending that review (see the -26 memo).
