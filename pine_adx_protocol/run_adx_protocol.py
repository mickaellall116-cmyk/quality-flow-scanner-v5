#!/usr/bin/env python3
"""ADX ranking under the canonical 12-step protocol (STUDY C of 3).

HYPOTHESIS.md frozen BEFORE running. Research only — nothing frozen touched.
`pine_backtest` and pine_ranking_confirm helpers imported unmodified.
Primary: per-contest advantage on crowded bars (ranking binds, free>0).
"""
import importlib.util
import json
import os
import sys
import traceback
from collections import defaultdict

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_adx_protocol")
sys.path.insert(0, BASE)
os.makedirs(OUTDIR, exist_ok=True)

import pine_backtest as pb

spec = importlib.util.spec_from_file_location(
    "rc", os.path.join(BASE, "pine_ranking_confirm", "run_ranking_confirm.py"))
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

SECTOR = {
    "QQQ": "XLK", "SMCI": "SOXX", "PLTR": "XLK", "ANET": "XLK", "SOFI": "XLF",
    "RKLB": "XLI", "ONDS": "XLK", "DRAM": "SOXX", "SPCX": "XLI", "ASTX": "XLK",
    "BBAI": "XLK", "NIO": "XLY", "HOOD": "XLF", "AMD": "SOXX",
}

WATCHLIST = list(SECTOR.keys())
COSTS = [0.0025, 0.005, 0.0075, 0.01]
COST = 0.0025
N_BOOT = 5000
RNG = np.random.default_rng(42)


def net_r(tr, cost):
    return pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]


def load_all():
    data, closes = {}, {}
    for sym in WATCHLIST:
        df = pd.read_pickle(
            os.path.join(BASE, "pine_entry_timing_backtest", "cache", f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        df["adx10"] = pb.adx(df, 10)
        df["adx20"] = pb.adx(df, 20)
        data[sym] = df
        closes[sym] = df["Close"]
    all_trades = []
    for sym in WATCHLIST:
        tr, _ = pb.gen_pine_trades(sym, data[sym])
        all_trades.extend(tr)
    all_trades.sort(key=lambda t: t["entry_time"])
    return all_trades, closes


def build_regime():
    """Reuse P4 daily caches; point-in-time regime labels at signal date."""
    cd = os.path.join(BASE, "pine_regime_backtest", "cache")
    def rd(t, p):
        df = pd.read_pickle(os.path.join(cd, p))
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        return df
    spy = rd("SPY", "d_SPY.pkl"); qqq = rd("QQQ", "d_QQQ.pkl"); vix = rd("^VIX", "d_VIX.pkl")
    reg = pd.DataFrame(index=spy.index)
    reg["e200"] = spy["Close"].ewm(span=200, adjust=False).mean()
    reg["e20"] = reg["e200"].shift(20)
    reg["above"] = spy["Close"] > reg["e200"]
    reg["rising"] = reg["e200"] > reg["e20"]
    v = vix["Close"].reindex(reg.index).ffill()
    reg["vix_regime"] = pd.cut(v, [-np.inf, 20, 30, np.inf],
                               labels=["low<20", "mid20-30", "high>30"])
    logret = np.log(spy["Close"] / spy["Close"].shift(1))
    reg["rv20_high"] = (logret.rolling(20).std()
                        > logret.rolling(20).std().rolling(252).median())
    reg["tri"] = np.where(reg["above"] & reg["rising"], "bull",
                  np.where(~reg["above"] & ~reg["rising"], "bear", "sideways"))
    return reg.dropna()


def regime_at(reg, ts):
    d = pd.Timestamp(ts).tz_localize(None).normalize()
    ii = reg.index.searchsorted(d, side="right") - 1
    if ii < 0:
        return None
    r = reg.iloc[ii]
    return {"tri": str(r["tri"]), "vix": str(r["vix_regime"]),
            "rv20_high": bool(r["rv20_high"])}


def main():
    all_trades, closes = load_all()
    print(f"trades: {len(all_trades)}", flush=True)
    # features need full dataframes + bench (same as rc.main)
    data = {}
    for sym in WATCHLIST:
        df = pd.read_pickle(
            os.path.join(BASE, "pine_entry_timing_backtest", "cache", f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        df["adx10"] = pb.adx(df, 10)
        df["adx20"] = pb.adx(df, 20)
        data[sym] = df
    sys.path.insert(0, os.path.join(BASE, "pine_signal_quality"))
    from pine_signal_quality import load_benchmarks
    bench, _ = load_benchmarks()
    sig_index = {sym: {df.index[i].isoformat(): i for i in range(len(df))}
                 for sym, df in data.items()}
    feats = rc.compute_features(all_trades, data, bench, sig_index)
    print("features done", flush=True)

    entries_by_t = defaultdict(list)
    for idx, t in enumerate(all_trades):
        entries_by_t[t["entry_time"]].append(idx)

    # contested timestamps from the do-nothing (takeall) reference
    diag = {"contested": []}
    rc.simulate_ranked(all_trades, closes, COST, feats, None, None, diag=diag)
    genuine = [(pd.Timestamp(ts), m, f) for ts, m, f in diag["contested"] if f > 0]
    print(f"contested ts: {len(diag['contested'])}, genuine: {len(genuine)}", flush=True)

    # ---- per-contest analysis (primary unit) ----
    contests = []
    for t, m, f in genuine:
        cands = entries_by_t[t]
        k = min(2, f)
        ta_picks = cands[:k]  # arrival order = all_trades order
        ax_picks = sorted(cands, key=lambda i: (-feats[i]["adx"], i))[:k]
        rs_picks = sorted(cands, key=lambda i: (-feats[i]["rs_spy"], i))[:k]
        rec = {"t": str(t), "n_cands": m, "free": f,
               "ta": ta_picks, "adx": ax_picks, "rs": rs_picks,
               "syms": sorted({all_trades[i]["symbol"] for i in cands})}
        contests.append(rec)
    print(f"genuine contests with picks: {len(contests)}", flush=True)

    def adv(rec, fid, cost, ref="ta"):
        a = [net_r(all_trades[i], cost) for i in rec[fid]]
        b = [net_r(all_trades[i], cost) for i in rec[ref]]
        return float(np.mean(a) - np.mean(b)) if a and b else 0.0

    res = {"n_trades": len(all_trades), "n_genuine_contests": len(contests)}
    for cost in COSTS:
        A = np.array([adv(r, "adx", cost) for r in contests])
        R = np.array([adv(r, "rs", cost, ref="ta") for r in contests])
        AR = np.array([adv(r, "adx", cost, ref="rs") for r in contests])
        res.setdefault("per_contest", {})[str(cost)] = {
            "adx_vs_takeall": {"n": len(A), "mean_adv_r": round(float(A.mean()), 4),
                               "pos_frac": round(float((A > 0).mean()), 3),
                               "sum_adv_r": round(float(A.sum()), 3)},
            "rs_vs_takeall": {"n": len(R), "mean_adv_r": round(float(R.mean()), 4),
                              "pos_frac": round(float((R > 0).mean()), 3)},
            "adx_vs_rs": {"n": len(AR), "mean_adv_r": round(float(AR.mean()), 4),
                          "pos_frac": round(float((AR > 0).mean()), 3)},
        }

    def nts(rec):
        return pd.Timestamp(rec["t"]).tz_localize(None)

    # ---- dev / validation split on contests ----
    def split(rec):
        return "dev" if nts(rec) <= pd.Timestamp("2024-12-31") else "val"
    dv = {}
    for cost in COSTS:
        for lbl in ("dev", "val"):
            A = np.array([adv(r, "adx", cost) for r in contests if split(r) == lbl])
            dv.setdefault(str(cost), {})[lbl] = {
                "n": len(A), "mean_adv_r": round(float(A.mean()), 4) if len(A) else None}
    res["dev_validation"] = dv

    # ---- rolling walk-forward on contests ----
    wf_defs = [
        ("2023-10", "2024-09", "2024-10", "2025-03"),
        ("2024-04", "2025-03", "2025-04", "2025-09"),
        ("2024-10", "2025-09", "2025-10", "2026-03"),
        ("2025-04", "2026-03", "2026-04", "2026-09"),
    ]
    wf = []
    for i, (t0, t1, s0, s1) in enumerate(wf_defs):
        lo = pd.Timestamp(s0 + "-01")
        hi = pd.Timestamp(s1 + "-01") + pd.offsets.MonthEnd(1)
        test = [r for r in contests if lo <= nts(r) < hi]
        A = np.array([adv(r, "adx", COST) for r in test])
        wf.append({"window": i + 1, "test": f"{s0}->{s1}", "n": len(A),
                   "mean_adv_r": round(float(A.mean()), 4) if len(A) else None})
    all_test = []
    for w in wf:
        if w["window"] == "combined_test":
            continue
        s0, s1 = w["test"].split("->")
        lo = pd.Timestamp(s0 + "-01")
        hi = pd.Timestamp(s1 + "-01") + pd.offsets.MonthEnd(1)
        all_test.extend([r for r in contests if lo <= nts(r) < hi])
    Aall = np.array([adv(r, "adx", COST) for r in all_test])
    wf.append({"window": "combined_test", "n": len(Aall),
               "mean_adv_r": round(float(Aall.mean()), 4) if len(Aall) else None})
    res["walk_forward"] = wf

    # ---- year + regime splits on contests ----
    yr = defaultdict(list)
    for r in contests:
        yr[str(pd.Timestamp(r["t"]).year)].append(adv(r, "adx", COST))
    res["by_year"] = {y: {"n": len(v), "mean_adv_r": round(float(np.mean(v)), 4)}
                      for y, v in sorted(yr.items())}
    reg = build_regime()
    rg = defaultdict(list)
    for r in contests:
        lab = regime_at(reg, r["t"])
        if lab:
            rg[lab["tri"]].append(adv(r, "adx", COST))
            rg["vix_" + lab["vix"]].append(adv(r, "adx", COST))
            rg["rv20_" + ("high" if lab["rv20_high"] else "low")].append(adv(r, "adx", COST))
    res["by_regime"] = {k: {"n": len(v), "mean_adv_r": round(float(np.mean(v)), 4)}
                        for k, v in sorted(rg.items())}

    # ---- perturbation: adx10/adx20 per-contest ----
    pert = {}
    for fid, lbl in (("adx", "adx14"), ("adx10", "adx10"), ("adx20", "adx20")):
        def advp(rec, _fid=fid, cost=COST):
            cands = entries_by_t[pd.Timestamp(rec["t"])]
            k = min(2, rec["free"])
            p = sorted(cands, key=lambda i: (-feats[i][_fid], i))[:k]
            a = [net_r(all_trades[i], cost) for i in p]
            b = [net_r(all_trades[i], cost) for i in rec["ta"]]
            return float(np.mean(a) - np.mean(b)) if a and b else 0.0
        A = np.array([advp(r) for r in contests])
        pert[lbl] = {"n": len(A), "mean_adv_r": round(float(A.mean()), 4),
                     "pos_frac": round(float((A > 0).mean()), 3)}
    res["perturbation"] = pert

    # ---- concentration of the differential ----
    def score_fn(fid):
        def fn(i, cands):
            return feats[i][fid]
        return fn
    varmap = {"takeall": None, "rs_spy_CONTROL": score_fn("rs_spy"),
              "adx": score_fn("adx"), "adx10": score_fn("adx10"),
              "adx20": score_fn("adx20")}
    taken_idx = {}
    sims = {}
    for vid, sfn in varmap.items():
        ti = []
        port = rc.simulate_ranked(all_trades, closes, COST, feats, sfn, 2, taken_out=ti)
        taken_idx[vid] = set(ti)
        sims[vid] = (ti, port)

    ref = taken_idx["takeall"]
    diffs = []
    for i in taken_idx["adx"] - ref:      # swapped in by ADX
        diffs.append({"idx": i, "contrib": net_r(all_trades[i], COST),
                      "side": "in", "symbol": all_trades[i]["symbol"],
                      "year": str(pd.Timestamp(all_trades[i]["signal_time"]).year)})
    for i in ref - taken_idx["adx"]:      # ranked out by ADX
        diffs.append({"idx": i, "contrib": -net_r(all_trades[i], COST),
                      "side": "out", "symbol": all_trades[i]["symbol"],
                      "year": str(pd.Timestamp(all_trades[i]["signal_time"]).year)})
    tot = float(sum(d["contrib"] for d in diffs))
    srt = sorted(diffs, key=lambda d: -d["contrib"])
    cum = np.cumsum([d["contrib"] for d in srt])
    conc = {"total_diff_r": round(tot, 3), "n_diff_trades": len(diffs)}
    for k in (1, 3, 5):
        conc[f"top{k}_share"] = round(float(cum[k - 1] / tot), 3) if tot and len(cum) >= k else None
    conc["top5"] = [{"symbol": d["symbol"], "side": d["side"],
                     "contrib": round(d["contrib"], 3), "year": d["year"]} for d in srt[:5]]
    bysym = defaultdict(float)
    for d in diffs:
        bysym[d["symbol"]] += d["contrib"]
    conc["by_symbol"] = {s: round(v, 3) for s, v in sorted(bysym.items(), key=lambda kv: -kv[1])}
    bysec = defaultdict(float)
    for d in diffs:
        bysec[SECTOR[d["symbol"]]] += d["contrib"]
    conc["by_sector"] = {s: round(v, 3) for s, v in sorted(bysec.items(), key=lambda kv: -kv[1])}
    byyr = defaultdict(float)
    for d in diffs:
        byyr[d["year"]] += d["contrib"]
    conc["by_year"] = {y: round(v, 3) for y, v in sorted(byyr.items())}
    y2025 = byyr.get("2025", 0.0)
    conc["y2025_share"] = round(float(y2025 / tot), 3) if tot else None
    res["concentration"] = conc

    # ---- bootstrap on per-contest advantage ----
    A = np.array([adv(r, "adx", COST) for r in contests])
    draws = RNG.choice(A, size=(N_BOOT, len(A)), replace=True).mean(axis=1)
    res["bootstrap"] = {
        "n_resamples": N_BOOT,
        "p5": round(float(np.percentile(draws, 5)), 4),
        "p25": round(float(np.percentile(draws, 25)), 4),
        "p50": round(float(np.percentile(draws, 50)), 4),
        "p75": round(float(np.percentile(draws, 75)), 4),
        "p95": round(float(np.percentile(draws, 95)), 4),
        "frac_above_0": round(float((draws > 0).mean()), 4),
        "observed_mean": round(float(A.mean()), 4),
    }

    # ---- leave-one-symbol-out ----
    loso = {}
    for sym in WATCHLIST:
        keep = [r for r in contests if sym not in r["syms"]]
        Ak = np.array([adv(r, "adx", COST) for r in keep])
        sub = [t for t in all_trades if t["symbol"] != sym]
        sub_idx = {id(t): k for k, t in enumerate(sub)}
        fmap = {sub_idx[id(all_trades[i])]: feats[i] for i in range(len(all_trades))
                if id(all_trades[i]) in sub_idx}
        def sfn_sub(j, cands, _fmap=fmap):
            return _fmap[j]["adx"]
        ti_ta, ti_ax = [], []
        rc.simulate_ranked(sub, closes, COST, fmap, None, 2, taken_out=ti_ta)
        rc.simulate_ranked(sub, closes, COST, fmap, sfn_sub, 2, taken_out=ti_ax)
        ta_t = [sub[i] for i in ti_ta]; ax_t = [sub[i] for i in ti_ax]
        e_ta = float(np.mean([net_r(t, COST) for t in ta_t])) if ta_t else 0.0
        e_ax = float(np.mean([net_r(t, COST) for t in ax_t])) if ax_t else 0.0
        loso[sym] = {"contests_kept": len(keep),
                     "contest_mean_adv_r": round(float(Ak.mean()), 4) if len(Ak) else None,
                     "fullsim_delta_exp_r": round(e_ax - e_ta, 4)}
    res["loso"] = loso

    # ---- economic effect: full sims at all costs ----
    econ = {}
    for cost in COSTS:
        row = {}
        for vid, sfn in varmap.items():
            ti = []
            port = rc.simulate_ranked(all_trades, closes, cost, feats, sfn, 2, taken_out=ti)
            taken = [all_trades[i] for i in ti]
            rs = np.array([net_r(t, cost) for t in taken])
            gw = rs[rs > 0].sum(); gl = -rs[rs <= 0].sum()
            row[vid] = {
                "n": len(taken),
                "exp_r": round(float(rs.mean()), 4) if len(rs) else None,
                "pf": round(float(gw / gl), 2) if gl > 0 else None,
                "dd_pct": round(port["max_drawdown"] * 100, 2),
                "ret_pct": round((port["final_equity"] / pb.START_EQUITY - 1) * 100, 2),
            }
        refn = row["takeall"]["n"]
        out = {i for i in taken_idx["takeall"]} - taken_idx["adx"]
        inn = taken_idx["adx"] - {i for i in taken_idx["takeall"]}
        ro = [net_r(all_trades[i], cost) for i in out]
        ri = [net_r(all_trades[i], cost) for i in inn]
        row["delta_adx_vs_takeall"] = {
            "d_exp_r": round(row["adx"]["exp_r"] - row["takeall"]["exp_r"], 4),
            "d_pf": round(row["adx"]["pf"] - row["takeall"]["pf"], 2),
            "d_dd_pp": round(row["adx"]["dd_pct"] - row["takeall"]["dd_pct"], 2),
            "ranked_out_n": len(out),
            "ranked_out_exp_r": round(float(np.mean(ro)), 4) if ro else None,
            "swapped_in_n": len(inn),
            "swapped_in_exp_r": round(float(np.mean(ri)), 4) if ri else None,
            "ret_per_dd_adx": round(row["adx"]["ret_pct"] / row["adx"]["dd_pct"], 3)
                if row["adx"]["dd_pct"] else None,
            "ret_per_dd_takeall": round(row["takeall"]["ret_pct"] / row["takeall"]["dd_pct"], 3)
                if row["takeall"]["dd_pct"] else None,
        }
        row["delta_adx_vs_rs"] = {
            "d_exp_r": round(row["adx"]["exp_r"] - row["rs_spy_CONTROL"]["exp_r"], 4),
            "d_pf": round(row["adx"]["pf"] - row["rs_spy_CONTROL"]["pf"], 2),
            "d_dd_pp": round(row["adx"]["dd_pct"] - row["rs_spy_CONTROL"]["dd_pct"], 2),
        }
        econ[str(cost)] = row
    res["economic_effect"] = econ

    # ---- crowded bars (>=3 candidates) for context ----
    cb = {"n_timestamps": 0, "n_candidates": 0, "by_variant": {}}
    cts = {t for t, c in entries_by_t.items() if len(c) >= 3}
    cb["n_timestamps"] = len(cts)
    cb["n_candidates"] = sum(len(entries_by_t[t]) for t in cts)
    for vid in ("takeall", "rs_spy_CONTROL", "adx"):
        sel = [i for i in taken_idx[vid] if all_trades[i]["entry_time"] in cts]
        rs = [net_r(all_trades[i], COST) for i in sel]
        cb["by_variant"][vid] = {"taken": len(sel),
                                 "exp_r": round(float(np.mean(rs)), 4) if rs else None}
    res["crowded_bars_ctx"] = cb

    out = os.path.join(OUTDIR, "adx_protocol_results.json")
    json.dump(res, open(out, "w"), indent=1, default=str)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
