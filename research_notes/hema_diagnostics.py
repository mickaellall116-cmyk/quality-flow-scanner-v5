#!/usr/bin/env python3
"""
HEMA mechanism diagnostics.
Research-only branch. Goal: determine whether HEMA's apparent edge comes from:
- general bull drift,
- HEMA's low-lag crossover itself,
- the saved crossover-low zone,
- first vs repeated retests,
- fresh vs stale zones,
- shallow vs deep penetrations,
- specific 20/40 parameter choice,
- or a few high-beta names.
"""

from __future__ import annotations
import json, math, time
from pathlib import Path
import numpy as np
import pandas as pd

from research_notes.hema_research import (
    SYMBOLS, fetch_symbol, regular_1h, add_hema, atr, ema,
    resample_closed_4h, daily_from_h4, weekly_from_h4, hema
)

PAIRS=[(15,30),(20,40),(25,50),(30,60)]
H=10

def exact_meta(df: pd.DataFrame, fast_col="HEMA20", slow_col="HEMA40") -> pd.DataFrame:
    x=df.copy()
    fast=x[fast_col].astype(float); slow=x[slow_col].astype(float)
    bigg=(fast>slow)&(fast.shift(1)<=slow.shift(1))
    bigr=(fast<slow)&(fast.shift(1)>=slow.shift(1))
    x["diag_big_green"]=bigg; x["diag_big_red"]=bigr
    n=len(x)
    sig=np.zeros(n,bool); age=np.full(n,np.nan); nth=np.full(n,np.nan)
    pierce=np.zeros(n,bool); current_bull=np.zeros(n,bool); samebar=np.zeros(n,bool)
    zone_bottom=np.full(n,np.nan); zone_top=np.full(n,np.nan)
    last_bull=None; count=0
    vals=x[["Open","High","Low","Close","ATR14"]].copy()
    for i in range(n):
        if bool(bigg.iloc[i]):
            vola=float(vals["ATR14"].iloc[i])/2
            last_bull=(float(vals["Low"].iloc[i]),float(vals["Low"].iloc[i])+vola,i)
            count=0
        if last_bull is None: continue
        lo,top,ci=last_bull
        r=vals.iloc[i]
        cond=(float(r["Low"])<top and float(r["High"])>top and float(r["Open"])>top and float(r["Close"])>top)
        if cond:
            count+=1; sig[i]=True; age[i]=i-ci; nth[i]=count
            pierce[i]=float(r["Low"])<lo
            current_bull[i]=bool(fast.iloc[i]>slow.iloc[i])
            samebar[i]=(i==ci); zone_bottom[i]=lo; zone_top[i]=top
    x["diag_small_green"]=sig
    x["diag_age"]=age; x["diag_nth"]=nth; x["diag_pierce_bottom"]=pierce
    x["diag_current_bull"]=current_bull; x["diag_samebar"]=samebar
    x["diag_zone_bottom"]=zone_bottom; x["diag_zone_top"]=zone_top
    return x

def simple_rejection(df: pd.DataFrame) -> pd.Series:
    # Does the saved crossover-zone add anything versus merely rejecting HEMA20?
    return (
        (df["HEMA20"]>df["HEMA40"]) &
        (df["Low"]<df["HEMA20"]) &
        (df["High"]>df["HEMA20"]) &
        (df["Open"]>df["HEMA20"]) &
        (df["Close"]>df["HEMA20"])
    )

def ema_zone_retest(df: pd.DataFrame) -> pd.Series:
    x=df.copy()
    e20=ema(x["Close"],20); e40=ema(x["Close"],40)
    cross=(e20>e40)&(e20.shift(1)<=e40.shift(1))
    sig=np.zeros(len(x),bool); z=None
    for i in range(len(x)):
        if bool(cross.iloc[i]):
            vola=float(x["ATR14"].iloc[i])/2
            z=(float(x["Low"].iloc[i]),float(x["Low"].iloc[i])+vola,i)
        if z:
            lo,top,ci=z; r=x.iloc[i]
            if float(r["Low"])<top and float(r["High"])>top and float(r["Open"])>top and float(r["Close"])>top:
                sig[i]=True
    return pd.Series(sig,index=x.index)

def forward_return(df,i,h=H):
    if i+1+h>=len(df): return np.nan
    entry=float(df["Open"].iloc[i+1]); out=float(df["Close"].iloc[i+1+h])
    return (out/entry-1)*100 if entry>0 else np.nan

def aligned_spy_return(spy: pd.DataFrame, signal_ts, h=H):
    if signal_ts not in spy.index: return np.nan
    i=spy.index.get_loc(signal_ts)
    if isinstance(i,slice) or isinstance(i,np.ndarray): return np.nan
    if i+1+h>=len(spy): return np.nan
    entry=float(spy["Open"].iloc[i+1]); out=float(spy["Close"].iloc[i+1+h])
    return (out/entry-1)*100 if entry>0 else np.nan

def year_of(ts): return pd.Timestamp(ts).year

def make_rows(sym,tf,df,spy):
    x=exact_meta(add_hema(df))
    x["simple_hema20_rejection"]=simple_rejection(x)
    x["ema20_40_zone_retest"]=ema_zone_retest(x)
    rows=[]
    # broad event families
    tests={
        "big_green":x["diag_big_green"],
        "small_green_exact":x["diag_small_green"],
        "simple_hema20_rejection":x["simple_hema20_rejection"],
        "ema20_40_zone_retest":x["ema20_40_zone_retest"],
        "any_bull_regime":x["HEMA20"]>x["HEMA40"],
    }
    for name,mask in tests.items():
        for i in np.flatnonzero(mask.fillna(False).to_numpy()):
            r=forward_return(x,i)
            if not np.isfinite(r): continue
            sr=aligned_spy_return(spy,x.index[i])
            rec={"symbol":sym,"timeframe":tf,"event":name,"signal_time":str(x.index[i]),
                 "year":year_of(x.index[i]),"ret10_pct":r,
                 "spy10_pct":sr,"excess10_pct":r-sr if np.isfinite(sr) else np.nan}
            if name=="small_green_exact":
                rec.update(age=float(x["diag_age"].iloc[i]),nth=int(x["diag_nth"].iloc[i]),
                           pierce_bottom=bool(x["diag_pierce_bottom"].iloc[i]),
                           current_bull=bool(x["diag_current_bull"].iloc[i]),
                           samebar=bool(x["diag_samebar"].iloc[i]))
            rows.append(rec)
    return rows,x

def param_rows(sym,tf,df,spy):
    out=[]
    base=df.copy(); base["ATR14"]=atr(base,14)
    for a,b in PAIRS:
        fast=hema(base["Close"],a); slow=hema(base["Close"],b)
        x=base.copy(); x["F"]=fast; x["S"]=slow
        x=exact_meta(x,"F","S")
        # "clean-ish" first retest after cross and before opposite cross
        clean=np.zeros(len(x),bool); active=None
        bigg=x["diag_big_green"]; bigr=x["diag_big_red"]
        for i in range(len(x)):
            if bool(bigg.iloc[i]):
                vola=float(x["ATR14"].iloc[i])/2
                active=(float(x["Low"].iloc[i]),float(x["Low"].iloc[i])+vola,i,False)
            elif bool(bigr.iloc[i]):
                active=None
            if active:
                lo,top,ci,used=active
                if not used and i>ci:
                    r=x.iloc[i]
                    cond=(float(r["Low"])<top and float(r["High"])>top and float(r["Open"])>top and float(r["Close"])>top and float(r["Low"])>=lo)
                    if cond:
                        clean[i]=True; active=(lo,top,ci,True)
        for name,mask in [("cross",bigg),("strict_first_retest",pd.Series(clean,index=x.index))]:
            vals=[]
            excess=[]
            for i in np.flatnonzero(mask.fillna(False).to_numpy()):
                rr=forward_return(x,i)
                if np.isfinite(rr):
                    vals.append(rr)
                    sr=aligned_spy_return(spy,x.index[i])
                    if np.isfinite(sr): excess.append(rr-sr)
            if vals:
                out.append({"symbol":sym,"timeframe":tf,"fast":a,"slow":b,"kind":name,
                            "n":len(vals),"mean10_pct":float(np.mean(vals)),
                            "median10_pct":float(np.median(vals)),
                            "hit10_pct":float(np.mean(np.array(vals)>0)*100),
                            "mean_excess10_pct":float(np.mean(excess)) if excess else np.nan})
    return out

def summarize_events(df):
    out=[]
    for (tf,event),g in df.groupby(["timeframe","event"]):
        v=g["ret10_pct"].dropna(); e=g["excess10_pct"].dropna()
        out.append({"timeframe":tf,"event":event,"n":int(len(v)),
                    "mean10_pct":round(float(v.mean()),4),
                    "median10_pct":round(float(v.median()),4),
                    "hit10_pct":round(float((v>0).mean()*100),2),
                    "mean_excess10_pct":round(float(e.mean()),4) if len(e) else None})
    return out

def small_green_slices(df):
    g=df[df.event=="small_green_exact"].copy()
    out=[]
    defs={
        "all":pd.Series(True,index=g.index),
        "same_bar":g["samebar"]==True,
        "later_only":g["samebar"]==False,
        "current_bull":g["current_bull"]==True,
        "stale_after_bear":g["current_bull"]==False,
        "first_retest":g["nth"]==1,
        "repeat_retest":g["nth"]>=2,
        "zone_held":g["pierce_bottom"]==False,
        "pierced_whole_zone":g["pierce_bottom"]==True,
        "age_0":g["age"]==0,
        "age_1_3":(g["age"]>=1)&(g["age"]<=3),
        "age_4_10":(g["age"]>=4)&(g["age"]<=10),
        "age_11_20":(g["age"]>=11)&(g["age"]<=20),
        "age_21_plus":g["age"]>=21,
    }
    for tf in sorted(g.timeframe.unique()):
        h=g[g.timeframe==tf]
        for name,mask0 in defs.items():
            mask=mask0.reindex(h.index).fillna(False)
            z=h[mask]
            if len(z)<5: continue
            v=z.ret10_pct.dropna(); e=z.excess10_pct.dropna()
            out.append({"timeframe":tf,"slice":name,"n":int(len(v)),
                        "mean10_pct":round(float(v.mean()),4),
                        "median10_pct":round(float(v.median()),4),
                        "hit10_pct":round(float((v>0).mean()*100),2),
                        "mean_excess10_pct":round(float(e.mean()),4) if len(e) else None})
    return out

def concentration(df):
    g=df[(df.timeframe=="4H")&(df.event=="small_green_exact")]
    by=g.groupby("symbol").agg(n=("ret10_pct","count"),mean10=("ret10_pct","mean"),sum10=("ret10_pct","sum")).sort_values("sum10",ascending=False)
    total=g.ret10_pct.sum()
    top3=by.head(3)
    return {
        "total_n":int(len(g)),"overall_mean10_pct":round(float(g.ret10_pct.mean()),4),
        "top3_symbols":top3.reset_index().round(4).to_dict("records"),
        "top3_share_of_sum_pct":round(float(top3.sum10.sum()/total*100),2) if total else None,
        "ex_top3_mean10_pct":round(float(g[~g.symbol.isin(top3.index)].ret10_pct.mean()),4)
    }

def stress_2022(df):
    z=df[(df.year==2022)&(df.timeframe.isin(["1D","1W"]))].copy()
    return summarize_events(z)

def main():
    outdir=Path("hema_diagnostics"); outdir.mkdir(exist_ok=True)
    allrows=[]; params=[]

    # Fetch SPY first per timeframe.
    spy_i=regular_1h(fetch_symbol("SPY","1h","729d"))
    spy4=add_hema(resample_closed_4h(spy_i,"SPY"))
    spyd=add_hema(fetch_symbol("SPY","1d","10y"))
    tmp=spyd[["Open","High","Low","Close","Volume"]].copy()
    keys=[f"{t.isocalendar().year}-{t.isocalendar().week:02d}" for t in tmp.index]
    rows=[]
    for key in pd.Index(keys).unique():
        g=tmp[np.array(keys)==key]; ts=g.index[-1]
        rows.append((ts,float(g.Open.iloc[0]),float(g.High.max()),float(g.Low.min()),float(g.Close.iloc[-1]),float(g.Volume.sum())))
    spyw=add_hema(pd.DataFrame(rows,columns=["idx","Open","High","Low","Close","Volume"]).set_index("idx"))

    for k,sym in enumerate(SYMBOLS,1):
        print(f"[{k}/{len(SYMBOLS)}] {sym}")
        intr=regular_1h(fetch_symbol(sym,"1h","729d"))
        daily=fetch_symbol(sym,"1d","10y")
        if not intr.empty:
            h4=resample_closed_4h(intr,sym)
            if len(h4)>60:
                r,_=make_rows(sym,"4H",h4,spy4); allrows.extend(r)
                params.extend(param_rows(sym,"4H",h4,spy4))
        if not daily.empty:
            d=daily[["Open","High","Low","Close","Volume"]].copy()
            r,_=make_rows(sym,"1D",d,spyd); allrows.extend(r)
            params.extend(param_rows(sym,"1D",d,spyd))
            keys=[f"{t.isocalendar().year}-{t.isocalendar().week:02d}" for t in d.index]
            rows=[]
            for key in pd.Index(keys).unique():
                g=d[np.array(keys)==key]; ts=g.index[-1]
                rows.append((ts,float(g.Open.iloc[0]),float(g.High.max()),float(g.Low.min()),float(g.Close.iloc[-1]),float(g.Volume.sum())))
            w=pd.DataFrame(rows,columns=["idx","Open","High","Low","Close","Volume"]).set_index("idx")
            if len(w)>60:
                r,_=make_rows(sym,"1W",w,spyw); allrows.extend(r)
                params.extend(param_rows(sym,"1W",w,spyw))

    ev=pd.DataFrame(allrows); pp=pd.DataFrame(params)
    ev.to_csv(outdir/"diagnostic_events.csv",index=False)
    pp.to_csv(outdir/"parameter_robustness.csv",index=False)

    # Aggregate parameter study across symbols, weighted by event count.
    parsum=[]
    for keys,g in pp.groupby(["timeframe","fast","slow","kind"]):
        n=int(g.n.sum())
        mean=float(np.average(g.mean10_pct,weights=g.n))
        hit=float(np.average(g.hit10_pct,weights=g.n))
        excess_g=g.dropna(subset=["mean_excess10_pct"])
        ex=float(np.average(excess_g.mean_excess10_pct,weights=excess_g.n)) if len(excess_g) else np.nan
        parsum.append({"timeframe":keys[0],"fast":int(keys[1]),"slow":int(keys[2]),"kind":keys[3],
                       "n":n,"mean10_pct":round(mean,4),"hit10_pct":round(hit,2),
                       "mean_excess10_pct":round(ex,4) if np.isfinite(ex) else None})

    headline={
        "event_summary":summarize_events(ev),
        "small_green_slices":small_green_slices(ev),
        "parameter_robustness":parsum,
        "stress_2022":stress_2022(ev),
        "concentration_4h_small_green":concentration(ev),
        "interpretation_guardrails":[
            "Raw returns can look strong simply because the sample is long-biased and growth-heavy; SPY-relative excess is reported.",
            "The exact AlgoAlpha small-green zone persists through opposite HEMA crosses and can fire repeatedly; slices isolate stale and repeat signals.",
            "Same-bar small-green signals are separated because the source creates the zone and tests it on the same bar.",
            "Parameter robustness tests neighboring HEMA length pairs; a result unique to 20/40 is more suspicious.",
            "This diagnoses the indicator mechanism; it is not yet a canonical V5.4 portfolio re-run."
        ]
    }
    (outdir/"diagnostics.json").write_text(json.dumps(headline,indent=2))
    print("DIAGNOSTICS_START")
    print(json.dumps(headline,indent=2))
    print("DIAGNOSTICS_END")

if __name__=="__main__":
    main()
