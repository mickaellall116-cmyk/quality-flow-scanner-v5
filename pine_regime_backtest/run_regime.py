"""Priority 4: Market-regime conditioning — descriptive measurement study.

Question: WHEN is the baseline 4H Hybrid edge strongest/weakest? Descriptive
buckets only — NO new filter, no threshold tuning, no model.

Setup: 14-stock watchlist, 4H bars Oct 2023–Sep 2026, canonical pine_buy_signal
+ gen_pine_trades (pine_backtest imported UNMODIFIED), frozen Mode B exits,
25bps costs. Baseline rerun in-study (never reuse numbers across studies).

Regime labels are computed from DAILY SPY/QQQ/VIX at the signal date
(pre-declared buckets, no tuning):
  - SPY above/below daily 200 EMA (ewm span 200)
  - QQQ above/below daily 200 EMA
  - 200 EMA rising vs falling (e200 vs 20 trading days earlier)
  - VIX level: low <20, mid 20-30, high >30
  - Market momentum: SPY 50-day return positive vs negative
  - Realized vol: SPY 20-day stdev of log returns above/below sample median
  - Bull/bear/sideways: bull = close>e200 & rising; bear = close<e200 & falling;
    else sideways

Verdict standard: is any expectancy difference LARGE and PERSISTENT (across
years) enough to justify a future filter? YES / UNCLEAR / NO.
Research only. No frozen files modified.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_regime_backtest")
CACHEDIR = os.path.join(OUTDIR, "cache")
os.makedirs(CACHEDIR, exist_ok=True)
sys.path.insert(0, BASE)
import pine_backtest as pb

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
H4CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
COST = 0.0025  # 25 bps


def get_daily(ticker, path):
    if os.path.exists(path):
        return pd.read_pickle(path)
    import yfinance as yf
    df = yf.download(ticker, start="2021-01-01", end="2026-09-26",
                     auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df.to_pickle(path)
    return df


def build_regime():
    spy = get_daily("SPY", os.path.join(CACHEDIR, "d_SPY.pkl"))
    qqq = get_daily("QQQ", os.path.join(CACHEDIR, "d_QQQ.pkl"))
    vix = get_daily("^VIX", os.path.join(CACHEDIR, "d_VIX.pkl"))
    reg = pd.DataFrame(index=spy.index)
    reg["spy_close"] = spy["Close"]
    reg["e200"] = spy["Close"].ewm(span=200, adjust=False).mean()
    reg["e200_20ago"] = reg["e200"].shift(20)
    reg["spy_above200"] = reg["spy_close"] > reg["e200"]
    reg["e200_rising"] = reg["e200"] > reg["e200_20ago"]
    qe200 = qqq["Close"].ewm(span=200, adjust=False).mean()
    reg["qqq_above200"] = qqq["Close"].reindex(reg.index) > qe200.reindex(reg.index)
    reg["mom50"] = spy["Close"] / spy["Close"].shift(50) - 1
    logret = np.log(spy["Close"] / spy["Close"].shift(1))
    reg["rv20"] = logret.rolling(20).std()
    reg["rv20_high"] = reg["rv20"] > reg["rv20"].median()
    v = vix["Close"].reindex(reg.index).ffill()
    reg["vix"] = v
    reg["vix_regime"] = pd.cut(v, [-np.inf, 20, 30, np.inf],
                               labels=["low<20", "mid20-30", "high>30"])
    reg["tri"] = np.where(reg["spy_above200"] & reg["e200_rising"], "bull",
                  np.where(~reg["spy_above200"] & ~reg["e200_rising"], "bear",
                           "sideways"))
    return reg.dropna()


def gen_baseline():
    trades = []
    for sym in WATCHLIST:
        path = os.path.join(H4CACHE, f"h4_{sym}.pkl")
        df = pd.read_pickle(path)
        df = pb.add_pine_indicators(df)
        tr, _ = pb.gen_pine_trades(sym, df)
        trades.extend(tr)
        print(f"  {sym}: {len(tr)} trades", flush=True)
    return trades


def bucket_stats(trades):
    t = pd.DataFrame(trades)
    n = len(t)
    wins = t[t["net_r"] > 0]
    gw = wins["net_r"].sum()
    gl = -t[t["net_r"] <= 0]["net_r"].sum()
    return {
        "n": n,
        "expectancy_r": round(float(t["net_r"].mean()), 3),
        "win_rate_pct": round(len(wins) / n * 100, 1),
        "profit_factor": round(gw / gl, 2) if gl > 0 else None,
        "total_r": round(float(t["net_r"].sum()), 2),
    }


def main():
    print("building regime frame...", flush=True)
    reg = build_regime()
    print(f"regime frame: {reg.index.min().date()} -> {reg.index.max().date()}", flush=True)
    print("generating baseline trades...", flush=True)
    trades = gen_baseline()
    # net R at 25bps
    for t in trades:
        t["net_r"] = pb._outcome(t["entry"], t["stop"], t["exit"], COST)[2]
        sig_date = pd.to_datetime(t["signal_time"]).tz_localize(None).normalize()
        # last daily bar on/before the signal date
        loc = reg.index.searchsorted(sig_date, side="right") - 1
        if loc < 0:
            t["_reg"] = None
            continue
        r = reg.iloc[loc]
        t["_reg"] = {
            "spy200": "above" if r["spy_above200"] else "below",
            "qqq200": "above" if r["qqq_above200"] else "below",
            "e200slope": "rising" if r["e200_rising"] else "falling",
            "vix": str(r["vix_regime"]),
            "mom50": "pos" if r["mom50"] > 0 else "neg",
            "rv20": "high" if r["rv20_high"] else "low",
            "tri": r["tri"],
            "year": sig_date.year,
            "sig_date": sig_date.date().isoformat(),
        }
    trades = [t for t in trades if t["_reg"]]
    print(f"tagged trades: {len(trades)}", flush=True)

    total_r = sum(t["net_r"] for t in trades)
    results = {"baseline": bucket_stats(trades),
               "total_r": round(total_r, 2),
               "buckets": {}, "year_xtab": {}}

    dims = ["spy200", "qqq200", "e200slope", "vix", "mom50", "rv20", "tri"]
    for dim in dims:
        groups = {}
        keys = sorted({t["_reg"][dim] for t in trades})
        for k in keys:
            sub = [t for t in trades if t["_reg"][dim] == k]
            s = bucket_stats(sub)
            s["share_of_total_r_pct"] = round(s["total_r"] / total_r * 100, 1) if total_r else 0
            groups[k] = s
        results["buckets"][dim] = groups

    # persistence: cross-tab each dim x year for expectancy
    for dim in dims:
        xt = {}
        for yr in sorted({t["_reg"]["year"] for t in trades}):
            xt[str(yr)] = {}
            for k in sorted({t["_reg"][dim] for t in trades}):
                sub = [t for t in trades if t["_reg"]["year"] == yr and t["_reg"][dim] == k]
                if len(sub) >= 5:
                    xt[str(yr)][k] = {"n": len(sub),
                                      "exp_r": round(float(np.mean([x["net_r"] for x in sub])), 3)}
                else:
                    xt[str(yr)][k] = {"n": len(sub), "exp_r": None}
        results["year_xtab"][dim] = xt

    with open(os.path.join(OUTDIR, "regime_results.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("wrote regime_results.json", flush=True)
    return results


if __name__ == "__main__":
    main()
