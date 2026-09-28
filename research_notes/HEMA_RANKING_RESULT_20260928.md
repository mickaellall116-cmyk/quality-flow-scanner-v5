# HEMA Slot-Ranking Result — 2026-09-28

Research-only. Frozen/live Quality Flow remains unchanged.

## Preregistered rule
When actual slot/heat pressure prevents all valid QF candidates from being accepted:
1. prefer candidates with a 4H HEMA bullish crossover on the current/prior 3 completed 4H bars;
2. retain the existing rs20_spy ordering inside each preference group;
3. never reject a QF setup solely because HEMA is absent.

Controls: existing rs20_spy only, EMA20>EMA40 preference, and 200 matched-random preference assignments preserving the HEMA-preference count in each batch.

## Result on the 30-symbol DST-corrected surrogate
At 50 bps:
- candidate batches: 291
- candidates after busy filtering: 296
- true competitive ranking decisions: 9
- candidates participating in those decisions: 25
- competitively ranked out: 15
- no-capacity rejects: 71

The HEMA rule changed **zero** accepted sets. Baseline and HEMA accepted the same set on 100% of the 9 competitive decisions.

Therefore baseline, HEMA ranking, EMA ranking and every matched-random control produced the same closed-trade result:
- closed trades: 205
- accepted entries: 206
- total net R: +113.805R
- net expectancy: +0.555R/trade
- net PF: 1.727
- marked return: +155.6%
- max marked-equity drawdown: 51.5%

There were no HEMA-unique or baseline-unique closed trades.

## Interpretation
The preregistered recent-crossover HEMA ranking rule has **no measurable incremental effect on this 30-symbol sample**. It did not lose to rs_top2; it simply never displaced a different trade. The sample has only nine true ranking-pressure decisions, and the HEMA preference labels were not positioned to alter any of them.

This does not establish that HEMA can never help ranking on the 131-symbol universe. It establishes that the 30-symbol surrogate cannot support that claim.

## Baseline reconciliation caveat
The corrected surrogate's very large portfolio-return headline is dominated by an extreme APLD trade:
- entry 2024-01-03 09:30 ET at 6.51
- structural stop 6.500459
- risk/share 0.009542
- 98,667 shares
- about $642k entry notional against roughly $94k book at that decision (~6.8x book)
- +54.38 net R

The canonical portfolio specification explicitly states that capital availability is not enforced beyond slot/heat limits, so the trade is mechanically consistent with the documented simulator but not representative of a normal cash-account implementation.

At 50 bps the baseline contains 13 trades above 1x book notional and 4 above 2x. Removing the largest trade reduces baseline net expectancy materially; removing the top 10 trades makes the remaining sample slightly negative. Portfolio-return percentages from this surrogate therefore should not be treated as robust live-return estimates.

## Current research decisions
- HEMA hard gate: FAIL as a system change.
- Small-green entry requirement: FAIL.
- Preregistered recent-crossover HEMA slot ranking on the 30-name surrogate: NO INCREMENTAL EFFECT / UNDERPOWERED.
- No live/frozen changes.

A real ranking conclusion requires the canonical 131-symbol PIT dataset, where slot competition is materially more frequent.
