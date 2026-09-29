"""V5.4 exit tracker — frozen Mode B state machine.

Traced to hybrid_exit_test.py::walk_hybrid(mode="B"), the implementation
that produced the frozen research result (UX51 +0.400R, PF 1.71).

Mode B (frozen):
- On entry: store structural stop + TP1, full size.
- Same-bar collision ordering: STOP first, then TP1, then EXIT.
  (Research convention: "First touch wins; stop wins same-bar ties" —
  conservative, no favorable assumption invented.)
- TP1 first touch -> realize 50% at TP1 (sticky flag), 50% runner continues.
- Runner keeps the STRUCTURAL stop. Never moved to breakeven
  (breakeven runner was mode C — rejected by research).
- Bar high reaching +1R permanently arms Profit Protect (sticky flag).
- Scanner EXIT may close the runner ONLY after arming; filled at the NEXT
  bar's open (research: "EXIT exits at NEXT bar open").
- 30-bar time exit (research MAX_HOLD = 30): "time" / "runner-time".
- Idempotent: reprocessing the same completed bar is a no-op. TP1 and +1R
  flags are sticky once set — reruns cannot double-take TP1, re-arm, or
  duplicate an exit.

Nothing here modifies V5.3.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

MAX_HOLD_BARS = 30  # research: hybrid_exit_test.py and backtest_v2.py

STATUS_OPEN_FULL = "open_full"
STATUS_OPEN_RUNNER = "open_runner"
STATUS_CLOSED = "closed"


def _r_of(px: float, entry: float, risk_frac: float) -> float:
    return (((px - entry) / entry) / risk_frac) if risk_frac > 0 else 0.0


class ModeBTracker:
    """State machine for one or more Mode B positions.

    Positions are keyed by signal_id (the stable key from qualification
    through final exit). An optional event_sink callable receives every
    lifecycle event (used to feed the forward logger).
    """

    def __init__(self, event_sink: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.positions: Dict[str, Dict[str, Any]] = {}
        self._sink = event_sink

    # -- lifecycle ------------------------------------------------------

    def open_position(
        self,
        signal: Dict[str, Any],
        entry_px: float,
        entry_bar_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Open a Mode B position. Returns None if entry <= stop (invalid).

        A gap open at/above TP1 closes immediately ("gap-above-target"),
        mirroring the research.
        """
        sid = signal["signal_id"]
        entry = float(entry_px)
        stop = float(signal["stop"])
        tp1 = float(signal["tp1"])
        if entry <= stop or sid in self.positions:
            return None
        risk_frac = (entry - stop) / entry
        pos: Dict[str, Any] = {
            "signal_id": sid,
            "symbol": signal.get("symbol"),
            "grade": signal.get("v54_grade"),
            "entry": entry,
            "stop": stop,          # structural stop — never moves (frozen)
            "tp1": tp1,
            "risk_frac": risk_frac,
            "entry_bar": entry_bar_id,
            "status": STATUS_OPEN_FULL,
            "tp1_taken": False,    # sticky
            "tp1_bar": None,
            "tp1_r": None,
            "plus_1r_armed": False,  # sticky
            "plus_1r_bar": None,
            "pending_exit": None,
            "mfe_r": 0.0,
            "mae_r": 0.0,
            "bars_held": 0,
            "last_processed_bar": None,
            "processed_bars": [],
            "events": [],
            "exit": None,
        }
        self.positions[sid] = pos
        if entry >= tp1:
            self._close(pos, entry, entry_bar_id, "gap-above-target",
                        partial_r=None, runner_r=None)
        else:
            self._emit(sid, {"event": "opened", "bar": entry_bar_id,
                             "entry": entry, "stop": stop, "tp1": tp1})
        return pos

    def process_bar(self, signal_id: str, bar: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process one COMPLETED 4H bar.

        bar = {"bar_id": str, "open": f, "high": f, "low": f, "close": f,
               "scanner_state": optional "EXIT" signal for this bar}.
        Idempotent: reprocessing an already-seen bar_id is a no-op.
        """
        pos = self.positions.get(signal_id)
        if pos is None or pos["status"] == STATUS_CLOSED:
            return pos
        bar_id = str(bar["bar_id"])
        if bar_id in pos["processed_bars"]:
            return pos  # idempotent rerun: exact no-op
        # Note: bars are expected in chronological order (ISO bar_ids sort
        # chronologically). Out-of-order feeds are a harness bug; they are
        # processed as given and visible in the events log.
        pos["processed_bars"].append(bar_id)

        pos["bars_held"] += 1
        pos["last_processed_bar"] = bar_id
        entry, stop, tp1 = pos["entry"], pos["stop"], pos["tp1"]
        risk_frac = pos["risk_frac"]
        hi, lo = float(bar["high"]), float(bar["low"])

        pos["mfe_r"] = max(pos["mfe_r"], _r_of(hi, entry, risk_frac))
        pos["mae_r"] = min(pos["mae_r"], _r_of(lo, entry, risk_frac))

        # Sticky Profit Protect arming: bar high reaching +1R arms forever.
        # Research gates EXIT on mfe_r >= 1.0 with the current bar's high
        # included, before the EXIT check — behaviorally identical, and the
        # flag can never gate anything on the TP1-take bar itself because no
        # EXIT check runs on that bar (research: continue after TP1).
        self._armed(pos, bar_id)

        # Pending EXIT from the previous bar fills at this bar's open.
        if pos["pending_exit"] is not None:
            kind = pos["pending_exit"]["kind"]
            if kind == "runner":
                self._close_runner(pos, float(bar["open"]), bar_id, "runner-exit")
            else:
                self._close(pos, float(bar["open"]), bar_id, "scanner-exit",
                            partial_r=None, runner_r=None)
            return pos

        if pos["status"] == STATUS_OPEN_FULL:
            # Research ordering: stop first (wins ties), then TP1.
            if lo <= stop:
                self._close(pos, stop, bar_id, "stop",
                            partial_r=None, runner_r=None)
            elif hi >= tp1:
                pos["tp1_taken"] = True  # sticky
                pos["tp1_bar"] = bar_id
                pos["tp1_r"] = _r_of(tp1, entry, risk_frac)
                pos["status"] = STATUS_OPEN_RUNNER
                self._emit(signal_id, {"event": "tp1_taken", "bar": bar_id,
                                       "tp1": tp1, "partial_r": round(0.5 * pos["tp1_r"], 4)})
                # Research: continue — no stop/exit check on the TP1 bar itself.
            elif bar.get("scanner_state") == "EXIT" and pos["plus_1r_armed"]:
                pos["pending_exit"] = {"kind": "full", "exit_bar": bar_id,
                                       "reason": "scanner-exit"}
                self._emit(signal_id, {"event": "exit_signaled", "bar": bar_id,
                                       "reason": "scanner-exit",
                                       "fills_at": "next_bar_open"})
        elif pos["status"] == STATUS_OPEN_RUNNER:
            if lo <= stop:
                self._close_runner(pos, stop, bar_id, "runner-stop")
            elif bar.get("scanner_state") == "EXIT" and pos["plus_1r_armed"]:
                pos["pending_exit"] = {"kind": "runner", "exit_bar": bar_id,
                                       "reason": "scanner-exit"}
                self._emit(signal_id, {"event": "exit_signaled", "bar": bar_id,
                                       "reason": "scanner-exit",
                                       "fills_at": "next_bar_open"})

        # Time exit (research MAX_HOLD = 30 bars).
        if pos["status"] != STATUS_CLOSED and pos["bars_held"] >= MAX_HOLD_BARS:
            if pos["status"] == STATUS_OPEN_RUNNER:
                self._close_runner(pos, float(bar["close"]), bar_id, "runner-time")
            else:
                self._close(pos, float(bar["close"]), bar_id, "time",
                            partial_r=None, runner_r=None)
        return pos

    # -- internals ------------------------------------------------------

    def _armed(self, pos: Dict[str, Any], bar_id: str) -> bool:
        """Sticky Profit Protect arming: bar high reaching +1R arms forever."""
        if not pos["plus_1r_armed"] and pos["mfe_r"] >= 1.0:
            pos["plus_1r_armed"] = True  # sticky
            pos["plus_1r_bar"] = bar_id
            self._emit(pos["signal_id"], {"event": "profit_protect_armed",
                                          "bar": bar_id})
        return pos["plus_1r_armed"]

    def _close(self, pos: Dict[str, Any], exit_px: float, bar_id: str,
               reason: str, partial_r: Optional[float], runner_r: Optional[float]):
        entry, risk_frac = pos["entry"], pos["risk_frac"]
        if partial_r is None:
            blended = _r_of(exit_px, entry, risk_frac)
        else:
            blended = partial_r + 0.5 * (runner_r if runner_r is not None else 0.0)
        pos["status"] = STATUS_CLOSED
        pos["exit"] = {
            "exit_px": exit_px,
            "exit_bar": bar_id,
            "reason": reason,
            "partial_r": None if partial_r is None else round(partial_r, 4),
            "runner_r": None if runner_r is None else round(runner_r, 4),
            "blended_r": round(blended, 4),
            "mfe_r": round(pos["mfe_r"], 4),
            "mae_r": round(pos["mae_r"], 4),
            "bars_held": pos["bars_held"],
            "reached_plus_1r": bool(pos["mfe_r"] >= 1.0),
        }
        self._emit(pos["signal_id"], {"event": "closed", "bar": bar_id,
                                      "reason": reason, "exit_px": exit_px,
                                      **pos["exit"]})

    def _close_runner(self, pos: Dict[str, Any], exit_px: float, bar_id: str, reason: str):
        partial_r = 0.5 * pos["tp1_r"]
        runner_r = _r_of(exit_px, pos["entry"], pos["risk_frac"])
        self._close(pos, exit_px, bar_id, reason,
                    partial_r=partial_r, runner_r=runner_r)

    def _emit(self, signal_id: str, event: Dict[str, Any]):
        pos = self.positions[signal_id]
        pos["events"].append(event)
        if self._sink is not None:
            self._sink({"signal_id": signal_id, **event})

    # -- access ----------------------------------------------------------

    def get(self, signal_id: str) -> Optional[Dict[str, Any]]:
        return self.positions.get(signal_id)

    def open_positions(self) -> List[Dict[str, Any]]:
        return [p for p in self.positions.values() if p["status"] != STATUS_CLOSED]


def close_summary(pos: Dict[str, Any], signal_snapshot: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build the frozen-schema final trade record from tracker state.

    Frozen schema fields: signal id/symbol/time/grade; market gate, exact
    RVOL, daily/weekly states, R:R, 15m state, premarket context; entry/TP1/
    stop; +1R reached; partial/runner/blended R; MFE/MAE/bars held; V5.3
    veto/control status.
    """
    snap = signal_snapshot or {}
    pm = {k: snap.get(k) for k in (
        "pm_last", "pm_gap_pct", "pm_range_pct", "pm_volume", "pm_vwap", "pm_read")}
    summary = {
        "signal_id": pos["signal_id"],
        "symbol": pos.get("symbol"),
        "signal_time": snap.get("signal_bar_close_at"),
        "grade": pos.get("grade"),
        "market_gate": snap.get("market_gate"),
        "market_regime": snap.get("market_regime"),
        "rvol_exact": snap.get("rel_vol"),
        "daily_state": snap.get("daily_trend"),
        "weekly_state": snap.get("weekly_trend"),
        "risk_reward": snap.get("risk_reward"),
        "confirmation_15m": snap.get("confirmation_15m"),
        "premarket": pm,
        "entry": pos.get("entry"),
        "entry_bar": pos.get("entry_bar"),
        "tp1": pos.get("tp1"),
        "stop": pos.get("stop"),
        "reached_plus_1r": (pos.get("exit") or {}).get("reached_plus_1r"),
        "tp1_taken": pos.get("tp1_taken"),
        "partial_r": (pos.get("exit") or {}).get("partial_r"),
        "runner_r": (pos.get("exit") or {}).get("runner_r"),
        "blended_r": (pos.get("exit") or {}).get("blended_r"),
        "mfe_r": (pos.get("exit") or {}).get("mfe_r"),
        "mae_r": (pos.get("exit") or {}).get("mae_r"),
        "bars_held": (pos.get("exit") or {}).get("bars_held"),
        "exit_reason": (pos.get("exit") or {}).get("reason"),
        "exit_px": (pos.get("exit") or {}).get("exit_px"),
        "exit_bar": (pos.get("exit") or {}).get("exit_bar"),
        "v53_vetoed": snap.get("v53_would_veto"),
        "v53_state": snap.get("v53_state"),
        "v53_entry": snap.get("v53_entry"),
        "v53_score": snap.get("v53_score"),
    }
    return summary
