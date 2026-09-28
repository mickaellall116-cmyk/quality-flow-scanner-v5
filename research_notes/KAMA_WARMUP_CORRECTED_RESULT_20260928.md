# KAMA Warmup-Corrected Portfolio Result — 2026-09-28

Research-only. Frozen/live Quality Flow remains unchanged.

## Mechanical correction
Both the baseline and KAMA-filter variants now ignore QF signals before the frozen 215-bar warmup completes. No KAMA parameter, risk rule, ranking rule, exit, cost, or execution assumption changed.

This removes 96 pre-warmup QF candidates and eliminates all accepted missing-RS trades in both variants.

## Primary 50 bps result

| Metric | Baseline | KAMA20>KAMA40 |
|---|---:|---:|
| Closed trades | 149 | 130 |
| Net expectancy | +0.2815R | +0.4047R |
| Total net R | +41.94R | +52.62R |
| Profit factor | 1.399 | 1.596 |
| Win rate | 39.60% | 41.54% |
| Marked return | +57.11% | +73.24% |
| Max marked DD | 13.03% | 13.56% |
| 2026 expectancy | +0.541R | +0.623R |
| Top-10 removed expectancy | -0.130R | -0.065R |

At 50 bps the corrected KAMA filter now improves expectancy, total R, PF, win rate, and marked return. Drawdown is slightly worse.

Trade-set comparison:
- shared closed trades: 121
- baseline-only: 28 trades, -0.328R/trade
- KAMA-only, created by freed capacity: 9 trades, +0.154R/trade

This reverses the prior capacity result: after the warmup fix, the trades removed/replaced by the KAMA-filter portfolio are materially less favorable.

## Cost ladder

25 bps:
- baseline: +0.390R/trade, +58.54R total, +82.03% return
- KAMA: +0.454R/trade, +59.50R total, +80.83% return

50 bps:
- baseline: +0.281R/trade, +41.94R total, +57.11% return
- KAMA: +0.405R/trade, +52.62R total, +73.24% return

75 bps:
- baseline: +0.206R/trade, +30.48R total, +48.44% return
- KAMA: +0.332R/trade, +42.86R total, +58.16% return

100 bps:
- baseline: +0.102R/trade, +15.32R total, +33.21% return
- KAMA: +0.250R/trade, +32.26R total, +44.26% return

The KAMA filter therefore improves both total R and marked return at 50, 75 and 100 bps. At 25 bps it has slightly higher total R but slightly lower marked return.

## Year splits at 50 bps

Baseline:
- 2024: n=45, +0.102R/trade
- 2025: n=63, +0.241R/trade
- 2026: n=41, +0.541R/trade

KAMA:
- 2024: n=38, +0.318R/trade
- 2025: n=53, +0.307R/trade
- 2026: n=39, +0.623R/trade

Direction is favorable to KAMA in all three full years.

## Remaining weakness
Concentration remains severe.

At 50 bps:
- baseline top-10 removed: -0.130R/trade
- KAMA top-10 removed: -0.065R/trade

At 100 bps:
- baseline top-10 removed: -0.313R/trade
- KAMA top-10 removed: -0.225R/trade

So the warmup correction strengthens the case for KAMA as a filter, but does not make the system robust to removal of its best trades.

## Decision
The exact frozen KAMA20>KAMA40 filter now passes the predeclared 30-name screen criterion: after the warmup correction it improves total R and marked return at 50-100 bps.

Status: **ADVANCE TO SHADOW / CANONICAL CONFIRMATION — NOT LIVE DEPLOYMENT.**

Canonical 131-symbol PIT confirmation remains blocked by the missing canonical executable artifacts/data. Until those are recovered, the legitimate next validation is forward shadow logging: record KAMA20, KAMA40 and KAMA-bull state on every future QF signal before its outcome is known, without changing whether the signal is issued or traded.
