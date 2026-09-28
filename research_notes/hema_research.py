#!/usr/bin/env python3
"""
HEMA 20/40 research harness for Quality Flow.
Research-only: does not modify live scanner logic.

Tests:
1) Exact AlgoAlpha HEMA 20/40 big-cross and small-retest signals.
2) Clean/strict retest variants that remove the original script's persistent-zone quirks.
3) Signal event studies on 1H / 4H / Daily / Weekly.
4) Standalone long trade pairings using HEMA entry/exit signals.
5) Quality-Flow-style 4H structural entry events with HEMA regime overlays.
6) Mode-B-like runner-exit comparison: current scanner EXIT vs HEMA red signals.

Execution uses next-bar opens for actionable signals and never acts on the same
bar that generated a signal.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from scanner_rules import resample_closed_4h, bar_close_at

SYMBOLS = [
    "NVDA","SMCI","IREN","PLTR","TSLA","AVGO","MSFT","AMD","ARM","ANET",
    "MU","RKLB","ASTS","SOFI","HOOD","IONQ","CRWD","PANW","ORCL","GOOGL",
    "AMZN","META","QQQ","SPY","IWM","SMH","BBAI","SOUN","APLD","ONDS",
]

HORIZONS = [1,3,5,10,20]

def ema(s: pd.Series, length: int) -> pd.Series:
    return s.astype(float).ewm(span=int(length), adjust=False, min_periods=1).mean()

def rma(s: pd.Series, length: int) -> pd.Series:
    return s.astype(float).ewm(alpha=1.0/int(length), adjust=False, min_periods=1).mean()

def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    c = df["Close"].astype(float)
    pc = c.shift(1)
    tr = pd.concat([
        df["High"].astype(float)-df["Low"].astype(float),
        (df["High"].astype(float)-pc).abs(),
        (df["Low"].astype(float)-pc).abs(),
    ], axis=1).max(axis=1)
    return rma(tr, length)

def adx(df: pd.DataFrame, length: int = 14) -> pd.Series:
    h = df["High"].astype(float)
    l = df["Low"].astype(float)
    up = h.diff()
    dn = -l.diff()
    plus = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    a = atr(df, length)
    pdi = 100 * rma(plus, length) / a.replace(0, np.nan)
    mdi = 100 * rma(minus, length) / a.replace(0, np.nan)
    dx = 100 * (pdi-mdi).abs() / (pdi+mdi).replace(0, np.nan)
    return rma(dx, length)

def hema(src: pd.Series, length: int) -> pd.Series:
    half = max(1, round(length/2))
    root = max(1, round(math.sqrt(length)))
    ehalf = ema(src, half)
    efull = ema(src, length)
    return ema(2*ehalf-efull, root)

def add_hema(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ATR14"] = atr(out, 14)
    out["HEMA20"] = hema(out["Close"], 20)
    out["HEMA40"] = hema(out["Close"], 40)
    out["big_green"] = (out["HEMA20"] > out["HEMA40"]) & (out["HEMA20"].shift(1) <= out["HEMA40"].shift(1))
    out["big_red"] = (out["HEMA20"] < out["HEMA40"]) & (out["HEMA20"].shift(1) >= out["HEMA40"].shift(1))

    exact_bull = np.zeros(len(out), dtype=bool)
    exact_bear = np.zeros(len(out), dtype=bool)
    clean_bull = np.zeros(len(out), dtype=bool)
    clean_bear = np.zeros(len(out), dtype=bool)
    strict_bull = np.zeros(len(out), dtype=bool)
    strict_bear = np.zeros(len(out), dtype=bool)

    bull_zone = None
    bear_zone = None
    clean_bull_zone = None
    clean_bear_zone = None
    clean_bull_used = False
    clean_bear_used = False

    vals = out[["Open","High","Low","Close","ATR14","big_green","big_red"]].to_dict("records")
    for i, r in enumerate(vals):
        if any(pd.isna(r[k]) for k in ("Open","High","Low","Close","ATR14")):
            continue
        vola = float(r["ATR14"]) / 2.0
        if bool(r["big_green"]):
            # Exact original: newest bull zone replaces the active .first() zone.
            bull_zone = (float(r["Low"]), float(r["Low"])+vola, i)
            # Clean variant: opposite side invalidates and only first later retest counts.
            clean_bull_zone = (float(r["Low"]), float(r["Low"])+vola, i)
            clean_bull_used = False
            clean_bear_zone = None
            clean_bear_used = False
        elif bool(r["big_red"]):
            bear_zone = (float(r["High"])-vola, float(r["High"]), i)
            clean_bear_zone = (float(r["High"])-vola, float(r["High"]), i)
            clean_bear_used = False
            clean_bull_zone = None
            clean_bull_used = False

        if bull_zone is not None:
            lo, top, cross_i = bull_zone
            if (float(r["Low"]) < top and float(r["High"]) > top and
                float(r["Open"]) > top and float(r["Close"]) > top):
                exact_bull[i] = True

        if bear_zone is not None:
            lower, hi, cross_i = bear_zone
            if (float(r["High"]) > lower and float(r["Low"]) < lower and
                float(r["Open"]) < lower and float(r["Close"]) < lower):
                exact_bear[i] = True

        if clean_bull_zone is not None and not clean_bull_used:
            lo, top, cross_i = clean_bull_zone
            if i > cross_i and (float(r["Low"]) < top and float(r["High"]) > top and
                                float(r["Open"]) > top and float(r["Close"]) > top):
                clean_bull[i] = True
                if float(r["Low"]) >= lo:
                    strict_bull[i] = True
                clean_bull_used = True

        if clean_bear_zone is not None and not clean_bear_used:
            lower, hi, cross_i = clean_bear_zone
            if i > cross_i and (float(r["High"]) > lower and float(r["Low"]) < lower and
                                float(r["Open"]) < lower and float(r["Close"]) < lower):
                clean_bear[i] = True
                if float(r["High"]) <= hi:
                    strict_bear[i] = True
                clean_bear_used = True

    out["small_green_exact"] = exact_bull
    out["small_red_exact"] = exact_bear
    out["small_green_clean"] = clean_bull
    out["small_red_clean"] = clean_bear
    out["small_green_strict"] = strict_bull
    out["small_red_strict"] = strict_bear
    out["bull_regime"] = out["HEMA20"] > out["HEMA40"]
    out["bear_regime"] = out["HEMA20"] < out["HEMA40"]
    return out

def _norm_yf(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    x = df.copy()
    if isinstance(x.columns, pd.MultiIndex):
        # Single-symbol yfinance sometimes leaves ticker as second level.
        if symbol in x.columns.get_level_values(-1):
            try:
                x = x.xs(symbol, level=-1, axis=1)
            except Exception:
                x.columns = [c[0] for c in x.columns]
        else:
            x.columns = [c[0] if isinstance(c, tuple) else c for c in x.columns]
    needed = ["Open","High","Low","Close","Volume"]
    if not all(c in x.columns for c in needed):
        return pd.DataFrame()
    x = x[needed].dropna(subset=["Open","High","Low","Close"]).copy()
    if not isinstance(x.index, pd.DatetimeIndex):
        x.index = pd.to_datetime(x.index)
    return x.sort_index()

def fetch_symbol(symbol: str, interval: str, period: str, tries: int = 3) -> pd.DataFrame:
    last = None
    for k in range(tries):
        try:
            df = yf.download(symbol, interval=interval, period=period, auto_adjust=True,
                             progress=False, threads=False, prepost=False)
            x = _norm_yf(df, symbol)
            if not x.empty:
                return x
            last = "empty"
        except Exception as e:
            last = repr(e)
        time.sleep(1.5*(k+1))
    print(f"FETCH_FAIL {symbol} {interval} {period}: {last}")
    return pd.DataFrame()

def regular_1h(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    x = df.copy()
    idx = x.index
    if idx.tz is not None:
        local = idx.tz_convert("America/New_York")
    else:
        local = idx.tz_localize("America/New_York")
        x.index = local
    mins = local.hour*60 + local.minute
    return x[(mins >= 570) & (mins < 960)].copy()

def daily_from_h4(h4: pd.DataFrame) -> tuple[pd.DataFrame, dict[pd.Timestamp,pd.Timestamp]]:
    if h4.empty:
        return pd.DataFrame(), {}
    x = h4.copy()
    idx = x.index.tz_convert("America/New_York") if x.index.tz is not None else x.index.tz_localize("America/New_York")
    keys = pd.Index(idx.date)
    rows=[]
    mapping={}
    for d in pd.unique(keys):
        g = x[keys==d]
        ts = g.index[-1]
        rows.append((ts,float(g["Open"].iloc[0]),float(g["High"].max()),float(g["Low"].min()),float(g["Close"].iloc[-1]),float(g["Volume"].sum())))
        mapping[ts]=ts
    out = pd.DataFrame(rows, columns=["idx","Open","High","Low","Close","Volume"]).set_index("idx")
    return out, mapping

def weekly_from_h4(h4: pd.DataFrame) -> pd.DataFrame:
    if h4.empty:
        return pd.DataFrame()
    x = h4.copy()
    idx = x.index.tz_convert("America/New_York") if x.index.tz is not None else x.index.tz_localize("America/New_York")
    keys = [f"{t.isocalendar().year}-{t.isocalendar().week:02d}" for t in idx]
    rows=[]
    for key in pd.unique(keys):
        mask = np.array(keys)==key
        g=x[mask]
        ts=g.index[-1]
        rows.append((ts,float(g["Open"].iloc[0]),float(g["High"].max()),float(g["Low"].min()),float(g["Close"].iloc[-1]),float(g["Volume"].sum())))
    return pd.DataFrame(rows, columns=["idx","Open","High","Low","Close","Volume"]).set_index("idx")

def event_study(df: pd.DataFrame, signal_col: str, side: int, symbol: str, timeframe: str, sample: str="all") -> list[dict]:
    rows=[]
    idxs=np.flatnonzero(df[signal_col].fillna(False).to_numpy())
    for i in idxs:
        if i+1 >= len(df):
            continue
        entry=float(df["Open"].iloc[i+1])
        if not np.isfinite(entry) or entry<=0:
            continue
        rec={"symbol":symbol,"timeframe":timeframe,"signal":signal_col,"side":side,"signal_time":str(df.index[i]),"entry_time":str(df.index[i+1]),"entry":entry,"sample":sample}
        for h in HORIZONS:
            j=i+1+h
            if j < len(df):
                r=(float(df["Close"].iloc[j])/entry-1.0)*100.0*side
                rec[f"fwd_{h}_bar_pct"]=r
        j2=min(len(df)-1,i+1+10)
        w=df.iloc[i+1:j2+1]
        if len(w):
            if side==1:
                rec["mfe_10_pct"]=(float(w["High"].max())/entry-1)*100
                rec["mae_10_pct"]=(float(w["Low"].min())/entry-1)*100
            else:
                rec["mfe_10_pct"]=(1-float(w["Low"].min())/entry)*100
                rec["mae_10_pct"]=(1-float(w["High"].max())/entry)*100
        rows.append(rec)
    return rows

def summarize_events(events: pd.DataFrame) -> list[dict]:
    if events.empty:
        return []
    out=[]
    group_cols=["timeframe","signal","sample"]
    for keys,g in events.groupby(group_cols, dropna=False):
        rec={"timeframe":keys[0],"signal":keys[1],"sample":keys[2],"n":int(len(g))}
        for h in HORIZONS:
            c=f"fwd_{h}_bar_pct"
            vals=g[c].dropna() if c in g else pd.Series(dtype=float)
            if len(vals):
                rec[f"mean_{h}b_pct"]=round(float(vals.mean()),4)
                rec[f"median_{h}b_pct"]=round(float(vals.median()),4)
                rec[f"hit_{h}b_pct"]=round(float((vals>0).mean()*100),2)
        for c in ["mfe_10_pct","mae_10_pct"]:
            vals=g[c].dropna() if c in g else pd.Series(dtype=float)
            if len(vals): rec[f"mean_{c}"]=round(float(vals.mean()),4)
        out.append(rec)
    return out

def pair_trades(df: pd.DataFrame, entry_col: str, exit_col: str, symbol: str, timeframe: str, cost_bps: float=50.0) -> list[dict]:
    trades=[]
    i=0
    while i < len(df)-1:
        if bool(df[entry_col].iloc[i]):
            ei=i+1
            entry=float(df["Open"].iloc[ei])
            j=ei
            while j < len(df)-1 and not bool(df[exit_col].iloc[j]):
                j+=1
            if j>=len(df)-1:
                break
            xi=j+1
            exit_px=float(df["Open"].iloc[xi])
            gross=(exit_px/entry-1)*100
            net=gross-cost_bps/100.0
            trades.append({"symbol":symbol,"timeframe":timeframe,"entry_signal":entry_col,"exit_signal":exit_col,
                           "entry_time":str(df.index[ei]),"exit_time":str(df.index[xi]),"entry":entry,"exit":exit_px,
                           "gross_pct":gross,"net_pct":net,"bars":int(xi-ei)})
            i=xi+1
        else:
            i+=1
    return trades

def summarize_trades(trades: pd.DataFrame) -> list[dict]:
    if trades.empty: return []
    out=[]
    for keys,g in trades.groupby(["timeframe","entry_signal","exit_signal"]):
        r=g["net_pct"].astype(float)
        wins=r[r>0]; losses=r[r<=0]
        pf=float(wins.sum()/abs(losses.sum())) if len(losses) and losses.sum()!=0 else None
        out.append({
            "timeframe":keys[0],"entry_signal":keys[1],"exit_signal":keys[2],"n":int(len(g)),
            "avg_net_pct":round(float(r.mean()),4),"median_net_pct":round(float(r.median()),4),
            "win_pct":round(float((r>0).mean()*100),2),
            "profit_factor":round(pf,3) if pf is not None and np.isfinite(pf) else None,
            "avg_bars":round(float(g["bars"].mean()),2),
        })
    return out

def add_qf_core(df: pd.DataFrame) -> pd.DataFrame:
    x=df.copy()
    c=x["Close"].astype(float)
    x["EMA9"]=ema(c,9); x["EMA21"]=ema(c,21); x["EMA55"]=ema(c,55); x["EMA200"]=ema(c,200)
    x["ADX14"]=adx(x,14); x["QF_ATR"]=atr(x,14)
    if "SessionVWAP" in x:
        x["QVWAP"]=x["SessionVWAP"]
    else:
        typ=(x["High"]+x["Low"]+x["Close"])/3
        vol=x["Volume"].replace(0,np.nan)
        x["QVWAP"]=(typ*vol).rolling(50).sum()/vol.rolling(50).sum()
    trend=c>x["EMA200"]
    ema_bull=x["EMA21"]>x["EMA55"]
    fresh=(x["EMA21"]>x["EMA55"]) & (x["EMA21"].shift(1)<=x["EMA55"].shift(1)) & trend
    pct=(c/x["EMA21"]-1).abs()*100
    pull=trend & ema_bull & (c>=x["EMA21"]) & (pct<=2.5) & (x["ADX14"]>=20)
    above_vwap=c>x["QVWAP"]
    zone_low=x["EMA21"]-x["QF_ATR"]*0.45
    zone_high=x["EMA21"]+x["QF_ATR"]*0.45
    in_zone=(c>=zone_low)&(c<=zone_high)
    safe=trend & ema_bull & (c>=x["EMA21"]) & above_vwap
    stop=(zone_low-x["QF_ATR"]*0.65).clip(lower=0)
    tp1=zone_high+x["QF_ATR"]*2.50
    rr=(tp1-c)/(c-stop).replace(0,np.nan)
    candidate=safe & in_zone & (fresh|pull) & (x["ADX14"]>=20) & (rr>=2.0)
    x["qf_core"]=candidate
    x["qf_event"]=candidate & ~candidate.shift(1).fillna(False)
    x["qf_stop"]=stop; x["qf_tp1"]=tp1
    x["scanner_exit"]=(c<x["EMA55"]) | ((x["EMA21"]<x["EMA55"]) & (x["EMA21"].shift(1)>=x["EMA55"].shift(1)))
    return x

def map_htf_signal_to_h4(h4: pd.DataFrame, htf: pd.DataFrame, col: str) -> pd.Series:
    s=pd.Series(False,index=h4.index)
    if htf.empty or col not in htf: return s
    for ts,val in htf[col].fillna(False).items():
        if bool(val) and ts in s.index:
            s.loc[ts]=True
    return s

def qf_overlay_events(h4: pd.DataFrame, daily_h: pd.DataFrame, weekly_h: pd.DataFrame, symbol: str) -> list[dict]:
    rows=[]
    base=np.flatnonzero(h4["qf_event"].fillna(False).to_numpy())
    daily_reg=pd.Series(False,index=h4.index)
    weekly_reg=pd.Series(False,index=h4.index)
    # Regime is carried forward from the last completed higher-timeframe bar.
    dreg=daily_h["bull_regime"] if not daily_h.empty else pd.Series(dtype=bool)
    wreg=weekly_h["bull_regime"] if not weekly_h.empty else pd.Series(dtype=bool)
    if len(dreg):
        tmp=pd.Series(dreg.to_numpy(),index=daily_h.index).reindex(h4.index,method="ffill").fillna(False)
        daily_reg=tmp.astype(bool)
    if len(wreg):
        tmp=pd.Series(wreg.to_numpy(),index=weekly_h.index).reindex(h4.index,method="ffill").fillna(False)
        weekly_reg=tmp.astype(bool)
    variants={
        "qf_baseline": pd.Series(True,index=h4.index),
        "qf_plus_4h_bull": h4["bull_regime"].fillna(False),
        "qf_plus_daily_bull": daily_reg,
        "qf_plus_weekly_bull": weekly_reg,
        "qf_plus_daily_weekly_bull": daily_reg & weekly_reg,
        "qf_plus_recent_small_green_exact": h4["small_green_exact"].rolling(4,min_periods=1).max().fillna(0).astype(bool),
        "qf_plus_recent_small_green_clean": h4["small_green_clean"].rolling(4,min_periods=1).max().fillna(0).astype(bool),
    }
    for name,mask in variants.items():
        for i in base:
            if not bool(mask.iloc[i]) or i+1>=len(h4): continue
            entry=float(h4["Open"].iloc[i+1])
            rec={"symbol":symbol,"variant":name,"signal_time":str(h4.index[i]),"entry_time":str(h4.index[i+1]),"entry":entry}
            for n in [1,3,5,10]:
                j=i+1+n
                if j<len(h4):
                    rec[f"fwd_{n}_bar_pct"]=(float(h4["Close"].iloc[j])/entry-1)*100
            rows.append(rec)
    return rows

def summarize_qf_overlay(df: pd.DataFrame) -> list[dict]:
    if df.empty:return []
    out=[]
    for name,g in df.groupby("variant"):
        rec={"variant":name,"n":int(len(g))}
        for n in [1,3,5,10]:
            c=f"fwd_{n}_bar_pct"; v=g[c].dropna()
            if len(v):
                rec[f"mean_{n}b_pct"]=round(float(v.mean()),4)
                rec[f"median_{n}b_pct"]=round(float(v.median()),4)
                rec[f"hit_{n}b_pct"]=round(float((v>0).mean()*100),2)
        out.append(rec)
    return out

@dataclass
class SimResult:
    symbol:str; variant:str; entry_time:str; exit_time:str; exit_reason:str
    blended_r:float; tp1_taken:bool; bars:int

def simulate_qf_trade(h4: pd.DataFrame, sig_i: int, variant: str, daily_h: pd.DataFrame, weekly_h: pd.DataFrame) -> SimResult|None:
    if sig_i+1>=len(h4): return None
    ei=sig_i+1
    entry=float(h4["Open"].iloc[ei]); stop=float(h4["qf_stop"].iloc[sig_i]); tp1=float(h4["qf_tp1"].iloc[sig_i])
    if not np.isfinite(entry+stop+tp1) or entry<=stop: return None
    risk=entry-stop
    if risk<=0:return None

    # Map HTF signal flags onto 4H closes.
    daily_big=map_htf_signal_to_h4(h4,daily_h,"big_red")
    daily_small=map_htf_signal_to_h4(h4,daily_h,"small_red_exact")
    daily_small_clean=map_htf_signal_to_h4(h4,daily_h,"small_red_clean")
    weekly_big=map_htf_signal_to_h4(h4,weekly_h,"big_red")
    weekly_small=map_htf_signal_to_h4(h4,weekly_h,"small_red_exact")
    weekly_small_clean=map_htf_signal_to_h4(h4,weekly_h,"small_red_clean")
    exit_series={
        "current": h4["scanner_exit"].fillna(False),
        "4h_big_red": h4["big_red"].fillna(False),
        "4h_small_red_exact": h4["small_red_exact"].fillna(False),
        "4h_small_red_clean": h4["small_red_clean"].fillna(False),
        "daily_big_red": daily_big,
        "daily_small_red_exact": daily_small,
        "daily_small_red_clean": daily_small_clean,
        "weekly_big_red": weekly_big,
        "weekly_small_red_exact": weekly_small,
        "weekly_small_red_clean": weekly_small_clean,
    }[variant]

    tp1_taken=False
    partial_r=0.0
    armed=False
    pending=False
    pending_reason=""
    max_i=min(len(h4)-1,ei+29)
    for j in range(ei,max_i+1):
        row=h4.iloc[j]
        o,h,l,c=map(float,[row["Open"],row["High"],row["Low"],row["Close"]])
        # pending exit fills at this bar's open before other evaluations
        if pending:
            rr=(o-entry)/risk
            blended=(0.5*partial_r+0.5*rr) if tp1_taken else rr
            return SimResult("",variant,str(h4.index[ei]),str(h4.index[j]),pending_reason,blended,tp1_taken,j-ei+1)

        if h>=entry+risk: armed=True

        # realistic stop: gaps through stop fill at open; otherwise stop
        if l<=stop:
            fill=o if o<stop else stop
            rr=(fill-entry)/risk
            blended=(0.5*partial_r+0.5*rr) if tp1_taken else rr
            return SimResult("",variant,str(h4.index[ei]),str(h4.index[j]),"STOP",blended,tp1_taken,j-ei+1)

        if not tp1_taken and h>=tp1:
            fill=o if o>tp1 else tp1
            partial_r=(fill-entry)/risk
            tp1_taken=True
            # no exit evaluation on TP1 bar, matching Mode B ordering
            if j==max_i:
                rr=(c-entry)/risk
                return SimResult("",variant,str(h4.index[ei]),str(h4.index[j]),"TIMEOUT",0.5*partial_r+0.5*rr,True,j-ei+1)
            continue

        if not tp1_taken:
            # Keep current pre-TP1 Profit Protect behavior identical for all runner tests.
            if armed and bool(h4["scanner_exit"].iloc[j]):
                pending=True; pending_reason="PP_PRE_TP1"
        else:
            if variant=="current":
                if armed and bool(h4["scanner_exit"].iloc[j]):
                    pending=True; pending_reason="CURRENT_RUNNER_EXIT"
            else:
                if bool(exit_series.iloc[j]):
                    pending=True; pending_reason=f"HEMA_{variant}"

        if j==max_i:
            rr=(c-entry)/risk
            blended=(0.5*partial_r+0.5*rr) if tp1_taken else rr
            return SimResult("",variant,str(h4.index[ei]),str(h4.index[j]),"TIMEOUT",blended,tp1_taken,j-ei+1)
    return None

def run_runner_exit_tests(h4: pd.DataFrame,daily_h:pd.DataFrame,weekly_h:pd.DataFrame,symbol:str)->list[dict]:
    out=[]
    sigs=np.flatnonzero(h4["qf_event"].fillna(False).to_numpy())
    variants=["current","4h_big_red","4h_small_red_exact","4h_small_red_clean","daily_big_red",
              "daily_small_red_exact","daily_small_red_clean","weekly_big_red","weekly_small_red_exact","weekly_small_red_clean"]
    for i in sigs:
        for v in variants:
            r=simulate_qf_trade(h4,i,v,daily_h,weekly_h)
            if r:
                d=r.__dict__.copy(); d["symbol"]=symbol; out.append(d)
    return out

def summarize_runner(df:pd.DataFrame)->list[dict]:
    if df.empty:return []
    out=[]
    for v,g in df.groupby("variant"):
        r=g["blended_r"].astype(float)
        wins=r[r>0]; losses=r[r<=0]
        pf=float(wins.sum()/abs(losses.sum())) if len(losses) and losses.sum()!=0 else None
        out.append({"variant":v,"n":int(len(g)),"expectancy_r":round(float(r.mean()),4),
                    "median_r":round(float(r.median()),4),"win_pct":round(float((r>0).mean()*100),2),
                    "profit_factor":round(pf,3) if pf is not None and np.isfinite(pf) else None,
                    "tp1_rate_pct":round(float(g["tp1_taken"].mean()*100),2),
                    "avg_bars":round(float(g["bars"].mean()),2)})
    return sorted(out,key=lambda x:x["expectancy_r"],reverse=True)

def slice_2022(df:pd.DataFrame)->pd.DataFrame:
    if df.empty:return df
    idx=pd.DatetimeIndex(df.index)
    return df[(idx.year==2022)].copy()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",default="hema_results")
    args=ap.parse_args()
    outdir=Path(args.output_dir); outdir.mkdir(parents=True,exist_ok=True)

    all_events=[]; all_trades=[]; qf_events=[]; runner_rows=[]; coverage=[]
    for n,sym in enumerate(SYMBOLS,1):
        print(f"[{n}/{len(SYMBOLS)}] {sym}")
        intr=fetch_symbol(sym,"1h","729d")
        daily=fetch_symbol(sym,"1d","10y")
        coverage.append({"symbol":sym,"intraday_rows":int(len(intr)),"daily_rows":int(len(daily)),
                         "intraday_start":str(intr.index[0]) if len(intr) else None,
                         "intraday_end":str(intr.index[-1]) if len(intr) else None,
                         "daily_start":str(daily.index[0]) if len(daily) else None,
                         "daily_end":str(daily.index[-1]) if len(daily) else None})
        if not intr.empty:
            intr=regular_1h(intr)
            h1=add_hema(intr)
            try:
                h4raw=resample_closed_4h(intr,sym)
            except Exception as e:
                print("RESAMPLE_FAIL",sym,e); h4raw=pd.DataFrame()
            if not h4raw.empty:
                h4=add_qf_core(add_hema(h4raw))
                d4,_=daily_from_h4(h4raw); d4=add_hema(d4) if not d4.empty else d4
                w4=weekly_from_h4(h4raw); w4=add_hema(w4) if not w4.empty else w4
            else:
                h4=d4=w4=pd.DataFrame()

            for tf,frame in [("1H",h1),("4H",h4)]:
                if frame.empty:continue
                for col,side in [("big_green",1),("small_green_exact",1),("small_green_clean",1),("small_green_strict",1),
                                 ("big_red",-1),("small_red_exact",-1),("small_red_clean",-1),("small_red_strict",-1)]:
                    all_events.extend(event_study(frame,col,side,sym,tf,"recent"))
                for ec,xc in [("big_green","big_red"),("small_green_exact","big_red"),
                              ("small_green_exact","small_red_exact"),("small_green_clean","big_red"),
                              ("small_green_clean","small_red_clean")]:
                    all_trades.extend(pair_trades(frame,ec,xc,sym,tf))
            if not h4.empty and not d4.empty and not w4.empty:
                qf_events.extend(qf_overlay_events(h4,d4,w4,sym))
                runner_rows.extend(run_runner_exit_tests(h4,d4,w4,sym))

        if not daily.empty:
            d=add_hema(daily)
            # Weekly from daily OHLC.
            tmp=daily.copy()
            idx=tmp.index
            keys=[f"{t.isocalendar().year}-{t.isocalendar().week:02d}" for t in idx]
            rows=[]
            for key in pd.unique(keys):
                g=tmp[np.array(keys)==key]
                ts=g.index[-1]
                rows.append((ts,float(g["Open"].iloc[0]),float(g["High"].max()),float(g["Low"].min()),float(g["Close"].iloc[-1]),float(g["Volume"].sum())))
            w=pd.DataFrame(rows,columns=["idx","Open","High","Low","Close","Volume"]).set_index("idx")
            w=add_hema(w)
            for tf,frame in [("1D",d),("1W",w)]:
                for col,side in [("big_green",1),("small_green_exact",1),("small_green_clean",1),("small_green_strict",1),
                                 ("big_red",-1),("small_red_exact",-1),("small_red_clean",-1),("small_red_strict",-1)]:
                    all_events.extend(event_study(frame,col,side,sym,tf,"all"))
                    yr=slice_2022(frame)
                    if len(yr)>45:
                        all_events.extend(event_study(yr,col,side,sym,tf,"2022"))
                for ec,xc in [("big_green","big_red"),("small_green_exact","big_red"),
                              ("small_green_exact","small_red_exact"),("small_green_clean","big_red"),
                              ("small_green_clean","small_red_clean")]:
                    all_trades.extend(pair_trades(frame,ec,xc,sym,tf))

    events_df=pd.DataFrame(all_events)
    trades_df=pd.DataFrame(all_trades)
    qf_df=pd.DataFrame(qf_events)
    runner_df=pd.DataFrame(runner_rows)
    cov_df=pd.DataFrame(coverage)

    event_summary=summarize_events(events_df)
    trade_summary=summarize_trades(trades_df)
    qf_summary=summarize_qf_overlay(qf_df)
    runner_summary=summarize_runner(runner_df)

    def best_event(tf,sideword):
        sigs=["big_green","small_green_exact","small_green_clean","small_green_strict"] if sideword=="bull" else ["big_red","small_red_exact","small_red_clean","small_red_strict"]
        rows=[r for r in event_summary if r["timeframe"]==tf and r["signal"] in sigs and r["sample"] in ("recent","all") and r.get("n",0)>=10 and "mean_10b_pct" in r]
        return max(rows,key=lambda r:r["mean_10b_pct"]) if rows else None

    headline={
        "generated_at_utc":pd.Timestamp.utcnow().isoformat(),
        "symbols_requested":len(SYMBOLS),
        "symbols_with_intraday":int((cov_df["intraday_rows"]>0).sum()) if len(cov_df) else 0,
        "symbols_with_daily":int((cov_df["daily_rows"]>0).sum()) if len(cov_df) else 0,
        "best_10bar_bull_signal_by_timeframe":{tf:best_event(tf,"bull") for tf in ["1H","4H","1D","1W"]},
        "best_10bar_bear_signal_by_timeframe":{tf:best_event(tf,"bear") for tf in ["1H","4H","1D","1W"]},
        "qf_overlay_summary":qf_summary,
        "runner_exit_summary":runner_summary,
        "notes":[
            "HEMA math and exact small-triangle logic match the Pine source supplied by the user.",
            "Clean retest invalidates the old zone on an opposite crossover and counts only the first later retest.",
            "Strict retest additionally requires the wick to remain inside the crossover ATR/2 box.",
            "All actionable event returns begin at the next bar open; same-bar signal execution is not allowed.",
            "QF overlay uses a reproducible 4H structural-core approximation from the public scanner code, not the missing canonical V5.4 historical engine.",
            "Runner test keeps pre-TP1 current Profit Protect behavior fixed and changes only the post-TP1 runner exit trigger.",
            "Intraday Yahoo history is limited to roughly 729 days; 2022 stress testing is therefore Daily/Weekly only.",
            "Standalone HEMA trade summaries use 50 bps round-trip friction."
        ]
    }

    events_df.to_csv(outdir/"event_detail.csv",index=False)
    trades_df.to_csv(outdir/"standalone_trade_detail.csv",index=False)
    qf_df.to_csv(outdir/"qf_overlay_detail.csv",index=False)
    runner_df.to_csv(outdir/"runner_exit_detail.csv",index=False)
    cov_df.to_csv(outdir/"coverage.csv",index=False)
    (outdir/"event_summary.json").write_text(json.dumps(event_summary,indent=2))
    (outdir/"standalone_summary.json").write_text(json.dumps(trade_summary,indent=2))
    (outdir/"qf_overlay_summary.json").write_text(json.dumps(qf_summary,indent=2))
    (outdir/"runner_exit_summary.json").write_text(json.dumps(runner_summary,indent=2))
    (outdir/"headline.json").write_text(json.dumps(headline,indent=2))

    print("HEMA_SUMMARY_JSON_START")
    print(json.dumps(headline,indent=2))
    print("HEMA_SUMMARY_JSON_END")

if __name__=="__main__":
    main()
