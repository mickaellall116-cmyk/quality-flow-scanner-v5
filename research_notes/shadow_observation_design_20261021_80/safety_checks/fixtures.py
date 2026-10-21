"""Synthetic fixtures for the -80 safety suite (no live data, no network).

Every expected value below is HAND-COMPUTED from the frozen Mode B
rules as implemented by the pinned tracker (v54_exit_tracker.py,
sha256 3ee92864...):

    R(px) = (px - entry) / (entry - stop)          [risk-normalized]
    entry  = open of the first completed bar after the signal bar
    stop   = filled AT the stop price when a bar's low touches it;
             stop is checked before TP1 (stop wins same-bar ties)
    TP1    = first touch realizes 50% at the TP1 price;
             partial_r (stored) = 0.5 * R(tp1); the runner continues
             on the structural stop, which never moves
    arm    = a bar high reaching +1R arms Profit Protect (sticky)
    EXIT   = a scanner EXIT state closes the position ONLY when armed,
             filled at the NEXT bar's open ("scanner-exit" for a full
             position, "runner-exit" for the runner); no EXIT check
             runs on the TP1 bar itself
    time   = at 30 bars held, close at that bar's close
             ("time" full / "runner-time" runner)
    blended_r (runner close) = 0.5 * R(tp1) + 0.5 * R(exit_px)

All three trades: entry basis 100.00, stop 95.00 -> risk = 5.00.
Signal bar (context only, never walked): 2026-10-02 14:30 ET.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

SIGNAL_START = "2026-10-02T14:30:00-04:00"
SIGNAL_CLOSE = "2026-10-02T16:00:00-04:00"


def bar(bar_id: str, o: float, h: float, l: float, c: float,
        scanner_state: Optional[str] = None) -> Dict[str, Any]:
    return {"bar_id": bar_id, "open": o, "high": h, "low": l, "close": c,
            "scanner_state": scanner_state}


def signal_bar(symbol: str) -> Dict[str, Any]:
    return bar(SIGNAL_START, 99.0, 100.5, 98.5, 100.0)


def signal_row(symbol: str, grade: str, stop: float, tp1: float) -> Dict[str, Any]:
    """A qualified-signal row in the frozen engine's output shape."""
    return {
        "signal_id": f"v54:{symbol}:4h:{SIGNAL_CLOSE}:2026-09-15-v54",
        "symbol": symbol,
        "theme": "Forward-UX51",
        "timeframe": "4h",
        "signal_bar_start_at": SIGNAL_START,
        "signal_bar_close_at": SIGNAL_CLOSE,
        "state": "BUY",
        "entry": "YES",
        "protection": "SAFE",
        "price": 100.0,
        "stop": stop,
        "tp1": tp1,
        "risk_reward": round((tp1 - 100.0) / (100.0 - stop), 3),
        "market_gate": "CONFIRM",
        "market_regime": "RISK-ON",
        "daily_trend": "confirmed",
        "weekly_trend": "confirmed",
        "rel_vol": 1.5,
        "adx": 30.0,
        "v54_grade": grade,
        "v54_rule_version": "2026-09-15-v54",
        "v53_state": "BUY",
        "v53_entry": "YES",
        "v53_would_veto": False,
    }


# ---------------------------------------------------------------------------
# TRADE A — full-position stop-out.
#   B1: entry 100.00 (bar open). R(H 103)=+0.60, R(L 98)=-0.40.
#       No arm (<1R), no stop (98>95), no TP1 (103<110).
#   B2: R(H 104)=+0.80 -> mfe 0.80; R(L 94.5)=-1.10 -> mae -1.10;
#       low 94.5 <= stop 95 -> STOP filled at 95.00.
#   blended = R(95) = (95-100)/5 = -1.0000. bars_held = 2.
# ---------------------------------------------------------------------------
TRADE_A = {
    "symbol": "FIXA",
    "row": signal_row("FIXA", "B", 95.0, 110.0),
    "bars": [
        bar("2026-10-05T06:30:00-04:00", 100.0, 103.0, 98.0, 102.0),
        bar("2026-10-05T10:30:00-04:00", 102.0, 104.0, 94.5, 96.0),
    ],
    "expected_close": {
        "reason": "stop", "exit_px": 95.0,
        "exit_bar": "2026-10-05T10:30:00-04:00",
        "partial_r": None, "runner_r": None, "blended_r": -1.0,
        "mfe_r": 0.8, "mae_r": -1.1, "bars_held": 2,
        "tp1_taken": False, "reached_plus_1r": False,
    },
}

# ---------------------------------------------------------------------------
# TRADE B — TP1 + runner, Profit Protect scanner-exit at next-bar open.
#   tp1_r = R(110) = (110-100)/5 = 2.0000.
#   B1: entry 100.00. R(H 106)=+1.20 >= 1R -> ARMED at B1 (sticky).
#       R(L 99)=-0.20 -> mae -0.20. No stop, no TP1 (106<110).
#   B2: R(H 111)=+2.20 -> mfe 2.20. scanner_state EXIT on this bar must
#       be IGNORED (the TP1 branch runs; no EXIT check on the TP1 bar).
#       high 111 >= tp1 110 -> TP1 taken at B2; stored partial = 0.5*2.0
#       = 1.0000. Status -> runner.
#   B3: R(H 112)=+2.40 -> mfe 2.40. Runner: no stop (108>95); EXIT +
#       armed -> exit_signaled; fill is PENDING (next bar open). No
#       close may exist after B3.
#   B4: pending fills at open 109.00 -> "runner-exit".
#       runner_r = R(109) = 1.8000.
#       blended = 0.5*2.0000 + 0.5*1.8000 = 1.0000 + 0.9000 = 1.9000.
#       bars_held = 4 (the fill bar counts).
# ---------------------------------------------------------------------------
TRADE_B = {
    "symbol": "FIXB",
    "row": signal_row("FIXB", "A", 95.0, 110.0),
    "bars": [
        bar("2026-10-05T06:30:00-04:00", 100.0, 106.0, 99.0, 105.0),
        bar("2026-10-05T10:30:00-04:00", 105.0, 111.0, 104.0, 110.0,
            scanner_state="EXIT"),
        bar("2026-10-05T14:30:00-04:00", 110.0, 112.0, 108.0, 111.0,
            scanner_state="EXIT"),
        bar("2026-10-06T06:30:00-04:00", 109.0, 109.5, 107.0, 108.0),
    ],
    "expected_close": {
        "reason": "runner-exit", "exit_px": 109.0,
        "exit_bar": "2026-10-06T06:30:00-04:00",
        "partial_r": 1.0, "runner_r": 1.8, "blended_r": 1.9,
        "mfe_r": 2.4, "mae_r": -0.2, "bars_held": 4,
        "tp1_taken": True, "reached_plus_1r": True,
    },
    "expected_tp1_bar": "2026-10-05T10:30:00-04:00",
    "expected_arm_bar": "2026-10-05T06:30:00-04:00",
}

# ---------------------------------------------------------------------------
# TRADE C — 30-bar time exit (full position, never armed).
#   tp1 = 130 (never touched: every high is 102 -> R = +0.40 < 1R, so
#   Profit Protect never arms; every low is 99 -> R = -0.20, never the
#   stop). B1 opens at 100.00 (the hypothetical entry); B2..B30 open
#   100.50. At B30 bars_held reaches 30 -> close at B30's close 101.00.
#   blended = R(101) = (101-100)/5 = +0.2000. mfe 0.40, mae -0.20.
# ---------------------------------------------------------------------------
_C_DAYS = ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08",
           "2026-10-09", "2026-10-12", "2026-10-13", "2026-10-14",
           "2026-10-15", "2026-10-16"]
_C_TIMES = ["06:30", "10:30", "14:30"]
_c_bars: List[Dict[str, Any]] = []
for _i, (_d, _t) in enumerate(
        [(d, t) for d in _C_DAYS for t in _C_TIMES]):
    _c_bars.append(bar(f"{_d}T{_t}:00-04:00",
                       100.0 if _i == 0 else 100.5, 102.0, 99.0, 101.0))

TRADE_C = {
    "symbol": "FIXC",
    "row": signal_row("FIXC", "B", 95.0, 130.0),
    "bars": _c_bars,
    "expected_close": {
        "reason": "time", "exit_px": 101.0,
        "exit_bar": "2026-10-16T14:30:00-04:00",
        "partial_r": None, "runner_r": None, "blended_r": 0.2,
        "mfe_r": 0.4, "mae_r": -0.2, "bars_held": 30,
        "tp1_taken": False, "reached_plus_1r": False,
    },
}

# Fixture D — a signal whose symbol is degraded in cycle 1 (S6).
TRADE_D_ROW = signal_row("FIXD", "C", 95.0, 110.0)
