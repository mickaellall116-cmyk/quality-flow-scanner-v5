# 3H Hybrid — forward-window live arbiter baseline (2026-09-26)

**Status: RESEARCH ONLY. Not approved, not deployed. V5.4, V3.7, and the forward test are untouched.**

## Spec reference (followed exactly, nothing invented)

- `pine_2h3h_backtest/README.md` + `pine_2h3h_backtest/run_2h3h_watchlist.py`
- Canonical `pine_backtest.py` imported **unmodified**: Hybrid `pine_buy_signal`
  (confirmedBuy OR breakoutBuy OR readyBuy), `gen_pine_trades`,
  `simulate_portfolio`, `summarize`, `COSTS`, `RISK_PCT`, `_outcome`.
- 1H bars (regular session, prepost=False) resampled **within** each trading day;
  bins anchored at 09:30 (3H: 09:30/12:30/15:30 + 15:30–16:00 stub kept);
  OHLCV = first/max/min/last/sum.
- Indicator lookbacks in **bars**, identical to 4H (EMA 9/21/55/200, ATR 14,
  ADX 14, vol SMA20, breakout 10). Unmodified transfer — no 3H tuning.
- Portfolio: $10k, 1%/trade, max 5 concurrent, 5% portfolio risk, next-bar-open
  entries, stop-first ties, gap-below-stop skips. Costs: 4bps and 25bps.
- Symbols with <200 3H bars fail closed (none this run; SPCX 219 bars, 0 trades).
- Universe: QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX, ASTX, BBAI,
  NIO, HOOD, AMD (Mike's 14-name watchlist).

Data: cached 1H through 2026-09-23 15:30 ET + fresh yfinance 1H pull merged
through **2026-09-25 15:30 ET** (14 new bars/ticker; Sep 24–25 sessions).
Cache copies were worked on in /tmp — no repo files modified.

## Forward-test log window (read-only, `v54_forward/forward_test.jsonl`)

- 94 lines: **26 signals**, 63 events, 5 closes
- First signal bar: **2026-09-15T10:30:00-04:00**
- Last signal bar: **2026-09-25T16:00:00-04:00**
- (Context only — the log is 4H V5.4 signals; it defines the window, not the trades.)

## A. Full-window reproduction (sanity check)

| cost | trades | win | expectancy | PF | return | max DD |
|------|-------:|----:|-----------:|---:|-------:|-------:|
| 4bps | 371 | 51.8% | **+0.221R** | 1.35 | +93.7% | 34.9% |
| 25bps | 371 | 50.7% | **+0.158R** | 1.24 | +55.8% | 39.3% |

Matches the historical 3H result **exactly** (371 trades, +0.158R @25bps).
Pipeline is faithful; the gate reference is +0.15R @25bps.

## B. Forward-window live arbiter (entry_time ≥ 2026-09-15)

| cost | trades | win | expectancy | PF |
|------|-------:|----:|-----------:|---:|
| 25bps | **0** | — | — | — |
| 4bps | **0** | — | — | — |

- Last 3H hybrid trade entered **2026-09-14 12:30 ET** (HOOD, stop).
- Trades since Sep 1: 4. Trades since Sep 15: **0**.
- The system averages ~0.5 trades/day across all 14 names; an 8-trading-day
  window with zero signals is within normal variation, not a malfunction.

## Plain-English verdict

**The +0.15R gate cannot be evaluated on forward data yet — n=0.**
This is neither a pass nor a fail. There is simply no forward evidence:
the 3H hybrid fired zero signals during the entire V5.4 forward-test window
to date. The historical +0.158R stands unreplicated and unrefuted.

What this means for the arbiter: the 3H system is low-frequency
(~30–40 trades per ticker over 3 years). A meaningful forward read needs
weeks to months of paper sidecar operation, not days. Recommend re-checking
at the ~50-signal V5.4 checkpoint (late Oct 2026) alongside the other live
arbiters (FVG sidecar, lone-wolf overlay, ADX shadow).

Raw results: `research_notes/3h_hybrid_forward_baseline_2026-09-26.json`
