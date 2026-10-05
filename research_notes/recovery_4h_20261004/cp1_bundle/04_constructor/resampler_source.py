# Verbatim source extract from scanner_rules.py (lines 87-267)
# File SHA-256 at extract time: 7db282ddfc150c9e9aec7d8f1f10f439ce7e296da2d69da38f97ed8cbec70cac
# Extracted: 2026-10-04

def resample_closed_4h(
    df: pd.DataFrame,
    symbol: str,
    now: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """Build session 4-hour bars and exclude the actively forming bar.

    US symbols produce 09:30-13:30 and 13:30-16:00 ET bars. The latter is a
    shortened closing-session bar. A cumulative regular-session VWAP is retained
    as ``SessionVWAP`` so it cannot be confused with rolling VWAP.

    RETAINED FOR THE AFFECTED FORWARD-TEST COHORT (entered 2026-09-15..10-03
    on this function's grid). Known defect: the pandas ``origin='start_day'``
    anchor is UTC-anchored to midnight of the first download day, so the
    resulting grid shifts with DST and download-window length (live produced
    06:30/10:30/14:30 instead of the intended 09:30/13:30). New work must use
    ``resample_closed_4h_session_anchored``. Do not change this function's
    behavior while the affected cohort has open positions.
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


def resample_closed_4h_session_anchored(
    df: pd.DataFrame,
    symbol: str,
    now: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """Session-anchored 4h bars, invariant to DST and download-window length.

    US symbols produce 09:30-13:30 and 13:30-16:00 America/New_York bars
    (the latter a shortened closing-session bar), matching the grid in
    ``backtest_cache/h4_*.pkl``. Bins are assigned explicitly from local
    session time — never via pandas ``origin='start_day'``, whose anchor is
    UTC-anchored to midnight of the first download day and shifts the grid
    with DST and window length (the defect that put the live forward test
    on 06:30/10:30/14:30 candles).

    Crypto ("-USD") symbols produce 00:00/04:00/.../20:00 UTC-anchored bars.

    Same output schema as ``resample_closed_4h`` (tz-aware DatetimeIndex,
    Open/High/Low/Close/Volume[/SessionVWAP], last_bar_* attrs) and the
    same forming-bar exclusion via ``bar_close_at``. Intended for the
    separately versioned corrected forward test — NOT wired into the live
    harness while the affected cohort is still managed on the old grid.

    Causal input guarantee (fail-closed): rows dated after ``now`` are dropped
    before binning, so no bar can contain future data regardless of what the
    caller passes. Session close is read from the XNYS exchange calendar, so
    early-close days (e.g. 13:00) produce correctly completed bars.
    """
    if df.empty:
        return df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("Market data must use a DatetimeIndex")

    data = df.copy().sort_index()
    is_crypto = symbol.upper().endswith("-USD")

    # Fail-closed causal cutoff: nothing dated after `now` may contribute to
    # any bar. Without this, a full-day frame passed with an earlier `now`
    # would let future rows contaminate putatively closed bars.
    cutoff = _now_for_index(data.index, now)
    data = data[data.index <= cutoff]
    if data.empty:
        return data

    if is_crypto:
        # Anchor explicitly to UTC midnight: bins at 00/04/08/12/16/20 UTC
        # regardless of which day the download window starts on.
        if data.index.tz is None:
            utc_idx = data.index.tz_localize("UTC")
        else:
            utc_idx = data.index.tz_convert("UTC")
        day = utc_idx.normalize()
        mins = utc_idx.hour * 60 + utc_idx.minute
        bin_start_min = (mins // 240) * 240
        labels = day + pd.to_timedelta(bin_start_min, unit="m")
        data = data.copy()
        data["_bin"] = pd.DatetimeIndex(labels).tz_convert("UTC")
        grouped = data.groupby("_bin")
        session_closes: dict = {}
    else:
        if data.index.tz is None:
            raise TypeError("US equity data must be tz-aware")
        local = data.index.tz_convert("America/New_York")
        minutes = local.hour * 60 + local.minute
        day_key = local.normalize()
        # Per-date session close from the exchange calendar (16:00 regular,
        # 13:00 early-close days). Unknown dates fall back to 16:00.
        session_closes = {}
        for d in pd.DatetimeIndex(day_key.unique()):
            sc = session_close_et(d)
            session_closes[d] = sc if sc is not None else d + pd.Timedelta(hours=16)
        close_minutes = day_key.map(
            lambda d: int((session_closes[d] - d).total_seconds() // 60)
        )
        regular = (minutes >= 570) & (minutes < close_minutes)
        data = data[regular].copy()
        local = local[regular]
        if data.empty:
            return data.drop(columns=[c for c in data.columns
                                     if c not in df.columns])
        typical = (data["High"] + data["Low"] + data["Close"]) / 3.0
        session_key = local.normalize()
        pv = typical * data["Volume"]
        cumulative_pv = pv.groupby(session_key).cumsum()
        cumulative_volume = data["Volume"].groupby(session_key).cumsum().replace(0, pd.NA)
        data["SessionVWAP"] = cumulative_pv / cumulative_volume
        # Explicit session bins: [09:30,13:30) -> 09:30, [13:30,close) -> 13:30.
        # On early-close days the second bin has no rows by construction.
        bin_start_min = [570 if m < 810 else 810 for m in minutes]
        labels = session_key + pd.to_timedelta(bin_start_min, unit="m")
        data["_bin"] = pd.DatetimeIndex(labels)
        grouped = data.groupby("_bin")

    aggregations: dict[str, str] = {
        "Open": "first", "High": "max", "Low": "min", "Close": "last",
        "Volume": "sum",
    }
    if "SessionVWAP" in data.columns:
        aggregations["SessionVWAP"] = "last"
    bars = grouped.agg(aggregations).dropna(subset=["Open", "High", "Low", "Close"])
    bars.index.name = None
    if bars.empty:
        return bars

    def _close_at(bar_start: pd.Timestamp) -> pd.Timestamp:
        if is_crypto or not session_closes:
            return bar_close_at(bar_start, symbol)
        day = pd.Timestamp(bar_start).tz_convert("America/New_York").normalize()
        return bar_close_at(bar_start, symbol, session_close=session_closes.get(day))

    current = _now_for_index(bars.index, now)
    if current < _close_at(bars.index[-1]):
        bars = bars.iloc[:-1]
    if not bars.empty:
        bars.attrs["last_bar_start_at"] = bars.index[-1].isoformat()
        bars.attrs["last_bar_close_at"] = _close_at(bars.index[-1]).isoformat()
    return bars


