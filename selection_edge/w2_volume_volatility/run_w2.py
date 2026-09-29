"""W2 worker: test F3 (dollar-volume expansion) and F4 (volatility expansion)
as SELECTION factors on the masked working universe.

Population: canonical_trades.json (V5.4 Mode B accepted book, 374 trades)
minus trades on the 14 masked names -> 353 working trades. Each trade is
tagged with the factor value computed strict-PIT at its signal timestamp.

Protocol per selection_edge/FACTOR_MENU.md:
  dev Oct2023-Dec2024 / val Jan2025-Sep2026 (thresholds pre-registered, frozen)
  walk-forward 12mo-observe/6mo-test -> rolling 6mo test windows
  year splits 2024/2025/2026, costs 25/50/75/100bps RT
  perturbation, concentration (top-1/3/5 symbols), bootstrap >=5000 on delta,
  leave-one-symbol-out, absolute (does selected clear zero?)

Verdict gates: PASS = selected beats unselected on validation + costs +
perturbation, survives LOSO/concentration, selected clears zero.
MAYBE = directionally consistent but thin/fragile. FAIL = otherwise.

Writes F3.json, F4.json.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import factors  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
CB = os.path.join(BASE, "..", "..", "canonical_baseline")
RNG = np.random.default_rng(20260924)

MASKED = factors.MASKED_14

FACTOR_SPECS = {
    "F3": {
        "name": "dollar-volume expansion (20d ADDV / 60d ADDV)",
        "series": factors.f3_series,
        "base": {"threshold": 1.25, "kw": {}},
        "perturb": [
            ("thr_1.15", 1.15, {}),
            ("thr_1.50", 1.50, {}),
            ("win_40d", 1.25, {"num_window": 40, "den_window": 60}),
        ],
    },
    "F4": {
        "name": "volatility expansion (14d ATR / 60d median ATR)",
        "series": factors.f4_series,
        "base": {"threshold": 1.2, "kw": {}},
        "perturb": [
            ("thr_1.10", 1.10, {}),
            ("thr_1.40", 1.40, {}),
        ],
    },
}

COST_FIELDS = {25: "net_r_25bps", 50: "net_r_50bps",
               75: "net_r_75bps", 100: "net_r_100bps"}
N_BOOT = 8000


def load_working_trades():
    with open(os.path.join(CB, "canonical_trades.json")) as fh:
        trades = json.load(fh)
    wt = [t for t in trades if t["symbol"] not in MASKED]
    for t in wt:
        t["_sig_date"] = pd.Timestamp(t["signal_bar_close_at"])
    return wt


def split_stats(trades, sel_mask, cost_field):
    """Expectancy split for one cost field. Returns dict of stats."""
    rs = np.array([t[cost_field] for t in trades], dtype=float)
    sel = np.asarray(sel_mask, dtype=bool)
    out = {"n_total": int(len(rs)),
           "n_sel": int(sel.sum()), "n_unsel": int((~sel).sum())}
    out["sel_rate"] = round(float(sel.mean()), 4)
    for key, m in (("sel", sel), ("unsel", ~sel)):
        r = rs[m]
        out[f"{key}_exp"] = round(float(r.mean()), 4) if len(r) else None
        out[f"{key}_winrate"] = round(float((r > 0).mean()), 4) if len(r) else None
        out[f"{key}_total_r"] = round(float(r.sum()), 2) if len(r) else None
    if out["sel_exp"] is not None and out["unsel_exp"] is not None:
        out["delta"] = round(float(out["sel_exp"] - out["unsel_exp"]), 4)
    else:
        out["delta"] = None
    return out


def period_masks(trades):
    dates = np.array([t["_sig_date"] for t in trades])
    dev = (dates >= pd.Timestamp("2023-10-01", tz="America/New_York")) & \
          (dates < pd.Timestamp("2025-01-01", tz="America/New_York"))
    val = (dates >= pd.Timestamp("2025-01-01", tz="America/New_York")) & \
          (dates < pd.Timestamp("2026-10-01", tz="America/New_York"))
    yrs = {}
    for y in (2024, 2025, 2026):
        yrs[str(y)] = np.array([d.year == y for d in dates])
    return {"dev": dev, "val": val, "years": yrs}


def walkforward_windows(trades):
    tz = "America/New_York"
    wins = []
    start = pd.Timestamp("2023-10-01", tz=tz)
    for k in range(6):
        s = start + pd.DateOffset(months=6 * k)
        e = s + pd.DateOffset(months=6)
        label = f"{s.strftime('%Y-%m')}..{e.strftime('%Y-%m')}"
        dates = np.array([t["_sig_date"] for t in trades])
        wins.append((label, (dates >= s) & (dates < e)))
    return wins


def bootstrap_delta(trades, sel_mask, cost_field, n=N_BOOT):
    rs = np.array([t[cost_field] for t in trades], dtype=float)
    sel = np.asarray(sel_mask, dtype=bool)
    nT = len(rs)
    deltas = np.empty(n)
    for b in range(n):
        idx = RNG.integers(0, nT, nT)
        rb, sb = rs[idx], sel[idx]
        if sb.sum() == 0 or (~sb).sum() == 0:
            deltas[b] = np.nan
            continue
        deltas[b] = rb[sb].mean() - rb[~sb].mean()
    deltas = deltas[~np.isnan(deltas)]
    return {
        "n_draws": int(len(deltas)),
        "mean": round(float(deltas.mean()), 4),
        "p2_5": round(float(np.percentile(deltas, 2.5)), 4),
        "p97_5": round(float(np.percentile(deltas, 97.5)), 4),
        "p_positive": round(float((deltas > 0).mean()), 4),
    }


def loso_delta(trades, sel_mask, cost_field):
    rs = np.array([t[cost_field] for t in trades], dtype=float)
    sel = np.asarray(sel_mask, dtype=bool)
    syms = np.array([t["symbol"] for t in trades])
    base_delta = rs[sel].mean() - rs[~sel].mean()
    rows = []
    for s in sorted(set(syms)):
        m = syms != s
        if sel[m].sum() == 0 or (~sel[m]).sum() == 0:
            continue
        d = rs[m][sel[m]].mean() - rs[m][~sel[m]].mean()
        rows.append({"symbol": s, "delta": round(float(d), 4),
                     "n_dropped": int((~m).sum())})
    ds = np.array([r["delta"] for r in rows])
    return {
        "base_delta": round(float(base_delta), 4),
        "n_symbols": len(rows),
        "min_delta": round(float(ds.min()), 4),
        "max_delta": round(float(ds.max()), 4),
        "frac_positive": round(float((ds > 0).mean()), 4),
        "worst": min(rows, key=lambda r: r["delta"]),
        "best": max(rows, key=lambda r: r["delta"]),
    }


def concentration(trades, sel_mask, cost_field):
    """Delta after dropping the top-1/3/5 symbols by contribution to delta."""
    rs = np.array([t[cost_field] for t in trades], dtype=float)
    sel = np.asarray(sel_mask, dtype=bool)
    syms = np.array([t["symbol"] for t in trades])
    base = rs[sel].mean() - rs[~sel].mean()
    contrib = {}
    for s in sorted(set(syms)):
        m = syms != s
        if sel[m].sum() == 0 or (~sel[m]).sum() == 0:
            continue
        contrib[s] = base - (rs[m][sel[m]].mean() - rs[m][~sel[m]].mean())
    ranked = sorted(contrib, key=lambda s: -contrib[s])
    out = {"base_delta": round(float(base), 4),
           "top_contributors": [{"symbol": s,
                                 "contrib": round(float(contrib[s]), 4),
                                 "n": int((syms == s).sum())}
                                for s in ranked[:5]]}
    for k in (1, 3, 5):
        drop = set(ranked[:k])
        m = np.array([s not in drop for s in syms])
        if sel[m].sum() == 0 or (~sel[m]).sum() == 0:
            out[f"ex_top{k}_delta"] = None
        else:
            out[f"ex_top{k}_delta"] = round(
                float(rs[m][sel[m]].mean() - rs[m][~sel[m]].mean()), 4)
    return out


def tag_trades(trades, series_fn, kw):
    vals = []
    for t in trades:
        v = factors.factor_at(series_fn, t["symbol"], t["signal_bar_close_at"], **kw)
        vals.append(v)
    return np.array(vals, dtype=float)


def analyze_factor(fid, spec, trades):
    cf = COST_FIELDS[50]
    vals = tag_trades(trades, spec["series"], spec["base"]["kw"])
    ok = ~np.isnan(vals)
    res = {
        "factor": fid,
        "description": spec["name"],
        "base_config": {"threshold": spec["base"]["threshold"],
                        "kw": spec["base"]["kw"]},
        "population": {"n_trades_total": len(trades),
                       "n_trades_computable": int(ok.sum()),
                       "n_trades_nan": int((~ok).sum())},
        "factor_distribution": {
            "median": round(float(np.nanmedian(vals)), 4),
            "p10": round(float(np.nanpercentile(vals, 10)), 4),
            "p25": round(float(np.nanpercentile(vals, 25)), 4),
            "p75": round(float(np.nanpercentile(vals, 75)), 4),
            "p90": round(float(np.nanpercentile(vals, 90)), 4),
        },
    }
    res["factor_values"] = [round(float(v), 6) if not np.isnan(v) else None
                            for v in vals]

    def run_all(v, thr, label):
        sel = (v > thr) & ~np.isnan(v)
        pm = period_masks(trades)
        blk = {"label": label, "threshold": thr,
               "selection_rate": round(float(sel.mean()), 4)}
        blk["full_50bps"] = split_stats(trades, sel, cf)
        blk["dev_50bps"] = split_stats([t for t, m in zip(trades, pm["dev"]) if m],
                                       sel[pm["dev"]], cf)
        blk["val_50bps"] = split_stats([t for t, m in zip(trades, pm["val"]) if m],
                                       sel[pm["val"]], cf)
        blk["years_50bps"] = {}
        for y, m in pm["years"].items():
            blk["years_50bps"][y] = split_stats(
                [t for t, mm in zip(trades, m) if mm], sel[m], cf)
        blk["costs_full"] = {}
        for bps, cff in COST_FIELDS.items():
            s = split_stats(trades, sel, cff)
            blk["costs_full"][f"{bps}bps"] = {
                "sel_exp": s["sel_exp"], "unsel_exp": s["unsel_exp"],
                "delta": s["delta"], "n_sel": s["n_sel"]}
        blk["walkforward_6mo_50bps"] = []
        for label_w, m in walkforward_windows(trades):
            s = split_stats([t for t, mm in zip(trades, m) if mm],
                            sel[m], cf)
            blk["walkforward_6mo_50bps"].append(
                {"window": label_w, "n": s["n_total"], "n_sel": s["n_sel"],
                 "sel_exp": s["sel_exp"], "unsel_exp": s["unsel_exp"],
                 "delta": s["delta"]})
        blk["bootstrap_delta_full_50bps"] = bootstrap_delta(trades, sel, cf)
        blk["bootstrap_delta_val_50bps"] = bootstrap_delta(
            [t for t, m in zip(trades, pm["val"]) if m], sel[pm["val"]], cf)
        blk["loso_full_50bps"] = loso_delta(trades, sel, cf)
        blk["concentration_full_50bps"] = concentration(trades, sel, cf)
        return blk

    res["base"] = run_all(vals, spec["base"]["threshold"], "base")
    res["perturbations"] = []
    for plabel, pthr, pkw in spec["perturb"]:
        pv = tag_trades(trades, spec["series"], pkw) if pkw else vals
        res["perturbations"].append(run_all(pv, pthr, plabel))
    return res


def verdict(fid, res):
    """Apply the pre-registered gates. Returns (verdict, rationale)."""
    b = res["base"]
    val = b["val_50bps"]
    notes = []
    # 1. validation: selected beats unselected
    vdelta = val["delta"]
    notes.append(f"val delta={vdelta} (sel {val['sel_exp']} vs unsel {val['unsel_exp']}, "
                 f"n_sel={val['n_sel']}/{val['n_total']})")
    # 2. absolute: selected clears zero
    notes.append(f"selected 50bps expectancy full={b['full_50bps']['sel_exp']}, "
                 f"val={val['sel_exp']}")
    # 3. costs
    cd = {k: v["delta"] for k, v in b["costs_full"].items()}
    notes.append(f"cost deltas={cd}")
    # 4. perturbation
    pd_ = {p["label"]: p["full_50bps"]["delta"] for p in res["perturbations"]}
    notes.append(f"perturb deltas={pd_}")
    # 5. loso / concentration
    notes.append(f"loso min={b['loso_full_50bps']['min_delta']} "
                 f"max={b['loso_full_50bps']['max_delta']} "
                 f"frac_pos={b['loso_full_50bps']['frac_positive']}")
    c = b["concentration_full_50bps"]
    notes.append(f"ex-top1/3/5 deltas={c['ex_top1_delta']}/{c['ex_top3_delta']}/{c['ex_top5_delta']}")
    # 6. bootstrap
    bb = b["bootstrap_delta_full_50bps"]
    bv = b["bootstrap_delta_val_50bps"]
    notes.append(f"bootstrap full: mean={bb['mean']} CI=[{bb['p2_5']},{bb['p97_5']}] "
                 f"P(>0)={bb['p_positive']}; val P(>0)={bv['p_positive']}")
    return notes


def main():
    trades = load_working_trades()
    print(f"working trades: {len(trades)}", flush=True)
    for fid, spec in FACTOR_SPECS.items():
        print(f"=== {fid}: {spec['name']} ===", flush=True)
        res = analyze_factor(fid, spec, trades)
        res["gate_notes"] = verdict(fid, res)
        with open(os.path.join(BASE, f"{fid}.json"), "w") as fh:
            json.dump(res, fh, indent=1)
        print(f"wrote {fid}.json", flush=True)
        b = res["base"]
        print(f"  sel_rate={b['selection_rate']} "
              f"full delta={b['full_50bps']['delta']} "
              f"(sel {b['full_50bps']['sel_exp']} vs unsel {b['full_50bps']['unsel_exp']})",
              flush=True)
        print(f"  dev delta={b['dev_50bps']['delta']} val delta={b['val_50bps']['delta']}",
              flush=True)


if __name__ == "__main__":
    main()
