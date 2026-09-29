#!/usr/bin/env python3
"""PLACEBO (c): SHUFFLED FVG TAGS.

Null: FVG's trade SELECTION is meaningless -> the 97 trades unique to one
variant or the other (34 base-only + 63 fvg-only; the 203 shared trades fill
identically in both) are randomly re-labeled: 63 go to the "FVG variant" and
34 to "baseline" in each draw. Recompute the variant-vs-baseline expectancy
differential. Where does the real +0.0464R sit?

FVG variant trades are regenerated exactly as in pine_fvg_robustness
(monkey-patching pine_backtest.pine_buy_signal at runtime -- the file itself
is never edited; verified: 266 trades @ +0.2852R vs study 266 @ +0.2852R).
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "pine_fvg_robustness"))
import pine_backtest as pb  # noqa: E402
import run_fvg_robustness as fr  # noqa: E402
from common import get_data, save_json

RNG = np.random.default_rng(20260927)
N_DRAW = 2000
COST = 0.0025


def gen_fvg_variant_trades():
    data = {}
    for sym in fr.WATCHLIST:
        df = pd.read_pickle(os.path.join(fr.CACHE, f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        df = fr.add_fvg_columns(df)
        data[sym] = df
    pb.pine_buy_signal = fr.make_signal(fr.PERTURB["FVG"])
    try:
        trades = []
        for sym in fr.WATCHLIST:
            t, _ = pb.gen_pine_trades(sym, data[sym])
            trades.extend(t)
        trades.sort(key=lambda t: t["entry_time"])
    finally:
        pb.pine_buy_signal = fr._orig_signal
    out = []
    for t in trades:
        net_r = pb._outcome(t["entry"], t["stop"], t["exit"], COST)[2]
        out.append((t["symbol"], t["signal_time"], float(net_r)))
    return out


def main():
    d = get_data()
    base = [(t["symbol"], t["signal_time"], t["net_r"]) for t in d["trades"]]
    fvg = gen_fvg_variant_trades()
    assert len(base) == 237 and len(fvg) == 266

    base_keys = {(s, st) for s, st, _ in base}
    fvg_keys = {(s, st) for s, st, _ in fvg}
    shared_keys = base_keys & fvg_keys
    base_only = [(s, st, r) for s, st, r in base if (s, st) not in shared_keys]
    fvg_only = [(s, st, r) for s, st, r in fvg if (s, st) not in shared_keys]
    print(f"shared={len(shared_keys)} (study 203), base_only={len(base_only)} "
          f"(study 34), fvg_only={len(fvg_only)} (study 63)")

    base_rs = np.array([r for _, _, r in base])
    shared_rs = np.array([r for s, st, r in fvg if (s, st) in shared_keys])
    baseline_mean = base_rs.mean()

    # verify the study's headline differential exactly
    fvg_mean = np.mean([r for _, _, r in fvg])
    real_delta = fvg_mean - baseline_mean
    print(f"real delta = {real_delta:.4f} (study: 0.0464)")

    # placebo: the 97 non-shared trades are the only ones whose assignment
    # differs between variants; shuffle their 63/34 assignment
    pool = np.array([r for _, _, r in base_only] + [r for _, _, r in fvg_only])
    assert len(pool) == 97
    n_fvg_only = len(fvg_only)  # 63

    draws = np.empty(N_DRAW)
    for i in range(N_DRAW):
        perm = RNG.permutation(pool)
        variant = np.concatenate([shared_rs, perm[:n_fvg_only]])
        draws[i] = variant.mean() - baseline_mean

    pct = float(100 * (draws <= real_delta).mean())
    p_emp = float((draws >= real_delta).mean())
    res = {
        "placebo": "shuffled_fvg_tags",
        "n_shared": len(shared_keys), "n_base_only": len(base_only),
        "n_fvg_only": len(fvg_only), "n_draws": N_DRAW,
        "real_delta_r": round(float(real_delta), 4),
        "fvg_only_exp_r": round(float(np.mean([r for _, _, r in fvg_only])), 4),
        "base_only_exp_r": round(float(np.mean([r for _, _, r in base_only])), 4),
        "null_mean_delta_r": round(float(draws.mean()), 4),
        "null_sd_delta_r": round(float(draws.std()), 4),
        "null_p5_r": round(float(np.percentile(draws, 5)), 4),
        "null_p50_r": round(float(np.percentile(draws, 50)), 4),
        "null_p95_r": round(float(np.percentile(draws, 95)), 4),
        "real_percentile": round(pct, 2),
        "empirical_p_value": round(p_emp, 4),
        "note": "null = which of the 97 variant-specific trades are "
                "'FVG-selected' is random; shared 203 trades fill identically",
    }
    save_json("placebo_c_fvg_tag_shuffle.json", res)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
