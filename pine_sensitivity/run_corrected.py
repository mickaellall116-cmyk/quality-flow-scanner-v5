#!/usr/bin/env python3
"""Research: corrected trendScore (int-cast) versions of Hybrid and live-config.

The canonical pine_backtest.py computes
    score = (r["e9"] > r["e21"]) + ...   # numpy.bool_ + numpy.bool_ -> numpy.bool_ (OR)
so score is True/False, never 0..5, and `score >= 4` / `score >= 3` are
always False. confirmedBuy and readyBuy (and Aggressive's earlyBuy) are
dead in every backtest run to date; all measured trades are breakout-only.

This driver monkey-patches a corrected signal (int-cast, matching Pine's
`trendScore += cond ? 1 : 0`) and reruns. Frozen files untouched.
"""
import sys, os, json, time
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_sensitivity")
sys.path.insert(0, BASE)
sys.path.insert(0, OUTDIR)
import pine_backtest as pb
from run_liveconfig import add_live_columns

_EARLY_LAST = {}
_CUR_SYM = None


def tscore(r, close):
    return (int(r["e9"] > r["e21"]) + int(r["e21"] > r["e55"])
            + int(close > r["e200"]) + int(r["adx"] > 25)
            + int(r["atr_ratio"] > 1))


def _common(df, i):
    r = df.iloc[i]
    rp = df.iloc[i - 1]
    close, vol = r["Close"], r["Volume"]
    d = {}
    d["volume_ok"] = vol > r["vol_ma"]
    d["safe"] = not (close > r["e9"] + r["atr"] * pb.HOT_ATR)
    d["trend_bull"] = r["e21"] > r["e55"] and close > r["e200"]
    d["strong_trend"] = r["adx"] > 20 and r["atr_ratio"] > 0.85
    d["score"] = tscore(r, close)
    d["breakout"] = close > df["High"].iloc[i - pb.BREAKOUT_BARS:i].max()
    d["ready_prev"] = rp["Close"] < rp["e21"] and rp["Close"] > rp["e55"] \
        and rp["e21"] > rp["e55"] and rp["atr_ratio"] > 0.85
    d["r"] = r
    d["close"] = close
    return d


def corrected_hybrid(df, i):
    r0 = df.iloc[i]
    if pd.isna(r0["e200"]) or pd.isna(r0["atr_base"]) or pd.isna(r0["adx"]):
        return False
    c = _common(df, i)
    r, close = c["r"], c["close"]
    confirmed = close > r["e21"] and r["e21"] > r["e55"] and close > r["e200"] \
        and c["score"] >= 4 and c["volume_ok"] and c["safe"]
    breakout_buy = c["trend_bull"] and c["strong_trend"] and c["breakout"] \
        and c["volume_ok"] and c["safe"]
    ready_buy = c["ready_prev"] and close > r["e21"] and c["score"] >= 3 \
        and c["volume_ok"] and c["safe"]
    return bool(confirmed or breakout_buy or ready_buy)


def corrected_live(df, i):
    global _EARLY_LAST, _CUR_SYM
    r0 = df.iloc[i]
    if pd.isna(r0["e200"]) or pd.isna(r0["atr_base"]) or pd.isna(r0["adx"]):
        return False
    c = _common(df, i)
    r, close = c["r"], c["close"]
    confirmed = close > r["e21"] and r["e21"] > r["e55"] and close > r["e200"] \
        and c["score"] >= 4 and c["volume_ok"] and c["safe"]
    breakout_buy = c["trend_bull"] and c["strong_trend"] and c["breakout"] \
        and c["volume_ok"] and c["safe"]
    ready_buy = c["ready_prev"] and close > r["e21"] and c["score"] >= 3 \
        and c["volume_ok"] and c["safe"]
    early_raw = r["e9"] > r["e21"] and close > r["e55"] and r["atr_ratio"] > 0.85
    aggressive = early_raw and close > r["e21"] and c["score"] >= 3 \
        and c["volume_ok"] and c["safe"]
    last_e = _EARLY_LAST.get(_CUR_SYM, -10 ** 9)
    early_buy = aggressive and (i - last_e > 10)
    if early_buy:
        _EARLY_LAST[_CUR_SYM] = i
    pullback_buy = c["trend_bull"] and bool(r["nearBuyZone"]) and close >= r["e21"] \
        and r["adx"] > 18 and c["volume_ok"] and c["safe"]
    sweep_buy = c["trend_bull"] and bool(r["bullSweep"]) and close > r["e21"] \
        and c["volume_ok"] and c["safe"]
    return bool(confirmed or breakout_buy or ready_buy or early_buy
                or pullback_buy or sweep_buy)


_orig_gen = pb.gen_pine_trades


def gen_with_live(sym, df):
    global _CUR_SYM
    _CUR_SYM = sym
    _EARLY_LAST[sym] = -10 ** 9
    return _orig_gen(sym, add_live_columns(df))


def run(name, signal_fn, gen_fn=None):
    pb.pine_buy_signal = signal_fn
    pb.gen_pine_trades = gen_fn or _orig_gen
    t0 = time.time()
    rows, trades = pb.run_universe(pb.UNIVERSE_X, "UX51", "4h")
    dt = time.time() - t0
    rec = {"config": name, "seconds": round(dt, 1)}
    for r in rows:
        rec[r["cost"]] = {
            "trades": r["trades"], "win_rate_pct": r["win_rate_pct"],
            "expectancy_r": r["expectancy_net_r"], "profit_factor": r["profit_factor"],
            "return_pct": r["total_return_pct"], "max_dd_pct": r["max_drawdown_pct"],
        }
        print(f"{name} [{r['cost']}]: n={r['trades']} win={r['win_rate_pct']}% "
              f"exp={r['expectancy_net_r']}R PF={r['profit_factor']} "
              f"ret={r['total_return_pct']}% dd={r['max_drawdown_pct']}%", flush=True)
    return rec


def main():
    out = []
    out.append(run("CORRECTED Hybrid", corrected_hybrid))
    out.append(run("CORRECTED live (Aggr+PB+SW)", corrected_live, gen_with_live))
    with open(os.path.join(OUTDIR, "corrected_results.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("wrote pine_sensitivity/corrected_results.json")


if __name__ == "__main__":
    main()
