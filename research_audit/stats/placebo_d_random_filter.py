#!/usr/bin/env python3
"""PLACEBO (d): RANDOMIZED FILTER blocking the same NUMBER of trades.

Null: blocking 83 of 237 trades at random does nothing -> the retained-minus-
baseline expectancy differential centers at ~0 by symmetry. Where does the
lone-wolf filter's real +0.1386R sit in the random-block distribution?
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import get_data, save_json

RNG = np.random.default_rng(20260926)
N_DRAW = 2000
N_BLOCK = 83  # same number the lone-wolf filter blocks


def main():
    d = get_data()
    rs = np.array([t["net_r"] for t in d["trades"]])
    n = len(rs)
    baseline = rs.mean()
    real_delta = 0.1386  # verified retained 0.3773 - baseline 0.2388

    draws = np.empty(N_DRAW)
    for i in range(N_DRAW):
        blocked = RNG.choice(n, size=N_BLOCK, replace=False)
        keep = np.ones(n, dtype=bool)
        keep[blocked] = False
        draws[i] = rs[keep].mean() - baseline

    pct = float(100 * (draws <= real_delta).mean())
    p_emp = float((draws >= real_delta).mean())
    res = {
        "placebo": "random_filter_same_block_count",
        "n_trades": n, "n_blocked": N_BLOCK, "n_draws": N_DRAW,
        "real_delta_r": real_delta,
        "null_mean_delta_r": round(float(draws.mean()), 4),
        "null_sd_delta_r": round(float(draws.std()), 4),
        "null_p5_r": round(float(np.percentile(draws, 5)), 4),
        "null_p50_r": round(float(np.percentile(draws, 50)), 4),
        "null_p95_r": round(float(np.percentile(draws, 95)), 4),
        "real_percentile": round(pct, 2),
        "empirical_p_value": round(p_emp, 4),
        "note": "null = the specific WHICH of the 83 blocked trades is random; "
                "symmetric so null mean ~0",
    }
    save_json("placebo_d_random_filter.json", res)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
