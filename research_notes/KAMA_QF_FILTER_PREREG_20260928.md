# KAMA 20/40 QF Filter — Portfolio Preregistration

Research-only. Frozen/live Quality Flow remains unchanged.

Hypothesis: keep only QF signals where KAMA20 > KAMA40 on the completed QF signal bar.

KAMA definition is frozen exactly as used in the trend-probe tournament:
- ER length equals the line length
- fast smoothing = 2
- slow smoothing = 30
- line lengths = 20 and 40

No tuning or additional KAMA conditions are allowed.

Compare:
1. REALISTIC_QF_BASELINE — all valid QF signals.
2. KAMA_BULL_FILTER — reject QF signals when KAMA20 <= KAMA40.

Both portfolios use identical execution/risk rules:
- next-4H-open entry
- realistic gap-through stop handling
- minimum 1% fill-to-stop distance
- 1% equity risk budget
- maximum single-position notional 100% of equity
- maximum total gross exposure 100% of equity
- maximum 6 open positions
- maximum 5% risk heat
- existing rs_top2 ranking; missing RS is null/unrankable and sorts last
- existing TP1, Profit Protect, runner and 30-bar timeout

Run 25/50/75/100 bps. Primary report is 50 bps.

Report candidate/reject counts, accepted trades, total R, expectancy, PF, win rate, marked return, max drawdown, max gross exposure, yearly results, top-trade removal, symbol concentration and trade-set differences.

This 30-symbol result is only a screen because KAMA was selected from a multi-probe tournament on the same universe. Promotion requires canonical 131-symbol PIT validation or forward shadow logging.
