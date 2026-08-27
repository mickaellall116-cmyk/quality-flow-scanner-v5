"""Shared market-bar and BUY NOW rules for MasterScanner V5.1."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Optional

import pandas as pd


BUY_NOW_STATES = frozenset({"BUY", "PULLBACK BUY"})


def _now_for_index(index: pd.DatetimeIndex, now: Optional[pd.Timestamp]) -> pd.Timestamp:
    """Return ``now`` expressed in the same timezone convention as ``index``."""
    if now is None:
        return pd.Timestamp.now(tz=index.tz) if index.tz is not None else pd.Timestamp.now()

    current = pd.Timestamp(now)
    if index.tz is None:
        return current.tz_localize(None) if current.tzinfo is not None else current
    if current.tzinfo is None:
        return current.tz_localize(index.tz)
    return current.tz_convert(index.tz)


def resample_closed_4h(
    df: pd.DataFrame,
    symbol: str,
    now: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """Build session-aligned 4-hour bars and remove the actively forming bar.

    US-listed symbols are aligned to the 09:30 exchange session, producing a
    09:30-13:30 bar and a 13:30-16:00 bar. Crypto symbols remain aligned to
    midnight and close every four hours around the clock.
    """
    if df.empty:
        return df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("Market data must use a DatetimeIndex")

    is_crypto = symbol.upper().endswith("-USD")
    kwargs: dict[str, Any] = {
        "origin": "start_day",
        "label": "left",
        "closed": "left",
    }
    if not is_crypto:
        kwargs["offset"] = "9h30min"

    bars = df.resample("4h", **kwargs).agg(
        {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }
    ).dropna()
    if bars.empty:
        return bars

    current = _now_for_index(bars.index, now)
    last_start = bars.index[-1]
    if is_crypto:
        last_close = last_start + pd.Timedelta(hours=4)
    else:
        session_close = last_start.normalize() + pd.Timedelta(hours=16)
        last_close = min(last_start + pd.Timedelta(hours=4), session_close)

    if current < last_close:
        bars = bars.iloc[:-1]
    return bars


def _inside_buy_zone(row: Mapping[str, Any]) -> bool:
    try:
        low, high = map(float, str(row["buy_zone"]).split("-", 1))
        price = float(row["price"])
    except (KeyError, TypeError, ValueError):
        return False
    return low <= price <= high


def is_buy_now_result(row: Mapping[str, Any]) -> bool:
    """Return whether a scanner row satisfies the canonical BUY NOW contract."""
    return (
        row.get("entry") == "YES"
        and row.get("protection") == "SAFE"
        and row.get("state") in BUY_NOW_STATES
        and row.get("above_vwap") is True
        and _inside_buy_zone(row)
    )


def filter_buy_now(
    rows: Iterable[Mapping[str, Any]],
    limit: Optional[int] = None,
) -> list[Mapping[str, Any]]:
    """Filter and rank rows using the shared BUY NOW contract."""
    valid = [row for row in rows if is_buy_now_result(row)]
    valid.sort(key=lambda row: int(row.get("rank_score", 0)), reverse=True)
    return valid if limit is None else valid[:limit]
