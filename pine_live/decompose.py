"""Read-only decomposition of the V3.6 Hybrid buy signal.

This mirrors pine_backtest.pine_buy_signal formula-for-formula to expose the
sub-condition booleans the parity spec's decision packet requires
(confirmed / breakout_buy / ready_buy and their components).

It is NOT a second decision implementation:
  - the live DECISION always comes from pine_backtest.pine_buy_signal;
  - constants (HOT_ATR, BREAKOUT_BARS) are imported from pine_backtest so
    they cannot drift independently;
  - test_decompose_matches_reference asserts decision agreement on every
    bar >= WARMUP for all 51 cached symbols. If the reference formula ever
    changes, that test fails loudly instead of silently diverging.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from pine_backtest import BREAKOUT_BARS, HOT_ATR, pine_buy_signal  # noqa: E402


def decompose_signal(df: pd.DataFrame, i: int) -> dict:
    """Return every sub-condition of the Hybrid buy signal at bar i."""
    r = df.iloc[i]
    rp = df.iloc[i - 1]

    nan_guard = not (pd.isna(r["e200"]) or pd.isna(r["atr_base"]) or pd.isna(r["adx"]))
    close, vol = r["Close"], r["Volume"]
    volume_ok = bool(vol > r["vol_ma"])
    hot = bool(close > r["e9"] + r["atr"] * HOT_ATR)
    safe = not hot
    trend_bull = bool(r["e21"] > r["e55"] and close > r["e200"])
    strong_trend = bool(r["adx"] > 20 and r["atr_ratio"] > 0.85)
    # Same explicit int-cast fix as pine_backtest.pine_buy_signal: the raw
    # NumPy boolean sum collapses to a Boolean, killing score >= 4 / >= 3.
    trend_score = (
        int(r["e9"] > r["e21"])
        + int(r["e21"] > r["e55"])
        + int(close > r["e200"])
        + int(r["adx"] > 25)
        + int(r["atr_ratio"] > 1)
    )
    breakout = bool(close > df["High"].iloc[i - BREAKOUT_BARS:i].max())
    ready_prev = bool(
        rp["Close"] < rp["e21"]
        and rp["Close"] > rp["e55"]
        and rp["e21"] > rp["e55"]
        and rp["atr_ratio"] > 0.85
    )

    confirmed = bool(
        close > r["e21"]
        and r["e21"] > r["e55"]
        and close > r["e200"]
        and trend_score >= 4
        and volume_ok
        and safe
    )
    breakout_buy = bool(trend_bull and strong_trend and breakout and volume_ok and safe)
    ready_buy = bool(
        ready_prev and close > r["e21"] and trend_score >= 3 and volume_ok and safe
    )
    decision = bool(nan_guard and (confirmed or breakout_buy or ready_buy))

    return {
        "nan_guard_passed": nan_guard,
        "volume_ok": volume_ok,
        "hot": hot,
        "safe": safe,
        "trend_bull": trend_bull,
        "strong_trend": strong_trend,
        "trend_score": trend_score,
        "breakout": breakout,
        "ready_prev": ready_prev,
        "confirmed": confirmed,
        "breakout_buy": breakout_buy,
        "ready_buy": ready_buy,
        "decision": decision,
        # Cross-check against the canonical decision in the same call.
        "reference_decision": bool(pine_buy_signal(df, i)),
    }
