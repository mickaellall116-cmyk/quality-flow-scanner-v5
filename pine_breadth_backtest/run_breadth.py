#!/usr/bin/env python3
"""Priority 11 — Cross-sectional breadth (2026-09-24).

Question (pre-registered): when many stocks signal simultaneously, is that
confirmation of a healthy market, or evidence of an overcrowded/late move?

METHOD (declared before looking at results):
- Baseline: canonical 4H Hybrid trades, 14-stock watchlist, 4H bars,
  Oct 2023-Sep 2026, frozen Mode B exits, 25bps costs. Engine imported
  unmodified; this is a MEASUREMENT study — no filter is built or proposed.
- For each baseline trade, count how many VALID SIGNALS fired on the same
  4H bar across the 14-stock watchlist. "Valid signal" = pine_buy_signal(df,i)
  True (raw signal, point-in-time, independent of whether that symbol already
  had an open position — breadth is about setups firing, not fills).
- Bucketing (pre-declared, mandate's buckets): 1-2, 3-5, 6-10, 10+
  simultaneous signals.
- Per bucket: n, expectancy @25bps, win rate, PF.
- Persistence: cross-tab the most interesting split by year.
- Verdict: crowded bars clearly worse across years -> MAYBE (supports P2
  ranking work); crowded bars better -> confirmation effect; flat -> NO.
"""
import json
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_breadth_backtest")
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "breadth_results.json")
os.makedirs(OUTDIR, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

COST = 0.0025
BUCKETS = ["1-2", "3-5", "6-10", "10+"]


def net_r(tr, cost=COST):
    return pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]


def bucket_stats(trades):
    if not trades:
        return {"n": 0}
    rs = np.array([net_r(t) for t in trades])
    wins = rs[rs > 0]
    losses = rs[rs <= 0]
    gw, gl = wins.sum(), -losses.sum()
    return {
        "n": len(trades),
        "expectancy_net_r": round(float(rs.mean()), 4),
        "win_rate_pct": round(float((rs > 0).mean()) * 100, 1),
        "profit_factor": round(float(gw / gl), 2) if gl > 0 else None,
    }


def breadth_bucket(c):
    if c <= 2:
        return "1-2"
    if c <= 5:
        return "3-5"
    if c <= 10:
        return "6-10"
    return "10+"


def main():
    data = {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        data[sym] = df

    # ---- raw signal count per 4H bar timestamp, across all 14 names -------
    sig_counts = Counter()
    sig_symbols = {}
    for sym in WATCHLIST:
        df = data[sym]
        n = len(df)
        for i in range(pb.WARMUP, n - 1):
            if pb.pine_buy_signal(df, i):
                ts = df.index[i].isoformat()
                sig_counts[ts] += 1
                sig_symbols.setdefault(ts, []).append(sym)
    print(f"bars with >=1 signal: {len(sig_counts)}", flush=True)
    hist = Counter(sig_counts.values())
    print("signal-count histogram:", dict(sorted(hist.items())), flush=True)

    # ---- baseline trades (canonical engine, unmodified) ------------------
    trades = []
    for sym in WATCHLIST:
        tr, _ = pb.gen_pine_trades(sym, data[sym])
        trades.extend(tr)
    trades.sort(key=lambda t: t["entry_time"])
    print(f"baseline trades: {len(trades)}", flush=True)

    rows = []
    missing = 0
    for t in trades:
        c = sig_counts.get(t["signal_time"], 0)
        if c == 0:
            # signal fired while this symbol was already in a trade:
            # the raw-signal scan counts it, but timestamp misalignment or
            # warmup edges can miss it. Count the trade's own signal at least.
            missing += 1
            c = 1
        rows.append({
            "symbol": t["symbol"], "signal_time": t["signal_time"],
            "year": str(pd.Timestamp(t["signal_time"]).year),
            "r": net_r(t), "n_signals": c, "bucket": breadth_bucket(c),
            "co_signals": sorted(sig_symbols.get(t["signal_time"], [])),
        })
    print(f"trades with no raw-signal match (counted as 1): {missing}",
          flush=True)
    m = pd.DataFrame(rows)

    results = {
        "n_trades": len(trades),
        "baseline": bucket_stats(trades),
        "signal_count_histogram": {str(k): int(v)
                                   for k, v in sorted(hist.items())},
        "buckets": {},
    }
    print("\n== breadth buckets ==", flush=True)
    for lab in BUCKETS:
        b = bucket_stats([t for t, r in zip(trades, rows)
                          if r["bucket"] == lab])
        results["buckets"][lab] = b
        print(f"  {lab}: n={b['n']} exp={b.get('expectancy_net_r')}R "
              f"win={b.get('win_rate_pct')}% pf={b.get('profit_factor')}",
              flush=True)

    # ---- persistence: crowded (6+) vs uncrowded, by year ------------------
    m["crowded"] = m["n_signals"] >= 6
    yr = {}
    print("\npersistence: crowded (>=6 signals) vs uncrowded, by year",
          flush=True)
    for y, grp in m.groupby("year"):
        cr = grp[grp["crowded"]]["r"]
        un = grp[~grp["crowded"]]["r"]
        yr[y] = {
            "n_crowded": int(len(cr)),
            "exp_crowded_r": round(float(cr.mean()), 4) if len(cr) else None,
            "n_uncrowded": int(len(un)),
            "exp_uncrowded_r": round(float(un.mean()), 4) if len(un) else None,
        }
        d = yr[y]
        print(f"  {y}: crowded n={d['n_crowded']} {d['exp_crowded_r']}R | "
              f"uncrowded n={d['n_uncrowded']} {d['exp_uncrowded_r']}R",
              flush=True)
    results["persistence_crowded_vs_uncrowded_by_year"] = yr

    # ---- distribution detail: expectancy by exact signal count -----------
    exact = {}
    for c, grp in m.groupby("n_signals"):
        exact[str(int(c))] = {
            "n": int(len(grp)),
            "expectancy_net_r": round(float(grp["r"].mean()), 4),
        }
    results["by_exact_count"] = exact

    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
