# F7 primary formulation — FROZEN 2026-09-26

**Status: FROZEN SPECIFICATION. No score has been computed, no return has
been inspected. This document may only change via a dated amendment written
before any performance read. Family: FAM-UNIVERSE-FACTOR-MINING / F7.
Lab-only sidecar; cannot change V5.4 BUY/EXIT, `rs_top2`, sizing, slots, heat,
alerts, or ERD v0.1.**

## 1. Components and weights (sum = 100; never renormalized)

| # | Component | Weight | Frozen field IDs |
|---|---|---|---|
| 1 | EPS revisions | 30 | `consensus_eps` revision: (mean_now − mean_90d_ago) / \|mean_90d_ago\|, PIT as-seen |
| 2 | Forward EPS growth | 20 | (PIT next-fiscal-period estimate − PIT comparable prior actual) / \|prior actual\| |
| 3 | Revenue growth | 15 | (PIT latest reported revenue − PIT same-quarter prior year) / \|prior year\| |
| 4 | Last earnings surprise | 15 | (non-GAAP actual − pre-release mean estimate) / \|pre-release mean\|, first known actual only |
| 5 | Margin change | 10 | Δ operating margin in percentage points, YoY same quarter |
| 6 | Price/volume pressure | 10 | 20-day return minus SPY, reported separately as memo (overlaps the technical selector) |

## 2. Frozen rules

- **Fiscal-period matching:** estimate and actual must share the vendor's fiscal-period ID; GAAP/adjusted policy follows the vendor's documented definition per field, frozen per field here: surprise uses the endpoint's `eps_actual` (documented non-GAAP) vs pre-release mean; growth components use adjusted figures where the vendor supplies both.
- **Denominators:** if \|denominator\| < 0.01 (currency units per share) or denominator ≤ 0 for growth, the component is UNKNOWN. No division by near-zero, no sign flips hidden.
- **Revision lookback:** 90 calendar days of as-seen consensus history; fewer than 3 as-seen snapshots in the window → component UNKNOWN.
- **Currency:** USD-reporting securities only in the primary formulation.
- **Corporate actions:** as-seen split-adjusted values per vendor policy; pre-action versions never rewritten (see `split_adjust` invariance control).
- **Missingness:** any of the six components missing/UNKNOWN → whole score UNKNOWN. Weights are never renormalized. A stored 0.0 is a real value.
- **Transformations:** each component cross-sectionally z-scored within the decision-date cohort, clipped at ±3, mapped to 0–100 via the frozen linear map (clip→ (z+3)/6×100). No sector/size controls in the primary formulation (diagnostics only).
- **Cohort:** canonical PIT 131-name universe (`canonical_baseline/REBASELINE.md`); the 14 masked names from `selection_edge/FACTOR_MENU.md` are excluded from all construction and appear only as a final reporting overlay.
- **Decision clock:** frozen 4H manifest; 13:30 ET and 16:00 ET decision bars; a fact version is usable only if `available_at + frozen_latency_buffer < decision_at` (strict); latest eligible as-seen version; fail closed on same-time conflicts; no decision-time override.
- **Coverage gate:** a decision date is evaluable only if ≥80% of the cohort has COMPUTABLE scores; otherwise the date is excluded (predeclared, not tuned).

## 3. Evaluation order (unchanged from the proposal)

1. Integrity before performance (provenance, coverage, revision replay, permanent-ID mapping, manifest/dual-anchor validation, independent timing fixtures; missingness placebo with frozen statistic + seed 20260926). Stop on a failed gate.
2. Same-population diagnostic on all canonical PIT candidates (descriptive only).
3. Selection test only on genuinely untouched holdout: exactly one predeclared slot-competition rule; full $75k / 1%-risk / 6-slot / 5%-heat portfolio replay at 50bp round-trip with 25/75/100bp stress; vs unchanged `rs_top2` on identical universe and dates. Displacement accounting mandatory.
4. Falsification battery: year/regime splits, untouched forward/holdout, episode-block uncertainty, concentration, leave-one-stock-out, coverage strata, placebo/permuted scores, adjacent parameters (no winner-picking).

## 4. Numeric PASS / MAYBE / FAIL (primary formulation only)

- **PASS:** expectancy ≥ +0.15R/trade net of 50bp costs on untouched holdout, ≥100 trades, survives the full falsification battery, no concentration flag.
- **MAYBE:** directionally positive but below +0.15R, or thin/fragile under perturbation.
- **FAIL:** ≤0R net, or fails falsification, or UNTESTABLE feed.

The best-performing variant or ablation can never quietly become the primary;
all variants stay in the family ledger as diagnostics.

## 5. Multiple-testing ledger (family history, retained)

- `selection_edge/FACTOR_MENU.md` (preregistered 2026-09-24): F7 earnings/revisions momentum listed as data-permitting; blinding rule for the 14 masked names; "if no clean PIT source exists, report UNTESTABLE, do not proxy it with price."
- `research_notes/research_mandate.md` (2026-09-25): FAM-UNIVERSE-FACTOR-MINING closed; family-ID governance adopted (this proposal reuses F7 inside that family — no new family ID minted to reset the ledger).
- `research_notes/fundamental_momentum_proposal_2026-09-26.md`: feasibility proposal + public-documentation check (this spec's parent).
- This document: first frozen primary formulation. Nothing computed against it.

## 6. Blocked until

Qualifying as-seen feed + complete anchored manifest + framework implementation-audit PASS + genuinely untouched confirmatory sample + Claude independent audit of the raw-to-normalized mapping. Until then: UNTESTABLE, not approximated.
