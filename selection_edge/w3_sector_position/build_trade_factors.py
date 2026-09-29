"""Compute F5/F6 factor records for the two trade populations.

P1: canonical_trades.json (taken trades, has net_r_*bps fields) - primary.
P2: v3_trades.json (independent trades; net R via net_r_legs) - robustness.

Working set only (masked names excluded). Includes all pre-registered
perturbation variants: F5 top 2/4, windows 15/25d; F6 thresholds 0.7/0.9,
windows 40/90d.
"""
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import factors as F
from factors import CB, pit_endpoint

OUT = os.path.dirname(os.path.abspath(__file__))

F5_VARS = {
    "base":   dict(window=20, top_k=3),
    "top2":   dict(window=20, top_k=2),
    "top4":   dict(window=20, top_k=4),
    "w15":    dict(window=15, top_k=3),
    "w25":    dict(window=25, top_k=3),
}
F6_VARS = {
    "base": dict(window=60, threshold=0.8),
    "t07":  dict(window=60, threshold=0.7),
    "t09":  dict(window=60, threshold=0.9),
    "w40":  dict(window=40, threshold=0.8),
    "w90":  dict(window=90, threshold=0.8),
}

sys.path.insert(0, CB)
from run_ablation import net_r_legs
COSTS = [0.0025, 0.005, 0.0075, 0.01]


def build(trades, tag):
    syms, sec = F.working_set()
    wset = set(syms)
    rows = []
    n_skip = 0
    for t in trades:
        s = t["symbol"]
        if s not in wset:
            continue
        ts = pd.Timestamp(t["signal_bar_close_at"])
        sector = sec[s]
        rec = {"signal_id": t["signal_id"], "symbol": s,
               "signal_bar_close_at": t["signal_bar_close_at"],
               "sector": sector, "blended_r": t["blended_r"]}
        if tag == "P1":
            for bps in COSTS:
                rec[f"net_r_{bps*10000:.0f}bps"] = t[f"net_r_{bps*10000:.0f}bps"]
        else:
            for bps in COSTS:
                rec[f"net_r_{bps*10000:.0f}bps"] = net_r_legs(t, bps)
        for name, kw in F5_VARS.items():
            sel, det = F.f5_sector_rank(s, sector, ts, window=kw["window"],
                                        top_k=kw["top_k"])
            rec[f"f5_{name}"] = bool(sel)
            if name == "base":
                rec["f5_rank"] = det.get("rank")
        for name, kw in F6_VARS.items():
            pos, _, _ = F.f6_position(s, ts, window=kw["window"])
            rec[f"f6_{name}_pos"] = None if pos is None else float(pos)
            rec[f"f6_{name}"] = bool(pos is not None and pos > kw["threshold"])
        rows.append(rec)
    print(f"[{tag}] trades: {len(rows)} (skipped {n_skip})")
    with open(os.path.join(OUT, f"trade_factors_{tag}.json"), "w") as fh:
        json.dump(rows, fh)
    return rows


def main():
    with open(os.path.join(CB, "canonical_trades.json")) as fh:
        p1 = json.load(fh)
    with open(os.path.join(CB, "v3_trades.json")) as fh:
        p2 = json.load(fh)
    build(p1, "P1")
    build(p2, "P2")


if __name__ == "__main__":
    main()
