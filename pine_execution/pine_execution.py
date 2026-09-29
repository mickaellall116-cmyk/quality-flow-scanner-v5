"""Execution / slippage sensitivity on the LOCKED Pine V3.6 stack.
Spec: EXECUTION_SPEC.md (frozen before runs). Sensitivity only — no rule changes.
Locked stack C1 = rs_top2 ranking + E1 sector cap (drawdown gate NOT adopted).
Reuses pine_stack's engine/loaders verbatim; only execution assumptions vary."""
import json
import os
import sys
import traceback

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "pine_stack"))
sys.path.insert(0, os.path.join(HERE, "pine_ranking"))
sys.path.insert(0, os.path.join(HERE, "pine_exposure"))
sys.path.insert(0, os.path.join(HERE, "pine_signal_quality"))

import pine_backtest as pb
import pine_stack as st
from pine_ranking import compute_features
from pine_signal_quality import load_benchmarks

# extra cost legs, runtime-only (no file modified)
pb.COSTS["10bps"] = 0.0010
pb.COSTS["50bps"] = 0.0050
pb.COSTS["100bps"] = 0.0100

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "execution_results.json")
OUT22 = os.path.join(BASE, "execution_results_2022.json")
SEED = 20260918


def run_locked(all_trades, closes, sector_map, cost_name, use_ranking,
               sector_cap, skipped_gap, rs_dict, label):
    """One sim of the locked stack (or C0 baseline) under a cost assumption."""
    st.rs = rs_dict
    cost = pb.COSTS[cost_name]
    port = st.simulate_stack(all_trades, closes, cost, use_ranking,
                             sector_cap, False, sector_map)
    taken = [all_trades[i] for i in port["taken"]]
    row = pb.summarize(label, taken, port, skipped_gap, cost_name)
    dd = row["max_drawdown_pct"]
    row["calmar"] = round(row["total_return_pct"] / dd, 3) if dd else None
    row["sector_cap_skips"] = port["skipped_gate"]
    row["rank_skips"] = port["skipped_rank"]
    return row, taken, port


def expectancy_at_cost(all_trades, closes, sector_map, cost, use_ranking,
                       sector_cap, skipped_gap, rs_dict):
    """Mean net R of taken trades at an arbitrary float cost (no COSTS lookup)."""
    st.rs = rs_dict
    port = st.simulate_stack(all_trades, closes, cost, use_ranking,
                             sector_cap, False, sector_map)
    taken = [all_trades[i] for i in port["taken"]]
    if not taken:
        return 0.0, 0, port
    net = [pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]
           for tr in taken]
    return float(np.mean(net)), len(taken), port


def breakeven_grid(all_trades, closes, sector_map, use_ranking, sector_cap,
                   skipped_gap, rs_dict, lo_bps=0, hi_bps=150, step_bps=5):
    """Grid scan of expectancy vs cost; linearly interpolate the zero crossing.
    Honest about the (weak) feedback of costs into the 5% risk gate via equity."""
    pts = []
    for bps in range(lo_bps, hi_bps + 1, step_bps):
        e, n, _ = expectancy_at_cost(all_trades, closes, sector_map,
                                     bps / 10000.0, use_ranking, sector_cap,
                                     skipped_gap, rs_dict)
        pts.append((bps, e, n))
    be = None
    for (b0, e0, _), (b1, e1, _) in zip(pts, pts[1:]):
        if e0 > 0 >= e1:
            be = b0 + (0 - e0) * (b1 - b0) / (e1 - e0)
            break
    return {"break_even_bps": round(be, 1) if be is not None else None,
            "grid": [{"bps": b, "expectancy_r": round(e, 3), "trades": n}
                     for b, e, n in pts]}


def adverse_entry(all_trades, rs_by_id, bps=10):
    adv, rs_adv = [], {}
    for tr in all_trades:
        t2 = dict(tr)
        t2["entry"] = tr["entry"] * (1 + bps / 10000.0)
        adv.append(t2)
        rs_adv[id(t2)] = rs_by_id[id(tr)]
    return adv, rs_adv


def run_window(all_trades, closes, sector_map, skipped_gap, tag, bench):
    print(f"== {tag}: {len(all_trades)} candidates ==", flush=True)
    feats = compute_features(all_trades,
                             {s: df for s, df in data_of[tag].items()},
                             bench)
    rs_by_id = {id(tr): feats[i]["rs"] for i, tr in enumerate(all_trades)}
    res = {"tag": tag, "cases": {}, "e5": {}, "breakeven_bps": {}}

    adv_trades, rs_adv = adverse_entry(all_trades, rs_by_id)

    # E0..E4,E6 on C0 and C1
    cfgs = [("E0_4bps", "4bps", None),
            ("E1_10bps", "10bps", None),
            ("E2_25bps", "25bps", None),
            ("E3_50bps", "50bps", None),
            ("E4_adverse10", "4bps", "adverse"),
            ("E6_100bps", "100bps", None)]
    taken_counts = {}
    for cname, cost_name, variant in cfgs:
        res["cases"][cname] = {}
        for case, ur, sc in (("C0", False, False), ("C1", True, True)):
            trs = adv_trades if variant == "adverse" else all_trades
            rsd = rs_adv if variant == "adverse" else rs_by_id
            row, taken, port = run_locked(trs, closes, sector_map, cost_name,
                                          ur, sc, skipped_gap, rsd,
                                          f"{tag}-{cname}-{case}")
            res["cases"][cname][case] = row
            taken_counts[(cname, case)] = row["trades"]
            print(f"{tag} {cname} {case}: n={row['trades']} "
                  f"exp={row['expectancy_net_r']}R PF={row['profit_factor']} "
                  f"ret={row['total_return_pct']}% dd={row['max_drawdown_pct']}% "
                  f"calmar={row['calmar']} skirisk={row['skipped_max_risk']}",
                  flush=True)
    # diagnostic: taken-set drift with cost (5% risk gate feeds back via equity)
    for case in ("C0", "C1"):
        drift = {c: taken_counts[(c, case)]
                 for c, _, v in cfgs if v is None}
        res.setdefault("taken_drift", {})[case] = drift
        print(f"{tag} {case} taken-count by cost leg: {drift}", flush=True)

    # break-even grid scan per case (headline number)
    for case, ur, sc in (("C0", False, False), ("C1", True, True)):
        g = breakeven_grid(all_trades, closes, sector_map, ur, sc,
                           skipped_gap, rs_by_id)
        res["breakeven_bps"][case] = g
        print(f"{tag} {case} break-even: {g['break_even_bps']} bps", flush=True)

    # E5: drop 10% of candidates, 20 seeded reps, locked stack only
    reps = []
    for rep in range(20):
        rng = np.random.default_rng(SEED + rep)
        drop = rng.random(len(all_trades)) < 0.10
        kept = [tr for tr, d in zip(all_trades, drop) if not d]
        row, taken, port = run_locked(kept, closes, sector_map, "4bps",
                                      True, True, skipped_gap, rs_by_id,
                                      f"{tag}-E5-rep{rep}")
        reps.append({"trades": row["trades"],
                     "expectancy_net_r": row["expectancy_net_r"],
                     "total_return_pct": row["total_return_pct"],
                     "max_drawdown_pct": row["max_drawdown_pct"]})
    exps = np.array([r["expectancy_net_r"] for r in reps])
    rets = np.array([r["total_return_pct"] for r in reps])
    res["e5"] = {
        "reps": reps,
        "expectancy_net_r": {"median": round(float(np.median(exps)), 3),
                             "p10": round(float(np.percentile(exps, 10)), 3),
                             "p90": round(float(np.percentile(exps, 90)), 3)},
        "total_return_pct": {"median": round(float(np.median(rets)), 2),
                             "p10": round(float(np.percentile(rets, 10)), 2),
                             "p90": round(float(np.percentile(rets, 90)), 2)},
    }
    print(f"{tag} E5 (miss 10%, 20 reps): exp median={res['e5']['expectancy_net_r']['median']} "
          f"p10={res['e5']['expectancy_net_r']['p10']} p90={res['e5']['expectancy_net_r']['p90']}; "
          f"ret median={res['e5']['total_return_pct']['median']}%", flush=True)
    return res


data_of = {}


def main():
    global data_of
    bench, _ = load_benchmarks()

    print("== BULL WINDOW ==", flush=True)
    all_trades, closes, data, order_of, skipped_gap = st.load_bull()
    data_of["bull"] = data
    res = run_window(all_trades, closes, st.SECTOR, skipped_gap, "bull", bench)

    # fidelity: E0 C1 must reproduce pine_stack C1 @4bps exactly
    stack = json.load(open(os.path.join(HERE, "pine_stack", "stack_results.json")))
    ref = stack["cases"]["C1"]["4bps"]
    got = res["cases"]["E0_4bps"]["C1"]
    ok = (got["trades"] == ref["trades"]
          and got["expectancy_net_r"] == ref["expectancy_net_r"]
          and got["total_return_pct"] == ref["total_return_pct"]
          and got["max_drawdown_pct"] == ref["max_drawdown_pct"])
    print(f"fidelity E0 C1 vs pine_stack C1@4bps: {'PASS' if ok else 'FAIL'} "
          f"(got {got['trades']}/{got['expectancy_net_r']}R/"
          f"{got['total_return_pct']}%/{got['max_drawdown_pct']}%; "
          f"want 143/0.337/52.25/31.63)", flush=True)
    if not ok:
        print("FIDELITY FAILED — aborting", flush=True)
        sys.exit(2)
    # consistency: E2 C1 vs stack C1@25bps
    ref25 = stack["cases"]["C1"]["25bps"]
    got25 = res["cases"]["E2_25bps"]["C1"]
    print(f"consistency E2 C1 vs pine_stack C1@25bps: "
          f"got {got25['expectancy_net_r']}R/{got25['total_return_pct']}%/"
          f"{got25['max_drawdown_pct']}% vs ref "
          f"{ref25['expectancy_net_r']}R/{ref25['total_return_pct']}%/"
          f"{ref25['max_drawdown_pct']}%", flush=True)
    json.dump(res, open(OUT, "w"), indent=1, default=str)

    print("== 2022 WINDOW ==", flush=True)
    all22, closes22, data22, oo22, sg22 = st.load_2022()
    data_of["2022"] = data22
    res22 = run_window(all22, closes22, st.SECTOR_2022, sg22, "2022", bench)
    json.dump(res22, open(OUT22, "w"), indent=1, default=str)
    print("DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
