# V1.1 vs V3.6 — Head-to-Head Analysis

## Verdict: **V1.1 does NOT beat V3.6. Keep V3.6.**

Spec: `V11_SPEC.md` (frozen before any test). Reference source: `v1_1_reference.pine`
(verbatim). No existing files modified; local-only research.

## Head-to-head: bull window (UX51 4H, 2024-09-16 → 2026-09-14)

| Metric | V3.6 (baseline) | V1.1 (4bps) | V1.1 (25bps) |
|---|---|---|---|
| Trades | 263 | 493 | 493 |
| Win rate | 44.9% | 60.2% | 58.0% |
| Expectancy | +0.195R | **+0.300R** | +0.243R |
| Profit factor | 1.27 | **1.84** | 1.64 |
| Return | +35.3% | **+105.7%** | +83.0% |
| Max drawdown | 35.2% | **20.4%** | 21.2% |
| Avg hold | 18.1 bars | 16.3 bars | 16.3 bars |
| TP1 hit rate | 47.5% | 59.0% | 59.0% |
| Avg winner | +2.02R | +1.09R | +1.08R |
| Avg loser | −1.29R | −0.90R | −0.91R |
| Stop-out % | 93.9% | 57.2% | 57.2% |
| Exit mix | stop-dominated | stop 282 / cmf 204 / trend2 7 | same |

V1.1 wins the bull window on every headline metric: +0.300R vs +0.195R expectancy,
PF 1.84, and a *lower* drawdown (20.4% vs 35.2%). The 60% win rate with avg winner
+1.09R / avg loser −0.90R is a different edge profile than V3.6's (45% wins,
+2.02R / −1.29R): V1.1 wins by frequency and loser control, V3.6 by winner size.

Adoption gate (per V11_SPEC.md): expectancy > +0.195R with DD ≤ 40% → **met**
(+0.300R, DD 20.4%) → 2022 validation required.

## 2022 bear-market validation (25 symbols, 4H, same framework as V1.7 study)

| Metric | V3.6 | V1.1 (4bps) | V1.1 (25bps) |
|---|---|---|---|
| Trades | 39 | 115 | 115 |
| Expectancy | **+0.160R** | **−0.083R** | −0.136R |
| Profit factor | 1.17 | 0.83 | 0.73 |
| Return | — | −0.63% | −5.29% |
| Max drawdown | 24.5% | 17.9% | 20.9% |

V1.1 fails the validation: the bull-window edge (+0.300R) does not survive the bear
market (−0.083R, PF 0.83). V3.6 stays positive on the identical framework (+0.160R).
11 of 115 trades were still open at data end (EOD liquidation).

## Why V1.1 breaks in 2022

V1.1's entry is looser than V1.7's confirmed entry (no ADX, no EMA200, no regime
gate — just EMA21>55 + 20-bar breakout + CMF>0 + MFI 40–75 + ATR ratio). In a bear
market, CMF>0 on a 20-bar breakout is exactly the setup that catches dead-cat
bounces and relief rallies: the CMF exit (which closed 204/493 trades in the bull
window) can't save entries taken at bear-market highs. Same species of failure as
V1.7's — extra looseness that monetizes bull-market chop but buys bear-market rips.

## Conclusion

- V1.1 is the best *bull-market* variant tested tonight (+0.300R, lowest DD), but it
  is not regime-robust. Tonight's discipline is clear: no candidate is adopted on
  bull-window performance alone.
- **Keep V3.6.** This is not a recommendation to change Mike's live script.

## Files
- `V11_SPEC.md` — frozen pre-test spec
- `v1_1_reference.pine` — verbatim source
- `pine_v11_backtest.py` / `pine_v11_validate.py`
- `v11_results.json` / `v11_validate.json`
- `ANALYSIS.md` (this file)
