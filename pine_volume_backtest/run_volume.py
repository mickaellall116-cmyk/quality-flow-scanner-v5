"""Priority 8: Relative volume and liquidity — measurement study.

Question: does volume/liquidity at entry affect baseline 4H Hybrid expectancy?

Setup: 14-stock watchlist, 4H bars Oct 2023-Sep 2026, canonical
pine_buy_signal + gen_pine_trades (pine_backtest imported UNMODIFIED),
frozen Mode B exits, 25bps costs. Baseline rerun in-study (never reuse
numbers across studies).

Volume metrics computed at the signal bar (pre-declared buckets, no tuning):
  - rvol: signal-bar volume / 20-bar mean volume -> low(<0.8) / med(0.8-1.5) / high(>1.5)
  - dollar_vol: signal-bar volume * close -> pooled terciles
  - avg_dollar_vol: 20-bar mean of volume*close -> pooled terciles
  - expansion: signal-bar volume / 10-bar mean volume -> pooled quartiles

Per bucket: n, expectancy R, win rate, PF, total R, share of total R.
Persistence: cross-tab the most interesting dimension by year.

Verdict standard: a broad bucket clearly better/worse across years -> MAYBE
(with a future filter direction). Flat -> NO. A volume filter is only
recommended if the data clearly supports it.
Research only. No frozen files modified.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_volume_backtest")
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, BASE)
import pine_backtest as pb

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
H4CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
COST = 0.0025  # 25 bps


def gen_tagged():
    trades = []
    for sym in WATCHLIST:
        path = os.path.join(H4CACHE, f"h4_{sym}.pkl")
        df = pd.read_pickle(path)
        df = pb.add_pine_indicators(df)
        tr, _ = pb.gen_pine_trades(sym, df)
        vol = df["Volume"].astype(float)
        close = df["Close"].astype(float)
        vol_ma20 = vol.rolling(20).mean()
        vol_ma10 = vol.rolling(10).mean()
        dvol = vol * close
        dvol_ma20 = dvol.rolling(20).mean()
        for t in tr:
            t["net_r"] = pb._outcome(t["entry"], t["stop"], t["exit"], COST)[2]
            st = pd.to_datetime(t["signal_time"])
            # locate the signal bar in the dataframe
            try:
                loc = df.index.get_loc(st)
            except KeyError:
                # nearest prior bar
                loc = df.index.searchsorted(st, side="right") - 1
            if isinstance(loc, slice):
                loc = loc.start
            if loc < 20 or pd.isna(vol_ma20.iloc[loc]):
                t["_vol"] = None
                continue
            v = vol.iloc[loc]
            rvol = v / vol_ma20.iloc[loc]
            exp = v / vol_ma10.iloc[loc]
            t["_vol"] = {
                "rvol": float(rvol),
                "expansion": float(exp),
                "dollar_vol": float(dvol.iloc[loc]),
                "avg_dollar_vol": float(dvol_ma20.iloc[loc]),
                "year": st.year,
                "symbol": sym,
            }
            trades.append(t)
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
        "profit_factor": round(float(gw / gl), 2) if gl > 0 else None,
        "total_r": round(float(t["net_r"].sum()), 2),
    }


def assign_buckets(trades):
    # terciles / quartiles pooled across all trades
    dvol = np.array([t["_vol"]["dollar_vol"] for t in trades])
    advol = np.array([t["_vol"]["avg_dollar_vol"] for t in trades])
    exp = np.array([t["_vol"]["expansion"] for t in trades])
    dv_t = np.quantile(dvol, [1 / 3, 2 / 3])
    adv_t = np.quantile(advol, [1 / 3, 2 / 3])
    exp_q = np.quantile(exp, [0.25, 0.5, 0.75])
    for t in trades:
        v = t["_vol"]
        r = v["rvol"]
        v["rvol_bucket"] = "low<0.8" if r < 0.8 else ("med0.8-1.5" if r <= 1.5 else "high>1.5")
        d = v["dollar_vol"]
        v["dollar_vol_bucket"] = "T1_low" if d <= dv_t[0] else ("T2_mid" if d <= dv_t[1] else "T3_high")
        a = v["avg_dollar_vol"]
        v["avg_dollar_vol_bucket"] = "T1_low" if a <= adv_t[0] else ("T2_mid" if a <= adv_t[1] else "T3_high")
        e = v["expansion"]
        v["expansion_bucket"] = ("Q1" if e <= exp_q[0] else
                                 "Q2" if e <= exp_q[1] else
                                 "Q3" if e <= exp_q[2] else "Q4")
    return {"dollar_vol_terciles": [float(x) for x in dv_t],
            "avg_dollar_vol_terciles": [float(x) for x in adv_t],
            "expansion_quartiles": [float(x) for x in exp_q]}


def main():
    print("generating baseline trades + volume tags...", flush=True)
    trades = gen_tagged()
    print(f"tagged trades: {len(trades)}", flush=True)
    cuts = assign_buckets(trades)
    total_r = sum(t["net_r"] for t in trades)
    results = {"baseline": bucket_stats(trades),
               "total_r": round(total_r, 2),
               "bucket_cuts": cuts,
               "buckets": {}, "year_xtab": {}}

    dims = ["rvol_bucket", "dollar_vol_bucket", "avg_dollar_vol_bucket", "expansion_bucket"]
    for dim in dims:
        groups = {}
        keys = sorted({t["_vol"][dim] for t in trades})
        for k in keys:
            sub = [t for t in trades if t["_vol"][dim] == k]
            s = bucket_stats(sub)
            s["share_of_total_r_pct"] = round(s["total_r"] / total_r * 100, 1) if total_r else 0
            groups[k] = s
        results["buckets"][dim] = groups

    # persistence cross-tab for the two headline dims
    for dim in ["rvol_bucket", "expansion_bucket"]:
        xt = {}
        for yr in sorted({t["_vol"]["year"] for t in trades}):
            xt[str(yr)] = {}
            for k in sorted({t["_vol"][dim] for t in trades}):
                sub = [t for t in trades if t["_vol"]["year"] == yr and t["_vol"][dim] == k]
                if len(sub) >= 5:
                    xt[str(yr)][k] = {"n": len(sub),
                                      "exp_r": round(float(np.mean([x["net_r"] for x in sub])), 3)}
                else:
                    xt[str(yr)][k] = {"n": len(sub), "exp_r": None}
        results["year_xtab"][dim] = xt

    with open(os.path.join(OUTDIR, "volume_results.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("wrote volume_results.json", flush=True)
    return results


if __name__ == "__main__":
    main()
