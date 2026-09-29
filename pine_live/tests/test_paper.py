"""Paper-phase tests (pine_live/paper/).

Fake in-memory provider, NO network. Covers:
  - first run sets watermarks and runs zero cycles
  - new-bar detection per symbol; cycles grouped by distinct bar_time in
    chronological order; mixed equity/crypto grids
  - exit-skip classification: misaligned expected, aligned-forced halts
  - ledger: theoretical vs fill + detection delay; trades link entry->exit
    with _outcome-consistent net R at both cost legs
  - dual ledger: achievable-vs-canonical fills (gap-up => achievable
    better, gap-down => achievable worse, no-gap => zero drag), bps and R
    deltas computed correctly, both ledgers reconcile; runner wiring
    end-to-end from pinned packets
  - verification halt: tampered packet -> HALT
  - report renders the three questions + the execution-realism section
    (dual R/trade, bps drag, proposed gate) from a synthetic ledger
  - production code never imports from pine_live.tests

Run: cd ~/workspace/quality-flow-scanner-v5 && \
     python3 -m pytest pine_live/tests/test_paper.py -x -q
"""

from __future__ import annotations

import json
import os
import pickle
import sys

import pandas as pd
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pine_backtest as pb
from pine_live.exits import _blended_exit_px
from pine_live.paper import dual as dual_ledger
from pine_live.paper.runner import WakeUp, FROZEN_COST
from pine_live.paper.ledger import read_jsonl
from pine_live.paper.report import (
    write_report, build_report, GATE_MIN_TRADES,
    GATE_MIN_ACH_EXPECTANCY_R, GATE_MAX_MEAN_DRAG_BPS)
from pine_live.paper.verify import (
    is_halted, verify_packet, verify_wake_up, write_halt,
)
from pine_live.paper import state as st

CACHE = os.path.join(REPO_ROOT, "backtest_cache", "v3")
T_A = pd.Timestamp("2025-05-29 13:30:00-04:00")  # NVDA entry bar (real signal)


@pytest.fixture(scope="module")
def frames():
    out = {}
    for sym in ("NVDA", "BTC-USD"):
        with open(os.path.join(CACHE, f"h4_{sym}.pkl"), "rb") as f:
            out[sym] = pickle.load(f)
    return out


@pytest.fixture()
def nvda_loc(frames):
    return int(frames["NVDA"].index.get_loc(T_A))


class FakeProvider:
    """In-memory versioned frames. Unknown symbols raise (download fail)."""

    def __init__(self, frames: dict):
        self.frames = dict(frames)

    def __call__(self, symbol: str) -> pd.DataFrame:
        s = str(symbol).upper()
        if s not in self.frames:
            raise RuntimeError(f"no fake frame for {s}")
        return self.frames[s]


def _wake(tmp_path, provider, tag="ps") -> WakeUp:
    wu = WakeUp(str(tmp_path / tag), provider=provider)
    # No network in tests: SPY unavailable -> exercises the A8 fallback.
    wu.download_spy = lambda: None
    return wu


def _synthetic_exit_bars():
    # ON the equity session grid: next session day 09:30 (trigger) and
    # 13:30 (fill bar). bar_close_at(09:30) == 13:30 so they chain.
    t3 = pd.Timestamp("2025-05-30 09:30:00-04:00")
    t4 = pd.Timestamp("2025-05-30 13:30:00-04:00")
    return pd.DataFrame(
        {"Open": [138.0, 135.5], "High": [139.0, 136.0],
         "Low": [133.0, 134.0], "Close": [134.0, 135.0],
         "Volume": [1e6, 1e6]},
        index=pd.DatetimeIndex([t3, t4], tz="America/New_York"))


# ------------------------------------------------------------------ first run
def test_first_run_sets_watermarks_zero_cycles(tmp_path, frames, nvda_loc):
    v1 = {"NVDA": frames["NVDA"].iloc[:nvda_loc],       # ends at signal bar
          "BTC-USD": frames["BTC-USD"].iloc[:500]}
    wu = _wake(tmp_path, FakeProvider(v1))
    assert wu.run_wake_up() == 0

    wm = st.load_watermarks(wu.state_dir)
    assert wm["NVDA"] == v1["NVDA"].index[-1].isoformat()
    assert wm["BTC-USD"] == v1["BTC-USD"].index[-1].isoformat()
    with open(os.path.join(wu.state_dir, "status.json")) as f:
        status = json.load(f)
    assert status["initialized"] is True
    assert status["cycles"] == []
    assert status["packets_replayed"] == 0
    # No packets written, no positions, no ledger decisions.
    assert read_jsonl(os.path.join(
        wu.state_dir, "ledger", "decisions.jsonl")) == []
    assert not os.path.exists(os.path.join(wu.state_dir, "packets.jsonl"))


# ------------------------------------------------------- new-bar detection
def test_new_bar_runs_one_cycle_takes_signal(tmp_path, frames, nvda_loc):
    v1 = {"NVDA": frames["NVDA"].iloc[:nvda_loc],
          "BTC-USD": frames["BTC-USD"].iloc[:500]}
    fp = FakeProvider(v1)
    assert _wake(tmp_path, fp, "ps1").run_wake_up() == 0  # init

    # One new bar: the NVDA entry bar -> exactly one cycle, signal TAKEN.
    fp.frames["NVDA"] = frames["NVDA"].iloc[:nvda_loc + 1]
    wu = _wake(tmp_path, fp, "ps1")
    assert wu.run_wake_up() == 0
    with open(os.path.join(wu.state_dir, "status.json")) as f:
        status = json.load(f)
    assert len(status["cycles"]) == 1
    c = status["cycles"][0]
    assert c["bar_time"] == T_A.isoformat()
    assert c["timestamp_status"] == "decided"
    assert c["n_new_packets"] > 0
    assert c["n_replayed"] == c["n_new_packets"]
    assert status["replay_mismatches"] == 0
    assert not is_halted(wu.state_dir)

    decisions = read_jsonl(os.path.join(
        wu.state_dir, "ledger", "decisions.jsonl"))
    nvda = [d for d in decisions if d["symbol"] == "NVDA"]
    assert len(nvda) == 1
    assert nvda[0]["decision"] == "TAKEN"
    assert nvda[0]["sector"] == "SEMIS"
    assert nvda[0]["bar_time"] == T_A.isoformat()

    fills = read_jsonl(os.path.join(wu.state_dir, "ledger", "fills.jsonl"))
    entries = [f for f in fills if f["kind"] == "entry"]
    assert len(entries) == 1
    e = entries[0]
    assert e["theoretical_px"] == e["paper_fill_px"]
    assert e["deviation_r"] == 0.0
    assert e["detection_delay_minutes"] is not None

    # Watermark advanced to the processed bar.
    wm = st.load_watermarks(wu.state_dir)
    assert wm["NVDA"] == T_A.isoformat()


def test_mixed_grids_chronological_order(tmp_path, frames, nvda_loc):
    v1 = {"NVDA": frames["NVDA"].iloc[:nvda_loc],
          "BTC-USD": frames["BTC-USD"].iloc[:500]}
    fp = FakeProvider(v1)
    sd = str(tmp_path / "ps")
    assert _wake(tmp_path, fp, "ps").run_wake_up() == 0

    # New bars on both grids at distinct times: BTC first, then NVDA t3/t4.
    t_btc = v1["BTC-USD"].index[-1] + pd.Timedelta(hours=4)
    btc_new = pd.DataFrame(
        {"Open": [100.0], "High": [101.0], "Low": [99.0], "Close": [100.5],
         "Volume": [10.0]},
        index=pd.DatetimeIndex([t_btc], tz="UTC"))
    fp.frames["BTC-USD"] = pd.concat([v1["BTC-USD"], btc_new])
    fp.frames["NVDA"] = pd.concat(
        [frames["NVDA"].iloc[:nvda_loc + 1], _synthetic_exit_bars()])
    wu = _wake(tmp_path, fp, "ps")
    assert wu.run_wake_up() == 0

    with open(os.path.join(sd, "status.json")) as f:
        status = json.load(f)
    # init(0) + T_A(1) + t_btc/t3/t4(3) = 4 cycles, chronological.
    bars = [c["bar_time"] for c in status["cycles"]]
    assert len(bars) == 4, bars
    assert bars == sorted(bars), bars
    assert not is_halted(sd)


# ------------------------------------------------------- exit-skip classes
def test_misaligned_exit_skip_is_expected_not_halt(tmp_path, frames,
                                                   nvda_loc):
    v1 = {"NVDA": frames["NVDA"].iloc[:nvda_loc],
          "BTC-USD": frames["BTC-USD"].iloc[:500]}
    fp = FakeProvider(v1)
    sd = str(tmp_path / "ps")
    assert _wake(tmp_path, fp, "ps").run_wake_up() == 0
    fp.frames["NVDA"] = frames["NVDA"].iloc[:nvda_loc + 1]
    assert _wake(tmp_path, fp, "ps").run_wake_up() == 0  # NVDA TAKEN

    # Only BTC has a new bar -> NVDA exit walk cannot run (misaligned).
    t_btc = v1["BTC-USD"].index[-1] + pd.Timedelta(hours=4)
    btc_new = pd.DataFrame(
        {"Open": [100.0], "High": [101.0], "Low": [99.0], "Close": [100.5],
         "Volume": [10.0]},
        index=pd.DatetimeIndex([t_btc], tz="UTC"))
    fp.frames["BTC-USD"] = pd.concat([v1["BTC-USD"], btc_new])
    wu = _wake(tmp_path, fp, "ps")
    assert wu.run_wake_up() == 0
    assert not is_halted(wu.state_dir)

    rej = read_jsonl(os.path.join(wu.state_dir, "ledger", "rejections.jsonl"))
    skips = [r for r in rej
             if r["reason"] == "exit_skip_misaligned_expected"]
    assert len(skips) == 1 and skips[0]["symbol"] == "NVDA"
    with open(os.path.join(wu.state_dir, "status.json")) as f:
        status = json.load(f)
    btc_cycle = [c for c in status["cycles"]
                 if c["bar_time"] == t_btc.isoformat()][0]
    assert btc_cycle["exit_skips_expected"] == 1


def test_aligned_exit_skip_halts(tmp_path, frames, nvda_loc):
    v1 = {"NVDA": frames["NVDA"].iloc[:nvda_loc],
          "BTC-USD": frames["BTC-USD"].iloc[:500]}
    fp = FakeProvider(v1)
    sd = str(tmp_path / "ps")
    assert _wake(tmp_path, fp, "ps").run_wake_up() == 0
    fp.frames["NVDA"] = frames["NVDA"].iloc[:nvda_loc + 1]
    assert _wake(tmp_path, fp, "ps").run_wake_up() == 0  # NVDA TAKEN

    # Corrupt the frame: drop the entry bar but keep a new bar at t3.
    # get_loc(t3) succeeds (aligned) but the entry_time lookup fails.
    t3 = T_A + pd.Timedelta(hours=4)
    dropped = frames["NVDA"].iloc[:nvda_loc + 1].drop(T_A)
    syn1 = _synthetic_exit_bars().iloc[:1]
    fp.frames["NVDA"] = pd.concat([dropped, syn1])
    wu = _wake(tmp_path, fp, "ps")
    assert wu.run_wake_up() == 2
    assert is_halted(wu.state_dir)
    with open(os.path.join(wu.state_dir, "HALT")) as f:
        halt = json.load(f)
    assert halt["classification"]["category"] == 6
    assert "aligned symbol NVDA" in halt["reason"]


# ------------------------------------------------------- fills + trades
def test_full_trade_lifecycle_ledger(tmp_path, frames, nvda_loc):
    v1 = {"NVDA": frames["NVDA"].iloc[:nvda_loc],
          "BTC-USD": frames["BTC-USD"].iloc[:500]}
    fp = FakeProvider(v1)
    sd = str(tmp_path / "ps")
    assert _wake(tmp_path, fp, "ps").run_wake_up() == 0
    fp.frames["NVDA"] = frames["NVDA"].iloc[:nvda_loc + 1]
    assert _wake(tmp_path, fp, "ps").run_wake_up() == 0  # entry at T_A

    # Synthetic stop-out: t3 triggers, t4 fills at its open (135.5).
    fp.frames["NVDA"] = pd.concat(
        [frames["NVDA"].iloc[:nvda_loc + 1], _synthetic_exit_bars()])
    wu = _wake(tmp_path, fp, "ps")
    assert wu.run_wake_up() == 0
    assert not is_halted(wu.state_dir)

    trades = read_jsonl(os.path.join(sd, "ledger", "trades.jsonl"))
    assert len(trades) == 1
    tr = trades[0]
    assert tr["symbol"] == "NVDA"
    assert tr["exit_reason"] == "stop"
    assert tr["exit_px"] == 135.5
    assert tr["hold_bars"] == 2
    # _outcome-consistent net R at both cost legs.
    _, _, want4, _ = pb._outcome(tr["entry_px"], tr["stop_px"],
                                 tr["exit_px"], pb.COSTS["4bps"])
    _, _, want25, _ = pb._outcome(tr["entry_px"], tr["stop_px"],
                                  tr["exit_px"], pb.COSTS["25bps"])
    assert tr["net_r_4bps"] == pytest.approx(want4)
    assert tr["net_r_25bps"] == pytest.approx(want25)
    assert tr["gross_r"] == pytest.approx(
        pb._outcome(tr["entry_px"], tr["stop_px"], tr["exit_px"],
                    pb.COSTS["4bps"])[1])
    assert tr["entry_time"] == T_A.isoformat()

    fills = read_jsonl(os.path.join(sd, "ledger", "fills.jsonl"))
    kinds = sorted(f["kind"] for f in fills)
    assert kinds == ["entry", "exit"]
    for f in fills:
        assert f["theoretical_px"] == f["paper_fill_px"]
        assert f["deviation_r"] == 0.0
        assert f["detection_delay_minutes"] >= 0
    # Entry fill carries no modeled cost; exit carries the round-trip leg.
    by_kind = {f["kind"]: f for f in fills}
    assert by_kind["entry"]["cost_dollars"] == 0.0
    assert by_kind["exit"]["cost_dollars"] == pytest.approx(
        pb.COSTS["4bps"] * by_kind["exit"]["size"])


# ------------------------------------------------------- verification halt
def test_tampered_packet_halts(tmp_path, frames, nvda_loc):
    v1 = {"NVDA": frames["NVDA"].iloc[:nvda_loc + 1],
          "BTC-USD": frames["BTC-USD"].iloc[:500]}
    wu = _wake(tmp_path, FakeProvider(v1), "psv")
    assert wu.run_wake_up() == 0  # init only (watermarks at latest)
    # Manually drive one packet through the real writer, then tamper.
    from pine_live.packets import PacketLog
    from pine_live.live_path import evaluate_frame
    plog = PacketLog(os.path.join(wu.state_dir, "packets.jsonl"))
    snap_dir = os.path.join(wu.state_dir, "snapshots")
    pkt = evaluate_frame("NVDA", v1["NVDA"], {"t": "x"}, plog, snap_dir,
                         bar_index=nvda_loc - 1, now=None)
    assert pkt["decision"] == "signal"
    tampered = dict(pkt)
    tampered["indicators_at_i"] = dict(pkt["indicators_at_i"])
    tampered["indicators_at_i"]["atr"] = float(
        pkt["indicators_at_i"]["atr"]) + 1.0

    rep = verify_packet(tampered, snapshot_dir=snap_dir, mark_fn=None,
                        state_before=None)
    assert rep["replayed"] is True
    assert rep["exact"] is False

    vrep = verify_wake_up(state_dir=wu.state_dir, new_packets=[tampered],
                          state_before_by_t={}, snapshot_dir=snap_dir,
                          mark_fn=None, fresh_provider=None)
    assert vrep["halted"] is True
    assert is_halted(wu.state_dir)
    with open(os.path.join(wu.state_dir, "HALT")) as f:
        halt = json.load(f)
    assert "replay mismatch" in halt["reason"]


def test_refused_packet_is_informational_not_mismatch(tmp_path):
    refused = {"type": "portfolio_refused", "packet_schema": "slice3-v1",
               "decision_time": "2025-06-02T13:30:00-04:00",
               "refused_reason": "decision_engine_exception: boom"}
    rep = verify_packet(refused, snapshot_dir=str(tmp_path), mark_fn=None,
                        state_before=None)
    assert rep["kind"] == "refused"
    assert rep["replayed"] is False
    vrep = verify_wake_up(state_dir=str(tmp_path / "hs2"),
                          new_packets=[refused], state_before_by_t={},
                          snapshot_dir=str(tmp_path), mark_fn=None)
    assert vrep["halted"] is False
    assert vrep["n_replayed"] == 0


def test_write_halt_roundtrip(tmp_path):
    d = str(tmp_path / "hs")
    os.makedirs(d)
    p = write_halt(d, reason="r", classification={"category": 2},
                   context={"k": "v"})
    assert is_halted(d)
    assert json.load(open(p))["reason"] == "r"


# ------------------------------------------------------- report
def _seed_ledger(state_dir, decisions, fills, trades, rejections, equity,
                 cycles):
    ld = os.path.join(state_dir, "ledger")
    os.makedirs(ld, exist_ok=True)

    def _w(name, rows):
        with open(os.path.join(ld, name + ".jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
    _w("decisions", decisions)
    _w("fills", fills)
    _w("trades", trades)
    _w("rejections", rejections)
    _w("equity", equity)
    with open(os.path.join(state_dir, "status.json"), "w") as f:
        json.dump({"schema": "x", "cycles": cycles, "packets_replayed": 7,
                   "replay_mismatches": 0, "flags": []}, f)


def test_report_three_questions_synthetic(tmp_path):
    sd = str(tmp_path / "rep")
    os.makedirs(sd)
    t = "2025-06-02T13:30:00-04:00"
    _seed_ledger(
        sd,
        decisions=[{"bar_time": t, "signal_id": "s1", "symbol": "NVDA",
                    "decision": "TAKEN", "reason_detail": "",
                    "rs_score": 0.05, "rank": 1, "contested": False,
                    "sector": "SEMIS", "marked_equity_at_t": 10000.0,
                    "risk_dollars": 100.0, "free_slots_at_t": 5}],
        fills=[{"kind": "entry", "bar_time": t, "signal_id": "s1",
                "symbol": "NVDA", "theoretical_px": 100.0,
                "paper_fill_px": 100.0, "deviation_r": 0.0,
                "cost_dollars": 0.0, "size": 60.0,
                "detection_delay_minutes": 12.5},
               {"kind": "exit", "bar_time": t, "signal_id": "s1",
                "symbol": "NVDA", "theoretical_px": 105.0,
                "paper_fill_px": 105.0, "deviation_r": 0.0,
                "cost_dollars": 2.4, "size": 60.0,
                "detection_delay_minutes": 12.5}],
        trades=[{"signal_id": "s1", "symbol": "NVDA", "sector": "SEMIS",
                 "entry_time": t, "exit_time": t, "entry_px": 100.0,
                 "stop_px": 97.0, "exit_px": 105.0, "exit_reason": "tp1",
                 "risk_dollars": 100.0, "size": 60.0, "hold_bars": 3,
                 "detection_delay_minutes": 12.5,
                 "gross_r": 1.5, "net_r_4bps": 1.48, "net_r_25bps": 1.42}],
        rejections=[{"bar_time": t, "symbol": "MSFT", "signal_id": None,
                     "reason": "no_signal", "detail": None}],
        equity=[{"bar_time": t, "marked_equity": 10148.0, "realized": 10148.0,
                 "peak": 10148.0, "max_dd": 0.0, "n_open": 0,
                 "detection_delay_minutes": 12.5}],
        cycles=[{"bar_time": t, "n_symbols": 2, "evaluated": 2, "signals": 1,
                 "skipped": 0, "pending_entry": 1, "timestamp_status":
                 "decided", "exit_evaluated": 0, "exit_skips_expected": 0,
                 "n_exits_applied": 0, "detection_delay_minutes": 12.5,
                 "n_new_packets": 2, "n_replayed": 2}])
    rep = write_report(sd)
    q1, q2, q3 = (rep["q1_spec_conformance"], rep["q2_cost_envelope"],
                  rep["q3_statistical_plausibility"])
    assert q1["cycles_run"] == 1
    assert q1["packets_replayed"] == 7
    assert q1["replay_mismatches"] == 0
    assert q1["completeness_ok"] is True
    assert q1["verdict"] == "CLEAN"
    assert q2["fills_match_theory"] is True
    assert q2["detection_delay_minutes"]["median"] == 12.5
    assert "paper fills assume execution at the bar open" in \
        q2["plain_english"]
    s4 = q3["at_4bps"]
    assert s4["n"] == 1 and s4["win_rate"] == 1.0
    assert s4["expectancy_r"] == pytest.approx(1.48)
    assert "cannot-reject, not proven" in q3["caveat"]
    md = open(os.path.join(sd, "report.md")).read()
    for h in ("Q1", "Q2", "Q3"):
        assert h in md
    assert os.path.exists(os.path.join(sd, "report.json"))


def test_report_empty_state(tmp_path):
    sd = str(tmp_path / "rep0")
    os.makedirs(sd)
    _seed_ledger(sd, [], [], [], [], [], [])
    rep = build_report(sd)
    assert rep["q1_spec_conformance"]["verdict"] == "CLEAN"
    assert rep["q3_statistical_plausibility"]["at_4bps"]["n"] == 0


# ------------------------------------------------------- static guards
def test_production_code_imports_no_tests():
    paper_dir = os.path.join(REPO_ROOT, "pine_live", "paper")
    for name in os.listdir(paper_dir):
        if not name.endswith(".py"):
            continue
        src = open(os.path.join(paper_dir, name)).read()
        assert "pine_live.tests" not in src, name
        assert "from tests" not in src, name


def test_no_network_in_paper_package():
    paper_dir = os.path.join(REPO_ROOT, "pine_live", "paper")
    for name in os.listdir(paper_dir):
        if not name.endswith(".py"):
            continue
        src = open(os.path.join(paper_dir, name)).read()
        assert "yf.download" not in src, name
        assert "requests." not in src, name


# ------------------------------------------------------- dual ledger
def _synth_exit_packet(tmp_path, trigger_t_iso, trigger_close):
    """Minimal slice5-v1-shaped packet with a two-bar pinned snapshot."""
    snap_path = str(tmp_path / "snap_exit.json")
    bars = [
        {"t": "2025-05-30T09:30:00-04:00", "o": 138.0, "h": 139.0,
         "l": 133.0, "c": 134.0, "v": 1e6, "e21": 1.0, "e55": 1.0,
         "e200": 1.0, "atr": 2.0},
        {"t": trigger_t_iso, "o": 135.0, "h": 136.0, "l": 133.5,
         "c": trigger_close, "v": 1e6, "e21": 1.0, "e55": 1.0,
         "e200": 1.0, "atr": 2.0},
    ]
    with open(snap_path, "w") as f:
        json.dump({"symbol": "NVDA", "kind": "exit_walk_bars",
                   "index_tz": "America/New_York", "bars": bars}, f)
    return {"packet_schema": "slice5-v1",
            "trigger": {"trigger_bar_time": trigger_t_iso,
                        "tp1_hit": True},
            "position": {"entry_px": 102.0, "stop_px": 97.0,
                         "tp1_px": 106.0},
            "bars_snapshot_ref": {"path": snap_path}}


def test_dual_fill_price_helpers(tmp_path):
    # Entry: signal-bar close from the pinned signal packet.
    assert dual_ledger.achievable_entry_px(
        {"signal_bar_ohlcv": {"close": 100.0}}) == 100.0
    assert dual_ledger.achievable_entry_px({}) is None
    assert dual_ledger.achievable_entry_px(None) is None
    assert dual_ledger.achievable_entry_px(
        {"signal_bar_ohlcv": {"close": 0.0}}) is None
    # Exit: trigger-bar close from the pinned snapshot.
    pkt = _synth_exit_packet(tmp_path, "2025-05-30T13:30:00-04:00", 134.0)
    assert dual_ledger.achievable_trigger_close(pkt) == 134.0
    missing_bar = dict(pkt)
    missing_bar["trigger"] = {"trigger_bar_time": "2099-01-01T00:00:00"}
    assert dual_ledger.achievable_trigger_close(missing_bar) is None
    missing_file = dict(pkt)
    missing_file["bars_snapshot_ref"] = {"path": "/no/such/file.json"}
    assert dual_ledger.achievable_trigger_close(missing_file) is None
    assert dual_ledger.achievable_trigger_close(None) is None
    assert dual_ledger.achievable_trigger_close({}) is None


def _dual_case(entry_canon, entry_ach, exit_fill_canon, exit_fill_ach,
               tp_hit=True, risk_dollars=100.0):
    """One synthetic long: signal close 100, ATR 2 -> stop 97 (pinned).

    Returns (atrade, drag, exit_canon, canon_net_r_4bps)."""
    stop = 97.0
    tp1_canon = entry_canon + 4.0          # reference: tp1 = entry + 2*ATR
    exit_canon, _, _, _, _ = _blended_exit_px(
        entry_canon, stop, tp1_canon, tp_hit, exit_fill_canon)
    atrade = dual_ledger.achievable_trade(
        entry_px=entry_canon, stop_px=stop, tp1_px=tp1_canon,
        tp_hit=tp_hit, ach_entry_px=entry_ach,
        ach_exit_fill_px=exit_fill_ach)
    assert atrade is not None
    _, _, canon_n4, _ = pb._outcome(entry_canon, stop, exit_canon,
                                    pb.COSTS["4bps"])
    _, _, canon_n25, _ = pb._outcome(entry_canon, stop, exit_canon,
                                     pb.COSTS["25bps"])
    size = risk_dollars / ((entry_canon - stop) / entry_canon)
    drag = dual_ledger.trade_drag(
        net_r_4bps=canon_n4, net_r_25bps=canon_n25,
        ach_net_r_4bps=atrade["ach_net_r_4bps"],
        ach_net_r_25bps=atrade["ach_net_r_25bps"],
        risk_dollars=risk_dollars, size=size, entry_px=entry_canon)
    assert drag is not None
    return atrade, drag, exit_canon, canon_n4, size


def test_dual_gap_up_entry_achievable_better():
    # Overnight gap UP: canonical fills 102, achievable buys the signal
    # close at 100 -> achievable better -> NEGATIVE drag.
    atrade, drag, exit_canon, canon_n4, size = _dual_case(
        entry_canon=102.0, entry_ach=100.0,
        exit_fill_canon=109.0, exit_fill_ach=110.0)
    # TP1 re-anchored to the achievable entry: 100 + (106-102) = 104.
    assert atrade["ach_tp1_px"] == pytest.approx(104.0)
    want_exit, _, _, _, _ = _blended_exit_px(100.0, 97.0, 104.0, True,
                                             110.0)
    assert atrade["ach_exit_px"] == pytest.approx(want_exit)
    _, _, want_n4, _ = pb._outcome(100.0, 97.0, want_exit,
                                   pb.COSTS["4bps"])
    assert atrade["ach_net_r_4bps"] == pytest.approx(want_n4)
    assert drag["drag_r_4bps"] == pytest.approx(canon_n4 - want_n4)
    assert drag["drag_r_4bps"] < 0, "gap-up entry must favor achievable"
    want_bps = drag["drag_r_4bps"] * 100.0 / size * 10000.0
    assert drag["drag_bps"] == pytest.approx(want_bps)
    assert drag["drag_bps"] < 0
    # Directional agreement with the independent price-drag formula (exact
    # equality only holds when risk_frac is unchanged; the entry gap
    # re-gears the achievable leg at constant risk dollars).
    px_drag = dual_ledger.round_trip_price_drag_bps(
        entry_px=102.0, ach_entry_px=100.0,
        exit_px=exit_canon, ach_exit_px=want_exit)
    assert px_drag < 0


def test_dual_gap_down_entry_achievable_worse():
    # Gap DOWN: canonical fills 98, achievable pays the signal close 100
    # -> achievable worse -> POSITIVE drag.
    atrade, drag, _, canon_n4, _ = _dual_case(
        entry_canon=98.0, entry_ach=100.0,
        exit_fill_canon=109.0, exit_fill_ach=110.0)
    assert atrade["ach_tp1_px"] == pytest.approx(104.0)
    assert drag["drag_r_4bps"] == pytest.approx(
        canon_n4 - atrade["ach_net_r_4bps"])
    assert drag["drag_r_4bps"] > 0, "gap-down entry must hurt achievable"
    assert drag["drag_bps"] > 0


def test_dual_no_gap_zero_drag():
    # No gaps anywhere: identical fills -> drag exactly zero, and the
    # achievable leg reproduces the canonical R.
    atrade, drag, exit_canon, canon_n4, _ = _dual_case(
        entry_canon=100.0, entry_ach=100.0,
        exit_fill_canon=110.0, exit_fill_ach=110.0, tp_hit=False)
    assert atrade["ach_exit_px"] == pytest.approx(exit_canon)
    assert atrade["ach_net_r_4bps"] == pytest.approx(canon_n4)
    assert drag["drag_r_4bps"] == pytest.approx(0.0)
    assert drag["drag_r_25bps"] == pytest.approx(0.0)
    assert drag["drag_bps"] == pytest.approx(0.0)
    # With no entry gap (same risk_frac) the R-based bps drag equals the
    # pure price-drag formula exactly.
    px_drag = dual_ledger.round_trip_price_drag_bps(
        entry_px=100.0, ach_entry_px=100.0,
        exit_px=exit_canon, ach_exit_px=atrade["ach_exit_px"])
    assert px_drag == pytest.approx(0.0)
    assert drag["drag_bps"] == pytest.approx(px_drag)


def test_achievable_fill_policy_documented(tmp_path):
    # The achievable fill source is a named, swappable policy: today's
    # conservative proxy for the hourly-polling architecture, upgrading to
    # first-actionable-quote when a real-time feed lands. Gate thresholds
    # must not move with the policy.
    assert dual_ledger.ACHIEVABLE_FILL_POLICY == \
        "signal-bar-close-at-detection"
    sd = str(tmp_path / "pold")
    os.makedirs(sd)
    _seed_ledger(sd, [], [], [], [], [], [])
    rep = build_report(sd)
    definition = rep["execution_realism"]["definition"]
    assert "signal-bar-close-at-detection" in definition
    assert "first-actionable-quote" in definition
    assert "conservative" in definition
    # Gate thresholds are policy-independent constants.
    assert GATE_MIN_TRADES == 20
    assert GATE_MIN_ACH_EXPECTANCY_R == 0.15
    assert GATE_MAX_MEAN_DRAG_BPS == 108.0


def test_dual_rejects_bad_inputs():
    assert dual_ledger.achievable_trade(
        entry_px=100.0, stop_px=97.0, tp1_px=104.0, tp_hit=True,
        ach_entry_px=None, ach_exit_fill_px=110.0) is None
    assert dual_ledger.achievable_trade(
        entry_px=100.0, stop_px=97.0, tp1_px=104.0, tp_hit=True,
        ach_entry_px=96.0, ach_exit_fill_px=110.0) is None  # through stop
    assert dual_ledger.trade_drag(
        net_r_4bps=1.0, net_r_25bps=1.0, ach_net_r_4bps=0.9,
        ach_net_r_25bps=0.9, risk_dollars=100.0, size=0.0,
        entry_px=100.0) is None
    assert dual_ledger.round_trip_price_drag_bps(
        entry_px=100.0, ach_entry_px=100.0, exit_px=110.0,
        ach_exit_px=None) is None


def test_dual_ledgers_reconcile():
    # Both ledgers reconcile: sum of per-trade dollar drags ==
    # canonical cum PnL - achievable cum PnL.
    cases = [
        _dual_case(102.0, 100.0, 109.0, 110.0),   # gap up: achievable better
        _dual_case(98.0, 100.0, 109.0, 110.0),    # gap down: achievable worse
        _dual_case(100.0, 100.0, 110.0, 110.0, tp_hit=False),  # no gap
    ]
    risk = 100.0
    canon_pnl = sum(c[3] * risk for c in cases)
    ach_pnl = sum(c[0]["ach_net_r_4bps"] * risk for c in cases)
    drag_dollars = sum(c[1]["drag_r_4bps"] * risk for c in cases)
    assert drag_dollars == pytest.approx(canon_pnl - ach_pnl)
    # bps drag is the dollar drag as bps of canonical notional (size).
    for (atrade, drag, _, _, size), entry_px in zip(
            cases, (102.0, 98.0, 100.0)):
        assert drag["drag_bps"] == pytest.approx(
            drag["drag_r_4bps"] * risk / size * 10000.0)


def test_dual_ledger_wired_through_runner(tmp_path, frames, nvda_loc):
    # Full lifecycle through the real runner: achievable fields must come
    # from the PINNED packets (signal-bar close / trigger-bar close).
    v1 = {"NVDA": frames["NVDA"].iloc[:nvda_loc],
          "BTC-USD": frames["BTC-USD"].iloc[:500]}
    fp = FakeProvider(v1)
    sd = str(tmp_path / "psd")
    assert _wake(tmp_path, fp, "psd").run_wake_up() == 0
    fp.frames["NVDA"] = frames["NVDA"].iloc[:nvda_loc + 1]
    assert _wake(tmp_path, fp, "psd").run_wake_up() == 0  # entry at T_A
    fp.frames["NVDA"] = pd.concat(
        [frames["NVDA"].iloc[:nvda_loc + 1], _synthetic_exit_bars()])
    wu = _wake(tmp_path, fp, "psd")
    assert wu.run_wake_up() == 0
    assert not is_halted(wu.state_dir)

    # Pinned sources of truth.
    sig_close = None
    for line in open(os.path.join(sd, "packets.jsonl")):
        p = json.loads(line)
        if p.get("decision") == "signal" and p.get("symbol") == "NVDA":
            sig_close = p["signal_bar_ohlcv"]["close"]
    assert sig_close is not None
    trig_close = None
    for line in open(os.path.join(sd, "exit_packets.jsonl")):
        p = json.loads(line)
        if p.get("packet_schema") == "slice5-v1":
            trig_t = p["trigger"]["trigger_bar_time"]
            snap = json.load(open(p["bars_snapshot_ref"]["path"]))
            trig_close = next(b["c"] for b in snap["bars"]
                              if b["t"] == trig_t)

    fills = read_jsonl(os.path.join(sd, "ledger", "fills.jsonl"))
    by_kind = {f["kind"]: f for f in fills}
    assert by_kind["entry"]["achievable_fill_px"] == pytest.approx(sig_close)
    assert by_kind["exit"]["achievable_fill_px"] == pytest.approx(trig_close)
    # Canonical legs untouched by the dual instrumentation.
    assert by_kind["entry"]["paper_fill_px"] == \
        by_kind["entry"]["theoretical_px"]
    assert by_kind["exit"]["paper_fill_px"] == \
        by_kind["exit"]["theoretical_px"]

    trades = read_jsonl(os.path.join(sd, "ledger", "trades.jsonl"))
    assert len(trades) == 1
    tr = trades[0]
    assert tr["ach_entry_px"] == pytest.approx(sig_close)
    assert tr["ach_exit_fill_px"] == pytest.approx(trig_close)
    # tp_hit False here (pure stop-out): achievable exit == trigger close.
    assert tr["ach_exit_px"] == pytest.approx(trig_close)
    _, _, want_ach_n4, _ = pb._outcome(
        tr["ach_entry_px"], tr["stop_px"], tr["ach_exit_px"],
        pb.COSTS["4bps"])
    assert tr["ach_net_r_4bps"] == pytest.approx(want_ach_n4)
    assert tr["drag_r_4bps"] == pytest.approx(
        tr["net_r_4bps"] - tr["ach_net_r_4bps"])
    assert tr["drag_bps"] == pytest.approx(
        tr["drag_r_4bps"] * tr["risk_dollars"] / tr["size"] * 10000.0)


def _dual_trade_row(i, ach_r4, drag_bps, risk=100.0):
    t = f"2025-06-{2 + i:02d}T13:30:00-04:00"
    return {"signal_id": f"s{i}", "symbol": "NVDA", "sector": "SEMIS",
            "entry_time": t, "exit_time": t, "entry_px": 100.0,
            "stop_px": 97.0, "exit_px": 105.0, "exit_reason": "tp1",
            "risk_dollars": risk, "size": 3333.0, "hold_bars": 3,
            "detection_delay_minutes": 12.5,
            "gross_r": 1.5, "net_r_4bps": ach_r4 + 0.05,
            "net_r_25bps": ach_r4 + 0.02,
            "ach_entry_px": 100.0, "ach_tp1_px": 104.0,
            "ach_exit_fill_px": 104.0, "ach_exit_px": 104.5,
            "ach_gross_r": ach_r4 + 0.01, "ach_net_r_4bps": ach_r4,
            "ach_net_r_25bps": ach_r4 - 0.03,
            "drag_r_4bps": 0.05, "drag_r_25bps": 0.05,
            "drag_bps": drag_bps}


def test_report_execution_realism_section(tmp_path):
    sd = str(tmp_path / "repd")
    os.makedirs(sd)
    t = "2025-06-02T13:30:00-04:00"
    _seed_ledger(
        sd,
        decisions=[{"bar_time": t, "signal_id": "s1", "symbol": "NVDA",
                    "decision": "TAKEN", "reason_detail": "",
                    "rs_score": 0.05, "rank": 1, "contested": False,
                    "sector": "SEMIS", "marked_equity_at_t": 10000.0,
                    "risk_dollars": 100.0, "free_slots_at_t": 5}],
        fills=[{"kind": "entry", "bar_time": t, "signal_id": "s1",
                "symbol": "NVDA", "theoretical_px": 100.0,
                "paper_fill_px": 100.0, "achievable_fill_px": 99.5,
                "deviation_r": 0.0, "cost_dollars": 0.0, "size": 60.0,
                "detection_delay_minutes": 12.5}],
        trades=[_dual_trade_row(0, ach_r4=0.20, drag_bps=50.0)],
        rejections=[], equity=[],
        cycles=[{"bar_time": t, "n_symbols": 2, "evaluated": 2, "signals": 1,
                 "skipped": 0, "pending_entry": 1, "timestamp_status":
                 "decided", "exit_evaluated": 0, "exit_skips_expected": 0,
                 "n_exits_applied": 0, "detection_delay_minutes": 12.5,
                 "n_new_packets": 2, "n_replayed": 2}])
    rep = write_report(sd)
    ex = rep["execution_realism"]
    assert ex["n_trades_dual"] == 1
    assert ex["n_trades_total"] == 1
    assert ex["canonical_r_per_trade_4bps"] == pytest.approx(0.25)
    assert ex["achievable_r_per_trade_4bps"] == pytest.approx(0.20)
    assert ex["mean_drag_bps_per_trade"] == pytest.approx(50.0)
    assert ex["median_drag_bps_per_trade"] == pytest.approx(50.0)
    # Realized equity curves reconcile with the per-trade R.
    assert ex["realized_equity_canonical"][-1][1] == pytest.approx(
        10000.0 + 0.25 * 100.0)
    assert ex["realized_equity_achievable"][-1][1] == pytest.approx(
        10000.0 + 0.20 * 100.0)
    g = ex["production_gate_proposed"]
    assert g["status"] == "INSUFFICIENT_DATA"
    assert g["gate_a"]["status"] == "INSUFFICIENT_DATA"
    md = open(os.path.join(sd, "report.md")).read()
    assert "Execution realism: canonical vs achievable" in md
    assert "INSUFFICIENT_DATA" in md


def test_report_gate_pass_fail(tmp_path):
    sd = str(tmp_path / "repg")
    os.makedirs(sd)
    # 20 dual trades: achievable expectancy +0.20R, mean drag 50bps.
    trades = [_dual_trade_row(i, ach_r4=0.20, drag_bps=50.0)
              for i in range(20)]
    _seed_ledger(sd, [], [], trades, [], [], [])
    rep = build_report(sd)
    g = rep["execution_realism"]["production_gate_proposed"]
    assert g["status"] == "FAIL"  # (a),(b) pass but (c) unattested
    assert g["gate_a"]["status"] == "PASS"
    assert g["gate_b"]["status"] == "PASS"
    assert g["gate_c"]["status"] == "NOT_ATTESTED"
    assert "real-time feed" in g["detail"]
    # Attest leg (c): the full gate passes.
    with open(os.path.join(sd, "gate_c_attestation.json"), "w") as f:
        json.dump({"attested_by": "Mike", "attested_at": "2026-09-18",
                   "feed": "realtime 4h bars", "latency": "quantified: 4h"},
                  f)
    g2 = build_report(sd)["execution_realism"]["production_gate_proposed"]
    assert g2["status"] == "PASS"
    assert g2["gate_c"]["status"] == "ATTESTED"
    # Failing leg (a): achievable expectancy +0.05R < +0.15R.
    sd2 = str(tmp_path / "repg2")
    os.makedirs(sd2)
    trades2 = [_dual_trade_row(i, ach_r4=0.05, drag_bps=50.0)
               for i in range(20)]
    _seed_ledger(sd2, [], [], trades2, [], [], [])
    g3 = build_report(sd2)["execution_realism"]["production_gate_proposed"]
    assert g3["status"] == "FAIL"
    assert g3["gate_a"]["status"] == "FAIL"
    # Failing leg (b): mean drag 200bps > 108bps.
    sd3 = str(tmp_path / "repg3")
    os.makedirs(sd3)
    trades3 = [_dual_trade_row(i, ach_r4=0.20, drag_bps=200.0)
               for i in range(20)]
    _seed_ledger(sd3, [], [], trades3, [], [], [])
    g4 = build_report(sd3)["execution_realism"]["production_gate_proposed"]
    assert g4["status"] == "FAIL"
    assert g4["gate_b"]["status"] == "FAIL"
