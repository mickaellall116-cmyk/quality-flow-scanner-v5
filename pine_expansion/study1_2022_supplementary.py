"""SUPPLEMENTARY (not pre-specified): validate scanner-alone S0 vs Pine on 2022 4H.

Emergent bonus finding from Study 1: scanner S0 structural + scanner exits on UX51
(2024-26) = +0.314R vs Pine +0.195R. This checks whether it holds on unseen 2022
bear-market 4H (Dukascopy). Same conventions: 4bps/25bps, $10k, 1% risk, max 5 pos.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import backtest_v2 as bv
import scanner_rules as sr
import masterscanner_api as m
import pine_backtest as pb

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "study1_2022_validation.json")
REPO = os.path.dirname(BASE)
C22A = os.path.join(REPO, "v6_short_v2", "cache")
C22B = os.path.join(REPO, "pine_exit_fix", "cache_2022")


def load_2022():
    syms = {}
    for d in (C22A, C22B):
        for f in os.listdir(d):
            if f.startswith("d4h_2022_") and f.endswith(".pkl"):
                sym = f[len("d4h_2022_"):-4]
                if sym not in syms:
                    syms[sym] = os.path.join(d, f)
    dfs = {}
    for sym, p in sorted(syms.items()):
        df = pd.read_pickle(p)
        if df.empty or len(df) < 300:
            continue
        dfs[sym] = df
    return dfs


def main():
    dfs = load_2022()
    print(f"2022 symbols: {len(dfs)}", flush=True)
    qqq, spy = dfs["QQQ"], dfs["SPY"]
    qqq_ind = m.add_indicators(qqq)
    empty = pd.DataFrame(index=pd.DatetimeIndex([], tz="UTC"))
    empty_d = pd.DataFrame(index=pd.DatetimeIndex([], tz="UTC"))

    # scanner signals + S0 trades
    strades, n_struct = [], 0
    for sym, df in dfs.items():
        if sym in ("QQQ", "SPY"):
            continue
        sigs, ns, _ = bv.generate_signals(sym, df, empty_d, empty, qqq, spy, qqq_ind)
        n_struct += ns
        tr, _ = bv.gen_trades(sym, sigs, df, set(), "scanner")
        strades.extend(tr)
    print(f"scanner structural signals: {n_struct}, trades: {len(strades)}", flush=True)

    # pine trades on same bars
    ptrades = []
    for sym, df in dfs.items():
        if sym in ("QQQ", "SPY"):
            continue
        if "Volume" not in df.columns or df["Volume"].isna().all():
            continue
        dfi = pb.add_pine_indicators(df)
        tr, _ = pb.gen_pine_trades(sym, dfi)
        ptrades.extend(tr)
    print(f"pine trades: {len(ptrades)}", flush=True)

    # 2022-only signal window (mirror exit_fix methodology: indicators warmed on
    # 2021-09+ headroom; only signals from 2022-01-01 on). entry_time is the bar
    # after the signal bar, so entry >= 2022-01-01 approximates it for both legs.
    CUTOFF = pd.Timestamp("2022-01-01", tz="UTC")
    strades = [t for t in strades if pd.Timestamp(t["entry_time"]) >= CUTOFF]
    ptrades = [t for t in ptrades if pd.Timestamp(t["entry_time"]) >= CUTOFF]
    print(f"2022-window trades: scanner={len(strades)} pine={len(ptrades)}", flush=True)

    closes = {s: dfs[s]["Close"] for s in dfs if s not in ("QQQ", "SPY")}
    results = {"notes": [
        "Supplementary 2022 validation of Study 1 bonus finding (not pre-specified).",
        f"{len([s for s in dfs if s not in ('QQQ','SPY')])} symbols, Dukascopy 4H 2022.",
        "Signals from 2022-01-01 only (entry_time >= cutoff), mirroring exit_fix window.",
        "No EOD liquidation (differs from exit_fix); both legs treated identically.",
    ], "n_structural": n_struct}
    for label, trades, sim_fn in (("scanner_s0", strades, bv), ("pine", ptrades, pb)):
        rows = []
        for cost_name in ["4bps", "25bps"]:
            cost = sim_fn.COSTS[cost_name]
            tc = sim_fn.apply_cost(trades, cost) if hasattr(sim_fn, "apply_cost") else trades
            port = sim_fn.simulate_portfolio(tc, closes, cost, pb.RISK_PCT)
            rows.append(sim_fn.summarize(f"2022_{label}:4h", tc, port, 0, cost_name))
        results[label] = rows
        for r in rows:
            print(f"  2022 {label} [{r['cost']}]: n={r['trades']} "
                  f"exp={r['expectancy_net_r']}R PF={r['profit_factor']} "
                  f"ret={r['total_return_pct']}% dd={r['max_drawdown_pct']}%", flush=True)
    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
