#!/usr/bin/env python3
"""Universe-integrity audit quantification for the 14-stock research universe.

Reads the study data cache (pine_entry_timing_backtest/cache) and the
canonical backtester (imported UNMODIFIED), then:
  1. prints per-symbol data coverage for the 14 names,
  2. reconstructs the 237-trade baseline per symbol at 25bps,
  3. compares the 14-stock baseline to random 14-name subsets of the
     51-symbol UX51 universe (same window, same cost) to estimate the
     selection-bias lift.

Outputs are printed to stdout; copy the numbers into the audit report.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402  (canonical, unmodified)

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
WATCH14 = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
           "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]


def trades_for(sym, cost):
    df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
    df = pb.add_pine_indicators(df)
    tr, _ = pb.gen_pine_trades(sym, df)
    return [pb._outcome(t["entry"], t["stop"], t["exit"], cost)[2] for t in tr]


def main():
    print("== 1. data coverage ==")
    for s in WATCH14:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{s}.pkl"))
        print(f"{s:5s} {len(df):5d} bars  {df.index.min()} -> {df.index.max()}")

    print("\n== 2. baseline reconstruction @25bps ==")
    tot_n, tot_r = 0, 0.0
    per = {}
    for s in WATCH14:
        rs = trades_for(s, 0.0025)
        per[s] = (len(rs), float(np.mean(rs)) if rs else float("nan"),
                  float(np.sum(rs)) if rs else 0.0)
        tot_n += len(rs)
        tot_r += per[s][2]
    print(f"total n={tot_n} meanR={tot_r / tot_n:+.4f} (reported +0.2388)")
    for s, (n, m, su) in per.items():
        print(f"  {s:5s} n={n:3d} meanR={m:+.4f} sumR={su:+7.2f}")
    top4 = sum(per[s][2] for s in ["RKLB", "PLTR", "HOOD", "ONDS"])
    print(f"top-4 (RKLB,PLTR,HOOD,ONDS) sumR={top4:+.2f} = {top4 / tot_r * 100:.1f}% of total")

    print("\n== 3. selection-bias estimate vs UX51 ==")
    r = json.load(open(os.path.join(BASE, "pine_backtest_results.json")))
    ps = r["per_symbol_UX51"]  # 4bps, window 2024-09-16 -> 2026-09-14
    arr = [(s, ps[s]["n"], ps[s]["mean_r"]) for s in ps]
    rng = np.random.default_rng(7)
    vals = []
    for _ in range(20000):
        idx = rng.choice(len(arr), 14, replace=False)
        n = sum(arr[i][1] for i in idx)
        vals.append(sum(arr[i][1] * arr[i][2] for i in idx) / n if n else 0.0)
    vals = np.array(vals)
    print("random 14-subsets of UX51 @4bps: median %+.4f  p90 %+.4f  p95 %+.4f  p99 %+.4f"
          % (np.median(vals), np.quantile(vals, .9), np.quantile(vals, .95),
             np.quantile(vals, .99)))
    # 14-stock baseline on the SAME window and cost for apples-to-apples
    lo, hi = "2024-09-16", "2026-09-15"
    tn, tr = 0, 0.0
    for s in WATCH14:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{s}.pkl"))
        df = pb.add_pine_indicators(df)
        trd, _ = pb.gen_pine_trades(s, df)
        trd = [t for t in trd if lo <= str(t["entry_time"])[:10] < hi]
        rs = [pb._outcome(t["entry"], t["stop"], t["exit"], 0.0004)[2] for t in trd]
        tn += len(rs)
        tr += sum(rs)
    print(f"14-stock same window @4bps: n={tn} meanR={tr / tn:+.4f}")
    print(f"implied selection lift ~= {tr / tn - float(np.median(vals)):+.4f}R "
          f"(hand-picked vs median random draw)")


if __name__ == "__main__":
    main()
