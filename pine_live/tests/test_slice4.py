"""Slice 4 acceptance tests: the multi-symbol live cycle.

Run:  cd ~/workspace/quality-flow-scanner-v5 && python3 -m pytest pine_live/tests/test_slice4.py -x -q

Mike's contract: one canonical cycle ingests all eligible symbols,
evaluates V3.6 through the reference path, applies ranking -> sector cap
-> 5% risk gate in the locked order, updates paper state deterministically,
and emits replayable packets for every accepted AND rejected decision.

Acceptance:
  (a) all 29 slice-1..3 tests still green (run the whole suite);
  (b) determinism: byte-identical rerun + symbol-order independence;
  (c) contested cross-sector scenario exercises ALL FOUR layers —
      V3.6 qualification (real signals), ranking contention (RANKED_OUT),
      sector cap (SECTOR_CAP), 5% risk gate (RISK_CAP) — with every reason
      code in the packet log and every decision replayable;
  (d) full-window aggregate parity: locked C1 reproduced EXACTLY through
      the cycle path (143 / +0.337R / 52.25% / 31.63% / 1.65, reason
      breakdowns incl. RISK_CAP=10);
  (e) failure drills: per-symbol download/assertion failures never poison
      the cycle; unknown sector fails closed with exact rollback;
  (f) static: no trading surface, no real-alert wiring; delivery layers
      still stdlib-only (causal separation preserved on the multi-symbol
      path: fault injection + enabled-vs-disabled inertness).

Reference-behavior pin (proven by sweep + full-window replay): within ONE
timestamp, RANKED_OUT and RISK_CAP are mutually exclusive under the locked
branch order (a veto freezes taken_at_t at k < min(2, free); a later
ranked-out would need k >= min(2, free) at the same free — impossible, and
no takes can intervene because heat only rises after a veto). The
four-layer scenario therefore uses two crafted timestamps in one scenario
run through the same cycle path; test_no_timestamp_has_both_codes pins the
property on real data.

Explicitly NOT built (out of scope): live exit generation (slice 5), the
Part-B reconciliation job (slice 6), real alert wiring, trading.
"""

from __future__ import annotations

import ast
import hashlib
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
import pine_live.live_path as lp
from pine_live.portfolio import (
    NO_SLOT, RANKED_OUT, RISK_CAP, SECTOR_CAP, TAKEN,
    PortfolioState, reference_mark,
)
from pine_live.sector import sector_counts
from pine_live.packets import PacketLog, _canonical, engine_version_extended
from pine_live.dedup import DedupStore
from pine_live.alerts import PaperOutbox, paper_sender, DELIVERY_CATEGORY
from pine_live.multicycle import run_cycle
from pine_live.replay import replay_portfolio_decision

from pine_live.tests.test_slice1 import BANNED_PATTERNS
from pine_live.tests.test_slice2 import (
    _research, COST, LOCKED_C1, LOCKED_REASONS,
)

LIVE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Research timestamps with >=3 simultaneous candidates (entry events).
T_A = pd.Timestamp("2025-05-29 13:30:00-04:00")  # NET, AVGO, NVDA (max-heat)
T_B = pd.Timestamp("2025-06-16 13:30:00-04:00")  # AMAT, PLTR, NVDA (contested)


def _sha(obj) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def research():
    all_trades, closes, data, bench, feats, skipped_gap = _research()
    # Cache indicator frames per symbol: evaluate_frame calls
    # add_pine_indicators per evaluation; the result is a pure function of
    # the frame, so memoizing is behavior-identical and keeps the suite fast.
    orig = lp.add_pine_indicators
    cache = {}

    def cached(bars):
        key = id(bars)
        if key not in cache:
            cache[key] = orig(bars)
        return cache[key]

    lp.add_pine_indicators = cached
    yield all_trades, closes, data, bench, feats, skipped_gap
    lp.add_pine_indicators = orig


def _provider_factory(data):
    def _p(symbol):
        return data[symbol]
    return _p


def _cycle_paths(tmp_path, tag):
    base = tmp_path / tag
    base.mkdir(exist_ok=True)
    return {
        "packet_log": PacketLog(str(base / "packets.jsonl")),
        "snapshot_dir": str(base / "snapshots"),
        "dedup": DedupStore(str(base / "dedup.jsonl")),
        "outbox": PaperOutbox(str(base / "outbox.jsonl")),
        "delivery_log": str(base / "delivery.jsonl"),
        "actions_log": str(base / "actions.jsonl"),
        "cycle_log": str(base / "cycle.jsonl"),
        "vintage": {"bars_source": "backtest_cache/v3 (research-window replay)",
                    "note": f"slice-4 {tag}"},
        "engine": engine_version_extended(),
    }


def _mark_flat(sym, t):
    return 100.0


def _seed_positions(symbols, t0, mark_fn, batch=2):
    """Seed open positions through decide_entries (batches of <=2: the
    locked ranking rule takes top min(2, free) at contested bars)."""
    st = PortfolioState(mark_fn, COST)
    st.advance_clock(t0)
    for b in range(0, len(symbols), batch):
        conts = [{"signal_id": f"v36:{s}:4h:seed", "symbol": s,
                  "entry_px": 100.0, "stop_px": 98.0, "tp1_px": 104.0,
                  "rs_score": 0.01, "universe_order": k}
                 for k, s in enumerate(symbols[b:b + batch])]
        d = st.decide_entries(t0, conts)
        assert all(x["decision"] == TAKEN for x in d), \
            [x["decision"] for x in d]
    st.settle(t0)
    return st


# ------------------------------------------------- (d) full-window parity
def _run_window_via_cycle(research, tmp_path, tag, delivery_enabled):
    all_trades, closes, data, bench, feats, skipped_gap = research
    spy = bench.get("SPY")
    assert spy is not None
    P = _cycle_paths(tmp_path, tag)
    provider = _provider_factory(data)
    mark = lambda sym, t: reference_mark(closes, sym, t)  # noqa: E731
    state = PortfolioState(mark, COST)

    entries_by_t, exits_by_t = defaultdict(list), defaultdict(list)
    for idx, tr in enumerate(all_trades):
        entries_by_t[tr["entry_time"]].append(idx)
        exits_by_t[tr["exit_time"]].append(idx)
    times = sorted(set(entries_by_t) | set(exits_by_t))

    by_signal_bar = defaultdict(list)  # entry event -> [(symbol, trade_idx)]
    for t in times:
        for i in entries_by_t.get(t, []):
            by_signal_bar[t].append((all_trades[i]["symbol"], i))

    per_t_codes = {}
    taken_idx = []
    idx_of = {}
    for t in times:
        exits = [{"symbol": all_trades[i]["symbol"],
                  "exit_px": all_trades[i]["exit"],
                  "reason": all_trades[i]["reason"],
                  "universe_order": i}
                 for i in sorted(exits_by_t.get(t, []))]
        syms = [s for s, _ in by_signal_bar.get(t, [])]
        # research cross-checks: the cycle's own evaluation must agree with
        # the research candidate set on every bar.
        for s, i in by_signal_bar.get(t, []):
            tr = all_trades[i]
            bars = data[s]
            loc = int(bars.index.get_loc(
                pd.Timestamp(t).tz_convert(bars.index.tz)))
            assert bars.index[tr["signal_idx"]] == bars.index[loc - 1], \
                (s, t, "signal bar is not the bar before the entry bar")
        rep = run_cycle(
            symbols=syms, bar_time=t, state=state, mark_fn=mark,
            packet_log=P["packet_log"], snapshot_dir=P["snapshot_dir"],
            vintage=P["vintage"], engine=P["engine"],
            dedup_store=P["dedup"] if delivery_enabled else None,
            outbox=P["outbox"] if delivery_enabled else None,
            delivery_log_path=P["delivery_log"],
            sender=paper_sender,
            actions_log_path=P["actions_log"] if delivery_enabled else None,
            cycle_log_path=P["cycle_log"],
            frame_provider=provider, spy_daily=spy,
            exits=exits, signal_bar="previous")
        ts = rep["timestamp"]
        assert ts["status"] in ("decided", "no_contenders"), (t, ts)
        # every research candidate must have produced a real signal packet
        # through the cycle's own slice-1 evaluation (layer 1, genuine)
        sig_ids = {e["signal_id"] for e in rep["signals"]}
        for s, i in by_signal_bar.get(t, []):
            tr = all_trades[i]
            want = f"v36:{s}:4h:{tr['signal_time']}"
            assert want in sig_ids, (s, t, "research candidate not signaled")
            idx_of[want] = i
        if ts["status"] == "decided":
            codes = [d["decision"] for d in ts["decisions"]]
            per_t_codes[str(t)] = codes
            for d in ts["decisions"]:
                # the cycle's contender prices must match the reference
                # research trade exactly (next-bar-open convention)
                tr = all_trades[idx_of[d["signal_id"]]]
                assert d["rs_score"] == feats[idx_of[d["signal_id"]]]["rs"]
                if d["decision"] == TAKEN:
                    taken_idx.append(idx_of[d["signal_id"]])
    return state, taken_idx, per_t_codes, all_trades, skipped_gap, P


def test_run_cycle_reproduces_locked_c1_exactly(research, tmp_path):
    """(d) The full research window driven through run_cycle (delivery
    enabled) reproduces locked C1 EXACTLY — the cycle path adds zero drift
    versus the slice-2/3 replay. The 5% risk gate is preserved: RISK_CAP=10.
    """
    state, taken_idx, per_t_codes, all_trades, skipped_gap, P = \
        _run_window_via_cycle(research, tmp_path, "parity", True)

    taken = [all_trades[i] for i in taken_idx]
    port = {"final_equity": state.realized, "max_drawdown": state.max_dd,
            "skipped_cap_count": (state.counters[RANKED_OUT]
                                  + state.counters[NO_SLOT]),
            "skipped_cap_risk": state.counters[RISK_CAP],
            "exposure": state.exposure()}
    row = pb.summarize("slice4-c1", taken, port, skipped_gap, "4bps")
    for k, v in LOCKED_C1.items():
        assert row[k] == v, (k, row[k], v)
    assert round(row["total_return_pct"] / row["max_drawdown_pct"], 2) == 1.65
    for code, n in LOCKED_REASONS.items():
        assert state.counters[code] == n, (code, state.counters[code], n)
    assert state.counters[RISK_CAP] == 10  # the gate, untouched

    # the cycle's contender prices must match the reference research trade
    # exactly (next-bar-open convention), for EVERY candidate — read from
    # the portfolio packet contenders, which carry entry/stop/TP1
    px_by_key = {}
    for p in _portfolio_packets(P["packet_log"]):
        for c in p["contenders"]:
            px_by_key[(p["decision_time"], c["signal_id"])] = c
    n_checked = 0
    for tr in all_trades:
        key = (pd.Timestamp(tr["entry_time"]).isoformat(),
               f"v36:{tr['symbol']}:4h:{tr['signal_time']}")
        c = px_by_key.get(key)
        assert c is not None, ("candidate missing from packet log", key)
        assert c["entry_px"] == tr["entry"], (key, c["entry_px"], tr["entry"])
        assert c["stop_px"] == tr["stop"], (key, c["stop_px"], tr["stop"])
        assert c["tp1_px"] == tr["tp1"], (key, c["tp1_px"], tr["tp1"])
        n_checked += 1
    assert n_checked == 263, n_checked

    # delivery: one paper alert per TAKEN, one claim per finalized decision
    assert P["outbox"].n_alerts() == 143
    assert P["dedup"].n_claimed() == 143 + 94 + 16 + 0 + 10

    # pin the mutual-exclusivity property on real data: no single timestamp
    # ever carries both RANKED_OUT and RISK_CAP (see module docstring)
    both = [t for t, codes in per_t_codes.items()
            if RANKED_OUT in codes and RISK_CAP in codes]
    assert not both, f"mutual-exclusivity violated at {both[:3]}"


# ------------------------------------------------- (b) determinism
def _scenario_cycle(research, tmp_path, tag, state, mark_fn, symbols, bar_time,
                    delivery_enabled=True, sender=paper_sender):
    all_trades, closes, data, bench, feats, skipped_gap = research
    P = _cycle_paths(tmp_path, tag)
    rep = run_cycle(
        symbols=symbols, bar_time=bar_time, state=state, mark_fn=mark_fn,
        packet_log=P["packet_log"], snapshot_dir=P["snapshot_dir"],
        vintage=P["vintage"], engine=P["engine"],
        dedup_store=P["dedup"] if delivery_enabled else None,
        outbox=P["outbox"] if delivery_enabled else None,
        delivery_log_path=P["delivery_log"], sender=sender,
        actions_log_path=P["actions_log"] if delivery_enabled else None,
        cycle_log_path=P["cycle_log"],
        frame_provider=_provider_factory(data), spy_daily=bench.get("SPY"),
        signal_bar="previous")
    return rep, P


def _crafted_state_B():
    """3 open (2x SEMIS + 1x CRYPTO): contested setup for T_B."""
    t0 = T_B - pd.Timedelta(days=1)
    return _seed_positions(["INTC", "MU", "BTC-USD"], t0, _mark_flat), t0


def test_cycle_deterministic_rerun(research, tmp_path):
    """(b) Same inputs + same prior state + same cycle run twice ->
    byte-identical decisions and byte-identical state."""
    state_before, _ = _crafted_state_B()
    before_dict = state_before.to_dict()

    s1 = PortfolioState.from_dict(before_dict, _mark_flat)
    rep1, _ = _scenario_cycle(research, tmp_path, "det1", s1, _mark_flat,
                             ["AMAT", "PLTR", "NVDA"], T_B)
    s2 = PortfolioState.from_dict(before_dict, _mark_flat)
    rep2, _ = _scenario_cycle(research, tmp_path, "det2", s2, _mark_flat,
                             ["AMAT", "PLTR", "NVDA"], T_B)
    assert rep1["timestamp"]["status"] == "decided"
    assert (_canonical(rep1["timestamp"]["decisions"])
            == _canonical(rep2["timestamp"]["decisions"]))
    assert _sha(s1.to_dict()) == _sha(s2.to_dict())


def test_cycle_order_independence(research, tmp_path):
    """(b) Symbol input order cannot affect outcomes: shuffled order (plus
    an extra no-signal symbol and mixed case) -> identical decisions and
    state. Ordering sensitivity would be a state/slot mismatch-class bug."""
    state_before, _ = _crafted_state_B()
    before_dict = state_before.to_dict()

    s1 = PortfolioState.from_dict(before_dict, _mark_flat)
    rep1, _ = _scenario_cycle(research, tmp_path, "ord1", s1, _mark_flat,
                             ["AMAT", "PLTR", "NVDA"], T_B)
    s2 = PortfolioState.from_dict(before_dict, _mark_flat)
    rep2, _ = _scenario_cycle(research, tmp_path, "ord2", s2, _mark_flat,
                             ["nvda", "MSFT", "amat", "pltr"], T_B)
    # MSFT has no signal at T_B: evaluated, no_signal, never a contender
    assert any(e["symbol"] == "MSFT" and e["decision"] == "no_signal"
               for e in rep2["evaluated"])
    assert (_canonical(rep1["timestamp"]["decisions"])
            == _canonical(rep2["timestamp"]["decisions"]))
    assert _sha(s1.to_dict()) == _sha(s2.to_dict())
    # canonical universe_order follows sorted symbols, never input order
    uo = {c["symbol"]: c["universe_order"] for c in rep2["contenders"]}
    assert uo == {"AMAT": 0, "NVDA": 2, "PLTR": 3}, uo


# ------------------------------------------------- (c) four-layer scenario
def _mark_heat(low_syms, low_px=99.5):
    def _m(sym, t):
        return low_px if sym in low_syms else 100.0
    return _m


def _portfolio_packets(packet_log):
    return [p for p in packet_log.read_all()
            if p.get("type") == "portfolio_decision"]


def test_four_layer_contested_scenario(research, tmp_path):
    """(c) Hardened: ALL FOUR strategic layers exercised through the cycle
    path in one scenario run, every rejection reason in the packet log:
      (1) V3.6 qualification — real signals via evaluate_frame;
      (2) ranking contention — RANKED_OUT at the contested bar;
      (3) sector cap — SECTOR_CAP (a would-be-taken signal, cap-blocked);
      (4) 5% risk gate — RISK_CAP veto at max heat (the whole point: the
          gate only engages at max-heat moments).
    T_A (max-heat): NET->SECTOR_CAP, AVGO/NVDA->RISK_CAP.
    T_B (contested): AMAT->SECTOR_CAP, PLTR->TAKEN, NVDA->RANKED_OUT.
    Every decision replays exactly from packet + prior state."""
    all_trades, closes, data, bench, feats, skipped_gap = research
    P = _cycle_paths(tmp_path, "scenario")
    provider = _provider_factory(data)
    spy = bench.get("SPY")

    # ---- T_A: max heat (4 open, heat 4.04% > 4%) ----
    priorA = ["MSFT", "CRM", "BTC-USD", "AAPL"]
    markA = _mark_heat(set(priorA))
    stA = _seed_positions(priorA, T_A - pd.Timedelta(days=1), markA)
    heat = (sum(p["risk_dollars"] for p in stA.positions.values())
            / stA.marked_equity(T_A))
    assert heat > 0.04, heat  # max-heat by construction
    beforeA = stA.to_dict()
    repA = run_cycle(symbols=["NET", "AVGO", "NVDA"], bar_time=T_A,
                     state=stA, mark_fn=markA, packet_log=P["packet_log"],
                     snapshot_dir=P["snapshot_dir"], vintage=P["vintage"],
                     engine=P["engine"], dedup_store=P["dedup"],
                     outbox=P["outbox"], delivery_log_path=P["delivery_log"],
                     sender=paper_sender, actions_log_path=P["actions_log"],
                     cycle_log_path=P["cycle_log"],
                     frame_provider=provider, spy_daily=spy,
                     signal_bar="previous")
    gotA = {d["symbol"]: d["decision"]
            for d in repA["timestamp"]["decisions"]}
    assert gotA == {"NET": SECTOR_CAP, "AVGO": RISK_CAP,
                    "NVDA": RISK_CAP}, gotA

    # ---- T_B: contested (3 open, 2x SEMIS) ----
    priorB = ["INTC", "MU", "BTC-USD"]
    stB = _seed_positions(priorB, T_B - pd.Timedelta(days=1), _mark_flat)
    beforeB = stB.to_dict()
    repB = run_cycle(symbols=["AMAT", "PLTR", "NVDA"], bar_time=T_B,
                     state=stB, mark_fn=_mark_flat, packet_log=P["packet_log"],
                     snapshot_dir=P["snapshot_dir"], vintage=P["vintage"],
                     engine=P["engine"], dedup_store=P["dedup"],
                     outbox=P["outbox"], delivery_log_path=P["delivery_log"],
                     sender=paper_sender, actions_log_path=P["actions_log"],
                     cycle_log_path=P["cycle_log"],
                     frame_provider=provider, spy_daily=spy,
                     signal_bar="previous")
    gotB = {d["symbol"]: d["decision"]
            for d in repB["timestamp"]["decisions"]}
    assert gotB == {"AMAT": SECTOR_CAP, "PLTR": TAKEN,
                    "NVDA": RANKED_OUT}, gotB

    # ---- all four layers visible in the packet log ----
    codes = {d["decision"]
             for p in _portfolio_packets(P["packet_log"])
             for d in p["decisions"]}
    assert TAKEN in codes and RANKED_OUT in codes \
        and SECTOR_CAP in codes and RISK_CAP in codes, codes
    # layer 1: every contender came from a genuine slice-1 signal packet
    assert len(repA["signals"]) == 3 and len(repB["signals"]) == 3

    # ---- every decision replays exactly from packet + prior state ----
    for (t, before, mark, rep) in (
            (T_A, beforeA, markA, repA), (T_B, beforeB, _mark_flat, repB)):
        pkts = [p for p in _portfolio_packets(P["packet_log"])
                if p["decision_time"] == pd.Timestamp(t).isoformat()]
        assert len(pkts) == 1, (t, len(pkts))
        r = replay_portfolio_decision(pkts[0], before, mark)
        # exact: the packet re-decides identically from prior state alone
        # (replay rebuilds contenders from the packet and re-runs the
        # locked decide_entries; any divergence lands in diffs)
        assert r["replayed"] is True and r["exact"] is True, (t, r["diffs"])


# ------------------------------------------------- causal separation (multi-symbol path)
def test_causal_inertness_multisymbol(research, tmp_path):
    """Delivery enabled vs PHYSICALLY DISABLED through run_cycle:
    byte-identical decisions and states. The delivery layer is observational
    on the multi-symbol path too — proven, not assumed."""
    priorA = ["MSFT", "CRM", "BTC-USD", "AAPL"]
    markA = _mark_heat(set(priorA))
    sA = _seed_positions(priorA, T_A - pd.Timedelta(days=1), markA)
    beforeA = sA.to_dict()

    bA, _ = _crafted_state_B()
    recs = []
    for tag, enabled in (("on", True), ("off", False)):
        sA = PortfolioState.from_dict(beforeA, markA)
        rA, _ = _scenario_cycle(research, tmp_path, f"inertA-{tag}", sA,
                               markA, ["NET", "AVGO", "NVDA"], T_A,
                               delivery_enabled=enabled)
        sB = PortfolioState.from_dict(bA.to_dict(), _mark_flat)
        rB, _ = _scenario_cycle(research, tmp_path, f"inertB-{tag}", sB,
                               _mark_flat, ["AMAT", "PLTR", "NVDA"], T_B,
                               delivery_enabled=enabled)
        recs.append((_canonical(rA["timestamp"]["decisions"]),
                     _canonical(rB["timestamp"]["decisions"]),
                     _sha(sA.to_dict()), _sha(sB.to_dict())))
    assert recs[0] == recs[1], "delivery layers altered multi-symbol decisions"


def test_fault_injection_cycle_sender_cannot_touch_state(research, tmp_path):
    """A raising alert sender mid-cycle through run_cycle: no raise, state
    hash identical to the control, decisions identical, category-7 logged."""
    def raising_sender(payload):
        raise RuntimeError("simulated delivery outage")

    b, _ = _crafted_state_B()
    before = b.to_dict()
    sA = PortfolioState.from_dict(before, _mark_flat)
    repA, PA = _scenario_cycle(research, tmp_path, "fault-good", sA,
                              _mark_flat, ["AMAT", "PLTR", "NVDA"], T_B)
    assert repA["timestamp"]["status"] == "decided"

    sB = PortfolioState.from_dict(before, _mark_flat)
    repB, PB = _scenario_cycle(research, tmp_path, "fault-bad", sB,
                              _mark_flat, ["AMAT", "PLTR", "NVDA"], T_B,
                              sender=raising_sender)
    assert repB["timestamp"]["status"] == "decided"
    assert _sha(sB.to_dict()) == _sha(sA.to_dict())
    assert (_canonical(repB["timestamp"]["decisions"])
            == _canonical(repA["timestamp"]["decisions"]))
    with open(PB["delivery_log"]) as f:
        events = [json.loads(l) for l in f if l.strip()]
    fails = [e for e in events if e.get("event") == "alert_delivery_failed"]
    assert fails and all(e["category"] == DELIVERY_CATEGORY for e in fails)


# ------------------------------------------------- (e) failure drills
def test_failure_drill_symbol_download_killed(research, tmp_path):
    """One symbol's frame provider raises mid-cycle: logged skip, the rest
    proceed, the cycle completes with a consistent state."""
    all_trades, closes, data, bench, feats, skipped_gap = research
    b, _ = _crafted_state_B()
    before = b.to_dict()
    s = PortfolioState.from_dict(before, _mark_flat)
    base_provider = _provider_factory(data)

    def flaky(symbol):
        if symbol == "PLTR":
            raise ConnectionError("simulated download kill")
        return base_provider(symbol)

    P = _cycle_paths(tmp_path, "dlkill")
    rep = run_cycle(symbols=["AMAT", "PLTR", "NVDA"], bar_time=T_B,
                    state=s, mark_fn=_mark_flat, packet_log=P["packet_log"],
                    snapshot_dir=P["snapshot_dir"], vintage=P["vintage"],
                    engine=P["engine"], dedup_store=P["dedup"],
                    outbox=P["outbox"], delivery_log_path=P["delivery_log"],
                    sender=paper_sender, actions_log_path=P["actions_log"],
                    cycle_log_path=P["cycle_log"],
                    frame_provider=flaky, spy_daily=bench.get("SPY"),
                    signal_bar="previous")
    assert rep["timestamp"]["status"] == "decided"
    assert any(x["symbol"] == "PLTR"
               and x["reason"] == "frame_provider_failed"
               for x in rep["skipped"])
    # AMAT/NVDA decided normally (both SEMIS, both cap-blocked; PLTR's
    # absence does not resurrect them — the cap is on the sector, not the bar)
    got = {d["symbol"]: d["decision"]
           for d in rep["timestamp"]["decisions"]}
    assert got == {"AMAT": SECTOR_CAP, "NVDA": SECTOR_CAP}, got
    with open(P["cycle_log"]) as f:
        events = [json.loads(l) for l in f if l.strip()]
    assert any(e["event"] == "symbol_skipped"
               and e["reason"] == "frame_provider_failed"
               for e in events)


def test_failure_drill_assertion_failure_skipped(research, tmp_path):
    """A symbol whose frame fails slice-1 assertions is SKIPPED with a
    logged reason — never evaluated on bad data; the rest proceed."""
    all_trades, closes, data, bench, feats, skipped_gap = research
    b, _ = _crafted_state_B()
    s = PortfolioState.from_dict(b.to_dict(), _mark_flat)
    base_provider = _provider_factory(data)

    bad = data["NVDA"].copy()
    # duplicate one bar timestamp: the frame is tz-aware and on-grid, so it
    # reaches slice-1 assertions, which must refuse it — never evaluated on
    # bad data. (High/Low cross-checks are NOT assertion invariants; the
    # reference tolerates them.)
    idx = bad.index.tolist()
    idx[500] = idx[501]
    bad.index = pd.DatetimeIndex(idx)

    def provider(symbol):
        return bad if symbol == "NVDA" else base_provider(symbol)

    P = _cycle_paths(tmp_path, "badframe")
    rep = run_cycle(symbols=["AMAT", "PLTR", "NVDA"], bar_time=T_B,
                    state=s, mark_fn=_mark_flat, packet_log=P["packet_log"],
                    snapshot_dir=P["snapshot_dir"], vintage=P["vintage"],
                    engine=P["engine"], dedup_store=P["dedup"],
                    outbox=P["outbox"], delivery_log_path=P["delivery_log"],
                    sender=paper_sender, actions_log_path=P["actions_log"],
                    cycle_log_path=P["cycle_log"],
                    frame_provider=provider, spy_daily=bench.get("SPY"),
                    signal_bar="previous")
    assert rep["timestamp"]["status"] == "decided"
    assert any(x["symbol"] == "NVDA" and x["reason"] == "evaluation_refused"
               for x in rep["skipped"])
    got = {d["symbol"]: d["decision"]
           for d in rep["timestamp"]["decisions"]}
    assert got == {"AMAT": SECTOR_CAP, "PLTR": TAKEN}, got


def test_failure_drill_unknown_sector_refuses_closed(research, tmp_path):
    """A symbol with a real signal but no sector label: the whole timestamp
    is refused with EXACT rollback (no partial entries), refusal logged,
    delivery layers never engaged. Fail closed."""
    all_trades, closes, data, bench, feats, skipped_gap = research
    b, _ = _crafted_state_B()
    before = b.to_dict()
    s = PortfolioState.from_dict(before, _mark_flat)

    def provider(symbol):
        # FAKE-SYMBOL reuses NVDA's frame: genuine signal, no sector label
        return data["NVDA"] if symbol == "FAKE-SYMBOL" else data[symbol]

    P = _cycle_paths(tmp_path, "unksec")
    rep = run_cycle(symbols=["FAKE-SYMBOL", "AMAT"], bar_time=T_B,
                    state=s, mark_fn=_mark_flat, packet_log=P["packet_log"],
                    snapshot_dir=P["snapshot_dir"], vintage=P["vintage"],
                    engine=P["engine"], dedup_store=P["dedup"],
                    outbox=P["outbox"], delivery_log_path=P["delivery_log"],
                    sender=paper_sender, actions_log_path=P["actions_log"],
                    cycle_log_path=P["cycle_log"],
                    frame_provider=provider, spy_daily=bench.get("SPY"),
                    signal_bar="previous")
    ts = rep["timestamp"]
    assert ts["status"] == "refused", ts
    # exact rollback: no entries taken, positions/counters/events identical
    # to before the cycle (the cycle clock still advances — documented
    # fail-closed semantics: clock accounting continues, nothing else moves)
    after = s.to_dict()
    for k in ("positions", "counters", "realized", "max_dd"):
        assert after[k] == before[k], (k, after[k], before[k])
    assert after["events"] == before["events"]
    # clock accounting advanced to the refused timestamp, nothing else moved
    assert after["prev_t"] == pd.Timestamp(T_B).isoformat(), after["prev_t"]
    refusals = [p for p in P["packet_log"].read_all()
                if p.get("type") == "portfolio_refused"]
    assert len(refusals) == 1
    assert P["outbox"].n_alerts() == 0
    assert P["dedup"].n_claimed() == 0


# ------------------------------------------------- (f) static proofs
def test_delivery_layers_still_stdlib_only():
    """Causal separation, structural (re-guarded for slice 4): dedup.py and
    alerts.py import stdlib ONLY — no path back to the decision engine."""
    for name in ("dedup.py", "alerts.py"):
        path = os.path.join(LIVE_DIR, name)
        tree = ast.parse(open(path).read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        imported.discard("__future__")
        non_stdlib = imported - set(sys.stdlib_module_names)
        assert not non_stdlib, (name, non_stdlib)
        assert not any(m.startswith("pine_live") for m in imported), (name, imported)


def test_multicycle_no_trading_or_remote_notification_surface():
    """multicycle.py: no trading surface, no remote-notification wiring.
    Alerts terminate at the caller-supplied local paper outbox."""
    src = open(os.path.join(LIVE_DIR, "multicycle.py")).read()
    for pat in BANNED_PATTERNS:
        assert pat not in src, ("multicycle.py", pat)
    for token in ("http://", "https://", "api_key", "API_KEY"):
        assert token not in src, ("multicycle.py", token)
    assert "paper_sender" in src  # default sender is the paper one
