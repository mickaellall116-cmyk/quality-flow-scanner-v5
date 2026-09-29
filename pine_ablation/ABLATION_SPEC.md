# ABLATION SPEC — four-layer audit of the locked Pine V3.6 stack

**Status: PRE-REGISTERED before runs. No new ideas, no parameter tuning.
The 5% threshold is not varied. Pure audit of what is already locked.**

## Purpose

Mike commissioned this as the final strategy-side check before the whole
stack freezes. Question: does each of the four locked components earn its
place, in particular whether the 5% portfolio-risk gate adds UNIQUE
protection beyond ranking + sector cap, or is another hidden redundancy
(like the S4 drawdown gate turned out to be).

## The four layers (cumulative)

| Layer | Components | Engine flags |
|---|---|---|
| L0 | V3.6 core: frozen signals/exits, 5-position slot cap, exits-before-entries ordering. No ranking, no sector cap, no 5% risk gate. | ranking=off, sector_cap=off, risk_gate=off |
| L1 | L0 + rs_top2 ranking (20-bar return minus SPY, take top min(2, free slots) on contested bars) | ranking=on, sector_cap=off, risk_gate=off |
| L2 | L1 + E1 sector cap (max 2 concurrent per sector, frozen SECTOR map) | ranking=on, sector_cap=on, risk_gate=off |
| L3 | L2 + 5% portfolio-risk gate (skip candidate when open_risk + cur_risk > 5%; the reference behavior that fired 10x in validated C1) | ranking=on, sector_cap=on, risk_gate=on |

L3 is the locked production stack (C1 from the combined-stack study).

## Engine

`pine_ablation.py` reuses the validated `pine_stack.simulate_stack`
event loop VERBATIM with exactly one difference: the MAX_PORTFOLIO_RISK
(5%) skip check is gated behind a `risk_gate` flag (off for L0–L2, on for
L3). The S4 drawdown gate (R3, archived) stays OFF for all four layers.
Identical trades, costs, and accounting across all layers; one consistent
accounting within this study.

## Fidelity check (must pass before verdicts)

L3 must reproduce locked C1 from `pine_stack/stack_results.json` exactly:
143 trades, +0.337R expectancy, +52.25% return, 31.63% maxDD @4bps
(and 142 / +0.280R / +39.64% / 33.79% @25bps). Any deviation = abort.

## Windows and costs

- Research window: UX51 4H, 2024-09-16 → 2026-09-14, cost legs 4bps + 25bps.
- 2022 window: same framework/caches as every prior study, 4bps + 25bps.

## Metrics per layer per leg

trades, expectancy R/trade, PF, return%, maxDD%, Calmar
(= return% / maxDD%, computed identically for all layers), plus engagement:
contested bars / contested signals (ranking), sector-cap skips, risk-gate
trips (L3 only by construction). Incremental deltas per layer vs previous:
Δreturn, ΔDD, ΔCalmar.

## Keep / archive rule (pre-registered)

A layer EARNS ITS PLACE if its incremental addition vs the previous layer
either (a) improves Calmar, or (b) cuts maxDD by ≥2pp at a return cost of
≤2pp. A layer that fails is flagged REDUNDANT — archived as validated, not
deleted (same treatment the S4 drawdown gate received). A layer that never
engages on a window cannot earn its place on that window; the verdict is
then driven by the window where it does engage.

## Headline question

L3 vs L2: does the 5% risk gate add unique protection beyond ranking +
sector cap, or is it another hidden redundancy? The incremental
ΔDD / Δreturn / ΔCalmar of the gate, plus its 10-trip engagement record,
decides it.
