"""POST-HOC diagnostics for the ranking study (not pre-registered, not candidates).
Purpose: separate ranking SKILL from mere selectivity.
1. takeall-taken: per-trade stats of the 184 trades the control portfolio
   actually took (vs the published 263-candidate / +0.195R baseline).
2. rs_bottom1 / vol_bottom1: reverse ranking — take the WORST-ranked at
   contested bars. If bottom also beats control, the edge is selectivity
   (fewer trades), not ranking skill.
3. random_top2 (seeded): random ordering placebo.
These cannot become candidates; they only inform interpretation.
"""
import json
import os
import sys
import traceback
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "pine_signal_quality"))
import pine_backtest as pb
from pine_signal_quality import extend_row
from pine_ranking import (load_4h_cache, gen_candidates, compute_features,
                          simulate_portfolio_ranked, pct_ranks)
from pine_signal_quality import load_benchmarks

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "ranking_diagnostics.json")


def main():
    print("loading data + candidates (same engine)...", flush=True)
    data = load_4h_cache()
    all_trades, closes, skipped_gap = [], {}, 0
    for sym, df in data.items():
        tr, sg = gen_candidates(sym, df)
        all_trades.extend(tr)
        closes[sym] = df["Close"]
        skipped_gap += sg
    all_trades.sort(key=lambda t: t["entry_time"])
    bench, _ = load_benchmarks()
    feats = compute_features(all_trades, data, bench)
    rng = np.random.default_rng(7)
    rand_score = {i: float(rng.random()) for i in range(len(all_trades))}
    feats_rand = {i: {"rs": rand_score[i], "vol": 0.0, "rr": 0.0}
                  for i in range(len(all_trades))}

    out = {"note": "POST-HOC diagnostics only; not candidates; cannot be adopted."}

    # 1. takeall taken-subset
    taken = []
    port = simulate_portfolio_ranked(all_trades, closes, pb.COSTS["4bps"],
                                     pb.RISK_PCT, feats, "takeall", None,
                                     taken_out=taken)
    tsub = [all_trades[i] for i in taken]
    row = pb.summarize("takeall-taken-subset", tsub, port, skipped_gap, "4bps")
    row = extend_row(row, tsub, "4bps")
    out["takeall_taken_subset_4bps"] = row
    print(f"takeall taken subset: n={row['trades']} exp={row['expectancy_net_r']}R "
          f"PF={row['profit_factor']} (control published: n=263, +0.195R)", flush=True)

    # 2/3. reverse + random placebos: implement by negating / random scores
    # rs_bottom1: rank by -rs with n_cap=1
    feats_neg = {i: {"rs": -feats[i]["rs"], "vol": -feats[i]["vol"],
                     "rr": feats[i]["rr"]} for i in feats}
    for vid, ff, scheme, n_cap in [
            ("rs_bottom1", feats_neg, "rs", 1),
            ("vol_bottom1", feats_neg, "vol", 1),
            ("random_top2", feats_rand, "rs", 2)]:
        taken = []
        port = simulate_portfolio_ranked(all_trades, closes, pb.COSTS["4bps"],
                                         pb.RISK_PCT, ff, scheme, n_cap,
                                         taken_out=taken)
        tsub = [all_trades[i] for i in taken]
        row = pb.summarize(f"placebo:{vid}", tsub, port, skipped_gap, "4bps")
        row = extend_row(row, tsub, "4bps")
        out[vid] = row
        print(f"{vid}: n={row['trades']} exp={row['expectancy_net_r']}R "
              f"PF={row['profit_factor']} dd={row['max_drawdown_pct']}%", flush=True)

    # overlap diagnostic: how many of rs_top2's taken trades are also in takeall taken?
    t_rs, t_ta = [], []
    simulate_portfolio_ranked(all_trades, closes, pb.COSTS["4bps"], pb.RISK_PCT,
                              feats, "rs", 2, taken_out=t_rs)
    simulate_portfolio_ranked(all_trades, closes, pb.COSTS["4bps"], pb.RISK_PCT,
                              feats, "takeall", None, taken_out=t_ta)
    s_rs, s_ta = set(t_rs), set(t_ta)
    out["overlap"] = {"rs_top2_taken": len(s_rs), "takeall_taken": len(s_ta),
                      "intersection": len(s_rs & s_ta),
                      "rs_only": len(s_rs - s_ta), "takeall_only": len(s_ta - s_rs)}
    print(f"overlap rs_top2 vs takeall: {out['overlap']}", flush=True)
    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print("DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
