#!/usr/bin/env python3
"""
No-lookahead QF pre-cross convergence test.

Classifies only information available on the completed QF signal bar:
HEMA20 < HEMA40, HEMA20 rising, and bearish HEMA gap narrowing.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

from research_notes.hema_research import fetch_symbol, regular_1h, resample_closed_4h
from research_notes.hema_qf_portfolio import SYMBOLS, prepare_symbol

OUT=Path("qf_precross")
OUT.mkdir(exist_ok=True)
HORIZONS=[4,6,10,20]


def spy_ret(spy: pd.DataFrame, entry_ts, exit_ts):
    if entry_ts not in spy.index or exit_ts not in spy.index:
        return np.nan
    e=float(spy.loc[entry_ts,"Open"]); x=float(spy.loc[exit_ts,"Close"])
    if not np.isfinite(e) or not np.isfinite(x) or e<=0:
        return np.nan
    return x/e-1.0


def rec_for(sym, df, spy, i):
    if i<1 or i+20>=len(df) or i+1>=len(df):
        return None
    h20=float(df["HEMA20"].iloc[i]); h40=float(df["HEMA40"].iloc[i])
    p20=float(df["HEMA20"].iloc[i-1]); p40=float(df["HEMA40"].iloc[i-1])
    if not all(np.isfinite(v) for v in [h20,h40,p20,p40]):
        return None
    if not h20<h40:
        return None
    gap=h40-h20; pgap=p40-p20
    converging=(h20>p20) and (gap<pgap)

    entry_i=i+1
    entry=float(df["Open"].iloc[entry_i])
    if not np.isfinite(entry) or entry<=0:
        return None
    out={
        "symbol":sym,
        "signal_time":str(df.index[i]),
        "entry_time":str(df.index[entry_i]),
        "year":int(df.index[i].year),
        "group":"PRE_CROSS_CONVERGING" if converging else "BEAR_NOT_CONVERGING",
        "hema20":h20,"hema40":h40,
        "gap":gap,"prior_gap":pgap,
        "hema20_delta":h20-p20,
        "gap_delta":gap-pgap,
        "future_cross_within4":bool(df["big_green"].iloc[i+1:min(i+5,len(df))].fillna(False).any()),
    }
    for h in HORIZONS:
        xi=i+h
        exit_px=float(df["Close"].iloc[xi])
        r=exit_px/entry-1.0
        sr=spy_ret(spy,df.index[entry_i],df.index[xi])
        out[f"ret_{h}"]=r
        out[f"excess_{h}"]=r-sr if np.isfinite(sr) else np.nan
    w=df.iloc[entry_i:i+11]
    out["mae10_pct"]=(float(w["Low"].min())/entry-1.0)*100.0
    out["mfe10_pct"]=(float(w["High"].max())/entry-1.0)*100.0
    return out


def summarize(g):
    out={"n":int(len(g))}
    if not len(g): return out
    out["future_cross_within4_pct"]=float(g["future_cross_within4"].mean()*100.0)
    out["mean_mae10_pct"]=float(g["mae10_pct"].mean())
    out["mean_mfe10_pct"]=float(g["mfe10_pct"].mean())
    for h in HORIZONS:
        v=g[f"ret_{h}"].dropna().astype(float)
        e=g[f"excess_{h}"].dropna().astype(float)
        out[f"mean_ret_{h}_pct"]=float(v.mean()*100.0) if len(v) else None
        out[f"median_ret_{h}_pct"]=float(v.median()*100.0) if len(v) else None
        out[f"hit_{h}_pct"]=float((v>0).mean()*100.0) if len(v) else None
        out[f"mean_excess_{h}_pct"]=float(e.mean()*100.0) if len(e) else None
    return out


def boot_diff(a,b,seed=280929,reps=20000):
    a=np.asarray(a,dtype=float); b=np.asarray(b,dtype=float)
    a=a[np.isfinite(a)]; b=b[np.isfinite(b)]
    if not len(a) or not len(b): return {}
    rng=np.random.default_rng(seed)
    vals=np.empty(reps)
    for j in range(reps):
        vals[j]=rng.choice(a,size=len(a),replace=True).mean()-rng.choice(b,size=len(b),replace=True).mean()
    d=float(a.mean()-b.mean())
    return {
        "n_a":int(len(a)),"n_b":int(len(b)),"mean_diff_pct_points":d,
        "ci95_low":float(np.quantile(vals,0.025)),
        "ci95_high":float(np.quantile(vals,0.975)),
        "p_le_zero":float((1+np.sum(vals<=0))/(reps+1)),
    }


def group_payload(x):
    out={}
    for grp,g in x.groupby("group"):
        out[grp]=summarize(g)
    if {"PRE_CROSS_CONVERGING","BEAR_NOT_CONVERGING"}.issubset(out):
        a=x[x["group"]=="PRE_CROSS_CONVERGING"]["excess_10"].to_numpy()*100.0
        b=x[x["group"]=="BEAR_NOT_CONVERGING"]["excess_10"].to_numpy()*100.0
        out["bootstrap_converging_minus_other_excess10"]=boot_diff(a,b)
    return out


def main():
    spy_i=regular_1h(fetch_symbol("SPY","1h","729d"))
    spy_h4=resample_closed_4h(spy_i,"SPY")

    rows=[]
    frames=0
    for k,sym in enumerate(SYMBOLS,1):
        print(f"[{k}/{len(SYMBOLS)}] {sym}")
        df=prepare_symbol(sym,spy_h4)
        if df is None: continue
        frames+=1
        for i in np.flatnonzero(df["qf_event"].fillna(False).to_numpy()):
            r=rec_for(sym,df,spy_h4,int(i))
            if r is not None: rows.append(r)
    d=pd.DataFrame(rows)
    d.to_csv(OUT/"events.csv",index=False)

    disc=d[d["year"]<=2025].copy()
    hold=d[d["year"]==2026].copy()

    by_symbol=[]
    cg=d[d["group"]=="PRE_CROSS_CONVERGING"]
    for sym,g in cg.groupby("symbol"):
        by_symbol.append({
            "symbol":sym,"n":int(len(g)),
            "mean_excess10_pct":float(g["excess_10"].mean()*100.0),
            "future_cross_within4_pct":float(g["future_cross_within4"].mean()*100.0),
        })
    by_symbol=sorted(by_symbol,key=lambda z:z["mean_excess10_pct"],reverse=True)

    payload={
        "data_note":"30-symbol DST-safe recent-history 4H structural-core surrogate; not canonical 131-symbol PIT",
        "frames":frames,
        "all":group_payload(d),
        "discovery_2023_2025":group_payload(disc),
        "holdout_2026":group_payload(hold),
        "converging_by_symbol":by_symbol,
    }
    (OUT/"results.json").write_text(json.dumps(payload,indent=2))
    print("QF_PRECROSS_START")
    print(json.dumps(payload,indent=2))
    print("QF_PRECROSS_END")


if __name__=="__main__":
    main()
