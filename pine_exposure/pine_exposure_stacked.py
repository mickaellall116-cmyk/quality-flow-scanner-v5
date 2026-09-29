"""Stacked secondary diagnostic: adopted rs_top2 ranking FIRST at contested bars,
then the E1 sector2 exposure gate at entry time. (Spec: reported, not a
candidate path.) Also includes ranking-only sanity vs the ranking study."""
import json
import os
import sys
import traceback

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "pine_ranking"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "pine_signal_quality"))
import pine_backtest as pb
from pine_ranking import gen_candidates, compute_features
from pine_signal_quality import load_benchmarks
from pine_exposure import SECTOR, ExposureSim, summarize

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(BASE, "exposure_stacked.json")


def run_stacked(all_trades, data, closes_4h, rs, order_of, cost,
                use_ranking, gate, max_concurrent=pb.MAX_CONCURRENT):
    events = []
    for t in all_trades:
        events.append((t["exit_time"], 0, t))
        events.append((t["entry_time"], 1, t))
    # group entries by timestamp; exits processed first at each timestamp
    from collections import defaultdict
    entries_by_t = defaultdict(list)
    exits = []
    for t, kind, tr in events:
        if kind == 0:
            exits.append((t, tr))
        else:
            entries_by_t[t].append(tr)
    exits.sort(key=lambda e: e[0])
    sim = ExposureSim.__new__(ExposureSim)
    # manual init (avoid double __init__)
    sim.closes_4h = closes_4h
    sim.logret_4h = None
    sim.cost = cost
    sim.risk_pct = pb.RISK_PCT
    sim.max_concurrent = max_concurrent
    sim.gate = None
    sim.skip_gate = 0
    sim.skip_cap = 0
    sim.skip_risk = 0
    sim.taken = []

    def mark(sym, t):
        s = closes_4h[sym]
        idx = s.index.searchsorted(t, side="right") - 1
        return float(s.iloc[idx]) if idx >= 0 else float(s.iloc[0])

    # merge exits and entry-groups in time order (exits first on ties)
    times = sorted(set([e[0] for e in exits]) | set(entries_by_t.keys()))
    exit_by_t = defaultdict(list)
    for t, tr in exits:
        exit_by_t[t].append(tr)
    realized = pb.START_EQUITY
    open_pos, by_id = [], {}
    peak, max_dd = realized, 0.0
    curve = []

    def marked_equity(t):
        unreal = sum(((mark(tr["symbol"], t) - tr["entry"]) / tr["entry"]) * p["size"]
                     for p, tr in ((p, p["trade"]) for p in open_pos))
        return realized + unreal

    def gate_sector2(tr, open_trades, t):
        s = SECTOR[tr["symbol"]]
        n = sum(1 for o in open_trades if SECTOR[o["symbol"]] == s)
        return (n < 2, "sector2")

    for t in times:
        for tr in exit_by_t.get(t, []):
            pos = by_id.pop(id(tr), None)
            if pos is None:
                continue
            _, _, net_r, _ = pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)
            realized += pos["risk_dollars"] * net_r
            open_pos.remove(pos)
            sim.taken.append({"trade": tr, "risk_dollars": pos["risk_dollars"],
                              "size": pos["size"], "net_r": net_r})
        grp = entries_by_t.get(t, [])
        if grp:
            # rank order for this bar (rs desc; deterministic tie-break by
            # candidate order); mirrors pine_ranking.simulate_portfolio_ranked:
            # the rank cap counts TAKEN (taken_at_t), so a risk-cap/gate
            # failure lets the next-ranked candidate in.
            grp = sorted(grp, key=lambda tr: order_of[id(tr)])
            n_cands_t = len(grp)
            if use_ranking:
                grp = sorted(grp, key=lambda tr: (-rs[id(tr)], order_of[id(tr)]))
            free = max_concurrent - len(open_pos)
            taken_at_t = 0
            for tr in grp:
                free = max_concurrent - len(open_pos)
                contested_now = n_cands_t > free
                if use_ranking and contested_now and taken_at_t >= min(2, free):
                    sim.skip_cap += 1  # ranked out
                    continue
                if free <= 0:
                    sim.skip_cap += 1
                    continue
                eq = marked_equity(t)
                open_risk = sum(p["risk_dollars"] for p in open_pos) / eq if eq > 0 else 1
                if open_risk + sim.risk_pct > pb.MAX_PORTFOLIO_RISK + 1e-9:
                    sim.skip_risk += 1
                    continue
                if gate == "E1":
                    take, _ = gate_sector2(tr, [p["trade"] for p in open_pos], t)
                    if not take:
                        sim.skip_gate += 1
                        continue
                risk_dollars = sim.risk_pct * eq
                risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
                pos = {"trade": tr, "risk_dollars": risk_dollars,
                       "size": risk_dollars / risk_frac, "risk_frac": risk_frac}
                open_pos.append(pos)
                by_id[id(tr)] = pos
                taken_at_t += 1
        eq = marked_equity(t)
        curve.append((t, eq, realized, len(open_pos)))
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    return {"final_equity": realized, "max_drawdown": max_dd,
            "skipped_gate": sim.skip_gate, "skipped_cap": sim.skip_cap,
            "skipped_risk": sim.skip_risk, "curve": curve, "taken": sim.taken}


def main():
    universe = pb.UNIVERSE_X
    all_trades, data, closes_4h = [], {}, {}
    order_of = {}
    for sym in universe:
        path = os.path.join(pb.CACHE, f"h4_{sym}.pkl")
        df = pd.read_pickle(path)
        df = pb.add_pine_indicators(df)
        data[sym] = df
        closes_4h[sym] = df["Close"]
        tr, _ = gen_candidates(sym, df)
        for t in tr:
            order_of[id(t)] = len(order_of)
        all_trades.extend(tr)
    all_trades.sort(key=lambda t: order_of[id(t)])
    print(f"candidates: {len(all_trades)}", flush=True)
    bench, _ = load_benchmarks()
    feats = compute_features(all_trades, data, bench)
    rs = {id(tr): feats[i]["rs"] for i, tr in enumerate(all_trades)}

    results = {"notes": ["Stacked secondary: rs_top2 first at contested bars, "
                         "then E1 sector2 gate. Reported only; not a candidate path."],
               "variants": {}}
    variants = [("stacked_none", False, None),
                ("stacked_rankonly", True, None),
                ("stacked_C1", True, "E1")]
    for vname, use_ranking, gate in variants:
        results["variants"][vname] = {}
        for cost_name, cost in pb.COSTS.items():
            port = run_stacked(all_trades, data, closes_4h, rs, order_of, cost,
                               use_ranking, gate)
            s = summarize(f"PINE_V36_stacked:{vname}", port, cost_name)
            s["fill_rate_pct"] = round(len(port["taken"]) / len(all_trades) * 100, 1)
            results["variants"][vname][cost_name] = s
            print(f"{vname} [{cost_name}]: n={s['trades']} exp={s['expectancy_net_r']}R "
                  f"PF={s['profit_factor']} ret={s['total_return_pct']}% "
                  f"dd={s['max_drawdown_pct']}% calmar={s['calmar']}", flush=True)
    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {OUT_JSON}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
