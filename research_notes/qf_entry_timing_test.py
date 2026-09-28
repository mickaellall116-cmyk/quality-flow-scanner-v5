#!/usr/bin/env python3
"""
Raw QF entry-timing validation against symbol-month matched random bars.

Research-only; does not change live/frozen Quality Flow.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

from research_notes.hema_research import fetch_symbol, regular_1h, resample_closed_4h
from research_notes.hema_qf_portfolio import SYMBOLS, prepare_symbol

OUT=Path("qf_entry_timing")
OUT.mkdir(exist_ok=True)
HORIZONS=[1,2,4,6,10,20]
SEEDS=list(range(500))
WARMUP=215


def month_key(ts):
    t=pd.Timestamp(ts)
    if t.tzinfo is not None:
        t=t.tz_localize(None)
    return str(t.to_period("M"))


def spy_ret(spy, entry_ts, exit_ts):
    if entry_ts not in spy.index or exit_ts not in spy.index:
        return np.nan
    e=float(spy.loc[entry_ts,"Open"]); x=float(spy.loc[exit_ts,"Close"])
    if not np.isfinite(e) or not np.isfinite(x) or e<=0:
        return np.nan
    return x/e-1.0


def event_record(sym,df,spy,i,kind):
    if i+max(HORIZONS)>=len(df) or i+1>=len(df):
        return None
    entry_i=i+1
    entry=float(df["Open"].iloc[entry_i])
    if not np.isfinite(entry) or entry<=0:
        return None
    r={
        "symbol":sym,"kind":kind,"signal_time":str(df.index[i]),
        "entry_time":str(df.index[entry_i]),"entry":entry,
        "year":int(df.index[i].year),"month":month_key(df.index[i]),
    }
    for h in HORIZONS:
        xi=entry_i+h-1
        px=float(df["Close"].iloc[xi])
        rr=px/entry-1.0
        sr=spy_ret(spy,df.index[entry_i],df.index[xi])
        r[f"ret_{h}"]=rr
        r[f"excess_{h}"]=rr-sr if np.isfinite(sr) else np.nan
    return r


def summarize(d):
    out={"n":int(len(d))}
    for h in HORIZONS:
        v=d[f"ret_{h}"].dropna().astype(float)
        e=d[f"excess_{h}"].dropna().astype(float)
        out[f"mean_ret_{h}_pct"]=float(v.mean()*100.0) if len(v) else None
        out[f"median_ret_{h}_pct"]=float(v.median()*100.0) if len(v) else None
        out[f"hit_{h}_pct"]=float((v>0).mean()*100.0) if len(v) else None
        out[f"mean_excess_{h}_pct"]=float(e.mean()*100.0) if len(e) else None
    return out


def stable_rng(seed,key):
    b=hashlib.sha256(f"{seed}|{key}".encode()).digest()[:8]
    return np.random.default_rng(int.from_bytes(b,"little",signed=False))


def build_pools(frames,spy):
    buckets={}
    need=max(HORIZONS)
    for sym,df in frames.items():
        for i in range(max(WARMUP,0),len(df)):
            if i+need>=len(df):
                continue
            if bool(df["qf_event"].iloc[i]):
                continue
            rec=event_record(sym,df,spy,i,"random")
            if rec is not None:
                buckets.setdefault((sym,rec["month"]),[]).append(rec)
    return {k:pd.DataFrame(v) for k,v in buckets.items()}


def matched_draw(pools,counts,seed):
    parts=[]
    for (sym,month),n in counts.items():
        pool=pools.get((sym,month))
        if pool is None or pool.empty:
            continue
        rng=stable_rng(seed,f"{sym}|{month}")
        take=int(n)
        idx=rng.choice(len(pool),size=take,replace=(len(pool)<take))
        parts.append(pool.iloc[np.atleast_1d(idx)])
    return pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()


def main():
    spy_i=regular_1h(fetch_symbol("SPY","1h","729d"))
    spy_h4=resample_closed_4h(spy_i,"SPY")

    frames={}
    qrows=[]
    for k,sym in enumerate(SYMBOLS,1):
        print(f"[{k}/{len(SYMBOLS)}] {sym}")
        df=prepare_symbol(sym,spy_h4)
        if df is None: continue
        frames[sym]=df
        for i in np.flatnonzero(df["qf_event"].fillna(False).to_numpy()):
            if i<WARMUP: continue
            rec=event_record(sym,df,spy_h4,int(i),"qf")
            if rec is not None:qrows.append(rec)

    qf=pd.DataFrame(qrows)
    qf.to_csv(OUT/"qf_events.csv",index=False)
    qsum=summarize(qf)

    counts=qf.groupby(["symbol","month"]).size()
    pools=build_pools(frames,spy_h4)
    rr=[]
    seed0=None
    for seed in SEEDS:
        rnd=matched_draw(pools,counts,seed)
        if seed0 is None: seed0=rnd.copy()
        s=summarize(rnd); s["seed"]=seed; rr.append(s)
        if seed%50==0: print("RANDOM",seed)
    rdf=pd.DataFrame(rr)
    rdf.to_csv(OUT/"random_matched_summaries.csv",index=False)
    if seed0 is not None: seed0.to_csv(OUT/"random_seed0_events.csv",index=False)

    compare={}
    for h in HORIZONS:
        col=f"mean_excess_{h}_pct"
        vals=rdf[col].dropna().astype(float)
        qv=qsum.get(col)
        compare[str(h)]={
            "qf_mean_excess_pct":qv,
            "random_mean_pct":float(vals.mean()) if len(vals) else None,
            "random_p2_5_pct":float(vals.quantile(.025)) if len(vals) else None,
            "random_p50_pct":float(vals.quantile(.5)) if len(vals) else None,
            "random_p97_5_pct":float(vals.quantile(.975)) if len(vals) else None,
            "one_sided_p_random_ge_qf":float((1+int((vals>=qv).sum()))/(len(vals)+1)) if len(vals) and qv is not None else None,
        }

    yearly={}
    for y,g in qf.groupby("year"):
        yearly[str(int(y))]=summarize(g)

    syms=[]
    for sym,g in qf.groupby("symbol"):
        e=g["excess_10"].dropna().astype(float)
        if len(e):
            syms.append({"symbol":sym,"n":int(len(e)),"mean_excess10_pct":float(e.mean()*100.0)})
    syms=sorted(syms,key=lambda z:z["mean_excess10_pct"],reverse=True)

    payload={
        "data_note":"30-symbol DST-safe recent-history 4H structural-core surrogate; not canonical 131-symbol PIT",
        "warmup_bars":WARMUP,
        "qf":qsum,
        "matched_random":compare,
        "yearly":yearly,
        "symbol_concentration_10bar":syms,
    }
    (OUT/"results.json").write_text(json.dumps(payload,indent=2))
    print("QF_ENTRY_TIMING_START")
    print(json.dumps(payload,indent=2))
    print("QF_ENTRY_TIMING_END")


if __name__=="__main__":
    main()
