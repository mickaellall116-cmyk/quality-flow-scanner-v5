# V1.7 Backtest — Pre-Specified Spec (frozen 2026-09-18, before any test)

## Goal
Head-to-head backtest of Mike's older Pine indicator **"Quality Flow System V1.7 AUTO Hybrid"**
(reference source: `v1_7_reference.pine`, copied verbatim from Mike's message) against the
V3.6 4H baseline (263 trades, +0.195R, PF 1.27, +35.3%, DD 35.2%, 4bps).

## Scope / hard boundaries
- LOCAL-ONLY. New namespace `pine_v17/`. No existing file modified.
- No GitHub, no forward test, no live signals, no money, Mike's TV scripts untouched.
- V5.4 forward test untouched. No shorts, no hedges.

## Universe / window / costs (identical to V3.6 baseline)
- UX51 = the same 51 symbols as `pine_backtest.py::UNIVERSE_X`.
- 4H bars 2024-09-16 → 2026-09-14 (same cache: `backtest_cache/v3/h4_*.pkl`).
- Cost legs: 4bps AND 25bps. $10k start, 1% risk/trade, max 5 concurrent positions,
  5% portfolio risk cap, next-bar-open entries, gap-below-stop entries skipped.
- NOTE (pre-specified simplification): ALL 51 symbols run on the **STOCK branch**
  (stockAdxMin=15, stockRunnerATR=3.5, cooldown 7, max 3 entries/trend-leg, stock weak
  exits). Per-symbol TV asset-type detection (crypto/index-like) is not reproduced;
  this keeps the comparison to V3.6 apples-to-apples on the same universe.
- The script's `default_qty_value=10` (% of equity) is a TV strategy-tester setting;
  the backtest uses the established 1%-risk convention for comparability.

## V1.7 logic implemented (all defaults: useAutoMode/useEarlyEntry/useAdaptive200/
## useSmartExits/useExitConfirm=true, useMFIExit=false)
Indicators: EMA21/55/50/200, ATR(14 Wilder), ATRbase=SMA50, ATRratio, DMI/ADX(14),
CMF(20) with money-flow multiplier, MFI(14, hlc3), OBV + EMA5/20.
Entries (evaluated on completed bar i, filled at open of i+1):
- confirmedBuy = trendBull & breakout(20) & cmf>0 & MFI 40–75 & ATRratio≥0.85 &
  ADX≥15 & close>EMA200*0.98 & tradeAllowed & cooldownOK & entryLimitOK & ext<3.2
- stockEarly = earlyAllowed & ADX≥15 & slopeOK & (controlledPullback|reclaim) & bullishCandle
  where earlyAllowed = trendBull & cmf>0 & MFI 40–75 & ATRratio≥0.85 &
  close>EMA200*0.98 & tradeAllowed & cooldownOK & entryLimitOK & ext<3.2
- stockRegime tradeAllowed = trendRegime OR (trendBull & slopeOK & ATRratio≥0.85);
  trendRegime = ADX≥15 & ATRratio≥0.85 & |EMA21−EMA55|/close > 0.006
- Trend-leg control: entriesThisTrend reset on EMA21/55 crossover; cooldown 7 bars
  between entries; max 3 entries per trend leg. pyramiding=0 (one position/symbol).
Exits:
- TP1: 50% at signal-close + 1.5×ATR, real intrabar LIMIT (fills at exact TP1 on high≥TP1).
- After TP1: stop moves to breakeven, then trails at close − ATR×smartRunnerATR
  (3.5×ATR; 4.5×ATR in strong trend = EMA21>EMA55 & ADX≥20). Ratchets up only.
- Close-evaluated exits → filled at NEXT bar open:
  cmfExit (CMF<0 & falling 2 bars), trendExit (2 consecutive closes < EMA55),
  stopExit (close < finalStop — note: close-evaluated, NOT intrabar),
  stockWeakExit (not strong trend & (CMF<0 | close<EMA21)).
- In strong trend only stopExit can exit (smartExit gate).
- useExitConfirm=true: exit requires smartExit true on TWO consecutive bars.
- MFI exit is OFF (useMFIExit=false) — not implemented.

## Approximations vs TradingView (documented)
1. Session-aligned 4H bars (same as V3.6 backtest), not TV regular 4H.
2. Breakeven uses the actual fill price (next-bar open); Pine uses signal-bar close.
3. TP1 level fixed from signal-bar ATR; Pine recomputes live.
4. `math.max(high-low, syminfo.mintick)` → epsilon 1e-9 (equivalent for liquid stocks).
5. All symbols on STOCK branch (see above).

## Metrics per cost leg
trades, win%, expectancy R, PF, return%, maxDD%, avg winner/loser R, TP1 hit rate,
avg hold (bars), stop-out%, exit-reason mix, EARLY vs confirmed trade split.

## Decision rule (pre-specified)
- Baseline sanity: V3.6 rerun must reproduce ≈+0.195R (already known; not rerun here —
  baseline numbers taken from `pine_backtest_results.json`).
- If V1.7 expectancy > +0.195R AND maxDD ≤ 40% → run 2022 4H bear-market validation
  (same Dukascopy-cache framework as the exit study) before any conclusion.
- Else verdict = "V1.7 does not beat V3.6", no 2022 run.
- Verdict options: (a) V1.7 beats V3.6 on both windows → candidate for Mike to decide
  (NOT a recommendation to change his live script); (b) V1.7 loses → keep V3.6;
  (c) inconclusive → say why.
- No parameter tuning, no second chances: one faithful run, one verdict.
