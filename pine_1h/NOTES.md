# Pine V3.6 on 1H — transfer test notes (2026-09-18)

Question: does the Pine V3.6 edge (entries +0.329R, full system +0.195R on 4H)
transfer to 1H bars with the strategy logic unmodified?

## Method
- `pine_backtest_1h.py` imports `pine_backtest.py` — entries, exits,
  indicators, portfolio sim byte-identical. Only the bar feed changes.
- Indicator lookbacks kept in BARS (EMA 9/21/55/200, ATR 14, vol SMA20,
  breakout 10) = ~4x less clock time than 4H. Parameters were tuned for 4H;
  this is an unmodified-transfer test, not a re-tuned 1H system.
- yfinance 1H, regular session for stocks (~6.5 bars/day), 24h crypto.
  Window: stocks 2023-10-19→2026-09-17, crypto 2024-09-19→2026-09-18
  (yfinance 1h crypto history shorter). All 51 UX51 symbols usable, none dropped.
- Same portfolio: $10k, 1%/trade, max 5 concurrent, 5% portfolio risk,
  next-bar-open entries, stop-first ties, 4bps and 25bps costs.

## Results

| | 4H baseline (263 trades) | 1H (1,394 trades) |
|---|---|---|
| Expectancy | +0.195R | +0.009R (4bps) / −0.167R (25bps) |
| Profit factor | 1.27 | 1.01 / 0.83 |
| Total return | +35.3% | −53.7% / −88.3% |
| Max drawdown | 35.2% | 66.7% / 88.5% |
| Win rate | 44.9% | 46.3% / 44.5% |
| TP1 hit | 47.5% | 49.1% |
| Avg hold | 18.1 bars | 19.4 bars (median 40.5h, mean 81h) |
| Exit mix | stop 247, ema55 16 | stop 1327, ema55 67 |

## Verdict: NO — the edge does not transfer to 1H unmodified.
Win rate and TP1 rate look similar, but expectancy collapses to ~zero
(negative at realistic costs). 5.3x the trade count: the strategy churns —
95% of exits (1327/1394) are stops. Same-bar lookbacks on 1H see ~4x less
clock time, so 4H "trends" become 1H noise and the ATR stops get chewed.

## Caveats
- Different window than the 4H run (longer for stocks); the result is so
  decisively flat-to-negative that window choice doesn't rescue it.
- Session-only stock bars (no pre/post market) — same convention as the 4H
  session-aligned bars.
- A re-tuned 1H variant (longer lookbacks, wider stops) is a different
  question and would need its own pre-specified + out-of-sample validation.
  Not attempted here.

Files: `fetch_1h.py`, `fetch_1h_log.json`, `cache/h1_*.pkl` (51),
`pine_backtest_1h.py`, `pine_1h_results.json`.
