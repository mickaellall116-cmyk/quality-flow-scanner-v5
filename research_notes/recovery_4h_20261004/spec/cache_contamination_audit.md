# GAP 2 RESOLUTION — Full Cache Contamination Audit
**Recovery pre-run package REV 2 | Date:** 2026-10-04 | **Branch:** `recovery-4h-20261004`
**Responds to:** ChatGPT review 5985221338, gap 2 (full-cache scope)
**Method:** Every `backtest_cache/v3/h4_*.pkl` equity file audited bar-by-bar.
Off-grid = bar NOT at 09:30 or 13:30 America/New_York.

---

## Per-symbol results

45 equity files audited. **Every file is contaminated.** 44,731 total bars;
14,986 off-grid (33.5%).

| Symbol | Total bars | Off-grid bars | % |
|--------|-----------|---------------|---|
| AMZN | 995 | 334 | 33.6% |
| APP | 995 | 334 | 33.6% |
| ARM | 995 | 334 | 33.6% |
| ASTS | 995 | 334 | 33.6% |
| CRM | 995 | 334 | 33.6% |
| CRWD | 995 | 334 | 33.6% |
| HOOD | 995 | 334 | 33.6% |
| INTC | 995 | 334 | 33.6% |
| LRCX | 995 | 334 | 33.6% |
| LUNR | 995 | 334 | 33.6% |
| MELI | 995 | 334 | 33.6% |
| MU | 995 | 334 | 33.6% |
| NET | 995 | 334 | 33.6% |
| NFLX | 995 | 334 | 33.6% |
| NU | 995 | 334 | 33.6% |
| PLTR | 995 | 334 | 33.6% |
| PYPL | 995 | 334 | 33.6% |
| QCOM | 995 | 334 | 33.6% |
| QQQ | 995 | 334 | 33.6% |
| SHOP | 995 | 334 | 33.6% |
| SOFI | 995 | 334 | 33.6% |
| SPY | 995 | 334 | 33.6% |
| TSLA | 995 | 334 | 33.6% |
| AAPL | 993 | 332 | 33.4% |
| AMAT | 993 | 332 | 33.4% |
| AMD | 993 | 332 | 33.4% |
| ARKK | 993 | 332 | 33.4% |
| AVGO | 993 | 332 | 33.4% |
| COIN | 993 | 332 | 33.4% |
| DDOG | 993 | 332 | 33.4% |
| F | 993 | 332 | 33.4% |
| GOOGL | 993 | 332 | 33.4% |
| IWM | 993 | 332 | 33.4% |
| META | 993 | 332 | 33.4% |
| MRNA | 993 | 332 | 33.4% |
| MSFT | 993 | 332 | 33.4% |
| MSTR | 993 | 332 | 33.4% |
| NIO | 993 | 332 | 33.4% |
| NVDA | 993 | 332 | 33.4% |
| PFE | 993 | 332 | 33.4% |
| RKLB | 993 | 332 | 33.4% |
| SMCI | 993 | 332 | 33.4% |
| SMH | 993 | 332 | 33.4% |
| SNOW | 993 | 332 | 33.4% |
| XLF | 993 | 332 | 33.4% |
| **TOTAL** | **44,731** | **14,986** | **33.5%** |

Crypto files (`h4_BTC-USD.pkl` etc.): 00/04/08/12/16/20 UTC grid — aligned,
no delta (verified in Phase A byte-identity report).

## Trade-level impact (240-trade C1 baseline)

Source: `pine_execution/c1_corrected_baseline_20261003.json` trade ledger.

- **82 of 240 trades (34.2%)** have entry timestamps inside EST off-grid periods
  (2024-11-04 → 2025-03-07, 2025-11-03 → 2026-03-06).
- These 82 trades were evaluated on bars covering [08:30,12:30) EST instead of
  [09:30,13:30) EST — different OHLCV inputs to signal, stop, TP1, and exit logic.

## Scope statement

This is NOT "332 AAPL bars." Every equity symbol in the baseline cache is
affected at ~33.5%. Roughly one-third of all bars and one-third of all trades
in the 240-trade baseline were computed on the wrong grid. The contamination
is systematic and uniform, not idiosyncratic.

The corrected canonical rebuild (Phase B) will re-cut ALL bars on the
session-anchored grid. No selective repair.
