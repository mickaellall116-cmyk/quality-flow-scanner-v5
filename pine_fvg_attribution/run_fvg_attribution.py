#!/usr/bin/env python3
"""Confirmatory Study 2: FVG-as-entry attribution — WHERE does the edge come from?

Re-uses the canonical pipeline from pine_fvg_robustness (run_fvg_robustness.py)
with per-trade capture. Question: is FVG improving trade QUALITY, or merely
changing the SAMPLE? Do NOT tune FVG thresholds — definition fixed.

Components:
  1. Re-verify shared-setup entry-price/timing = 0.0000R (entry diff, stop dist)
  2. Avoided losers: the 34 BASE-only trades — losers or just below-average?
  3. Added winners: the 63 FVG-only trades — concentration vs breadth
  4. Stop geometry: stop distances (entry-stop as % of entry and vs ATR) by bucket
  5. Sector/symbol concentration of the FVG-only and BASE-only buckets
  6. Regime dependence: identify the 4 outsized 2024 bear trades explicitly
  7. Walk-forward ON THE BUCKETS: FVG-only / BASE-only in train (<=2024) vs
     test (>=2025) — does the selection effect persist out-of-sample?

Research only. pine_backtest imported unmodified; nothing frozen touched.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_fvg_attribution")
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "pine_stalefvg_backtest"))
sys.path.insert(0, os.path.join(BASE, "pine_fvg_robustness"))
import pine_backtest as pb
from run_stalefvg import add_fvg_columns  # FVG port, unmodified
from run_fvg_robustness import (WATCHLIST, THEME, fvg_sub, _orig_signal,
                                make_signal, PERTURB, net_r, dist_stats,
                                add_excursion, WF_SPLIT)  # noqa

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "fvg_attribution_results.json")
os.makedirs(OUTDIR, exist_ok=True)

COST = 0.0025


def slim(t):
    return {
        "symbol": t["symbol"], "signal_time": t["signal_time"],
        "entry": t["entry"], "stop": t["stop"], "exit": t["exit"],
        "entry_time": t.get("entry_time"), "exit_time": t.get("exit_time"),
        "hold_bars": t.get("hold_bars"), "reason": t.get("reason"),
        "net_r": net_r(t, COST),
        "mfe_r": t.get("mfe_r"), "mae_r": t.get("mae_r"),
        "stop_pct": (t["entry"] - t["stop"]) / t["entry"] * 100
        if t["entry"] and t["stop"] else None,
    }


def bucket_breakdown(trades, label):
    """Concentration + shape stats for a bucket."""
    rs = np.array([t["net_r"] for t in trades])
    n = len(rs)
    tot = rs.sum()
    order = np.argsort(rs)  # ascending
    top5 = rs[order[-5:][::-1]]
    bot5 = rs[order[:5]]
    by_sym = {}
    for t in trades:
        by_sym.setdefault(t["symbol"], []).append(t["net_r"])
    sym_mean = {s: float(np.mean(v)) for s, v in sorted(by_sym.items())}
    sym_sum = {s: float(np.sum(v)) for s, v in sorted(by_sym.items())}
    return {
        "label": label, "n": n,
        "expectancy_net_r": round(float(rs.mean()), 4),
        "total_r": round(float(tot), 3),
        "win_rate_pct": round(float((rs > 0).mean()) * 100, 1),
        "top5_r": [round(float(x), 3) for x in top5],
        "top5_sum_r": round(float(top5.sum()), 3),
        "top5_share_of_total_pct": round(float(top5.sum() / tot * 100), 1) if tot else None,
        "worst5_r": [round(float(x), 3) for x in bot5],
        "median_r": round(float(np.median(rs)), 4),
        "p75_r": round(float(np.percentile(rs, 75)), 3),
        "p25_r": round(float(np.percentile(rs, 25)), 3),
        "max_r": round(float(rs.max()), 3),
        "min_r": round(float(rs.min()), 3),
        "trades_over_2R": int((rs > 2).sum()),
        "trades_under_neg1R": int((rs < -1).sum()),
        "mean_stop_pct": round(float(np.mean([t["stop_pct"] for t in trades
                                              if t["stop_pct"]])), 2),
        "per_symbol_sum_r": {k: round(v, 3) for k, v in sym_sum.items()},
        "per_symbol_mean_r": {k: round(v, 3) for k, v in sym_mean.items()},
        "top_trades": sorted(trades, key=lambda t: t["net_r"], reverse=True)[:8],
    }


def main():
    data, closes, sig_index = {}, {}, {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        if "Volume" not in df.columns or df["Volume"].isna().all():
            print(f"dropped {sym}", flush=True)
            continue
        df = pb.add_pine_indicators(df)
        df = add_fvg_columns(df)
        data[sym] = df
        closes[sym] = df["Close"]
        sig_index[sym] = {df.index[i].isoformat(): i for i in range(len(df))}
    used = [s for s in WATCHLIST if s in data]

    q = data["QQQ"]
    q_sma200 = q["Close"].rolling(200).mean()
    q_idx = sig_index["QQQ"]

    def regime_at(signal_time):
        i = q_idx.get(signal_time)
        if i is None or pd.isna(q_sma200.iloc[i]):
            return "unknown"
        return "bull" if q["Close"].iloc[i] > q_sma200.iloc[i] else "bear/sideways"

    atr_at = {}
    for sym in used:
        df = data[sym]
        atr_at[sym] = {df.index[i].isoformat(): float(df["atr_base"].iloc[i])
                       if "atr_base" in df.columns else np.nan
                       for i in range(len(df))}

    trades_by_var = {}
    for name in ["BASE", "FVG"]:
        pb.pine_buy_signal = _orig_signal if name == "BASE" else make_signal(PERTURB["FVG"])
        all_trades = []
        for sym in used:
            tr, _ = pb.gen_pine_trades(sym, data[sym])
            all_trades.extend(tr)
        all_trades.sort(key=lambda t: t["entry_time"])
        add_excursion(all_trades, data, sig_index)
        trades_by_var[name] = all_trades
    pb.pine_buy_signal = _orig_signal

    base, fvg = trades_by_var["BASE"], trades_by_var["FVG"]
    key = lambda t: (t["symbol"], t["signal_time"])
    bmap, fmap = {key(t): t for t in base}, {key(t): t for t in fvg}
    shared_keys = set(bmap) & set(fmap)
    base_only = [slim(bmap[k]) for k in sorted(set(bmap) - set(fmap))]
    fvg_only = [slim(fmap[k]) for k in sorted(set(fmap) - set(bmap))]
    shared_pairs = [(slim(bmap[k]), slim(fmap[k])) for k in sorted(shared_keys)]

    res = {"cost": COST, "wf_split": WF_SPLIT}

    # 1. shared-setup re-verification (entry + stop geometry)
    ed = np.array([f["entry"] - b["entry"] for b, f in shared_pairs])
    sd = np.array([f["stop_pct"] - b["stop_pct"] for b, f in shared_pairs])
    rd = np.array([f["net_r"] - b["net_r"] for b, f in shared_pairs])
    res["shared_verify"] = {
        "n_shared": len(shared_pairs),
        "mean_entry_diff_usd": round(float(ed.mean()), 6),
        "mean_abs_entry_diff_usd": round(float(np.abs(ed).mean()), 6),
        "max_abs_entry_diff_usd": round(float(np.abs(ed).max()), 6),
        "mean_stopdist_pct_diff": round(float(sd.mean()), 6),
        "max_abs_stopdist_pct_diff": round(float(np.abs(sd).max()), 6),
        "shared_mean_delta_r": round(float(rd.mean()), 6),
        "shared_mean_r_base": round(float(np.mean([b["net_r"] for b, _ in shared_pairs])), 4),
        "shared_mean_r_fvg": round(float(np.mean([f["net_r"] for _, f in shared_pairs])), 4),
        "nonzero_deltas": int((np.abs(rd) > 1e-9).sum()),
    }

    # 2/3. bucket breakdowns
    res["fvg_only"] = bucket_breakdown(fvg_only, "FVG-only (added)")
    res["base_only"] = bucket_breakdown(base_only, "BASE-only (omitted)")
    res["shared"] = bucket_breakdown([slim(bmap[k]) for k in sorted(shared_keys)], "shared")

    # 4. stop geometry: risk width vs ATR
    def stop_atr(tr):
        a = atr_at.get(tr["symbol"], {}).get(tr["signal_time"])
        if a is None or (isinstance(a, float) and np.isnan(a)) or a <= 0:
            return None
        return (tr["entry"] - tr["stop"]) / a

    res["stop_geometry"] = {}
    for label, bucket in [("shared", [slim(bmap[k]) for k in sorted(shared_keys)]),
                          ("fvg_only", fvg_only), ("base_only", base_only)]:
        widths = [stop_atr(t) for t in bucket]
        widths = [w for w in widths if w]
        res["stop_geometry"][label] = {
            "n": len(bucket),
            "mean_stop_atr_mult": round(float(np.mean(widths)), 3) if widths else None,
            "mean_stop_pct": round(float(np.mean([t["stop_pct"] for t in bucket])), 2),
        }

    # 5. theme concentration of the buckets
    def per_theme(trades):
        out = {}
        for t in trades:
            out.setdefault(THEME.get(t["symbol"], "Other"), []).append(t["net_r"])
        return {th: {"n": len(v), "sum_r": round(float(np.sum(v)), 3),
                     "mean_r": round(float(np.mean(v)), 3)}
                for th, v in sorted(out.items())}

    res["theme_fvg_only"] = per_theme(fvg_only)
    res["theme_base_only"] = per_theme(base_only)

    # 6. regime dependence — identify the 2024 bear trades explicitly
    def yreg(t):
        return (str(pd.Timestamp(t["signal_time"]).year), regime_at(t["signal_time"]))

    res["outsized_2024_bear"] = []
    for label, bucket, raw in [("FVG", fvg_only, fvg), ("BASE", base_only, base),
                               ("shared", [slim(bmap[k]) for k in sorted(shared_keys)], None)]:
        sel = [t for t in bucket if yreg(t) == ("2024", "bear/sideways")]
        if label == "FVG":
            res["outsized_2024_bear"] = sorted(sel, key=lambda t: -t["net_r"])
        res[f"bucket_2024_bear_{label.lower()}"] = {
            "n": len(sel), "sum_r": round(float(np.sum([t["net_r"] for t in sel])), 3),
            "mean_r": round(float(np.mean([t["net_r"] for t in sel])), 3) if sel else None,
        }

    # regime x bucket summary (which bucket/regime supplies the +0.046)
    res["regime_bucket"] = {}
    for bname, bucket in [("shared", [slim(bmap[k]) for k in sorted(shared_keys)]),
                          ("fvg_only", fvg_only), ("base_only", base_only)]:
        d = {}
        for t in bucket:
            y, r = yreg(t)
            d.setdefault(f"{y} {r}", []).append(t["net_r"])
        res["regime_bucket"][bname] = {k: {"n": len(v), "sum_r": round(float(np.sum(v)), 3),
                                            "mean_r": round(float(np.mean(v)), 3)}
                                       for k, v in sorted(d.items())}

    # 7. walk-forward ON THE BUCKETS (does the selection effect persist?)
    def split(bucket):
        return ([t for t in bucket if t["signal_time"] < WF_SPLIT],
                [t for t in bucket if t["signal_time"] >= WF_SPLIT])

    res["walkforward_buckets"] = {}
    for bname, bucket in [("shared", [slim(bmap[k]) for k in sorted(shared_keys)]),
                          ("fvg_only", fvg_only), ("base_only", base_only)]:
        tr, te = split(bucket)
        res["walkforward_buckets"][bname] = {
            "train": {"n": len(tr), "mean_r": round(float(np.mean([t["net_r"] for t in tr])), 4)
                       if tr else None, "sum_r": round(float(np.sum([t["net_r"] for t in tr])), 3)},
            "test": {"n": len(te), "mean_r": round(float(np.mean([t["net_r"] for t in te])), 4)
                      if te else None, "sum_r": round(float(np.sum([t["net_r"] for t in te])), 3)},
        }

    with open(OUT, "w") as f:
        json.dump(res, f, indent=1, default=str)
    print(f"wrote {OUT}")
    print(f"repro: n_base={len(base)} n_fvg={len(fvg)} shared={len(shared_pairs)} "
          f"base_only={len(base_only)} fvg_only={len(fvg_only)}")
    print("shared delta R:", res["shared_verify"]["shared_mean_delta_r"])
    print("fvg_only exp:", res["fvg_only"]["expectancy_net_r"],
          "| base_only exp:", res["base_only"]["expectancy_net_r"])


if __name__ == "__main__":
    main()
