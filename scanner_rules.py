"""Canonical bar construction and signal validation for MasterScanner V5.2."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Optional

import pandas as pd


SCANNER_VERSION = "5.2"
RULE_VERSION = "2026-09-10-v2"
BUY_NOW_STATES = frozenset({"BUY", "PULLBACK BUY"})
MIN_ADX = 20.0
MIN_RELATIVE_VOLUME = 0.80
MIN_RISK_REWARD = 2.0
STOP_ZONE_ATR_BUFFER = 0.65
TP_ZONE_ATR_EXTENSION = 2.50


def _now_for_index(index: pd.DatetimeIndex, now: Optional[pd.Timestamp]) -> pd.Timestamp:
    if now is None:
        return pd.Timestamp.now(tz=index.tz) if index.tz is not None else pd.Timestamp.now()
    current = pd.Timestamp(now)
    if index.tz is None:
        return current.tz_localize(None) if current.tzinfo is not None else current
    if current.tzinfo is None:
        return current.tz_localize(index.tz)
    return current.tz_convert(index.tz)


def bar_close_at(bar_start: pd.Timestamp, symbol: str) -> pd.Timestamp:
    """Return the actual close time for a session-aligned scanner bar."""
    start = pd.Timestamp(bar_start)
    if symbol.upper().endswith("-USD"):
        return start + pd.Timedelta(hours=4)
    session_close = start.normalize() + pd.Timedelta(hours=16)
    return min(start + pd.Timedelta(hours=4), session_close)


def resample_closed_4h(
    df: pd.DataFrame,
    symbol: str,
    now: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """Build session 4-hour bars and exclude the actively forming bar.

    US symbols produce 09:30-13:30 and 13:30-16:00 ET bars. The latter is a
    shortened closing-session bar. A cumulative regular-session VWAP is retained
    as ``SessionVWAP`` so it cannot be confused with rolling VWAP.
    """
    if df.empty:
        return df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("Market data must use a DatetimeIndex")

    data = df.copy().sort_index()
    is_crypto = symbol.upper().endswith("-USD")
    if not is_crypto:
        local = data.index.tz_convert("America/New_York") if data.index.tz is not None else data.index
        minutes = local.hour * 60 + local.minute
        regular = (minutes >= 570) & (minutes < 960)
        data = data[regular]
        local = local[regular]
        if data.empty:
            return data
        typical = (data["High"] + data["Low"] + data["Close"]) / 3.0
        session_key = local.normalize()
        pv = typical * data["Volume"]
        cumulative_pv = pv.groupby(session_key).cumsum()
        cumulative_volume = data["Volume"].groupby(session_key).cumsum().replace(0, pd.NA)
        data["SessionVWAP"] = cumulative_pv / cumulative_volume

    kwargs: dict[str, Any] = {"origin": "start_day", "label": "left", "closed": "left"}
    if not is_crypto:
        kwargs["offset"] = "9h30min"
    aggregations: dict[str, str] = {
        "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
    }
    if "SessionVWAP" in data:
        aggregations["SessionVWAP"] = "last"
    bars = data.resample("4h", **kwargs).agg(aggregations).dropna(subset=["Open", "High", "Low", "Close"])
    if bars.empty:
        return bars

    current = _now_for_index(bars.index, now)
    if current < bar_close_at(bars.index[-1], symbol):
        bars = bars.iloc[:-1]
    if not bars.empty:
        bars.attrs["last_bar_start_at"] = bars.index[-1].isoformat()
        bars.attrs["last_bar_close_at"] = bar_close_at(bars.index[-1], symbol).isoformat()
    return bars


def _inside_buy_zone(row: Mapping[str, Any]) -> bool:
    try:
        low, high = map(float, str(row["buy_zone"]).split("-", 1))
        price = float(row["price"])
    except (KeyError, TypeError, ValueError):
        return False
    return low <= price <= high


def risk_reward(row: Mapping[str, Any]) -> float:
    try:
        price, stop, target = float(row["price"]), float(row["stop"]), float(row["tp1"])
    except (KeyError, TypeError, ValueError):
        return 0.0
    risk = price - stop
    return max(0.0, (target - price) / risk) if risk > 0 else 0.0


def trade_levels(zone_low: float, zone_high: float, atr_value: float) -> tuple[float, float]:
    """Return structure-anchored invalidation and first target levels."""
    return (
        max(0.0, zone_low - atr_value * STOP_ZONE_ATR_BUFFER),
        zone_high + atr_value * TP_ZONE_ATR_EXTENSION,
    )


def is_structural_candidate(row: Mapping[str, Any]) -> bool:
    """The stable 4-hour candidate contract, before confirmation gates."""
    return (
        row.get("entry") == "YES"
        and row.get("protection") == "SAFE"
        and row.get("state") in BUY_NOW_STATES
        and row.get("above_vwap") is True
        and _inside_buy_zone(row)
    )


def validation_reasons(row: Mapping[str, Any]) -> list[str]:
    """Return every reason a candidate is not an actionable BUY NOW signal."""
    reasons: list[str] = []
    if not is_structural_candidate(row):
        reasons.append("4h setup is not a valid in-zone SAFE candidate")
        return reasons
    if str(row.get("market_gate", "UNKNOWN")) != "CONFIRM":
        reasons.append(f"market gate is {row.get('market_gate', 'UNKNOWN')}")
    if float(row.get("adx", 0) or 0) < MIN_ADX:
        reasons.append(f"ADX below {MIN_ADX:g}")
    if float(row.get("rel_vol", 0) or 0) < MIN_RELATIVE_VOLUME:
        reasons.append(f"relative volume below {MIN_RELATIVE_VOLUME:.2f}x")
    rr = float(row.get("risk_reward", risk_reward(row)) or 0)
    if rr < MIN_RISK_REWARD:
        reasons.append(f"reward/risk below {MIN_RISK_REWARD:.1f}:1")
    if row.get("mtf_confirmed") is not True:
        reasons.append("weekly/daily/4h alignment not confirmed")
    if row.get("confirmation_15m") is not True:
        reasons.append("completed 15-minute confirmation missing")
    return reasons


def annotate_validation(row: Mapping[str, Any]) -> dict[str, Any]:
    enriched = dict(row)
    enriched["risk_reward"] = round(risk_reward(enriched), 3)
    reasons = validation_reasons(enriched)
    enriched["validation_status"] = "BUY NOW VALID" if not reasons else "WATCH/WAIT"
    enriched["validation_reasons"] = reasons
    return enriched


def is_buy_now_result(row: Mapping[str, Any]) -> bool:
    return not validation_reasons(row)


def filter_buy_now(rows: Iterable[Mapping[str, Any]], limit: Optional[int] = None) -> list[Mapping[str, Any]]:
    valid = [annotate_validation(row) for row in rows if is_buy_now_result(row)]
    valid.sort(key=lambda row: (float(row.get("risk_reward", 0)), int(row.get("rank_score", 0))), reverse=True)
    return valid if limit is None else valid[:limit]


def completed_15m_confirmation(df: pd.DataFrame, now: Optional[pd.Timestamp] = None) -> dict[str, Any]:
    """Validate the latest completed regular-session 15-minute bar."""
    result = {"confirmed": False, "bar_close_at": None, "session_vwap": None, "relative_volume": 0.0}
    if df.empty or not isinstance(df.index, pd.DatetimeIndex):
        return result
    data = df.copy().sort_index()
    current = _now_for_index(data.index, now)
    data = data[data.index + pd.Timedelta(minutes=15) <= current]
    if data.empty:
        return result
    local = data.index.tz_convert("America/New_York") if data.index.tz is not None else data.index
    minutes = local.hour * 60 + local.minute
    regular = (minutes >= 570) & (minutes < 960)
    data = data[regular]
    local = local[regular]
    if data.empty:
        return result
    latest_session = local.normalize()[-1]
    session = data[local.normalize() == latest_session].copy()
    if len(session) < 2:
        return result
    typical = (session["High"] + session["Low"] + session["Close"]) / 3.0
    volume = session["Volume"].astype(float)
    session_vwap = float((typical * volume).sum() / volume.sum()) if volume.sum() > 0 else float("nan")
    ema9 = session["Close"].ewm(span=9, adjust=False).mean()
    baseline = volume.rolling(20, min_periods=4).mean().iloc[-1]
    relative_volume = float(volume.iloc[-1] / baseline) if baseline and not pd.isna(baseline) else 0.0
    last, previous = session.iloc[-1], session.iloc[-2]
    price_action = float(last["Close"]) >= float(last["Open"]) or float(last["Close"]) >= float(previous["Close"])
    confirmed = (
        float(last["Close"]) >= session_vwap
        and float(last["Close"]) >= float(ema9.iloc[-1])
        and price_action
        and relative_volume >= MIN_RELATIVE_VOLUME
    )
    result.update(
        confirmed=bool(confirmed),
        bar_close_at=(session.index[-1] + pd.Timedelta(minutes=15)).isoformat(),
        session_vwap=round(session_vwap, 4),
        relative_volume=round(relative_volume, 3),
    )
    return result


def closed_higher_timeframe(
    df: pd.DataFrame,
    timeframe: str,
    now: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """Remove an unfinished daily or weekly bar before MTF validation."""
    if df.empty or not isinstance(df.index, pd.DatetimeIndex):
        return df.copy()
    data = df.copy().sort_index()
    current = pd.Timestamp.now(tz="America/New_York") if now is None else pd.Timestamp(now)
    if current.tzinfo is None:
        current = current.tz_localize("America/New_York")
    else:
        current = current.tz_convert("America/New_York")
    last = pd.Timestamp(data.index[-1])
    if last.tzinfo is None:
        last_date = last.date()
    else:
        last_date = last.tz_convert("America/New_York").date()
    if timeframe == "1d" and last_date == current.date() and current.time() < pd.Timestamp("16:00").time():
        data = data.iloc[:-1]
    elif timeframe == "1wk":
        current_week_start = (current - pd.Timedelta(days=current.weekday())).date()
        last_week_start = last_date - pd.Timedelta(days=last_date.weekday())
        week_finished = current.weekday() > 4 or (current.weekday() == 4 and current.time() >= pd.Timestamp("16:00").time())
        if last_week_start == current_week_start and not week_finished:
            data = data.iloc[:-1]
    return data


def timeframe_trend_confirmed(
    df: pd.DataFrame,
    timeframe: str = "1d",
    now: Optional[pd.Timestamp] = None,
) -> bool:
    """Approximate TradingView BUY/HOLD using completed higher-timeframe bars."""
    df = closed_higher_timeframe(df, timeframe, now)
    if df.empty or len(df) < 205:
        return False
    close = df["Close"].astype(float)
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema55 = close.ewm(span=55, adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()
    return bool(close.iloc[-1] > ema200.iloc[-1] and ema21.iloc[-1] > ema55.iloc[-1] and ema21.iloc[-1] >= ema21.iloc[-2])
