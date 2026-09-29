"""Shadow hold/sell advisor — pure classification + counterfactual math.

OBSERVATION ONLY. This module is research instrumentation for the Pine
V3.6 paper phase. It NEVER affects paper positions, fills, runner
decisions, gate thresholds, or alerts. It imports no order-placement,
alert-sending, or state-mutating capability; the only frozen import is
``pine_backtest._outcome`` (the canonical R definition, same as the
dual-ledger module uses). It never writes to ``pine_live/paper_state/``.

The deterministic rules implemented here are pre-registered in
``SHADOW_ADVISOR_SPEC.md``. Rule ids EC1..W2 below map 1:1 to that
document; precedence is EXIT-CANDIDATE > PROTECT > WEAKENING > HOLD.
"""

from __future__ import annotations

import math

import pine_backtest as pb  # noqa: E402  (frozen R definition only)

LABELS = ("HOLD", "PROTECT", "WEAKENING", "EXIT-CANDIDATE")
SENTINEL_INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

# Pre-registered advisor constants (frozen in SHADOW_ADVISOR_SPEC.md).
# These are research-only calibration; changing them requires a spec edit
# and can never alter paper behavior.
EC_R_NOW = -0.75
EC_STALE_BARS = 60
EC_STALE_R = 0.25
EC_NEARDEATH_MAE = -0.90
P_R_NOW = 1.50
P_PEAK_R = 2.00
P_GIVEBACK_R = 1.00
W_STALE_BARS = 20
W_STALE_R = 0.25
W_MAE = -0.50
W_R_NOW = 0.50

RULE_IDS = ("EC1", "EC2", "EC3", "P1", "P2", "W1", "W2")

COST_4BPS = pb.COSTS["4bps"]
COST_25BPS = pb.COSTS["25bps"]


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def compute_inputs(position: dict | None, bars: list | None) -> dict | None:
    """Build the spec's rule inputs from a paper position + 4H bars.

    ``position``: paper portfolio position (entry_px, stop_px required).
    ``bars``: ascending list of {"t": iso, "c": close} with t > entry_time.
    Returns the inputs dict, or None when inputs cannot be built
    (caller logs INSUFFICIENT_DATA).
    """
    if not isinstance(position, dict) or not bars:
        return None
    entry_px = position.get("entry_px")
    stop_px = position.get("stop_px")
    if not (_finite(entry_px) and _finite(stop_px)):
        return None
    entry_px, stop_px = float(entry_px), float(stop_px)
    risk = entry_px - stop_px
    if not risk > 0:
        return None
    closes = []
    last_t = None
    for b in bars:
        if not isinstance(b, dict):
            return None
        c, t = b.get("c"), b.get("t")
        if not _finite(c) or not isinstance(t, str):
            return None
        closes.append(float(c))
        last_t = t
    if not closes:
        return None
    r_series = [(c - entry_px) / risk for c in closes]
    r_now = r_series[-1]
    return {
        "r_now": r_now,
        "dist_to_stop_frac": (closes[-1] - stop_px) / risk,
        "mae_r": min(0.0, min(r_series)),
        "mfe_r": max(0.0, max(r_series)),
        "bars_held": len(closes),
        "bar_time": last_t,
    }


def classify(inputs: dict | None) -> tuple[str, str | None]:
    """Deterministic (label, rule_id) for the spec's rule inputs.

    None inputs -> (INSUFFICIENT_DATA, None). Otherwise exactly one of
    the four labels, with the firing rule's id (HOLD -> None).
    """
    if not isinstance(inputs, dict):
        return SENTINEL_INSUFFICIENT_DATA, None
    try:
        r_now = float(inputs["r_now"])
        mae_r = float(inputs["mae_r"])
        mfe_r = float(inputs["mfe_r"])
        bars_held = int(inputs["bars_held"])
    except (KeyError, TypeError, ValueError):
        return SENTINEL_INSUFFICIENT_DATA, None
    if not all(map(math.isfinite, (r_now, mae_r, mfe_r))) or bars_held < 0:
        return SENTINEL_INSUFFICIENT_DATA, None

    # EXIT-CANDIDATE (highest precedence)
    if r_now <= EC_R_NOW:
        return "EXIT-CANDIDATE", "EC1"
    if bars_held >= EC_STALE_BARS and r_now < EC_STALE_R:
        return "EXIT-CANDIDATE", "EC2"
    if mae_r <= EC_NEARDEATH_MAE and r_now < 0.0:
        return "EXIT-CANDIDATE", "EC3"
    # PROTECT
    if r_now >= P_R_NOW:
        return "PROTECT", "P1"
    if mfe_r >= P_PEAK_R and (mfe_r - r_now) >= P_GIVEBACK_R:
        return "PROTECT", "P2"
    # WEAKENING
    if bars_held >= W_STALE_BARS and r_now < W_STALE_R:
        return "WEAKENING", "W1"
    if mae_r <= W_MAE and r_now < W_R_NOW:
        return "WEAKENING", "W2"
    return "HOLD", None


def hypothetical_exit_r(*, entry_px: float, stop_px: float,
                        next_open_px: float) -> dict | None:
    """HYPOTHETICAL R of a full exit at ``next_open_px``.

    Pure math for the counterfactual: "what if the whole position had
    been sold at the next bar's open." Returns net R at both cost legs,
    or None on invalid input. Every consumer must label the result
    HYPOTHETICAL.
    """
    for v in (entry_px, stop_px, next_open_px):
        if not _finite(v):
            return None
    entry_px, stop_px, next_open_px = (float(entry_px), float(stop_px),
                                      float(next_open_px))
    if not (entry_px > stop_px > 0 and next_open_px > 0):
        return None
    _, hyp_gross_r, hyp_net_r_4bps, _ = pb._outcome(
        entry_px, stop_px, next_open_px, COST_4BPS)
    _, _, hyp_net_r_25bps, _ = pb._outcome(
        entry_px, stop_px, next_open_px, COST_25BPS)
    return {
        "hypothetical_gross_r": float(hyp_gross_r),
        "hypothetical_net_r_4bps": float(hyp_net_r_4bps),
        "hypothetical_net_r_25bps": float(hyp_net_r_25bps),
    }
