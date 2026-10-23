"""Diagnostic for QF-EQUITY43-DEV-PREFLIGHT-20261023-12 STOP blocker:
why does the corrected-simulator C0 fidelity invariant fail on the real
43-name DEV candidate set? Tests whether the divergence is isolated to
coincident-timestamp entry processing ORDER (pb: candidate-list order;
stack C0: canonical (symbol, signal_idx)) and whether the ranked C1 sim
(the actual study configuration) is input-order invariant on real data.
NO study performance is produced or reported by this diagnostic: the C1
equity values below are computed ONLY to test order-invariance (equality
across orderings), never as results."""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_study as rs_mod

import numpy as np
import pandas as pd


def main():
    child_manifest = json.load(open(os.path.join(HERE, "child_manifest.json")))
    symbols_study = rs_mod.PILOT + [l["symbol"] for l in child_manifest["legs"]
                                    if l["window"] == "W_DEV"]
    table, dev_sessions = rs_mod.load_session_table()
    admitted = rs_mod.phase2(table, dev_sessions, symbols_study)
    assert not rs_mod.failures, rs_mod.failures

    import scanner_rules as sr
    import pine_backtest as pb
    import pine_stack as st
    from pine_ranking import gen_candidates, compute_features
    from pine_exposure import SECTOR
    import asof_benchmark

    bars = {s: sr.resample_closed_4h_session_anchored(admitted[s], s,
                                                      now=rs_mod.FIXED_NOW)
            for s in symbols_study}
    data, closes = {}, {}
    for s in symbols_study:
        data[s] = pb.add_pine_indicators(bars[s])
        closes[s] = data[s]["Close"]
    bench = {"SPY": asof_benchmark.build_daily_asof(admitted["SPY"])}

    UX = [s for s in pb.UNIVERSE_X if s in set(symbols_study)]
    assert len(UX) == 43, len(UX)
    orders = {
        "study_order_pilot_first_then_manifest": symbols_study,
        "universe_x_order": UX,
        "alphabetical_order": sorted(symbols_study),
    }
    out = {"candidate_counts": {}, "fidelity": {}, "c1_order_invariance": {}}
    base_trades = {}
    for name, order in orders.items():
        trades, sg = [], 0
        for s in order:
            tr, g = gen_candidates(s, data[s])
            trades.extend(tr)
            sg += g
        base_trades[name] = trades
        out["candidate_counts"][name] = len(trades)
        ppb = pb.simulate_portfolio(trades, closes, pb.COSTS["4bps"], pb.RISK_PCT)
        pc0 = st.simulate_stack(trades, closes, pb.COSTS["4bps"],
                                False, False, False, SECTOR)
        out["fidelity"][name] = {
            "pb_final_equity": ppb["final_equity"],
            "stack_c0_final_equity": pc0["final_equity"],
            "delta": ppb["final_equity"] - pc0["final_equity"],
            "pb_skipped_cap_count": ppb["skipped_cap_count"],
            "stack_c0_skipped_cap": pc0["skipped_cap"],
            "pb_skipped_cap_risk": ppb["skipped_cap_risk"],
            "stack_c0_skipped_risk": pc0["skipped_risk"],
            "taken_pb_equals_stack_c0": None,
            "fidelity_pass": abs(ppb["final_equity"] - pc0["final_equity"]) < 1e-6
            and ppb["skipped_cap_count"] == pc0["skipped_cap"]}
        print(f"FIDELITY [{name}]: pb={ppb['final_equity']:.4f} "
              f"stackC0={pc0['final_equity']:.4f} delta={ppb['final_equity']-pc0['final_equity']:.4f} "
              f"capskip pb={ppb['skipped_cap_count']} stack={pc0['skipped_cap']} "
              f"riskskip pb={ppb['skipped_cap_risk']} stack={pc0['skipped_risk']}", flush=True)

    # C1 (ranked, the study configuration) order-invariance on real data:
    # same candidate OBJECTS, three list orders; rs recomputed per order.
    trades0 = base_trades["study_order_pilot_first_then_manifest"]
    shuffled = list(trades0)
    random.Random(20261023).shuffle(shuffled)
    canonical = sorted(trades0, key=lambda t: (t["symbol"], t["signal_idx"]))
    variants = {"study_order": trades0, "shuffled_seed20261023": shuffled,
                "canonical_symbol_signalidx": canonical}
    c1 = {}
    for name, tr_list in variants.items():
        feats = compute_features(tr_list, data, bench)
        st.rs = {id(tr): feats[i]["rs"] for i, tr in enumerate(tr_list)}
        port = st.simulate_stack(tr_list, closes, pb.COSTS["4bps"],
                                 True, True, False, SECTOR)
        taken_keys = sorted((tr_list[i]["symbol"], tr_list[i]["signal_idx"])
                            for i in port["taken"])
        c1[name] = {"final_equity": port["final_equity"],
                    "taken_count": len(port["taken"]),
                    "taken_keys_sha256": __import__("hashlib").sha256(
                        json.dumps(taken_keys).encode()).hexdigest(),
                    "skips": {k: port[k] for k in ("skipped_rank", "skipped_cap",
                                                   "skipped_risk", "skipped_gate")}}
        print(f"C1 [{name}]: equity={port['final_equity']:.4f} taken={len(port['taken'])} "
              f"taken_sha={c1[name]['taken_keys_sha256'][:16]}", flush=True)
    eqs = {v["final_equity"] for v in c1.values()}
    shas = {v["taken_keys_sha256"] for v in c1.values()}
    out["c1_order_invariance"] = {
        "variants": c1,
        "final_equity_identical_all_orders": len(eqs) == 1,
        "taken_set_identical_all_orders": len(shas) == 1}
    json.dump(out, open(os.path.join(HERE, "diag_fidelity.json"), "w"),
              indent=1, default=str)
    print("DIAG DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
