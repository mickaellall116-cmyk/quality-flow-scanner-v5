"""Study 2: Pine V3.6 4H on the broader X2 cohort (199 symbols).
Data: pine_expansion/cache_x2/h4_*.pkl (same builder as h4 cache).
Logic imported unmodified from pine_backtest. Reports X2-only vs UX51 baseline + pooled.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pine_backtest as pb
from v54_universe_x2 import UNIVERSE_X2

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "cache_x2")
OUT = os.path.join(BASE, "study2_results.json")


def run_on_cache(symbols, cache_dir, prefix, tag):
    all_trades, closes, skipped, used = [], {}, 0, []
    for sym in symbols:
        path = os.path.join(cache_dir, f"{prefix}{sym}.pkl")
        if not os.path.exists(path):
            continue
        df = pd.read_pickle(path)
        if "Volume" not in df.columns or df["Volume"].isna().all():
            continue
        df = pb.add_pine_indicators(df)
        closes[sym] = df["Close"]
        tr, sg = pb.gen_pine_trades(sym, df)
        all_trades.extend(tr)
        skipped += sg
        used.append(sym)
    all_trades.sort(key=lambda t: t["entry_time"])
    rows = []
    for cost_name, cost in pb.COSTS.items():
        port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
        rows.append(pb.summarize(f"PINE_V36_hybrid:{tag}:4h", all_trades, port,
                                 skipped, cost_name))
    return rows, all_trades, used


def main():
    results = {"notes": [
        "Study 2: unmodified Pine V3.6 4H on X2 cohort (199 symbols).",
        "X2 bars: masterscanner_api.download_data(sym,'4h','2y') -> session-aligned 4H.",
        "Symbols dropped only for missing/empty/no-volume data; coverage documented.",
    ]}
    print("== X2 universe ==", flush=True)
    x2_rows, x2_trades, x2_used = run_on_cache(UNIVERSE_X2, CACHE, "h4_", "X2")
    results["x2_symbols_requested"] = len(UNIVERSE_X2)
    results["x2_symbols_used"] = len(x2_used)
    results["x2_symbols_dropped"] = sorted(set(UNIVERSE_X2) - set(x2_used))
    results["x2"] = x2_rows
    for r in x2_rows:
        print(f"  X2 [{r['cost']}]: n={r['trades']} win={r['win_rate_pct']}% "
              f"exp={r['expectancy_net_r']}R PF={r['profit_factor']} "
              f"ret={r['total_return_pct']}% dd={r['max_drawdown_pct']}%", flush=True)

    print("== POOLED UX51+X2 ==", flush=True)
    v3 = os.path.join(os.path.dirname(BASE), "backtest_cache", "v3")
    ux_rows, ux_trades, ux_used = run_on_cache(pb.UNIVERSE_X, v3, "h4_", "UX51")
    pooled = sorted(x2_trades + ux_trades, key=lambda t: t["entry_time"])
    closes = {}
    for sym in set(x2_used) | set(ux_used):
        for cdir, pre in ((CACHE, "h4_"), (v3, "h4_")):
            p = os.path.join(cdir, f"{pre}{sym}.pkl")
            if os.path.exists(p):
                closes[sym] = pd.read_pickle(p)["Close"]
                break
    pooled_rows = []
    for cost_name, cost in pb.COSTS.items():
        port = pb.simulate_portfolio(pooled, closes, cost, pb.RISK_PCT)
        pooled_rows.append(pb.summarize("PINE_V36_hybrid:POOLED:4h", pooled, port,
                                       0, cost_name))
    results["pooled"] = pooled_rows
    results["pooled_symbols"] = len(closes)
    for r in pooled_rows:
        print(f"  POOLED [{r['cost']}]: n={r['trades']} "
              f"exp={r['expectancy_net_r']}R PF={r['profit_factor']} "
              f"ret={r['total_return_pct']}% dd={r['max_drawdown_pct']}%", flush=True)

    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
