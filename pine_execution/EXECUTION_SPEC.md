# EXECUTION_SPEC.md — Execution / slippage sensitivity on the LOCKED Pine V3.6 stack

**Status: FROZEN before any runs. Written 2026-09-18.**

Last item in Mike's approved research sequence
(MFE/MAE → Monte Carlo → sizing → exposure → combined stack → execution).
**Sensitivity analysis, not optimization.** No rule changes, no new strategy
variants, no execution "improvements" proposed.

## The locked stack (unchanged; only execution assumptions vary)

1. V3.6 signals and exits — frozen, byte-identical.
2. R1 rs_top2 ranking on contested bars (rank by 20-bar return minus SPY,
   take top min(2, free slots)).
3. R2 E1 sector cap (skip candidate if ≥2 positions in its sector are open;
   frozen sector map).

Reference (pine_stack/ C1 @4bps): 143 trades, +0.337R, +52.25%, DD 31.63%,
Calmar 1.65. The R3 drawdown gate was tested in the combined study and
rejected as redundant — it is NOT part of the locked stack.

## Scenarios (max 6, all pre-registered)

Costs are one-way per-trade costs applied in `pb._outcome`
(`net_ret = gross_ret − cost`), same accounting as every prior study.

| ID | Scenario | Definition |
|----|----------|------------|
| E0 | 4bps control | Locked stack at 4bps. **Fidelity check:** must reproduce C1 exactly (143 / 0.337R / +52.25% / DD 31.63%). Abort if it does not. |
| E1 | 10bps | Locked stack, cost = 0.0010. Realistic retail fill with spread. |
| E2 | 25bps | Locked stack, cost = 0.0025. Must reproduce pine_stack C1@25bps for consistency. |
| E3 | 50bps | Locked stack, cost = 0.0050. Stress: wide spreads / bad fills. |
| E4 | Adverse entry | Next-bar-open entry shifted **10bps adverse**: entry′ = entry × 1.0010; stop, TP1, exit prices unchanged; cost stays 4bps. Proxy for delay/chase on entry. Risk fraction recomputed from entry′ (consistent sizing). |
| E5 | Missed signals (HEADLINE) | Drop 10% of candidate signals uniformly at random, then run the locked stack on the remainder (ranking/sector cap operate on what remains — faithful model of Mike skipping ~1 in 10 signals). 20 repetitions, seeds = 20260918 + rep. Report median / p10 / p90 of expectancy and return. Rationale: the MFE study showed rare monster winners fund much of the expectancy, so discretionary skipping may cost more than transaction costs. |
| E6 | 100bps | Locked stack, cost = 0.0100. Extreme stress / very wide effective spread. |

E0–E4, E6 are run on **both C0 (V3.6 baseline, no ranking/sector cap) and C1
(locked stack)** — the stack's advantage must be re-verified under costs.
E5 is run on **C1 only** (the question is Mike's behavior on the locked
stack, not on the baseline).

## Metrics per scenario

trades, expectancy R (net), PF, return%, maxDD%, Calmar (= return% / DD%).
E5: distribution (median, p10, p90) of expectancy and return across reps,
plus median trades taken.

## The three key questions

1. **Break-even friction (THE headline number):** total round-trip
   slippage/fees the stack absorbs before expectancy hits zero. Computed
   by grid scan: run the full sim at costs 0, 5, 10, …, 150bps and
   linearly interpolate the zero crossing of expectancy, per case per
   window. (Exact-linearity does not hold: costs feed back through
   realized equity into the 5% portfolio-risk gate, so the taken set can
   shift by a trade or two at higher costs — observed: C1 took 142 vs 143
   trades at 25bps. The grid scan handles this honestly; the feedback is
   itself a finding: higher costs tighten the risk gate via lower equity.)
   Report break-even in bps for C1 (and C0 for reference), bull and 2022.
2. **Does the stack's edge over baseline survive costs?** Compare C1 vs C0
   at 10/25/50/100bps on expectancy, return, DD, Calmar. The locked stack
   is only worth its complexity if it still beats C0 when fills are bad.
3. **What does cherry-picking cost? (HEADLINE)** E5 median Δexpectancy and
   Δreturn vs E0 (full-signal C1), with p10/p90 bands. Compared directly
   against the transaction-cost legs: is skipping 1-in-10 signals worse
   than paying 25bps on every trade?

## 2022 window

Same framework/caches as every prior study
(v6_short_v2/cache + pine_exit_fix/cache_2022, signals ≥ 2022-01-01, EOD
liquidation, SECTOR_2022 map). Run E0–E4, E6 on C0 and C1, E5 on C1 (20 reps),
plus the break-even grid scan per case. Report whether the edge survives
realistic costs (25bps) in the bear window. Known: 2022 C0 = C1 (gates never
engaged, 37 trades) — the 2022 leg tests cost-robustness of the raw edge,
not the overlays.

## Pre-registered interpretation thresholds

- Edge **survives realistic costs** if at 25bps: bull expectancy > 0.15R
  AND Calmar > 1.0, AND 2022 expectancy > 0.
- Edge is **fragile to fills** if E4 cuts expectancy by >40% vs E0, or
  break-even < 15bps.
- Cherry-picking is **material** if E5 median return penalty vs E0 > 5pp,
  and **worse than transaction costs** if the E5 median penalty exceeds
  the E2 (25bps) penalty.

## What happens with the findings

- No execution "improvements" (limit orders, delayed entries as strategy)
  are designed or proposed here — that would be a new research round Mike
  did not authorize.
- If a scenario shows the edge is fragile to fills, it is reported
  plainly as a finding about **live viability**, feeding the pre-live
  engineering requirements (scanner parity, data integrity, live/backtest
  reconciliation) — not another research round.
- After this study, the approved research sequence is complete.
