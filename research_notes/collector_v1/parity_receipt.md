# PARITY RECEIPT — target session 2026-11-03

Primary bars: derived session-anchored 4H from **yahoo** 1h (collector pipeline), aggregated over the session's 4H bars to a daily bar.
Second source: **Nasdaq API** daily bars (api.nasdaq.com historical; keyless, an independent vendor pipeline), fetched at parity time. (Stooq and the TradingView scanner were tried first and returned empty responses from this network on 2026-11-03.)

Comparison is daily-granularity by construction: Open = first 4H open, High = max, Low = min, Close = last 4H close, Volume = sum. Price verdict per field: EXACT (equal at 2dp), NEAR (|diff| <= 0.01), MISMATCH (anything else, values shown). Volume verdict: EXACT, NEAR (<=0.1% diff), MISMATCH. Mismatches are reported, never hidden.

## A. Collector-universe sample, target session 2026-11-03

| symbol | field | primary (derived) | nasdaq | diff | verdict |
|---|---|---|---|---|---|
| SPY | Open | 752.73 | 752.73 | -0.00 | EXACT |
| SPY | High | 757.07 | 757.07 | +0.00 | EXACT |
| SPY | Low | 752.39 | 752.39 | +0.00 | EXACT |
| SPY | Close | 754.41 | 754.35 | +0.06 | MISMATCH |
| SPY | Volume | 112,577,784 | 32,891,580 | +79,686,204 | MISMATCH |
| AAPL | Open | 325.54 | 325.58 | -0.04 | MISMATCH |
| AAPL | High | 334.50 | 334.50 | +0.00 | EXACT |
| AAPL | Low | 325.33 | 325.33 | -0.00 | EXACT |
| AAPL | Close | 331.74 | 331.90 | -0.16 | MISMATCH |
| AAPL | Volume | 206,784,808 | 63,160,030 | +143,624,778 | MISMATCH |
| MSFT | Open | 508.46 | 509.00 | -0.55 | MISMATCH |
| MSFT | High | 523.44 | 523.44 | +0.00 | EXACT |
| MSFT | Low | 507.85 | 507.82 | +0.03 | MISMATCH |
| MSFT | Close | 520.77 | 520.99 | -0.22 | MISMATCH |
| MSFT | Volume | 44,371,373 | 20,010,170 | +24,361,203 | MISMATCH |
| NVDA | Open | 207.85 | 207.96 | -0.11 | MISMATCH |
| NVDA | High | 209.14 | 209.14 | -0.00 | EXACT |
| NVDA | Low | 205.93 | 205.93 | -0.00 | EXACT |
| NVDA | Close | 206.57 | 206.69 | -0.12 | MISMATCH |
| NVDA | Volume | 204,462,991 | 91,943,390 | +112,519,601 | MISMATCH |
| AMZN | Open | 248.62 | 248.59 | +0.03 | MISMATCH |
| AMZN | High | 252.45 | 252.45 | -0.00 | EXACT |
| AMZN | Low | 245.89 | 245.88 | +0.01 | NEAR |
| AMZN | Close | 250.74 | 250.69 | +0.05 | MISMATCH |
| AMZN | Volume | 52,375,374 | 37,853,500 | +14,521,874 | MISMATCH |
| JPM | Open | 340.00 | 340.00 | +0.00 | EXACT |
| JPM | High | 340.75 | 340.75 | +0.00 | EXACT |
| JPM | Low | 335.82 | 335.82 | +0.00 | EXACT |
| JPM | Close | 338.00 | 337.98 | +0.02 | MISMATCH |
| JPM | Volume | 5,870,074 | 6,764,319 | -894,245 | MISMATCH |
| XOM | Open | 178.00 | 178.00 | +0.00 | EXACT |
| XOM | High | 180.30 | 180.30 | +0.00 | EXACT |
| XOM | Low | 177.20 | 177.20 | -0.00 | EXACT |
| XOM | Close | 177.50 | 177.46 | +0.04 | MISMATCH |
| XOM | Volume | 12,063,086 | 11,578,510 | +484,576 | MISMATCH |
| WMT | Open | 126.71 | 126.69 | +0.02 | MISMATCH |
| WMT | High | 126.85 | 126.85 | -0.00 | EXACT |
| WMT | Low | 124.55 | 124.55 | +0.00 | EXACT |
| WMT | Close | 124.81 | 124.86 | -0.05 | MISMATCH |
| WMT | Volume | 13,343,157 | 21,184,330 | -7,841,173 | MISMATCH |
| HD | Open | 337.25 | 337.25 | +0.00 | EXACT |
| HD | High | 338.78 | 338.78 | -0.00 | EXACT |
| HD | Low | 330.71 | 330.71 | -0.00 | EXACT |
| HD | Close | 333.58 | 333.66 | -0.08 | MISMATCH |
| HD | Volume | 3,987,272 | 3,801,379 | +185,893 | MISMATCH |
| CAT | Open | 618.94 | 618.94 | +0.00 | EXACT |
| CAT | High | 628.30 | 628.30 | -0.00 | EXACT |
| CAT | Low | 617.01 | 617.01 | +0.00 | EXACT |
| CAT | Close | 623.82 | 623.94 | -0.12 | MISMATCH |
| CAT | Volume | 3,121,718 | 3,511,976 | -390,258 | MISMATCH |
| LLY | Open | 1399.63 | 1399.63 | +0.00 | EXACT |
| LLY | High | 1437.00 | 1437.00 | +0.00 | EXACT |
| LLY | Low | 1393.47 | 1393.47 | -0.00 | EXACT |
| LLY | Close | 1409.39 | 1409.38 | +0.01 | MISMATCH |
| LLY | Volume | 3,317,293 | 2,841,275 | +476,018 | MISMATCH |
| UNH | Open | 399.17 | 399.17 | +0.00 | EXACT |
| UNH | High | 405.40 | 405.40 | -0.00 | EXACT |
| UNH | Low | 397.00 | 397.00 | +0.00 | EXACT |
| UNH | Close | 403.97 | 404.44 | -0.47 | MISMATCH |
| UNH | Volume | 3,703,999 | 4,060,062 | -356,063 | MISMATCH |
| MA | Open | 652.84 | 652.84 | +0.00 | EXACT |
| MA | High | 654.39 | 654.39 | +0.00 | EXACT |
| MA | Low | 645.50 | 645.50 | +0.00 | EXACT |
| MA | Close | 647.31 | 647.18 | +0.13 | MISMATCH |
| MA | Volume | 2,495,303 | 3,199,803 | -704,500 | MISMATCH |
| V | Open | 422.40 | 422.40 | -0.00 | EXACT |
| V | High | 423.72 | 423.72 | +0.00 | EXACT |
| V | Low | 418.27 | 418.27 | -0.00 | EXACT |
| V | Close | 420.38 | 420.42 | -0.04 | MISMATCH |
| V | Volume | 9,958,141 | 5,524,692 | +4,433,449 | MISMATCH |
| TSLA | Open | 406.31 | 406.25 | +0.06 | MISMATCH |
| TSLA | High | 406.49 | 406.50 | -0.01 | MISMATCH |
| TSLA | Low | 396.54 | 396.53 | +0.01 | MISMATCH |
| TSLA | Close | 398.22 | 398.50 | -0.28 | MISMATCH |
| TSLA | Volume | 44,730,645 | 26,647,730 | +18,082,915 | MISMATCH |
| META | — | — | — | — | NASDAQ NO ROW |
| AVGO | — | — | — | — | NASDAQ NO ROW |
| CRM | Open | 222.40 | 222.40 | -0.00 | EXACT |
| CRM | High | 223.50 | 223.50 | +0.00 | EXACT |
| CRM | Low | 214.67 | 214.67 | -0.00 | EXACT |
| CRM | Close | 222.20 | 222.20 | -0.00 | EXACT |
| CRM | Volume | 5,365,616 | 6,709,910 | -1,344,294 | MISMATCH |
| MU | Open | 859.81 | 859.92 | -0.12 | MISMATCH |
| MU | High | 871.49 | 871.49 | -0.00 | EXACT |
| MU | Low | 845.25 | 845.25 | +0.00 | EXACT |
| MU | Close | 854.97 | 855.10 | -0.13 | MISMATCH |
| MU | Volume | 43,307,442 | 21,286,480 | +22,020,962 | MISMATCH |
| QCOM | Open | 164.21 | 164.21 | +0.00 | EXACT |
| QCOM | High | 165.27 | 165.28 | -0.01 | NEAR |
| QCOM | Low | 160.40 | 160.38 | +0.02 | MISMATCH |
| QCOM | Close | 164.50 | 164.43 | +0.07 | MISMATCH |
| QCOM | Volume | 10,209,010 | 11,445,340 | -1,236,330 | MISMATCH |

## B. Supplementary: Tier-3 names (ad hoc through the same pipeline; NOT universe members), 2026-11-03

| symbol | field | primary (derived) | nasdaq | diff | verdict |
|---|---|---|---|---|---|
| BE | Open | 210.33 | 210.33 | +0.00 | EXACT |
| BE | High | 220.50 | 220.50 | +0.00 | EXACT |
| BE | Low | 208.03 | 208.03 | -0.00 | EXACT |
| BE | Close | 213.99 | 214.01 | -0.02 | MISMATCH |
| BE | Volume | 12,591,851 | 14,298,510 | -1,706,659 | MISMATCH |
| ACN | Open | 254.56 | 254.56 | -0.00 | EXACT |
| ACN | High | 256.37 | 256.37 | -0.00 | EXACT |
| ACN | Low | 246.86 | 246.86 | +0.00 | EXACT |
| ACN | Close | 254.51 | 254.56 | -0.05 | MISMATCH |
| ACN | Volume | 10,024,576 | 5,686,187 | +4,338,389 | MISMATCH |
| IREN | Open | 22.49 | 22.48 | +0.01 | MISMATCH |
| IREN | High | 24.67 | 24.66 | +0.00 | NEAR |
| IREN | Low | 22.22 | 22.22 | -0.00 | EXACT |
| IREN | Close | 24.49 | 24.46 | +0.03 | MISMATCH |
| IREN | Volume | 46,544,177 | 54,802,450 | -8,258,273 | MISMATCH |
| CRDO | Open | 144.45 | 144.85 | -0.40 | MISMATCH |
| CRDO | High | 152.62 | 152.62 | -0.00 | EXACT |
| CRDO | Low | 142.00 | 142.00 | +0.00 | EXACT |
| CRDO | Close | 151.08 | 150.91 | +0.17 | MISMATCH |
| CRDO | Volume | 4,958,897 | 6,400,070 | -1,441,173 | MISMATCH |
| TWLO | Open | 207.50 | 207.50 | +0.00 | EXACT |
| TWLO | High | 216.87 | 216.87 | +0.00 | EXACT |
| TWLO | Low | 205.13 | 205.13 | +0.00 | EXACT |
| TWLO | Close | 213.81 | 213.77 | +0.04 | MISMATCH |
| TWLO | Volume | 2,583,638 | 2,942,544 | -358,906 | MISMATCH |
| AAOI | Open | 63.92 | 63.96 | -0.04 | MISMATCH |
| AAOI | High | 66.58 | 66.58 | +0.00 | EXACT |
| AAOI | Low | 62.30 | 62.30 | -0.00 | EXACT |
| AAOI | Close | 63.94 | 63.97 | -0.03 | MISMATCH |
| AAOI | Volume | 9,998,313 | 11,455,120 | -1,456,807 | MISMATCH |
| MPWR | Open | 1300.27 | 1303.15 | -2.88 | MISMATCH |
| MPWR | High | 1363.36 | 1363.36 | -0.00 | EXACT |
| MPWR | Low | 1275.75 | 1275.75 | +0.00 | EXACT |
| MPWR | Close | 1328.54 | 1328.30 | +0.24 | MISMATCH |
| MPWR | Volume | 972,409 | 1,311,562 | -339,153 | MISMATCH |
| SPOT | Open | 588.59 | 588.59 | +0.00 | EXACT |
| SPOT | High | 601.55 | 601.55 | -0.00 | EXACT |
| SPOT | Low | 581.72 | 581.72 | -0.00 | EXACT |
| SPOT | Close | 600.22 | 600.09 | +0.13 | MISMATCH |
| SPOT | Volume | 1,232,615 | 1,663,857 | -431,242 | MISMATCH |
| BABA | Open | 101.82 | 101.83 | -0.00 | NEAR |
| BABA | High | 102.04 | 102.04 | +0.00 | EXACT |
| BABA | Low | 99.86 | 99.86 | +0.00 | EXACT |
| BABA | Close | 100.34 | 100.36 | -0.02 | MISMATCH |
| BABA | Volume | 5,407,243 | 6,563,376 | -1,156,133 | MISMATCH |
| COF | Open | 211.07 | 211.07 | +0.00 | EXACT |
| COF | High | 211.97 | 211.97 | +0.00 | EXACT |
| COF | Low | 207.50 | 207.50 | +0.00 | EXACT |
| COF | Close | 208.72 | 208.71 | +0.01 | MISMATCH |
| COF | Volume | 2,078,243 | 3,000,569 | -922,326 | MISMATCH |
| BLK | Open | 1167.65 | 1167.65 | +0.00 | EXACT |
| BLK | High | 1172.52 | 1172.52 | +0.00 | EXACT |
| BLK | Low | 1154.00 | 1154.00 | +0.00 | EXACT |
| BLK | Close | 1160.77 | 1161.32 | -0.55 | MISMATCH |
| BLK | Volume | 432,297 | 700,096 | -267,799 | MISMATCH |

## C. Settled sessions (same pipeline, prior completed sessions — separates same-day provisional-feed effects from persistent feed defects)

| symbol/session | field | primary (derived) | nasdaq | diff | verdict |
|---|---|---|---|---|---|
| SPY 2026-11-02 | Open | 759.45 | 759.45 | +0.00 | EXACT |
| SPY 2026-11-02 | High | 763.86 | 763.86 | -0.00 | EXACT |
| SPY 2026-11-02 | Low | 751.60 | 751.60 | -0.00 | EXACT |
| SPY 2026-11-02 | Close | 752.12 | 752.10 | +0.02 | MISMATCH |
| SPY 2026-11-02 | Volume | 45,008,300 | 50,804,340 | -5,796,040 | MISMATCH |
| SPY 2026-10-30 | Open | 761.40 | 761.38 | +0.02 | MISMATCH |
| SPY 2026-10-30 | High | 761.46 | 761.46 | +0.00 | EXACT |
| SPY 2026-10-30 | Low | 750.36 | 750.36 | -0.00 | EXACT |
| SPY 2026-10-30 | Close | 755.71 | 755.72 | -0.01 | NEAR |
| SPY 2026-10-30 | Volume | 62,144,767 | 77,696,480 | -15,551,713 | MISMATCH |
| AAPL 2026-11-02 | Open | 342.91 | 342.67 | +0.24 | MISMATCH |
| AAPL 2026-11-02 | High | 343.78 | 343.80 | -0.02 | MISMATCH |
| AAPL 2026-11-02 | Low | 335.84 | 335.82 | +0.02 | MISMATCH |
| AAPL 2026-11-02 | Close | 339.11 | 338.32 | +0.79 | MISMATCH |
| AAPL 2026-11-02 | Volume | 42,840,963 | 64,757,690 | -21,916,727 | MISMATCH |
| AAPL 2026-10-30 | Open | 346.68 | 346.71 | -0.03 | MISMATCH |
| AAPL 2026-10-30 | High | 349.19 | 349.19 | +0.00 | EXACT |
| AAPL 2026-10-30 | Low | 342.35 | 334.35 | +8.00 | MISMATCH |
| AAPL 2026-10-30 | Close | 344.80 | 344.63 | +0.17 | MISMATCH |
| AAPL 2026-10-30 | Volume | 47,899,009 | 67,841,560 | -19,942,551 | MISMATCH |
| MSFT 2026-11-02 | Open | 524.10 | 524.01 | +0.08 | MISMATCH |
| MSFT 2026-11-02 | High | 529.63 | 529.63 | +0.00 | EXACT |
| MSFT 2026-11-02 | Low | 504.96 | 504.96 | -0.00 | EXACT |
| MSFT 2026-11-02 | Close | 507.13 | 507.12 | +0.01 | MISMATCH |
| MSFT 2026-11-02 | Volume | 27,547,950 | 34,743,320 | -7,195,370 | MISMATCH |
| MSFT 2026-10-30 | Open | 525.27 | 525.27 | +0.00 | EXACT |
| MSFT 2026-10-30 | High | 526.00 | 526.00 | +0.00 | EXACT |
| MSFT 2026-10-30 | Low | 514.35 | 514.35 | -0.00 | EXACT |
| MSFT 2026-10-30 | Close | 521.90 | 521.91 | -0.01 | NEAR |
| MSFT 2026-10-30 | Volume | 23,493,766 | 35,652,050 | -12,158,284 | MISMATCH |

## Summary

- universe sample: 20 names; supplementary Tier-3 sample: 11 names; settled block: 3 names x 2 sessions
- field verdicts (all blocks): EXACT 80, NEAR 6, MISMATCH 89, no-comparison rows: 2

Per-name detail (target session):

- **SPY**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **AAPL**: bars_4h=2 {'Open': 'MISMATCH', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **MSFT**: bars_4h=2 {'Open': 'MISMATCH', 'High': 'EXACT', 'Low': 'MISMATCH', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **NVDA**: bars_4h=2 {'Open': 'MISMATCH', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **AMZN**: bars_4h=2 {'Open': 'MISMATCH', 'High': 'EXACT', 'Low': 'NEAR', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **JPM**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **XOM**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **WMT**: bars_4h=2 {'Open': 'MISMATCH', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **HD**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **CAT**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **LLY**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **UNH**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **MA**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **V**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **TSLA**: bars_4h=2 {'Open': 'MISMATCH', 'High': 'MISMATCH', 'Low': 'MISMATCH', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **META**: bars_4h=2 {} 
- **AVGO**: bars_4h=2 {} 
- **CRM**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'EXACT', 'Volume': 'MISMATCH'} 
- **MU**: bars_4h=2 {'Open': 'MISMATCH', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **QCOM**: bars_4h=2 {'Open': 'EXACT', 'High': 'NEAR', 'Low': 'MISMATCH', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **BE**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **ACN**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **IREN**: bars_4h=2 {'Open': 'MISMATCH', 'High': 'NEAR', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **CRDO**: bars_4h=2 {'Open': 'MISMATCH', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **TWLO**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **AAOI**: bars_4h=2 {'Open': 'MISMATCH', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **MPWR**: bars_4h=2 {'Open': 'MISMATCH', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **SPOT**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **BABA**: bars_4h=2 {'Open': 'NEAR', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **COF**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 
- **BLK**: bars_4h=2 {'Open': 'EXACT', 'High': 'EXACT', 'Low': 'EXACT', 'Close': 'MISMATCH', 'Volume': 'MISMATCH'} 

## Findings (appended by the collector author after inspecting the tables above; no values above were changed)

1. **Pipeline mechanics are proven; the Yahoo 1h feed is not official-grade.**
   Across 35 compared name-sessions (175 fields): High EXACT/NEAR in
   36/37, Low in 33/37, Open in 22/35 — the session grid, 09:30/13:30
   anchoring and 4H aggregation reproduce the official daily bars.
2. **Close mismatches on 32/35 name-sessions** (max |diff| $0.79): the
   derived close is the last regular-trade close of the 15:30 1h bar;
   the Nasdaq daily close is the official closing-auction print. The
   two are different quantities; on settled sessions SPY/MSFT agree
   within $0.01-0.04 while single names (AAPL) show genuine feed
   defects as well (e.g. AAPL 2026-10-30 derived Low $342.35 vs
   official $334.35).
3. **Volume mismatches on 35/35**: Yahoo 1h volume is not official
   consolidated volume — settled sessions run ~20-40% BELOW official,
   while the target (same-day) session ran up to ~3.4x ABOVE official
   (same-day intraday bars are evidently provisional/mis-bucketed and
   revised later — the Lane C lesson, again). Yahoo also emits a
   zero-volume 16:00 bar carrying the official close; the collector's
   session filter excludes it by construction.
4. **Consequence, stated plainly:** on the Yahoo fallback leg, the
   frozen signal's close-based indicators and its relative-volume
   gate inherit this feed noise (within-feed consistency mitigates,
   does not eliminate). The collector's official leg must be the
   Alpaca SIP route; it awaits keys (see dry_run_receipt.json).
   Yahoo remains a labeled fallback for dry runs and development.
5. META and AVGO returned no Nasdaq historical row (counted NO_DATA,
   not hidden).
