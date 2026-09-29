"""Study 1: scanner+indicator agreement filter on Pine 4H trades (UX51).

Scanner structural signals regenerated with FROZEN backtest_v2.generate_signals on the
EXACT backtest_cache/v3/h4_*.pkl bars the Pine baseline used. Agreement (primary N=2):
Pine trade kept iff a scanner structural-candidate bar exists on the same symbol with
|bar_idx_scanner - bar_idx_pine| <= N. Sensitivity N in {0,1,3,5} reported.
Comparisons: agreement-filtered vs unfiltered Pine baseline vs scanner-alone
(S0 structural, no gates, scanner exits).
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
SIGCACHE = os.path.join(BASE, "cache_scanner_sig")
os.makedirs(SIGCACHE, exist_ok=True)
OUT = os.path.join(BASE, "study1_results.json")
# BASE's parent IS the repo (we live inside quality-flow-scanner-v5); resolve robustly:
REPO = os.path.dirname(BASE)
V3 = os.path.join(REPO, "backtest_cache", "v3")

N_PRIMARY = 2
N_SENS = [0, 1, 3, 5]


def load_bars():
    dfs = {}
    for sym in pb.UNIVERSE_X:
        p = os.path.join(V3, f"h4_{sym}.pkl")
        if not os.path.exists(p):
            print(f"  [warn] no h4 for {sym}", flush=True)
            continue
        dfs[sym] = pd.read_pickle(p)
    qqq = pd.read_pickle(os.path.join(V3, "h4_QQQ.pkl"))
    spy = pd.read_pickle(os.path.join(V3, "h4_SPY.pkl"))
    return dfs, qqq, spy


def scanner_signals(dfs, qqq, spy):
    qqq_ind = m.add_indicators(qqq)
    # empty weekly with tz-aware DatetimeIndex: _as_et passes it through,
    # MTF fields become False (caught), irrelevant for structural candidacy
    empty_w = pd.DataFrame(index=pd.DatetimeIndex([], tz="America/New_York"))
    sigs, struct_idx = {}, {}
    for n, sym in enumerate(dfs):
        sp = os.path.join(SIGCACHE, f"sig_{sym}.pkl")
        if os.path.exists(sp):
            signals = pd.read_pickle(sp)
        else:
            d1p = os.path.join(V3, f"d1_5y_{sym}.pkl")
            daily = pd.read_pickle(d1p) if os.path.exists(d1p) else pd.DataFrame()
            signals, n_struct, _ = bv.generate_signals(
                sym, dfs[sym], daily, empty_w, qqq, spy, qqq_ind)
            pd.to_pickle(signals, sp)
            print(f"  [{n+1}/{len(dfs)}] {sym}: {n_struct} structural", flush=True)
        sigs[sym] = signals
        struct_idx[sym] = {i for i, row in enumerate(signals)
                           if row and sr.is_structural_candidate(row)}
    return sigs, struct_idx


def pine_trades_with_idx(dfs):
    trades, idx_of = [], {}
    for sym, df in dfs.items():
        dfi = pb.add_pine_indicators(df)
        idx_of[sym] = {pd.Timestamp(t): i for i, t in enumerate(dfi.index)}
        tr, _ = pb.gen_pine_trades(sym, dfi)
        for t in tr:
            t["sig_idx"] = idx_of[sym].get(pd.Timestamp(t["signal_time"]))
        trades.extend(tr)
    missing = sum(1 for t in trades if t["sig_idx"] is None)
    print(f"  pine trades: {len(trades)}, unmapped sig_idx: {missing}", flush=True)
    return trades, idx_of


def run_portfolio(trades, dfs, label):
    closes = {s: dfs[s]["Close"] for s in dfs}
    rows = []
    for cost_name, cost in pb.COSTS.items():
        port = pb.simulate_portfolio(trades, closes, cost, pb.RISK_PCT)
        rows.append(pb.summarize(label, trades, port, 0, cost_name))
    return rows


def main():
    print("loading bars...", flush=True)
    dfs, qqq, spy = load_bars()
    print(f"  {len(dfs)} symbols", flush=True)
    print("generating scanner structural signals (frozen v5 rules)...", flush=True)
    sigs, struct_idx = scanner_signals(dfs, qqq, spy)
    n_struct_total = sum(len(v) for v in struct_idx.values())
    print(f"  total structural signals: {n_struct_total}", flush=True)

    print("generating pine trades...", flush=True)
    pine_trades, _ = pine_trades_with_idx(dfs)

    results = {"notes": [
        "Study 1: Pine 4H trades filtered by scanner structural agreement (frozen v5 rules).",
        f"Primary N={N_PRIMARY} (bar-index distance); sensitivity {N_SENS}.",
        "Same v3 h4 bars for both signal sets. Portfolio: 4/25bps, $10k, 1% risk, max 5 pos.",
    ], "n_structural_total": n_struct_total, "filters": {}}

    for N in [N_PRIMARY] + N_SENS:
        kept = [t for t in pine_trades
                if t["sig_idx"] is not None and
                any(abs(s - t["sig_idx"]) <= N for s in struct_idx[t["symbol"]])]
        rows = run_portfolio(kept, dfs, f"PINE_V36_agreeN{N}:UX51:4h")
        results["filters"][f"N={N}"] = {
            "trades_kept": len(kept),
            "of_pine_trades": len(pine_trades),
            "runs": rows,
        }
        for r in rows:
            print(f"  agree N={N} [{r['cost']}]: kept={len(kept)} "
                  f"exp={r['expectancy_net_r']}R PF={r['profit_factor']} "
                  f"ret={r['total_return_pct']}% dd={r['max_drawdown_pct']}%", flush=True)

    print("scanner-alone (S0 structural, scanner exits)...", flush=True)
    strades = []
    for sym in dfs:
        tr, _ = bv.gen_trades(sym, sigs[sym], dfs[sym], set(), "scanner")
        strades.extend(tr)
    srows = []
    for cost_name in ["4bps", "25bps"]:
        cost = bv.COSTS[cost_name]
        tc = bv.apply_cost(strades, cost)
        closes = {s: dfs[s]["Close"] for s in dfs}
        port = bv.simulate_portfolio(tc, closes, cost, pb.RISK_PCT)
        srows.append(bv.summarize(f"SCANNER_S0_structural:UX51:4h", tc, port, 0, cost_name))
    results["scanner_alone"] = srows
    for r in srows:
        print(f"  scanner-alone [{r['cost']}]: n={r['trades']} "
              f"exp={r['expectancy_net_r']}R PF={r['profit_factor']} "
              f"ret={r['total_return_pct']}% dd={r['max_drawdown_pct']}%", flush=True)

    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
