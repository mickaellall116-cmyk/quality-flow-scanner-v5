"""Slice 2 acceptance tests: ranking + sector cap + slot accounting.

Run:  cd ~/workspace/quality-flow-scanner-v5 && python3 -m pytest pine_live/tests/test_slice2.py -x -q

Acceptance contract (Mike):
  (1) deterministic per-decision replay — crafted contested bar -> exact
      take/skip/reason codes from packet + prior state alone;
  (2) full-window aggregate parity — the slice-2 event loop reproduces the
      locked C1 stack EXACTLY: 143 trades, +0.337R, +52.25%, DD 31.63%,
      Calmar 1.65 @4bps, identical accepted/rejected counts AND identical
      rejection-reason breakdowns (RANKED_OUT=94, SECTOR_CAP=16, NO_SLOT=0,
      RISK_CAP=10).
Any difference must map to the parity-spec mismatch taxonomy; nothing is
"close enough".
"""

from __future__ import annotations

import functools
import json
import os
import sys
from collections import defaultdict

import pandas as pd
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (REPO_ROOT,
           os.path.join(REPO_ROOT, "pine_ranking"),
           os.path.join(REPO_ROOT, "pine_exposure"),
           os.path.join(REPO_ROOT, "pine_signal_quality"),
           os.path.join(REPO_ROOT, "pine_stack")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pine_backtest as pb
import pine_stack
from pine_ranking import compute_features
from pine_signal_quality import load_benchmarks
from pine_exposure import SECTOR

from pine_live.portfolio import (
    NO_SLOT, RANKED_OUT, RISK_CAP, SECTOR_CAP, TAKEN,
    PortfolioState, reference_mark,
)
from pine_live.ranking import rs_score
from pine_live.sector import (
    FROZEN_SECTOR_SHA256, SECTOR_SHA256, UnknownSectorSymbol,
    sector_counts, sector_of,
)
from pine_live.packets import (
    PacketLog, append_portfolio_packet, build_portfolio_packet,
    engine_version_extended,
)
from pine_live.replay import replay_portfolio_decision

COST = pb.COSTS["4bps"]

# Locked C1 numbers (pine_stack/stack_results.json, @4bps).
LOCKED_C1 = {"trades": 143, "expectancy_net_r": 0.337,
             "total_return_pct": 52.25, "max_drawdown_pct": 31.63}
LOCKED_REASONS = {TAKEN: 143, RANKED_OUT: 94, SECTOR_CAP: 16,
                  NO_SLOT: 0, RISK_CAP: 10}


@functools.lru_cache(maxsize=1)
def _research():
    """Load the research window once: candidates, closes, frames, rs feats."""
    all_trades, closes, data, order_of, skipped_gap = pine_stack.load_bull()
    bench, _ = load_benchmarks()
    feats = compute_features(all_trades, data, bench)
    return all_trades, closes, data, bench, feats, skipped_gap


def _signal_id(tr) -> str:
    return f"v36:{tr['symbol']}:4h:{tr['signal_time']}"


def _run_full_window(packet_log=None, vintage=None, engine=None):
    """Drive the slice-2 state machine over the whole research window.

    Returns (state, taken_idx, packets) where packets is a list of
    (t, packet_dict, state_before_dict) for every timestamp with entries.
    """
    all_trades, closes, data, bench, feats, skipped_gap = _research()
    mark = lambda sym, t: reference_mark(closes, sym, t)  # noqa: E731
    state = PortfolioState(mark, COST)
    entries_by_t, exits_by_t = defaultdict(list), defaultdict(list)
    for idx, tr in enumerate(all_trades):
        entries_by_t[tr["entry_time"]].append(idx)
        exits_by_t[tr["exit_time"]].append(idx)
    times = sorted(set(entries_by_t) | set(exits_by_t))
    taken_idx = []
    idx_of = {}
    packets = []
    for t in times:
        state.advance_clock(t)
        exits = [{"symbol": all_trades[i]["symbol"],
                  "exit_px": all_trades[i]["exit"],
                  "reason": all_trades[i]["reason"],
                  "universe_order": i}
                 for i in sorted(exits_by_t.get(t, []))]
        state.process_exits(t, exits)
        cand_idx = entries_by_t.get(t, [])
        if cand_idx:
            contenders = []
            for i in cand_idx:
                tr = all_trades[i]
                c = {"signal_id": _signal_id(tr), "symbol": tr["symbol"],
                     "entry_px": tr["entry"], "stop_px": tr["stop"],
                     "tp1_px": tr["tp1"], "rs_score": feats[i]["rs"],
                     "universe_order": i, "trade_idx": i}
                contenders.append(c)
                idx_of[c["signal_id"]] = i
            before = state.to_dict()
            seq_before = len(state.events)
            free_before = state.free_slots()
            n_open_before = state.n_open()
            counts_before = sector_counts(state.positions)
            decisions = state.decide_entries(t, contenders)
            for d in decisions:
                if d["decision"] == TAKEN:
                    taken_idx.append(idx_of[d["signal_id"]])
            state.settle(t)
            if packet_log is not None:
                packet = build_portfolio_packet(
                    decision_time=t, contenders=contenders, decisions=decisions,
                    free_slots_at_t=free_before, n_open_before=n_open_before,
                    n_open_after=state.n_open(),
                    sector_counts_before=counts_before,
                    sector_counts_after=sector_counts(state.positions),
                    seq_before=seq_before, seq_after=len(state.events),
                    vintage=vintage, engine=engine)
                stored = append_portfolio_packet(packet_log, packet)
                packets.append((t, stored, before))
        else:
            state.settle(t)
    return state, taken_idx, packets, all_trades, closes, skipped_gap


# ------------------------------------------------- reference-behavior pins
def test_sector_map_pinned_and_fail_closed():
    assert SECTOR_SHA256 == FROZEN_SECTOR_SHA256
    assert sector_of("nvda") == "SEMIS"  # case-insensitive lookup
    assert sector_of("BTC-USD") == "CRYPTO"
    with pytest.raises(UnknownSectorSymbol):
        sector_of("FAKE-SYMBOL")


def test_rs_score_matches_reference_on_all_candidates():
    """The live rs_score entry point is bit-identical to
    pine_ranking.compute_features (R1) on every research-window candidate.
    If the reference formula ever changes, this fails loudly."""
    all_trades, closes, data, bench, feats, _ = _research()
    spy = bench.get("SPY")
    assert spy is not None
    for idx, tr in enumerate(all_trades):
        df = data[tr["symbol"]]
        mine, reason = rs_score(df, tr["signal_idx"], spy)
        ref = feats[idx]["rs"]
        if ref == float("-inf"):
            assert mine == float("-inf"), (tr["symbol"], idx)
            assert reason is not None  # never silent
        else:
            assert reason is None, (tr["symbol"], idx, reason)
            assert mine == ref, (tr["symbol"], idx)


def test_slice2_modules_import_cleanly():
    import pine_live.ranking  # noqa: F401
    import pine_live.sector  # noqa: F401
    import pine_live.portfolio  # noqa: F401


# ------------------------------------------------- acceptance (2): full window
def test_full_window_reproduces_locked_c1_exactly(tmp_path):
    """The slice-2 event loop must reproduce pine_stack C1 bit-for-bit AND
    match the locked numbers. Any diff maps to the mismatch taxonomy."""
    log = PacketLog(str(tmp_path / "portfolio.jsonl"))
    vintage = {"bars_source": "backtest_cache/v3 (research-window replay)",
               "note": "slice-2 acceptance run"}
    engine = engine_version_extended()
    state, taken_idx, packets, all_trades, closes, skipped_gap = \
        _run_full_window(packet_log=log, vintage=vintage, engine=engine)

    # --- vs the live reference simulator (rules out stale JSON)
    pine_stack.rs = {id(tr): _research()[4][i]["rs"]
                     for i, tr in enumerate(all_trades)}
    port_ref = pine_stack.simulate_stack(all_trades, closes, COST,
                                         True, True, False, SECTOR)
    assert abs(state.realized - port_ref["final_equity"]) < 1e-6
    assert abs(state.max_dd - port_ref["max_drawdown"]) < 1e-9
    assert taken_idx == port_ref["taken"], "taken trade sets differ"
    assert state.counters[RANKED_OUT] == port_ref["skipped_rank"]
    assert state.counters[NO_SLOT] == port_ref["skipped_cap"]
    assert state.counters[SECTOR_CAP] == port_ref["skipped_gate"]
    assert state.counters[RISK_CAP] == port_ref["skipped_risk"]

    # --- vs the locked C1 numbers
    taken = [all_trades[i] for i in taken_idx]
    port = {"final_equity": state.realized, "max_drawdown": state.max_dd,
            "skipped_cap_count": (state.counters[RANKED_OUT]
                                  + state.counters[NO_SLOT]),
            "skipped_cap_risk": state.counters[RISK_CAP],
            "exposure": state.exposure()}
    row = pb.summarize("slice2-c1", taken, port, skipped_gap, "4bps")
    for k, v in LOCKED_C1.items():
        assert row[k] == v, (k, row[k], v)
    calmar = round(row["total_return_pct"] / row["max_drawdown_pct"], 2)
    assert calmar == 1.65, calmar

    # --- identical rejection-reason breakdowns
    for code, n in LOCKED_REASONS.items():
        assert state.counters[code] == n, (code, state.counters[code], n)

    # --- the first contested bar's packet replays exactly from
    # --- packet + prior state alone (acceptance (1) on real data)
    contested = [(t, p, b) for (t, p, b) in packets if p["contested"]]
    assert contested, "no contested bar found in the research window"
    t, packet, before = contested[0]
    mark = lambda sym, tt: reference_mark(closes, sym, tt)  # noqa: E731
    rep = replay_portfolio_decision(packet, before, mark)
    assert rep["replayed"] is True, rep
    assert rep["exact"] is True, rep["diffs"]


# ------------------------------------------------- acceptance (1): crafted bar
def _flat_mark(sym, t):
    return 100.0


def _contender(signal_id, symbol, rs, order, entry=50.0, stop=49.0, tp1=52.0):
    return {"signal_id": signal_id, "symbol": symbol, "entry_px": entry,
            "stop_px": stop, "tp1_px": tp1, "rs_score": rs,
            "universe_order": order}


def test_crafted_contested_bar_replay(tmp_path):
    """3 open (2x SEMIS + 1x CRYPTO), 1-2 free slots, 4 simultaneous
    signals. Replay from packet + prior state must reproduce exactly:
    INTC/MU -> SECTOR_CAP, MSFT -> TAKEN, CRM -> RANKED_OUT."""
    state = PortfolioState(_flat_mark, COST)
    t0 = pd.Timestamp("2026-09-17 13:30", tz="America/New_York")
    state.advance_clock(t0)
    pre = [_contender("v36:NVDA:4h:pre", "NVDA", 0.03, 0, 100.0, 98.0, 104.0),
           _contender("v36:AMD:4h:pre", "AMD", 0.02, 1, 100.0, 98.0, 104.0),
           _contender("v36:BTC-USD:4h:pre", "BTC-USD", 0.01, 2,
                      100.0, 98.0, 104.0)]
    d0 = state.decide_entries(t0, pre)
    assert [d["decision"] for d in d0] == [TAKEN, TAKEN, TAKEN]
    state.settle(t0)

    t1 = t0 + pd.Timedelta(hours=4)
    before = state.to_dict()
    seq_before = len(state.events)
    free_before = state.free_slots()
    n_open_before = state.n_open()
    counts_before = sector_counts(state.positions)
    assert free_before == 2

    contenders = [
        _contender("v36:INTC:4h:t1", "INTC", 0.05, 0),
        _contender("v36:MU:4h:t1", "MU", 0.03, 1),
        _contender("v36:MSFT:4h:t1", "MSFT", 0.02, 2),
        _contender("v36:CRM:4h:t1", "CRM", 0.01, 3),
    ]
    state.advance_clock(t1)
    decisions = state.decide_entries(t1, contenders)
    state.settle(t1)
    got = {d["symbol"]: d["decision"] for d in decisions}
    assert got == {"INTC": SECTOR_CAP, "MU": SECTOR_CAP,
                   "MSFT": TAKEN, "CRM": RANKED_OUT}, got
    assert [d["rank"] for d in decisions] == [1, 2, 3, 4]
    assert all(d["contested"] for d in decisions)

    log = PacketLog(str(tmp_path / "p.jsonl"))
    packet = build_portfolio_packet(
        decision_time=t1, contenders=contenders, decisions=decisions,
        free_slots_at_t=free_before, n_open_before=n_open_before,
        n_open_after=state.n_open(),
        sector_counts_before=counts_before,
        sector_counts_after=sector_counts(state.positions),
        seq_before=seq_before, seq_after=len(state.events),
        vintage={"note": "crafted contested-bar test"},
        engine=engine_version_extended())
    stored = append_portfolio_packet(log, packet)
    assert stored["packet_schema"] == "slice2-v2"

    rep = replay_portfolio_decision(stored, before, _flat_mark)
    assert rep["replayed"] is True, rep
    assert rep["exact"] is True, rep["diffs"]

    # Tamper check: replay against a WRONG prior state must not claim exact.
    wrong_before = dict(before)
    wrong_before["positions"] = {}
    rep2 = replay_portfolio_decision(stored, wrong_before, _flat_mark)
    assert rep2["replayed"] is False
