"""Detection-delay slicing — pure functions.

OBSERVATION ONLY. Slices dual-ledger per-trade drag (canonical vs
achievable fills, see pine_live/paper/dual.py) by symbol, structural-vol
bucket, time-of-day, gap-size bucket, and regime. Bucket definitions are
pre-registered in DELAY_STUDY_SPEC.md and frozen. No bucket is ranked
until it holds MIN_BUCKET_TRADES trades; smaller buckets are labeled
INSUFFICIENT_SAMPLE and excluded from all rankings.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

# Pre-registered (frozen in DELAY_STUDY_SPEC.md).
MIN_BUCKET_TRADES = 10
INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"

# Structural-vol buckets: stop distance / entry (frozen stop ~= 1.5x ATR).
VOL_BUCKETS = (
    (0.015, "vol<1.5%"),
    (0.030, "vol 1.5-3%"),
    (0.050, "vol 3-5%"),
    (float("inf"), "vol>=5%"),
)
# UTC hour-of-day buckets for entry_time.
TOD_BUCKETS = (
    (6, "tod 00-05"),
    (12, "tod 06-11"),
    (18, "tod 12-17"),
    (24, "tod 18-23"),
)
# Entry-leg gap buckets, |next-bar-open - signal-bar-close| in bps.
GAP_BUCKETS = (
    (10.0, "gap<10bps"),
    (30.0, "gap 10-30bps"),
    (75.0, "gap 30-75bps"),
    (float("inf"), "gap>=75bps"),
)
BPS = 10000.0


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def _bucket(value: float, buckets: tuple) -> str | None:
    if not _finite(value):
        return None
    for upper, name in buckets:
        if value < upper:
            return name
    return None


def _mean(xs: list) -> float | None:
    return sum(xs) / len(xs) if xs else None


def _median(xs: list) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


def _entry_hour_utc(entry_time) -> float | None:
    if not isinstance(entry_time, str):
        return None
    try:
        dt = datetime.fromisoformat(entry_time)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return float(dt.astimezone(timezone.utc).hour)


def trade_keys(trade: dict) -> dict | None:
    """Bucket keys + drag for one dual-ledger trade record.

    Returns None when the trade lacks a finite drag_bps (not included
    in any slice). All fields defensive; never raises.
    """
    if not isinstance(trade, dict):
        return None
    drag_bps = trade.get("drag_bps")
    if not _finite(drag_bps):
        return None
    entry_px = trade.get("entry_px")
    stop_px = trade.get("stop_px")
    ach_entry_px = trade.get("ach_entry_px")
    vol_key = None
    if _finite(entry_px) and _finite(stop_px) and float(entry_px) > 0:
        vol_key = _bucket((float(entry_px) - float(stop_px))
                         / float(entry_px), VOL_BUCKETS)
    gap_key = None
    if (_finite(entry_px) and _finite(ach_entry_px)
            and float(entry_px) > 0):
        gap_key = _bucket(abs(float(entry_px) - float(ach_entry_px))
                          / float(entry_px) * BPS, GAP_BUCKETS)
    tod_key = _bucket(_entry_hour_utc(trade.get("entry_time")), TOD_BUCKETS)
    regime = trade.get("regime")
    regime_key = regime if isinstance(regime, str) and regime else None
    symbol = trade.get("symbol")
    return {
        "symbol": symbol if isinstance(symbol, str) else None,
        "drag_bps": float(drag_bps),
        "drag_r_4bps": (float(trade["drag_r_4bps"])
                        if _finite(trade.get("drag_r_4bps")) else None),
        "vol": vol_key, "tod": tod_key, "gap": gap_key,
        "regime": regime_key,
    }


def slice_drag(trades: list | None) -> dict:
    """Slice qualifying trades; rank qualifying buckets by mean drag_bps.

    Returns {"n_trades", "dimensions": {dim: {"ranked": [...],
    "insufficient_sample": [...]}}, "regime_available": bool}.
    Buckets with n < MIN_BUCKET_TRADES are never ranked.
    """
    keyed = []
    for t in (trades or []):
        k = trade_keys(t)
        if k is not None:
            keyed.append(k)
    dims: dict[str, dict[str, list]] = {
        "symbol": {}, "vol": {}, "tod": {}, "gap": {}, "regime": {},
    }
    for k in keyed:
        for dim in dims:
            name = k[dim]
            if name:
                dims[dim].setdefault(name, []).append(k)
    out_dims = {}
    for dim, buckets in dims.items():
        ranked, small = [], []
        for name in sorted(buckets):
            rows = buckets[name]
            drags = [r["drag_bps"] for r in rows]
            entry = {
                "bucket": name,
                "n": len(rows),
                "mean_drag_bps": _mean(drags),
                "median_drag_bps": _median(drags),
                "mean_drag_r_4bps": _mean(
                    [r["drag_r_4bps"] for r in rows
                     if r["drag_r_4bps"] is not None]),
            }
            if len(rows) >= MIN_BUCKET_TRADES:
                ranked.append(entry)
            else:
                entry["note"] = INSUFFICIENT_SAMPLE
                small.append(entry)
        ranked.sort(key=lambda e: e["mean_drag_bps"], reverse=True)
        out_dims[dim] = {"ranked": ranked, "insufficient_sample": small}
    return {
        "n_trades": len(keyed),
        "dimensions": out_dims,
        "regime_available": bool(dims["regime"]),
        "min_bucket_trades": MIN_BUCKET_TRADES,
    }


def top_drag_buckets(sliced: dict, limit: int = 10) -> list:
    """Headline answer: top qualifying buckets by mean drag_bps across
    all dimensions ('where a real-time feed would matter most')."""
    cands = []
    for dim, d in sliced.get("dimensions", {}).items():
        for e in d.get("ranked", []):
            cands.append({"dimension": dim, **e})
    cands.sort(key=lambda e: e["mean_drag_bps"], reverse=True)
    return cands[:limit]
