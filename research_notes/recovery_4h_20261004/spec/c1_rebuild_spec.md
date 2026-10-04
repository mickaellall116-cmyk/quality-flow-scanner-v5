# CORRECTED CANONICAL C1 REBUILD — SPECIFICATION
**Recovery pre-run package — Phase B**
**Date:** 2026-10-04 | **Branch:** `recovery-4h-20261004`
**Status:** SPECIFICATION ONLY — no performance data opened. ChatGPT review required before any corrected performance run.

---

## 1. Objective

Rebuild the as-studied C1 (V3.6 hybrid) stack on **corrected session-anchored 4H bars**
(Phase A canonical constructor), producing a side-by-side delta against the
prior evidence families. This isolates how much of every prior result was
bar-construction artifact vs genuine signal.

## 2. Complete C1 stack (frozen parameters)

### 2.1 Signal generation (`pine_backtest.pine_buy_signal`, evaluated on completed bar i)
- **Indicators:** EMA(9/21/55/200), ATR, ATR_base = ATR.rolling(50).mean,
  ATR_ratio = ATR/ATR_base, ADX, vol_ma = Volume.rolling(20).mean.
- **Warmup:** 215 bars before first signal evaluation.
- **Confirmed:** close > e21, e21 > e55, close > e200, trendScore ≥ 4,
  volume > vol_ma, NOT hot (close ≤ e9 + 1.5×ATR).
  trendScore = int(e9>e21) + int(e21>e55) + int(close>e200) + int(adx>25) + int(atr_ratio>1).
- **Breakout buy:** e21>e55, close>e200 (trend_bull), adx>20, atr_ratio>0.85
  (strong_trend), close > max(High, prior 10 bars), volume > vol_ma, not hot.
- **Ready buy:** prev close<e21, prev close>e55, prev e21>e55, prev atr_ratio>0.85,
  close>e21, trendScore ≥ 3, volume > vol_ma, not hot.
- Signal = confirmed OR breakout_buy OR ready_buy.

### 2.2 Trade management (`pine_backtest.gen_pine_trades`)
- **Entry:** next 4H bar open after signal bar. Skip if entry ≤ stop (gap guard).
- **Stop:** signal close − 1.5×ATR.
- **TP1:** entry + 2.0×ATR (50% filled as intrabar limit when high ≥ TP1).
- **Runner:** after TP1, trailing stop = max(stop, close − 2.5×ATR), updated at bar close.
- **Exits (close-evaluated → next bar open):** close < runner (stop) |
  close < e55 (ema55-break) | (e21<e55 and close<e200) (ema55-bear).
- **R accounting:** blended — 50% at TP1 R + 50% at final-exit R (if TP1 hit),
  else 100% final-exit R.

### 2.3 Portfolio stack (`pine_stack.simulate_stack`, C1 = ranking + sector cap + S4)
- **Ranking:** when candidates contest slots at the same timestamp, rank by
  20-bar return minus SPY; take top 2 (`use_ranking=True`).
- **Sector cap:** max 2 concurrent positions per sector (`sector_cap=True`,
  frozen sector map).
- **Slots:** max 5 concurrent positions.
- **Sizing:** 1% risk per trade (RISK_PCT=0.01); shares = risk_dollars / (entry − stop).
- **Heat:** ~5% portfolio heat cap at risk.
- **S4 drawdown gate:** marked equity ≤ 90% of peak → risk halves;
  marked equity ≥ 95% of peak → risk restores. Checked BEFORE sizing each entry.
- **Costs:** canonical 4bps + 25bps primary + 5bps/10bps stress (Phase C).

### 2.4 What changes vs prior runs
**ONLY the bar constructor:** Path 3 (per-day origin, `fetch_4h.py`) or Path 1
(legacy) → Path 2 (session-anchored canonical). Every parameter, threshold,
indicator length, and portfolio rule above stays byte-identical.

## 3. Side-by-side delta format (to be populated AFTER ChatGPT review)

For each prior evidence family (240-trade C1 baseline, corrected-grid replay,
TOP-vs-BROAD legs), report:

| Metric | Prior (old bars) | Corrected (canonical bars) | Δ |
|--------|------------------|---------------------------|---|
| Trade count | | | |
| Entries changed (count + % of trades) | — | | |
| Exits changed (count + reason-shift table) | — | | |
| Expectancy (R) @25bps | | | |
| Profit factor | | | |
| Total return % | | | |
| Max drawdown % | | | |
| Longest losing streak (trades) | | | |

**Materiality map:** for each changed trade, classify cause:
(a) bar-construction (different OHLC → different signal/level/fill),
(b) ranking/displacement (same signals, different admission),
(c) S4 interaction (different equity path → different gate state),
(d) other (document).

## 4. Gating

- Phase B spec is COMPLETE with this document.
- Corrected performance runs are NOT authorized by this package.
- After ChatGPT reviews the full pre-run package, Phase B execution proceeds
  ONLY on explicit authorization, producing the delta table above.
