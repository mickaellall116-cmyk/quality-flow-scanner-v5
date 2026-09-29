"""Tests for v54_forward_harness.py.

Verifies the forward-test loop end to end: signal detection -> pending
entry at next bar open -> Mode B tracking -> close -> append-only log ->
state persistence -> idempotent reruns. Plus a small real-data replay.
"""

import json
import os
import sys
import tempfile

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import v54_engine as eng
import v54_forward_harness as hz
from v54_exit_tracker import ModeBTracker
from v54_forward_log import ForwardLog

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "backtest_cache", "v3")


def _scripted_df():
    idx = pd.date_range("2026-01-06 09:30", periods=4, freq="4h", tz="America/New_York")
    return pd.DataFrame({
        "Open":  [100.0, 100.0, 101.0, 107.0],
        "High":  [101.0, 102.0, 108.5, 107.5],
        "Low":   [99.0, 99.5, 100.5, 94.5],
        "Close": [100.5, 101.0, 107.0, 96.0],
        "Volume": [1e6] * 4,
    }, index=idx)


def _row(ts0):
    return {
        "signal_id": f"v54:SYN:4h:{ts0.isoformat()}:v",
        "symbol": "SYN", "stop": 95.0, "tp1": 108.0,
        "v54_eligible": True, "v54_grade": "A", "v54_grade_label": "EARLY",
        "signal_bar_start_at": ts0.isoformat(),
        "signal_bar_close_at": ts0.isoformat(),
        "market_gate": "BLOCK", "market_regime": "RISK-OFF",
        "rel_vol": 1.1, "daily_trend": "not_confirmed",
        "weekly_trend": "not_confirmed", "risk_reward": 2.4,
        "confirmation_15m": False,
    }


def _ctx(df_holder, row_holder, regime):
    return hz.CycleContext(
        scan_rows=row_holder["rows"],
        regime=regime,
        get_4h=lambda s: df_holder["df"],
        get_market_4h=lambda: df_holder["df"].iloc[:0],
    )


def _fresh(tmp):
    state = hz.blank_state()
    log = ForwardLog(os.path.join(tmp, "f.jsonl"))
    tracker = hz._tracker_with_sink(log)
    return state, log, tracker


def test_full_lifecycle_pending_to_close():
    tmp = tempfile.mkdtemp()
    df = _scripted_df()
    row = _row(df.index[0])
    regime = {"gate": "BLOCK", "regime": "RISK-OFF", "score": 35}
    state, log, tracker = _fresh(tmp)
    df_holder, row_holder = {"df": df.iloc[:2]}, {"rows": [row]}

    s1 = hz.run_cycle(_ctx(df_holder, row_holder, regime), state, log, tracker)
    assert s1["new_signals"] == 1 and s1["opened"] == 1
    pos = tracker.get(row["signal_id"])
    assert pos["entry"] == 100.0 and pos["status"] == "open_full"
    assert pos["bars_held"] == 1, "walk must start at the entry bar, not history"

    df_holder["df"] = df.iloc[:3]
    s2 = hz.run_cycle(_ctx(df_holder, row_holder, regime), state, log, tracker)
    assert tracker.get(row["signal_id"])["status"] == "open_runner"
    assert s2["opened"] == 0 and s2["new_signals"] == 0  # seen-signal dedupe

    df_holder["df"] = df
    s3 = hz.run_cycle(_ctx(df_holder, row_holder, regime), state, log, tracker)
    assert s3["closed"] == [row["signal_id"]]
    close = log.get_close(row["signal_id"])
    assert close is not None
    assert abs(close["blended_r"] - 0.3) < 1e-9
    assert close["exit_reason"] == "runner-stop"
    assert close["grade"] == "A"
    assert close["reached_plus_1r"] is True

    # events were logged through the tracker sink
    kinds = [e["event"] for e in log.get_events(row["signal_id"])]
    for expected in ("pending_entry", "opened", "tp1_taken", "closed"):
        assert expected in kinds, f"missing logged event {expected}"

    # state persistence round-trip
    hz.save_state({**state, "positions": tracker.positions},
                  os.path.join(tmp, "state.json"))
    reloaded = hz.load_state(os.path.join(tmp, "state.json"))
    assert reloaded["positions"][row["signal_id"]]["exit"]["blended_r"] == \
        close["blended_r"]

    # idempotent rerun: nothing new happens
    n_events = len(log.get_events(row["signal_id"]))
    s4 = hz.run_cycle(_ctx(df_holder, row_holder, regime), state, log, tracker)
    assert s4["closed"] == [] and s4["opened"] == 0
    assert len(log.get_events(row["signal_id"])) == n_events


def test_second_signal_while_busy_is_logged_and_skipped():
    tmp = tempfile.mkdtemp()
    df = _scripted_df()
    row = _row(df.index[0])
    regime = {"gate": "BLOCK", "regime": "RISK-OFF", "score": 35}
    state, log, tracker = _fresh(tmp)
    df_holder, row_holder = {"df": df.iloc[:2]}, {"rows": [row]}
    hz.run_cycle(_ctx(df_holder, row_holder, regime), state, log, tracker)

    row2 = dict(row)
    row2["signal_id"] = row["signal_id"].replace("09:30", "13:30")
    row2["signal_bar_start_at"] = df.index[1].isoformat()
    row_holder["rows"] = [row, row2]
    df_holder["df"] = df.iloc[:3]
    hz.run_cycle(_ctx(df_holder, row_holder, regime), state, log, tracker)

    evs = log.get_events(row2["signal_id"])
    assert any(e["event"] == "signal_skipped" for e in evs)
    assert len(tracker.positions) == 1, "never double-trade one symbol"


def test_replay_cached_bars_invariants():
    tmp = tempfile.mkdtemp()
    syms = ["NVDA", "SOFI"]
    dfs = {s: pd.read_pickle(os.path.join(CACHE, f"h4_{s}.pkl")) for s in syms}
    regime = {"gate": "BLOCK", "regime": "RISK-OFF", "score": 35}
    state, log, tracker = _fresh(tmp)
    start, end = 260, 320
    for k in range(start, end):
        rows = []
        for s in syms:
            r = eng.v54_classify(s, "T", dfs[s].iloc[:k + 1], None, regime, "4h")
            if r:
                rows.append(r)
        ctx = hz.CycleContext(
            scan_rows=rows, regime=regime,
            get_4h=lambda s, k=k: dfs[s].iloc[:k + 1],
            get_market_4h=lambda k=k: dfs["NVDA"].iloc[:k + 1].iloc[:0],
        )
        hz.run_cycle(ctx, state, log, tracker)

    assert state["runs"] == end - start
    assert set(log.signal_ids()) == set(state["seen_signal_ids"])
    for sid in log.signal_ids():
        snap = log.get_signal(sid)
        assert snap["v54_grade"] in ("A", "B", "C")
    # every logged close belongs to a closed tracker position
    for sid in state["close_logged"]:
        assert tracker.positions[sid]["status"] == "closed"
    # rerun of the final cycle is a no-op
    n_events = sum(len(log.get_events(s)) for s in log.signal_ids())
    k = end - 1
    rows = []
    for s in syms:
        r = eng.v54_classify(s, "T", dfs[s].iloc[:k + 1], None, regime, "4h")
        if r:
            rows.append(r)
    ctx = hz.CycleContext(
        scan_rows=rows, regime=regime,
        get_4h=lambda s: dfs[s].iloc[:k + 1],
        get_market_4h=lambda: dfs["NVDA"].iloc[:k + 1].iloc[:0],
    )
    hz.run_cycle(ctx, state, log, tracker)
    assert sum(len(log.get_events(s)) for s in log.signal_ids()) == n_events
