"""V5.4 scan engine — narrow job per the frozen spec.

Pipeline:
    same market data + same indicator math (imported from V5.3, never
    modified) -> V5.4 hard-gate evaluation -> raw context attached ->
    frozen grade assigned -> every qualified signal output.

FROZEN GUARDRAIL: score is logged only. It NEVER determines V5.4
eligibility. v54_classify derives state/entry from pure technical triggers
WITHOUT V5.3's score>=60/65/55 thresholds. See test_v54_engine.py::
test_score_cannot_change_v54_eligibility.

V5.3 import shim: masterscanner_api is imported for its pure data and
indicator functions only. fastapi is not installed in this environment and
the HTTP surface is not needed, so a minimal stub satisfies the import.
The V5.3 file itself is never modified.
"""

from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import scanner_rules as sr
import v54_rules


def _import_v53():
    """Import masterscanner_api for its pure functions (no HTTP needed)."""
    if "masterscanner_api" in sys.modules:
        return sys.modules["masterscanner_api"]
    stub = types.ModuleType("fastapi")

    class _App:
        def __init__(self, *a, **k):
            pass

        def get(self, *a, **k):
            return lambda f: f

        def post(self, *a, **k):
            return lambda f: f

    class _HTTPException(Exception):
        def __init__(self, status_code=500, detail=""):
            super().__init__(detail)
            self.status_code = status_code

    stub.FastAPI = _App
    stub.HTTPException = _HTTPException
    stub.Query = lambda *a, **k: None
    sys.modules["fastapi"] = stub
    return importlib.import_module("masterscanner_api")


m53 = _import_v53()


# ---------------------------------------------------------------------------
# Pure setup triggers (no score inputs — guardrail by construction)
# ---------------------------------------------------------------------------

def _pure_setup_triggers(
    last: pd.Series,
    prev: pd.Series,
    price: float,
    e9: float,
    e21: float,
    e55: float,
    e200: float,
    adx: float,
    above_vwap: bool,
) -> Dict[str, bool]:
    """Technical setup triggers mirroring V5.3's definitions, minus scores.

    Field-for-field the same trigger conditions as classify_symbol's
    fresh_buy / early_buy / pullback_buy / exit_signal — with the
    score>=60/65/55 thresholds deliberately removed (frozen guardrail).
    ADX uses V5.3's ADX_MIN (18) in the trigger; the frozen V5.4 hard gate
    (ADX >= 20) is applied separately by v54_rules.v54_hard_gates_pass.
    """
    trend_bull = price > e200
    ema_bull = e21 > e55
    accel_bull = e9 > e21
    fast_rising = bool(last["EMA21"] > prev["EMA21"])
    accel_rising = bool(last["EMA9"] > prev["EMA9"])
    fresh_buy = bool(
        last["EMA21"] > last["EMA55"]
        and prev["EMA21"] <= prev["EMA55"]
        and trend_bull
    )
    early_buy = bool(
        trend_bull and accel_bull and fast_rising and accel_rising
        and price > e21 and e21 <= e55 * 1.015
    )
    pullback_buy = bool(
        trend_bull and ema_bull and price >= e21
        and abs(m53.safe_pct(price, e21)) <= m53.PULLBACK_NEAR_EMA_PCT
        and adx >= m53.ADX_MIN
    )
    exit_signal = bool(
        price < e55
        or (last["EMA21"] < last["EMA55"] and prev["EMA21"] >= prev["EMA55"])
    )
    return {
        "trend_bull": bool(trend_bull),
        "ema_bull": bool(ema_bull),
        "fresh_buy": fresh_buy,
        "early_buy": early_buy,
        "pullback_buy": pullback_buy,
        "exit_signal": exit_signal,
    }


def _v54_trend_state(df: Optional[pd.DataFrame], timeframe: str) -> str:
    """confirmed | not_confirmed | unknown.

    "unknown" means the context is indeterminate (missing/insufficient
    data) — which the frozen grading maps to C (OBSERVATION), never to A.
    """
    try:
        if df is None or df.empty:
            return "unknown"
        trimmed = sr.closed_higher_timeframe(df, timeframe)
        if len(trimmed) < 205:
            return "unknown"
        return "confirmed" if sr.timeframe_trend_confirmed(df, timeframe) else "not_confirmed"
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# V5.4 classification
# ---------------------------------------------------------------------------

def v54_classify(
    symbol: str,
    theme: str,
    df: pd.DataFrame,
    market_df: Optional[pd.DataFrame],
    market_regime: Dict[str, Any],
    timeframe: str,
    daily_df: Optional[pd.DataFrame] = None,
    weekly_df: Optional[pd.DataFrame] = None,
    conf_15m: Optional[Dict[str, Any]] = None,
    premarket: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Classify one symbol under V5.4 rules.

    Same data, same indicator math as V5.3 (via m53). The V5.3 row is reused
    for its computed fields (score included — LOGGED ONLY). state/entry/
    protection are re-derived from pure triggers without score thresholds.
    """
    min_bars = max(m53.TREND_EMA, m53.ATR_BASE_LEN, m53.VOL_BASE_LEN, m53.VWAP_LEN) + 5
    if df is None or df.empty or len(df) < min_bars:
        return None

    # V5.3 row: indicator math + logged score. Score never gates V5.4.
    v53row = m53.classify_symbol(symbol, theme, df, market_df, market_regime, timeframe)
    if v53row is None:
        return None

    dfi = m53.add_indicators(df)
    last, prev = dfi.iloc[-1], dfi.iloc[-2]
    price = float(last["Close"])
    e9, e21, e55, e200 = (float(last[k]) for k in ("EMA9", "EMA21", "EMA55", "EMA200"))
    adx = float(last["ADX"]) if not pd.isna(last["ADX"]) else 0.0
    atrv = float(last["ATR"]) if not pd.isna(last["ATR"]) else 0.0
    vwap = float(last["VWAP"]) if not pd.isna(last["VWAP"]) else float("nan")
    above_vwap = bool(price > vwap) if not pd.isna(vwap) else False
    volbase = float(last["VOL_BASE"]) if not pd.isna(last["VOL_BASE"]) else 0.0
    rvol = float(last["Volume"] / volbase) if volbase > 0 else 0.0

    zone_low = max(0.0, e21 - atrv * m53.BUY_ZONE_ATR_WIDTH)
    zone_high = e21 + atrv * m53.BUY_ZONE_ATR_WIDTH
    in_zone = zone_low <= price <= zone_high
    stop, tp1 = sr.trade_levels(zone_low, zone_high, atrv)

    trig = _pure_setup_triggers(last, prev, price, e9, e21, e55, e200, adx, above_vwap)

    # Protection mirrors V5.3's non-score logic (hot/extension included).
    extension = m53.safe_pct(price, e21)
    hot = trig["trend_bull"] and trig["ema_bull"] and adx >= m53.HOT_ADX and extension >= m53.HOT_EXTENSION_PCT
    if trig["exit_signal"]:
        protection = "EXIT"
    elif hot or extension >= m53.HOT_EXTENSION_PCT:
        protection = "LOCK GAINS"
    elif trig["trend_bull"] and trig["ema_bull"] and price >= e21 and above_vwap:
        protection = "SAFE"
    elif trig["trend_bull"] and price < e21 and price > e55:
        protection = "WARNING"
    else:
        protection = "WARNING"

    # State from pure triggers — NO score thresholds (frozen guardrail).
    if trig["exit_signal"]:
        state = "EXIT"
    elif trig["fresh_buy"]:
        state = "BUY"
    elif trig["pullback_buy"]:
        state = "PULLBACK BUY"
    elif trig["early_buy"]:
        state = "EARLY BUY"
    else:
        state = "NEUTRAL"

    # Entry follows the structural contract exactly (no score).
    entry = "YES" if (
        state in ("BUY", "PULLBACK BUY")
        and protection == "SAFE"
        and above_vwap
        and in_zone
    ) else "NO"

    gate = str(market_regime.get("gate", "UNKNOWN")).upper()
    if gate not in ("BLOCK", "CAUTION", "CONFIRM"):
        gate = "UNKNOWN"

    bar_start = dfi.index[-1]
    bar_close = sr.bar_close_at(bar_start, symbol)

    row: Dict[str, Any] = {
        # identity
        "symbol": symbol,
        "theme": theme,
        "timeframe": timeframe,
        "signal_id": f"v54:{symbol}:{timeframe}:{bar_close.isoformat()}:{v54_rules.V54_RULE_VERSION}",
        "signal_bar_start_at": bar_start.isoformat(),
        "signal_bar_close_at": bar_close.isoformat(),
        # V5.4 state (pure triggers, no score)
        "state": state,
        "entry": entry,
        "protection": protection,
        # levels / indicators (same math as V5.3)
        "price": price,
        "stop": stop,
        "tp1": tp1,
        "buy_zone": f"{zone_low:.2f}-{zone_high:.2f}",
        "above_vwap": above_vwap,
        "adx": adx,
        "rel_vol": rvol,
        "ema9": e9, "ema21": e21, "ema55": e55, "ema200": e200,
        "risk_reward": round(sr.risk_reward({"price": price, "stop": stop, "tp1": tp1}), 3),
        # raw grading context (observational fields; grade never replaces them)
        "market_gate": gate,
        "market_regime": market_regime.get("regime", "UNKNOWN"),
        "daily_trend": _v54_trend_state(daily_df, "1d"),
        "weekly_trend": _v54_trend_state(weekly_df, "1wk"),
        # 15m / premarket: observational only (frozen spec)
        "confirmation_15m": bool((conf_15m or {}).get("confirmed", False)),
        "confirmation_15m_at": (conf_15m or {}).get("bar_close_at"),
        "confirmation_15m_rel_vol": (conf_15m or {}).get("relative_volume", 0.0),
        # V5.3 control fields (logged only — the live control comparison)
        "v53_state": v53row.get("state"),
        "v53_entry": v53row.get("entry"),
        "v53_score": v53row.get("score"),
        "v53_rank_score": v53row.get("rank_score"),
        "v53_would_veto": v53row.get("entry") != "YES",
        "score": v53row.get("score"),  # alias; logged only, never gating
    }
    if premarket:
        row.update(premarket)
    else:
        row.update(m53.PM_EMPTY)
    return v54_rules.v54_annotate(row)


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def v54_scan_symbols(
    tickers: List[str],
    theme_map: Dict[str, str],
    interval: str = "4h",
    period: str = "180d",
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Scan all tickers. Returns (annotated_rows, market_regime).

    annotated_rows includes EVERY classified symbol (eligible or not) with
    its frozen grade attached; use v54_qualified_signals for the eligible
    set. download_data already returns closed 4H bars (completed-bar rule).
    """
    regime = m53.get_market_regime(interval, period)
    market_df = m53.download_data(m53.MARKET_SYMBOL, interval, period)
    rows: List[Dict[str, Any]] = []
    for symbol in tickers:
        try:
            df = m53.download_data(symbol, interval, period)

            def _dl(fn, *a):
                try:
                    return fn(*a)
                except Exception:
                    return None

            daily_df = _dl(m53.download_confirmation_data, symbol, "1d", "2y")
            weekly_df = _dl(m53.download_confirmation_data, symbol, "1wk", "5y")
            raw_15m = _dl(m53.download_confirmation_data, symbol, "15m", "5d")
            try:
                conf_15m = sr.completed_15m_confirmation(raw_15m) if raw_15m is not None else None
            except Exception:
                conf_15m = None
            pm = m53.premarket_fields(symbol)

            row = v54_classify(
                symbol, theme_map.get(symbol, "Watchlist"), df, market_df,
                regime, interval, daily_df, weekly_df, conf_15m, pm,
            )
            if row is not None:
                rows.append(row)
        except Exception as exc:
            rows.append({
                "symbol": symbol, "theme": theme_map.get(symbol, "Watchlist"),
                "timeframe": interval, "state": "ERROR", "entry": "NO",
                "v54_eligible": False, "v54_grade": None, "note": str(exc),
                **m53.PM_EMPTY,
            })
    return rows, regime


def v54_qualified_signals(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Every hard-gate-qualified signal, grades A/B/C — including C.

    Frozen anti-V5.3 rule: nothing qualified is dropped here.
    """
    return [r for r in rows if r.get("v54_eligible") is True]


def v54_default_universe() -> Tuple[List[str], Dict[str, str]]:
    return m53.default_universe()


def v54_envelope(
    qualified: List[Dict[str, Any]],
    regime: Dict[str, Any],
    interval: str,
    period: str,
) -> Dict[str, Any]:
    """Build the latest_v54_signals.json payload (separate from V5.3's)."""
    signal_close = regime.get("signal_bar_close_at")
    grades = {"A": 0, "B": 0, "C": 0}
    for r in qualified:
        g = r.get("v54_grade")
        if g in grades:
            grades[g] += 1
    return {
        "scanner": f"Quality Flow Scanner V{v54_rules.V54_SCANNER_VERSION}",
        "scanner_version": v54_rules.V54_SCANNER_VERSION,
        "rule_version": v54_rules.V54_RULE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "interval": interval,
        "period": period,
        "signal_bar_close_at": signal_close,
        "signal_id": f"v54:{interval}:{signal_close}:{v54_rules.V54_RULE_VERSION}" if signal_close else None,
        "market_regime": regime,
        "count": len(qualified),
        "grades": grades,
        "results": m53.clean_rows(qualified),
        "source": "v54-engine-local",
        "uses_closed_4h_candles": True,
    }
