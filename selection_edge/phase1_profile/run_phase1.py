#!/usr/bin/env python3
"""Selection-Edge Worker A, Phase 1: per-stock profiling (descriptive only).

BLINDING: the 14 names (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX,
ASTX, BBAI, NIO, HOOD, AMD) are masked out of ALL characteristic-discovery
work. Working set = 131 PIT universe - 14 = 117 names.

R measure: net_r_50bps from canonical_trades.json (headline cost level).
Characteristics computed strictly from daily bars <= 2023-09-29 (last bar at
or before the 2023-09-30 universe formation date). No future performance used.
"""
import json, os, pickle, math
import numpy as np
import pandas as pd

MASKED = {"QQQ","SMCI","PLTR","ANET","SOFI","RKLB","ONDS","DRAM","SPCX",
          "ASTX","BBAI","NIO","HOOD","AMD"}
BASE = os.path.expanduser("~/workspace/quality-flow-scanner-v5/canonical_baseline")
OUT  = os.path.expanduser("~/workspace/quality-flow-scanner-v5/selection_edge/phase1_profile")
DATA = os.path.join(BASE, "data")
FORMATION = "2023-09-30"

trades = json.load(open(os.path.join(BASE, "canonical_trades.json")))
universe = json.load(open(os.path.join(BASE, "universe.json")))
work_syms = [u["symbol"] for u in universe if u["symbol"] not in MASKED]
# NOTE: only 8 of the 14 masked names are in the PIT universe (ASTX, BBAI, HOOD,
# ONDS, RKLB, SOFI were never in it). Working set = 123, all 14 excluded anyway.
assert len(work_syms) == 123, len(work_syms)

RKEY = "net_r_50bps"

# ---------------- per-stock stats ----------------
per_stock = {}
for sym in work_syms:
    st = [t for t in trades if t["symbol"] == sym]
    r = np.array([t[RKEY] for t in st])
    if len(r) == 0:
        per_stock[sym] = {"n": 0}
        continue
    w = r[r > 0]; l = r[r <= 0]
    gp = w.sum(); gl = -l.sum()
    cum = np.cumsum(r); peak = np.maximum.accumulate(cum)
    dd = float((cum - peak).min())          # own-series max drawdown in R
    per_stock[sym] = {
        "n": len(r),
        "expectancy_R": float(r.mean()),
        "sum_R": float(r.sum()),
        "pf": float(gp / gl) if gl > 0 else (float("inf") if gp > 0 else None),
        "win_rate": float((r > 0).mean()),
        "median_R": float(np.median(r)),
        "avg_winner_R": float(w.mean()) if len(w) else None,
        "avg_loser_R": float(l.mean()) if len(l) else None,
        "max_dd_R": dd,
        "gross_winners_R": float(gp),
        "gross_losers_R": float(gl),
    }

total_sum_R = sum(s["sum_R"] for s in per_stock.values() if s["n"])
total_abs_R = sum(abs(s["sum_R"]) for s in per_stock.values() if s["n"])
for sym, s in per_stock.items():
    if s["n"]:
        # share of total ABSOLUTE per-stock P&L (sums to 1 in magnitude; sign = stock's sign)
        s["pnl_contrib_share"] = s["sum_R"] / total_abs_R if total_abs_R else None
        s["sum_R"] = round(s["sum_R"], 4)

ranked = sorted([ (s, per_stock[s]) for s in per_stock if per_stock[s]["n"] >= 5 ],
                key=lambda kv: kv[1]["expectancy_R"], reverse=True)
thin = sorted([ (s, per_stock[s]) for s in per_stock if 0 < per_stock[s]["n"] < 5 ],
              key=lambda kv: kv[1]["n"], reverse=True)
zero = [s for s in per_stock if per_stock[s]["n"] == 0]

# ---------------- universe-formation observables ----------------
_d1 = {}
def d1(sym):
    if sym not in _d1:
        fn = os.path.join(DATA, f"d1_{sym}.pkl")
        _d1[sym] = pd.read_pickle(fn) if os.path.exists(fn) else None
    return _d1[sym]

spy = d1("SPY")

def feat(sym):
    df = d1(sym)
    out = {}
    if df is None or len(df) == 0:
        return out
    cut = df[df.index <= pd.Timestamp(FORMATION, tz="America/New_York")]
    if len(cut) < 64:
        return out
    c = cut["Close"]; h = cut["High"]; l = cut["Low"]; v = cut["Volume"]
    # trailing 63 trading days ending last bar <= formation date
    c63 = c.iloc[-63:]; h63 = h.iloc[-63:]; l63 = l.iloc[-63:]; v63 = v.iloc[-63:]
    # 1. trailing 63-day RS vs SPY (total return diff)
    scut = spy[spy.index <= pd.Timestamp(FORMATION, tz="America/New_York")].iloc[-63:]
    out["rs63_spy"] = float(c63.iloc[-1]/c63.iloc[0]-1) - float(scut["Close"].iloc[-1]/scut["Close"].iloc[0]-1)
    # 2. ADDV rank (1 = highest dollar volume) from universe.json
    # 3. sector from universe.json (handled outside)
    # 4. distance from trailing max high (52wk target; only ~4mo of history available)
    out["dist_high"] = float(c63.iloc[-1]/h63.max()-1)
    out["n_bars_used"] = int(len(cut))
    # 5. trailing 63-day 14d-ATR / price
    tr = pd.concat([h63-l63, (h63-c63.shift(1)).abs(), (l63-c63.shift(1)).abs()], axis=1).max(axis=1)
    atr14 = float(tr.iloc[-14:].mean())
    out["atr_pct"] = atr14 / float(c63.iloc[-1])
    # 6. dollar-volume trend: ADDV(last 21d) / ADDV(first 21d) of the 63d window
    dv = (c63*v63)
    out["dv_trend"] = float(dv.iloc[-21:].mean()/dv.iloc[:21].mean()) if dv.iloc[:21].mean()>0 else None
    out["addv63"] = float(dv.mean())
    return out

umap = {u["symbol"]: u for u in universe}
feats = {s: feat(s) for s in work_syms}
# ADDV rank from universe record (computed on formation date by pipeline)
for s in work_syms:
    if "addv_rank_2023_09_30" in umap[s] and umap[s]["addv_rank_2023_09_30"]:
        feats[s]["addv_rank"] = umap[s]["addv_rank_2023_09_30"]

# ---------------- group split ----------------
pos = [s for s,_ in ranked if _["expectancy_R"] > 0]  # ranked items are (sym, stats)
neg = [s for s,_ in ranked if _["expectancy_R"] <= 0]
pos_syms = pos; neg_syms = neg

def group_stats(syms):
    rs = np.array([t[RKEY] for s in syms for t in trades if t["symbol"] == s])
    return {
        "n_stocks": len(syms),
        "n_trades": int(len(rs)),
        "expectancy_R": float(rs.mean()),
        "sum_R": float(rs.sum()),
        "win_rate": float((rs>0).mean()),
        "pf": float(rs[rs>0].sum() / -rs[rs<=0].sum()) if (rs<=0).any() else None,
    }

NUM_KEYS = ["rs63_spy","dist_high","atr_pct","dv_trend","addv_rank"]

def group_feats(syms):
    d = {}
    for k in NUM_KEYS:
        vals = [feats[s][k] for s in syms if feats[s].get(k) is not None]
        if vals:
            d[k] = {"n": len(vals), "mean": float(np.mean(vals)),
                    "median": float(np.median(vals)), "std": float(np.std(vals, ddof=1)) if len(vals)>1 else 0.0}
    sects = [umap[s].get("sector") for s in syms]
    sects = [x for x in sects if x]
    from collections import Counter
    d["sector_counts"] = dict(Counter(sects))
    d["sector_n"] = len(sects)
    return d

gpos, gneg = group_feats(pos_syms), group_feats(neg_syms)
spos, sneg = group_stats(pos_syms), group_stats(neg_syms)

# difference table (trade-weighted groups)
diff = {}
for k in NUM_KEYS:
    if k in gpos and k in gneg:
        diff[k] = {
            "pos_mean": gpos[k]["mean"], "neg_mean": gneg[k]["mean"],
            "mean_diff": gpos[k]["mean"] - gneg[k]["mean"],
            "pos_median": gpos[k]["median"], "neg_median": gneg[k]["median"],
            "median_diff": gpos[k]["median"] - gneg[k]["median"],
        }

# sector share comparison (top sectors by count)
all_sect = {}
for s in pos_syms + neg_syms:
    sec = umap[s].get("sector")
    if sec: all_sect.setdefault(sec, {"pos":0,"neg":0})["pos" if s in pos_syms else "neg"] += 1
sector_table = {sec: {"pos":v["pos"],"neg":v["neg"],
    "pos_share": v["pos"]/len(pos_syms), "neg_share": v["neg"]/len(neg_syms)}
    for sec,v in sorted(all_sect.items(), key=lambda kv:-(kv[1]["pos"]+kv[1]["neg"]))}

# expectancy histogram over ranked stocks
exps = [st["expectancy_R"] for _,st in ranked]
buckets = {}
for e in exps:
    b = f"{math.floor(e*2)/2:.2f}..{math.floor(e*2)/2+0.5:.2f}"  # 0.5R buckets
    buckets[b] = buckets.get(b,0)+1

profile = {
    "meta": {"universe":131,"masked":14,"working_set":117,"r_key":RKEY,
             "formation_date":FORMATION,
             "note_dist_high":"only ~4mo of daily history pre-formation; 52wk-high distance approximated by max-high distance on available pre-formation history"},
    "per_stock": per_stock,
    "ranked_by_expectancy": [{"symbol":s, **st} for s,st in ranked],
    "thin_n_lt5": [{"symbol":s, **st} for s,st in thin],
    "zero_trade_stocks": zero,
    "n_ranked_ge5": len(ranked), "n_thin": len(thin), "n_zero": len(zero),
    "expectancy_histogram": buckets,
    "groups": {"positive_expectancy": spos, "negative_expectancy": sneg,
               "pos_symbols": pos_syms, "neg_symbols": neg_syms},
    "group_characteristics": {"pos": gpos, "neg": gneg},
    "characteristic_differences": diff,
    "sector_table": sector_table,
    "masked_14": sorted(MASKED),
}
os.makedirs(OUT, exist_ok=True)
json.dump(profile, open(os.path.join(OUT,"PROFILE.json"),"w"), indent=1)
print("ranked:",len(ranked),"thin:",len(thin),"zero:",len(zero))
print("pos group:",spos)
print("neg group:",sneg)
print(json.dumps(diff,indent=1))
