#!/usr/bin/env python3
"""
Quality Flow structural-core x HEMA portfolio test.

Research-only surrogate because the canonical V5.4 historical engine/cache is
not present in the public repository. Uses the current public scanner rules
recreated in hema_research.add_qf_core, next-bar-open execution, realistic
gap stops, 50 bps round-trip leg costs, 1% planned risk, max 6 positions,
5% heat cap, and rs_top2-style 20-bar return minus SPY for slot competition.

Purpose: isolate whether HEMA adds value to Quality Flow mechanics, not to
replace the canonical baseline.
"""
from __future__ import annotations

import json, math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from research_notes.hema_research import (
    SYMBOLS, fetch_symbol, regular_1h, resample_closed_4h,
    add_hema, add_qf_core, daily_from_h4, weekly_from_h4,
)

INITIAL_EQUITY=75_000.0
RISK_FRAC=0.01
MAX_OPEN=6
MAX_HEAT=0.05
ROUND_TRIP_BPS=50.0

ENTRY_VARIANTS = [
    "qf_baseline",
    "qf_4h_bull",
    "qf_daily_bull",
    "qf_4h_daily_bull",
    "qf_recent_big_green_4",
    "qf_recent_first_small_green_4",
]
EXIT_VARIANTS = [
    "current",
    "4h_big_red",
    "daily_big_red",
    "4h_small_red_clean",
]

def carry_htf_to_h4(h4_index, htf, col):
    if htf is None or htf.empty or col not in htf:
        return pd.Series(False,index=h4_index)
    s=pd.Series(htf[col].astype(bool).to_numpy(),index=htf.index)
    return s.reindex(h4_index,method="ffill").fillna(False).astype(bool)

def map_exact_htf_events(h4_index, htf, col):
    s=pd.Series(False,index=h4_index)
    if htf is None or htf.empty or col not in htf:return s
    for ts,v in htf[col].fillna(False).items():
        if bool(v) and ts in s.index:s.loc[ts]=True
    return s

def prepare_symbol(sym, spy_h4):
    intr=regular_1h(fetch_symbol(sym,"1h","729d"))
    if intr.empty:return None
    h4=resample_closed_4h(intr,sym)
    if len(h4)<240:return None
    h4=add_qf_core(add_hema(h4))
    d,_=daily_from_h4(h4)
    d=add_hema(d) if not d.empty else d
    w=weekly_from_h4(h4)
    w=add_hema(w) if not w.empty else w

    h4["daily_bull"]=carry_htf_to_h4(h4.index,d,"bull_regime")
    h4["weekly_bull"]=carry_htf_to_h4(h4.index,w,"bull_regime")
    h4["daily_big_red_evt"]=map_exact_htf_events(h4.index,d,"big_red")

    # first small green after most recent big green, invalidated by big red
    first=np.zeros(len(h4),bool); active=False
    for i in range(len(h4)):
        if bool(h4["big_green"].iloc[i]): active=True
        elif bool(h4["big_red"].iloc[i]): active=False
        if active and i>0 and bool(h4["small_green_strict"].iloc[i]):
            first[i]=True; active=False
    h4["first_small_green"]=first

    h4["recent_big_green_4"]=h4["big_green"].rolling(4,min_periods=1).max().fillna(0).astype(bool)
    h4["recent_first_small_green_4"]=pd.Series(first,index=h4.index).rolling(4,min_periods=1).max().fillna(0).astype(bool)

    # rs_top2-style relative strength: 20-bar return minus SPY.
    sret=h4["Close"]/h4["Close"].shift(20)-1.0
    spy=spy_h4["Close"].reindex(h4.index,method="ffill")
    pret=spy/spy.shift(20)-1.0
    h4["rs20_spy"]=sret-pret
    return h4

def entry_mask(h4, variant):
    q=h4["qf_event"].fillna(False)
    if variant=="qf_baseline":return q
    if variant=="qf_4h_bull":return q & h4["bull_regime"].fillna(False)
    if variant=="qf_daily_bull":return q & h4["daily_bull"].fillna(False)
    if variant=="qf_4h_daily_bull":return q & h4["bull_regime"].fillna(False) & h4["daily_bull"].fillna(False)
    if variant=="qf_recent_big_green_4":return q & h4["recent_big_green_4"].fillna(False)
    if variant=="qf_recent_first_small_green_4":return q & h4["recent_first_small_green_4"].fillna(False)
    raise KeyError(variant)

@dataclass
class Position:
    sym:str
    entry_i:int
    entry_time:object
    entry:float
    stop:float
    tp1:float
    shares:int
    risk_per_share:float
    planned_risk:float
    tp1_taken:bool=False
    runner_shares:int=0
    partial_r:float=0.0
    armed:bool=False
    pending_exit:bool=False
    pending_reason:str=""
    bars:int=0

def cost_dollars(notional, half_round_trip=True):
    # 50 bps round trip = 25 bps each leg.
    bps=(ROUND_TRIP_BPS/2.0 if half_round_trip else ROUND_TRIP_BPS)/10000.0
    return abs(notional)*bps

def simulate(entry_variant, exit_variant, frames):
    equity=INITIAL_EQUITY
    realized=0.0
    positions={}
    trades=[]
    events=[]

    # union timestamps
    timeline=sorted(set().union(*[set(df.index) for df in frames.values()]))

    # precompute candidate rows by timestamp
    candidates={}
    for sym,df in frames.items():
        m=entry_mask(df,entry_variant)
        for i in np.flatnonzero(m.to_numpy()):
            if i+1>=len(df):continue
            ts=df.index[i]
            candidates.setdefault(ts,[]).append((sym,i,float(df["rs20_spy"].iloc[i]) if np.isfinite(df["rs20_spy"].iloc[i]) else -999))

    # pending entries are filled at the next actual bar for that symbol.
    pending_entries=[]

    for ts in timeline:
        # 1) Fill pending entries whose next bar is this timestamp.
        still=[]
        for pe in pending_entries:
            sym=pe["sym"]; df=frames[sym]; ei=pe["entry_i"]
            if df.index[ei]!=ts:
                still.append(pe); continue
            if sym in positions:continue
            # recheck slot/heat at actual fill time
            planned_risk=equity*RISK_FRAC
            heat=sum(p.planned_risk for p in positions.values())/max(equity,1.0)
            if len(positions)>=MAX_OPEN or heat+planned_risk/max(equity,1.0)>MAX_HEAT+1e-12:
                continue
            entry=float(df["Open"].iloc[ei]); stop=float(pe["stop"]); tp1=float(pe["tp1"])
            rps=entry-stop
            if not np.isfinite(rps) or rps<=0 or entry<=0:continue
            shares=max(1,int(math.floor(planned_risk/rps)))
            notional=shares*entry
            c=cost_dollars(notional)
            realized-=c; equity-=c
            positions[sym]=Position(sym,ei,ts,entry,stop,tp1,shares,rps,shares*rps,False,shares,0.0,False,False,"",0)
            events.append({"time":str(ts),"symbol":sym,"event":"ENTRY","price":entry,"shares":shares,"cost":c})
        pending_entries=still

        # 2) Process open positions on this bar.
        to_close=[]
        for sym,p in list(positions.items()):
            df=frames[sym]
            if ts not in df.index:continue
            j=df.index.get_loc(ts)
            if isinstance(j,slice) or isinstance(j,np.ndarray):continue
            if j<p.entry_i:continue
            row=df.iloc[j]
            o,h,l,c=map(float,[row.Open,row.High,row.Low,row.Close])
            p.bars+=1

            # pending exit at open takes precedence
            if p.pending_exit:
                fill=o; qty=p.runner_shares if p.tp1_taken else p.shares
                pnl=(fill-p.entry)*qty
                cc=cost_dollars(fill*qty)
                realized+=pnl-cc; equity+=pnl-cc
                full_r=(fill-p.entry)/p.risk_per_share
                blend=(0.5*p.partial_r+0.5*full_r) if p.tp1_taken else full_r
                trades.append({"symbol":sym,"entry_time":str(p.entry_time),"exit_time":str(ts),
                               "entry_variant":entry_variant,"exit_variant":exit_variant,
                               "reason":p.pending_reason,"gross_r":blend,"net_pnl":pnl-cc,
                               "bars":p.bars,"tp1":p.tp1_taken})
                to_close.append(sym); continue

            if h>=p.entry+p.risk_per_share:p.armed=True

            # realistic stop
            if l<=p.stop:
                fill=o if o<p.stop else p.stop
                qty=p.runner_shares if p.tp1_taken else p.shares
                pnl=(fill-p.entry)*qty
                cc=cost_dollars(fill*qty)
                realized+=pnl-cc; equity+=pnl-cc
                rr=(fill-p.entry)/p.risk_per_share
                blend=(0.5*p.partial_r+0.5*rr) if p.tp1_taken else rr
                trades.append({"symbol":sym,"entry_time":str(p.entry_time),"exit_time":str(ts),
                               "entry_variant":entry_variant,"exit_variant":exit_variant,
                               "reason":"STOP","gross_r":blend,"net_pnl":pnl-cc,
                               "bars":p.bars,"tp1":p.tp1_taken})
                to_close.append(sym); continue

            # TP1 half
            if not p.tp1_taken and h>=p.tp1:
                fill=o if o>p.tp1 else p.tp1
                qty=max(1,p.shares//2)
                pnl=(fill-p.entry)*qty
                cc=cost_dollars(fill*qty)
                realized+=pnl-cc; equity+=pnl-cc
                p.partial_r=(fill-p.entry)/p.risk_per_share
                p.tp1_taken=True
                p.runner_shares=p.shares-qty
                events.append({"time":str(ts),"symbol":sym,"event":"TP1","price":fill,"shares":qty,"cost":cc})
                # Mode B: no exit evaluation on TP1 bar
                if p.bars>=30:
                    # runner timeout at close
                    qty2=p.runner_shares
                    pnl2=(c-p.entry)*qty2; cc2=cost_dollars(c*qty2)
                    realized+=pnl2-cc2; equity+=pnl2-cc2
                    rr=(c-p.entry)/p.risk_per_share
                    blend=0.5*p.partial_r+0.5*rr
                    trades.append({"symbol":sym,"entry_time":str(p.entry_time),"exit_time":str(ts),
                                   "entry_variant":entry_variant,"exit_variant":exit_variant,
                                   "reason":"TIMEOUT","gross_r":blend,"net_pnl":pnl+pnl2-cc-cc2,
                                   "bars":p.bars,"tp1":True})
                    to_close.append(sym)
                continue

            # exits
            if not p.tp1_taken:
                if p.armed and bool(row["scanner_exit"]):
                    p.pending_exit=True;p.pending_reason="PP_PRE_TP1"
            else:
                fire=False
                if exit_variant=="current":
                    fire=p.armed and bool(row["scanner_exit"])
                elif exit_variant=="4h_big_red":
                    fire=bool(row["big_red"])
                elif exit_variant=="daily_big_red":
                    fire=bool(row["daily_big_red_evt"])
                elif exit_variant=="4h_small_red_clean":
                    fire=bool(row["small_red_clean"])
                if fire:
                    p.pending_exit=True;p.pending_reason=exit_variant

            # timeout
            if p.bars>=30:
                qty=p.runner_shares if p.tp1_taken else p.shares
                pnl=(c-p.entry)*qty; cc=cost_dollars(c*qty)
                realized+=pnl-cc; equity+=pnl-cc
                rr=(c-p.entry)/p.risk_per_share
                blend=(0.5*p.partial_r+0.5*rr) if p.tp1_taken else rr
                trades.append({"symbol":sym,"entry_time":str(p.entry_time),"exit_time":str(ts),
                               "entry_variant":entry_variant,"exit_variant":exit_variant,
                               "reason":"TIMEOUT","gross_r":blend,"net_pnl":pnl-cc,
                               "bars":p.bars,"tp1":p.tp1_taken})
                to_close.append(sym)

        for sym in to_close:positions.pop(sym,None)

        # 3) After close, rank new signals and schedule next-bar fills.
        batch=candidates.get(ts,[])
        if batch:
            # busy symbols excluded
            batch=[x for x in batch if x[0] not in positions and not any(pe["sym"]==x[0] for pe in pending_entries)]
            batch.sort(key=lambda z:z[2],reverse=True)
            free=max(0,MAX_OPEN-len(positions)-len(pending_entries))
            # heat cap effectively constrains adds as well
            heat=sum(p.planned_risk for p in positions.values())/max(equity,1.0)
            heat_slots=max(0,int(math.floor((MAX_HEAT-heat)/RISK_FRAC+1e-9)))
            take=min(free,heat_slots,len(batch))
            for sym,i,rank in batch[:take]:
                df=frames[sym]
                if i+1>=len(df):continue
                pending_entries.append({"sym":sym,"entry_i":i+1,
                                        "stop":float(df["qf_stop"].iloc[i]),
                                        "tp1":float(df["qf_tp1"].iloc[i]),
                                        "rank":rank})

    # mark remaining positions at final available close; do not call them closed trades
    open_mark=0.0
    for sym,p in positions.items():
        df=frames[sym]
        last=float(df["Close"].iloc[-1])
        qty=p.runner_shares if p.tp1_taken else p.shares
        open_mark+=(last-p.entry)*qty
    ending=equity+open_mark

    tdf=pd.DataFrame(trades)
    if tdf.empty:
        return {"entry_variant":entry_variant,"exit_variant":exit_variant,"n":0},tdf
    r=tdf.gross_r.astype(float)
    wins=r[r>0]; losses=r[r<=0]
    pf=float(wins.sum()/abs(losses.sum())) if len(losses) and losses.sum()!=0 else None
    return {
        "entry_variant":entry_variant,"exit_variant":exit_variant,
        "n":int(len(tdf)),"gross_expectancy_r":round(float(r.mean()),4),
        "median_r":round(float(r.median()),4),"win_pct":round(float((r>0).mean()*100),2),
        "profit_factor":round(pf,3) if pf is not None and np.isfinite(pf) else None,
        "realized_pnl":round(float(realized),2),"ending_equity_marked":round(float(ending),2),
        "return_pct_marked":round(float((ending/INITIAL_EQUITY-1)*100),2),
        "open_positions":int(len(positions)),
        "avg_bars":round(float(tdf.bars.mean()),2),
        "tp1_rate_pct":round(float(tdf.tp1.mean()*100),2),
    },tdf

def main():
    out=Path("hema_qf_portfolio");out.mkdir(exist_ok=True)
    spy_i=regular_1h(fetch_symbol("SPY","1h","729d"))
    spy_h4=resample_closed_4h(spy_i,"SPY")
    frames={}
    for k,sym in enumerate(SYMBOLS,1):
        print(f"[{k}/{len(SYMBOLS)}] {sym}")
        df=prepare_symbol(sym,spy_h4)
        if df is not None:frames[sym]=df
    print("frames",len(frames))

    summaries=[]; alltr=[]
    for ev in ENTRY_VARIANTS:
        for xv in EXIT_VARIANTS:
            print("SIM",ev,xv)
            s,t=simulate(ev,xv,frames)
            summaries.append(s)
            if not t.empty:alltr.append(t)
    sdf=pd.DataFrame(summaries).sort_values(["entry_variant","exit_variant"])
    tdf=pd.concat(alltr,ignore_index=True) if alltr else pd.DataFrame()
    sdf.to_csv(out/"summary.csv",index=False)
    tdf.to_csv(out/"trades.csv",index=False)

    baseline=next((x for x in summaries if x["entry_variant"]=="qf_baseline" and x["exit_variant"]=="current"),None)
    for x in summaries:
        if baseline and x.get("n",0):
            x["delta_expectancy_r_vs_baseline"]=round(x["gross_expectancy_r"]-baseline["gross_expectancy_r"],4)
            x["delta_return_pp_vs_baseline"]=round(x["return_pct_marked"]-baseline["return_pct_marked"],2)
    payload={"data_note":"30-symbol recent-history structural-core surrogate; NOT canonical V5.4 baseline",
             "symbols":list(frames.keys()),"baseline":baseline,
             "results":sorted(summaries,key=lambda z:z.get("gross_expectancy_r",-999),reverse=True)}
    (out/"results.json").write_text(json.dumps(payload,indent=2))
    print("QF_HEMA_PORTFOLIO_START")
    print(json.dumps(payload,indent=2))
    print("QF_HEMA_PORTFOLIO_END")

if __name__=="__main__":
    main()
