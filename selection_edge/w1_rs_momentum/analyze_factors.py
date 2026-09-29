"""W1 worker: full selection-edge protocol for F1 (RS vs SPY) and F2 (acceleration).

Protocol per factor (pre-registered thresholds, never fit):
  1. headline split @50bps: selection rate, selected/unselected expectancy, delta
  2. cost ladder 25/50/75/100bps on the delta
  3. dev (Oct2023-Dec2024) / val (Jan2025-Sep2026); verdict on val
  4. year splits 2024/2025/2026
  5. rolling 12mo-observe / 6mo-test walk-forward (fixed threshold; observe = context)
  6. perturbation (not optimization)
  7. concentration: drop top 1/3/5 selected-R symbols, recompute delta
  8. bootstrap 10,000 on the delta (trade-level primary + symbol-block secondary)
  9. leave-one-symbol-out
  10. absolute: does selected clear zero?

Writes F1.json, F2.json (all numbers).
"""

import json
import os
import sys

import numpy as np
import pandas as pd

OUT = os.path.expanduser("~/workspace/quality-flow-scanner-v5/selection_edge/w1_rs_momentum")

COSTS = ["25bps", "50bps", "75bps", "100bps"]
RKEY = {c: f"net_r_{c}" for c in COSTS}
HEAD = "50bps"

rng = np.random.default_rng(20260924)


def load():
    with open(os.path.join(OUT, "factor_trades.json")) as fh:
        trades = json.load(fh)
    with open(os.path.join(OUT, "signals_factors.json")) as fh:
        sigs = json.load(fh)
    return trades, sigs


def sel_fns(trades):
    """Selection masks. Thresholds pre-registered; median-split diagnostic only."""
    f1 = np.array([t["f1_20d"] for t in trades], dtype=float)
    med = float(np.nanmedian(f1))
    return {
        "F1": {
            "base": ("f1_20d>0", lambda t: t["f1_20d"] is not None and t["f1_20d"] > 0),
            "variants": {
                "f1_15d>0": lambda t: t["f1_15d"] is not None and t["f1_15d"] > 0,
                "f1_25d>0": lambda t: t["f1_25d"] is not None and t["f1_25d"] > 0,
                f"f1_median_split>{med:.4f} (diagnostic, non-causal)":
                    (lambda m: (lambda t: t["f1_20d"] is not None and t["f1_20d"] > m))(med),
            },
            "median": med,
        },
        "F2": {
            "base": ("f2_10_50>0", lambda t: t["f2_10_50"] is not None and t["f2_10_50"] > 0),
            "variants": {
                "f2_20_50>0": lambda t: t["f2_20_50"] is not None and t["f2_20_50"] > 0,
                "f2_10_40>0": lambda t: t["f2_10_40"] is not None and t["f2_10_40"] > 0,
                "f2_10_60>0": lambda t: t["f2_10_60"] is not None and t["f2_10_60"] > 0,
                "f2_20_60>0": lambda t: t["f2_20_60"] is not None and t["f2_20_60"] > 0,
            },
        },
    }


def split_stats(trades, mask, cost=HEAD):
    rs = np.array([t[RKEY[cost]] for t in trades])
    m = np.array([bool(mask(t)) for t in trades])
    out = {"n": len(trades), "n_sel": int(m.sum()),
           "selection_rate": round(float(m.mean()), 4) if len(trades) else 0.0}
    if m.sum() == 0 or m.sum() == len(trades):
        out.update({"sel_exp": None, "unsel_exp": None, "delta": None})
        return out
    se, ue = rs[m].mean(), rs[~m].mean()
    out.update({
        "n_unsel": int((~m).sum()),
        "sel_exp": round(float(se), 4), "unsel_exp": round(float(ue), 4),
        "delta": round(float(se - ue), 4),
        "sel_total_r": round(float(rs[m].sum()), 2),
        "unsel_total_r": round(float(rs[~m].sum()), 2),
        "sel_win_rate": round(float((rs[m] > 0).mean()), 3),
        "unsel_win_rate": round(float((rs[~m] > 0).mean()), 3),
    })
    return out


def date_of(t):
    return pd.Timestamp(t["signal_bar_close_at"])


def in_range(t, a, b):
    d = date_of(t)
    return pd.Timestamp(a, tz="America/New_York") <= d < pd.Timestamp(b, tz="America/New_York")


def bootstrap_delta(trades, mask, cost=HEAD, n_iter=10000, block="trade"):
    rs = np.array([t[RKEY[cost]] for t in trades])
    m = np.array([bool(mask(t)) for t in trades])
    if m.sum() == 0 or m.sum() == len(trades):
        return None
    if block == "trade":
        idx = np.arange(len(trades))
        deltas = np.empty(n_iter)
        for b in range(n_iter):
            s = rng.integers(0, len(trades), len(trades))
            ms = m[s]
            if ms.sum() == 0 or ms.sum() == len(s):
                deltas[b] = np.nan
                continue
            deltas[b] = rs[s][ms].mean() - rs[s][~ms].mean()
    else:  # symbol-block
        syms = np.array([t["symbol"] for t in trades])
        usym = np.unique(syms)
        deltas = np.empty(n_iter)
        for b in range(n_iter):
            pick = rng.choice(usym, len(usym), replace=True)
            s = np.concatenate([np.flatnonzero(syms == p) for p in pick])
            ms = m[s]
            if ms.sum() == 0 or ms.sum() == len(s):
                deltas[b] = np.nan
                continue
            deltas[b] = rs[s][ms].mean() - rs[s][~ms].mean()
    d = deltas[~np.isnan(deltas)]
    return {
        "n_iter": n_iter, "block": block,
        "mean": round(float(d.mean()), 4),
        "ci95_lo": round(float(np.percentile(d, 2.5)), 4),
        "ci95_hi": round(float(np.percentile(d, 97.5)), 4),
        "p_positive": round(float((d > 0).mean()), 4),
    }


def loso(trades, mask, cost=HEAD):
    syms = sorted(set(t["symbol"] for t in trades))
    ds = []
    for s in syms:
        sub = [t for t in trades if t["symbol"] != s]
        st = split_stats(sub, mask, cost)
        if st["delta"] is not None:
            ds.append(st["delta"])
    ds = np.array(ds)
    return {
        "n_symbols": len(syms), "min": round(float(ds.min()), 4),
        "q25": round(float(np.percentile(ds, 25)), 4),
        "median": round(float(np.median(ds)), 4),
        "mean": round(float(ds.mean()), 4),
        "max": round(float(ds.max()), 4),
        "n_negative": int((ds < 0).sum()),
    }


def concentration(trades, mask, cost=HEAD):
    """Drop top-k symbols by selected total-R contribution; recompute delta."""
    rs = np.array([t[RKEY[cost]] for t in trades])
    m = np.array([bool(mask(t)) for t in trades])
    contrib = {}
    for t, r, sel in zip(trades, rs, m):
        if sel:
            contrib[t["symbol"]] = contrib.get(t["symbol"], 0.0) + r
    ranked = sorted(contrib.items(), key=lambda kv: -kv[1])
    out = {"top_symbols_by_selected_r": [(s, round(v, 2)) for s, v in ranked[:8]]}
    for k in (1, 3, 5):
        drop = set(s for s, _ in ranked[:k])
        sub = [t for t in trades if t["symbol"] not in drop]
        st = split_stats(sub, mask, cost)
        out[f"drop_top{k}"] = {"n": st["n"], "delta": st["delta"],
                               "sel_exp": st.get("sel_exp"),
                               "unsel_exp": st.get("unsel_exp")}
    return out


def run_factor(name, trades, sigs, sel, variants):
    rep = {"factor": name}
    mask = sel
    # candidate-level selection rate (pre-busy)
    cm = np.array([bool(mask(t)) for t in sigs])
    rep["candidate_selection_rate"] = round(float(cm.mean()), 4)
    rep["n_candidates"] = len(sigs)
    rep["headline"] = split_stats(trades, mask)
    rep["cost_ladder"] = {c: split_stats(trades, mask, c) for c in COSTS}
    dev = [t for t in trades if in_range(t, "2023-10-01", "2025-01-01")]
    val = [t for t in trades if in_range(t, "2025-01-01", "2026-10-01")]
    rep["dev"] = split_stats(dev, mask)
    rep["val"] = split_stats(val, mask)
    rep["years"] = {}
    for y, a, b in (("2024", "2024-01-01", "2025-01-01"),
                    ("2025", "2025-01-01", "2026-01-01"),
                    ("2026", "2026-01-01", "2026-10-01")):
        rep["years"][y] = split_stats([t for t in trades if in_range(t, a, b)], mask)
    # walk-forward: 12mo observe / 6mo test, stepped 6mo
    wf = []
    starts = [("2024-10-01", "2025-04-01"), ("2025-04-01", "2025-10-01"),
              ("2025-10-01", "2026-04-01"), ("2026-04-01", "2026-10-01")]
    for a, b in starts:
        sub = [t for t in trades if in_range(t, a, b)]
        wf.append({"test_window": f"{a}..{b}", **split_stats(sub, mask)})
    rep["walk_forward_12_6"] = wf
    rep["perturbations"] = {}
    for vname, vmask in variants.items():
        rep["perturbations"][vname] = {
            "headline": split_stats(trades, vmask),
            "val": split_stats(val, vmask),
        }
    rep["concentration"] = concentration(trades, mask)
    rep["bootstrap_trade"] = bootstrap_delta(trades, mask, block="trade")
    rep["bootstrap_symbol_block"] = bootstrap_delta(trades, mask, block="symbol")
    rep["loso"] = loso(trades, mask)
    # absolute: selected CI at headline cost
    rs = np.array([t[RKEY[HEAD]] for t in trades])
    m = np.array([bool(mask(t)) for t in trades])
    if m.sum() > 0:
        sel_rs = rs[m]
        bs = np.array([sel_rs[rng.integers(0, len(sel_rs), len(sel_rs))].mean()
                       for _ in range(10000)])
        rep["selected_absolute"] = {
            "exp": round(float(rs[m].mean()), 4),
            "ci95": [round(float(np.percentile(bs, 2.5)), 4),
                     round(float(np.percentile(bs, 97.5)), 4)],
            "n": int(m.sum()),
        }
    return rep


def main():
    trades, sigs = load()
    print(f"trades={len(trades)} signals={len(sigs)}", flush=True)
    fns = sel_fns(trades)
    f1 = fns["F1"]
    print(f"F1 pooled median (diagnostic): {f1['median']:.4f}", flush=True)
    rep1 = run_factor("F1_rs_vs_spy_20d", trades, sigs, f1["base"][1], f1["variants"])
    rep1["rule"] = "RS(20d stock) - RS(20d SPY) > 0, strict-PIT daily endpoint"
    rep1["preregistered_threshold"] = "f1_20d>0"
    with open(os.path.join(OUT, "F1.json"), "w") as fh:
        json.dump(rep1, fh, indent=1)
    print("wrote F1.json", flush=True)
    f2 = fns["F2"]
    rep2 = run_factor("F2_momentum_acceleration_10_50", trades, sigs, f2["base"][1], f2["variants"])
    rep2["rule"] = "ret(10d) - ret(preceding 50d) > 0, strict-PIT daily closes"
    rep2["preregistered_threshold"] = "f2_10_50>0"
    with open(os.path.join(OUT, "F2.json"), "w") as fh:
        json.dump(rep2, fh, indent=1)
    print("wrote F2.json", flush=True)


if __name__ == "__main__":
    main()
