# ============================================================
# QUALITY FLOW SCANNER V5 - MODE-AWARE DISCOVERY STREAMLIT APP
# ============================================================
# Upgrades from V3:
# 1) Discovery Mode: scans curated AI / Space / Quantum / Semis / Crypto / Nuclear / Cyber / Growth baskets
# 2) Watchlist / Discovery / Both scan modes
# 3) Theme label per ticker
# 4) ENTRY column: YES / WATCH / NO
# 5) PROTECTION column: SAFE / LOCK GAINS / WARNING / EXIT
# 6) Buy Zone, Stop, TP1 columns
# 7) Opportunity ranking across all scanned tickers
# 8) Cleaner Top Opportunities table
#
# Install:
#   pip install streamlit yfinance pandas numpy plotly
#
# Run:
#   python -m streamlit run scanner_streamlit_v4_discovery.py
# ============================================================

import os
import time
import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Quality Flow Scanner V5 Mode-Aware Discovery",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# FILES / DEFAULTS
# ============================================================

WATCHLIST_FILE = "saved_watchlist.txt"
MARKET_SYMBOL = "QQQ"

DEFAULT_WATCHLIST = [
    "NVDA", "SMCI", "APLD", "ONDS", "PLTR", "TSLA", "AVGO", "MSFT", "AMD", "ARM",
    "QQQ", "SPY", "VOO", "SMH", "BTC-USD", "ETH-USD", "SOL-USD",
]

# Curated discovery baskets. Keep this around 100-200 total unique symbols for speed.
DISCOVERY_THEMES: Dict[str, List[str]] = {
    "AI Infrastructure": [
        "NVDA", "SMCI", "APLD", "IREN", "VRT", "ANET", "MU", "AVGO", "AMD", "ARM",
        "DELL", "HPE", "NTAP", "WDC", "STX", "MRVL", "CLS", "CEG", "VST", "ETN",
    ],
    "AI Software": [
        "MSFT", "PLTR", "SNOW", "CRWD", "NET", "DDOG", "NOW", "AI", "PATH", "SOUN",
        "BBAI", "GFAI", "CRM", "ADBE", "ORCL",
    ],
    "Space": [
        "ASTS", "RKLB", "LUNR", "RDW", "PL", "SPIR", "BKSY", "SATL", "GSAT", "IRDM",
        "LMT", "NOC", "BA", "HWM", "TDY",
    ],
    "Quantum": [
        "IONQ", "RGTI", "QBTS", "QUBT", "ARQQ", "IBM", "GOOGL", "HON", "NVDA", "MSFT",
    ],
    "Semiconductors": [
        "NVDA", "AMD", "AVGO", "ARM", "MU", "MRVL", "TSM", "ASML", "AMAT", "LRCX",
        "KLAC", "TER", "ON", "NXPI", "QCOM", "INTC", "TXN", "MCHP", "SMH", "SOXX",
    ],
    "Crypto / Mining": [
        "BTC-USD", "ETH-USD", "SOL-USD", "SUI-USD", "AVAX-USD", "LINK-USD", "ONDO-USD",
        "MARA", "RIOT", "CLSK", "IREN", "CIFR", "HUT", "BTDR", "COIN", "HOOD", "MSTR",
    ],
    "Nuclear / Power": [
        "CEG", "VST", "NEE", "OKLO", "SMR", "CCJ", "UEC", "URNM", "BWXT", "ETN",
        "GEV", "PWR", "FLR", "LEU", "DNN",
    ],
    "Cybersecurity": [
        "CRWD", "PANW", "NET", "ZS", "FTNT", "S", "OKTA", "CYBR", "TENB", "RPD",
    ],
    "High-Beta Growth": [
        "ONDS", "SOFI", "HIMS", "TSLA", "PLTR", "ASTS", "RKLB", "APLD", "SMCI", "NVTS",
        "BBAI", "SOUN", "ACHR", "JOBY", "RIVN", "LCID", "UPST", "AFRM", "HOOD", "COIN",
    ],
    "ETFs / Market": [
        "QQQ", "SPY", "VOO", "IWM", "DIA", "SMH", "SOXX", "ARKK", "XLK", "XLF", "XLE", "XLV",
    ],
}

PRESETS = {
    "Core List": DEFAULT_WATCHLIST,
    "AI Momentum": sorted(set(DISCOVERY_THEMES["AI Infrastructure"] + DISCOVERY_THEMES["AI Software"])),
    "Space": DISCOVERY_THEMES["Space"],
    "Quantum": DISCOVERY_THEMES["Quantum"],
    "Crypto": DISCOVERY_THEMES["Crypto / Mining"],
    "ETFs": DISCOVERY_THEMES["ETFs / Market"],
}

# ============================================================
# SETTINGS
# ============================================================

FAST_EMA = 21
SLOW_EMA = 55
TREND_EMA = 200
ACCEL_EMA = 9
ADX_LEN = 14
ATR_LEN = 14
ATR_BASE_LEN = 50
VOL_BASE_LEN = 50
RS_LOOKBACK = 20
VWAP_LEN = 50
ADX_MIN = 18
HOT_ADX = 30
ATR_EXPANSION_THRESHOLD = 1.03
PULLBACK_NEAR_EMA_PCT = 2.5
HOT_EXTENSION_PCT = 6.0
STOP_ATR = 1.5
TP1_ATR = 2.0
BUY_ZONE_ATR_WIDTH = 0.45

# ============================================================
# HELPERS
# ============================================================

def load_saved_watchlist() -> str:
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                text = f.read().strip()
                if text:
                    return text
        except Exception:
            pass
    return ",".join(DEFAULT_WATCHLIST)


def save_watchlist(text: str) -> None:
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        f.write(text.strip())


def parse_tickers(text: str) -> List[str]:
    cleaned = text.replace("\n", ",").replace(";", ",")
    tickers: List[str] = []
    for item in cleaned.split(","):
        symbol = item.strip().upper()
        if symbol and symbol not in tickers:
            tickers.append(symbol)
    return tickers


def unique_keep_order(items: List[str]) -> List[str]:
    out: List[str] = []
    for x in items:
        x = x.strip().upper()
        if x and x not in out:
            out.append(x)
    return out


def build_discovery_universe(selected_themes: List[str]) -> Tuple[List[str], Dict[str, str]]:
    tickers: List[str] = []
    symbol_themes: Dict[str, List[str]] = {}
    for theme in selected_themes:
        for sym in DISCOVERY_THEMES.get(theme, []):
            sym = sym.upper()
            tickers.append(sym)
            symbol_themes.setdefault(sym, []).append(theme)
    tickers = unique_keep_order(tickers)
    # Keep theme label short, use first theme + +N if multiple.
    label_map: Dict[str, str] = {}
    for sym, themes in symbol_themes.items():
        label_map[sym] = themes[0] if len(themes) == 1 else f"{themes[0]} +{len(themes)-1}"
    return tickers, label_map

# ============================================================
# DATA / INDICATORS
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def download_data(symbol: str, interval: str, period: str) -> pd.DataFrame:
    yf_interval = interval
    if interval.lower() == "4h":
        yf_interval = "1h"

    df = yf.download(
        symbol,
        interval=yf_interval,
        period=period,
        progress=False,
        auto_adjust=True,
        threads=False,
    )

    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    df = df.dropna()

    if interval.lower() == "4h":
        df = df.resample("4h").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }).dropna()

    return df


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / length, adjust=False).mean()


def adx(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high = df["High"]
    low = df["Low"]
    plus_dm_raw = high.diff()
    minus_dm_raw = -low.diff()
    plus_dm = np.where((plus_dm_raw > minus_dm_raw) & (plus_dm_raw > 0), plus_dm_raw, 0.0)
    minus_dm = np.where((minus_dm_raw > plus_dm_raw) & (minus_dm_raw > 0), minus_dm_raw, 0.0)
    trur = atr(df, length)
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / length, adjust=False).mean() / trur
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / length, adjust=False).mean() / trur
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / length, adjust=False).mean()


def rolling_vwap(df: pd.DataFrame, length: int = 50) -> pd.Series:
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    vol = df["Volume"].replace(0, np.nan)
    return (typical * vol).rolling(length).sum() / vol.rolling(length).sum()


def safe_pct(a, b) -> float:
    if b == 0 or pd.isna(b):
        return 0.0
    return float(((a - b) / b) * 100)


def clamp_int(value: float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))


def mode_label_from_scores(aggressive_score: int, hybrid_score: int, conservative_score: int) -> str:
    scores = {
        "Aggressive": aggressive_score,
        "Hybrid": hybrid_score,
        "Conservative": conservative_score,
    }
    return max(scores, key=scores.get)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["Close"]
    volume = out["Volume"]
    out["EMA9"] = ema(close, ACCEL_EMA)
    out["EMA21"] = ema(close, FAST_EMA)
    out["EMA55"] = ema(close, SLOW_EMA)
    out["EMA200"] = ema(close, TREND_EMA)
    out["ATR"] = atr(out, ATR_LEN)
    out["ATR_BASE"] = out["ATR"].rolling(ATR_BASE_LEN).mean()
    out["ADX"] = adx(out, ADX_LEN)
    out["VOL_BASE"] = volume.rolling(VOL_BASE_LEN).mean()
    out["VWAP"] = rolling_vwap(out, VWAP_LEN)
    return out

# ============================================================
# SCANNER LOGIC
# ============================================================

@dataclass
class ScanResult:
    rank_score: int
    symbol: str
    theme: str
    timeframe: str
    state: str
    entry: str
    protection: str
    suggested_mode: str
    personality: str
    mode_setup: str
    aggressive_score: int
    hybrid_score: int
    conservative_score: int
    ema_respect_pct: float
    score: int
    buy_zone: str
    price: float
    stop: float
    tp1: float
    trend_score: int
    momentum_score: int
    volume_score: int
    rs_score: int
    risk_score: int
    ema9: float
    ema21: float
    ema55: float
    ema200: float
    vwap: float
    above_vwap: bool
    adx: float
    atr_pct: float
    rel_vol: float
    rs_qqq: float
    extension_pct: float
    note: str


def get_market_regime(scan_interval: str, period: str) -> Dict:
    try:
        df = download_data(MARKET_SYMBOL, scan_interval, period)
        if df.empty or len(df) < TREND_EMA + 5:
            return {"regime": "UNKNOWN", "risk_on": True, "score": 50}
        df = add_indicators(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        score = 0
        if last["Close"] > last["EMA200"]:
            score += 35
        if last["EMA21"] > last["EMA55"]:
            score += 35
        if last["EMA21"] > prev["EMA21"]:
            score += 15
        if last["Close"] > last["EMA21"]:
            score += 15
        regime = "RISK-ON" if score >= 75 else "CAUTIOUS" if score >= 50 else "RISK-OFF"
        return {"regime": regime, "risk_on": score >= 50, "score": int(score)}
    except Exception:
        return {"regime": "UNKNOWN", "risk_on": True, "score": 50}


def classify_symbol(symbol: str, theme: str, df: pd.DataFrame, market_df: Optional[pd.DataFrame], market_regime: Dict, timeframe: str) -> Optional[ScanResult]:
    if df.empty or len(df) < max(TREND_EMA, ATR_BASE_LEN, VOL_BASE_LEN, VWAP_LEN) + 5:
        return None

    df = add_indicators(df)
    last = df.iloc[-1]
    prev = df.iloc[-2]

    price = float(last["Close"])
    ema9_val = float(last["EMA9"])
    ema21_val = float(last["EMA21"])
    ema55_val = float(last["EMA55"])
    ema200_val = float(last["EMA200"])
    vwap_val = float(last["VWAP"]) if not pd.isna(last["VWAP"]) else np.nan
    adx_value = float(last["ADX"]) if not pd.isna(last["ADX"]) else 0.0
    atr_value = float(last["ATR"]) if not pd.isna(last["ATR"]) else 0.0
    atr_base = float(last["ATR_BASE"]) if not pd.isna(last["ATR_BASE"]) else 0.0
    vol_base = float(last["VOL_BASE"]) if not pd.isna(last["VOL_BASE"]) else 0.0
    rel_vol = float(last["Volume"] / vol_base) if vol_base > 0 else 0.0

    trend_bull = price > ema200_val
    ema_bull = ema21_val > ema55_val
    accel_bull = ema9_val > ema21_val
    fast_rising = last["EMA21"] > prev["EMA21"]
    accel_rising = last["EMA9"] > prev["EMA9"]
    above_vwap = bool(price > vwap_val) if not pd.isna(vwap_val) else False

    fresh_buy = last["EMA21"] > last["EMA55"] and prev["EMA21"] <= prev["EMA55"] and trend_bull
    early_buy = trend_bull and accel_bull and fast_rising and accel_rising and price > ema21_val and ema21_val <= ema55_val * 1.015
    pullback_buy = trend_bull and ema_bull and price >= ema21_val and abs(safe_pct(price, ema21_val)) <= PULLBACK_NEAR_EMA_PCT and adx_value >= ADX_MIN
    exit_signal = price < ema55_val or (last["EMA21"] < last["EMA55"] and prev["EMA21"] >= prev["EMA55"])

    atr_good = atr_value > atr_base * ATR_EXPANSION_THRESHOLD if atr_base > 0 else False
    adx_good = adx_value >= ADX_MIN
    volume_good = rel_vol >= 1.10
    extension_pct = safe_pct(price, ema21_val)
    atr_pct = (atr_value / price) * 100 if price else 0

    rs_qqq = 0.0
    if market_df is not None and not market_df.empty and len(market_df) > RS_LOOKBACK and len(df) > RS_LOOKBACK:
        stock_ret = safe_pct(df["Close"].iloc[-1], df["Close"].iloc[-RS_LOOKBACK])
        market_ret = safe_pct(market_df["Close"].iloc[-1], market_df["Close"].iloc[-RS_LOOKBACK])
        rs_qqq = stock_ret - market_ret

    trend_score = 0
    if trend_bull:
        trend_score += 25
    if ema_bull:
        trend_score += 25
    if fast_rising:
        trend_score += 10
    if above_vwap:
        trend_score += 10
    trend_score = min(trend_score, 70)

    momentum_score = 0
    if accel_bull:
        momentum_score += 10
    if accel_rising:
        momentum_score += 10
    if adx_good:
        momentum_score += 10
    momentum_score = min(momentum_score, 30)

    volume_score = 10 if volume_good else 0
    rs_score = 10 if rs_qqq > 0 else 0
    risk_score = 0 if market_regime.get("regime") != "RISK-OFF" else -10
    score = int(max(0, min(100, trend_score + momentum_score + volume_score + rs_score + risk_score)))

    hot_state = trend_bull and ema_bull and adx_value >= HOT_ADX and extension_pct >= HOT_EXTENSION_PCT
    ready_state = trend_bull and price < ema21_val and price > ema55_val and ema_bull and atr_value >= atr_base * 0.85 if atr_base > 0 else False

    # Buy zone around EMA21, widened by ATR. For strong trends, the best entry is usually near EMA21/VWAP support.
    zone_mid = ema21_val
    zone_low = max(0.0, zone_mid - atr_value * BUY_ZONE_ATR_WIDTH)
    zone_high = zone_mid + atr_value * BUY_ZONE_ATR_WIDTH
    in_buy_zone = zone_low <= price <= zone_high
    near_buy_zone = zone_low * 0.995 <= price <= zone_high * 1.015

    stop = price - atr_value * STOP_ATR
    tp1 = price + atr_value * TP1_ATR

    state = "NEUTRAL"
    note = "No clean setup"

    if exit_signal:
        state = "EXIT"
        note = "Trend broke / below EMA55"
    elif fresh_buy and score >= 60:
        state = "BUY"
        note = "Fresh EMA21/55 bullish trigger"
    elif pullback_buy and score >= 65:
        state = "PULLBACK BUY"
        note = "Bull trend pulling into EMA21 area"
    elif early_buy and score >= 55:
        state = "EARLY BUY"
        note = "Early acceleration before full confirmation"
    elif hot_state:
        state = "HOT"
        note = "Strong but extended; avoid chasing"
    elif trend_bull and ema_bull and score >= 55:
        state = "HOLD"
        note = "Bullish trend intact"
    elif trend_bull and score >= 45:
        state = "READY"
        note = "Setup building; wait for trigger"

    # ENTRY logic: direct answer to "can I buy now?"
    if exit_signal or not trend_bull:
        entry = "NO"
    elif hot_state and not in_buy_zone:
        entry = "NO"
        note += " | Entry NO: too extended"
    elif state in ["BUY", "PULLBACK BUY", "EARLY BUY"] and near_buy_zone:
        entry = "YES"
    elif state in ["HOLD", "READY"] and in_buy_zone and score >= 60:
        entry = "YES"
        note += " | Entry zone active"
    elif state in ["BUY", "PULLBACK BUY", "EARLY BUY", "HOLD", "READY"] and near_buy_zone:
        entry = "WATCH"
        note += " | Near entry zone"
    else:
        entry = "NO"

    # PROTECTION logic: direct answer to "is this normal drawdown or trend failing?"
    if exit_signal:
        protection = "EXIT"
    elif hot_state or extension_pct >= HOT_EXTENSION_PCT:
        protection = "LOCK GAINS"
    elif trend_bull and ema_bull and price >= ema21_val:
        protection = "SAFE"
    elif trend_bull and price < ema21_val and price > ema55_val:
        protection = "WARNING"
    else:
        protection = "WARNING"

    if market_regime.get("regime") == "RISK-OFF" and entry == "YES":
        entry = "WATCH"
        note += " | Market risk-off: smaller size"

    if not above_vwap and state in ["BUY", "EARLY BUY", "PULLBACK BUY", "HOLD"]:
        note += " | Below VWAP caution"

    # ============================================================
    # MODE-AWARE PERSONALITY ENGINE
    # ============================================================
    # This does NOT backtest every ticker. It estimates which QFS engine
    # fits the ticker's recent behavior using volatility, RS, EMA respect,
    # trend quality, extension, volume, and theme.
    recent = df.tail(80).copy()
    if len(recent) > 20:
        ema_respect_series = ((recent["Close"] - recent["EMA21"]).abs() / recent["Close"] * 100 <= 3.0) & (recent["Close"] > recent["EMA55"])
        ema_respect_pct = float(ema_respect_series.mean() * 100)
        trend_days_pct = float(((recent["Close"] > recent["EMA200"]) & (recent["EMA21"] > recent["EMA55"])).mean() * 100)
    else:
        ema_respect_pct = 0.0
        trend_days_pct = 0.0

    theme_lower = theme.lower()
    is_etf = symbol in ["QQQ", "SPY", "VOO", "IWM", "DIA", "SMH", "SOXX", "ARKK"] or "etf" in theme_lower or "market" in theme_lower
    is_crypto = symbol.endswith("-USD") or "crypto" in theme_lower or "mining" in theme_lower
    is_high_beta_theme = any(x in theme_lower for x in ["high-beta", "space", "ai infrastructure", "crypto", "quantum"])

    aggressive_score = 0
    aggressive_score += 20 if trend_bull else 0
    aggressive_score += 18 if accel_bull and accel_rising else 0
    aggressive_score += 15 if rs_qqq > 5 else 8 if rs_qqq > 0 else 0
    aggressive_score += 15 if rel_vol >= 1.2 else 5 if rel_vol >= 1.0 else 0
    aggressive_score += 15 if atr_pct >= 5 else 8 if atr_pct >= 3 else 0
    aggressive_score += 10 if adx_value >= 22 else 0
    aggressive_score += 8 if is_high_beta_theme or is_crypto else 0
    aggressive_score -= 10 if is_etf and atr_pct < 3 else 0

    hybrid_score = 0
    hybrid_score += 25 if trend_bull and ema_bull else 0
    hybrid_score += 20 if ema_respect_pct >= 30 else 10 if ema_respect_pct >= 18 else 0
    hybrid_score += 15 if 18 <= adx_value <= 38 else 8 if adx_value > 38 else 0
    hybrid_score += 12 if -2 <= extension_pct <= 8 else 0
    hybrid_score += 10 if rs_qqq > 0 else 0
    hybrid_score += 8 if volume_good else 0
    hybrid_score += 5 if trend_days_pct >= 50 else 0

    conservative_score = 0
    conservative_score += 25 if trend_bull and ema_bull else 0
    conservative_score += 18 if atr_pct < 4 else 8 if atr_pct < 7 else 0
    conservative_score += 14 if is_etf else 0
    conservative_score += 12 if 15 <= adx_value <= 30 else 0
    conservative_score += 10 if rel_vol < 1.5 else 0
    conservative_score += 10 if extension_pct < 6 else 0
    conservative_score += 6 if trend_days_pct >= 60 else 0

    aggressive_score = clamp_int(aggressive_score)
    hybrid_score = clamp_int(hybrid_score)
    conservative_score = clamp_int(conservative_score)

    suggested_mode = mode_label_from_scores(aggressive_score, hybrid_score, conservative_score)
    if max(aggressive_score, hybrid_score, conservative_score) < 45 or state in ["EXIT", "NEUTRAL"]:
        personality = "Avoid / Weak Setup"
    elif suggested_mode == "Aggressive":
        personality = "Momentum / High Beta"
    elif suggested_mode == "Hybrid":
        personality = "Trend Builder / EMA Respect"
    else:
        personality = "Slow / Confirmed Trend"

    # Based on today's testing: FVG/Sweep should stay dashboard-only by default.
    # Pullback can help stocks with strong EMA21 respect, but can hurt pure momentum names.
    pullback_suggestion = "PB ON" if ema_respect_pct >= 30 and suggested_mode in ["Hybrid", "Conservative"] else "PB OFF"
    mode_setup = f"{suggested_mode} | {pullback_suggestion} | FVG OFF | SWEEP OFF"

    # Rank score weights what you care about: entry + trend + RS + not chasing.
    rank_score = score
    rank_score += 18 if entry == "YES" else 6 if entry == "WATCH" else -8
    rank_score += 8 if protection == "SAFE" else 3 if protection == "LOCK GAINS" else -10 if protection == "EXIT" else -3
    rank_score += 8 if rs_qqq > 0 else 0
    rank_score += 6 if volume_good else 0
    rank_score -= 8 if hot_state and entry != "YES" else 0
    rank_score = int(max(0, min(150, rank_score)))

    return ScanResult(
        rank_score=rank_score,
        symbol=symbol,
        theme=theme,
        timeframe=timeframe,
        state=state,
        entry=entry,
        protection=protection,
        suggested_mode=suggested_mode,
        personality=personality,
        mode_setup=mode_setup,
        aggressive_score=aggressive_score,
        hybrid_score=hybrid_score,
        conservative_score=conservative_score,
        ema_respect_pct=ema_respect_pct,
        score=score,
        buy_zone=f"{zone_low:.2f}-{zone_high:.2f}",
        price=price,
        stop=stop,
        tp1=tp1,
        trend_score=int(trend_score),
        momentum_score=int(momentum_score),
        volume_score=int(volume_score),
        rs_score=int(rs_score),
        risk_score=int(risk_score),
        ema9=ema9_val,
        ema21=ema21_val,
        ema55=ema55_val,
        ema200=ema200_val,
        vwap=vwap_val,
        above_vwap=above_vwap,
        adx=adx_value,
        atr_pct=atr_pct,
        rel_vol=rel_vol,
        rs_qqq=rs_qqq,
        extension_pct=extension_pct,
        note=note,
    )


def scan_symbols(tickers: List[str], theme_map: Dict[str, str], interval: str, period: str) -> pd.DataFrame:
    market_regime = get_market_regime(interval, period)
    market_df = download_data(MARKET_SYMBOL, interval, period)

    rows = []
    progress = st.progress(0, text="Scanning symbols...")

    for idx, symbol in enumerate(tickers):
        try:
            df = download_data(symbol, interval, period)
            result = classify_symbol(symbol, theme_map.get(symbol, "Watchlist"), df, market_df, market_regime, interval)
            if result:
                rows.append(result.__dict__)
            else:
                rows.append({
                    "rank_score": 0, "symbol": symbol, "theme": theme_map.get(symbol, "Watchlist"), "timeframe": interval,
                    "state": "NO DATA", "entry": "NO", "protection": "N/A", "suggested_mode": "N/A", "personality": "No Data", "mode_setup": "N/A", "aggressive_score": 0, "hybrid_score": 0, "conservative_score": 0, "ema_respect_pct": np.nan, "score": 0, "buy_zone": "N/A",
                    "price": np.nan, "stop": np.nan, "tp1": np.nan, "trend_score": 0, "momentum_score": 0,
                    "volume_score": 0, "rs_score": 0, "risk_score": 0, "ema9": np.nan, "ema21": np.nan,
                    "ema55": np.nan, "ema200": np.nan, "vwap": np.nan, "above_vwap": False, "adx": np.nan,
                    "atr_pct": np.nan, "rel_vol": np.nan, "rs_qqq": np.nan, "extension_pct": np.nan,
                    "note": "Not enough data or no Yahoo data returned",
                })
        except Exception as exc:
            rows.append({
                "rank_score": 0, "symbol": symbol, "theme": theme_map.get(symbol, "Watchlist"), "timeframe": interval,
                "state": "ERROR", "entry": "NO", "protection": "N/A", "suggested_mode": "N/A", "personality": "Error", "mode_setup": "N/A", "aggressive_score": 0, "hybrid_score": 0, "conservative_score": 0, "ema_respect_pct": np.nan, "score": 0, "buy_zone": "N/A",
                "price": np.nan, "stop": np.nan, "tp1": np.nan, "trend_score": 0, "momentum_score": 0,
                "volume_score": 0, "rs_score": 0, "risk_score": 0, "ema9": np.nan, "ema21": np.nan,
                "ema55": np.nan, "ema200": np.nan, "vwap": np.nan, "above_vwap": False, "adx": np.nan,
                "atr_pct": np.nan, "rel_vol": np.nan, "rs_qqq": np.nan, "extension_pct": np.nan,
                "note": str(exc),
            })
        progress.progress((idx + 1) / max(1, len(tickers)), text=f"Scanned {idx + 1}/{len(tickers)}")

    progress.empty()
    df_out = pd.DataFrame(rows)
    if not df_out.empty:
        entry_priority = {"YES": 1, "WATCH": 2, "NO": 3}
        state_priority = {
            "BUY": 1, "PULLBACK BUY": 2, "EARLY BUY": 3, "READY": 4, "HOLD": 5,
            "HOT": 6, "NEUTRAL": 7, "EXIT": 8, "NO DATA": 9, "ERROR": 10,
        }
        df_out["entry_priority"] = df_out["entry"].map(entry_priority).fillna(9)
        df_out["state_priority"] = df_out["state"].map(state_priority).fillna(99)
        df_out = df_out.sort_values(["entry_priority", "rank_score", "state_priority"], ascending=[True, False, True])
        df_out = df_out.drop(columns=["entry_priority", "state_priority"])
    return df_out


def scan_mtf_states(tickers: List[str], theme_map: Dict[str, str], period: str) -> pd.DataFrame:
    frames = []
    for tf in ["1wk", "1d", "4h"]:
        scan_period = "2y" if tf == "1wk" else period
        df_tf = scan_symbols(tickers, theme_map, tf, scan_period)
        if not df_tf.empty:
            frames.append(df_tf[["symbol", "suggested_mode", "state", "entry", "score", "rank_score"]].rename(columns={
                "suggested_mode": f"{tf}_mode",
                "state": f"{tf}_state",
                "entry": f"{tf}_entry",
                "score": f"{tf}_score",
                "rank_score": f"{tf}_rank",
            }))
    if not frames:
        return pd.DataFrame()
    out = frames[0]
    for f in frames[1:]:
        out = out.merge(f, on="symbol", how="outer")
    return out

# ============================================================
# DISPLAY
# ============================================================

STATE_COLORS = {
    "BUY": "background-color: #00c853; color: black; font-weight: bold",
    "PULLBACK BUY": "background-color: #64dd17; color: black; font-weight: bold",
    "EARLY BUY": "background-color: #aeea00; color: black; font-weight: bold",
    "READY": "background-color: #ffd600; color: black; font-weight: bold",
    "HOLD": "background-color: #00bcd4; color: black; font-weight: bold",
    "HOT": "background-color: #ff9100; color: black; font-weight: bold",
    "EXIT": "background-color: #ff1744; color: white; font-weight: bold",
    "NEUTRAL": "background-color: #9e9e9e; color: black; font-weight: bold",
    "NO DATA": "background-color: #424242; color: white; font-weight: bold",
    "ERROR": "background-color: #b71c1c; color: white; font-weight: bold",
}

ENTRY_COLORS = {
    "YES": "background-color: #00c853; color: black; font-weight: bold",
    "WATCH": "background-color: #ffd600; color: black; font-weight: bold",
    "NO": "background-color: #ff7043; color: black; font-weight: bold",
}

MODE_COLORS = {
    "Aggressive": "background-color: #ff7043; color: black; font-weight: bold",
    "Hybrid": "background-color: #7c4dff; color: white; font-weight: bold",
    "Conservative": "background-color: #40c4ff; color: black; font-weight: bold",
    "N/A": "background-color: #424242; color: white; font-weight: bold",
}

PROTECTION_COLORS = {
    "SAFE": "background-color: #00c853; color: black; font-weight: bold",
    "LOCK GAINS": "background-color: #ff9100; color: black; font-weight: bold",
    "WARNING": "background-color: #ffd600; color: black; font-weight: bold",
    "EXIT": "background-color: #ff1744; color: white; font-weight: bold",
}


def style_table(df: pd.DataFrame):
    def color_state(value):
        return STATE_COLORS.get(value, "")
    def color_entry(value):
        return ENTRY_COLORS.get(value, "")
    def color_protection(value):
        return PROTECTION_COLORS.get(value, "")
    def color_mode(value):
        return MODE_COLORS.get(value, "")

    styler = df.style
    if "State" in df.columns:
        styler = styler.map(color_state, subset=["State"])
    if "Entry" in df.columns:
        styler = styler.map(color_entry, subset=["Entry"])
    if "Protection" in df.columns:
        styler = styler.map(color_protection, subset=["Protection"])
    if "Suggested Mode" in df.columns:
        styler = styler.map(color_mode, subset=["Suggested Mode"])
    return styler


def make_display_df(df: pd.DataFrame, compact: bool = False) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    rename = {
        "rank_score": "Rank Score", "symbol": "Symbol", "theme": "Theme", "timeframe": "TF",
        "state": "State", "entry": "Entry", "protection": "Protection", "suggested_mode": "Suggested Mode", "personality": "Personality", "mode_setup": "Mode Setup", "aggressive_score": "Agg Score", "hybrid_score": "Hybrid Score", "conservative_score": "Cons Score", "ema_respect_pct": "EMA Respect%", "score": "Score",
        "buy_zone": "Buy Zone", "price": "Price", "stop": "Stop", "tp1": "TP1",
        "trend_score": "Trend", "momentum_score": "Momentum", "volume_score": "Volume", "rs_score": "RS",
        "risk_score": "Risk", "ema9": "EMA9", "ema21": "EMA21", "ema55": "EMA55",
        "ema200": "EMA200", "vwap": "VWAP", "above_vwap": "Above VWAP", "adx": "ADX",
        "atr_pct": "ATR%", "rel_vol": "RVOL", "rs_qqq": "RS vs QQQ%", "extension_pct": "Ext%",
        "note": "Note",
    }
    out = out.rename(columns=rename)
    if compact:
        cols = ["Symbol", "Theme", "Suggested Mode", "Personality", "Mode Setup", "Entry", "State", "Protection", "Rank Score", "Score", "Price", "Buy Zone", "Stop", "TP1", "RVOL", "RS vs QQQ%", "Ext%", "Note"]
    else:
        cols = ["Symbol", "Theme", "TF", "Suggested Mode", "Personality", "Mode Setup", "Entry", "State", "Protection", "Rank Score", "Agg Score", "Hybrid Score", "Cons Score", "EMA Respect%", "Score", "Price", "Buy Zone", "Stop", "TP1", "Trend", "Momentum", "Volume", "RS", "Risk", "EMA9", "EMA21", "EMA55", "EMA200", "VWAP", "Above VWAP", "ADX", "ATR%", "RVOL", "RS vs QQQ%", "Ext%", "Note"]
    out = out[[c for c in cols if c in out.columns]]
    for c in ["Price", "Stop", "TP1", "EMA9", "EMA21", "EMA55", "EMA200", "VWAP"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").round(2)
    for c in ["ADX", "ATR%", "RVOL", "RS vs QQQ%", "Ext%", "EMA Respect%"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").round(2)
    return out


def plot_symbol(symbol: str, interval: str, period: str):
    df = download_data(symbol, interval, period)
    if df.empty or len(df) < 60:
        st.warning("Not enough chart data.")
        return
    df = add_indicators(df)
    tail = df.tail(180)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=tail.index, open=tail["Open"], high=tail["High"], low=tail["Low"], close=tail["Close"], name="Price"))
    fig.add_trace(go.Scatter(x=tail.index, y=tail["EMA9"], name="EMA9", mode="lines"))
    fig.add_trace(go.Scatter(x=tail.index, y=tail["EMA21"], name="EMA21", mode="lines"))
    fig.add_trace(go.Scatter(x=tail.index, y=tail["EMA55"], name="EMA55", mode="lines"))
    fig.add_trace(go.Scatter(x=tail.index, y=tail["EMA200"], name="EMA200", mode="lines"))
    fig.add_trace(go.Scatter(x=tail.index, y=tail["VWAP"], name="VWAP", mode="lines"))
    fig.update_layout(height=620, xaxis_rangeslider_visible=False, title=f"{symbol} - {interval}")
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# SIDEBAR
# ============================================================

st.title("Quality Flow Scanner V5 Mode-Aware Discovery")
st.caption("Mode-aware discovery scanner for AI, space, quantum, semis, crypto, nuclear, cyber, and high-beta growth setups.")

with st.sidebar:
    st.header("Scanner Settings")

    mode = st.radio("Mode", ["Watchlist", "Discovery", "Both"], index=1)

    preset = st.selectbox("Watchlist Preset", ["Saved / Custom"] + list(PRESETS.keys()))
    default_text = load_saved_watchlist()
    if preset != "Saved / Custom":
        default_text = ",".join(PRESETS[preset])
    watchlist_text = st.text_area("Custom / Saved Watchlist", value=default_text, height=120)

    col_save1, col_save2 = st.columns(2)
    with col_save1:
        if st.button("Save List"):
            save_watchlist(watchlist_text)
            st.success("Saved")
    with col_save2:
        if st.button("Clear Cache"):
            st.cache_data.clear()
            st.success("Cache cleared")

    st.divider()
    st.subheader("Discovery Themes")
    selected_themes = st.multiselect(
        "Themes to Scan",
        list(DISCOVERY_THEMES.keys()),
        default=["AI Infrastructure", "Space", "Quantum", "Semiconductors", "Crypto / Mining", "Nuclear / Power", "High-Beta Growth"],
    )

    st.divider()
    interval = st.selectbox("Primary Timeframe", ["1h", "4h", "1d", "1wk"], index=1)
    period = st.selectbox("Data Period", ["60d", "180d", "1y", "2y", "5y"], index=1)

    st.divider()
    st.subheader("Filters")
    min_rank = st.slider("Minimum Rank Score", 0, 150, 0, 5)
    entry_filter = st.multiselect("Entry", ["YES", "WATCH", "NO"], default=["YES", "WATCH", "NO"])
    mode_filter = st.multiselect("Suggested Mode", ["Aggressive", "Hybrid", "Conservative", "N/A"], default=["Aggressive", "Hybrid", "Conservative", "N/A"])
    show_states = st.multiselect(
        "Show States",
        ["BUY", "PULLBACK BUY", "EARLY BUY", "READY", "HOLD", "HOT", "NEUTRAL", "EXIT", "NO DATA", "ERROR"],
        default=["BUY", "PULLBACK BUY", "EARLY BUY", "READY", "HOLD", "HOT"],
    )
    hide_exit = st.checkbox("Hide EXIT", value=True)

    st.divider()
    st.subheader("Refresh")
    auto_refresh = st.checkbox("Auto-refresh", value=False)
    refresh_minutes = st.selectbox("Refresh Every", [1, 5, 15, 30, 60], index=1)

    st.divider()
    run_scan = st.button("Run Scanner", type="primary")
    run_mtf = st.button("Run W/D/4H Alignment")

if auto_refresh:
    time.sleep(refresh_minutes * 60)
    st.rerun()

# ============================================================
# UNIVERSE BUILD
# ============================================================

watchlist = parse_tickers(watchlist_text)
discovery, theme_map = build_discovery_universe(selected_themes)

if mode == "Watchlist":
    tickers = watchlist
    final_theme_map = {s: "Watchlist" for s in tickers}
elif mode == "Discovery":
    tickers = discovery
    final_theme_map = theme_map
else:
    tickers = unique_keep_order(watchlist + discovery)
    final_theme_map = {**theme_map, **{s: "Watchlist" for s in watchlist}}

if not tickers:
    st.warning("Enter tickers or select at least one discovery theme.")
    st.stop()

market_regime = get_market_regime(interval, period)
cols = st.columns(5)
cols[0].metric("Market", market_regime["regime"])
cols[1].metric("Market Score", f"{market_regime['score']}/100")
cols[2].metric("Symbols", len(tickers))
cols[3].metric("Timeframe", interval)
cols[4].metric("Mode", mode)

if run_mtf:
    st.subheader("Multi-Timeframe Alignment: Weekly / Daily / 4H")
    align_df = scan_mtf_states(tickers, final_theme_map, period)
    st.dataframe(align_df, use_container_width=True, height=520)
    st.download_button("Download Alignment CSV", data=align_df.to_csv(index=False).encode("utf-8"), file_name="quality_flow_v5_alignment.csv", mime="text/csv")

if run_scan or "last_scan_v4" not in st.session_state:
    with st.spinner("Running scanner..."):
        st.session_state["last_scan_v4"] = scan_symbols(tickers, final_theme_map, interval, period)
        st.session_state["last_scan_v4_time"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

scan_df = st.session_state.get("last_scan_v4", pd.DataFrame())
if scan_df.empty:
    st.info("No scan results yet. Click Run Scanner.")
    st.stop()

filtered = scan_df.copy()
if entry_filter:
    filtered = filtered[filtered["entry"].isin(entry_filter)]
if mode_filter and "suggested_mode" in filtered.columns:
    filtered = filtered[filtered["suggested_mode"].isin(mode_filter)]
if show_states:
    filtered = filtered[filtered["state"].isin(show_states)]
if hide_exit:
    filtered = filtered[filtered["state"] != "EXIT"]
filtered = filtered[pd.to_numeric(filtered["rank_score"], errors="coerce").fillna(0) >= min_rank]

st.subheader("Top Opportunities")
st.caption(f"Last scan: {st.session_state.get('last_scan_v4_time', 'N/A')}")
top_df = make_display_df(filtered.head(25), compact=True)
st.dataframe(style_table(top_df), use_container_width=True, height=430)

st.subheader("Full Scanner Results")
display_df = make_display_df(filtered, compact=False)
st.dataframe(style_table(display_df), use_container_width=True, height=520)

with st.expander("Alerts / Action List", expanded=True):
    alerts = filtered[filtered["entry"].isin(["YES", "WATCH"])]
    if alerts.empty:
        st.info("No Entry YES / WATCH setups right now.")
    else:
        for _, row in alerts.head(30).iterrows():
            icon = "🟢" if row["entry"] == "YES" else "🟡"
            st.write(f"{icon} **{row['symbol']}** — {row['theme']} — {row.get('suggested_mode', 'N/A')} — {row['entry']} — {row['state']} — Rank {int(row['rank_score'])} — {row['note']}")

st.download_button("Download Results CSV", data=display_df.to_csv(index=False).encode("utf-8"), file_name="quality_flow_v5_mode_aware_scan.csv", mime="text/csv")

st.subheader("Chart")
symbol_options = [r for r in filtered["symbol"].dropna().unique()] if not filtered.empty else tickers
selected_symbol = st.selectbox("Select ticker to chart", symbol_options)
if selected_symbol:
    plot_symbol(selected_symbol, interval, period)

with st.expander("How to Use V4"):
    st.markdown(
        """
        - **Entry YES** = acceptable new entry/add area.
        - **Entry WATCH** = close to entry zone, but not ideal yet.
        - **Entry NO** = avoid new money right now.
        - **Protection SAFE** = normal bullish trend/pullback.
        - **Protection LOCK GAINS** = extended; hold existing shares but don't chase.
        - **Protection WARNING** = trend weakening; watch stop/EMA55.
        - **Protection EXIT** = trend broke.
        - **Suggested Mode** = scanner's best estimate of which QFS engine fits the ticker now: Aggressive / Hybrid / Conservative.
        - **Mode Setup** = suggested TradingView configuration, including whether Pullback should be ON/OFF.
        - For your workflow: use **Discovery Mode** to find names, sort by **Rank Score**, check **Suggested Mode**, then only open charts where **Entry = YES/WATCH**.
        """
    )
