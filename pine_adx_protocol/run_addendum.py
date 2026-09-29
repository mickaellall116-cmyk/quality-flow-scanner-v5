#!/usr/bin/env python3
"""Addendum: dev/val + yearly + LOSO for ADX vs rs_top2 (Verdict A gates)."""
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
COST = 0.0025
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

entries_by_t = defaultdict(list)
for i, t in enumerate(trades): entries_by_t[t["entry_time"]].append(i)
diag = {"contested": []}
rc.simulate_ranked(trades, closes, COST, feats, None, None, diag=diag)
genuine = [(pd.Timestamp(ts), m, f) for ts, m, f in diag["contested"] if f > 0]

def adv_at(t, m, f, ref_fid, cost=COST):
    cands = entries_by_t[t]; k = min(2, f)
    ax = sorted(cands, key=lambda i: (-feats[i]["adx"], i))[:k]
    rf = sorted(cands, key=lambda i: (-feats[i][ref_fid], i))[:k]
    a = [net_r(trades[i], cost) for i in ax]; b = [net_r(trades[i], cost) for i in rf]
    return float(np.mean(a) - np.mean(b)) if a and b else 0.0

out = {}
A = np.array([adv_at(t, m, f, "rs_spy") for t, m, f in genuine])
out["pooled"] = {"n": len(A), "mean": round(float(A.mean()), 4),
                 "pos_frac": round(float((A > 0).mean()), 3)}
dv = {}
for lbl, pred in (("dev", lambda t: t.tz_localize(None) <= pd.Timestamp("2024-12-31")),
                  ("val", lambda t: t.tz_localize(None) > pd.Timestamp("2024-12-31"))):
    B = np.array([adv_at(t, m, f, "rs_spy") for t, m, f in genuine if pred(t)])
    dv[lbl] = {"n": len(B), "mean": round(float(B.mean()), 4) if len(B) else None}
out["dev_val"] = dv
yr = defaultdict(list)
for t, m, f in genuine: yr[t.year].append(adv_at(t, m, f, "rs_spy"))
out["by_year"] = {str(y): {"n": len(v), "mean": round(float(np.mean(v)), 4)} for y, v in sorted(yr.items())}

# LOSO on adx-vs-rs full-sim differential
def score_fn(fid):
    def fn(i, cands): return feats[i][fid]
    return fn
loso = {}
for sym in WATCHLIST:
    sub = [t for t in trades if t["symbol"] != sym]
    sidx = {id(t): k for k, t in enumerate(sub)}
    fm = {sidx[id(trades[i])]: feats[i] for i in range(len(trades)) if id(trades[i]) in sidx}
    def s_adx(j, c, _fm=fm): return _fm[j]["adx"]
    def s_rs(j, c, _fm=fm): return _fm[j]["rs_spy"]
    ti_a, ti_r = [], []
    rc.simulate_ranked(sub, closes, COST, fm, s_adx, 2, taken_out=ti_a)
    rc.simulate_ranked(sub, closes, COST, fm, s_rs, 2, taken_out=ti_r)
    ea = float(np.mean([net_r(t, COST) for t in (sub[i] for i in ti_a)])) if ti_a else 0
    er = float(np.mean([net_r(t, COST) for t in (sub[i] for i in ti_r)])) if ti_r else 0
    loso[sym] = round(ea - er, 4)
out["loso_adx_vs_rs_delta"] = loso
json.dump(out, open(os.path.join(OUTDIR, "adx_protocol_addendum.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
