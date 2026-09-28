# Position-Sizing Constraint Result — 2026-09-28

Research-only. No frozen/live scanner signal logic changed.

## Primary pre-registered rule
NO_LEVERAGE_1PCT_STOP:
- reject actual next-bar fills whose structural stop is less than 1.00% below entry;
- otherwise size from the existing 1% risk budget;
- cap entry notional at 100% of current equity;
- do not widen the stop.

At 50 bps on the DST-safe 30-symbol surrogate:

### RAW sizing
- 207 closed trades
- +0.599 net R/trade
- PF 1.79
- marked return +181.1%
- maximum marked DD 51.6%
- 13 entries >1.0x book
- max entry notional 9.21x book
- top-10 removed expectancy: +0.024R

### NO_LEVERAGE_1PCT_STOP — primary
- 199 closed trades
- 18 tight-stop rejections
- +0.332 net R/trade
- PF 1.47
- marked return +79.8%
- maximum marked DD 18.1%
- no entry >1.0x book; max 0.992x
- 2026: +0.258R/trade, PF 1.40
- top-10 removed expectancy: +0.005R

The 1% minimum stop itself prevented the extreme leverage, so the 1.0x notional cap did not bind in the primary run.

### Sensitivity checks at 50 bps
HALF_BOOK_1PCT_STOP:
- 200 closed trades
- +0.351R/trade
- PF 1.51
- marked return +87.4%
- maximum marked DD 15.8%
- 43 cap binds
- top-10 removed expectancy +0.026R

NO_LEVERAGE_2PCT_STOP:
- 171 closed trades
- +0.429R/trade
- PF 1.66
- marked return +93.0%
- maximum marked DD 13.5%
- 87 tight-stop rejections
- 2026 +0.528R/trade
- top-10 removed expectancy +0.055R

The 2% rule is a sensitivity result, not a selected winner; it must not be promoted just because it backtested better.

## Interpretation
Basic executable sizing constraints remove the pathological 6-9x exposures and greatly reduce the surrogate drawdown while leaving positive expectancy in the full sample. That is encouraging for **risk control**, but the edge remains highly concentrated: under the primary rule, removing the ten best trades leaves approximately flat expectancy.

This finding does not prove the canonical system is robust. It does show that any future executable layer should have explicit notional and stop-distance controls rather than sizing solely as risk_budget / stop_distance.

The current main-branch scanner does not size shares or place orders, so this is not a production-code change.
