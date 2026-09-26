# Decision-Time Availability Audit — Amendment 3

Status: FROZEN GOVERNANCE / FAILURE-MODE CONTROL
Date: 2026-09-25
Builds on Amendments 1 and 2.
Purpose: tighten two residual researcher-discretion/leakage paths in Amendment 2 without overwriting prior frozen artifacts.

No V5.4, ERD v0.1, production logic, or killed-family change.

## 1. Supersede Amendment 2 §1 primary-statistic discretion

Amendment 2 allowed the candidate's preregistered primary portfolio metric to define M_obs. For this availability-specific diagnostic, that leaves unnecessary family-level discretion.

The program-wide missingness statistic is fixed as portfolio-level expectancy in R/trade at the canonical 50 bps round-trip cost assumption.

Construct:
- B_full = frozen baseline replay on the full PIT-eligible opportunity set using only baseline information.
- B_masked_actual = identical baseline replay, except the candidate external-data availability mask is applied before ranking/slot competition. No candidate feature value or candidate signal is supplied.

Define:
delta_actual = expectancy_R50(B_masked_actual) - expectancy_R50(B_full).

This tests whether *who has data* acts as a hidden selector.

Generate exactly 9,999 matched placebo masks. Each preserves, per decision:
- exact exclusion count;
- PIT eligible universe;
- preregistered PIT size/liquidity strata;
- PIT sector strata only where reliable PIT sector classification exists;
- all baseline ranking, slot, sector-cap, risk, execution and cost rules.

Matching variables, bucket boundaries and sparse-stratum fallback are frozen in the family manifest.

Deterministic seed:
seed = first_64_bits(SHA256("QF-MISSINGNESS-" + family_id + manifest_hash)).

For placebo b:
delta_b = expectancy_R50(B_masked_placebo_b) - expectancy_R50(B_full).

This is a one-sided diagnostic for beneficial selection by missingness:
- if delta_actual <= 0: PASS this diagnostic only;
- if delta_actual > 0, compute p = (1 + count(delta_b >= delta_actual)) / 10000;
- p <= 0.05: FAIL availability audit for confirmatory use;
- p > 0.05: PASS this diagnostic only.

PASS here is not evidence of alpha and does not override any other gate.

If 9,999 valid matched masks cannot be generated under the frozen design, status = REVIEW. The matching design may not be relaxed after seeing the failed run except by dated amendment, and the inspected result may not be used to choose a favorable replacement.

No alternate alpha, tail, metric, seed, permutation count or matching rule may be selected after results.

### T14 — missingness boundary
Use a deterministic fixture:
- delta_actual > 0 with exact p=0.05 -> FAIL;
- delta_actual > 0 with exact p=0.0501 -> PASS this diagnostic;
- delta_actual <= 0 -> PASS this diagnostic.
Expected: exact boundary behavior.

## 2. Supersede Amendment 2 §3 revision tie-break

Research-time ingestion_at is not accepted as proof of historical feed-delivery order.

For rows sharing the same permanent security ID, fact/event period and available_at:
- exact duplicate values/content may collapse deterministically while retaining source hashes;
- conflicting values with no documented vendor-native delivery sequence are marked AMBIGUOUS_CONFLICT;
- AMBIGUOUS_CONFLICT rows are unavailable for primary historical decisions until a later uniquely ordered eligible version exists;
- a vendor-native sequence/version field may order same-timestamp versions only when its semantics are documented as delivery order and that rule is frozen in the manifest.

No lexicographic vendor ID/hash ordering may decide which conflicting value was historically usable; identifiers are not temporal evidence.

### T2C — simultaneous revision conflict
Two conflicting values, same available_at, no documented vendor delivery sequence.
Expected: neither eligible; AMBIGUOUS_CONFLICT.

Two exact duplicates, same available_at.
Expected: collapse without eligibility change.

Two conflicts with documented vendor-native delivery sequence.
Expected: use only the version proven delivered last among versions otherwise eligible at decision_at.

## 3. Tighten corporate-action test interpretation

Amendment 2 T12 is retained, with this explicit implementation criterion:

Compute all price-derived historical features/decision inputs through time T on a dataset truncated at T. Then append a corporate action whose effective/available time is after T and recompute.

Expected: every feature/decision input at <=T is identical, except for a preregistered floating-point serialization tolerance. Any backward change caused solely by the future action is FAIL.

A conventional fully backward-adjusted chart series may be stored for display/research diagnostics, but it cannot drive confirmatory historical decision features if appending a future action changes prior inputs.

## 4. Uniform manifest provenance

Amendment 2 §2/T11/T13 remain in force. Clarification: the manifest must include the fixed Amendment 3 missingness rule verbatim/by version reference and the same-timestamp ambiguity policy.

Any change after the first performance artifact requires a dated manifest amendment and retains the original hash and family multiple-testing history.

## 5. REVIEW quarantine

Amendment 2 §6 remains unchanged: REVIEW is non-confirmatory and cannot advance a candidate. It must resolve to PASS or FAIL through a dated preregistered amendment/falsification test.

## 6. Current independent-audit gate

Do not call the framework READY merely because Amendments 2/3 exist.

Next required step: Claude independently re-audits the combined frozen framework (original + Amendments 1, 2, and 3), focusing on whether:
- AV-03/N-2 is now quantitatively closed without candidate metric discretion;
- N-3 provenance locking is closed by the unified manifest;
- same-timestamp conflicts fail closed;
- corporate-action future-invariance is sufficient;
- REVIEW cannot bypass confirmation;
- any new researcher degree of freedom was introduced.

Only after independent READY may the governance specification be called READY. Implementation still must pass its deterministic tests before any candidate receives an availability PASS.
