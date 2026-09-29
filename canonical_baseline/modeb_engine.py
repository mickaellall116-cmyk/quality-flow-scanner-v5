"""Canonical Mode B execution engine — exact rebuild of the live tracker.

Ground truth: ``v54_exit_tracker.py`` (``ModeBTracker``), driven live by
``v54_forward_harness.py``. Frozen spec: ``v54_spec.md`` section 3
("Exit — FROZEN (Mode B)", locked 2026-09-15).

This is a FRESH implementation. It is NOT derived from ``pine_backtest.py``'s
exit logic, which models V3.6 close-evaluated strategy semantics and implements
zero Mode B features (no resting stop, no Profit Protect, no stop-wins-ties,
no 30-bar timeout — see
``research_audit/execution/EXECUTION_AUDIT_REPORT.md``).

Bar conventions (match live exactly):
- Entry fills at the NEXT 4H bar's OPEN after the signal bar
  (``v54_forward_harness.py:156``:
  ``tracker.open_position(snap, float(newbars.iloc[0]["Open"]), ts.isoformat())``
  where ``newbars = df[df.index > signal_bar_start]`` — the first completed
  bar after the signal bar).
- The entry bar is the FIRST processed bar and counts as bar #1 of the 30-bar
  clock (``v54_forward_harness.py:173``: ``df[df.index >= entry_bar]`` for
  newly opened positions; ``v54_exit_tracker.py:127``: ``bars_held += 1`` at
  the top of ``process_bar``).
- The 30-bar timeout exits at the CLOSE of the 30th processed bar
  (``v54_exit_tracker.py:178-183``).

Fill assumptions — PRIMARY is live-faithful (``realistic_gaps=False``):
- Resting stop fills at the EXACT stop price — including when the bar gaps
  through it (``v54_exit_tracker.py:151-152`` full position,
  ``v54_exit_tracker.py:169-170`` runner). Optimistic vs a real stop-market
  order; see the ``realistic_gaps=True`` variant below and ENGINE.md.
- TP1 limit fills at the EXACT TP1 price even when the bar opens above it
  (``v54_exit_tracker.py:157-162``: ``pos["tp1_r"] = _r_of(tp1, ...)`` — the
  partial credit is always computed at the tp1 level). Conservative vs a real
  limit order, which would fill at the better open.
- Profit Protect fills at the NEXT bar's OPEN, exact price
  (``v54_exit_tracker.py:141-147``), with the pending-exit fill taking
  precedence over any stop/TP1/EXIT evaluation on the fill bar.
- Scanner EXIT is evaluated only on the bar's ``scanner_state`` and only
  counts when Profit Protect is already armed; an EXIT signal sets a pending
  exit that fills at the next bar's open (``v54_exit_tracker.py:165-167``
  full, ``171-174`` runner).
- Same-bar stop/TP1 conflict: STOP WINS
  (``v54_exit_tracker.py:150`` checks ``lo <= stop`` before
  ``v54_exit_tracker.py:153`` checks ``hi >= tp1``).
- No stop/exit evaluation on the bar TP1 is taken (after the TP1 branch the
  live code falls through to the timeout check only —
  ``v54_exit_tracker.py:164`` "Research: continue").
- The structural stop NEVER moves (no breakeven, no trail).
  The runner keeps the structural stop (``v54_spec.md`` §3, frozen).
- Zero slippage everywhere (matches live).

``realistic_gaps=True`` variant (documented alternative, NOT live behavior):
- Gap-through-stop (bar open at/below the stop): stop-market fills at the
  bar's OPEN, the first tradable price beyond the stop.
- Intrabar stop touch (open above the stop, low at/below it): fills at the
  stop price (resting stop, no slippage).
- Gap-through-TP1 (bar open at/above TP1): limit fills at the bar's OPEN
  (price improvement the live tracker ignores).

R-multiple convention (matches live ``_close``/``_close_runner``,
``v54_exit_tracker.py:199-227``): R is denominated in the PLANNED risk unit
``risk = entry - stop``. Full-position exits (STOP / PP / TIMEOUT /
GAP_ABOVE_TARGET) report ``blended_r = R(exit_px)`` on the full position.
Post-TP1 runner exits report
``blended_r = 0.5 * R(tp1_fill) + 0.5 * R(runner_exit_px)``
(the 50% scale-out is real: half the position is gone at TP1, so the runner's
R only applies to the remaining half).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

MAX_HOLD_BARS = 30  # v54_exit_tracker.py:29 — research MAX_HOLD = 30

# ---------------------------------------------------------------------------
# Exit reasons. ``live_reason`` keeps the v54_exit_tracker.py vocabulary;
# ``exit_reason`` is the canonical set handed to worker (d).
# ---------------------------------------------------------------------------
LIVE_TO_CANONICAL = {
    "stop": "STOP",                    # full position stopped before TP1
    "runner-stop": "TP1_THEN_STOP",     # TP1 taken, then runner hit the stop
    "runner-exit": "TP1_THEN_PP",       # TP1 taken, then PP exited the runner
    "scanner-exit": "PP",              # PP exited the full position (pre-TP1)
    "time": "TIMEOUT",                 # 30-bar timeout, full position
    "runner-time": "TIMEOUT",          # 30-bar timeout, runner
    "gap-above-target": "GAP_ABOVE_TARGET",  # entry bar opened at/above TP1
}


def r_of(px: float, entry: float, risk: float) -> float:
    """R-multiple of a price vs the planned risk unit (entry - stop).

    Mirrors ``v54_exit_tracker.py:32-33`` (``_r_of``), with ``risk`` passed as
    a price distance instead of a fraction — algebraically identical.
    """
    return (px - entry) / risk if risk > 0 else 0.0


@dataclass
class TradeResult:
    """Result of running one trade through the Mode B exit engine."""

    exit_bar: Any = None            # bar label of the exit (None if OPEN)
    exit_px: Optional[float] = None
    # For post-TP1 runner exits, exit_px is the RUNNER exit price and the TP1
    # fill is recorded separately (the 50% scale-out is a distinct event).
    tp1_fill_px: Optional[float] = None
    tp1_fill_bar: Any = None
    exit_reason: str = "OPEN"       # canonical: STOP / TP1_THEN_STOP /
                                    # TP1_THEN_PP / PP / TIMEOUT /
                                    # GAP_ABOVE_TARGET / OPEN
    live_reason: Optional[str] = None  # v54_exit_tracker.py vocabulary
    blended_r: Optional[float] = None   # full-position R (see R convention)
    partial_r: Optional[float] = None   # 0.5 * R(tp1_fill); None pre-TP1
    runner_r: Optional[float] = None    # R(runner exit); None pre-TP1
    mfe_r: float = 0.0
    mae_r: float = 0.0
    bars_held: int = 0
    tp1_taken: bool = False
    pp_armed: bool = False
    pp_arming_bar: Any = None
    reached_plus_1r: bool = False
    realistic_gaps: bool = False
    events: List[Dict[str, Any]] = field(default_factory=list)


def _round4(x: float) -> float:
    return round(float(x), 4)


def run_trade(
    entry_bar_idx: int,
    entry_price: float,
    stop: float,
    tp1: float,
    bars_df: pd.DataFrame,
    scanner_states: Optional[List[Optional[str]]] = None,
    realistic_gaps: bool = False,
    entry_bar_label: Optional[Any] = None,
) -> TradeResult:
    """Run one Mode B trade over a bar sequence.

    Parameters
    ----------
    entry_bar_idx:
        Positional index into ``bars_df`` of the ENTRY bar. The entry bar is
        the first completed 4H bar AFTER the signal bar, and the entry fills
        at that bar's open (live: ``v54_forward_harness.py:156``). The caller
        supplies ``entry_price`` (= that bar's open in live paper); the engine
        processes the entry bar itself as bar #1 of the 30-bar clock (live:
        ``v54_forward_harness.py:173``).
    entry_price, stop, tp1:
        Entry fill, structural stop (never moves), TP1 level.
    bars_df:
        DataFrame with ``Open``/``High``/``Low``/``Close`` columns. Rows are
        processed in positional order starting at ``entry_bar_idx``. The index
        provides bar labels (used for ``exit_bar``/event bars only).
    scanner_states:
        Optional list aligned to ``bars_df`` rows (positional) of the scanner
        state per bar (e.g. ``"EXIT"`` from ``v53_state_for_bar``). ``None``
        entries mean "no EXIT signal". Only the ``"EXIT"`` value is read, and
        only when Profit Protect is armed — mirroring
        ``v54_exit_tracker.py:165,171``.
    realistic_gaps:
        ``False`` (default) = byte-faithful to the live tracker (gap-through-
        stop fills AT THE STOP PRICE — optimistic, see module docstring).
        ``True`` = realistic variant (gap-through-stop fills at the bar open
        beyond the stop; gap-through-TP1 fills at the open).
    entry_bar_label:
        Optional override for the entry bar's label in events (defaults to
        ``bars_df.index[entry_bar_idx]``).

    Returns
    -------
    TradeResult. If the bar data ends before any exit fires, ``exit_reason``
    is ``"OPEN"`` with the in-flight state (live never hits this; the forward
    test keeps feeding bars until close).
    """
    entry = float(entry_price)
    stop = float(stop)
    tp1 = float(tp1)
    if entry <= stop:
        # Live: open_position returns None ("invalid") —
        # v54_exit_tracker.py:87-88. A pure function can't return None and a
        # result, so this is a hard error here.
        raise ValueError(f"entry ({entry}) <= stop ({stop}): invalid trade")
    risk = entry - stop
    n = len(bars_df)
    if not (0 <= entry_bar_idx < n):
        raise IndexError(f"entry_bar_idx {entry_bar_idx} out of range (n={n})")

    labels = list(bars_df.index)
    if entry_bar_label is None:
        entry_bar_label = labels[entry_bar_idx]
    states = scanner_states if scanner_states is not None else [None] * n

    res = TradeResult(realistic_gaps=realistic_gaps)

    def label(i: int) -> Any:
        return labels[i]

    # -- gap-above-target: entry bar opened at/above TP1 -------------------
    # Live: open_position closes immediately at the entry price —
    # v54_exit_tracker.py:92-95. blended = R(entry) = 0.0.
    if entry >= tp1:
        res.exit_bar = entry_bar_label
        res.exit_px = entry
        res.live_reason = "gap-above-target"
        res.exit_reason = LIVE_TO_CANONICAL["gap-above-target"]
        res.blended_r = _round4(r_of(entry, entry, risk))
        res.bars_held = 0
        res.events.append({"event": "closed", "bar": entry_bar_label,
                           "live_reason": "gap-above-target",
                           "exit_px": entry, "blended_r": res.blended_r})
        return res

    res.events.append({"event": "opened", "bar": entry_bar_label,
                       "entry": entry, "stop": stop, "tp1": tp1})

    status = "open_full"          # live STATUS_OPEN_FULL
    tp1_taken = False
    tp1_fill_px: Optional[float] = None
    tp1_fill_bar: Any = None
    tp1_r: Optional[float] = None  # R of the TP1 fill (full-position units)
    armed = False
    arming_bar: Any = None
    pending: Optional[str] = None  # "full" | "runner" — PP fills next open
    mfe = 0.0
    mae = 0.0
    bars_held = 0

    def stop_fill_px(bar_open: float) -> float:
        # Live: fill AT THE STOP PRICE even when the bar gaps through it —
        # v54_exit_tracker.py:151-152 (full), 169-170 (runner). Optimistic.
        if realistic_gaps and bar_open <= stop:
            return bar_open  # stop-market: first tradable price beyond stop
        return stop

    def tp1_fill_px_of(bar_open: float) -> float:
        # Live: limit fills at the EXACT tp1 price even when the bar opens
        # above it — v54_exit_tracker.py:157-162 (conservative).
        if realistic_gaps and bar_open >= tp1:
            return bar_open  # real limit: fills at the better open
        return tp1

    last_i = min(entry_bar_idx + MAX_HOLD_BARS - 1, n - 1)
    for i in range(entry_bar_idx, last_i + 1):
        bar = bars_df.iloc[i]
        o, hi, lo, c = (float(bar["Open"]), float(bar["High"]),
                        float(bar["Low"]), float(bar["Close"]))
        bar_label = label(i)

        bars_held += 1  # live v54_exit_tracker.py:127 (entry bar = bar #1)
        mfe = max(mfe, r_of(hi, entry, risk))  # live :130
        mae = min(mae, r_of(lo, entry, risk))  # live :131

        # Sticky Profit Protect arming — live v54_exit_tracker.py:189-197.
        # Runs BEFORE the pending-exit fill so the fill bar's high counts.
        if not armed and mfe >= 1.0:
            armed = True
            arming_bar = bar_label
            res.events.append({"event": "profit_protect_armed",
                               "bar": bar_label})

        # Pending PP exit fills at THIS bar's open — takes precedence over
        # every stop/TP1/EXIT evaluation on the fill bar
        # (live v54_exit_tracker.py:141-147: fills and returns).
        if pending is not None:
            kind = pending
            res.exit_bar = bar_label
            res.exit_px = o
            res.bars_held = bars_held
            res.mfe_r = _round4(mfe)
            res.mae_r = _round4(mae)
            if kind == "runner":
                # live _close_runner -> _close — v54_exit_tracker.py:229-232
                assert tp1_r is not None
                res.partial_r = _round4(0.5 * tp1_r)
                res.runner_r = _round4(r_of(o, entry, risk))
                res.blended_r = _round4(res.partial_r + 0.5 * res.runner_r)
                res.live_reason = "runner-exit"
            else:
                # live _close with partial_r=None — v54_exit_tracker.py:143-146
                res.blended_r = _round4(r_of(o, entry, risk))
                res.live_reason = "scanner-exit"
            res.exit_reason = LIVE_TO_CANONICAL[res.live_reason]
            res.events.append({"event": "closed", "bar": bar_label,
                               "live_reason": res.live_reason,
                               "exit_px": o, "blended_r": res.blended_r})
            _finalize(res, tp1_taken, tp1_fill_px, tp1_fill_bar,
                      armed, arming_bar, mfe, mae, bars_held)
            return res

        if status == "open_full":
            # Live ordering: stop first (wins ties), then TP1, then EXIT —
            # v54_exit_tracker.py:150-167.
            if lo <= stop:
                fill = stop_fill_px(o)
                res.exit_bar = bar_label
                res.exit_px = fill
                res.live_reason = "stop"
                res.exit_reason = LIVE_TO_CANONICAL["stop"]
                res.blended_r = _round4(r_of(fill, entry, risk))
                res.events.append({"event": "closed", "bar": bar_label,
                                   "live_reason": "stop", "exit_px": fill,
                                   "blended_r": res.blended_r})
                _finalize(res, False, None, None, armed, arming_bar,
                          mfe, mae, bars_held)
                return res
            elif hi >= tp1:
                # TP1 first touch -> 50% at the TP1 fill; runner continues.
                # Live takes NO stop/exit evaluation on the TP1 bar itself
                # ("Research: continue" — v54_exit_tracker.py:164).
                tp1_taken = True
                tp1_fill_px = tp1_fill_px_of(o)
                tp1_fill_bar = bar_label
                tp1_r = r_of(tp1_fill_px, entry, risk)
                status = "open_runner"
                res.events.append({"event": "tp1_taken", "bar": bar_label,
                                   "tp1_fill_px": tp1_fill_px,
                                   "partial_r": _round4(0.5 * tp1_r)})
            elif states[i] == "EXIT" and armed:
                pending = "full"
                res.events.append({"event": "exit_signaled", "bar": bar_label,
                                   "reason": "scanner-exit",
                                   "fills_at": "next_bar_open"})
        else:  # open_runner — runner keeps the STRUCTURAL stop (frozen)
            if lo <= stop:
                fill = stop_fill_px(o)
                res.exit_bar = bar_label
                res.exit_px = fill
                res.live_reason = "runner-stop"
                res.exit_reason = LIVE_TO_CANONICAL["runner-stop"]
                assert tp1_r is not None
                res.partial_r = _round4(0.5 * tp1_r)
                res.runner_r = _round4(r_of(fill, entry, risk))
                res.blended_r = _round4(res.partial_r + 0.5 * res.runner_r)
                res.events.append({"event": "closed", "bar": bar_label,
                                   "live_reason": "runner-stop",
                                   "exit_px": fill, "blended_r": res.blended_r})
                _finalize(res, True, tp1_fill_px, tp1_fill_bar,
                          armed, arming_bar, mfe, mae, bars_held)
                return res
            elif states[i] == "EXIT" and armed:
                pending = "runner"
                res.events.append({"event": "exit_signaled", "bar": bar_label,
                                   "reason": "scanner-exit",
                                   "fills_at": "next_bar_open"})

        # 30-bar time exit at the bar's close — live v54_exit_tracker.py:178-183.
        # Runs on every processed bar, including the TP1-take bar.
        if bars_held >= MAX_HOLD_BARS:
            res.exit_bar = bar_label
            res.exit_px = c
            res.live_reason = ("runner-time" if status == "open_runner"
                               else "time")
            res.exit_reason = LIVE_TO_CANONICAL[res.live_reason]
            if status == "open_runner":
                assert tp1_r is not None
                res.partial_r = _round4(0.5 * tp1_r)
                res.runner_r = _round4(r_of(c, entry, risk))
                res.blended_r = _round4(res.partial_r + 0.5 * res.runner_r)
            else:
                res.blended_r = _round4(r_of(c, entry, risk))
            res.events.append({"event": "closed", "bar": bar_label,
                               "live_reason": res.live_reason,
                               "exit_px": c, "blended_r": res.blended_r})
            _finalize(res, tp1_taken, tp1_fill_px, tp1_fill_bar,
                      armed, arming_bar, mfe, mae, bars_held)
            return res

    # Bar data exhausted before any exit fired (live never hits this — the
    # forward test keeps feeding bars until the position closes).
    _finalize(res, tp1_taken, tp1_fill_px, tp1_fill_bar,
              armed, arming_bar, mfe, mae, bars_held)
    res.events.append({"event": "data_exhausted_open",
                       "status": status, "bars_held": bars_held})
    return res


def _finalize(res: TradeResult, tp1_taken: bool,
              tp1_fill_px: Optional[float], tp1_fill_bar: Any,
              armed: bool, arming_bar: Any,
              mfe: float, mae: float, bars_held: int) -> None:
    res.tp1_taken = tp1_taken
    res.tp1_fill_px = tp1_fill_px
    res.tp1_fill_bar = tp1_fill_bar
    res.pp_armed = armed
    res.pp_arming_bar = arming_bar
    res.reached_plus_1r = mfe >= 1.0
    res.mfe_r = _round4(mfe)
    res.mae_r = _round4(mae)
    res.bars_held = bars_held
