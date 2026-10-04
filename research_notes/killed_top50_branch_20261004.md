# KILLED BRANCH: TOP-50 / quarterly / frozen composite
**Status:** KILL (Mike, 2026-10-04). Adjudicating result accepted.
**Do not retune.** Do not revive without genuinely new held-out/forward evidence or a materially different preregistered hypothesis.

## Hypothesis
A mechanically selected TOP-50 stock universe (quarterly rebalance; 50% liquidity + 50% RS-vs-SPY composite) improves the frozen System-1 (C1) stack versus BROAD-218.

## Adjudicating test
- System: true frozen System-1 (gen_candidates → compute_features → simulate_stack, ranking + sector cap 2 + **S4 DD gate**).
- Inputs: 225 Yahoo 1H hash-verified; 218 daily + SPY frozen/hashed; corrected session candles.
- Window: 2025-03-17 → 2026-09-14. Costs: 4bps + 25bps (25bps primary).
- Results: `research_notes/top_broad_results_20261004.json` (commit `df79558`).

## Result
| | BROAD (218) | TOP (50) |
|---|---|---|
| Trades @25bps | 195 | 173 |
| Expectancy @25bps | −0.091R | **+0.002R** |
| Calmar @25bps | −0.69 | 0.26 |

Gates: G0 FAIL, G1 FAIL (+0.093R vs +0.10R bar), G2 FAIL, G3 FAIL, G4 PASS, G5 FAIL (CI [−0.20, +0.43]).

## Verdict rationale (Mike)
- TOP beat BROAD by +0.093R directionally — possible ranking information in the composite — but missed the preregistered +0.10R differential.
- Decisively: TOP itself produced essentially **zero** expectancy (+0.002R). There is no edge to improve upon.
- The descriptive run (no S4) showed +0.050R; the adjudicating run (S4 on) collapsed it to +0.002R. **Do not conclude "S4 is bad."** The lesson: the apparent advantage did not survive interaction with the actual frozen portfolio/risk system — exactly why full-stack replay was required.

## Frozen prohibitions
Do NOT retune using these results: cutoff (50), rebalance interval (quarterly), composite weights (50/50), S4 interaction, or any other parameter. Revival requires new held-out/forward evidence or a materially different preregistered hypothesis. Holdout remains sealed.

## Surviving research lesson
Ranking/filter ideas must be judged inside the actual portfolio stack, not on isolated trade expectancy. This test demonstrated why.
