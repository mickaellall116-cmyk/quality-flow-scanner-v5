"""Live V3.6 evaluation path — SLICE 1.

For one symbol and one closed 4H bar: assert the inputs, run the canonical
reference functions, emit a deterministic decision packet.

Decision source of truth: pine_backtest.pine_buy_signal (imported).
Indicators: pine_backtest.add_pine_indicators (imported).
Bar close times: scanner_rules.bar_close_at (imported).
Data: masterscanner_api.download_data (imported) — the ONLY network call.

Paper-only: the only side effects are the packet log, bar snapshots, and
refusal records. No ranking, sector cap, position state, dedup, alerts,
orders, or trading exist in this module.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from datetime import datetime, timezone

import pandas as pd

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from pine_backtest import (  # noqa: E402
    SL_ATR,
    TP_ATR,
    WARMUP,
    add_pine_indicators,
    pine_buy_signal,
)
from scanner_rules import bar_close_at  # noqa: E402
from masterscanner_api import download_data  # noqa: E402

from pine_live.assertions import (  # noqa: E402
    LiveInputError,
    assert_no_forming_bar,
    assert_valid_bars,
)
from pine_live.decompose import decompose_signal  # noqa: E402
from pine_live.packets import PacketLog, write_snapshot  # noqa: E402

TIMEFRAME = "4h"
ADJUSTMENT_CONVENTION = "auto_adjust=True (split/dividend-adjusted OHLCV)"

_REFERENCE_FILES = ("pine_backtest.py", "scanner_rules.py", "masterscanner_api.py")


def engine_version() -> dict:
    """Identify the exact reference code that ran."""
    try:
        sha = subprocess.run(
            ["git", "-C", _REPO_ROOT, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except Exception:
        sha = "unknown"
    hashes = {}
    for name in _REFERENCE_FILES:
        path = os.path.join(_REPO_ROOT, name)
        with open(path, "rb") as f:
            hashes[name] = hashlib.sha256(f.read()).hexdigest()
    return {"repo_git_sha": sha or "unknown", "reference_sha256": hashes}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _signal_id(symbol: str, bar_start: pd.Timestamp) -> str:
    return f"v36:{symbol.upper()}:{TIMEFRAME}:{bar_start.isoformat()}"


def _refusal_packet(symbol, reason, vintage, packet_log, snapshot_dir) -> dict:
    packet = {
        "signal_id": None,
        "symbol": symbol.upper(),
        "timeframe": TIMEFRAME,
        "decision": "refused",
        "refused_reason": reason,
        "computed_at": _utcnow_iso(),
        "data_vintage": vintage,
        "engine_version": engine_version(),
        "bars_snapshot_ref": None,
    }
    return packet_log.append(packet)


def evaluate_frame(
    symbol: str,
    bars: pd.DataFrame,
    vintage: dict,
    packet_log: PacketLog,
    snapshot_dir: str,
    bar_index: int | None = None,
    now: pd.Timestamp | None = None,
) -> dict:
    """Evaluate one closed 4H bar. bar_index=None -> latest bar in frame.

    If `now` is given, the last bar must be fully closed as of `now`
    (forming-bar exclusion, A11)."""
    symbol = symbol.upper()
    try:
        n_bars = assert_valid_bars(symbol, bars)
        if now is not None:
            now_ts = pd.Timestamp(now)
            if now_ts.tzinfo is None:
                now_ts = now_ts.tz_localize(bars.index.tz)
            else:
                now_ts = now_ts.tz_convert(bars.index.tz)
            assert_no_forming_bar(symbol, bars, now_ts)
    except LiveInputError as exc:
        return _refusal_packet(symbol, f"input_assertion: {exc}", vintage,
                               packet_log, snapshot_dir)

    if n_bars < WARMUP:
        return _refusal_packet(
            symbol,
            f"warmup: {n_bars} completed bars < required {WARMUP}; no decision made",
            vintage, packet_log, snapshot_dir,
        )

    i = len(bars) - 1 if bar_index is None else bar_index
    if i < 1 or i >= len(bars):
        raise LiveInputError(f"{symbol}: bar_index {i} out of range")

    snap = write_snapshot(symbol, bars, snapshot_dir)
    ind = add_pine_indicators(bars)  # canonical, imported
    parts = decompose_signal(ind, i)  # read-only explanation of the formula
    decision_bool = bool(pine_buy_signal(ind, i))  # THE decision, canonical
    if parts["decision"] != decision_bool or parts["reference_decision"] != decision_bool:
        # The mirror and the reference disagree: fail closed, never emit.
        return _refusal_packet(
            symbol,
            "internal: decompose/reference decision mismatch; fail-closed",
            vintage, packet_log, snapshot_dir,
        )

    bar_start = bars.index[i]
    r = ind.iloc[i]
    bar = bars.iloc[i]
    signal_bar_close = bar_close_at(bar_start, symbol)

    packet = {
        "signal_id": _signal_id(symbol, bar_start),
        "symbol": symbol,
        "timeframe": TIMEFRAME,
        "signal_bar_start": bar_start.isoformat(),
        "signal_bar_close": signal_bar_close.isoformat(),
        "computed_at": _utcnow_iso(),
        # Next bar's open is the actionable time. For the terminal bar the
        # next bar is not in-frame (e.g. overnight gap), so we record the
        # earliest possible time and flag it.
        "actionable_at": signal_bar_close.isoformat(),
        "next_bar_open_known": False,
        "actionable_at_note": (
            "next bar open; for the terminal bar this is the earliest "
            "possible time (next session open may be later)"
        ),
        "decision": "signal" if decision_bool else "no_signal",
        "signal_bar_ohlcv": {
            "open": float(bar["Open"]),
            "high": float(bar["High"]),
            "low": float(bar["Low"]),
            "close": float(bar["Close"]),
            "volume": float(bar["Volume"]),
        },
        "indicators_at_i": {
            k: (None if pd.isna(r[k]) else float(r[k]))
            for k in ("e9", "e21", "e55", "e200", "atr", "atr_base",
                      "atr_ratio", "adx", "vol_ma")
        },
        "sub_conditions": {
            k: parts[k] for k in (
                "nan_guard_passed", "volume_ok", "hot", "safe",
                "trend_bull", "strong_trend", "trend_score",
                "breakout", "ready_prev",
                "confirmed", "breakout_buy", "ready_buy")
        },
        "entry_plan": {
            "entry_px_rule": "next_bar_open",
            "stop_rule": "signal_close - 1.5*ATR",
            "stop_px": float(r["Close"] - r["atr"] * SL_ATR),
            "tp1_px_provisional": float(r["Close"] + r["atr"] * TP_ATR),
            "tp1_note": (
                "provisional: reference tp1 = actual next-bar entry "
                "+ 2.0*ATR; entry price unknown until the next bar opens"
            ),
        },
        "data_vintage": dict(vintage, n_bars_used=n_bars,
                             first_bar_start=bars.index[0].isoformat(),
                             last_bar_start=bars.index[-1].isoformat(),
                             adjustment_convention=ADJUSTMENT_CONVENTION,
                             warmup_bars=WARMUP, warmup_ok=True),
        "engine_version": engine_version(),
        "bars_snapshot_ref": {"path": snap["path"], "sha256": snap["sha256"],
                              "n_bars": snap["n_bars"]},
    }
    return packet_log.append(packet)


def evaluate_live(
    symbol: str,
    period: str = "1y",
    packet_log: PacketLog | None = None,
    snapshot_dir: str | None = None,
) -> dict:
    """Download fresh 4H bars and evaluate the latest closed bar."""
    base = os.path.dirname(os.path.abspath(__file__))
    packet_log = packet_log or PacketLog(os.path.join(base, "packets", "decisions.jsonl"))
    snapshot_dir = snapshot_dir or os.path.join(base, "snapshots")
    downloaded_at = _utcnow_iso()
    bars = download_data(symbol, "4h", period)  # the ONLY network call
    if bars.empty:
        return _refusal_packet(
            symbol, "download: empty frame", _vintage(symbol, downloaded_at, 0),
            packet_log, snapshot_dir,
        )
    return evaluate_frame(symbol, bars, _vintage(symbol, downloaded_at, len(bars)),
                          packet_log, snapshot_dir,
                          now=pd.Timestamp(downloaded_at))


def _vintage(symbol: str, downloaded_at: str, n_bars: int) -> dict:
    return {
        "bars_source": "yfinance",
        "bars_downloaded_at": downloaded_at,
        "n_bars_downloaded": n_bars,
    }
