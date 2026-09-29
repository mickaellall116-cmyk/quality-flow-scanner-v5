"""Priority 5: Volatility normalization -- MEASUREMENT study.

Question (pre-registered 2026-09-25): does baseline setup quality depend on
volatility at entry? Is there a broad volatility sweet spot?

This is descriptive, NOT a filter test. Every canonical baseline trade is
tagged with point-in-time volatility metrics at its signal bar, then grouped
into pre-declared buckets (quartiles / terciles). No threshold tuning, no
model, no production change. pine_backtest.py imported UNMODIFIED.

Metrics (all evaluated on the signal bar i, point-in-time):
- atr_price   = atr[i] / close[i]
- atr_pctile  = percentile rank of atr[i] within trailing 1500 bars (~1yr 4H)
- rv_pctile   = percentile rank of 20-bar realized vol within trailing 1500
- breakout_atr= (close[i] - max(high[i-10:i])) / atr[i]
- stop_atr    = (entry - stop) / atr[i]

Buckets: quartiles for atr_price / breakout_atr / stop_atr; terciles
(<33 / 33-66 / >66) for atr_pctile / rv_pctile. All bucket edges computed
from the pooled trade sample, declared before results are inspected.

Verdict standard: a broad, persistent zone = MAYBE (with a future filter
direction); flat curve or thin-bucket-only differences = NO.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_volatility_backtest")
sys.path.insert(0, BASE)
import pine_backtest as pb

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "volatility_results.json")
os.makedirs(OUTDIR, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
COST = 0.0025  # 25 bps
TRAIL = 500   # ~4 months of 4H bars (series is only 1453 bars)


def add_vol_columns(df):
    out = df.copy()
    logret = np.log(out["Close"] / out["Close"].shift(1))
    rv = logret.rolling(20).std()
    out["rv"] = rv
    out["atr_pctile"] = out["atr"].rolling(TRAIL, min_periods=250).rank(pct=True) * 100
    out["rv_pctile"] = out["rv"].rolling(TRAIL, min_periods=250).rank(pct=True) * 100
    out["atr_price"] = out["atr"] / out["Close"]
    return out


def bucket_stats(trades):
    if not trades:
        return {"n": 0}
    rs = [pb._outcome(tr["entry"], tr["stop"], tr["exit"], COST)[2]
          for tr in trades]
    s = pd.Series(rs)
    gw = float(s[s > 0].sum())
    gl = float(-s[s <= 0].sum())
    return {
        "n": len(trades),
        "win_rate_pct": round(float((s > 0).mean()) * 100, 1),
        "expectancy_net_r": round(float(s.mean()), 3),
        "profit_factor": round(gw / gl, 2) if gl > 0 else None,
    }


def quartile_buckets(vals, labels=("Q1_low", "Q2", "Q3", "Q4_high")):
    edges = np.quantile(vals, [0.25, 0.5, 0.75])
    def tag(v):
        if v <= edges[0]:
            return labels[0]
        if v <= edges[1]:
            return labels[1]
        if v <= edges[2]:
            return labels[2]
        return labels[3]
    return edges.tolist(), tag


def tercile_tag(v):
    if v < 33:
        return "low_lt33"
    if v <= 66:
        return "mid_33_66"
    return "high_gt66"


def main():
    data, sig_index = {}, {}
    dropped = []
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        if "Volume" not in df.columns or df["Volume"].isna().all():
            dropped.append(sym)
            continue
        df = pb.add_pine_indicators(df)
        df = add_vol_columns(df)
        data[sym] = df
        sig_index[sym] = {df.index[i].isoformat(): i for i in range(len(df))}
    used = [s for s in WATCHLIST if s in data]
    print(f"loaded {len(used)} tickers; dropped: {dropped}", flush=True)

    # ---- baseline trades (canonical engine, unmodified) --------------------
    all_trades, skipped = [], 0
    for sym in used:
        tr, sg = pb.gen_pine_trades(sym, data[sym])
        all_trades.extend(tr)
        skipped += sg
    all_trades.sort(key=lambda t: t["entry_time"])

    rs = [pb._outcome(t["entry"], t["stop"], t["exit"], COST)[2]
          for t in all_trades]
    s = pd.Series(rs)
    print(f"BASELINE sanity: n={len(all_trades)} "
          f"exp={s.mean():.3f}R win={(s > 0).mean()*100:.1f}% "
          f"(expect n=237 exp=+0.239)", flush=True)

    # ---- tag each trade with volatility metrics at its signal bar ---------
    tagged, unmapped = [], 0
    for tr in all_trades:
        sym = tr["symbol"]
        i = sig_index[sym].get(tr["signal_time"])
        if i is None:
            unmapped += 1
            continue
        df = data[sym]
        r = df.iloc[i]
        sig_close = float(r["Close"])
        atr_i = float(r["atr"])
        tr["_vol"] = {
            "atr_price": float(r["atr_price"]),
            "atr_pctile": float(r["atr_pctile"]) if not pd.isna(r["atr_pctile"]) else None,
            "rv_pctile": float(r["rv_pctile"]) if not pd.isna(r["rv_pctile"]) else None,
            "breakout_atr": (sig_close - float(df["High"].iloc[max(0, i-10):i].max())) / atr_i,
            "stop_atr": (tr["entry"] - tr["stop"]) / atr_i,
            "year": int(pd.Timestamp(tr["signal_time"]).year),
        }
        tagged.append(tr)
    print(f"tagged {len(tagged)} trades; unmapped signal bars: {unmapped}",
          flush=True)

    results = {"baseline": bucket_stats(all_trades), "buckets": {},
               "year_crosstab": {}, "unmapped": unmapped}

    def get(m, t):
        return t["_vol"][m]

    # ---- quartile buckets -------------------------------------------------
    for metric in ["atr_price", "breakout_atr", "stop_atr"]:
        vals = [get(metric, t) for t in tagged]
        edges, tag = quartile_buckets(vals)
        groups = {}
        for t in tagged:
            groups.setdefault(tag(get(metric, t)), []).append(t)
        results["buckets"][metric] = {
            "type": "quartile",
            "edges": [round(e, 6) for e in edges],
            "groups": {k: bucket_stats(v) for k, v in sorted(groups.items())},
        }

    # ---- tercile buckets on percentiles -----------------------------------
    for metric in ["atr_pctile", "rv_pctile"]:
        sub = [t for t in tagged if get(metric, t) is not None]
        groups = {}
        for t in sub:
            groups.setdefault(tercile_tag(get(metric, t)), []).append(t)
        results["buckets"][metric] = {
            "type": "tercile",
            "n_missing": len(tagged) - len(sub),
            "groups": {k: bucket_stats(v) for k, v in sorted(groups.items())},
        }

    # ---- persistence: cross-tab each bucket by year ----------------------
    # (computed for all metrics; the verdict uses the most interesting one)
    for metric, spec in results["buckets"].items():
        xt = {}
        if spec["type"] == "quartile":
            vals = [get(metric, t) for t in tagged]
            _, tag = quartile_buckets(vals)
            keyfn = lambda t: tag(get(metric, t))
            pool = tagged
        else:
            keyfn = lambda t: tercile_tag(get(metric, t))
            pool = [t for t in tagged if get(metric, t) is not None]
        for t in pool:
            k = (keyfn(t), t["_vol"]["year"])
            xt.setdefault(k, []).append(t)
        results["year_crosstab"][metric] = {
            f"{b}|{y}": bucket_stats(v)
            for (b, y), v in sorted(xt.items())
        }

    with open(OUT, "w") as f:
        json.dump(results, f, indent=2)
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
