# V1.1 Backtest — Pre-Specified Spec (frozen 2026-09-18, before any test)

## Goal
Head-to-head backtest of Mike's older Pine indicator **"Quality Flow System V1.1 - Better
Runner Exits"** (reference source: `v1_1_reference.pine`, copied verbatim from Mike's
message) against the V3.6 4H baseline (263 trades, +0.195R, PF 1.27, +35.3%, DD 35.2%, 4bps).

## Scope / hard boundaries
- LOCAL-ONLY. New namespace `pine_v11/`. No existing file modified (pine_backtest.py,
  pine_v17/, pine_entry_ablation/, pine_expansion/, pine_exit_fix/, pine_1h/, v54_*, backtest.py).
- No GitHub, no forward test, no live signals, no money, Mike's TV scripts untouched.
- V5.4 forward test untouched. No shorts, no hedges, 4H only.
- The script's `default_qty_value=10` (% of equity) is a TV strategy-tester setting;
  the backtest uses the established 1%-risk convention for comparability.

## Universe / window / costs (identical to V3.6 baseline)
- UX51 = the same 51 symbols as `pine_backtest.py::UNIVERSE_X`.
- 4H bars 2024-09-16 → 2026-09-14 (same cache: `backtest_cache/v3/h4_*.pkl`).
- Cost legs: 4bps AND 25bps. $10k start, 1% risk/trade, max 5 concurrent positions,
  5% portfolio risk cap, next-bar-open entries, gap-below-stop entries skipped.
- Volume required for CMF/MFI (same cache conventions as pine_backtest.py).

## V1.1 logic implemented (exactly as coded, nothing more)
Indicators: EMA21/55, ATR(14 Wilder), ATRbase=SMA50, ATRratio, CMF(20) with
money-flow multiplier, MFI(14, hlc3), OBV + EMA5/20 (computed but only OBV plotted;
OBV is NOT used in any rule — entry/exit gates use only what the script uses).

Entry (evaluated on completed bar i, filled at open of i+1):
- buySignal = trendBull & breakout(20) & flowOK & mfiOK & atrOK
  - trendBull = EMA21 > EMA55
  - breakout = close > highest(high, 20)[1]  (prior 20-bar high, offset 1)
  - flowOK = CMF > 0
  - mfiOK = 40 ≤ MFI ≤ 75
  - atrOK = ATRratio ≥ 0.85
- NOTE: NO ADX filter, NO EMA200 filter, NO volume filter, NO cooldown,
  NO early entries, NO regime gate — exactly as the script is written.
- pyramiding=0: no entry while a position is open (one position per symbol).

Exits:
- TP1: 50% at signal-close + 1.5×ATR, real intrabar LIMIT (fills at exact TP1 on high≥TP1).
- Before TP1: stop = signal-close − 2.0×ATR (close-evaluated, not intrabar — the script
  never passes a stop to strategy.exit; only TP1 is a limit order).
- After TP1: stop moves to breakeven (actual fill price, not signal close), then
  finalStop = max(breakeven, close − 3.5×ATR). Ratchets up only.
- Close-evaluated exits → filled at NEXT bar open:
  cmfExit (CMF<0 & falling 2 bars), trendExit (2 consecutive closes < EMA55),
  stopExit (close < finalStop).
- MFI exit is OFF (useMFIExit=false) — not implemented.
- Single-bar exit confirmation (V1.1 has NO useExitConfirm; exit fires the same bar
  the condition is true, filled next bar open).
- Same-bar tie priority for reason attribution: stop > cmf > trend2.

## Approximations vs TradingView (documented)
1. Session-aligned 4H bars (same as V3.6 backtest), not TV regular 4H.
2. Breakeven uses the actual fill price (next-bar open); Pine uses signal-bar close.
3. TP1 level fixed from signal-bar ATR; Pine recomputes live.
4. `math.max(high-low, syminfo.mintick)` → epsilon 1e-9 (equivalent for liquid stocks).
5. `strategy.entry` fills at next-bar open (same convention as the V1.7 study).

## Metrics per cost leg
trades, win%, expectancy R, PF, return%, maxDD%, avg winner/loser R, TP1 hit rate,
avg hold (bars), stop-out%, exit-reason mix.

## Adoption gate
- If V1.1 beats +0.195R expectancy WITH DD ≤ 40%: run the same 2022 4H bear-market
  validation (Dukascopy cache in v6_short_v2/cache/ + pine_exit_fix/cache_2022/)
  before any conclusion.
- If it does not beat the baseline, no 2022 run — verdict is "V1.1 does not beat V3.6".
- Verdict options: beats on both windows (candidate for Mike to decide — NOT a
  recommendation to change his live script), loses (keep V3.6), inconclusive (say why).
