# KAMA 20/40 QF Filter — Portfolio Result (2026-09-28)

Research-only. Frozen/live Quality Flow remains unchanged.

## Pre-registered rule
Filter raw QF signals using only:
- KAMA20 > KAMA40 on the completed QF signal bar;
- KAMA ER length equals line length;
- fast=2, slow=30;
- no other KAMA condition or tuning.

Both baseline and filter used:
- minimum 1% actual fill-to-stop distance;
- max single-position notional 100% of marked equity;
- max total gross exposure 100% of marked equity;
- 1% risk budget;
- max 6 open;
- max 5% risk heat;
- explicit null/unrankable RS handling;
- realistic gap-through stop fills;
- unchanged TP1 / Profit Protect / runner / timeout.

## Primary 50 bps result

| Metric | Realistic QF baseline | KAMA bull filter |
|---|---:|---:|
| Raw QF candidates | 380 | 380 |
| KAMA rejects | 0 | 93 |
| Closed trades | 191 | 160 |
| Net expectancy | +0.410R | +0.466R |
| Total net R | +78.34R | +74.53R |
| Profit factor | 1.595 | 1.678 |
| Win rate | 41.36% | 42.50% |
| Marked return | +104.10% | +98.17% |
| Max marked DD | 12.87% | 12.73% |
| 2026 expectancy | +0.616R | +0.741R |
| Top-10 removed expectancy | +0.055R | +0.041R |

Interpretation:
- KAMA improved **per-trade quality**, PF, win rate and 2026 expectancy.
- It did **not** improve the primary 50-bps total R or marked return because it removed opportunity.
- Drawdown improvement was negligible.
- After removing the ten best trades, both variants remain only slightly positive.

Trade-set comparison at 50 bps:
- 150 closed trades were shared.
- Baseline-only: 41 trades, +0.030R/trade.
- KAMA-only (created indirectly because filtering freed capacity): 10 trades, -0.268R/trade.

So the portfolio improvement in average trade quality is not simply explained by KAMA replacing baseline trades with superior unique trades; much of it comes from dropping weak marginal exposure.

## Cost ladder
At 25 bps:
- baseline +0.453R/trade, +119.31% marked return
- KAMA +0.577R/trade, +130.59%

At 75 bps:
- baseline +0.315R/trade, +78.92%
- KAMA +0.380R/trade, +77.15%

At 100 bps:
- baseline +0.221R/trade, +56.69%
- KAMA +0.296R/trade, +58.71%

KAMA therefore improves expectancy at every tested cost and improves marked return at 25 and 100 bps, but not at the primary 50 bps or 75 bps.

## Concentration
At 50 bps:
- baseline top-10 removed = +0.055R/trade
- KAMA top-10 removed = +0.041R/trade

At 75 and 100 bps, top-10 removal makes both variants negative.

The filter does not solve the system's dependence on large winners.

## Exposure / RS hygiene
The 100% gross-exposure rule prevented the earlier multi-x book leverage. The observed peak ratio can drift a few tenths of a percent above 1.0 after entry because market prices and marked equity move after the entry-time cap is applied.

KAMA-filter accepted trades had zero missing-RS entries at every cost in this run. Baseline still accepted 6-7 unrankable signals depending on cost because unrankable signals are allowed when capacity exists; they sort last rather than being rejected.

## EMA feature audit clarification
The tournament's EMA fast-line slope and price-distance features being perfectly correlated is **not a calculation defect**.

For an EMA with smoothing alpha:
- EMA_t - EMA_(t-1) = alpha * (Price_t - EMA_(t-1))
- Price_t - EMA_t = (1-alpha) * (Price_t - EMA_(t-1))

Therefore:
Price_t - EMA_t = ((1-alpha)/alpha) * (EMA_t - EMA_(t-1))

Both tournament features divide by the same current price, so they are exactly proportional by construction. For EMA20, price distance is 9.5 times the one-bar EMA slope. They are redundant features, not independent evidence.

## Decision
KAMA20>KAMA40 remains **PROMISING BUT UNPROVEN**.

It survives the full 30-name realistic portfolio screen as a trade-quality filter, but:
- primary 50-bps total return is lower;
- concentration remains;
- KAMA was selected from a multi-probe tournament on this same research universe.

Do not add KAMA to frozen/live QF from this result. The next valid confirmation is canonical 131-symbol PIT or genuinely forward shadow logging.
