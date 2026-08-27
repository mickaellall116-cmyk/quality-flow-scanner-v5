"""MasterScanner V5.1 API

Standalone FastAPI wrapper that mirrors the Quality Flow Scanner V5.1
classification and Morning Action logic from the public Streamlit app.

Run locally:
    pip install fastapi uvicorn yfinance pandas numpy
    uvicorn masterscanner_api:app --host 0.0.0.0 --port 8000

Endpoints:
    GET /health
    GET /buy-now
    GET /watch-today
    GET /no-new-entry
    GET /scan/{symbol}
    GET /scan?symbols=PLTR,SOFI,MSFT

Deploy this file on Render/Railway/Fly.io (or another Python web host). Once
public, ChatGPT can fetch the JSON endpoints directly.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="MasterScanner V5.1 API", version="5.1-api")

MARKET_SYMBOL = "QQQ"
DEFAULT_WATCHLIST = [
    "NVDA", "SMCI", "APLD", "ONDS", "PLTR", "TSLA", "AVGO", "MSFT", "AMD", "ARM",
    "QQQ", "SPY", "VOO", "SMH", "BTC-USD", "ETH-USD", "SOL-USD",
]
DISCOVERY_THEMES: Dict[str, List[str]] = {
    "AI Infrastructure": ["NVDA","SMCI","APLD","IREN","VRT","ANET","MU","AVGO","AMD","ARM","DELL","HPE","NTAP","WDC","STX","MRVL","CLS","CEG","VST","ETN"],
    "AI Software": ["MSFT","PLTR","SNOW","CRWD","NET","DDOG","NOW","AI","PATH","SOUN","BBAI","GFAI","CRM","ADBE","ORCL"],
    "Space": ["ASTS","RKLB","LUNR","RDW","PL","SPIR","BKSY","SATL","GSAT","IRDM","LMT","NOC","BA","HWM","TDY"],
    "Quantum": ["IONQ","RGTI","QBTS","QUBT","ARQQ","IBM","GOOGL","HON","NVDA","MSFT"],
    "Semiconductors": ["NVDA","AMD","AVGO","ARM","MU","MRVL","TSM","ASML","AMAT","LRCX","KLAC","TER","ON","NXPI","QCOM","INTC","TXN","MCHP","SMH","SOXX"],
    "Crypto / Mining": ["BTC-USD","ETH-USD","SOL-USD","SUI-USD","AVAX-USD","LINK-USD","ONDO-USD","MARA","RIOT","CLSK","IREN","CIFR","HUT","BTDR","COIN","HOOD","MSTR"],
    "Nuclear / Power": ["CEG","VST","NEE","OKLO","SMR","CCJ","UEC","URNM","BWXT","ETN","GEV","PWR","FLR","LEU","DNN"],
    "Cybersecurity": ["CRWD","PANW","NET","ZS","FTNT","S","OKTA","CYBR","TENB","RPD"],
    "High-Beta Growth": ["ONDS","SOFI","HIMS","TSLA","PLTR","ASTS","RKLB","APLD","SMCI","NVTS","BBAI","SOUN","ACHR","JOBY","RIVN","LCID","UPST","AFRM","HOOD","COIN"],
    "ETFs / Market": ["QQQ","SPY","VOO","IWM","DIA","SMH","SOXX","ARKK","XLK","XLF","XLE","XLV"],
}
DEFAULT_THEMES = ["AI Infrastructure","Space","Quantum","Semiconductors","Crypto / Mining","Nuclear / Power","High-Beta Growth"]

FAST_EMA=21; SLOW_EMA=55; TREND_EMA=200; ACCEL_EMA=9
ADX_LEN=14; ATR_LEN=14; ATR_BASE_LEN=50; VOL_BASE_LEN=50; RS_LOOKBACK=20; VWAP_LEN=50
ADX_MIN=18; HOT_ADX=30; ATR_EXPANSION_THRESHOLD=1.03; PULLBACK_NEAR_EMA_PCT=2.5; HOT_EXTENSION_PCT=6.0
STOP_ATR=1.5; TP1_ATR=2.0; BUY_ZONE_ATR_WIDTH=0.45


def unique_keep_order(items: List[str]) -> List[str]:
    out=[]
    for x in items:
        x=x.strip().upper()
        if x and x not in out: out.append(x)
    return out


def build_discovery_universe(selected_themes: List[str]) -> Tuple[List[str], Dict[str,str]]:
    tickers=[]; symbol_themes: Dict[str,List[str]]={}
    for theme in selected_themes:
        for sym in DISCOVERY_THEMES.get(theme, []):
            sym=sym.upper(); tickers.append(sym); symbol_themes.setdefault(sym, []).append(theme)
    tickers=unique_keep_order(tickers)
    label_map={sym:(themes[0] if len(themes)==1 else f"{themes[0]} +{len(themes)-1}") for sym,themes in symbol_themes.items()}
    return tickers,label_map


def download_data(symbol: str, interval: str, period: str) -> pd.DataFrame:
    yf_interval = "1h" if interval.lower()=="4h" else interval
    df = yf.download(symbol, interval=yf_interval, period=period, progress=False, auto_adjust=True, threads=False)
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex): df.columns=[c[0] for c in df.columns]
    df=df.dropna()
    if interval.lower()=="4h":
        is_crypto = symbol.upper().endswith("-USD")
        # Align stock bars to the 09:30 ET session. Crypto remains aligned to midnight.
        offset = None if is_crypto else "9h30min"
        resample_kwargs = {"origin": "start_day", "label": "left", "closed": "left"}
        if offset:
            resample_kwargs["offset"] = offset
        df=df.resample("4h", **resample_kwargs).agg(
            {"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}
        ).dropna()

        # Never classify an actively forming 4-hour candle. For US stocks the
        # second session bar is considered closed at the 16:00 ET market close.
        if not df.empty:
            last_start=df.index[-1]
            now=pd.Timestamp.now(tz=last_start.tz) if last_start.tz is not None else pd.Timestamp.now()
            if is_crypto:
                last_close=last_start+pd.Timedelta(hours=4)
            else:
                session_close=last_start.normalize()+pd.Timedelta(hours=16)
                last_close=min(last_start+pd.Timedelta(hours=4), session_close)
            if now < last_close:
                df=df.iloc[:-1]
    return df


def ema(s,l): return s.ewm(span=l, adjust=False).mean()

def atr(df,l=14):
    h,lw,c=df["High"],df["Low"],df["Close"]; pc=c.shift(1)
    tr=pd.concat([h-lw,(h-pc).abs(),(lw-pc).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/l, adjust=False).mean()

def adx(df,l=14):
    h,lw=df["High"],df["Low"]; plus_raw=h.diff(); minus_raw=-lw.diff()
    plus=np.where((plus_raw>minus_raw)&(plus_raw>0),plus_raw,0.0)
    minus=np.where((minus_raw>plus_raw)&(minus_raw>0),minus_raw,0.0)
    trur=atr(df,l)
    pdi=100*pd.Series(plus,index=df.index).ewm(alpha=1/l,adjust=False).mean()/trur
    mdi=100*pd.Series(minus,index=df.index).ewm(alpha=1/l,adjust=False).mean()/trur
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    return dx.ewm(alpha=1/l,adjust=False).mean()

def rolling_vwap(df,l=50):
    typical=(df["High"]+df["Low"]+df["Close"])/3; vol=df["Volume"].replace(0,np.nan)
    return (typical*vol).rolling(l).sum()/vol.rolling(l).sum()

def safe_pct(a,b): return 0.0 if b==0 or pd.isna(b) else float(((a-b)/b)*100)
def clamp_int(v,low=0,high=100): return int(max(low,min(high,round(v))))
def mode_label_from_scores(a,h,c): return max({"Aggressive":a,"Hybrid":h,"Conservative":c}, key={"Aggressive":a,"Hybrid":h,"Conservative":c}.get)

def add_indicators(df):
    out=df.copy(); close=out["Close"]; volume=out["Volume"]
    out["EMA9"]=ema(close,ACCEL_EMA); out["EMA21"]=ema(close,FAST_EMA); out["EMA55"]=ema(close,SLOW_EMA); out["EMA200"]=ema(close,TREND_EMA)
    out["ATR"]=atr(out,ATR_LEN); out["ATR_BASE"]=out["ATR"].rolling(ATR_BASE_LEN).mean(); out["ADX"]=adx(out,ADX_LEN)
    out["VOL_BASE"]=volume.rolling(VOL_BASE_LEN).mean(); out["VWAP"]=rolling_vwap(out,VWAP_LEN)
    return out


def get_market_regime(interval:str, period:str)->Dict:
    try:
        df=download_data(MARKET_SYMBOL,interval,period)
        if df.empty or len(df)<TREND_EMA+5: return {"regime":"UNKNOWN","risk_on":True,"score":50}
        df=add_indicators(df); last=df.iloc[-1]; prev=df.iloc[-2]; score=0
        if last["Close"]>last["EMA200"]: score+=35
        if last["EMA21"]>last["EMA55"]: score+=35
        if last["EMA21"]>prev["EMA21"]: score+=15
        if last["Close"]>last["EMA21"]: score+=15
        regime="RISK-ON" if score>=75 else "CAUTIOUS" if score>=50 else "RISK-OFF"
        return {"regime":regime,"risk_on":score>=50,"score":int(score)}
    except Exception:
        return {"regime":"UNKNOWN","risk_on":True,"score":50}


def classify_symbol(symbol, theme, df, market_df, market_regime, timeframe):
    if df.empty or len(df)<max(TREND_EMA,ATR_BASE_LEN,VOL_BASE_LEN,VWAP_LEN)+5: return None
    df=add_indicators(df); last=df.iloc[-1]; prev=df.iloc[-2]
    price=float(last["Close"]); e9=float(last["EMA9"]); e21=float(last["EMA21"]); e55=float(last["EMA55"]); e200=float(last["EMA200"])
    vwap=float(last["VWAP"]) if not pd.isna(last["VWAP"]) else np.nan; adxv=float(last["ADX"]) if not pd.isna(last["ADX"]) else 0.0
    atrv=float(last["ATR"]) if not pd.isna(last["ATR"]) else 0.0; atrbase=float(last["ATR_BASE"]) if not pd.isna(last["ATR_BASE"]) else 0.0
    volbase=float(last["VOL_BASE"]) if not pd.isna(last["VOL_BASE"]) else 0.0; rvol=float(last["Volume"]/volbase) if volbase>0 else 0.0
    trend_bull=price>e200; ema_bull=e21>e55; accel_bull=e9>e21; fast_rising=last["EMA21"]>prev["EMA21"]; accel_rising=last["EMA9"]>prev["EMA9"]
    above_vwap=bool(price>vwap) if not pd.isna(vwap) else False
    fresh_buy=last["EMA21"]>last["EMA55"] and prev["EMA21"]<=prev["EMA55"] and trend_bull
    early_buy=trend_bull and accel_bull and fast_rising and accel_rising and price>e21 and e21<=e55*1.015
    pullback_buy=trend_bull and ema_bull and price>=e21 and abs(safe_pct(price,e21))<=PULLBACK_NEAR_EMA_PCT and adxv>=ADX_MIN
    exit_signal=price<e55 or (last["EMA21"]<last["EMA55"] and prev["EMA21"]>=prev["EMA55"])
    volume_good=rvol>=1.10; extension=safe_pct(price,e21); atr_pct=(atrv/price)*100 if price else 0
    rs_qqq=0.0
    if market_df is not None and not market_df.empty and len(market_df)>RS_LOOKBACK and len(df)>RS_LOOKBACK:
        rs_qqq=safe_pct(df["Close"].iloc[-1],df["Close"].iloc[-RS_LOOKBACK])-safe_pct(market_df["Close"].iloc[-1],market_df["Close"].iloc[-RS_LOOKBACK])
    trend_score=(25 if trend_bull else 0)+(25 if ema_bull else 0)+(10 if fast_rising else 0)+(10 if above_vwap else 0); trend_score=min(trend_score,70)
    momentum=(10 if accel_bull else 0)+(10 if accel_rising else 0)+(10 if adxv>=ADX_MIN else 0); momentum=min(momentum,30)
    volume_score=10 if volume_good else 0; rs_score=10 if rs_qqq>0 else 0; risk_score=-10 if market_regime.get("regime")=="RISK-OFF" else 0
    score=int(max(0,min(100,trend_score+momentum+volume_score+rs_score+risk_score)))
    hot=trend_bull and ema_bull and adxv>=HOT_ADX and extension>=HOT_EXTENSION_PCT
    zone_low=max(0.0,e21-atrv*BUY_ZONE_ATR_WIDTH); zone_high=e21+atrv*BUY_ZONE_ATR_WIDTH
    in_zone=zone_low<=price<=zone_high; near_zone=zone_low*0.995<=price<=zone_high*1.015
    stop=price-atrv*STOP_ATR; tp1=price+atrv*TP1_ATR
    state="NEUTRAL"; note="No clean setup"
    if exit_signal: state="EXIT"; note="Trend broke / below EMA55"
    elif fresh_buy and score>=60: state="BUY"; note="Fresh EMA21/55 bullish trigger"
    elif pullback_buy and score>=65: state="PULLBACK BUY"; note="Bull trend pulling into EMA21 area"
    elif early_buy and score>=55: state="EARLY BUY"; note="Early acceleration before full confirmation"
    elif hot: state="HOT"; note="Strong but extended; avoid chasing"
    elif trend_bull and ema_bull and score>=55: state="HOLD"; note="Bullish trend intact"
    elif trend_bull and score>=45: state="READY"; note="Setup building; wait for trigger"
    if exit_signal or not trend_bull: entry="NO"
    elif hot and not in_zone: entry="NO"; note+=" | Entry NO: too extended"
    elif state in ["BUY","PULLBACK BUY","EARLY BUY"] and near_zone: entry="YES"
    elif state in ["HOLD","READY"] and in_zone and score>=60: entry="YES"; note+=" | Entry zone active"
    elif state in ["BUY","PULLBACK BUY","EARLY BUY","HOLD","READY"] and near_zone: entry="WATCH"; note+=" | Near entry zone"
    else: entry="NO"
    if exit_signal: protection="EXIT"
    elif hot or extension>=HOT_EXTENSION_PCT: protection="LOCK GAINS"
    elif trend_bull and ema_bull and price>=e21 and above_vwap: protection="SAFE"
    elif trend_bull and price<e21 and price>e55: protection="WARNING"
    else: protection="WARNING"
    if market_regime.get("regime")=="RISK-OFF" and entry=="YES": entry="WATCH"; note+=" | Market risk-off: smaller size"
    if not above_vwap and state in ["BUY","EARLY BUY","PULLBACK BUY","HOLD"]: note+=" | Below VWAP caution"
    recent=df.tail(80).copy()
    if len(recent)>20:
        ema_respect=float(((((recent["Close"]-recent["EMA21"]).abs()/recent["Close"]*100)<=3.0)&(recent["Close"]>recent["EMA55"])).mean()*100)
        trend_days=float((((recent["Close"]>recent["EMA200"])&(recent["EMA21"]>recent["EMA55"])).mean()*100))
    else: ema_respect=trend_days=0.0
    tl=theme.lower(); is_etf=symbol in ["QQQ","SPY","VOO","IWM","DIA","SMH","SOXX","ARKK"] or "etf" in tl or "market" in tl; is_crypto=symbol.endswith("-USD") or "crypto" in tl or "mining" in tl; is_high=any(x in tl for x in ["high-beta","space","ai infrastructure","crypto","quantum"])
    ag=(20 if trend_bull else 0)+(18 if accel_bull and accel_rising else 0)+(15 if rs_qqq>5 else 8 if rs_qqq>0 else 0)+(15 if rvol>=1.2 else 5 if rvol>=1.0 else 0)+(15 if atr_pct>=5 else 8 if atr_pct>=3 else 0)+(10 if adxv>=22 else 0)+(8 if is_high or is_crypto else 0)-(10 if is_etf and atr_pct<3 else 0)
    hy=(25 if trend_bull and ema_bull else 0)+(20 if ema_respect>=30 else 10 if ema_respect>=18 else 0)+(15 if 18<=adxv<=38 else 8 if adxv>38 else 0)+(12 if -2<=extension<=8 else 0)+(10 if rs_qqq>0 else 0)+(8 if volume_good else 0)+(5 if trend_days>=50 else 0)
    co=(25 if trend_bull and ema_bull else 0)+(18 if atr_pct<4 else 8 if atr_pct<7 else 0)+(14 if is_etf else 0)+(12 if 15<=adxv<=30 else 0)+(10 if rvol<1.5 else 0)+(10 if extension<6 else 0)+(6 if trend_days>=60 else 0)
    ag,hy,co=map(clamp_int,[ag,hy,co]); mode=mode_label_from_scores(ag,hy,co)
    personality="Avoid / Weak Setup" if max(ag,hy,co)<45 or state in ["EXIT","NEUTRAL"] else "Momentum / High Beta" if mode=="Aggressive" else "Trend Builder / EMA Respect" if mode=="Hybrid" else "Slow / Confirmed Trend"
    pb="PB ON" if ema_respect>=30 and mode in ["Hybrid","Conservative"] else "PB OFF"; mode_setup=f"{mode} | {pb} | FVG OFF | SWEEP OFF"
    rank=score+(18 if entry=="YES" else 6 if entry=="WATCH" else -8)+(8 if protection=="SAFE" else 3 if protection=="LOCK GAINS" else -10 if protection=="EXIT" else -3)+(8 if rs_qqq>0 else 0)+(6 if volume_good else 0)-(8 if hot and entry!="YES" else 0)
    rank=int(max(0,min(150,rank)))
    return {"rank_score":rank,"symbol":symbol,"theme":theme,"timeframe":timeframe,"state":state,"entry":entry,"protection":protection,"suggested_mode":mode,"personality":personality,"mode_setup":mode_setup,"aggressive_score":ag,"hybrid_score":hy,"conservative_score":co,"ema_respect_pct":ema_respect,"score":score,"buy_zone":f"{zone_low:.2f}-{zone_high:.2f}","price":price,"stop":stop,"tp1":tp1,"trend_score":int(trend_score),"momentum_score":int(momentum),"volume_score":int(volume_score),"rs_score":int(rs_score),"risk_score":int(risk_score),"ema9":e9,"ema21":e21,"ema55":e55,"ema200":e200,"vwap":vwap,"above_vwap":above_vwap,"adx":adxv,"atr_pct":atr_pct,"rel_vol":rvol,"rs_qqq":rs_qqq,"extension_pct":extension,"note":note}


def scan_symbols(tickers, theme_map, interval="4h", period="180d"):
    regime=get_market_regime(interval,period); market_df=download_data(MARKET_SYMBOL,interval,period); rows=[]
    for symbol in tickers:
        try:
            result=classify_symbol(symbol,theme_map.get(symbol,"Watchlist"),download_data(symbol,interval,period),market_df,regime,interval)
            if result: rows.append(result)
        except Exception as exc:
            rows.append({"rank_score":0,"symbol":symbol,"theme":theme_map.get(symbol,"Watchlist"),"timeframe":interval,"state":"ERROR","entry":"NO","protection":"N/A","score":0,"note":str(exc)})
    return sorted(rows,key=lambda r:({"YES":1,"WATCH":2,"NO":3}.get(r.get("entry"),9),-int(r.get("rank_score",0)),{"BUY":1,"PULLBACK BUY":2,"EARLY BUY":3,"READY":4,"HOLD":5,"HOT":6,"NEUTRAL":7,"EXIT":8}.get(r.get("state"),99)))


def clean_value(v):
    if isinstance(v,(np.floating,float)):
        return None if np.isnan(v) or np.isinf(v) else round(float(v),4)
    if isinstance(v,(np.integer,)): return int(v)
    if isinstance(v,(np.bool_,)): return bool(v)
    return v

def clean_rows(rows): return [{k:clean_value(v) for k,v in r.items()} for r in rows]

def default_universe(): return build_discovery_universe(DEFAULT_THEMES)

def envelope(rows, regime, interval, period):
    return {"scanner":"Quality Flow Scanner V5.1","generated_at":datetime.now(timezone.utc).isoformat(),"interval":interval,"period":period,"market_regime":regime,"count":len(rows),"results":clean_rows(rows)}

@app.get("/health")
def health(): return {"ok":True,"scanner":"MasterScanner V5.1 API"}

@app.get("/buy-now")
def buy_now(interval:str="4h", period:str="180d", limit:int=Query(20,ge=1,le=100)):
    tickers,theme_map=default_universe(); regime=get_market_regime(interval,period); rows=scan_symbols(tickers,theme_map,interval,period)
    rows=[r for r in rows if r.get("entry")=="YES" and r.get("protection")=="SAFE" and r.get("state") in ["BUY","PULLBACK BUY"]]
    rows=sorted(rows,key=lambda r:r.get("rank_score",0), reverse=True)[:limit]
    return envelope(rows,regime,interval,period)

@app.get("/watch-today")
def watch_today(interval:str="4h", period:str="180d", limit:int=Query(20,ge=1,le=100)):
    tickers,theme_map=default_universe(); regime=get_market_regime(interval,period); rows=scan_symbols(tickers,theme_map,interval,period)
    rows=[r for r in rows if r.get("entry")=="YES" and r.get("protection")=="SAFE" and r.get("state") in ["EARLY BUY","READY"]]
    rows=sorted(rows,key=lambda r:r.get("rank_score",0), reverse=True)[:limit]
    return envelope(rows,regime,interval,period)

@app.get("/no-new-entry")
def no_new_entry(interval:str="4h", period:str="180d", limit:int=Query(30,ge=1,le=100)):
    tickers,theme_map=default_universe(); regime=get_market_regime(interval,period); rows=scan_symbols(tickers,theme_map,interval,period)
    rows=[r for r in rows if r.get("state") in ["HOLD","HOT","EXIT"] or r.get("protection") in ["WARNING","EXIT","LOCK GAINS"] or r.get("entry")=="NO"]
    rows=sorted(rows,key=lambda r:r.get("rank_score",0), reverse=True)[:limit]
    return envelope(rows,regime,interval,period)

@app.get("/scan/{symbol}")
def scan_one(symbol:str, interval:str="4h", period:str="180d"):
    symbol=symbol.strip().upper(); regime=get_market_regime(interval,period); market_df=download_data(MARKET_SYMBOL,interval,period)
    result=classify_symbol(symbol,"Direct Scan",download_data(symbol,interval,period),market_df,regime,interval)
    if not result: raise HTTPException(status_code=404,detail="No usable market data returned for symbol")
    return envelope([result],regime,interval,period)

@app.get("/scan")
def scan_list(symbols:str=Query(...,description="Comma-separated symbols"), interval:str="4h", period:str="180d"):
    tickers=unique_keep_order(symbols.split(",")); theme_map={s:"Direct Scan" for s in tickers}; regime=get_market_regime(interval,period)
    return envelope(scan_symbols(tickers,theme_map,interval,period),regime,interval,period)
