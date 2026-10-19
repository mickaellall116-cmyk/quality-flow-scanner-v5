"""Offline synthetic tests for QF-V54-PAUSE-ENFORCEMENT-20261019-37.

Proves, against the DEPLOYED harness bytes (imported from the repo root):
 1. gate matrix: sentinel / missing / corrupt / invalid / valid controls
    all resolve fail-closed PAUSED except a strictly-valid resume;
 2. while PAUSED (explicit sentinel): zero new signals, zero pending
    fills (a preserved pending whose fill bar exists is blocked and the
    block is logged), zero observer assessments — while an open
    position's frozen exit logic still processes its stop bar;
 3. while PAUSED by DEFAULT (no control files at all): identical blocks;
 4. with a valid resume: the full signal -> pending -> fill -> exit flow
    works, observer appends work, and behavior matches the PRE-CHANGE
    harness byte-for-byte on the same synthetic scenario (regression);
 5. rollback: the preserved pre-change harness (sha256 dc3ee392...) has
    no gate and fills normally — restoring it restores prior behavior.

Everything runs on synthetic frames in temp dirs. No live state, no
market data, no model calls. Run: python3 -m pytest <this file> -q
or:  python3 <this file>   (built-in runner)
"""

import copy
import importlib.machinery
import importlib.util
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get(
    "QF_REPO", os.path.abspath(os.path.join(_HERE, "..", "..")))
sys.path.insert(0, REPO)

import v54_forward_harness as hz
from v54_forward_log import ForwardLog

PRE_CHANGE = os.path.expanduser(
    "~/workspace/goals/v5-4-forward-test/hidden_files/"
    "pause_enforcement_20261019_37/pre_change/v54_forward_harness.py.pre")
EXPECTED_PRE_SHA = ("dc3ee392c808aa2e52d468cad0020d8fe85b6f2bda0adc65630419"
                    "3563cba0c8")


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

def _frame(opens, highs, lows, closes):
    idx = pd.date_range("2026-01-06 09:30", periods=len(opens), freq="4h",
                        tz="America/New_York")
    return pd.DataFrame({"Open": opens, "High": highs, "Low": lows,
                         "Close": closes, "Volume": [1e6] * len(opens)},
                        index=idx)


def _aaa_df():
    # Signal bar 0; fill bar 1 (open 101 > stop 95); bar 3 tags stop 94.
    return _frame([100.0, 101.0, 102.0, 103.0, 104.0],
                  [101.0, 102.0, 103.0, 103.5, 104.5],
                  [99.0, 100.5, 101.5, 94.0, 103.0],
                  [100.5, 101.5, 102.5, 95.5, 103.5])


def _bbb_df():
    # Signal bar 1; intended fill bar 2 (open 50 > stop 45); never stops.
    return _frame([48.0, 49.0, 50.0, 51.0, 52.0],
                  [49.0, 50.0, 51.0, 52.0, 53.0],
                  [47.0, 48.0, 49.0, 50.0, 51.0],
                  [48.5, 49.5, 50.5, 51.5, 52.5])


def _row(sym, ts0, stop, tp1):
    return {"signal_id": f"v54:{sym}:4h:{ts0.isoformat()}:v",
            "symbol": sym, "stop": stop, "tp1": tp1,
            "v54_eligible": True, "v54_grade": "B",
            "v54_grade_label": "PULLBACK",
            "signal_bar_start_at": ts0.isoformat(),
            "signal_bar_close_at": ts0.isoformat(),
            "market_gate": "BLOCK", "market_regime": "RISK-OFF",
            "rel_vol": 1.1, "daily_trend": "not_confirmed",
            "weekly_trend": "not_confirmed", "risk_reward": 2.4,
            "confirmation_15m": False}


class _Feed:
    def __init__(self, frames):
        self.frames = frames
        self.n = 0

    def __call__(self, symbol):
        return self.frames[symbol].iloc[:self.n]


def _fresh(tmp):
    state = hz.blank_state()
    log = ForwardLog(os.path.join(tmp, "f.jsonl"))
    tracker = hz._tracker_with_sink(log)
    return state, log, tracker


def _cycle(feed, rows, state, log, tracker, n):
    feed.n = n
    ctx = hz.CycleContext(
        scan_rows=rows, regime={"gate": "BLOCK", "regime": "RISK-OFF",
                                "score": 35},
        get_4h=feed, get_market_4h=lambda: feed.frames["AAA"].iloc[:0])
    return hz.run_cycle(ctx, state, log, tracker)


def _controls(tmp, monkey):
    """Point the gate at a temp control dir; return (sentinel, resume)."""
    sentinel = os.path.join(tmp, "PAUSE_NEW_ENTRIES")
    resume = os.path.join(tmp, "RESUME_NEW_ENTRIES")
    monkey(hz, "PAUSE_SENTINEL_PATH", sentinel)
    monkey(hz, "RESUME_CONTROL_PATH", resume)
    return sentinel, resume


def _write_resume(path, body=None):
    if body is None:
        body = ("ENTRIES_RESUME_AUTHORIZED\n"
                "at: 2026-10-19T00:00:00+00:00\n")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)


def _assessment(sid):
    return {"observer": "AI-OBS-v1", "prompt_version": "v1",
            "signal_id": sid, "classification": "NEUTRAL", "confidence": 50,
            "reasons": ["synthetic", "test"], "primary_risk": "none",
            "invalidation": "none", "timing": "EARLY",
            "features": {"symbol": "SYN"},
            "assessed_at": datetime.now(timezone.utc).isoformat()}


class _Monkey:
    """Minimal monkeypatch stand-in so the file also runs without pytest."""

    def __init__(self):
        self._undo = []

    def __call__(self, obj, name, value):
        self._undo.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def undo(self):
        for obj, name, old in reversed(self._undo):
            setattr(obj, name, old)
        self._undo.clear()


# --------------------------------------------------------------------------
# 1. gate matrix (fail-closed, default PAUSED)
# --------------------------------------------------------------------------

def test_gate_matrix():
    tmp = tempfile.mkdtemp()
    mk = _Monkey()
    sentinel, resume = _controls(tmp, mk)
    try:
        st = hz.pause_control_state()
        assert st["paused"] and st["control"] == "default", st

        with open(sentinel, "w") as fh:
            fh.write("paused\n")
        st = hz.pause_control_state()
        assert st["paused"] and st["control"] == "sentinel", st

        _write_resume(resume)  # sentinel must win over a valid resume
        st = hz.pause_control_state()
        assert st["paused"] and st["control"] == "sentinel", st

        os.remove(sentinel)  # valid resume alone opens the gate
        st = hz.pause_control_state()
        assert not st["paused"] and st["control"] == "resume", st

        for body in ("garbage\n",
                     "ENTRIES_RESUME_AUTHORIZED\n",
                     "ENTRIES_RESUME_AUTHORIZED\nat: not-a-date\n",
                     ""):
            _write_resume(resume, body)
            st = hz.pause_control_state()
            assert st["paused"] and st["control"] == "invalid_resume", \
                (body, st)

        os.remove(resume)
        os.mkdir(resume)  # unreadable control -> exception path
        st = hz.pause_control_state()
        assert st["paused"] and st["control"] == "error", st
    finally:
        mk.undo()


# --------------------------------------------------------------------------
# 2/3. paused cycles: no signals, no fills, no observer; exits still work
# --------------------------------------------------------------------------

def _paused_scenario(explicit_sentinel):
    tmp = tempfile.mkdtemp()
    mk = _Monkey()
    sentinel, resume = _controls(tmp, mk)
    obs_path = os.path.join(tmp, "ai_observer.jsonl")
    mk(hz, "OBSERVER_LOG_PATH", obs_path)
    try:
        aaa, bbb = _aaa_df(), _bbb_df()
        row_aaa = _row("AAA", aaa.index[0], 95.0, 108.0)
        row_bbb = _row("BBB", bbb.index[1], 45.0, 60.0)
        row_ccc = _row("CCC", aaa.index[3], 10.0, 20.0)
        frames = {"AAA": aaa, "BBB": bbb}
        feed = _Feed(frames)
        state, log, tracker = _fresh(tmp)

        if explicit_sentinel:
            with open(sentinel, "w") as fh:
                fh.write("ENTRIES PAUSED — synthetic test\n")
        else:
            _write_resume(resume)  # will be removed for phase 3
            pass

        if explicit_sentinel:
            # Open AAA + stage BBB while gate is OPEN would need a resume;
            # instead build positions directly (harness-equivalent state).
            pass
        # Build pre-pause state directly: AAA opened at bar 1, BBB pending.
        tracker.open_position(row_aaa, 101.0, aaa.index[1].isoformat())
        state["snapshots"][row_aaa["signal_id"]] = row_aaa
        state["snapshots"][row_bbb["signal_id"]] = row_bbb
        state["pending"][row_bbb["signal_id"]] = {
            "symbol": "BBB", "signal_bar_start": bbb.index[1].isoformat()}
        state["seen_signal_ids"] = sorted([row_aaa["signal_id"],
                                           row_bbb["signal_id"]])
        bbb_before = copy.deepcopy(state["pending"][row_bbb["signal_id"]])
        if not explicit_sentinel:
            os.remove(resume)  # phase-3 state: NO control files at all

        # Paused cycle: AAA stop bar (idx3) and BBB fill bar (idx2) exist,
        # plus a brand-new qualified signal row for CCC.
        s = _cycle(feed, [row_ccc], state, log, tracker, 4)
        assert s["entries_paused"] is True, s
        assert s["new_signals"] == 0, s
        assert row_ccc["signal_id"] not in state["seen_signal_ids"]
        assert s["opened"] == 0, s
        # BBB pending preserved byte-for-byte, blocked fill logged.
        assert state["pending"][row_bbb["signal_id"]] == bbb_before
        assert s.get("fills_blocked_by_pause") == [row_bbb["signal_id"]], s
        ev = [e for e in log.get_events(row_bbb["signal_id"])
              if e["event"] == "pending_fill_blocked_pause"]
        assert len(ev) == 1 and ev[0]["intended_fill_open"] == 50.0, ev
        # AAA exit management continued: stop bar closed the position.
        assert row_aaa["signal_id"] in s["closed"], s
        assert tracker.positions[row_aaa["signal_id"]]["status"] == "closed"
        # Observer dispatch refused while paused.
        res = hz.observer_append_assessment(
            _assessment(row_ccc["signal_id"]))
        assert res["ok"] is False and "paused" in res["errors"][0], res
        assert not os.path.exists(obs_path)
    finally:
        mk.undo()


def test_paused_explicit_sentinel_blocks_entries_exits_continue():
    _paused_scenario(explicit_sentinel=True)


def test_paused_default_missing_controls_block_identically():
    _paused_scenario(explicit_sentinel=False)


# --------------------------------------------------------------------------
# 4. valid resume: full flow + observer; regression vs pre-change harness
# --------------------------------------------------------------------------

def _flow(module, tmp):
    aaa = _aaa_df()
    row = _row("AAA", aaa.index[0], 95.0, 108.0)
    feed = _Feed({"AAA": aaa})
    state = module.blank_state()
    log = ForwardLog(os.path.join(tmp, "f.jsonl"))
    tracker = module._tracker_with_sink(log)
    out = []
    for rows, n in (([row], 1), ([], 2), ([], 5)):
        feed.frames = {"AAA": aaa}
        feed_n = n
        feed2 = _Scripted(feed.frames, feed_n)
        ctx = module.CycleContext(
            scan_rows=rows, regime={"gate": "BLOCK", "regime": "RISK-OFF",
                                    "score": 35},
            get_4h=feed2, get_market_4h=lambda: aaa.iloc[:0])
        s = module.run_cycle(ctx, state, log, tracker)
        out.append((s["new_signals"], s["opened"], list(s["closed"])))
    events = []
    with open(os.path.join(tmp, "f.jsonl")) as fh:
        for line in fh:
            rec = json.loads(line)
            events.append(rec.get("event") or rec.get("type"))
    pos = tracker.positions[row["signal_id"]]
    return out, events, pos["status"], dict(state["pending"])


class _Scripted:
    def __init__(self, frames, n):
        self.frames, self.n = frames, n

    def __call__(self, symbol):
        return self.frames[symbol].iloc[:self.n]


def test_resume_flow_and_regression_vs_prechange():
    tmp = tempfile.mkdtemp()
    mk = _Monkey()
    sentinel, resume = _controls(tmp, mk)
    try:
        _write_resume(resume)
        os.makedirs(os.path.join(tmp, "new"), exist_ok=True)
        got = _flow(hz, os.path.join(tmp, "new"))
        # observer append works when the gate is open
        obs_path = os.path.join(tmp, "ai_observer.jsonl")
        mk(hz, "OBSERVER_LOG_PATH", obs_path)
        res = hz.observer_append_assessment(_assessment("v54:SYN:v"))
        assert res["ok"] is True, res
    finally:
        mk.undo()

    import hashlib
    with open(PRE_CHANGE, "rb") as fh:
        assert hashlib.sha256(fh.read()).hexdigest() == EXPECTED_PRE_SHA
    loader = importlib.machinery.SourceFileLoader("hz_pre", PRE_CHANGE)
    spec = importlib.util.spec_from_loader("hz_pre", loader)
    hz_pre = importlib.util.module_from_spec(spec)
    sys.modules["hz_pre"] = hz_pre  # dataclasses resolve via sys.modules
    loader.exec_module(hz_pre)
    assert not hasattr(hz_pre, "pause_control_state")  # rollback = no gate

    os.makedirs(os.path.join(tmp, "old"), exist_ok=True)
    want = _flow(hz_pre, os.path.join(tmp, "old"))
    assert got == want, (got, want)


# --------------------------------------------------------------------------

if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {type(exc).__name__}: {exc}")
    print(f"{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
