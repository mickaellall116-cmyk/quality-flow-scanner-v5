#!/usr/bin/env python3
"""Research: backtest Mike's LIVE TradingView config as a signal-only delta.

Live config (per 2026-09-20 screenshots + pasted script):
  Entry Mode = Aggressive, Use Pullback as Real Entry = true,
  Use Sweep as Real Entry = true, Use FVG as Real Entry = false.

Signal: confirmedBuy or breakoutBuy or readyBuy or earlyBuy or pullbackBuy or sweepBuy
Trade management: identical to pine_backtest.py (documented approximations).
Frozen strategy file is never edited; everything is monkey-patched here.

Approximations vs Pine (documented):
 1. earlyBuy 10-bar throttle evaluated only on bars where the loop checks
    signals (flat periods). Pine updates lastEarlyBar on every bar, so this
    replica can allow a post-exit early signal slightly sooner than Pine.
 2. Same session-aligned 4h bars / TP1 / cost conventions as pine_backtest.py.
"""
import sys, os, json, time
import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_sensitivity")
sys.path.insert(0, BASE)
import pine_backtest as pb

SWEEP_LB = 20
BUY_ZONE_W = 0.35
NEAR_ZONE_ATR = 0.50

_EARLY_LAST = {}
_CUR_SYM = None


def add_live_columns(df):
    out = df.copy()
    n = len(out)
    low, high, close = out["Low"].to_numpy(), out["High"].to_numpy(), out["Close"].to_numpy()
    e21 = out["e21"].to_numpy(); atr = out["atr"].to_numpy()

    sweep_ref = out["Low"].rolling(SWEEP_LB).min().shift(1).to_numpy()
    out["bullSweep"] = (low < sweep_ref) & (close > sweep_ref)

    # FVG state machine (Pine order: FVG block runs before the entry engine each bar)
    last_fvg_lo, last_fvg_hi = np.nan, np.nan
    use_fvg = np.zeros(n, dtype=bool)
    bz_lo = np.zeros(n); bz_hi = np.zeros(n); near = np.zeros(n, dtype=bool)
    for i in range(n):
        if i >= 2 and low[i] > high[i - 2]:  # bullFVG = low > high[2]
            last_fvg_lo, last_fvg_hi = high[i - 2], low[i]
        c, a, e = close[i], atr[i], e21[i]
        uf = (not np.isnan(last_fvg_lo) and abs(c - last_fvg_hi) <= a * 3
              and last_fvg_hi <= c * 1.08)
        use_fvg[i] = uf
        ez_lo, ez_hi = e - a * BUY_ZONE_W, e + a * BUY_ZONE_W
        zlo = min(ez_lo, last_fvg_lo) if uf else ez_lo
        zhi = max(ez_hi, last_fvg_hi) if uf else ez_hi
        bz_lo[i], bz_hi[i] = zlo, zhi
        near[i] = (abs(c - zhi) <= a * NEAR_ZONE_ATR
                   or abs(c - zlo) <= a * NEAR_ZONE_ATR
                   or (zlo <= c <= zhi))
    out["nearBuyZone"] = near
    return out


def live_buy_signal(df, i):
    """Mike's live signal: Hybrid components + earlyBuy + pullbackBuy + sweepBuy."""
    global _EARLY_LAST, _CUR_SYM
    r = df.iloc[i]
    rp = df.iloc[i - 1]
    if pd.isna(r["e200"]) or pd.isna(r["atr_base"]) or pd.isna(r["adx"]):
        return False
    close, vol = r["Close"], r["Volume"]
    volume_ok = vol > r["vol_ma"]
    hot = close > r["e9"] + r["atr"] * pb.HOT_ATR
    safe = not hot
    trend_bull = r["e21"] > r["e55"] and close > r["e200"]
    strong_trend = r["adx"] > 20 and r["atr_ratio"] > 0.85
    score = (r["e9"] > r["e21"]) + (r["e21"] > r["e55"]) + (close > r["e200"]) \
        + (r["adx"] > 25) + (r["atr_ratio"] > 1)
    breakout = close > df["High"].iloc[i - pb.BREAKOUT_BARS:i].max()
    ready_prev = rp["Close"] < rp["e21"] and rp["Close"] > rp["e55"] \
        and rp["e21"] > rp["e55"] and rp["atr_ratio"] > 0.85

    confirmed = close > r["e21"] and r["e21"] > r["e55"] and close > r["e200"] \
        and score >= 4 and volume_ok and safe
    breakout_buy = trend_bull and strong_trend and breakout and volume_ok and safe
    ready_buy = ready_prev and close > r["e21"] and score >= 3 and volume_ok and safe

    # Aggressive: earlyBuy with 10-bar throttle
    early_raw = r["e9"] > r["e21"] and close > r["e55"] and r["atr_ratio"] > 0.85
    aggressive = early_raw and close > r["e21"] and score >= 3 and volume_ok and safe
    last_e = _EARLY_LAST.get(_CUR_SYM, -10 ** 9)
    early_buy = aggressive and (i - last_e > 10)
    if early_buy:
        _EARLY_LAST[_CUR_SYM] = i

    # extraEntry from his toggles: pullback + sweep (FVG toggle is off)
    pullback_buy = trend_bull and bool(r["nearBuyZone"]) and close >= r["e21"] \
        and r["adx"] > 18 and volume_ok and safe
    sweep_buy = trend_bull and bool(r["bullSweep"]) and close > r["e21"] \
        and volume_ok and safe

    return bool(confirmed or breakout_buy or ready_buy or early_buy
                or pullback_buy or sweep_buy)


_orig_gen = pb.gen_pine_trades


def gen_with_live(sym, df):
    global _CUR_SYM
    _CUR_SYM = sym
    _EARLY_LAST[sym] = -10 ** 9
    df2 = add_live_columns(df)
    return _orig_gen(sym, df2)


def main():
    pb.pine_buy_signal = live_buy_signal
    pb.gen_pine_trades = gen_with_live
    t0 = time.time()
    rows, trades = pb.run_universe(pb.UNIVERSE_X, "UX51", "4h")
    dt = time.time() - t0
    rec = {"config": "LIVE Aggressive+pullback+sweep", "seconds": round(dt, 1)}
    for r in rows:
        rec[r["cost"]] = {
            "trades": r["trades"], "win_rate_pct": r["win_rate_pct"],
            "expectancy_r": r["expectancy_net_r"], "profit_factor": r["profit_factor"],
            "return_pct": r["total_return_pct"], "max_dd_pct": r["max_drawdown_pct"],
            "avg_hold_bars": r["avg_hold_bars"],
            "exit_reasons": r["exit_reasons"],
        }
        print(f"LIVE [{r['cost']}]: n={r['trades']} win={r['win_rate_pct']}% "
              f"exp={r['expectancy_net_r']}R PF={r['profit_factor']} "
              f"ret={r['total_return_pct']}% dd={r['max_drawdown_pct']}%", flush=True)
    with open(os.path.join(OUTDIR, "liveconfig_results.json"), "w") as f:
        json.dump(rec, f, indent=1)
    print(f"done in {dt:.0f}s; wrote pine_sensitivity/liveconfig_results.json")


if __name__ == "__main__":
    main()
