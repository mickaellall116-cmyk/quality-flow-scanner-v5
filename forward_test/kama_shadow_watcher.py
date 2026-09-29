#!/usr/bin/env python3
"""Passive KAMA shadow logger for live V5.4 Quality Flow signals.

This file never changes V5.4 decisions. It reads the published forward-test
state, finds new signal IDs after the frozen shadow start, computes the frozen
KAMA20/KAMA40 state, and publishes a separate shadow snapshot.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scanner_rules import resample_closed_4h as production_resample_closed_4h  # noqa: E402

START_AT = pd.Timestamp("2026-09-28T13:46:00Z")
WARMUP = 215
PRIMARY_TARGET = 100
CHECKPOINT = 50
DOWNLOAD_PERIOD = "729d"

FORWARD_DIR = REPO_ROOT / "forward_test"
STATUS_PATH = FORWARD_DIR / "v54_status.json"
OBSERVER_PATH = FORWARD_DIR / "v54_ai_observer.json"
CLOSED_PATH = FORWARD_DIR / "v54_closed_trades.json"
SHADOW_PATH = FORWARD_DIR / "kama_shadow.json"

_SIGNAL_RE = re.compile(r"^v54:([^:]+):4h:(.+):\d{4}-\d{2}-\d{2}-v54$")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            x = json.load(f)
        return x if isinstance(x, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _signal_time_from_id(signal_id: str) -> str | None:
    m = _SIGNAL_RE.match(str(signal_id))
    return m.group(2) if m else None


def _as_utc(ts) -> pd.Timestamp | None:
    try:
        x = pd.Timestamp(ts)
        if x.tzinfo is None:
            x = x.tz_localize("America/New_York")
        return x.tz_convert("UTC")
    except Exception:
        return None


def collect_live_signals() -> dict[str, dict]:
    """Union all visible V5.4 signal sources; dedupe by signal_id."""
    out: dict[str, dict] = {}

    observer = _load(OBSERVER_PATH)
    for a in observer.get("assessments", []) or []:
        sid = str(a.get("signal_id") or "")
        if not sid:
            continue
        f = a.get("features") or {}
        out[sid] = {
            "signal_id": sid,
            "symbol": str(f.get("symbol") or a.get("symbol") or ""),
            "signal_time": (
                f.get("signal_bar_close_at")
                or f.get("signal_time")
                or _signal_time_from_id(sid)
            ),
            "source": "v54_ai_observer",
        }

    status = _load(STATUS_PATH)
    for p in status.get("pending_entries", []) or []:
        sid = str(p.get("signal_id") or "")
        if sid:
            out.setdefault(sid, {
                "signal_id": sid,
                "symbol": str(p.get("symbol") or ""),
                "signal_time": p.get("signal_bar") or _signal_time_from_id(sid),
                "source": "v54_status_pending",
            })
    for p in status.get("open_positions", []) or []:
        sid = str(p.get("signal_id") or "")
        if sid:
            out.setdefault(sid, {
                "signal_id": sid,
                "symbol": str(p.get("symbol") or ""),
                "signal_time": _signal_time_from_id(sid),
                "source": "v54_status_open",
            })

    closed = _load(CLOSED_PATH)
    for t in closed.get("trades", []) or []:
        sid = str(t.get("signal_id") or "")
        if sid:
            out.setdefault(sid, {
                "signal_id": sid,
                "symbol": str(t.get("symbol") or ""),
                "signal_time": t.get("signal_time") or _signal_time_from_id(sid),
                "source": "v54_closed_trades",
            })
    return out


def closed_outcomes() -> dict[str, dict]:
    closed = _load(CLOSED_PATH)
    out = {}
    for t in closed.get("trades", []) or []:
        sid = str(t.get("signal_id") or "")
        if not sid:
            continue
        out[sid] = {
            "resolved": True,
            "blended_r": t.get("blended_r"),
            "exit_reason": t.get("exit_reason"),
            "exit_bar": t.get("exit_bar"),
            "bars_held": t.get("bars_held"),
            "tp1_taken": t.get("tp1_taken"),
            "mfe_r": t.get("mfe_r"),
            "mae_r": t.get("mae_r"),
        }
    return out


def download_1h(symbol: str) -> pd.DataFrame:
    df = yf.download(
        symbol,
        interval="1h",
        period=DOWNLOAD_PERIOD,
        progress=False,
        auto_adjust=True,
        threads=False,
    )
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    need = ["Open", "High", "Low", "Close", "Volume"]
    if any(c not in df.columns for c in need):
        return pd.DataFrame()
    return df[need].dropna().sort_index()


def session_aligned_4h(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Exact DST-safe research grid: 09:30-13:30 and 13:30-16:00 ET."""
    if df.empty:
        return df.copy()
    x = df.copy().sort_index()
    if not isinstance(x.index, pd.DatetimeIndex):
        return pd.DataFrame()

    if symbol.upper().endswith("-USD"):
        return x.resample("4h", origin="start_day", label="left", closed="left").agg({
            "Open": "first", "High": "max", "Low": "min",
            "Close": "last", "Volume": "sum",
        }).dropna(subset=["Open", "High", "Low", "Close"])

    idx = x.index
    if idx.tz is None:
        idx = idx.tz_localize("America/New_York")
    else:
        idx = idx.tz_convert("America/New_York")
    x.index = idx
    mins = idx.hour * 60 + idx.minute
    x = x[(mins >= 570) & (mins < 960)].copy()
    if x.empty:
        return x

    rows = []
    for day, g in x.groupby(x.index.normalize(), sort=True):
        gm = g.index.hour * 60 + g.index.minute
        for start_min, end_min in ((570, 810), (810, 960)):
            b = g[(gm >= start_min) & (gm < end_min)]
            if b.empty:
                continue
            label = pd.Timestamp(day).replace(hour=start_min // 60, minute=start_min % 60)
            rows.append({
                "idx": label,
                "Open": float(b["Open"].iloc[0]),
                "High": float(b["High"].max()),
                "Low": float(b["Low"].min()),
                "Close": float(b["Close"].iloc[-1]),
                "Volume": float(b["Volume"].sum()),
            })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("idx").sort_index()


def tested_bar_close(start: pd.Timestamp, symbol: str) -> pd.Timestamp:
    s = pd.Timestamp(start)
    if symbol.upper().endswith("-USD"):
        return s + pd.Timedelta(hours=4)
    if s.tzinfo is None:
        s = s.tz_localize("America/New_York")
    else:
        s = s.tz_convert("America/New_York")
    close = s + pd.Timedelta(hours=4)
    session_close = s.normalize() + pd.Timedelta(hours=16)
    return min(close, session_close)


def kama(s: pd.Series, er_length: int, fast: int = 2, slow: int = 30) -> pd.Series:
    """Frozen tournament definition."""
    n = int(er_length)
    s = s.astype(float)
    change = (s - s.shift(n)).abs()
    volatility = s.diff().abs().rolling(n).sum()
    er = (change / volatility.replace(0.0, np.nan)).fillna(0.0)
    fast_sc = 2.0 / (fast + 1.0)
    slow_sc = 2.0 / (slow + 1.0)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    out = pd.Series(np.nan, index=s.index, dtype=float)
    vals = s.to_numpy(dtype=float)
    scv = sc.to_numpy(dtype=float)
    first = None
    for i, v in enumerate(vals):
        if np.isfinite(v):
            first = i
            out.iloc[i] = v
            break
    if first is None:
        return out
    prev = float(out.iloc[first])
    for i in range(first + 1, len(s)):
        v = vals[i]
        if not np.isfinite(v):
            out.iloc[i] = prev
            continue
        a = scv[i] if np.isfinite(scv[i]) else slow_sc ** 2
        prev = prev + a * (v - prev)
        out.iloc[i] = prev
    return out


def _state_from_bars(bars: pd.DataFrame, decision_time: pd.Timestamp, symbol: str, tested_grid: bool) -> dict:
    if bars is None or bars.empty:
        return {"valid": False, "reason": "no_bars"}

    dt = pd.Timestamp(decision_time)
    if dt.tzinfo is None:
        dt = dt.tz_localize("America/New_York")
    else:
        dt = dt.tz_convert("America/New_York")

    if tested_grid:
        keep = [tested_bar_close(ts, symbol) <= dt for ts in bars.index]
        b = bars.loc[np.asarray(keep, dtype=bool)].copy()
    else:
        # production_resample_closed_4h(..., now=decision_time) already drops
        # the active bar; all returned bars are observable.
        b = bars.copy()

    if len(b) < WARMUP:
        return {"valid": False, "reason": "warmup", "bars": int(len(b))}
    k20 = kama(b["Close"], 20, 2, 30)
    k40 = kama(b["Close"], 40, 2, 30)
    a = float(k20.iloc[-1])
    z = float(k40.iloc[-1])
    if not np.isfinite(a) or not np.isfinite(z):
        return {"valid": False, "reason": "nonfinite", "bars": int(len(b))}
    return {
        "valid": True,
        "bars": int(len(b)),
        "bar_start": pd.Timestamp(b.index[-1]).isoformat(),
        "kama20": a,
        "kama40": z,
        "bull": bool(a > z),
        "gap_pct_of_kama40": float((a / z - 1.0) * 100.0) if z else None,
    }


def evaluate_signal(symbol: str, signal_time: str) -> dict:
    raw = download_1h(symbol)
    if raw.empty:
        return {
            "tested_session_state": {"valid": False, "reason": "download"},
            "live_grid_state": {"valid": False, "reason": "download"},
        }

    dt = pd.Timestamp(signal_time)
    if dt.tzinfo is None:
        dt = dt.tz_localize("America/New_York")

    tested = session_aligned_4h(raw, symbol)
    try:
        live = production_resample_closed_4h(raw, symbol, now=dt)
    except Exception as exc:
        live = pd.DataFrame()
        live_error = type(exc).__name__
    else:
        live_error = None

    live_state = _state_from_bars(live, dt, symbol, tested_grid=False)
    if live_error and not live_state.get("valid"):
        live_state["reason"] = f"production_grid_{live_error}"

    return {
        "tested_session_state": _state_from_bars(tested, dt, symbol, tested_grid=True),
        "live_grid_state": live_state,
    }


def signal_hash(event: dict) -> str:
    frozen = {
        "signal_id": event.get("signal_id"),
        "symbol": event.get("symbol"),
        "signal_time": event.get("signal_time"),
        "tested_session_state": event.get("tested_session_state"),
        "live_grid_state": event.get("live_grid_state"),
    }
    return hashlib.sha256(json.dumps(frozen, sort_keys=True).encode("utf-8")).hexdigest()


def main() -> dict:
    snapshot = _load(SHADOW_PATH)
    prior_events = snapshot.get("events", []) if isinstance(snapshot.get("events"), list) else []
    by_id = {str(e.get("signal_id")): e for e in prior_events if e.get("signal_id")}

    visible = collect_live_signals()
    new_ids = []
    errors = []

    for sid, s in visible.items():
        st = _as_utc(s.get("signal_time"))
        if st is None or st < START_AT:
            continue
        if sid in by_id:
            continue
        symbol = str(s.get("symbol") or "")
        if not symbol:
            errors.append({"signal_id": sid, "error": "missing_symbol"})
            continue
        try:
            states = evaluate_signal(symbol, str(s["signal_time"]))
        except Exception as exc:
            errors.append({"signal_id": sid, "symbol": symbol, "error": type(exc).__name__})
            continue
        event = {
            "signal_id": sid,
            "symbol": symbol,
            "signal_time": str(s["signal_time"]),
            "first_logged_at": _utcnow(),
            "source": s.get("source"),
            **states,
            "outcome": {"resolved": False},
        }
        event["signal_record_sha256"] = signal_hash(event)
        by_id[sid] = event
        new_ids.append(sid)

    # Outcome enrichment is separate from immutable signal-time fields.
    outcomes = closed_outcomes()
    for sid, e in by_id.items():
        if sid in outcomes:
            e["outcome"] = outcomes[sid]

    events = sorted(
        by_id.values(),
        key=lambda e: (_as_utc(e.get("signal_time")) or pd.Timestamp.max.tz_localize("UTC"), str(e.get("signal_id"))),
    )

    old_cohort = snapshot.get("primary_cohort_signal_ids")
    cohort = list(old_cohort) if isinstance(old_cohort, list) and len(old_cohort) == PRIMARY_TARGET else None
    frozen_at = snapshot.get("primary_cohort_frozen_at")
    if cohort is None and len(events) >= PRIMARY_TARGET:
        cohort = [e["signal_id"] for e in events[:PRIMARY_TARGET]]
        frozen_at = _utcnow()

    cohort_set = set(cohort or [])
    resolved = sum(
        1 for e in events
        if e.get("signal_id") in cohort_set and (e.get("outcome") or {}).get("resolved") is True
    )

    out = {
        "protocol": "KAMA_SHADOW_PROTOCOL.md",
        "updated_at": _utcnow(),
        "start_at": START_AT.isoformat(),
        "review_target_signals": PRIMARY_TARGET,
        "data_quality_checkpoint": CHECKPOINT,
        "signal_count": len(events),
        "checkpoint_50_reached": len(events) >= CHECKPOINT,
        "primary_cohort_signal_ids": cohort,
        "primary_cohort_frozen_at": frozen_at,
        "primary_cohort_resolved": resolved,
        "review_ready": bool(cohort is not None and resolved == PRIMARY_TARGET),
        "new_signal_ids_this_run": new_ids,
        "errors_this_run": errors,
        "events": events,
    }
    with SHADOW_PATH.open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    return out


if __name__ == "__main__":
    result = main()
    print(json.dumps({
        "signal_count": result["signal_count"],
        "new_signal_ids_this_run": result["new_signal_ids_this_run"],
        "primary_cohort_resolved": result["primary_cohort_resolved"],
        "review_ready": result["review_ready"],
        "errors_this_run": result["errors_this_run"],
    }, indent=2))
