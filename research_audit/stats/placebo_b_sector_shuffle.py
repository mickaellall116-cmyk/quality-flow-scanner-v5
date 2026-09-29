#!/usr/bin/env python3
"""PLACEBO (b): SHUFFLED SECTOR LABELS for the lone-wolf filter.

Null: sector RS carries no signal -> permute the sector_rs series across the
237 trades (preserving the marginal distribution), reapply the rule
(stock_rs > 0 & shuffled sector_rs <= 0), recompute the retained-vs-baseline
expectancy differential. Where does the real +0.1386R sit?
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import get_data, save_json

RNG = np.random.default_rng(20260925)
N_DRAW = 2000


def main():
    d = get_data()
    tr = d["trades"]
    stock_rs = np.array([t["stock_rs"] for t in tr])
    sector_rs = np.array([t["sector_rs"] for t in tr])
    rs = np.array([t["net_r"] for t in tr])
    assert not np.any(pd_isnan(stock_rs)) and not np.any(pd_isnan(sector_rs)), \
        "unexpected NaN RS values"

    baseline = rs.mean()
    real_blocked = (stock_rs > 0) & (sector_rs <= 0)
    real_delta = rs[~real_blocked].mean() - baseline
    print(f"real: blocked={real_blocked.sum()} delta={real_delta:.4f} (study 0.1386)")

    draws = np.empty(N_DRAW)
    n_blocked = np.empty(N_DRAW, dtype=int)
    for n in range(N_DRAW):
        shuf = RNG.permutation(sector_rs)
        blocked = (stock_rs > 0) & (shuf <= 0)
        n_blocked[n] = blocked.sum()
        draws[n] = rs[~blocked].mean() - baseline

    pct = float(100 * (draws <= real_delta).mean())
    p_emp = float((draws >= real_delta).mean())
    res = {
        "placebo": "shuffled_sector_rs_labels",
        "n_trades": len(tr), "n_draws": N_DRAW,
        "real_delta_r": round(float(real_delta), 4),
        "real_blocked_n": int(real_blocked.sum()),
        "null_mean_delta_r": round(float(draws.mean()), 4),
        "null_sd_delta_r": round(float(draws.std()), 4),
        "null_p5_r": round(float(np.percentile(draws, 5)), 4),
        "null_p50_r": round(float(np.percentile(draws, 50)), 4),
        "null_p95_r": round(float(np.percentile(draws, 95)), 4),
        "null_blocked_n_mean": round(float(n_blocked.mean()), 1),
        "null_blocked_n_sd": round(float(n_blocked.std()), 1),
        "real_percentile": round(pct, 2),
        "empirical_p_value": round(p_emp, 4),
        "note": "null = sector RS unrelated to trade outcomes; the rule blocks "
                "trades on stock strength vs shuffled sector weakness",
    }
    save_json("placebo_b_lonewolf_sector_shuffle.json", res)
    print(json.dumps(res, indent=1))


def pd_isnan(a):
    import pandas as pd
    return pd.isna(a)


if __name__ == "__main__":
    main()
