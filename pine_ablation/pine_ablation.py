"""Four-layer ablation audit of the locked Pine V3.6 stack.
Spec: ABLATION_SPEC.md (pre-registered). No new ideas, no tuning.

Engine: verbatim copy of pine_stack.simulate_stack with EXACTLY one
difference: the MAX_PORTFOLIO_RISK (5%) skip check is gated behind a
`risk_gate` flag (off for L0-L2, on for L3). The S4 drawdown gate (R3,
archived) stays OFF for all layers. Identical trades/costs/accounting.
"""
import json
import os
import sys
import traceback
from collections import defaultdict

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "pine_ranking"))
sys.path.insert(0, os.path.join(HERE, "pine_exposure"))
sys.path.insert(0, os.path.join(HERE, "pine_signal_quality"))
import pine_backtest as pb
from pine_stack import pine_stack as ps
from pine_ranking import compute_features
from pine_signal_quality import load_benchmarks, extend_row

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(BASE, "ablation_results.json")
OUT_JSON_2022 = os.path.join(BASE, "ablation_results_2022.json")
LOG = os.path.join(BASE, "pine_ablation.log")

rs = {}  # id(trade) -> 20-bar return minus SPY, set per window


def log(msg):
    print(msg, flush=True)
    with open(LOG, "a") as f:
        f.write(msg + "\n")


def simulate_ablation(all_trades, closes, cost, use_ranking, sector_cap,
                      risk_gate, sector_map):
    """pine_stack.simulate_stack verbatim except:
    (1) MAX_PORTFOLIO_RISK check gated by `risk_gate`;
    (2) contested-bar/signal engagement counters added."""
    def mark(sym, t):
        s = closes[sym]
        ii = s.index.searchsorted(t, side="right") - 1
        return float(s.iloc[ii]) if ii >= 0 else float(s.iloc[0])

    entries_by_t = defaultdict(list)
    exits_by_t = defaultdict(list)
    for idx, tr in enumerate(all_trades):
        entries_by_t[tr["entry_time"]].append(idx)
        exits_by_t[tr["exit_time"]].append(idx)
    times = sorted(set(entries_by_t) | set(exits_by_t))

    realized = pb.START_EQUITY
    open_pos, by_id = [], {}
    peak, max_dd = realized, 0.0
    skipped_rank = skipped_cap = skipped_risk = skipped_gate = 0
    n_half_risk = n_full_risk = 0
    contested_bars = 0
    contested_signals = 0
    taken = []
    open_time = total_time = pd.Timedelta(0)
    prev_t = None

    def marked_equity(t):
        unreal = sum(((mark(tr["symbol"], t) - tr["entry"]) / tr["entry"]) * p["size"]
                      for p, tr in ((p, p["trade"]) for p in open_pos))
        return realized + unreal

    for t in times:
        if prev_t is not None and t > prev_t:
            dt = t - prev_t
            total_time += dt
            if open_pos:
                open_time += dt
        prev_t = t
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
            if use_ranking:
                scored = [(-rs[id(all_trades[i])], i) for i in cands]
                scored.sort()
                ordered = [i for _, i in scored]
            else:
                ordered = sorted(cands)  # deterministic candidate order
            free0 = pb.MAX_CONCURRENT - len(open_pos)
            bar_contested = n_cands_t > free0
            if bar_contested:
                contested_bars += 1
                contested_signals += n_cands_t
            taken_at_t = 0
            for idx in ordered:
                tr = all_trades[idx]
                free = pb.MAX_CONCURRENT - len(open_pos)
                contested_now = n_cands_t > free
                if use_ranking and contested_now and taken_at_t >= min(2, free):
                    skipped_rank += 1
                    continue
                if free <= 0:
                    skipped_cap += 1
                    continue
                eq = marked_equity(t)
                if sector_cap:
                    s = sector_map[tr["symbol"]]
                    n_sec = sum(1 for p in open_pos
                                if sector_map[p["trade"]["symbol"]] == s)
                    if n_sec >= 2:
                        skipped_gate += 1
                        continue
                cur_risk = pb.RISK_PCT
                open_risk = (sum(p["risk_dollars"] for p in open_pos) / eq
                             if eq > 0 else 1)
                # THE one gated difference: 5% portfolio-risk gate
                if risk_gate and open_risk + cur_risk > pb.MAX_PORTFOLIO_RISK + 1e-9:
                    skipped_risk += 1
                    continue
                risk_dollars = cur_risk * eq
                risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
                pos = {"trade": tr, "risk_dollars": risk_dollars,
                       "size": risk_dollars / risk_frac, "risk_frac": risk_frac,
                       "risk_pct": cur_risk}
                open_pos.append(pos)
                by_id[id(tr)] = pos
                taken.append(idx)
                taken_at_t += 1
                if cur_risk < pb.RISK_PCT:
                    n_half_risk += 1
                else:
                    n_full_risk += 1
        eq = marked_equity(t)
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    exposure = float(open_time / total_time) if total_time > pd.Timedelta(0) else 0.0
    return {"final_equity": realized, "max_drawdown": max_dd,
            "skipped_rank": skipped_rank, "skipped_cap": skipped_cap,
            "skipped_risk": skipped_risk, "skipped_gate": skipped_gate,
            "n_half_risk": n_half_risk, "n_full_risk": n_full_risk,
            "taken": taken, "exposure": exposure,
            "contested_bars": contested_bars,
            "contested_signals": contested_signals,
            "skipped_cap_count": skipped_cap + skipped_rank,
            "skipped_cap_risk": skipped_risk}


def run_layer(all_trades, closes, sector_map, cost_name, use_ranking,
              sector_cap, risk_gate, skipped_gap):
    global rs
    cost = pb.COSTS[cost_name]
    port = simulate_ablation(all_trades, closes, cost, use_ranking, sector_cap,
                             risk_gate, sector_map)
    taken = [all_trades[i] for i in port["taken"]]
    row = pb.summarize("ablation", taken, port, skipped_gap, cost_name)
    row = extend_row(row, taken, cost_name)
    dd = row["max_drawdown_pct"]
    row["calmar"] = round(row["total_return_pct"] / dd, 3) if dd else None
    row["rank_skips"] = port["skipped_rank"]
    row["sector_cap_skips"] = port["skipped_gate"]
    row["risk_gate_skips"] = port["skipped_risk"]
    row["slot_cap_skips"] = port["skipped_cap"]
    row["contested_bars"] = port["contested_bars"]
    row["contested_signals"] = port["contested_signals"]
    return row


LAYERS = [
    ("L0", False, False, False),  # V3.6 core
    ("L1", True, False, False),    # + ranking
    ("L2", True, True, False),     # + sector cap
    ("L3", True, True, True),      # + 5% risk gate (= locked C1)
]


def main():
    global rs
    open(LOG, "w").write("ablation run started\n")

    log("== BULL WINDOW ==")
    all_trades, closes, data, order_of, skipped_gap = ps.load_bull()
    log(f"candidates: {len(all_trades)}")
    bench, _ = load_benchmarks()
    feats = compute_features(all_trades, data, bench)
    rs = {id(tr): feats[i]["rs"] for i, tr in enumerate(all_trades)}

    # ---- fidelity: L3 must reproduce locked C1 exactly
    ref = json.load(open(os.path.join(HERE, "pine_stack", "stack_results.json")))
    ref_c1 = ref["cases"]["C1"]
    results = {"spec": "ABLATION_SPEC.md pre-registered before runs",
               "engine": "pine_stack.simulate_stack verbatim + risk_gate flag "
                         "(5% MAX_PORTFOLIO_RISK check); S4 dd_gate off for all",
               "layers": {}}
    for lname, ur, sc, rg in LAYERS:
        results["layers"][lname] = {}
        for cost_name in pb.COSTS:
            row = run_layer(all_trades, closes, ps.SECTOR, cost_name,
                            ur, sc, rg, skipped_gap)
            results["layers"][lname][cost_name] = row
            log(f"{lname} [{cost_name}]: n={row['trades']} "
                f"exp={row['expectancy_net_r']}R PF={row['profit_factor']} "
                f"ret={row['total_return_pct']}% dd={row['max_drawdown_pct']}% "
                f"calmar={row['calmar']} rankskip={row['rank_skips']} "
                f"secskip={row['sector_cap_skips']} riskskip={row['risk_gate_skips']} "
                f"contested={row['contested_bars']}b/{row['contested_signals']}s")
        json.dump(results, open(OUT_JSON, "w"), indent=1, default=str)

    # fidelity check on 4bps and 25bps
    ok = True
    for cost_name in pb.COSTS:
        got = results["layers"]["L3"][cost_name]
        want = ref_c1[cost_name]
        match = (got["trades"] == want["trades"]
                 and got["expectancy_net_r"] == want["expectancy_net_r"]
                 and got["total_return_pct"] == want["total_return_pct"]
                 and got["max_drawdown_pct"] == want["max_drawdown_pct"]
                 and got["sector_cap_skips"] == want["sector_cap_skips"]
                 and got["rank_skips"] == want["rank_skips"])
        log(f"fidelity L3 == locked C1 [{cost_name}]: {'PASS' if match else 'FAIL'}")
        ok = ok and match
    results["fidelity_L3_vs_C1"] = ok
    json.dump(results, open(OUT_JSON, "w"), indent=1, default=str)
    if not ok:
        log("FIDELITY FAILED — aborting")
        sys.exit(2)

    log("== 2022 WINDOW ==")
    all22, closes22, data22, order_of22, sg22 = ps.load_2022()
    log(f"2022 candidates: {len(all22)} symbols={len(data22)}")
    feats22 = compute_features(all22, data22, bench)
    rs = {id(tr): feats22[i]["rs"] for i, tr in enumerate(all22)}
    results22 = {"notes": "2022 validation; same framework as every prior study.",
                 "layers": {}}
    for lname, ur, sc, rg in LAYERS:
        results22["layers"][lname] = {}
        for cost_name in pb.COSTS:
            row = run_layer(all22, closes22, ps.SECTOR_2022, cost_name,
                            ur, sc, rg, sg22)
            results22["layers"][lname][cost_name] = row
            log(f"2022 {lname} [{cost_name}]: n={row['trades']} "
                f"exp={row['expectancy_net_r']}R ret={row['total_return_pct']}% "
                f"dd={row['max_drawdown_pct']}% calmar={row['calmar']} "
                f"rankskip={row['rank_skips']} secskip={row['sector_cap_skips']} "
                f"riskskip={row['risk_gate_skips']} "
                f"contested={row['contested_bars']}b")
        json.dump(results22, open(OUT_JSON_2022, "w"), indent=1, default=str)
    log("DONE")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
