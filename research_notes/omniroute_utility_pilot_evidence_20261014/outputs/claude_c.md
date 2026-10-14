Methodological flaws:

1. Look-ahead leakage in feature construction. Features were normalized using the mean and standard deviation of the full 2019-2024 sample, so every observation embeds information from its own future. Any signal built on those features is partly trading on data that was not available at the time, inflating returns and Sharpe.

2. Multiple testing / in-sample selection. 240 parameter combinations were grid-searched and the best was selected on the same 2019-2024 period used to report performance. With 240 trials, a Sharpe of 2.1 can arise from selection alone; with no untouched holdout and no trial-count adjustment (e.g., deflated Sharpe), the reported figure is an upper bound, not an estimate.

3. Survivorship bias. Using today's index constituent list backfilled to 2019 excludes firms that were dropped, acquired, or failed during the period, systematically flattering the universe's returns.

4. No transaction costs. Returns are gross of commissions and slippage; a 4-hour strategy trades frequently, so costs are first-order and could erase much or all of the reported edge.

5. In-sample results presented as expected live performance. The 38% CAGR and 2.1 Sharpe are the optimized in-sample maximum under the flaws above; nothing in the claim supports the confidence statement about live trading.

Evidence required to make the claim credible: point-in-time constituent membership and feature computation using only data available at each timestamp; a pre-registered parameter set or an untouched out-of-sample / walk-forward evaluation; disclosure of the number of trials with a multiple-testing adjustment; results net of realistic commissions, spread, and slippage; and the same metrics reported separately for in-sample and out-of-sample periods.
