"""rs_top2 ranking support — SLICE 2.

Reference: pine_ranking.compute_features (R1) + RANKING_SPEC.md, adopted as
the locked rule: score = (Close[i]/Close[i-20] - 1) - SPY_ret, where SPY_ret
= bench_ret(spy_daily, t0, t1) with t0/t1 the symbol's own bar-i and
bar-(i-20) timestamps converted to UTC (last daily bar <= each timestamp,
no lookahead).

This module exposes the per-signal entry point the live path needs.
compute_features operates on research trade dicts; the live path operates
on signals. The two are pinned equal by
test_slice2.test_rs_score_matches_reference_on_all_candidates: if the
reference formula ever changes, that test fails loudly instead of drifting.

Ranking engages ONLY at contested timestamps (candidates > free slots,
after same-timestamp exits). Take top min(2, free_slots); ties broken by
deterministic candidate order (universe order, then signal time).
Uncontested timestamps take all (subject to the other gates in
portfolio.py, which applies the ranking cutoff inline exactly as the
reference simulate_stack does).
"""

from __future__ import annotations

import os
import sys

import numpy as np

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
_RANKING_DIR = os.path.join(_REPO_ROOT, "pine_ranking")
if _RANKING_DIR not in sys.path:
    sys.path.insert(0, _RANKING_DIR)
_SQ_DIR = os.path.join(_REPO_ROOT, "pine_signal_quality")
if _SQ_DIR not in sys.path:
    sys.path.insert(0, _SQ_DIR)

from pine_ranking import RS_LOOKBACK  # noqa: E402  (pre-registered constant, 20)
from pine_signal_quality import bench_ret  # noqa: E402  (canonical)

RANK_TOP_N = 2  # locked rule: top min(2, free_slots) at contested bars


def rs_score(df, signal_idx: int, spy_daily):
    """Reference-exact rs_score for one signal bar.

    df: 4H frame (tz-aware index) with a 'Close' column; signal_idx: bar i.
    spy_daily: daily SPY frame (UTC index, adjusted closes) or None.

    Returns (score, unavailable_reason). score is -inf when the SPY return
    is unavailable — and the reason is ALWAYS reported, never silent
    (parity spec A8).
    """
    i = int(signal_idx)
    sym_ret = float(df["Close"].iloc[i] / df["Close"].iloc[i - RS_LOOKBACK] - 1.0)
    t1 = df.index[i].tz_convert("UTC")
    t0 = df.index[i - RS_LOOKBACK].tz_convert("UTC")
    br = bench_ret(spy_daily, t0, t1) if spy_daily is not None else None
    if br is None or (isinstance(br, float) and np.isnan(br)):
        reason = ("spy_daily is None" if spy_daily is None
                  else "bench_ret returned None/NaN (no daily bar <= span)")
        return float("-inf"), reason
    return float(sym_ret - br), None


def order_contenders(contenders: list) -> list:
    """Deterministic contender order: higher rs_score first; ties broken by
    universe_order (then signal_id). Mirrors the reference's
    scored.sort(key=(-rs, candidate_index)) exactly: -inf scores sort last.
    Each contender is a dict with keys: rs_score, universe_order, signal_id.
    """
    return sorted(
        contenders,
        key=lambda c: (-c["rs_score"], c["universe_order"], c["signal_id"]),
    )


def rank_take_limit(n_candidates: int, free_slots: int) -> int | None:
    """How many may be taken by rank at this timestamp, or None if the bar
    is uncontested (ranking does not engage; all candidates proceed to the
    other gates). Contested <=> n_candidates > free_slots, evaluated after
    same-timestamp exits (parity spec A8)."""
    if n_candidates > free_slots:
        return min(RANK_TOP_N, free_slots)
    return None
