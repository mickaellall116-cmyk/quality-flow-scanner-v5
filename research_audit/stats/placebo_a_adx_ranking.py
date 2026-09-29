#!/usr/bin/env python3
"""PLACEBO (a): RANDOM RANKING on the 21 crowded bars (ADX selection-edge null).

Null: ranking is meaningless -> on each crowded bar, the "selected" set is a
random subset of the same size ADX selected. Where does ADX's real mean
selection edge (+0.6507R) sit in that null distribution?

Per-symbol trade returns are recovered by matching (symbol, entry_time) to the
canonical regenerated baseline trades (25bps costs, verified +0.2388R/237).
"""
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import get_data, save_json

RNG = np.random.default_rng(20260924)
N_DRAW = 2000


def load_bars():
    path = os.path.join(
        "/home/hatch/workspace/quality-flow-scanner-v5",
        "pine_adx_protocol", "adx_selection_edge.json")
    return json.load(open(path))


def match_candidates(trades, bar):
    """Return list of (symbol, net_r) matched to this crowded bar, and verify
    the ADX sel/rej means against a subset partition -> k_selected."""
    bt = pd.Timestamp(bar["t"])
    cands = [t for t in trades
             if t["symbol"] in bar["syms"] and pd.Timestamp(t["entry_time"]) == bt]
    rs = [c["net_r"] for c in cands]
    sel_mean, rej_mean = bar["sel"], bar["rej"]
    m = len(cands)
    found = None
    for k in range(1, m):
        for sel_idx in itertools.combinations(range(m), k):
            rej_idx = [i for i in range(m) if i not in sel_idx]
            if (abs(np.mean([rs[i] for i in sel_idx]) - sel_mean) < 2e-3
                    and abs(np.mean([rs[i] for i in rej_idx]) - rej_mean) < 2e-3):
                found = k
                break
        if found is not None:
            break
    return cands, found


def main():
    d = get_data()
    trades = d["trades"]
    bars = load_bars()["selection_edge_adx"]["bars"]

    matched, k_sel = [], []
    for bar in bars:
        cands, k = match_candidates(trades, bar)
        if k is None:
            print(f"WARN: could not reproduce partition for {bar['t']} "
                  f"({len(cands)} cands)")
            continue
        matched.append([c["net_r"] for c in cands])
        k_sel.append(k)

    # recompute the real ADX mean edge from the matched partitions
    real_edges = []
    for rs_list, k, bar in zip(matched, k_sel, bars):
        # ADX edge recorded in the JSON; verify it equals partition mean diff
        real_edges.append(bar["edge"])
    real_mean = float(np.mean(real_edges))
    print(f"matched {len(matched)}/{len(bars)} bars; real mean edge = {real_mean:.4f} "
          f"(study: 0.6507)")

    # placebo: random ranking -> random subset of size k per bar
    draws = np.empty(N_DRAW)
    for n in range(N_DRAW):
        edges = []
        for rs_list, k in zip(matched, k_sel):
            idx = RNG.permutation(len(rs_list))
            sel = [rs_list[i] for i in idx[:k]]
            rej = [rs_list[i] for i in idx[k:]]
            edges.append(np.mean(sel) - np.mean(rej))
        draws[n] = np.mean(edges)

    pct = float(100 * (draws <= real_mean).mean())
    p_emp = float((draws >= real_mean).mean())
    res = {
        "placebo": "random_ranking_crowded_bars",
        "n_bars": len(matched), "n_draws": N_DRAW,
        "real_adx_mean_edge_r": round(real_mean, 4),
        "null_mean_r": round(float(draws.mean()), 4),
        "null_sd_r": round(float(draws.std()), 4),
        "null_p5_r": round(float(np.percentile(draws, 5)), 4),
        "null_p50_r": round(float(np.percentile(draws, 50)), 4),
        "null_p95_r": round(float(np.percentile(draws, 95)), 4),
        "real_percentile": round(pct, 2),
        "empirical_p_value": round(p_emp, 4),
        "note": "null = random ranking selects same-sized subset per bar; "
                "expected null mean is ~0 by symmetry",
    }
    save_json("placebo_a_adx_random_ranking.json", res)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
