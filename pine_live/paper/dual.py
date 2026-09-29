"""Dual-ledger execution measurement: achievable vs canonical fills.

Instrumentation ONLY. Nothing here touches strategy, entries, exits,
ranking, parameters, or any frozen module: it only READS pinned packet
data and recomputes P&L under a different fill-price assumption. The
canonical paper path is byte-for-byte unchanged.

The problem being measured: the paper runner detects 4H signals only
after the signal bar closes (the frozen yfinance path excludes the
forming bar), but the frozen backtest assumes fills at the next bar's
OPEN -- a price that is invisible at detection time. This module makes
that gap an explicit, per-trade measurement instead of an assumption.

Fill definitions (frozen for the paper phase):
  CANONICAL (existing behavior, unchanged):
      entry: next bar's OPEN after the signal bar (the backtest assumption)
      exit:  next bar's OPEN after the exit-trigger bar, blended 50/50
             with the TP1 leg exactly as the reference does
  ACHIEVABLE (new measurement leg):
      entry: the CLOSE of the signal bar -- the last visible price when
             the runner's cycle detects the signal. Pinned in the signal
             packet as signal_bar_ohlcv.close (NOT re-read from a fresh
             download, which could restate history under auto_adjust).
      exit:  the CLOSE of the exit-trigger bar -- the last visible price
             when the exit trigger is detected. Pinned in the exit walk's
             hash-pinned bar snapshot.

The achievable TRADE re-anchors the position geometry to the achievable
entry, exactly as the reference conventions define each level relative
to the actual fill:
  - stop: the pinned stop_px, UNCHANGED. The strategy defines the stop as
    signal-close minus 1.5*ATR and the achievable entry IS the signal
    close, so the pinned stop is already consistent with it.
  - tp1: re-anchored to the achievable entry:
    ach_tp1 = ach_entry + (pinned_tp1 - pinned_entry), preserving the
    reference "tp1 = entry + 2.0*ATR" relationship.
  - exit: the canonical blended-exit formula (_blended_exit_px, imported
    -- the formula itself is untouched) with the exit fill leg replaced
    by the trigger-bar close. tp_hit and the trigger bar come from the
    canonical walk: this measures fill-price difference, it does NOT
    re-simulate the trade path (no alternate trigger bars, no
    re-decisions, no slot/risk-gate replay).
  - R: pb._outcome at both cost legs (4bps, 25bps), same as canonical.

Per-trade drag (positive = achievable WORSE than canonical):
  drag_r   = canonical net R - achievable net R        (per cost leg)
  drag_bps = drag_r_4bps * risk_dollars / size * 10000,
             where size is the canonical notional dollars
             (size = risk_dollars / risk_frac, so dollar P&L = R * size *
             risk_frac consistently). I.e. the dollar drag as basis points
             of canonical trade notional -- the same-risk-dollar
             comparison the production gate's 108bps headroom is stated
             in. (The 108bps headroom is the 25bps-leg expectancy, 0.280R,
             expressed as bps of average notional.)

All helpers are pure and return None (never raise) when an input is
missing, non-finite, or geometrically invalid -- the caller logs loudly
and records nulls. Instrumentation must never break the canonical
wake-up, so callers additionally guard these calls.

ACHIEVABLE-FILL POLICY (swappable; current value below): the achievable
ledger's fill source is a named policy, not a fact about the market.
  Current policy: "signal-bar-close-at-detection" -- the CLOSE of the
  signal bar (entries) / the CLOSE of the exit-trigger bar (exits),
  i.e. the last visible price when THIS architecture (hourly yfinance
  polling, which never sees the forming bar) can act. This is the honest
  conservative proxy for what the current architecture can do today.
  Future policy, when a real-time feed lands: "first-actionable-quote" --
  the first actually actionable quote after the signal becomes knowable.
  Upgrading the policy is an execution-architecture change: it changes
  what the achievable ledger measures, never strategy, entries, exits,
  ranking, or parameters. Gate thresholds are policy-independent and do
  not change with the policy.
If the achievable ledger ever fails the production gate while the
canonical leg holds, the investigation goes to data timing and the
execution architecture -- V3.6 stays frozen; no strategy changes.
"""

from __future__ import annotations

import json
import math
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pine_backtest as pb  # noqa: E402  (frozen params + _outcome)
from pine_live.exits import _blended_exit_px  # noqa: E402  (canonical blend)

ACHIEVABLE_FILL_POLICY = "signal-bar-close-at-detection"
"""Current achievable-fill policy (see module docstring). Swappable:
"first-actionable-quote" once a real-time feed exists."""

COST_4BPS = pb.COSTS["4bps"]
COST_25BPS = pb.COSTS["25bps"]
BPS = 10000.0


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def _pos(x) -> bool:
    return _finite(x) and float(x) > 0


def achievable_entry_px(signal_packet: dict | None) -> float | None:
    """Achievable entry fill: CLOSE of the signal bar, from the pinned
    signal packet. None when the packet/field is missing or invalid."""
    if not isinstance(signal_packet, dict):
        return None
    try:
        px = signal_packet["signal_bar_ohlcv"]["close"]
    except (KeyError, TypeError):
        return None
    return float(px) if _pos(px) else None


def achievable_trigger_close(exit_packet: dict | None) -> float | None:
    """Achievable exit fill leg: CLOSE of the exit-trigger bar, from the
    exit packet's hash-pinned bar snapshot. None when the packet,
    snapshot, or trigger bar is missing/invalid."""
    if not isinstance(exit_packet, dict):
        return None
    try:
        trig_t = exit_packet["trigger"]["trigger_bar_time"]
        snap_path = exit_packet["bars_snapshot_ref"]["path"]
    except (KeyError, TypeError):
        return None
    if not isinstance(trig_t, str) or not isinstance(snap_path, str):
        return None
    try:
        with open(snap_path, encoding="utf-8") as f:
            snap = json.load(f)
    except (OSError, ValueError):
        return None
    bars = snap.get("bars") if isinstance(snap, dict) else None
    if not isinstance(bars, list):
        return None
    for bar in bars:
        if isinstance(bar, dict) and bar.get("t") == trig_t:
            c = bar.get("c")
            return float(c) if _pos(c) else None
    return None


def achievable_trade(*, entry_px: float, stop_px: float, tp1_px: float,
                     tp_hit: bool, ach_entry_px: float,
                     ach_exit_fill_px: float) -> dict | None:
    """Achievable-leg outcome for one closed trade.

    Inputs are the pinned canonical position fields (entry_px, stop_px,
    tp1_px, tp_hit) plus the two achievable fill prices. Returns the
    achievable exit price, re-anchored TP1, and R at both cost legs --
    or None when the inputs are unusable.
    """
    for v in (entry_px, stop_px, tp1_px, ach_entry_px, ach_exit_fill_px):
        if not _finite(v):
            return None
    entry_px, stop_px, tp1_px = float(entry_px), float(stop_px), float(tp1_px)
    ach_entry_px, ach_exit_fill_px = float(ach_entry_px), float(ach_exit_fill_px)
    if not (entry_px > stop_px > 0):
        return None
    if not (ach_entry_px > stop_px > 0 and ach_exit_fill_px > 0):
        return None
    # Re-anchor TP1 to the achievable entry (reference: tp1 = entry + 2*ATR).
    ach_tp1_px = ach_entry_px + (tp1_px - entry_px)
    if not ach_tp1_px > ach_entry_px:
        return None
    ach_exit_px, r1, r2, r_blend, risk_frac = _blended_exit_px(
        ach_entry_px, stop_px, ach_tp1_px, bool(tp_hit), ach_exit_fill_px)
    if not _pos(ach_exit_px):
        return None
    _, ach_gross_r, ach_net_r_4bps, _ = pb._outcome(
        ach_entry_px, stop_px, ach_exit_px, COST_4BPS)
    _, _, ach_net_r_25bps, _ = pb._outcome(
        ach_entry_px, stop_px, ach_exit_px, COST_25BPS)
    return {
        "ach_entry_px": ach_entry_px,
        "ach_tp1_px": ach_tp1_px,
        "ach_exit_fill_px": ach_exit_fill_px,
        "ach_exit_px": ach_exit_px,
        "ach_r1": (float(r1) if r1 is not None else None),
        "ach_r2": float(r2),
        "ach_r_blend": float(r_blend),
        "ach_gross_r": float(ach_gross_r),
        "ach_net_r_4bps": float(ach_net_r_4bps),
        "ach_net_r_25bps": float(ach_net_r_25bps),
    }


def trade_drag(*, net_r_4bps: float, net_r_25bps: float,
               ach_net_r_4bps: float, ach_net_r_25bps: float,
               risk_dollars: float, size: float,
               entry_px: float) -> dict | None:
    """Achievable-vs-canonical drag for one trade.

    Positive drag = achievable WORSE (a cost); negative = achievable
    better (e.g. gap-up at entry for a long). drag_bps is the 4bps-leg R
    drag converted to basis points of canonical trade notional
    (``size`` is already notional dollars: size = risk_dollars /
    risk_frac). R figures are per intended risk dollar on both legs, so
    this is a same-risk-dollar comparison.
    """
    vals = (net_r_4bps, net_r_25bps, ach_net_r_4bps, ach_net_r_25bps,
            risk_dollars, size, entry_px)
    if any(not _finite(v) for v in vals):
        return None
    risk_dollars, size, entry_px = (float(risk_dollars), float(size),
                                   float(entry_px))
    if not (risk_dollars > 0 and size > 0 and entry_px > 0):
        return None
    drag_r_4bps = float(net_r_4bps) - float(ach_net_r_4bps)
    drag_r_25bps = float(net_r_25bps) - float(ach_net_r_25bps)
    drag_bps = drag_r_4bps * risk_dollars / size * BPS
    return {
        "drag_r_4bps": drag_r_4bps,
        "drag_r_25bps": drag_r_25bps,
        "drag_bps": drag_bps,
    }


def round_trip_price_drag_bps(*, entry_px: float, ach_entry_px: float,
                              exit_px: float,
                              ach_exit_px: float) -> float | None:
    """Pure price-based cross-check: the entry-leg plus exit-leg price
    differences as bps of canonical notional, for a long: paying more at
    entry or receiving less at exit is positive drag.

    Exactly equals trade_drag()['drag_bps'] when both legs share the same
    risk_frac (no entry gap -- then R is a pure price multiple). When the
    entry gap moves risk_frac, the R-based drag additionally reflects the
    changed gearing at constant risk dollars, and the two differ by that
    gearing effect (this is expected, not an error).
    """
    vals = (entry_px, ach_entry_px, exit_px, ach_exit_px)
    if any(not _pos(v) for v in vals):
        return None
    entry_px = float(entry_px)
    price_drag = ((float(ach_entry_px) - entry_px)
                  + (float(exit_px) - float(ach_exit_px))) / entry_px
    return price_drag * BPS
