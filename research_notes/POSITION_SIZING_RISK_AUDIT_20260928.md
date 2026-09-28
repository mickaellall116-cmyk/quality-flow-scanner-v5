# Position-Sizing Risk Audit — 2026-09-28

Research-only audit. No live/frozen production logic changed.

## Trigger
The DST-corrected 30-symbol surrogate produced an extreme APLD trade because shares were sized as risk_budget / (entry - structural_stop) with no notional/capital cap.

## Baseline with and without APLD (50 bps, rs ranking)
With APLD:
- n = 205
- total net R = +113.8052R
- net expectancy = +0.5551R/trade
- net PF = 1.7271
- win rate = 39.02%

Without APLD 2024-01-03:
- n = 204
- total net R = +59.4247R
- net expectancy = +0.2913R/trade
- net PF = 1.3796
- win rate = 38.73%

APLD 2024-01-03:
- entry = 6.51
- stop = 6.500459
- stop distance = 0.009541/share = 0.1466% of entry
- shares = 99,601
- entry notional / contemporaneous book ≈ 6.82x
- net result = +54.3805R

The stop distance is approximately 0.1466%, not 0.015%. Historical bid/ask quotes are not in the dataset, so this audit cannot prove that the stop was literally inside the spread. It is nevertheless an extremely narrow next-open-to-stop distance.

## Tight-stop / notional concentration in the 205-trade surrogate
Stop distance below:
- 0.25%: 2 trades
- 0.50%: 4 trades
- 1.00%: 13 trades
- 1.50%: 37 trades
- 2.00%: 54 trades

Entry notional above:
- 1.0x book: 13 trades
- 2.0x book: 4 trades
- 3.0x book: 3 trades
- 5.0x book: 2 trades

Largest notional/book examples:
1. SPY 2024-04-12: 9.22x book, 0.1085% stop distance, -5.61 net R.
2. APLD 2024-01-03: 6.82x book, 0.1466% stop distance, +54.38 net R.
3. ORCL 2023-12-05: 3.39x book, 0.2954% stop distance, -2.69 net R.
4. NVDA 2024-06-24: 2.88x book, 0.3467% stop distance, -2.44 net R.

This is therefore a general sizing-model issue, not an APLD-only anomaly.

## Canonical baseline
canonical_baseline/PORTFOLIO.md documents:
- $75k book;
- $750 fixed risk/trade;
- shares = floor(750 / (entry - stop));
- max 6 open and approximately 5% heat;
- **no capital-availability constraint beyond slots/heat**.

The trade-level canonical artifacts referenced by that document (canonical_trades.json, portfolio_results.json, simlib.py, run_portfolio.py) are not present on main and have no commit history at those paths, so the 374 canonical trades cannot currently be audited for tight-stop/notional concentration. The historical canonical metrics should therefore remain qualified until the actual trade records are recovered or regenerated.

## Live / forward code check
The current main-branch MasterScanner API and Streamlit scanner output setup state, entry status, stop and TP1. They do not calculate shares, account equity, or position notional, and they do not place orders. Therefore this repository's live scanner does **not** automatically create the 6.8x APLD exposure.

Any separate execution/sizing layer that uses risk_budget/(entry-stop) must be audited independently.

The committed forward-test snapshot as of 2026-09-25 contains entries/stops but no share sizing. The visible open/closed stops are materially wider than the APLD case; no sub-1% stop distance was observed in that snapshot.

## Required risk controls before any executable sizing layer
1. Hard maximum entry notional as a fraction/multiple of actual account equity.
2. Entry-time minimum usable stop distance or a rule that rejects/recomputes a trade when the next fill is too close to the structural stop.
3. Recompute risk/reward at the actual fill, not only on the signal bar.
4. Slippage/gap handling so a tight planned stop cannot be treated as guaranteed 1R risk.
5. Log entry, stop, stop-distance %, shares, notional/equity and actual dollars-at-risk for every trade.

Threshold values should be preregistered as risk controls and validated; they should not be chosen to maximize this historical sample's return.
