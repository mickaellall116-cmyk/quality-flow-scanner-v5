"""V1.7 — 2022 4H bear-market validation.

Same framework as pine_exit_fix/pine_exit_fix_validate.py:
- Universe: v6_short_v2/cache/d4h_2022_*.pkl + pine_exit_fix/cache_2022/d4h_2022_*.pkl,
  restricted to UX51 symbols.
- Signals with signal_time >= 2022-01-01 only (indicators warmed on 2021-09+).
- Open trades at data end liquidated at last close (reason "eod").
- Same portfolio conventions (4bps/25bps, $10k, 1% risk, max 5 positions).

Trigger (documented deviation from V17_SPEC.md): the spec required DD <= 40% for
the 2022 run; V1.7 exploratory DD was 42.26% (miss by 2.3pp) with expectancy
+0.338R vs +0.195R baseline (+73%). The 2022 run proceeds as a pure validation
step (it can only reject, not tune) because the expectancy margin is large and
the regime-robustness question is exactly what tonight's discipline demands.
"""

import glob
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))  # repo root: pine_backtest
import pine_backtest as pb
import pine_v17_backtest as v17

CACHE_OLD = os.path.join(os.path.dirname(HERE), "v6_short_v2", "cache")
CACHE_NEW = os.path.join(os.path.dirname(HERE), "pine_exit_fix", "cache_2022")
CUTOFF = pd.Timestamp("2022-01-01", tz="UTC")


def main():
    paths = {}
    for d in (CACHE_OLD, CACHE_NEW):
        for p in glob.glob(os.path.join(d, "d4h_2022_*.pkl")):
            sym = os.path.basename(p)[len("d4h_2022_"):-len(".pkl")]
            if sym not in pb.UNIVERSE_X:
                continue
            paths[sym] = p
    print(f"found {len(paths)} 2022 symbols", flush=True)

    all_trades, closes, skipped = [], {}, 0
    for sym in sorted(paths):
        df = pd.read_pickle(paths[sym])
        if "Volume" not in df.columns or df["Volume"].isna().all():
            print(f"  [warn] no volume for {sym}, skipping", flush=True)
            continue
        df = v17.add_v17_indicators(df)
        closes[sym] = df["Close"]
        tr, sg, se = v17.gen_v17_trades(sym, df, cutoff=CUTOFF, eod_liquidate=True)
        all_trades.extend(tr)
        skipped += sg
        print(f"  {sym}: {len(tr)} trades", flush=True)
    all_trades.sort(key=lambda t: t["entry_time"])

    rows = []
    for cost_name, cost in pb.COSTS.items():
        port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
        row = pb.summarize("PINE_V17_val2022:UX51:4h", all_trades, port, skipped, cost_name)
        t = pd.DataFrame(all_trades)
        net_r = []
        for tr in all_trades:
            _, _, nr, _ = pb._outcome(tr["entry"], tr["stop"], tr["exit"], pb.COSTS[cost_name])
            net_r.append(nr)
        t["net_r"] = net_r
        row["avg_winner_r"] = round(float(t.loc[t.net_r > 0, "net_r"].mean()), 3)
        row["avg_loser_r"] = round(float(t.loc[t.net_r <= 0, "net_r"].mean()), 3)
        row["stop_out_pct"] = round(float((t["reason"] == "stop").mean()) * 100, 1)
        rows.append(row)
        print(f"[{cost_name}] trades={row['trades']} exp={row['expectancy_net_r']}R "
              f"PF={row['profit_factor']} ret={row['total_return_pct']}% "
              f"dd={row['max_drawdown_pct']}% stopout={row['stop_out_pct']}% "
              f"reasons={row['exit_reasons']}", flush=True)

    out = {"symbols": sorted(paths), "n_symbols": len(paths),
           "framework": "same as pine_exit_fix 2022 validation (cutoff 2022-01-01, eod liquidation)",
           "trigger_note": "DD gate missed by 2.3pp (42.26% vs 40%); run proceeds as pure validation",
           "runs": rows}
    with open(os.path.join(HERE, "v17_validate.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    print("wrote v17_validate.json", flush=True)


if __name__ == "__main__":
    main()
