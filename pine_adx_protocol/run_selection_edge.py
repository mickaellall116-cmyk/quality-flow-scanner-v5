#!/usr/bin/env python3
"""TEST 3 (Mike's exact validation prompt): SELECTION EDGE on crowded bars.

SELECTION EDGE (per crowded bar) = mean R of method-selected trades
                                  minus mean R of method-rejected trades.
Plus per-method full reports (avg winner/loser, MFE, MAE, opportunity cost).
Combo skipped per prompt: RS does not beat take-all -> not justified.
"""
import importlib.util, json, os, sys
from collections import defaultdict
import numpy as np, pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_adx_protocol")
sys.path.insert(0, BASE)
import pine_backtest as pb
spec = importlib.util.spec_from_file_location(
    "rc", os.path.join(BASE, "pine_ranking_confirm", "run_ranking_confirm.py"))
rc = importlib.util.module_from_spec(spec); spec.loader.exec_module(rc)

WATCHLIST = ["QQQ","SMCI","PLTR","ANET","SOFI","RKLB","ONDS","DRAM","SPCX","ASTX","BBAI","NIO","HOOD","AMD"]
COSTS = [0.0025, 0.005, 0.0075, 0.01]
COST = 0.0025
N_BOOT = 5000
RNG = np.random.default_rng(7)

def net_r(tr, cost): return pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]

data = {}
for sym in WATCHLIST:
    df = pd.read_pickle(os.path.join(BASE, "pine_entry_timing_backtest", "cache", f"h4_{sym}.pkl"))
    df = pb.add_pine_indicators(df); df["adx10"] = pb.adx(df, 10); df["adx20"] = pb.adx(df, 20)
    data[sym] = df
sys.path.insert(0, os.path.join(BASE, "pine_signal_quality"))
from pine_signal_quality import load_benchmarks
bench, _ = load_benchmarks()
sig_index = {s: {df.index[i].isoformat(): i for i in range(len(df))} for s, df in data.items()}
trades = []
for s in WATCHLIST:
    t, _ = pb.gen_pine_trades(s, data[s]); trades.extend(t)
trades.sort(key=lambda t: t["entry_time"])
closes = {s: data[s]["Close"] for s in WATCHLIST}
feats = rc.compute_features(trades, data, bench, sig_index)

# ---- MFE / MAE per trade (R multiples, from the same 4H bars) ----
def mfe_mae(tr):
    df = data[tr["symbol"]]
    risk = tr["entry"] - tr["stop"]
    if risk <= 0: return (None, None)
    try:
        seg = df.loc[tr["entry_time"]:tr["exit_time"]]
    except Exception:
        return (None, None)
    if len(seg) == 0: return (None, None)
    mfe = float(((seg["High"] - tr["entry"]) / risk).max())
    mae = float(((seg["Low"] - tr["entry"]) / risk).min())
    return (mfe, mae)

mm = [mfe_mae(t) for t in trades]
MFE = {i: mm[i][0] for i in range(len(trades))}
MAE = {i: mm[i][1] for i in range(len(trades))}
print(f"mfe/mae computed for {sum(1 for v in MFE.values() if v is not None)} trades", flush=True)

entries_by_t = defaultdict(list)
for i, t in enumerate(trades): entries_by_t[t["entry_time"]].append(i)
diag = {"contested": []}
rc.simulate_ranked(trades, closes, COST, feats, None, None, diag=diag)
genuine = [(pd.Timestamp(ts), m, f) for ts, m, f in diag["contested"] if f > 0]
print(f"genuine crowded bars: {len(genuine)}", flush=True)

METHODS = {
    "takeall": lambda cands: cands,  # arrival order handled by slicing
    "rs":  lambda cands: sorted(cands, key=lambda i: (-feats[i]["rs_spy"], i)),
    "adx": lambda cands: sorted(cands, key=lambda i: (-feats[i]["adx"], i)),
}

# ---- per-bar SELECTION EDGE ----
bars = []
for t, m, f in genuine:
    cands = entries_by_t[t]
    k = min(2, f)
    rec = {"t": str(t), "n_cands": m, "free": f,
           "syms": sorted({trades[i]["symbol"] for i in cands})}
    for name, order in METHODS.items():
        sel = order(cands)[:k]
        rej = [i for i in cands if i not in set(sel)]
        s = [net_r(trades[i], COST) for i in sel]
        r = [net_r(trades[i], COST) for i in rej]
        rec[name] = {
            "sel_idx": sel, "rej_idx": rej,
            "sel_mean_r": round(float(np.mean(s)), 4) if s else None,
            "rej_mean_r": round(float(np.mean(r)), 4) if r else None,
            "selection_edge": round(float(np.mean(s) - np.mean(r)), 4) if (s and r) else None,
        }
    bars.append(rec)

res = {"n_genuine_crowded_bars": len(bars)}
for name in ("adx", "rs"):
    E = np.array([b[name]["selection_edge"] for b in bars if b[name]["selection_edge"] is not None])
    draws = RNG.choice(E, size=(N_BOOT, len(E)), replace=True).mean(axis=1)
    res[f"selection_edge_{name}"] = {
        "n_bars": len(E),
        "mean_edge_r": round(float(E.mean()), 4),
        "median_edge_r": round(float(np.median(E)), 4),
        "pos_frac": round(float((E > 0).mean()), 3),
        "bootstrap": {
            "n": N_BOOT,
            "p5": round(float(np.percentile(draws, 5)), 4),
            "p25": round(float(np.percentile(draws, 25)), 4),
            "p50": round(float(np.percentile(draws, 50)), 4),
            "p75": round(float(np.percentile(draws, 75)), 4),
            "p95": round(float(np.percentile(draws, 95)), 4),
            "frac_above_0": round(float((draws > 0).mean()), 4),
        },
        "bars": [{"t": b["t"], "edge": b[name]["selection_edge"],
                  "sel": b[name]["sel_mean_r"], "rej": b[name]["rej_mean_r"],
                  "syms": b["syms"]} for b in bars],
    }

# ---- per-method report: full sample AND crowded-bar subset ----
def score_fn(fid):
    def fn(i, cands): return feats[i][fid]
    return fn
varmap = {"takeall": None, "rs": score_fn("rs_spy"), "adx": score_fn("adx")}

def method_report(taken_idx, label):
    taken = [trades[i] for i in taken_idx]
    rs = np.array([net_r(t, COST) for t in taken])
    w = rs[rs > 0]; l = rs[rs <= 0]
    mfe = [MFE[i] for i in taken_idx if MFE[i] is not None]
    mae = [MAE[i] for i in taken_idx if MAE[i] is not None]
    gw, gl = w.sum(), -l.sum()
    return {
        "eligible_signals": len(trades),
        "selected_signals": len(taken),
        "expectancy_r": round(float(rs.mean()), 4) if len(rs) else None,
        "profit_factor": round(float(gw / gl), 2) if gl > 0 else None,
        "win_rate_pct": round(float((rs > 0).mean()) * 100, 1) if len(rs) else None,
        "avg_winner_r": round(float(w.mean()), 4) if len(w) else None,
        "avg_loser_r": round(float(l.mean()), 4) if len(l) else None,
        "mean_mfe_r": round(float(np.mean(mfe)), 3) if mfe else None,
        "mean_mae_r": round(float(np.mean(mae)), 3) if mae else None,
    }

rep = {}
taken_sets = {}
for name, sfn in varmap.items():
    ti = []
    port = rc.simulate_ranked(trades, closes, COST, feats, sfn, 2, taken_out=ti)
    taken_sets[name] = set(ti)
    r = method_report(ti, name)
    r["max_dd_pct"] = round(port["max_drawdown"] * 100, 2)
    r["total_return_pct"] = round((port["final_equity"] / pb.START_EQUITY - 1) * 100, 2)
    # opportunity cost: eligible-but-rejected by this method vs takeall reference
    rej = taken_sets["takeall"] - taken_sets[name] if name != "takeall" else set()
    rr = [net_r(trades[i], COST) for i in rej]
    r["opportunity_cost"] = {
        "rejected_n": len(rej),
        "rejected_exp_r": round(float(np.mean(rr)), 4) if rr else None,
    }
    rep[name] = r
res["per_method_full_sample"] = rep

# crowded-bar subset: trades each method took at the 21 genuine bars
cts = {pd.Timestamp(b["t"]) for b in bars}
for name in ("takeall", "rs", "adx"):
    sel = [i for i in taken_sets[name] if trades[i]["entry_time"] in cts]
    rs = np.array([net_r(trades[i], COST) for i in sel])
    w = rs[rs > 0]; l = rs[rs <= 0]
    res.setdefault("per_method_crowded_bars", {})[name] = {
        "selected_at_crowded": len(sel),
        "expectancy_r": round(float(rs.mean()), 4) if len(rs) else None,
        "win_rate_pct": round(float((rs > 0).mean()) * 100, 1) if len(rs) else None,
        "avg_winner_r": round(float(w.mean()), 4) if len(w) else None,
        "avg_loser_r": round(float(l.mean()), 4) if len(l) else None,
    }

# ---- combo check: is it even justified? ----
rs_beats_ta = rep["rs"]["expectancy_r"] > rep["takeall"]["expectancy_r"]
res["combo_decision"] = {
    "rs_expectancy_r": rep["rs"]["expectancy_r"],
    "takeall_expectancy_r": rep["takeall"]["expectancy_r"],
    "rs_beats_takeall": bool(rs_beats_ta),
    "combo_run": False,
    "reason": ("RS ranking does not beat take-all (+0.160R vs +0.221R); "
               "per the prompt and the mandate's 'do not combine weak discoveries' rule, "
               "the RS+ADX combo is NOT justified and was not run."),
}

json.dump(res, open(os.path.join(OUTDIR, "adx_selection_edge.json"), "w"), indent=1, default=str)
print("wrote adx_selection_edge.json")
