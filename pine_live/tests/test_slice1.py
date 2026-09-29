"""Slice 1 acceptance tests.

Run:  cd ~/workspace/quality-flow-scanner-v5 && python3 -m pytest pine_live/tests/ -x -q
"""

from __future__ import annotations

import glob
import json
import os
import pickle
import sys

import pandas as pd
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pine_backtest as pb
from pine_live.assertions import LiveInputError, assert_valid_bars
from pine_live.decompose import decompose_signal
from pine_live.live_path import evaluate_frame, evaluate_live
from pine_live.packets import PacketLog
from pine_live.replay import replay_packet

CACHE = os.path.join(REPO_ROOT, "backtest_cache", "v3")
SYMBOLS = sorted(
    os.path.basename(p)[3:-4]
    for p in glob.glob(os.path.join(CACHE, "h4_*.pkl"))
)


def load_cached(symbol: str) -> pd.DataFrame:
    with open(os.path.join(CACHE, f"h4_{symbol}.pkl"), "rb") as f:
        return pickle.load(f)


def cached_vintage(symbol: str, n: int) -> dict:
    return {
        "bars_source": "backtest_cache/v3 (cached replay, not live)",
        "bars_downloaded_at": "2026-09-18T00:00:00+00:00",
        "n_bars_downloaded": n,
    }


# ---------------------------------------------------------------- A6/A7 parity
def test_decompose_matches_reference_all_symbols():
    """The explain-mirror agrees with pine_buy_signal on every bar >= WARMUP,
    for every cached symbol. If the reference formula ever changes, this
    fails loudly instead of drifting silently."""
    checked = 0
    for sym in SYMBOLS:
        bars = load_cached(sym)
        ind = pb.add_pine_indicators(bars)
        for i in range(pb.WARMUP, len(bars)):
            d = decompose_signal(ind, i)
            assert d["decision"] == bool(pb.pine_buy_signal(ind, i)), (sym, i)
            assert d["reference_decision"] == d["decision"], (sym, i)
            checked += 1
    assert checked > 30000


def test_evaluate_frame_latest_bar_matches_reference():
    """The live path's packet decision equals the reference decision on the
    latest closed bar (guards the bar_index plumbing, not the math)."""
    for sym in ("NVDA", "BTC-USD", "SPY"):
        bars = load_cached(sym)
        log = PacketLog(os.path.join("/tmp", f"pl_test_{sym}.jsonl"))
        pkt = evaluate_frame(sym, bars, cached_vintage(sym, len(bars)), log,
                             f"/tmp/pl_snap_{sym}", bar_index=len(bars) - 1)
        ind = pb.add_pine_indicators(bars)
        expected = "signal" if pb.pine_buy_signal(ind, len(bars) - 1) else "no_signal"
        assert pkt["decision"] == expected, sym


# ------------------------------------------------------- milestone: replay
def _replay_roundtrip(symbol: str, bar_index: int, tmp_path):
    bars = load_cached(symbol)
    log = PacketLog(str(tmp_path / "decisions.jsonl"))
    snap_dir = str(tmp_path / "snaps")
    pkt = evaluate_frame(symbol, bars, cached_vintage(symbol, len(bars)),
                         log, snap_dir, bar_index=bar_index)
    assert pkt["decision"] in ("signal", "no_signal")
    report = replay_packet(pkt)
    assert report["replayed"] is True
    assert report["exact"] is True, json.dumps(report["indicator_diffs"])
    assert report["decision_match"] is True
    return pkt


def test_replay_latest_bar_no_signal(tmp_path):
    """Milestone: one ticker/bar replayed from packet alone -> same decision."""
    pkt = _replay_roundtrip("NVDA", 992, tmp_path)  # latest cached bar
    assert pkt["decision"] == "no_signal"
    assert pkt["signal_bar_start"].startswith("2026-09-14")


def test_replay_known_signal_bar(tmp_path):
    """Same replay proof on a bar where V3.6 actually fired."""
    pkt = _replay_roundtrip("NVDA", 981, tmp_path)  # 2026-09-04 09:30 signal
    assert pkt["decision"] == "signal"
    subs = pkt["sub_conditions"]
    assert subs["confirmed"] or subs["breakout_buy"] or subs["ready_buy"]


def test_replay_rejects_tampered_snapshot(tmp_path):
    bars = load_cached("NVDA")
    log = PacketLog(str(tmp_path / "d.jsonl"))
    pkt = evaluate_frame("NVDA", bars, cached_vintage("NVDA", len(bars)),
                         log, str(tmp_path / "s"), bar_index=992)
    snap = pkt["bars_snapshot_ref"]["path"]
    with open(snap, "a") as f:
        f.write(" ")
    with pytest.raises(RuntimeError):
        replay_packet(pkt)


# ---------------------------------------------------------------- assertions
def test_assertions_reject_naive_index(tmp_path):
    bars = load_cached("NVDA").tz_localize(None)
    log = PacketLog(str(tmp_path / "d.jsonl"))
    pkt = evaluate_frame("NVDA", bars, cached_vintage("NVDA", len(bars)),
                         log, str(tmp_path / "s"))
    assert pkt["decision"] == "refused"
    assert "naive" in pkt["refused_reason"]


def test_warmup_refusal(tmp_path):
    bars = load_cached("NVDA").iloc[:100]  # < 215
    log = PacketLog(str(tmp_path / "d.jsonl"))
    pkt = evaluate_frame("NVDA", bars, cached_vintage("NVDA", 100),
                         log, str(tmp_path / "s"))
    assert pkt["decision"] == "refused"
    assert "warmup" in pkt["refused_reason"]
    assert pkt["bars_snapshot_ref"] is None  # refused before any snapshot


def test_assertions_reject_offgrid_bars():
    bars = load_cached("NVDA").copy()
    idx = bars.index.tolist()
    idx[300] = idx[300] + pd.Timedelta(minutes=7)  # knock one bar off grid
    bars.index = pd.DatetimeIndex(idx)
    with pytest.raises(LiveInputError):
        assert_valid_bars("NVDA", bars)


def test_forming_bar_rejected(tmp_path):
    bars = load_cached("NVDA")
    log = PacketLog(str(tmp_path / "d.jsonl"))
    # pretend "now" is 1 minute after the last bar opened: not closed yet
    fake_now = bars.index[-1] + pd.Timedelta(minutes=1)
    pkt = evaluate_frame("NVDA", bars, cached_vintage("NVDA", len(bars)),
                         log, str(tmp_path / "s"), now=fake_now)
    assert pkt["decision"] == "refused"
    assert "forming-bar" in pkt["refused_reason"]
    # but with a now after the bar close, the same frame evaluates fine
    real_now = bars.index[-1] + pd.Timedelta(hours=5)
    pkt2 = evaluate_frame("NVDA", bars, cached_vintage("NVDA", len(bars)),
                          log, str(tmp_path / "s"), now=real_now)
    assert pkt2["decision"] in ("signal", "no_signal")


# ------------------------------------------------------------------ packets
def test_packet_schema(tmp_path):
    bars = load_cached("NVDA")
    log = PacketLog(str(tmp_path / "d.jsonl"))
    pkt = evaluate_frame("NVDA", bars, cached_vintage("NVDA", len(bars)),
                         log, str(tmp_path / "s"), bar_index=981)
    for field in ("signal_id", "symbol", "timeframe", "signal_bar_start",
                  "signal_bar_close", "computed_at", "actionable_at",
                  "decision", "signal_bar_ohlcv", "indicators_at_i",
                  "sub_conditions", "entry_plan", "data_vintage",
                  "engine_version", "bars_snapshot_ref", "packet_schema"):
        assert field in pkt, field
    assert pkt["signal_id"].startswith("v36:NVDA:4h:")
    # every timestamp is tz-aware ISO
    for f in ("signal_bar_start", "signal_bar_close", "computed_at", "actionable_at"):
        assert pd.Timestamp(pkt[f]).tzinfo is not None, f
    # engine version pins the reference code
    ev = pkt["engine_version"]
    assert ev["repo_git_sha"] and len(ev["repo_git_sha"]) == 40
    assert set(ev["reference_sha256"]) == {"pine_backtest.py", "scanner_rules.py",
                                           "masterscanner_api.py"}
    # log is append-only JSONL
    assert len(log.read_all()) == 1


# ------------------------------------------------------- no side effects
BANNED_PATTERNS = (
    # import-level: pine_live must not import any of these itself
    "import requests", "from requests", "import urllib", "from urllib",
    "import smtplib", "from smtplib", "import websocket", "from websocket",
    "import fastapi", "from fastapi", "import uvicorn", "from uvicorn",
    "import yfinance", "from yfinance",
    # usage-level: no direct data download, no alert/trade/send surface
    "yf.download", "yf.", "send_alert", "place_order",
    "telegram", "slack", "discord", "webhook",
    "alpaca", "ib_insync", "broker",
)


def test_no_side_effect_channels_static():
    """pine_live may not contain alert/trading/network code. The ONLY network
    call in the slice is download_data inside the imported reference module."""
    live_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for path in glob.glob(os.path.join(live_dir, "*.py")):
        with open(path) as f:
            src = f.read()
        for pat in BANNED_PATTERNS:
            assert pat not in src, (os.path.basename(path), pat)
    with open(os.path.join(live_dir, "live_path.py")) as f:
        src = f.read()
    assert "pine_buy_signal" in src  # decision comes from the canonical fn
    assert "from masterscanner_api import download_data" in src


def test_runtime_writes_only_to_given_dirs(tmp_path):
    live_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    before = set()
    for root, _, files in os.walk(live_dir):
        if "tests" in root or "__pycache__" in root:
            continue
        before.update(os.path.join(root, f) for f in files)
    bars = load_cached("AAPL")
    log = PacketLog(str(tmp_path / "d.jsonl"))
    evaluate_frame("AAPL", bars, cached_vintage("AAPL", len(bars)),
                   log, str(tmp_path / "s"), bar_index=len(bars) - 1)
    after = set()
    for root, _, files in os.walk(live_dir):
        if "tests" in root or "__pycache__" in root:
            continue
        after.update(os.path.join(root, f) for f in files)
    assert after == before  # nothing written outside the given dirs


def test_live_smoke_optional():
    """Real download -> packet -> replay. Skipped gracefully if offline."""
    import tempfile
    try:
        tmp = tempfile.mkdtemp()
        log = PacketLog(os.path.join(tmp, "d.jsonl"))
        pkt = evaluate_live("NVDA", period="6mo", packet_log=log,
                            snapshot_dir=os.path.join(tmp, "s"))
    except Exception as exc:  # network/vendor failure != code failure
        pytest.skip(f"live download unavailable: {exc}")
    assert pkt["decision"] in ("signal", "no_signal", "refused")
    if pkt["decision"] != "refused":
        assert replay_packet(pkt)["exact"] is True
