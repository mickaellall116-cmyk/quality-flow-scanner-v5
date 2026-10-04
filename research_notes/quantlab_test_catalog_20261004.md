# QuantLab (@quant_labde) — Full Test Catalog

Distilled from all 160 reels posted by QUANTLAB | Algorithmic Trading
(Germany, ~15.6k followers) between ~2026-08-12 and 2026-10-04.
Source: Instagram captions read 2026-10-04 (videos not watched).
Mike's directive: catalogue is for ChatGPT to brainstorm replication
candidates. Nothing here is verified evidence — Instagram captions, no raw
data or code. Replicate on our own data before trusting any claim.

His house method (worth copying regardless of results): every concept is
tested against RANDOM baselines, costs included, R-multiples, drawdown,
parameter-robustness, Monte Carlo, look-ahead-bias checks.

## Concepts tested (with his reported numbers where given)

### Fair Value Gap / ICT cluster
1. ~100,000 FVGs on Nasdaq — do FVGs work or do traders see what they want?
2. Do FVGs actually get filled? (fill-rate test)
3. 8 different FVG strategies tested head-to-head
4. Inverted FVG after a liquidity sweep — does it create edge? (2026-10-04)
5. ICT Silver Bullet tested on historical Nasdaq — claims real edge (2026-09-06)
6. ICT Kill Zones — do the time windows give edge?
7. AMD model test
8. SMT divergence — does it work?
9. 3,771 Order Blocks on Gold

### Levels / price structure
10. Point of Control: 55.2% touched vs 52.6% random; 1,096 trades, +10.2R
    before costs, edge mostly gone after costs
11. Asian range breakout: Nasdaq 64% continuation vs 61% random hour;
    strategy −55R after costs, 80R max drawdown
12. Previous day high/low (Gold and Nasdaq)
13. Previous week high/low on Nasdaq
14. Nasdaq opening gaps: fill rate, post-open behavior
15. Round numbers — 6+ years of Nasdaq data
16. Fibonacci — edge or chart illusion?

### Breakouts / momentum / trend
17. 16,000+ breakouts tested by condition — which are worth trading
18. Does high volume confirm breakouts? (tested on Nasdaq)
19. Volatility compression — does it predict expansions?
20. Session Momentum (NY open): +1,029% vs +227% buy & hold, ~40% exposure
21. Break & retest on Gold
22. Two momentum/trend research papers tested with real data
23. Asset comparison: Nasdaq, Gold, BTC, EURUSD, GBPUSD across
    momentum/trend/breakout/mean-reversion/volatility
24. Trading AGAINST the trend — tested
25. Removing complexity: what survives when you strip everything?

### Time / session effects
26. First 5-minute candle: can it predict the next 6 hours? (multiple tests,
    incl. 7 years of Nasdaq data)
27. NY Open 5-min candle system: +$9,141 live in one week (his claim)
28. What happens at the 9:30 NY open (volume/volatility mechanics)
29. Can the first hours predict the last hour?
30. Can yesterday predict today?
31. Does time of day matter? Tested across sessions
32. Timeframes compared: same strategy 5-min → 4H; higher TFs better,
    reason = costs, not noise
33. First week of the month on Gold: 19 years of data
34. January effect on Gold: 7 years

### Indicators / patterns
35. EVERY indicator tested (megatest)
36. Golden Cross (50/200 EMA) on Nasdaq
37. Bollinger Bands on Gold — edge? (two tests)
38. Which EMA cross works best on Gold
39. Hammer candle reversal test
40. Engulfing candles test
41. VWAP: 3 approaches; look-ahead bias fix took +89.8R → +17R
42. VWAP deviations edge test
43. RSI oversold: immediate entry (−0.17R) vs RSI recovery (−0.16R)
    vs price V-shape (−0.16R) — all flat
44. Is RSI the most useless indicator?
45. Gamma flip explained

### Money management / robustness methodology
46. Take-profit levels tested against data — which R target best
47. Can a negative RR be profitable?
48. 70% win rate can still lose money
49. Reversing a losing strategy (long↔short)
50. Reversing a profitable strategy
51. Random/coin-flip trading baseline
52. 10,000 strategies tested — brutal result
53. 40 parameter combinations — best setup wasn't the trusted one
54. Monte Carlo stress testing explainer
55. "Tested against random" methodology explainer
56. Why backtests look perfect in the past
57. Why profitable-in-backtest fails live (execution/spreads)

### Gold-specific
58. Gold: after a >2% day, next day continuation or reversal?
59. Gold new ATH: continuation or crash?
60. Gold massive candle: mean reversion? 8+ years
61. Gold volatility predicting trends
62. Simple EMA vs Gold

### Event / exogenous
63. FOMC volatility test
64. News candles mechanics
65. Market moving seconds before major news
66. Does the weather affect the Nasdaq? (sun/rain/cloud)
67. COT data: edge or overrated?

### Microstructure / education
68. What is liquidity, really
69. What liquidity sweeps do (EURUSD 2020–2026 reversal test)
70. Why you get stopped out (stop placement)
71. Circuit breakers
72. Order book behind candles

## Muse's ranking for our research (posted to bridge 2026-10-04)

1. FVG fill stats on QQQ — same concept our sidecar is built on; decides
   whether the premise survives our data.
2. ICT Silver Bullet / kill zones — mechanical time windows; he claims edge;
   we've never tested time-of-day.
3. Take-profit levels — we already hold the MFE data; direct question for
   the ~50-signal checkpoint diagnostic.
4. Breakouts + volume confirmation — replicable on 4H; his 16k-breakout test.
5. Everything else: idea queue, not priority.

Mike approved replicating the tests (not using his numbers) — starting with
FVG fill stats on QQQ.
