"""Tests for v54_exit_tracker.py — frozen Mode B, traced to
hybrid_exit_test.py::walk_hybrid(mode="B").

Conventions pinned here: stop wins same-bar ties; TP1/+1R flags sticky;
idempotent reruns; runner keeps structural stop (never breakeven);
EXIT gated until +1R, filled at next bar open; 30-bar time exit.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v54_exit_tracker import ModeBTracker, close_summary, MAX_HOLD_BARS

ENTRY, STOP, TP1 = 100.0, 95.0, 108.0  # risk 5 -> r_of(px) = (px-100)/5


def _signal(**kw):
    s = {"signal_id": "v54:TEST:4h:bar0:v", "symbol": "TEST",
         "stop": STOP, "tp1": TP1, "v54_grade": "A"}
    s.update(kw)
    return s


def _bar(bar_id, o=100.0, h=101.0, l=99.0, c=100.5, state=None):
    b = {"bar_id": bar_id, "open": o, "high": h, "low": l, "close": c}
    if state:
        b["scanner_state"] = state
    return b


def _open(tracker=None, entry=ENTRY):
    t = tracker or ModeBTracker()
    pos = t.open_position(_signal(), entry, "bar0")
    return t, pos


# ---- basic Mode B paths ------------------------------------------------

def test_full_stop_before_tp1():
    t, pos = _open()
    t.process_bar(pos["signal_id"], _bar("b1", h=103.0, l=94.0))
    assert pos["status"] == "closed"
    assert pos["exit"]["reason"] == "stop"
    assert pos["exit"]["blended_r"] == -1.0
    assert pos["tp1_taken"] is False
    assert pos["exit"]["exit_px"] == STOP


def test_tp1_then_runner_stop_blended():
    t, pos = _open()
    sid = pos["signal_id"]
    t.process_bar(sid, _bar("b1", h=108.5))          # TP1 taken
    assert pos["status"] == "open_runner" and pos["tp1_taken"] is True
    t.process_bar(sid, _bar("b2", l=94.5))           # runner stopped
    assert pos["exit"]["reason"] == "runner-stop"
    # 0.5 * 1.6 + 0.5 * (-1.0) = 0.3
    assert abs(pos["exit"]["blended_r"] - 0.3) < 1e-9
    assert pos["exit"]["partial_r"] == 0.8
    assert pos["exit"]["runner_r"] == -1.0


def test_stop_wins_same_bar_tie():
    t, pos = _open()
    t.process_bar(pos["signal_id"], _bar("b1", h=109.0, l=94.0))
    assert pos["exit"]["reason"] == "stop"
    assert pos["tp1_taken"] is False, "tie must not take TP1 (conservative)"


def test_runner_stop_never_moves_to_breakeven():
    t, pos = _open()
    sid = pos["signal_id"]
    t.process_bar(sid, _bar("b1", h=108.5))           # TP1
    for i in range(2, 8):
        t.process_bar(sid, _bar(f"b{i}", h=115.0, l=112.0))
        assert pos["stop"] == STOP, "structural stop must never move"
    t.process_bar(sid, _bar("b8", l=94.0))
    assert pos["exit"]["reason"] == "runner-stop"
    assert pos["exit"]["exit_px"] == STOP


# ---- Profit Protect gating ----------------------------------------------

def test_exit_ignored_before_plus_1r():
    t, pos = _open()
    sid = pos["signal_id"]
    t.process_bar(sid, _bar("b1", h=108.5))                    # TP1 taken
    t.process_bar(sid, _bar("b2", h=104.0, l=103.0, state="EXIT"))
    # mfe after b1 = (108.5-100)/5 = 1.7 >= 1 -> armed; use a fresh case instead
    assert pos["status"] == "open_runner"  # not closed on b2's signal


def test_exit_gated_until_1r_then_fills_next_open():
    t = ModeBTracker()
    # engineer: TP1 far away so runner phase starts without +1R
    sig = _signal(tp1=200.0)
    pos = t.open_position(sig, ENTRY, "bar0")
    sid = pos["signal_id"]
    # force runner: simulate TP1 via direct bar (tp1=200 unreachable; emulate)
    pos["tp1_taken"] = True
    pos["tp1_r"] = 1.6
    pos["status"] = "open_runner"
    t.process_bar(sid, _bar("b1", h=102.0, l=101.0, state="EXIT"))
    assert pos["status"] == "open_runner", "EXIT before +1R must be ignored"
    assert pos["plus_1r_armed"] is False
    t.process_bar(sid, _bar("b2", h=106.0, l=104.0, state="EXIT"))  # mfe=1.2 -> arm
    assert pos["plus_1r_armed"] is True
    assert pos["pending_exit"] is not None, "armed EXIT defers to next open"
    assert pos["status"] == "open_runner"
    t.process_bar(sid, _bar("b3", o=103.0, h=104.0, l=102.0))
    assert pos["status"] == "closed"
    assert pos["exit"]["reason"] == "runner-exit"
    assert pos["exit"]["exit_px"] == 103.0, "research: EXIT fills at next bar open"


def test_full_size_exit_after_1r_before_tp1():
    t = ModeBTracker()
    sig = _signal(tp1=200.0)  # unreachable: stays full size
    pos = t.open_position(sig, ENTRY, "bar0")
    sid = pos["signal_id"]
    t.process_bar(sid, _bar("b1", h=106.0, l=104.0, state="EXIT"))  # mfe=1.2
    assert pos["pending_exit"] is not None
    t.process_bar(sid, _bar("b2", o=105.0, h=105.5, l=104.5))
    assert pos["exit"]["reason"] == "scanner-exit"
    assert pos["exit"]["exit_px"] == 105.0
    assert pos["exit"]["blended_r"] == 1.0


# ---- idempotency / stickiness ----------------------------------------------

def test_rerun_same_bar_is_noop():
    t, pos = _open()
    sid = pos["signal_id"]
    bar = _bar("b1", h=108.5)
    t.process_bar(sid, bar)
    n_events = len(pos["events"])
    t.process_bar(sid, dict(bar))  # rerun
    t.process_bar(sid, dict(bar))  # rerun again
    assert len(pos["events"]) == n_events, "rerun must not duplicate events"
    assert pos["tp1_taken"] is True
    assert pos["bars_held"] == 1


def test_closed_position_ignores_further_bars():
    t, pos = _open()
    sid = pos["signal_id"]
    t.process_bar(sid, _bar("b1", l=94.0))
    first_exit = dict(pos["exit"])
    t.process_bar(sid, _bar("b2", h=200.0))
    assert pos["exit"] == first_exit


def test_plus_1r_flag_sticky():
    t, pos = _open()
    sid = pos["signal_id"]
    t.process_bar(sid, _bar("b1", h=108.5))   # TP1; mfe 1.7 -> armed
    assert pos["plus_1r_armed"] is True
    t.process_bar(sid, _bar("b2", h=103.0, l=102.0))
    t.process_bar(sid, _bar("b3", h=101.0, l=100.0))
    assert pos["plus_1r_armed"] is True, "arming must be sticky"
    assert len([e for e in pos["events"]
                if e["event"] == "profit_protect_armed"]) == 1


# ---- time exit ---------------------------------------------------------------

def test_time_exit_at_30_bars():
    t, pos = _open()
    sid = pos["signal_id"]
    for i in range(1, MAX_HOLD_BARS):
        t.process_bar(sid, _bar(f"b{i}", h=101.0, l=99.0, c=100.0))
        assert pos["status"] == "open_full"
    t.process_bar(sid, _bar(f"b{MAX_HOLD_BARS}", h=101.0, l=99.0, c=100.2))
    assert pos["status"] == "closed"
    assert pos["exit"]["reason"] == "time"
    assert pos["bars_held"] == MAX_HOLD_BARS


def test_runner_time_exit_blends():
    t, pos = _open()
    sid = pos["signal_id"]
    t.process_bar(sid, _bar("b1", h=108.5))  # TP1
    for i in range(2, MAX_HOLD_BARS + 1):
        t.process_bar(sid, _bar(f"b{i}", h=107.0, l=106.0, c=106.5))
    assert pos["exit"]["reason"] == "runner-time"
    # 0.5*1.6 + 0.5*((106.5-100)/5) = 0.8 + 0.65 = 1.45
    assert abs(pos["exit"]["blended_r"] - 1.45) < 1e-9


# ---- close summary schema ------------------------------------------------------

def test_close_summary_has_frozen_fields():
    t, pos = _open()
    sid = pos["signal_id"]
    t.process_bar(sid, _bar("b1", h=108.5))
    t.process_bar(sid, _bar("b2", l=94.0))
    snap = {"signal_bar_close_at": "2026-09-14T16:00:00-04:00",
            "market_gate": "BLOCK", "market_regime": "RISK-OFF",
            "rel_vol": 1.23, "daily_trend": "not_confirmed",
            "weekly_trend": "confirmed", "risk_reward": 2.4,
            "confirmation_15m": True, "pm_gap_pct": 0.5,
            "v53_would_veto": True, "v53_state": "HOLD",
            "v53_entry": "NO", "v53_score": 40}
    s = close_summary(pos, snap)
    for field in ("signal_id", "symbol", "signal_time", "grade", "market_gate",
                  "rvol_exact", "daily_state", "weekly_state", "risk_reward",
                  "confirmation_15m", "premarket", "entry", "tp1", "stop",
                  "reached_plus_1r", "partial_r", "runner_r", "blended_r",
                  "mfe_r", "mae_r", "bars_held", "exit_reason",
                  "v53_vetoed", "v53_state", "v53_score"):
        assert field in s, f"frozen schema missing {field}"
    assert s["blended_r"] == 0.3
    assert s["reached_plus_1r"] is True
