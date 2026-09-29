"""Worker C: full selection-edge protocol for FAM2/FAM3/FAM5/FAM6.

Protocol (pre-registered in REPORT.md Sections 2-4):
  per-bucket n/exp/PF/win-rate/maxDD @50bps; monotonicity TOP>MID>BOTTOM;
  TOP-BOTTOM delta; cost ladder 25/50/75/100; dev/val; year splits;
  rolling 12mo-observe/6mo-test walk-forward on the delta; perturbations;
  concentration (drop top 1/3/5); bootstrap 5000 trade + symbol-block;
  leave-one-symbol-out; absolute TOP-clears-zero check; gates -> verdict.

Writes FAM2.json, FAM3.json, FAM5.json, FAM6.json.
"""
import json
import os

import numpy as np
import pandas as pd

OUT = os.path.expanduser("~/workspace/quality-flow-scanner-v5/selection_edge/phase2_other")
COSTS = ["25bps", "50bps", "75bps", "100bps"]
RKEY = {c: f"net_r_{c}" for c in COSTS}
HEAD = "50bps"
N_BOOT = 5000
rng = np.random.default_rng(20260925)

FACTORS = {
    "FAM2": {"name": "FAM2_trend_persistence",
             "keys": ("fam2_63", "fam2_42", "fam2_84"),
             "rule": "pct of last 63 trading days with close above 50d EMA (EMA span 50, causal)"},
    "FAM3": {"name": "FAM3_atr_normalized_momentum",
             "keys": ("fam3_126", "fam3_84", "fam3_168"),
             "rule": "126d total return / (14d Wilder ATR / close)"},
    "FAM5": {"name": "FAM5_vol_regime_percentile",
             "keys": ("fam5_63", "fam5_42", "fam5_84"),
             "rule": "63d realized-vol percentile rank vs own trailing 252 values"},
    "FAM6": {"name": "FAM6_dollar_volume_trend",
             "keys": ("fam6_63", "fam6_42", "fam6_84"),
             "rule": "OLS slope of log(dollar volume) over trailing 63 trading days"},
}


def load():
    with open(os.path.join(OUT, "trade_factors.json")) as fh:
        return json.load(fh)


def date_of(t):
    return pd.Timestamp(t["signal_bar_close_at"])


def in_range(t, a, b):
    d = date_of(t)
    return pd.Timestamp(a, tz="America/New_York") <= d < pd.Timestamp(b, tz="America/New_York")


def bucket_stats(trades, bkey, cost=HEAD):
    sub = [t for t in trades if t[bkey] in ("TOP", "MIDDLE", "BOTTOM")]
    out = {}
    for b in ("TOP", "MIDDLE", "BOTTOM"):
        tb = [t for t in sub if t[bkey] == b]
        rs = np.array([t[RKEY[cost]] for t in tb], dtype=float)
        stat = {"n": len(tb)}
        if len(tb):
            stat.update({
                "exp": round(float(rs.mean()), 4),
                "pf": round(float(rs[rs > 0].sum() / -rs[rs <= 0].sum()), 3)
                      if (rs <= 0).any() and (rs > 0).any()
                      else (float("inf") if (rs > 0).any() else 0.0),
                "win_rate": round(float((rs > 0).mean()), 3),
                "max_dd_r": round(float(max_dd(cum_chron(tb, cost))), 3),
                "total_r": round(float(rs.sum()), 2),
            })
        out[b] = stat
    exps = [out[b].get("exp") for b in ("TOP", "MIDDLE", "BOTTOM")]
    out["monotonic"] = (exps[0] is not None and exps[1] is not None and exps[2] is not None
                        and exps[0] > exps[1] > exps[2])
    out["top_minus_bottom"] = (round(float(exps[0] - exps[2]), 4)
                               if exps[0] is not None and exps[2] is not None else None)
    return out


def cum_chron(tb, cost):
    tb = sorted(tb, key=lambda t: (t["signal_bar_close_at"], t["symbol"]))
    return np.cumsum([t[RKEY[cost]] for t in tb])


def max_dd(cum):
    if len(cum) == 0:
        return 0.0
    peak = np.maximum.accumulate(cum)
    return float((cum - peak).min())


def bootstrap_delta(trades, bkey, cost=HEAD, n_iter=N_BOOT, block="trade"):
    sub = [t for t in trades if t[bkey] in ("TOP", "BOTTOM")]
    rs = np.array([t[RKEY[cost]] for t in sub], dtype=float)
    is_top = np.array([t[bkey] == "TOP" for t in sub])
    if is_top.sum() == 0 or is_top.sum() == len(sub):
        return None
    deltas = np.empty(n_iter)
    if block == "trade":
        idx = np.arange(len(sub))
        for b in range(n_iter):
            s = rng.integers(0, len(sub), len(sub))
            mt, mb = is_top[s], ~is_top[s]
            deltas[b] = rs[s][mt].mean() - rs[s][mb].mean() if mt.sum() and mb.sum() else np.nan
    else:
        syms = np.array([t["symbol"] for t in sub])
        usym = np.unique(syms)
        for b in range(n_iter):
            pick = rng.choice(usym, len(usym), replace=True)
            s = np.concatenate([np.flatnonzero(syms == p) for p in pick])
            mt, mb = is_top[s], ~is_top[s]
            deltas[b] = rs[s][mt].mean() - rs[s][mb].mean() if mt.sum() and mb.sum() else np.nan
    d = deltas[~np.isnan(deltas)]
    return {"n_iter": n_iter, "block": block, "n_valid": int(len(d)),
            "mean": round(float(d.mean()), 4),
            "ci95_lo": round(float(np.percentile(d, 2.5)), 4),
            "ci95_hi": round(float(np.percentile(d, 97.5)), 4),
            "p_positive": round(float((d > 0).mean()), 4)}


def bootstrap_top_abs(trades, bkey, cost=HEAD, n_iter=N_BOOT):
    rs = np.array([t[RKEY[cost]] for t in trades if t[bkey] == "TOP"], dtype=float)
    if len(rs) == 0:
        return None
    bs = np.array([rs[rng.integers(0, len(rs), len(rs))].mean() for _ in range(n_iter)])
    return {"n": int(len(rs)), "exp": round(float(rs.mean()), 4),
            "ci95": [round(float(np.percentile(bs, 2.5)), 4),
                     round(float(np.percentile(bs, 97.5)), 4)],
            "clears_zero": bool(np.percentile(bs, 2.5) > 0)}


def loso(trades, bkey, cost=HEAD):
    syms = sorted(set(t["symbol"] for t in trades if t[bkey] in ("TOP", "MIDDLE", "BOTTOM")))
    ds, te = [], []
    for s in syms:
        sub = [t for t in trades if t["symbol"] != s and t[bkey] in ("TOP", "MIDDLE", "BOTTOM")]
        st = bucket_stats(sub, bkey, cost)
        if st["top_minus_bottom"] is not None:
            ds.append(st["top_minus_bottom"])
        if st["TOP"].get("exp") is not None:
            te.append(st["TOP"]["exp"])
    ds, te = np.array(ds), np.array(te)
    def summ(x):
        return {"n": int(len(x)), "min": round(float(x.min()), 4),
                "q25": round(float(np.percentile(x, 25)), 4),
                "median": round(float(np.median(x)), 4),
                "mean": round(float(x.mean()), 4),
                "max": round(float(x.max()), 4),
                "n_negative": int((x < 0).sum())}
    return {"delta": summ(ds), "top_exp": summ(te)}


def concentration(trades, bkey, cost=HEAD):
    sub = [t for t in trades if t[bkey] == "TOP"]
    contrib = {}
    for t in sub:
        contrib[t["symbol"]] = contrib.get(t["symbol"], 0.0) + t[RKEY[cost]]
    ranked = sorted(contrib.items(), key=lambda kv: -kv[1])
    out = {"top_symbols_by_topbucket_r": [(s, round(v, 2)) for s, v in ranked[:8]]}
    for k in (1, 3, 5):
        drop = set(s for s, _ in ranked[:k])
        rest = [t for t in trades if t["symbol"] not in drop
                and t[bkey] in ("TOP", "MIDDLE", "BOTTOM")]
        st = bucket_stats(rest, bkey, cost)
        out[f"drop_top{k}"] = {"n": len(rest), "delta": st["top_minus_bottom"],
                               "top_exp": st["TOP"].get("exp"),
                               "monotonic": st["monotonic"]}
    return out


def run_factor(fid, cfg, trades):
    base, lo, hi = cfg["keys"]
    bkey = f"{base}_bucket"
    rep = {"factor": cfg["name"], "rule": cfg["rule"], "base_key": base,
           "pre_registered": "REPORT.md Sections 1-4, locked before computation"}
    ftr = [t for t in trades if t[bkey] in ("TOP", "MIDDLE", "BOTTOM")]
    rep["n_trades_total"] = len(trades)
    rep["n_trades_with_factor"] = len(ftr)
    rep["n_excluded_null_factor"] = len(trades) - len(ftr)

    rep["headline"] = bucket_stats(ftr, bkey, HEAD)
    rep["cost_ladder"] = {c: bucket_stats(ftr, bkey, c) for c in COSTS}

    dev = [t for t in ftr if in_range(t, "2023-10-01", "2025-01-01")]
    val = [t for t in ftr if in_range(t, "2025-01-01", "2026-10-01")]
    rep["dev"] = bucket_stats(dev, bkey, HEAD)
    rep["val"] = bucket_stats(val, bkey, HEAD)
    rep["years"] = {}
    for y, a, b in (("2024", "2024-01-01", "2025-01-01"),
                    ("2025", "2025-01-01", "2026-01-01"),
                    ("2026", "2026-01-01", "2026-10-01")):
        rep["years"][y] = bucket_stats([t for t in ftr if in_range(t, a, b)], bkey, HEAD)

    wf = []
    for oa, ob, ta, tb in (("2023-10-01", "2024-10-01", "2024-10-01", "2025-04-01"),
                           ("2024-04-01", "2025-04-01", "2025-04-01", "2025-10-01"),
                           ("2024-10-01", "2025-10-01", "2025-10-01", "2026-04-01"),
                           ("2025-04-01", "2026-04-01", "2026-04-01", "2026-10-01")):
        o = [t for t in ftr if in_range(t, oa, ob)]
        w = [t for t in ftr if in_range(t, ta, tb)]
        wf.append({"observe": f"{oa}..{ob}", "test": f"{ta}..{tb}",
                   "observe_delta": bucket_stats(o, bkey, HEAD)["top_minus_bottom"],
                   "observe_n": len(o),
                   "test_delta": bucket_stats(w, bkey, HEAD)["top_minus_bottom"],
                   "test_n": len(w)})
    rep["walk_forward_12mo_observe_6mo_test"] = wf

    rep["perturbations"] = {}
    for vk in (lo, hi):
        vb = f"{vk}_bucket"
        vf = [t for t in trades if t[vb] in ("TOP", "MIDDLE", "BOTTOM")]
        vv = [t for t in vf if in_range(t, "2025-01-01", "2026-10-01")]
        rep["perturbations"][vk] = {
            "headline": bucket_stats(vf, vb, HEAD),
            "val": bucket_stats(vv, vb, HEAD)}

    rep["concentration"] = concentration(ftr, bkey, HEAD)
    rep["bootstrap_delta_trade"] = bootstrap_delta(ftr, bkey, HEAD, block="trade")
    rep["bootstrap_delta_symbol_block"] = bootstrap_delta(ftr, bkey, HEAD, block="symbol")
    rep["top_absolute"] = bootstrap_top_abs(ftr, bkey, HEAD)
    rep["loso"] = loso(ftr, bkey, HEAD)
    rep["verdict"] = judge(rep)
    return rep


def judge(rep):
    """Pre-registered gates (REPORT.md Section 4)."""
    h, v, d = rep["headline"], rep["val"], rep["dev"]
    td, te = h["top_minus_bottom"], h["TOP"].get("exp")
    mono = h["monotonic"]
    notes = []
    fails = []
    # monotonic + top positive @50bps
    if not mono:
        fails.append("headline not monotonic TOP>MID>BOTTOM")
    if te is None or te <= 0:
        fails.append("TOP bucket not positive @50bps")
    # validation: val direction consistent, val delta >= 0
    vd = v["top_minus_bottom"]
    if vd is None or vd < 0:
        fails.append(f"validation delta {vd} < 0")
    elif td is not None and vd < td / 2:
        notes.append(f"val delta {vd} materially below headline {td}")
    dd = d["top_minus_bottom"]
    if dd is not None and vd is not None and dd < 0 and vd < 0:
        fails.append("negative in both dev and val")
    # costs: positive delta at 75bps
    d75 = rep["cost_ladder"]["75bps"]["top_minus_bottom"]
    if d75 is None or d75 <= 0:
        fails.append(f"delta not positive @75bps ({d75})")
    # perturbations keep direction (delta >= 0 headline+val)
    for vk, p in rep["perturbations"].items():
        hd, vd2 = p["headline"]["top_minus_bottom"], p["val"]["top_minus_bottom"]
        if hd is None or hd < 0 or vd2 is None or vd2 < 0:
            fails.append(f"perturbation {vk} flips direction (headline {hd}, val {vd2})")
    # LOSO: min delta >= 0
    lm = rep["loso"]["delta"]["min"]
    if lm < 0:
        fails.append(f"LOSO delta min {lm} < 0")
    # bootstrap CI on delta excludes 0
    bc = rep["bootstrap_delta_trade"]
    if bc is not None and bc["ci95_lo"] <= 0:
        fails.append(f"bootstrap delta CI includes 0 [{bc['ci95_lo']}, {bc['ci95_hi']}]")
    # absolute check recorded but not gating (only TOP clears-zero noted)
    if not fails:
        verdict = "PASS"
    elif (mono and te is not None and te > 0 and vd is not None and vd >= 0
          and len([f for f in fails if "bootstrap" not in f and "LOSO" not in f]) <= 1):
        verdict = "MAYBE"
    else:
        verdict = "FAIL"
    return {"verdict": verdict, "hard_fails": fails, "notes": notes}


def main():
    trades = load()
    print(f"trades: {len(trades)}", flush=True)
    for fid, cfg in FACTORS.items():
        print(f"running {fid}...", flush=True)
        rep = run_factor(fid, cfg, trades)
        path = os.path.join(OUT, f"{fid}.json")
        with open(path, "w") as fh:
            json.dump(rep, fh, indent=1)
        h = rep["headline"]
        print(f"  {fid}: mono={h['monotonic']} top={h['TOP'].get('exp')} "
              f"mid={h['MIDDLE'].get('exp')} bot={h['BOTTOM'].get('exp')} "
              f"delta={h['top_minus_bottom']} val_delta={rep['val']['top_minus_bottom']} "
              f"-> {rep['verdict']['verdict']}", flush=True)
        print(f"wrote {path}", flush=True)


if __name__ == "__main__":
    main()
