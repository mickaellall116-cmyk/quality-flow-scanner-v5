"""Tests for v54_forward_log.py — append-only audit behavior."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v54_forward_log import ForwardLog


def _log(tmp=None):
    import tempfile
    d = tmp or tempfile.mkdtemp()
    return ForwardLog(os.path.join(d, "forward_test.jsonl"))


def test_signal_snapshot_preserved_verbatim():
    log = _log()
    snap = {"signal_id": "v54:AAPL:4h:x:v", "symbol": "AAPL", "v54_grade": "A",
            "rel_vol": 1.234, "market_gate": "BLOCK", "nested": {"a": 1}}
    log.log_signal(snap, entry_px=100.0, entry_bar_id="b0")
    # append events + close afterwards
    log.log_event("v54:AAPL:4h:x:v", {"event": "tp1_taken", "bar": "b5"})
    stored = log.get_signal("v54:AAPL:4h:x:v")
    for k, v in snap.items():
        assert stored[k] == v, f"snapshot field {k} was rewritten"
    assert stored["entry_px"] == 100.0


def test_events_append_in_order_without_rewriting():
    log = _log()
    sid = "v54:NVDA:4h:x:v"
    log.log_signal({"signal_id": sid}, 100.0, "b0")
    log.log_event(sid, {"event": "tp1_taken", "bar": "b3"})
    log.log_event(sid, {"event": "profit_protect_armed", "bar": "b4"})
    log.log_event(sid, {"event": "closed", "bar": "b9", "reason": "runner-stop"})
    evs = log.get_events(sid)
    assert [e["event"] for e in evs] == ["tp1_taken", "profit_protect_armed", "closed"]
    # raw file has 5 lines: signal + 3 events, none rewritten
    with open(log.path) as fh:
        lines = [json.loads(l) for l in fh if l.strip()]
    assert len(lines) == 4
    assert lines[0]["type"] == "signal"


def test_close_and_grade_counts():
    log = _log()
    log.log_signal({"signal_id": "s1", "v54_grade": "A"}, 1.0, "b0")
    log.log_signal({"signal_id": "s2", "v54_grade": "C"}, 1.0, "b0")
    log.log_close({"signal_id": "s1", "blended_r": 0.3})
    assert log.get_close("s1")["blended_r"] == 0.3
    assert log.get_close("s2") is None
    assert log.grade_counts() == {"A": 1, "B": 0, "C": 1}
    assert log.signal_ids() == ["s1", "s2"]


def test_tracker_sink_wires_to_log():
    import tempfile
    from v54_exit_tracker import ModeBTracker
    d = tempfile.mkdtemp()
    log = ForwardLog(os.path.join(d, "f.jsonl"))
    t = ModeBTracker(event_sink=lambda e: log.log_event(e["signal_id"], e))
    sig = {"signal_id": "v54:T:4h:x:v", "symbol": "T", "stop": 95.0,
           "tp1": 108.0, "v54_grade": "B"}
    log.log_signal(sig, 100.0, "bar0")
    pos = t.open_position(sig, 100.0, "bar0")
    t.process_bar(pos["signal_id"], {"bar_id": "b1", "open": 100, "high": 108.5,
                                     "low": 99, "close": 107})
    evs = log.get_events("v54:T:4h:x:v")
    assert any(e["event"] == "tp1_taken" for e in evs)
