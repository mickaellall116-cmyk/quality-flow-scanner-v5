# §6 Power Report — Quality Flow Preregistration v1.0 (freeze item C4)

**Date:** 2026-10-26. **Status:** produced for the v1.0 freeze record; closes checklist item C4's production half (independent review remains ChatGPT's).
**Decisions incorporated:** B1 REDUCED and B2 ECONOMICS-FIRST (Mike + ChatGPT, 2026-10-26). PASS under the adopted contract = all validity/economic gates met + point estimate ≥ δ + one-sided 95% interval excludes zero (L > 0). **CONFIRMED AT δ** (L ≥ δ) is retained as the stronger grade and is powered separately below.

## Method and bounds (binding)

- **Variance only.** Every figure below is computed from the frozen planning constants carried from v0.2 and confirmed by the -28 independent recomputation — per-trade σ = 1.8R, paired-excess σ = 2.6 ATR, planning μ = +0.17R (H-SYS-1). **No group difference was computed, no returns were computed, no outcome data was accessed, and the holdout window was not touched.** The corrected -28 arithmetic (693 / 1,392 / 3,506 / 1,829 / 8,013 / 4,179) is reused, not re-derived from data.
- Normal-approximation power: power = Φ((μ − δ)/(σ/√n) − z₁₋α) for the strict grade; Φ(μ/(σ/√n) − z₁₋α) for the L > 0 component of the adopted PASS. z₀.₉₅ = 1.6449, z₀.₈₀ = 0.8416 (sum 2.4865), matching the record's conventions.
- All required-n figures are **independent-observation** values; the dependence-aware requirement is the independent figure × the design effect (DE). A measured DE is on record for exactly one construction (§5); all other endpoints carry the planning DE grid, and no endpoint's power claim relies on DE < 1.
- Interval method (frozen, §6 [C10]): circular block bootstrap over calendar time, 20-session blocks, 10,000 reps; symbol-cluster bootstrap as robustness; **the verdict uses the wider of the two intervals**. Normal-approximation half-widths below are planning figures for that procedure, stated as E[half-width] = z₁₋α · σ/√n (× √DE dependence-aware).

## 1. Frozen inputs per endpoint

| Endpoint | δ | σ (planning) | α after allocation | Validity floor | Family / sequence |
|---|---|---|---|---|---|
| H-SYS-1 (primary, edge claim) | 0.05R / closed trade | 1.8R per-trade | 0.05 (single test) | 100 closed trades, ≥30 blocks, ≥20 symbols | own family |
| H-BUY-P (primary, h=10) | 0.10 ATR | 2.6 ATR paired excess | 0.05 (first in fixed sequence) | 200 de-clustered events, ≥30 blocks, ≥20 symbols | fixed sequence 10 → 5, 20 |
| H-BUY-S5 / S20 (secondary) | 0.10 ATR | 2.6 ATR paired excess | no α spent (gated on H-BUY-P) | same as H-BUY-P | descriptive if H-BUY-P fails |
| H-EXIT-1 (7A paired, E1−E0) | 0.10R / trade | paired SD — **not on record** (§6) | Holm over {1, 3, 4}: worst case 0.0167 (z = 2.1280), then 0.025 (z = 1.9600), then 0.05 | 100 closed trades | Holm, ties by fixed order 1, 3, 4 |
| H-EXIT-3 (7A paired, E0−E3) | 0.10R / trade | paired SD — **not on record** (§6) | same Holm allocation | 100 closed trades | Holm |
| H-EXIT-4 (7C replay diff) | 0.10R / trade | per-arm 1.8R; cross-arm dependence not estimable outcome-blind | same Holm allocation | 100 closed trades per replay | Holm |
| R-EXIT-2 (robustness) | — | — | **no α** (outside the family) | — | reported with FILL-OPTIMISM flag at < −0.10R; no power claim |

Gating cost for all verdicts: 25 bps round trip, per-fill convention (§8). Costs cancel in the H-BUY paired difference.

## 2. H-SYS-1 — required n and power

Independent-observation requirements (reused from -28 §1.2, verified):

| Question | Required n (independent) | At 7.5 closed trades/month |
|---|---|---|
| Adopted PASS power 80% at planning μ = +0.17R (L > 0 binds; see §5) | **≈693** | ≈7.7 years |
| CONFIRMED AT δ (L ≥ δ) at μ = +0.17R, 80% power | **≈1,392** | ≈15.5 years |
| Interval half-width = δ | ≈3,506 | ≈39 years |
| CONFIRMED AT δ at true effect 2δ, 80% power | ≈8,013 | ≈89 years |

Power and expected half-width at candidate sample sizes (α = 0.05, independent):

| n (closed trades) | E[half-width] | Power, adopted PASS (L > 0) | Power, CONFIRMED AT δ (L ≥ δ) |
|---|---|---|---|
| 85 (holdout-scale, -28) | 0.321R | 0.22 | 0.15 |
| 100 (validity floor) | 0.296R | 0.24 | 0.16 |
| 187 (DEV realized) | 0.217R | 0.36 | 0.23 |
| 500 | 0.132R | 0.68 | 0.44 |
| 693 | 0.113R | **0.80** | 0.54 |
| 1,392 | 0.079R | 0.97 | **0.80** |

**Reading.** At every attainable n the expected half-width (≥0.08R even at n = 1,392) exceeds δ = 0.05R, so under the frozen label rule H-SYS-1 is **UNDERPOWERED FOR PASS at the strict grade** on any near-term accrual — it can FAIL (U < δ) or be INCONCLUSIVE, and under B2 it can PASS at the economics-first grade with the power shown above. The binding constraint is accrual time, not measurement (feasibility doc §3).

## 3. H-BUY-P — required n and power

No planning μ was declared for H-BUY in v0.2; power is therefore tabled parametrically in the true paired-excess μ (σ = 2.6 ATR, δ = 0.10 ATR, α = 0.05).

| True μ (ATR) | Required n, CONFIRMED AT δ (80%) | Required n, half-width = δ |
|---|---|---|
| 0.20 (= 2δ) | **≈4,179** | ≈1,829 |
| 0.26 | ≈1,633 | ≈1,829 |
| 0.30 | ≈1,045 | ≈1,829 |

| n (de-clustered events) | E[half-width] | Power, adopted PASS (L > 0) @ μ = 0.20 / 0.26 | Power, CONFIRMED AT δ @ μ = 0.20 / 0.26 |
|---|---|---|---|
| 200 (validity floor) | 0.302 ATR | 0.29 / 0.41 | 0.14 / 0.22 |
| 240 (EXP-14B retained scale) | 0.276 ATR | 0.33 / — | 0.15 / 0.25 |
| 500 | 0.191 ATR | — / — | 0.22 / 0.39 |
| 1,829 | 0.100 ATR | — / — | 0.50 / 0.84 |

**Reading.** H-BUY-P is likewise **UNDERPOWERED FOR PASS at the strict grade** at the validity floor and at any DEV-scale event count; the economics-first PASS is attainable but far from assured at the floor (≈29–41% at the planning grid). The 5- and 20-bar secondaries inherit this table (same σ planning constant); they spend no α and are inferential only behind a H-BUY-P PASS (fixed sequence).

## 4. H-EXIT family — paired SD status and power grid

**The one §6 input not on record:** the paired per-trade SDs for the 7A endpoints (H-EXIT-1, H-EXIT-3). They cannot be reused from the -28 arithmetic (which covers only σ = 1.8R and 2.6 ATR) and estimating them requires the pooled arm-difference variance on DEV — a variance-only computation that is part of the freeze procedure, not yet run. This report therefore publishes the frozen formula and the planning grid; **the freeze record must be completed with the estimated paired SDs before any tier opens** (§6: the power report is required *before any tier is opened* — this item is the named residue).

Required n for 80% power, CONFIRMED AT δ (δ = 0.10R), by paired SD and true paired effect μ:

| Paired SD | μ = 0.15R, α = 0.05 / Holm worst | μ = 0.20R, α = 0.05 / Holm worst | μ = 0.30R, α = 0.05 / Holm worst |
|---|---|---|---|
| 0.50R | 618 / 882 | 155 / 220 | 39 / 55 |
| 0.75R | 1,391 / 1,984 | 348 / 496 | 87 / 124 |
| 1.00R | 2,473 / 3,528 | 618 / 882 | 155 / 220 |
| 1.50R | 5,564 / 7,937 | 1,391 / 1,984 | 348 / 496 |

Power at the validity floor (n = 100 paired trades), CONFIRMED AT δ:

| Paired SD | μ = 0.20R, α = 0.05 / Holm worst | μ = 0.30R, α = 0.05 / Holm worst | E[half-width] at α = 0.05 |
|---|---|---|---|
| 0.50R | 0.64 / 0.45 | 0.99 / 0.97 | 0.082R |
| 0.75R | 0.38 / 0.21 | 0.85 / 0.71 | 0.123R |
| 1.00R | 0.26 / 0.13 | 0.64 / 0.45 | 0.164R |
| 1.50R | 0.16 / 0.07 | 0.38 / 0.21 | 0.247R |

Under B2's adopted PASS (L > 0, Holm-adjusted bound), floor power is materially higher (e.g. paired SD 0.75R, μ = 0.20R: ≈0.85 at α = 0.05 before Holm adjustment).

**H-EXIT-4 (study 7C)** is not a paired test: the estimand is the difference of two replay means, inference by the joint calendar-block bootstrap. On the conservative independent-arms approximation (per-arm σ = 1.8R, equal n per arm): SE(diff) at 100 trades/arm = 0.255R, E[half-width] = 0.419R, CONFIRMED-AT-δ power at a true 0.20R difference ≈ 0.11, adopted-PASS (L > 0) power ≈ 0.20. Positive cross-arm dependence (same calendar blocks, same signal stream) can only narrow the joint-bootstrap interval relative to this approximation; the approximation is therefore a floor, stated as such, and no tighter figure is claimed outcome-blind.

## 5. Why the adopted-PASS power equals the vs-zero power at realistic n

The B2 PASS rule has two statistical components: θ̂ ≥ δ and L > 0. L > 0 fails exactly when θ̂ ≤ z₁₋α·SE. At every realistic sample size in §§2–4, z₁₋α·SE (the expected half-width, 0.08R–0.42R) exceeds δ (0.05R / 0.10 ATR / 0.10R), so the L > 0 component binds first and θ̂ ≥ δ is implied whenever L > 0 holds with θ̂ near its expectation. The adopted-PASS power is therefore the vs-zero power at the planning μ — this is an arithmetic property of the frozen constants, not a relaxation smuggled in by this report. The strict grade's power is reported separately everywhere above, and the UNDERPOWERED FOR PASS label continues to attach to the strict grade exactly as §6 defines it.

## 6. Design effects

- **Measured (one construction, on record):** EXP-14B's DEV matched-subpopulation run reports design effect **0.880** (symbol-cluster resample variance of the mean ÷ iid variance of the mean; n = 240, n_eff = 272.6; run record commit `3c92dc8`, output sha `d9f4864e…`). This is a variance statistic from a completed DEV exploratory run, quoted as record — it is **not** adopted as the planning DE for any v1.0 endpoint, and no requirement above is reduced by it.
- **Planning grid (dependence-aware required n = independent n × DE):**

| Independent requirement | DE 1.0 | DE 1.5 | DE 2.0 | DE 3.0 |
|---|---|---|---|---|
| H-SYS-1 adopted PASS, 693 | 693 | 1,040 | 1,386 | 2,079 |
| H-SYS-1 CONFIRMED AT δ, 1,392 | 1,392 | 2,088 | 2,784 | 4,176 |
| H-BUY-P half-width = δ, 1,829 | 1,829 | 2,744 | 3,658 | 5,487 |
| H-BUY-P CONFIRMED AT δ @ 2δ, 4,179 | 4,179 | 6,268 | 8,358 | 12,537 |

- Per-tier expected half-widths are the §2–§4 half-width columns evaluated at each tier's analysis n (Stage A pooled Tier 2 + Tier 3 event/trade counts are not yet countable outcome-blind — the §5 pool-size feasibility check is a freeze-procedure step; Stage B counts accrue prospectively under §10). Where a tier's eventual n is below its endpoint's floor, the verdict is INCONCLUSIVE regardless of estimate (§6 validity floors).

## 7. Bottom line

1. At the frozen planning constants, **no endpoint reaches 80% power for CONFIRMED AT δ on any near-term sample**; H-SYS-1 needs ≈1,392 independent closed trades (≈15.5 years at DEV accrual) and H-BUY-P ≈4,179 independent events at a 2δ true effect. This is the -28/feasibility conclusion, unchanged.
2. Under the adopted B2 economics-first contract, PASS is attainable at realistic samples with the power tabled above (H-SYS-1: 24% at the 100-trade floor, 36% at DEV scale, 80% at ≈693 independent trades) — the contract change, not new data, is what makes a PASS reachable, and both grades will be printed with every verdict.
3. The single missing §6 input is the **H-EXIT paired SDs** (variance-only estimate, freeze procedure). Everything else §6 requires of this report — per-endpoint strict-δ power, allocated α (Holm worst case for H-EXIT), design effects, expected half-widths — is published above from variance only.

— Muse (production lane; independent review: ChatGPT, checklist C1/C4)
