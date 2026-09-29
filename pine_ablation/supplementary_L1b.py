"""Supplementary diagnostic for the ablation audit (NOT pre-registered;
labeled diagnostic only). Two questions:
1. L1b = ranking + 5% risk gate, NO sector cap — the three-layer stack the
   ablation verdict points to. Does it match or beat L3?
2. What was the R of the trades each gate skipped (sector cap's 17, risk
   gate's 10)?
"""
import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "pine_ranking"))
sys.path.insert(0, os.path.join(HERE, "pine_exposure"))
sys.path.insert(0, os.path.join(HERE, "pine_signal_quality"))
sys.path.insert(0, os.path.join(HERE, "pine_ablation"))
import pine_backtest as pb
from pine_stack import pine_stack as ps
from pine_ranking import compute_features
from pine_signal_quality import load_benchmarks, extend_row
import pine_ablation as pa

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "supplementary_L1b.json")


def trade_r(tr, cost):
    _, _, net_r, _ = pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)
    return net_r


def main():
    global rs
    all_trades, closes, data, order_of, skipped_gap = ps.load_bull()
    bench, _ = load_benchmarks()
    feats = compute_features(all_trades, data, bench)
    pa.rs = {id(tr): feats[i]["rs"] for i, tr in enumerate(all_trades)}

    out = {}
    for cost_name in pb.COSTS:
        cost = pb.COSTS[cost_name]
        # L1b: ranking on, sector cap OFF, risk gate ON
        port = pa.simulate_ablation(all_trades, closes, cost, True, False,
                                    True, ps.SECTOR)
        taken = [all_trades[i] for i in port["taken"]]
        row = pb.summarize("L1b", taken, port, skipped_gap, cost_name)
        row = extend_row(row, taken, cost_name)
        dd = row["max_drawdown_pct"]
        row["calmar"] = round(row["total_return_pct"] / dd, 3) if dd else None
        row["risk_gate_skips"] = port["skipped_risk"]
        row["rank_skips"] = port["skipped_rank"]
        out[cost_name] = row
        print(f"L1b [{cost_name}]: n={row['trades']} exp={row['expectancy_net_r']}R "
              f"PF={row['profit_factor']} ret={row['total_return_pct']}% "
              f"dd={row['max_drawdown_pct']}% calmar={row['calmar']} "
              f"rankskip={row['rank_skips']} riskskip={row['risk_gate_skips']}",
              flush=True)

    # Q2: R of skipped trades. Re-run capturing skipped indices per reason.
    cost = pb.COSTS["4bps"]
    for tag, sc, rg in (("L2", True, False), ("L3", True, True)):
        # re-run with reason capture via a wrapped pass
        skipped = defaultdict(list)
        entries_by_t = defaultdict(list)
        exits_by_t = defaultdict(list)
        for idx, tr in enumerate(all_trades):
            entries_by_t[tr["entry_time"]].append(idx)
            exits_by_t[tr["exit_time"]].append(idx)
        times = sorted(set(entries_by_t) | set(exits_by_t))
        realized = pb.START_EQUITY
        open_pos, by_id = [], {}
        peak = realized

        def mark(sym, t):
            s = closes[sym]
            ii = s.index.searchsorted(t, side="right") - 1
            return float(s.iloc[ii]) if ii >= 0 else float(s.iloc[0])

        def marked_equity(t):
            unreal = sum(((mark(tr["symbol"], t) - tr["entry"]) / tr["entry"]) * p["size"]
                          for p, tr in ((p, p["trade"]) for p in open_pos))
            return realized + unreal

        for t in times:
            for idx in sorted(exits_by_t.get(t, [])):
                pos = by_id.pop(id(all_trades[idx]), None)
                if pos is None:
                    continue
                tr = all_trades[idx]
                _, _, net_r, _ = pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)
                realized += pos["risk_dollars"] * net_r
                open_pos.remove(pos)
            cands = entries_by_t.get(t, [])
            if cands:
                n_cands_t = len(cands)
                scored = [(-pa.rs[id(all_trades[i])], i) for i in cands]
                scored.sort()
                ordered = [i for _, i in scored]
                free0 = pb.MAX_CONCURRENT - len(open_pos)
                taken_at_t = 0
                for idx in ordered:
                    tr = all_trades[idx]
                    free = pb.MAX_CONCURRENT - len(open_pos)
                    contested_now = n_cands_t > free
                    if contested_now and taken_at_t >= min(2, free):
                        skipped["RANKED_OUT"].append(idx)
                        continue
                    if free <= 0:
                        skipped["NO_SLOT"].append(idx)
                        continue
                    eq = marked_equity(t)
                    if sc:
                        s = ps.SECTOR[tr["symbol"]]
                        n_sec = sum(1 for p in open_pos
                                    if ps.SECTOR[p["trade"]["symbol"]] == s)
                        if n_sec >= 2:
                            skipped["SECTOR_CAP"].append(idx)
                            continue
                    open_risk = (sum(p["risk_dollars"] for p in open_pos) / eq
                                 if eq > 0 else 1)
                    if rg and open_risk + pb.RISK_PCT > pb.MAX_PORTFOLIO_RISK + 1e-9:
                        skipped["RISK_GATE"].append(idx)
                        continue
                    risk_dollars = pb.RISK_PCT * eq
                    risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
                    pos = {"trade": tr, "risk_dollars": risk_dollars,
                           "size": risk_dollars / risk_frac}
                    open_pos.append(pos)
                    by_id[id(tr)] = pos
                    taken_at_t += 1
            eq = marked_equity(t)
            peak = max(peak, eq)
        print(f"--- skipped-trade R @4bps ({tag}) ---", flush=True)
        for reason, idxs in skipped.items():
            rs_ = [trade_r(all_trades[i], cost) for i in idxs]
            tot = sum(rs_)
            print(f"{reason}: n={len(idxs)} mean_R={np.mean(rs_):.3f} "
                  f"sum_R={tot:.2f} median={np.median(rs_):.3f}", flush=True)
            out.setdefault("skipped_R_4bps", {})[f"{tag}_{reason}"] = {
                "n": len(idxs), "mean_R": round(float(np.mean(rs_)), 3),
                "sum_R": round(float(tot), 2),
                "median_R": round(float(np.median(rs_)), 3)}

    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
