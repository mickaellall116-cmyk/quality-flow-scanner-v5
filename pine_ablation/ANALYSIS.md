# ABLATION ANALYSIS — four-layer audit of the locked Pine V3.6 stack

Spec: `ABLATION_SPEC.md` (pre-registered before runs). Engine:
`pine_stack.simulate_stack` verbatim + one gated `risk_gate` flag; S4
drawdown gate off for all layers; identical trades/costs/accounting.
Supplementary `L1b` cell (ranking + risk gate, no sector cap) is a
non-pre-registered diagnostic, labeled as such throughout.

## Fidelity

L3 reproduces locked C1 **exactly** on both cost legs: 143 / +0.337R /
+52.25% / 31.63% @4bps; 142 / +0.280R / +39.64% / 33.79% @25bps —
matching `pine_stack/stack_results.json` trade-for-trade. PASS.

Cross-check: L1b @4bps reproduces the published rs_top2 numbers exactly
(154 / +0.324R / 52.78% / 32.65%), confirming engine consistency with the
ranking study.

## Layer table — research window (UX51 4H, 2024-09-16 → 2026-09-14)

@4bps:

| Layer | Trades | Exp R | PF | Return | MaxDD | Calmar |
|---|---|---:|---:|---:|---:|---:|
| L0 V3.6 core | 167 | 0.215 | 1.31 | 31.79% | 36.95% | 0.860 |
| L1 + ranking | 157 | 0.300 | 1.43 | 47.30% | 35.34% | 1.338 |
| L2 + sector cap | 143 | 0.273 | 1.39 | 38.09% | 32.92% | 1.157 |
| L3 + 5% risk gate (= locked) | 143 | 0.337 | 1.49 | 52.25% | 31.63% | 1.652 |
| L1b ranking + gate, no cap (suppl.) | 154 | 0.324 | 1.48 | 52.78% | 32.65% | 1.617 |

@25bps:

| Layer | Trades | Exp R | PF | Return | MaxDD | Calmar |
|---|---|---:|---:|---:|---:|---:|
| L0 V3.6 core | 167 | 0.141 | 1.19 | 16.39% | 41.07% | 0.399 |
| L1 + ranking | 157 | 0.226 | 1.31 | 31.10% | 39.03% | 0.797 |
| L2 + sector cap | 143 | 0.200 | 1.27 | 24.10% | 37.95% | 0.635 |
| L3 + 5% risk gate (= locked) | 142 | 0.280 | 1.39 | 39.64% | 33.79% | 1.173 |
| L1b ranking + gate, no cap (suppl.) | 153 | 0.260 | 1.36 | 37.84% | 33.63% | 1.125 |

## Incremental verdicts (pre-registered rule)

Rule: a layer EARNS ITS PLACE if vs the previous layer it improves
Calmar, or cuts maxDD ≥2pp at a return cost ≤2pp.

| Step | ΔReturn | ΔDD | ΔCalmar | Verdict @4bps | Verdict @25bps |
|---|---|---:|---:|---|---|
| L1−L0 (ranking) | +15.51pp | −1.61pp | +0.478 | **EARNS PLACE** | **EARNS PLACE** (+14.71pp, +0.398) |
| L2−L1 (sector cap) | −9.21pp | −2.42pp | −0.181 | **FAILS** (DD cut ≥2pp but return cost 9.21pp > 2pp; Calmar worse) | **FAILS** (−7.00pp, −1.08pp, −0.162) |
| L3−L2 (risk gate) | +14.16pp | −1.29pp | +0.495 | **EARNS PLACE** | **EARNS PLACE** (+15.54pp, −4.16pp, +0.538) |

## The sector-cap nuance (supplementary, decision-relevant)

The cumulative rule tests the cap *without* the gate — and there it fails.
But the final stack *includes* the gate, so the decision-relevant
counterfactual is L3 vs L1b (cap given ranking + gate):

| Step | ΔReturn | ΔDD | ΔCalmar @4bps | ΔCalmar @25bps |
|---|---|---:|---:|---:|
| L3−L1b (cap, gate present) | −0.53pp | −1.02pp | +0.035 (1.617→1.652) | +0.048 (1.125→1.173), ΔReturn +1.80pp |

With the gate present, the cap is Calmar-positive at **both** cost legs:
a mild de-risking (−1.0pp DD at −0.5pp return @4bps; +1.8pp return @25bps).
Skipped-trade diagnostic @4bps: the cap's 17 skips summed to ~0R
(mean 0.001R) — its L2-vs-L1 harm came from perturbing the selection path
without the gate to stabilize it, not from skipping winners. The cap's
value is real but THIN and GATE-DEPENDENT: without the risk gate it hurts;
with it, it helps slightly. It is the thinnest layer of the four — first
candidate for removal if a future documented failure mode ever implicates
it.

## 2022 window

All four layers identical: 37 trades, +0.376R, +11.2%, DD 21.3% @4bps
(+0.293R, +8.0%, DD 23.1% @25bps). Ranking engaged trivially (2 contested
signals, same 37 taken); sector cap never engaged (0 skips); the 5% risk
gate never tripped (0 trips). Per the spec, layers that never engage cannot
earn their place on this window — 2022 confirms no harm, verdicts are
driven by the research window. Same as every prior study.

## Engagement summary (research window @4bps)

- Ranking: 76–82 contested bars / 105–113 contested signals per run;
  94–106 rank skips. Engages constantly.
- Sector cap: 16–17 skips. Engages on clustered bars.
- 5% risk gate: 10 trips @4bps (11 @25bps). Engages exactly when the
  portfolio is at max heat — which is when protection matters.

## Headline answer

**The 5% portfolio-risk gate adds UNIQUE protection — it is not another
hidden redundancy.** L3 vs L2: +14.2pp return, −1.3pp DD, Calmar
1.16→1.65 @4bps (+15.5pp, −4.2pp, 0.64→1.17 @25bps). It also earns its
place on top of ranking alone (L1b vs L1: +5.5pp, −2.7pp). The gate's 10
skipped trades summed to −1.2R — it was vetoing real losers at max-heat
moments, a job neither ranking nor the sector cap does.

## Final verdict

**The locked stack STAYS FOUR LAYERS: V3.6 core + ranking + sector cap +
5% risk gate.** L3 has the best Calmar at both cost legs (1.652 @4bps,
1.173 @25bps); the three-layer alternative without the cap (L1b) is not
better on a risk-adjusted basis at either leg. Ranking and the risk gate
earn their places decisively; the sector cap earns a thin, gate-dependent
place in the final stack. No layer is removed. Per the change-control bar,
the stack now freezes: any future change needs a documented failure mode,
a pre-registered test, and out-of-sample validation.
