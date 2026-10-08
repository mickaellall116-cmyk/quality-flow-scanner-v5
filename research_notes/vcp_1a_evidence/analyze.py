#!/usr/bin/env python3
"""Phase 1A analysis: Fama-MacBeth paired differences, block bootstrap,
persistence rule, hit rates, downside, breadth, turnover. Frozen per RUN_PLAN.
"""
import argparse, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(42)
N_BOOT = 9999
BLOCK = 12
HORIZONS = ["r3", "r6", "r12"]
WIN = {"r3": 63, "r6": 126, "r12": 252}
SUBPERIODS = [(f"{y}-01", f"{y+1}-12") for y in range(2010, 2025, 2)]  # 8 x 2Y
MIN_SIDE = 5


def load_panel(path):
    rows = [json.loads(l) for l in open(path)]
    return rows


def block_bootstrap(d, n=N_BOOT, block=BLOCK):
    d = np.asarray(d, float)
    nobs = len(d)
    if nobs < 2:
        return None
    block = min(block, nobs)
    starts = np.arange(nobs - block + 1)
    nb = int(np.ceil(nobs / block))
    means = np.empty(n)
    for i in range(n):
        idx = np.concatenate([np.arange(s, s + block) for s in
                              rng.choice(starts, nb, replace=True)])[:nobs]
        means[i] = d[idx].mean()
    return means


def summarize(d):
    d = np.asarray(d, float)
    if len(d) < 2:
        return {"n_months": len(d), "mean_m": None, "mean_ann": None,
                "ci95": [None, None], "p_two_sided": None}
    obs = d.mean()
    boots = block_bootstrap(d)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    # two-sided p vs H0: mean = 0 — recenter the bootstrap distribution at 0
    # (the raw bootstrap is centered at obs; testing against it is degenerate)
    boots0 = boots - obs
    p = float(np.mean(np.abs(boots0) >= abs(obs)))
    return {"n_months": len(d), "mean_m": round(float(obs), 6),
            "mean_ann": round(float(obs * 12), 6),
            "ci95": [round(float(lo), 6), round(float(hi), 6)],
            "p_two_sided": round(float(min(p, 1.0)), 6)}


def _mean(xs):
    return round(float(np.mean(xs)), 6) if len(xs) else None


def load_spy_ref(months_path, eod_path):
    """SPY total returns over identical forward windows. Returns {m: {r3,r6,r12}} or {}."""
    import bisect
    try:
        bars = json.load(open(eod_path))
        months = json.load(open(months_path))
    except FileNotFoundError:
        return {}
    dates = sorted(b["date"][:10] for b in bars)
    px = {b["date"][:10]: b["adjClose"] for b in bars}
    closes = [px[d] for d in dates]
    ref = {}
    for m in months:
        pos = bisect.bisect_right(dates, m) - 1
        if pos < 0:
            continue
        obs = closes[pos]
        r = {}
        for key, w in WIN.items():
            end_i = min(pos + w, len(dates) - 1)
            r[key] = round(closes[end_i] / obs - 1.0, 6)
        ref[m] = r
    return ref


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--panel", default=os.path.join(HERE, "panels", "panel.jsonl"))
    a.add_argument("--out", default=os.path.join(HERE, "results_phase1a.json"))
    a.add_argument("--spy", default=None,
                 help="path to raw/eod/SPY.json for secondary reference")
    args = a.parse_args()
    rows = load_panel(args.panel)
    spy_ref = load_spy_ref(os.path.join(HERE, "month_ends.json"), args.spy) if args.spy else {}
    # mcap filter (frozen): $2B <= mcap <= $100B, PIT estimate; null -> exclude
    filt = [r for r in rows if r.get("mcap") is not None
            and 2e9 <= r["mcap"] <= 100e9]
    print(f"panel rows={len(rows)} after mcap filter={len(filt)}")
    months = sorted(set(r["m"] for r in filt))
    if not months:
        print("no rows after mcap filter; nothing to analyze")
        return 0
    out = {"n_panel_rows": len(rows), "n_filtered_rows": len(filt),
           "months": [months[0], months[-1]], "variants": {}}
    for v in ["v1", "v2"]:
        vres = {"horizons": {}, "breadth": {}, "turnover": None,
                "hit_rate": {}, "downside": {}}
        qsets = {}
        for h in HORIZONS:
            used = [mm for mm in months if not (h == "r12" and mm > "2025-09")]
            d_all, qrets, crets, qmeans = [], [], [], []
            for m in used:
                rm = [r for r in filt if r["m"] == m]
                q = [r[h] for r in rm if r[v]]
                c = [r[h] for r in rm if not r[v]]
                if len(q) < MIN_SIDE or len(c) < MIN_SIDE:
                    d_all.append(np.nan)
                    qmeans.append(np.nan)
                else:
                    d_all.append(float(np.mean(q) - np.mean(c)))
                    qmeans.append(float(np.mean(q)))
                    qrets.extend(q)
                    crets.extend(c)
            d = [x for x in d_all if not np.isnan(x)]
            s = summarize(d)
            s["n_months_used"] = len(d)
            s["n_qual_obs"] = len(qrets)
            s["n_ctrl_obs"] = len(crets)
            s["mean_qual_ret"] = _mean(qrets)
            s["mean_ctrl_ret"] = _mean(crets)
            vres["horizons"][h] = s
            sub = []
            for (y0, y1) in SUBPERIODS:
                vals = [x for mth, x in zip(used, d_all)
                        if y0 <= mth <= y1 and not np.isnan(x)]
                sub.append({"period": f"{y0[:4]}-{y1[:4]}",
                            "n_months": len(vals),
                            "mean_excess_m": round(float(np.mean(vals)), 6)
                            if vals else None})
            vres["horizons"][h]["subperiods"] = sub
            vres["horizons"][h]["n_positive_subperiods"] = sum(
                1 for s_ in sub if s_["mean_excess_m"] is not None and s_["mean_excess_m"] > 0)
            # hit rate / downside on qualifier observations
            vres["hit_rate"][h] = {
                "qual": round(float(np.mean(np.array(qrets) > 0)), 4) if qrets else None,
                "ctrl": round(float(np.mean(np.array(crets) > 0)), 4) if crets else None}
            dds = [r["dd_" + h] for r in filt if r[v] and
                   not (h == "r12" and r["m"] > "2025-09")]
            vres["downside"][h] = {"n": len(dds),
                                   "mean_max_adv_exc": _mean(dds),
                                   "median_max_adv_exc": round(float(np.median(dds)), 4)
                                   if dds else None}
            if spy_ref:
                exc = [qm - spy_ref[m][h] for m, qm in zip(used, qmeans)
                       if m in spy_ref and not np.isnan(qm)]
                if exc:
                    vres["horizons"][h]["vs_spy"] = {
                        "n_months": len(exc),
                        "mean_excess_m": round(float(np.mean(exc)), 6),
                        "mean_excess_ann": round(float(np.mean(exc) * 12), 6)}
        # breadth + turnover
        counts = []
        for m in months:
            q = [r["t"] for r in filt if r["m"] == m and r[v]]
            qsets[m] = set(q)
            counts.append(len(q))
        vres["breadth"] = {"mean": round(float(np.mean(counts)), 1),
                           "min": int(np.min(counts)), "max": int(np.max(counts))}
        to = []
        for i in range(len(months) - 1):
            a_, b_ = qsets[months[i]], qsets[months[i + 1]]
            if a_:
                to.append(1 - len(a_ & b_) / len(a_))
        vres["turnover"] = round(float(np.mean(to)), 4) if to else None
        out["variants"][v] = vres
    # persistence rule (frozen §7): per horizon h, pass_h =
    #   full-sample mean(d_h) > 0  AND  >=5/8 subperiods with mean>0
    #   AND  bootstrap p_h < 0.05.
    # Overall verdict: all three horizons pass (no cherry-picking).
    persist = {}
    for v in ["v1", "v2"]:
        h_pass = {}
        for h in HORIZONS:
            s = out["variants"][v]["horizons"][h]
            h_pass[h] = bool(
                s["mean_m"] is not None and s["mean_m"] > 0
                and s["n_positive_subperiods"] is not None
                and s["n_positive_subperiods"] >= 5
                and s["p_two_sided"] is not None
                and s["p_two_sided"] < 0.05)
        persist[v] = {"per_horizon": h_pass,
                      "pass_all_three": all(h_pass.values())}
    out["persistence_rule"] = persist
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
    print(f"-> {args.out}")
    print("persistence:", json.dumps(persist))
    # console tables
    def _f(x):
        return f"{x:+.4f}" if x is not None else "n/a"
    for v in ["v1", "v2"]:
        print(f"\n=== {v.upper()} ===")
        for h in HORIZONS:
            s = out["variants"][v]["horizons"][h]
            print(f" {h}: excess_m={_f(s['mean_m'])} ann={_f(s['mean_ann'])} "
                  f"CI95=[{_f(s['ci95'][0])},{_f(s['ci95'][1])}] p={s['p_two_sided']} "
                  f"nmo={s['n_months']} subpos={s['n_positive_subperiods']}/8 "
                  f"qret={_f(s['mean_qual_ret'])} cret={_f(s['mean_ctrl_ret'])}")
        print(f" breadth={out['variants'][v]['breadth']} turnover={out['variants'][v]['turnover']}")
        print(f" hit_rate={out['variants'][v]['hit_rate']}")
        print(f" downside={out['variants'][v]['downside']}")


if __name__ == "__main__":
    sys.exit(main())
