"""Input assertions for the live V3.6 path (parity spec A2/A5/A6).

Every assertion failure raises LiveInputError with a precise reason.
Naive timestamps, off-grid bars, and short history never produce a decision.
"""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ("Open", "High", "Low", "Close", "Volume")

# Equity 4H bars are session-anchored 09:30-13:30 / 13:30-16:00 ET, BUT the
# reference resample (origin="start_day", offset="9h30min" on a tz-aware
# index) applies the fixed offset across DST transitions, so the week after
# the fall-back the bins land on 08:30/12:30 local time (labels shift; the
# aggregated 1h bars are still regular-session). This is reference behavior
# shared by backtest and live path alike -- the assertion pins to the
# reference's actual grid, not an idealized one. Discovered 2026-09-18:
# an idealized {(9,30),(13,30)} check falsely rejects genuine reference
# output (332 NVDA bars).
_EQUITY_GRID = {(8, 30), (9, 30), (12, 30), (13, 30)}


class LiveInputError(Exception):
    """Raised when live input bars fail a parity assertion."""


def _is_crypto(symbol: str) -> bool:
    return symbol.upper().endswith("-USD")


def assert_valid_bars(symbol: str, bars: pd.DataFrame) -> int:
    """Validate a 4H bar frame. Returns the bar count. Raises LiveInputError."""
    if not isinstance(bars.index, pd.DatetimeIndex):
        raise LiveInputError(
            f"{symbol}: index is {type(bars.index).__name__}, not DatetimeIndex"
        )
    if bars.index.tz is None:
        raise LiveInputError(f"{symbol}: naive bar timestamps rejected (tz is None)")
    if not bars.index.is_monotonic_increasing:
        raise LiveInputError(f"{symbol}: bar index not monotonic increasing")
    if not bars.index.is_unique:
        raise LiveInputError(f"{symbol}: duplicate bar timestamps")
    missing = [c for c in REQUIRED_COLUMNS if c not in bars.columns]
    if missing:
        raise LiveInputError(f"{symbol}: missing OHLCV columns: {missing}")
    if bars[["Open", "High", "Low", "Close"]].isna().any().any():
        raise LiveInputError(f"{symbol}: NaN in OHLC (forward-fill is forbidden)")

    if _is_crypto(symbol):
        local = bars.index.tz_convert("UTC")
        bad = [
            ts for ts in local
            if ts.minute != 0 or ts.second != 0 or ts.hour % 4 != 0
        ]
        if bad:
            raise LiveInputError(
                f"{symbol}: {len(bad)} crypto bars off the 4h UTC grid, "
                f"first={bad[0].isoformat()}"
            )
    else:
        local = bars.index.tz_convert("America/New_York")
        bad = [
            ts for ts in local
            if (ts.hour, ts.minute) not in _EQUITY_GRID
        ]
        if bad:
            raise LiveInputError(
                f"{symbol}: {len(bad)} equity bars off the reference session "
                f"grid, first={bad[0].isoformat()}"
            )
        # Intraday chain consistency via the reference's own close-time rule:
        # consecutive bars on the same date must satisfy
        # next_start == bar_close_at(prev_start).
        from scanner_rules import bar_close_at
        starts = bars.index
        for a, b in zip(starts[:-1], starts[1:]):
            if a.tz_convert("America/New_York").date() == b.tz_convert("America/New_York").date():
                if pd.Timestamp(b) != bar_close_at(a, symbol):
                    raise LiveInputError(
                        f"{symbol}: intraday bars do not chain: "
                        f"{a.isoformat()} -> {b.isoformat()}, expected "
                        f"{bar_close_at(a, symbol).isoformat()}"
                    )
    return len(bars)


def assert_no_forming_bar(symbol: str, bars: pd.DataFrame, now: pd.Timestamp) -> None:
    """The last bar in the frame must be fully closed as of `now` (A11)."""
    from scanner_rules import bar_close_at
    last_start = bars.index[-1]
    if bar_close_at(last_start, symbol) > now:
        raise LiveInputError(
            f"{symbol}: last bar {last_start.isoformat()} not closed as of "
            f"{now.isoformat()} (forming-bar violation)"
        )
