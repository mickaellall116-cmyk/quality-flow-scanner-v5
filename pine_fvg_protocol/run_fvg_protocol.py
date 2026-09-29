#!/usr/bin/env python3
"""CANONICAL-PROTOCOL STUDY B of 3: FVG-as-entry under the 12-step protocol.

Pre-registered in HYPOTHESIS.md (written before this ran). FVG definition FIXED
(no threshold search). Matched-trade framework: same setups, baseline entry vs
FVG entry; the decision metric is the SELECTION differential
(FVG-only bucket vs BASE-only bucket).

Research only. pine_backtest imported unmodified; nothing frozen touched.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_fvg_protocol")
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "pine_stalefvg_backtest"))
sys.path.insert(0, os.path.join(BASE, "pine_fvg_robustness"))
import pine_backtest as pb
from run_stalefvg import add_fvg_columns  # FVG port, unmodified
from run_fvg_robustness import (WATCHLIST, THEME, _orig_signal,
                                make_signal, PERTURB, net_r)  # noqa

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "fvg_protocol_results.json")
os.makedirs(OUTDIR, exist_ok=True)

COSTS = {"25bps": 0.0025, "50bps": 0.005, "75bps": 0.0075, "100bps": 0.01}
RNG = np.random.default_rng(42)

DEV_END = "2025-01-01"  # DEV: Oct2023-Dec2024 ; VALIDATION: Jan2025-Sep2026
WF_WINDOWS = [
    ("Oct2023-Sep2024", "train", "2023-10-01", "2024-10-01"),
    ("Oct2024-Mar2025", "test", "2024-10-01", "2025-04-01"),
    ("Apr2024-Mar2025", "train", "2024-04-01", "2025-04-01"),
    ("Apr2025-Sep2025", "test", "2025-04-01", "2025-10-01"),
    ("Oct2024-Sep2025", "train", "2024-10-01", "2025-10-01"),
    ("Oct2025-Mar2026", "test", "2025-10-01", "2026-04-01"),
    ("Apr2025-Mar2026", "train", "2025-04-01", "2026-04-01"),
    ("Apr2026-Sep2026", "test", "2026-04-01", "2026-10-01"),
]


def rs_of(trades, cost):
    return np.array([net_r(t, cost) for t in trades])


def exp_pf(rs):
    if len(rs) == 0:
        return None, None
    wins, losses = rs[rs > 0], rs[rs <= 0]
    gw, gl = wins.sum(), -losses.sum()
    return float(rs.mean()), (round(float(gw / gl), 3) if gl > 0 else None)


def max_dd(trades, cost):
    """Max drawdown of cumulative net-R equity curve in entry_time order."""
    if not trades:
        return None
    rs = rs_of(sorted(trades, key=lambda t: t["entry_time"]), cost)
    cum = np.concatenate([[0.0], np.cumsum(rs)])
    peak = np.maximum.accumulate(cum)
    dd = peak - cum
    return round(float(dd.max()), 3)


def year_of(t):
    return pd.Timestamp(t["signal_time"]).year


def main():
    # ---- load data + indicators (mirrors run_fvg_attribution) ----
    data, sig_index = {}, {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        if "Volume" not in df.columns or df["Volume"].isna().all():
            print(f"dropped {sym}", flush=True)
            continue
        df = pb.add_pine_indicators(df)
        df = add_fvg_columns(df)
        data[sym] = df
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

    # ---- generate both variants ----
    trades_by_var = {}
    for name in ["BASE", "FVG"]:
        pb.pine_buy_signal = _orig_signal if name == "BASE" else make_signal(PERTURB["FVG"])
        all_trades = []
        for sym in used:
            tr, _ = pb.gen_pine_trades(sym, data[sym])
            all_trades.extend(tr)
        all_trades.sort(key=lambda t: t["entry_time"])
        trades_by_var[name] = all_trades
    pb.pine_buy_signal = _orig_signal

    base, fvg = trades_by_var["BASE"], trades_by_var["FVG"]
    key = lambda t: (t["symbol"], t["signal_time"])
    bmap, fmap = {key(t): t for t in base}, {key(t): t for t in fvg}
    shared_keys = set(bmap) & set(fmap)
    base_only = [bmap[k] for k in sorted(set(bmap) - set(fmap))]
    fvg_only = [fmap[k] for k in sorted(set(fmap) - set(bmap))]
    shared_b = [bmap[k] for k in sorted(shared_keys)]
    shared_f = [fmap[k] for k in sorted(shared_keys)]

    res = {"hypothesis": "frozen in HYPOTHESIS.md (pre-run)",
           "n_base": len(base), "n_fvg": len(fvg),
           "n_shared": len(shared_keys), "n_base_only": len(base_only),
           "n_fvg_only": len(fvg_only)}

    # ---- STEP 2: same population — shared entry check + bucket expectancies ----
    c = 0.0025
    shared_d = rs_of(shared_f, c) - rs_of(shared_b, c)
    e_f, pf_f = exp_pf(rs_of(fvg, c))
    e_b, pf_b = exp_pf(rs_of(base, c))
    e_add, _ = exp_pf(rs_of(fvg_only, c))
    e_omit, _ = exp_pf(rs_of(base_only, c))
    res["step2_matched"] = {
        "shared_mean_delta_r": round(float(shared_d.mean()), 6),
        "shared_nonzero_deltas": int((np.abs(shared_d) > 1e-9).sum()),
        "expectancy_fvg": round(e_f, 4), "expectancy_base": round(e_b, 4),
        "pooled_differential_dE": round(e_f - e_b, 4),
        "pf_fvg": pf_f, "pf_base": pf_b,
        "fvg_only_expectancy": round(e_add, 4),
        "base_only_expectancy": round(e_omit, 4),
    }

    # ---- STEP 3: dev / validation ----
    res["step3_dev_validation"] = {}
    for cname, ccost in COSTS.items():
        d = {}
        for label, bucket in [("fvg_only", fvg_only), ("base_only", base_only),
                              ("shared", shared_b), ("fvg_all", fvg), ("base_all", base)]:
            dev = [t for t in bucket if t["signal_time"] < DEV_END]
            val = [t for t in bucket if t["signal_time"] >= DEV_END]
            ed, _ = exp_pf(rs_of(dev, ccost))
            ev, _ = exp_pf(rs_of(val, ccost))
            d[label] = {
                "dev": {"n": len(dev), "exp": round(ed, 4) if ed is not None else None},
                "val": {"n": len(val), "exp": round(ev, 4) if ev is not None else None},
            }
        res["step3_dev_validation"][cname] = d

    # ---- STEP 4: rolling walk-forward on the selection differential ----
    res["step4_walkforward"] = {"windows": [], "combined_test": None}
    test_rs_f, test_rs_b = [], []
    for wname, kind, start, end in WF_WINDOWS:
        fw = [t for t in fvg if start <= t["signal_time"] < end]
        bw = [t for t in base if start <= t["signal_time"] < end]
        ef, _ = exp_pf(rs_of(fw, 0.0025))
        eb, _ = exp_pf(rs_of(bw, 0.0025))
        rec = {"window": wname, "kind": kind, "n_fvg": len(fw), "n_base": len(bw),
               "dE": round((ef - eb), 4) if ef is not None and eb is not None else None}
        res["step4_walkforward"]["windows"].append(rec)
        if kind == "test":
            test_rs_f.extend(rs_of(fw, 0.0025).tolist())
            test_rs_b.extend(rs_of(bw, 0.0025).tolist())
    tf, tb = np.array(test_rs_f), np.array(test_rs_b)
    res["step4_walkforward"]["combined_test"] = {
        "n_fvg": len(tf), "n_base": len(tb),
        "dE_combined": round(float(tf.mean() - tb.mean()), 4),
    }

    # ---- STEP 5: year + regime splits ----
    res["step5_year_regime"] = {}
    for cname, ccost in COSTS.items():
        yd = {}
        for y in [2023, 2024, 2025, 2026]:
            fw = [t for t in fvg if year_of(t) == y]
            bw = [t for t in base if year_of(t) == y]
            ef, _ = exp_pf(rs_of(fw, ccost))
            eb, _ = exp_pf(rs_of(bw, ccost))
            yd[str(y)] = {"n_fvg": len(fw), "n_base": len(bw),
                          "dE": round(ef - eb, 4) if ef is not None and eb is not None else None}
        rg = {}
        for r in ["bull", "bear/sideways", "unknown"]:
            fw = [t for t in fvg if regime_at(t["signal_time"]) == r]
            bw = [t for t in base if regime_at(t["signal_time"]) == r]
            ef, _ = exp_pf(rs_of(fw, ccost))
            eb, _ = exp_pf(rs_of(bw, ccost))
            rg[r] = {"n_fvg": len(fw), "n_base": len(bw),
                     "dE": round(ef - eb, 4) if ef is not None and eb is not None else None}
        res["step5_year_regime"][cname] = {"by_year": yd, "by_regime": rg}

    # ---- STEP 6: cost stress ----
    res["step6_cost_stress"] = {}
    for cname, ccost in COSTS.items():
        ef, pfv = exp_pf(rs_of(fvg, ccost))
        eb, pfb = exp_pf(rs_of(base, ccost))
        res["step6_cost_stress"][cname] = {
            "exp_fvg": round(ef, 4), "exp_base": round(eb, 4),
            "dE": round(ef - eb, 4), "pf_fvg": pfv, "pf_base": pfb,
        }

    # ---- STEP 7: selection-boundary perturbation (top-1 / top-3 removal) ----
    res["step7_perturbation"] = {}
    fo_sorted = sorted(fvg_only, key=lambda t: net_r(t, 0.0025), reverse=True)
    for drop_n, dlabel in [(0, "none"), (1, "drop_top1"), (3, "drop_top3")]:
        kept = fo_sorted[drop_n:]
        dropped = fo_sorted[:drop_n]
        # pooled differential with kept FVG-only + shared, vs full baseline
        fvg_kept = shared_f + kept
        ef, _ = exp_pf(rs_of(fvg_kept, 0.0025))
        eb, _ = exp_pf(rs_of(base, 0.0025))
        res["step7_perturbation"][dlabel] = {
            "n_fvg_only_kept": len(kept),
            "dropped_trades": [{"symbol": t["symbol"], "signal_time": t["signal_time"],
                                "net_r": round(float(net_r(t, 0.0025)), 3)} for t in dropped],
            "dE": round(ef - eb, 4),
        }

    # ---- STEP 8: concentration ----
    res["step8_concentration"] = {}
    add_rs = [(t["symbol"], THEME.get(t["symbol"], "Other"), float(net_r(t, 0.0025))) for t in fvg_only]
    omit_rs = [(t["symbol"], THEME.get(t["symbol"], "Other"), float(net_r(t, 0.0025))) for t in base_only]
    diff_total = sum(r for _, _, r in add_rs) - sum(r for _, _, r in omit_rs)
    res["step8_concentration"]["total_R_differential"] = round(diff_total, 3)
    # top-k trades by |contribution| — here top-k positive contributors in FVG-only
    top_trades = sorted(add_rs, key=lambda x: -x[2])
    for k in [1, 3, 5]:
        tk = top_trades[:k]
        share = sum(r for _, _, r in tk) / diff_total if diff_total else None
        res["step8_concentration"][f"top{k}_trades"] = {
            "trades": [{"symbol": s, "net_r": round(r, 3)} for s, _, r in tk],
            "sum_r": round(sum(r for _, _, r in tk), 3),
            "share_of_differential": round(share, 3) if share is not None else None,
        }
    for grp_name, idx in [("symbol", 0), ("theme", 1)]:
        agg = {}
        for s, th, r in add_rs:
            k = s if idx == 0 else th
            agg[k] = agg.get(k, 0) + r
        ranked = sorted(agg.items(), key=lambda x: -x[1])
        out = {}
        for k in [1, 3, 5]:
            tk = ranked[:k]
            share = sum(v for _, v in tk) / diff_total if diff_total else None
            out[f"top{k}_{grp_name}"] = {
                "members": [(n_, round(v, 3)) for n_, v in tk],
                "sum_r": round(sum(v for _, v in tk), 3),
                "share_of_differential": round(share, 3) if share is not None else None,
            }
        res["step8_concentration"][f"by_{grp_name}"] = out
    # best year
    yagg = {}
    for t in fvg_only:
        y = year_of(t)
        yagg[y] = yagg.get(y, 0) + float(net_r(t, 0.0025))
    for t in base_only:
        y = year_of(t)
        yagg[y] = yagg.get(y, 0) - float(net_r(t, 0.0025))
    ranked_y = sorted(yagg.items(), key=lambda x: -x[1])
    res["step8_concentration"]["by_year"] = {
        "members": [(str(y_), round(v, 3)) for y_, v in ranked_y],
        "top1_share": round(ranked_y[0][1] / diff_total, 3) if diff_total else None,
    }

    # ---- STEP 9: bootstrap ----
    B = 10000
    rf_all = rs_of(fvg, 0.0025)
    rb_all = rs_of(base, 0.0025)
    dE_boot = np.empty(B)
    for i in range(B):
        bf = RNG.choice(rf_all, size=len(rf_all), replace=True)
        bb = RNG.choice(rb_all, size=len(rb_all), replace=True)
        dE_boot[i] = bf.mean() - bb.mean()
    res["step9_bootstrap"] = {
        "B": B, "seed": 42,
        "frac_dE_positive": round(float((dE_boot > 0).mean()), 4),
        "frac_dE_gt_0_02": round(float((dE_boot > 0.02).mean()), 4),
        "p5": round(float(np.percentile(dE_boot, 5)), 4),
        "p50": round(float(np.percentile(dE_boot, 50)), 4),
        "p95": round(float(np.percentile(dE_boot, 95)), 4),
        "observed_dE": res["step2_matched"]["pooled_differential_dE"],
    }

    # ---- STEP 10: leave-one-symbol-out ----
    res["step10_loso"] = {}
    for sym in used:
        fw = [t for t in fvg if t["symbol"] != sym]
        bw = [t for t in base if t["symbol"] != sym]
        ef, _ = exp_pf(rs_of(fw, 0.0025))
        eb, _ = exp_pf(rs_of(bw, 0.0025))
        res["step10_loso"][sym] = {
            "n_fvg": len(fw), "n_base": len(bw),
            "dE": round(ef - eb, 4),
            "sign_flipped": bool((ef - eb) <= 0),
        }

    # ---- STEP 11: economic effect ----
    res["step11_economic"] = {}
    for cname, ccost in COSTS.items():
        rf, rb = rs_of(fvg, ccost), rs_of(base, ccost)
        ef, pfv = exp_pf(rf)
        eb, pfb = exp_pf(rb)
        res["step11_economic"][cname] = {
            "d_expectancy": round(ef - eb, 4),
            "d_pf": round(pfv - pfb, 3) if pfv is not None and pfb is not None else None,
            "d_max_dd": None,  # filled below at 25bps-equivalent equity basis per cost
            "trades_added": len(fvg_only), "trades_removed": len(base_only),
            "opportunity_cost_added_bucket_exp": round(float(rs_of(fvg_only, ccost).mean()), 4),
            "opportunity_cost_removed_bucket_exp": round(float(rs_of(base_only, ccost).mean()), 4),
            "total_R_fvg": round(float(rf.sum()), 3),
            "total_R_base": round(float(rb.sum()), 3),
            "return_per_risk_fvg": None, "return_per_risk_base": None,
        }
    # DD + return-per-risk at 25bps (equity-curve basis)
    dd_f = max_dd(fvg, 0.0025)
    dd_b = max_dd(base, 0.0025)
    tot_f = float(rs_of(fvg, 0.0025).sum())
    tot_b = float(rs_of(base, 0.0025).sum())
    res["step11_economic"]["25bps"]["d_max_dd"] = round(dd_f - dd_b, 3)
    res["step11_economic"]["dd_detail"] = {"max_dd_fvg": dd_f, "max_dd_base": dd_b}
    res["step11_economic"]["25bps"]["return_per_risk_fvg"] = round(tot_f / dd_f, 3) if dd_f else None
    res["step11_economic"]["25bps"]["return_per_risk_base"] = round(tot_b / dd_b, 3) if dd_b else None

    # ---- STEP 12: sidecar note ----
    res["step12_forward"] = {
        "note": "Exact FVG version papered live via FVG paper sidecar since 2026-09-23. "
                "This study does not change it. Forward validation is the arbiter; "
                "revisit at the ~50-signal checkpoint (late Oct 2026).",
    }

    with open(OUT, "w") as f:
        json.dump(res, f, indent=1, default=str)
    print(f"wrote {OUT}")
    print("pooled dE:", res["step2_matched"]["pooled_differential_dE"])
    print("drop_top1 dE:", res["step7_perturbation"]["drop_top1"]["dE"],
          "| drop_top3 dE:", res["step7_perturbation"]["drop_top3"]["dE"])
    print("bootstrap frac>0:", res["step9_bootstrap"]["frac_dE_positive"])
    print("LOSO sign flips:", [s for s, r in res["step10_loso"].items() if r["sign_flipped"]])


if __name__ == "__main__":
    main()
