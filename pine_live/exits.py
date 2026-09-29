"""Slice-5 live exit evaluation — the canonical V3.6 exit logic as a pure function.

Paper-only. No trading, no alerts, no network. This module is PURE
computation over (position params, bars): it never touches portfolio
state, dedup, or alerts, and it cannot import them (see the slice-5
import-graph test). Exit evaluation therefore cannot retroactively alter
entry decisions — structurally, not just by convention.

Canonical source: the position-management block of
``pine_backtest.gen_pine_trades`` (mirrored by
``pine_ranking.gen_candidates``, the engine behind the locked C1 trades).
That logic lives INSIDE the reference's walk — there is no standalone
reference exit function to import, and ``pine_backtest.py`` is frozen (no
existing repo file outside ``pine_live/`` may be modified). So this module
is a character-faithful extraction of the per-bar manage block:

    TP1 arm:          hi >= tp1  ->  tp_hit = True   (50% filled at TP1)
    trailing runner:  runner = max(runner, close - atr*TRAIL_ATR) once armed
    exit triggers (close-evaluated, stop wins same-bar ties):
        close < runner                                -> "stop"
        close < e55                                    -> "ema55-break"
        e21 < e55 and close < e200                     -> "ema55-bear"
    exit fill: next bar's open; blended exit price =
        entry * (1 + r_blend * risk_frac), r_blend = 0.5*r1 + 0.5*r2
        (r1 = TP1 R if hit, else r2 alone) — exactly as the reference.

Every constant comes from ``pine_backtest`` by import (``TRAIL_ATR``);
entry/stop/tp1 are the reference-convention values carried by the live
position (next-bar-open entry, signal-close - 1.5*ATR stop,
entry + 2.0*ATR tp1 — asserted equal to the reference trade on every
research candidate by the slice-4 suite).

Parity proof: ``test_exit_walk_matches_reference_on_all_trades`` replays
the walk for every one of the 263 research-window reference trades and
requires the first trigger to reproduce (exit_time, exit price, reason,
tp1_hit, hold_bars) exactly. The walk is a pure function of
(entry, stop, tp1, bars) with no carried state, so a missed cycle cannot
corrupt it: the next cycle simply walks further.

Reference-behavior notes (pinned, not "fixed"):
- ``lo`` is unpacked but never read in the reference manage block; it is
  not read here either.
- The reference's ``else: exit at close`` terminal branch is unreachable:
  its walk runs ``while i < n - 1``, so ``i + 1 < n`` is always true at a
  trigger. It is kept here for the live edge (trigger on the last
  in-frame bar) with identical semantics.
- There is NO time-based (e.g. 30-bar) exit in the V3.6 reference. The
  30-bar max hold belongs to the V5.4 Mode-B exit — a different system.
  Adding one here would be a strategy change and would break the
  bit-identical differential proof, so there isn't one.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pine_backtest as pb  # noqa: E402  (TRAIL_ATR; _outcome used by replay)

EXIT_REASONS = ("stop", "ema55-break", "ema55-bear")

# Columns the walk reads from the indicator frame.
_WALK_COLS = ("Open", "High", "Low", "Close", "e21", "e55", "e200", "atr")
# Indicator columns that must not be NaN on a walked bar (fail closed).
_NAN_GUARDED = ("e21", "e55", "e200", "atr")


class ExitEvaluationError(Exception):
    """The exit walk cannot be evaluated: fail closed, never a wrong exit."""


def _blended_exit_px(entry_px: float, stop_px: float, tp1_px: float,
                     tp_hit: bool, fill_px: float):
    """Reference blended exit price. Identical op order to gen_pine_trades."""
    risk_frac = (entry_px - stop_px) / entry_px
    r1 = ((tp1_px - entry_px) / entry_px / risk_frac) if tp_hit else None
    r2 = (fill_px - entry_px) / entry_px / risk_frac
    r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
    exit_px = entry_px * (1.0 + r_blend * risk_frac)
    return float(exit_px), r1, float(r2), float(r_blend), float(risk_frac)


def evaluate_position_exit(*, symbol: str, entry_px: float, stop_px: float,
                           tp1_px: float, entry_idx: int, ind: pd.DataFrame,
                           eval_end_idx: int) -> dict:
    """Evaluate the canonical V3.6 exit walk for one position.

    Walks the reference manage block over bars
    ``[entry_idx, eval_end_idx]`` (both inclusive) of the indicator frame
    ``ind`` — the same bars the reference walk would have covered, in the
    same order, with the same operations. Pure: no state is read or
    written.

    Returns a dict. If ``triggered`` is True it carries the trigger bar,
    fill bar/price, reason, tp_hit, runner, the blended exit price and
    its R breakdown, and hold_bars (fill_idx - entry_idx, as the
    reference records it). If False it carries the final tp_hit/runner
    and the walked bar count. ``entry_bar_not_closed`` (entry_idx >
    eval_end_idx) is a normal case — the reference starts managing from
    the entry bar once it is completed — not an error.
    """
    symbol = str(symbol).upper()
    n = len(ind)
    entry_idx = int(entry_idx)
    eval_end_idx = int(eval_end_idx)
    base = {"symbol": symbol, "entry_idx": entry_idx,
            "eval_end_idx": eval_end_idx}
    if n == 0:
        raise ExitEvaluationError(f"{symbol}: empty indicator frame")
    if entry_idx < 0 or entry_idx >= n:
        raise ExitEvaluationError(
            f"{symbol}: entry_idx {entry_idx} out of range (n={n})")
    if eval_end_idx >= n:
        raise ExitEvaluationError(
            f"{symbol}: eval_end_idx {eval_end_idx} beyond frame (n={n})")
    if eval_end_idx < entry_idx:
        return {**base, "triggered": False, "note": "entry_bar_not_closed",
                "n_bars_walked": 0}
    missing = [c for c in _WALK_COLS if c not in ind.columns]
    if missing:
        raise ExitEvaluationError(
            f"{symbol}: indicator frame missing columns {missing}")

    entry_px = float(entry_px)
    stop_px = float(stop_px)
    tp1_px = float(tp1_px)
    tp_hit = False
    runner = stop_px
    for i in range(entry_idx, eval_end_idx + 1):
        bar = ind.iloc[i]
        for col in _NAN_GUARDED:
            if pd.isna(bar[col]):
                raise ExitEvaluationError(
                    f"{symbol}: NaN indicator {col} at bar "
                    f"{ind.index[i].isoformat()}; fail closed "
                    "(forward-fill is forbidden)")
        hi = float(bar["High"])
        close = float(bar["Close"])
        # ---- the reference manage block, verbatim semantics ----
        if not tp_hit and hi >= tp1_px:
            tp_hit = True                      # 50% filled at the TP1 limit
        if tp_hit:
            runner = max(runner, close - float(bar["atr"]) * pb.TRAIL_ATR)
        trend_bear = bar["e21"] < bar["e55"] and close < bar["e200"]
        reason = None
        if close < runner:
            reason = "stop"                     # stop wins same-bar ties
        elif close < bar["e55"] or trend_bear:
            reason = "ema55-bear" if trend_bear else "ema55-break"
        # --------------------------------------------------------
        if reason is not None:
            if i + 1 < n:
                fill_px = float(ind["Open"].iloc[i + 1])
                fill_idx = i + 1
            else:
                # Live edge only: unreachable in the reference walk
                # (``while i < n - 1``), identical semantics kept.
                fill_px = close
                fill_idx = i
            exit_px, r1, r2, r_blend, risk_frac = _blended_exit_px(
                entry_px, stop_px, tp1_px, tp_hit, fill_px)
            return {
                **base, "triggered": True,
                "trigger_idx": i,
                "trigger_bar_time": ind.index[i].isoformat(),
                "fill_idx": fill_idx,
                "fill_bar_time": ind.index[fill_idx].isoformat(),
                "fill_px": float(fill_px),
                "reason": reason,
                "tp1_hit": bool(tp_hit),
                "runner_at_trigger": float(runner),
                "r1": (float(r1) if r1 is not None else None),
                "r2": r2, "r_blend": r_blend, "risk_frac": risk_frac,
                "exit_px": exit_px,
                "hold_bars": int(fill_idx - entry_idx),
                "n_bars_walked": int(i - entry_idx + 1),
            }
    return {**base, "triggered": False, "tp_hit": bool(tp_hit),
            "runner": float(runner),
            "n_bars_walked": int(eval_end_idx - entry_idx + 1)}
