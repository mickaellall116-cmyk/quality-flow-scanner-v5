# V1.7 vs V3.6 — Head-to-Head Analysis (2026-09-18)

## Verdict: V1.7 does NOT beat V3.6. Keep V3.6.

V1.7 wins the 2024–26 bull window decisively on expectancy (+0.338R vs +0.195R, +73%)
but fails on both robustness checks: it misses the pre-set drawdown gate
(42.3% vs 40% cap) and goes negative in the 2022 bear market (−0.112R vs V3.6's
+0.160R on the identical validation framework). This is the same pattern as every
other "improvement" tested in this research program (exit fixes, entry-ablation
candidates): complexity that shines in a bull market and breaks in a bear market.

## Head-to-head (UX51, 4H, 2024-09-16 → 2026-09-14, 4bps)

| Metric | V3.6 baseline | V1.7 AUTO Hybrid |
|---|---|---|
| Trades | 263 | 488 |
| Win rate | 44.9% | 52.3% |
| Expectancy | +0.195R | **+0.338R** |
| Profit factor | 1.27 | 1.77 |
| Portfolio return | +35.3% | +75.5% |
| Max drawdown | 35.2% | **42.3%** ← fails ≤40% gate |
| Avg winner / loser | +2.02R / −1.29R | +1.49R / −0.92R |
| Avg hold | 18.1 bars | 23.2 bars |
| TP1 hit rate | 47.5% | 55.5% |
| Stop-out % | 93.9% | 57.2% |
| Market exposure | ~? | 86.0% |
| Exit mix | — | stop 279 / weak 137 / cmf 59 / trend2 13 |

At 25bps: V1.7 +0.28R, PF 1.60, +55.4%, DD 46.5% (vs V3.6 +0.115R, PF 1.15).

Entry-type split (V1.7): 258 EARLY trades @ +0.178R vs 230 confirmed @ **+0.517R**.
The confirmed entries carry the edge; the early-entry machinery adds trade count
at roughly half the expectancy.

## 2022 bear-market validation (25 UX51 symbols, 4H, cutoff 2022-01-01, EOD liquidation)

| Metric (4bps) | V3.6 baseline* | V1.7 |
|---|---|---|
| Trades | ~39 | 91 |
| Expectancy | **+0.160R** | **−0.112R** |
| Profit factor | 1.17 | 0.81 |
| Return | — | −5.34% |
| Max drawdown | 24.5% | 24.1% |

\* V3.6 2022 numbers from the exit-fix validation on this identical framework
(25 symbols, same cutoff/EOD conventions).

V1.7's bull-window edge does not survive contact with a bear market. The
money-flow exit machinery (CMF/weak exits) and early entries that padded
bull-market returns became churn in 2022: 59.3% stop-out rate, PF 0.81.

## Why V1.7 loses (interpretation)
1. **More knobs, more regime-dependence.** CMF/MFI/OBV filters, per-asset-class
   branches, cooldowns, entry caps, weak exits — each adds a bull-market-tuned
   assumption. V3.6's simpler breakout engine proved regime-robust (+0.160R in
   2022); V1.7 did not.
2. **The DD gate existed for a reason.** 42.3% exploratory drawdown already
   signaled a rougher ride than V3.6's 35.2%; the 2022 failure confirms the
   extra return was rented, not owned.
3. **Early entries dilute.** +0.178R vs +0.517R for confirmed — the "AUTO Hybrid"
   early-entry system adds activity, not edge.

## Notes / deviations
- All 51 symbols ran on the STOCK branch per the frozen spec (crypto/index-like
  TV asset detection not reproduced; documented pre-test).
- Breakeven uses actual fill price; Pine uses signal-bar close (documented pre-test).
- V1.7's stop is close-evaluated (not intrabar) — faithful to the script, which
  never passes a stop to strategy.exit; only TP1 is a real intrabar limit order.
- Spec deviation (documented, honest): the 2022 run proceeded despite the
  42.26% DD missing the 40% gate by 2.3pp — as a pure validation step, which can
  only reject. The rejection stands on its own merits.

## Files
- `v1_7_reference.pine` — Mike's source, verbatim
- `V17_SPEC.md` — frozen pre-test spec
- `pine_v17_backtest.py` — exploratory backtest
- `pine_v17_validate.py` — 2022 validation
- `v17_results.json` / `v17_validate.json` — results
