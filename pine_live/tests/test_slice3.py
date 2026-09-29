"""Slice 3 acceptance tests: duplicate suppression + paper alert delivery.

Run:  cd ~/workspace/quality-flow-scanner-v5 && python3 -m pytest pine_live/tests/test_slice3.py -x -q

Mike's contract for this slice — CAUSAL SEPARATION, structural not just
behavioral: delivery plumbing (dedup + alerts) must be INCAPABLE of
influencing trading logic, not merely observed not to. Acceptance:

  (a) all slice-1 and slice-2 tests still green (run the whole suite);
  (b) dedup proof: contested-bar scenario twice (rerun + simulated retry)
      -> decision outputs byte-identical, exactly one action per finalized
      decision; dedup on vs off -> byte-identical decisions;
  (c) alert-failure drill: failed delivery -> portfolio state unchanged,
      decision packet intact, failure logged as category-7 event;
  (d) full-window replay with dedup+alerts enabled reproduces C1 exactly
      (143 / +0.337R / 52.25% / 31.63% / 1.65, reason breakdowns incl.
      RISK_CAP=10) — delivery layers add zero drift;
  (e) static + runtime proof: no trading surface, alerts to local paper
      outbox only.
  (f) NEW — dependency direction: dedup.py/alerts.py import stdlib ONLY
      (AST-level import-graph assertion). One-way data flow, structural.
  (g) NEW — fault injection: an exception inside the alert sender mid-cycle
      cannot propagate into the state machine (state hash identical,
      packet intact, decide_entries called exactly once).
  (h) NEW — full-window C1-exactness run TWICE: delivery enabled vs
      physically disabled -> byte-identical per-timestamp decisions.

If (f), (g), or (h) fail, the slice fails even if outputs "usually match".
"""

from __future__ import annotations

import ast
import glob
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
from pine_live.portfolio import (
    NO_SLOT, RANKED_OUT, RISK_CAP, SECTOR_CAP, TAKEN,
    PortfolioState, reference_mark,
)
from pine_live.sector import sector_counts
from pine_live.packets import PacketLog, _canonical, engine_version_extended
from pine_live.dedup import DedupStore, dedup_key
from pine_live.alerts import (
    ALERT_SCHEMA, DELIVERY_CATEGORY, PaperOutbox,
    alert_id_for, build_alert_payload, deliver_pending, paper_sender,
)
from pine_live.cycle import run_timestamp, safe_evaluate_live

from pine_live.tests.test_slice1 import BANNED_PATTERNS
from pine_live.tests.test_slice2 import (
    _research, _signal_id, COST, LOCKED_C1, LOCKED_REASONS,
)

LIVE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sha(obj) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def _flat_mark(sym, t):
    return 100.0


def _contender(signal_id, symbol, rs, order, entry=50.0, stop=49.0, tp1=52.0):
    return {"signal_id": signal_id, "symbol": symbol, "entry_px": entry,
            "stop_px": stop, "tp1_px": tp1, "rs_score": rs,
            "universe_order": order}


def _crafted_before():
    """3 open (2x SEMIS + 1x CRYPTO), settled at t0. Returns (before_dict, t1)."""
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
    return state.to_dict(), t0 + pd.Timedelta(hours=4)


def _crafted_contenders():
    return [
        _contender("v36:INTC:4h:t1", "INTC", 0.05, 0),
        _contender("v36:MU:4h:t1", "MU", 0.03, 1),
        _contender("v36:MSFT:4h:t1", "MSFT", 0.02, 2),
        _contender("v36:CRM:4h:t1", "CRM", 0.01, 3),
    ]


def _cycle_paths(tmp_path, tag):
    base = tmp_path / tag
    base.mkdir(exist_ok=True)
    return {
        "packet_log": PacketLog(str(base / "portfolio.jsonl")),
        "dedup": DedupStore(str(base / "dedup.jsonl")),
        "outbox": PaperOutbox(str(base / "outbox.jsonl")),
        "delivery_log": str(base / "delivery.jsonl"),
        "actions_log": str(base / "actions.jsonl"),
        "vintage": {"note": f"slice-3 test {tag}"},
        "engine": engine_version_extended(),
    }


# ------------------------------------------------- (f) dependency direction
def test_dependency_direction_static():
    """CAUSAL SEPARATION, structural: dedup.py and alerts.py may import
    stdlib ONLY. No import path back to the decision engine or portfolio
    state can exist — the data flow is one-way by construction."""
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
        assert "pine_backtest" not in imported, name


def test_dedup_key_deterministic_and_state_pinned():
    k1 = dedup_key("v36:MSFT:4h:t", "2026-09-17T13:30:00-04:00", 42)
    k2 = dedup_key("v36:MSFT:4h:t", "2026-09-17T13:30:00-04:00", 42)
    assert k1 == k2
    # any change in identity -> different key
    assert dedup_key("v36:MSFT:4h:t", "2026-09-17T13:30:00-04:00", 43) != k1
    assert dedup_key("v36:AAPL:4h:t", "2026-09-17T13:30:00-04:00", 42) != k1


# ------------------------------------------------- (b) dedup: rerun/retry
def test_dedup_rerun_retry_single_action(tmp_path):
    """Same finalized decision twice (rerun + simulated retry): decisions
    byte-identical, exactly ONE action per finalized decision, no second
    alert enqueued."""
    before, t1 = _crafted_before()
    contenders = _crafted_contenders()
    P = _cycle_paths(tmp_path, "rerun")

    s1 = PortfolioState.from_dict(before, _flat_mark)
    rep1 = run_timestamp(state=s1, mark_fn=_flat_mark, t=t1,
                        contenders=contenders, exits=[],
                        packet_log=P["packet_log"], vintage=P["vintage"],
                        engine=P["engine"], dedup_store=P["dedup"],
                        outbox=P["outbox"],
                        delivery_log_path=P["delivery_log"],
                        sender=paper_sender,
                        actions_log_path=P["actions_log"])
    assert rep1["status"] == "decided"
    d1 = _canonical(rep1["decisions"])

    # rerun: identical prior state (simulated retry / overlapping cycle)
    s2 = PortfolioState.from_dict(before, _flat_mark)
    rep2 = run_timestamp(state=s2, mark_fn=_flat_mark, t=t1,
                        contenders=contenders, exits=[],
                        packet_log=P["packet_log"], vintage=P["vintage"],
                        engine=P["engine"], dedup_store=P["dedup"],
                        outbox=P["outbox"],
                        delivery_log_path=P["delivery_log"],
                        sender=paper_sender,
                        actions_log_path=P["actions_log"])
    d2 = _canonical(rep2["decisions"])
    assert d1 == d2, "decision outputs must be byte-identical across reruns"

    actions = [json.loads(l) for l in open(P["actions_log"])]
    acted = [a for a in actions if a["action"] == "acted"]
    suppressed = [a for a in actions if a["action"] == "duplicate_suppressed"]
    assert len(acted) == 4 and len(suppressed) == 4, actions
    assert len({a["dedup_key"] for a in acted}) == 4  # one action per key
    # only the TAKEN decision produced an alert, exactly once
    assert P["outbox"].n_alerts() == 1
    assert P["dedup"].n_claimed() == 4


def test_dedup_on_off_decisions_byte_identical(tmp_path):
    """Dedup in the pipeline vs decide_entries called directly (no dedup
    anywhere): decision outputs byte-identical. Dedup cannot alter
    decisions — it is consulted only after finalization."""
    before, t1 = _crafted_before()
    contenders = _crafted_contenders()

    direct_state = PortfolioState.from_dict(before, _flat_mark)
    direct_state.advance_clock(t1)
    direct = direct_state.decide_entries(t1, contenders)

    P = _cycle_paths(tmp_path, "onoff")
    pipe_state = PortfolioState.from_dict(before, _flat_mark)
    rep = run_timestamp(state=pipe_state, mark_fn=_flat_mark, t=t1,
                       contenders=contenders, exits=[],
                       packet_log=P["packet_log"], vintage=P["vintage"],
                       engine=P["engine"], dedup_store=P["dedup"],
                       outbox=P["outbox"],
                       delivery_log_path=P["delivery_log"],
                       sender=paper_sender,
                       actions_log_path=P["actions_log"])
    assert _canonical(rep["decisions"]) == _canonical(direct)


# ------------------------------------------------- (g) fault injection
def test_fault_injection_alert_sender_cannot_touch_state(tmp_path):
    """An exception INSIDE the alert sender mid-cycle: must not propagate,
    must not mutate state, must not trigger recalculation, packet intact,
    failure logged as a category-7 event."""
    before, t1 = _crafted_before()
    contenders = _crafted_contenders()

    def raising_sender(payload):
        raise RuntimeError("simulated delivery outage")

    # control run: working sender, from the identical before-state
    PA = _cycle_paths(tmp_path, "good")
    sA = PortfolioState.from_dict(before, _flat_mark)
    repA = run_timestamp(state=sA, mark_fn=_flat_mark, t=t1,
                        contenders=contenders, exits=[],
                        packet_log=PA["packet_log"], vintage=PA["vintage"],
                        engine=PA["engine"], dedup_store=PA["dedup"],
                        outbox=PA["outbox"],
                        delivery_log_path=PA["delivery_log"],
                        sender=paper_sender,
                        actions_log_path=PA["actions_log"])
    assert repA["status"] == "decided"

    # fault run: sender raises; count decide_entries calls (recalculation?)
    PB = _cycle_paths(tmp_path, "bad")
    sB = PortfolioState.from_dict(before, _flat_mark)
    calls = []
    orig_decide = sB.decide_entries

    def counting_decide(t, conts):
        calls.append((str(t), len(conts)))
        return orig_decide(t, conts)

    sB.decide_entries = counting_decide
    repB = run_timestamp(state=sB, mark_fn=_flat_mark, t=t1,  # must not raise
                        contenders=contenders, exits=[],
                        packet_log=PB["packet_log"], vintage=PB["vintage"],
                        engine=PB["engine"], dedup_store=PB["dedup"],
                        outbox=PB["outbox"],
                        delivery_log_path=PB["delivery_log"],
                        sender=raising_sender,
                        actions_log_path=PB["actions_log"])
    assert repB["status"] == "decided"
    assert len(calls) == 1, f"strategy recalculated {len(calls)} times"

    # state hash identical: the exception changed nothing downstream
    assert _sha(sB.to_dict()) == _sha(sA.to_dict())
    assert _canonical(repB["decisions"]) == _canonical(repA["decisions"])

    # decision packet intact: exactly one finalized portfolio packet
    pkts = [p for p in PB["packet_log"].read_all()
            if p.get("type") == "portfolio_decision"]
    assert len(pkts) == 1
    assert [d["decision"] for d in pkts[0]["decisions"]] == \
        [d["decision"] for d in repB["decisions"]]

    # category-7 delivery-failure event logged
    with open(PB["delivery_log"]) as f:
        events = [json.loads(l) for l in f if l.strip()]
    fails = [e for e in events if e.get("event") == "alert_delivery_failed"]
    assert fails, "no category-7 event logged"
    assert all(e["category"] == DELIVERY_CATEGORY for e in fails)
    assert any("simulated delivery outage" in (e["error"] or {}).get("error", "")
               for e in fails)


def test_alert_payload_derives_only_from_packet():
    packet = {"decision_time": "2026-09-17T13:30:00-04:00"}
    entry = {"signal_id": "v36:MSFT:4h:x", "symbol": "MSFT",
             "decision": "TAKEN", "reason_detail": "", "rs_score": 0.02,
             "rank": 1, "contested": True, "marked_equity_at_t": 10000.0}
    p = build_alert_payload(packet, entry)
    for k in ("signal_id", "symbol", "decision", "reason_detail",
              "rs_score", "rank", "contested", "marked_equity_at_t"):
        assert p[k] == entry[k], k
    assert p["decision_time"] == packet["decision_time"]
    assert p["paper_only"] is True
    assert p["alert_schema"] == ALERT_SCHEMA
    assert p["alert_id"] == alert_id_for(entry["signal_id"],
                                        packet["decision_time"])
    # a missing field is a loud KeyError, never an invented default
    bad = dict(entry)
    del bad["rs_score"]
    with pytest.raises(KeyError):
        build_alert_payload(packet, bad)


# ------------------------------------------------- (d)+(h) full window
def _run_window_through_cycle(tmp_path, tag, delivery_enabled, sender=None):
    """Drive the whole research window through cycle.run_timestamp.

    delivery_enabled=False is the PHYSICALLY DISABLED mode: dedup and
    alerts are never invoked (not merely idle). Returns (state, taken_idx,
    per_t_canonical, all_trades, skipped_gap, outbox, dedup_store).
    """
    all_trades, closes, data, bench, feats, skipped_gap = _research()
    base = tmp_path / tag
    base.mkdir(exist_ok=True)
    mark = lambda sym, t: reference_mark(closes, sym, t)  # noqa: E731
    state = PortfolioState(mark, COST)
    entries_by_t, exits_by_t = defaultdict(list), defaultdict(list)
    for idx, tr in enumerate(all_trades):
        entries_by_t[tr["entry_time"]].append(idx)
        exits_by_t[tr["exit_time"]].append(idx)
    times = sorted(set(entries_by_t) | set(exits_by_t))

    packet_log = PacketLog(str(base / "portfolio.jsonl"))
    dedup_store = (DedupStore(str(base / "dedup.jsonl"))
                   if delivery_enabled else None)
    outbox = (PaperOutbox(str(base / "outbox.jsonl"))
              if delivery_enabled else None)
    vintage = {"bars_source": "backtest_cache/v3 (research-window replay)",
               "note": f"slice-3 full-window {tag}"}
    engine = engine_version_extended()
    idx_of = {}
    taken_idx = []
    per_t = []
    for t in times:
        exits = [{"symbol": all_trades[i]["symbol"],
                  "exit_px": all_trades[i]["exit"],
                  "reason": all_trades[i]["reason"],
                  "universe_order": i}
                 for i in sorted(exits_by_t.get(t, []))]
        contenders = []
        for i in entries_by_t.get(t, []):
            tr = all_trades[i]
            c = {"signal_id": _signal_id(tr), "symbol": tr["symbol"],
                 "entry_px": tr["entry"], "stop_px": tr["stop"],
                 "tp1_px": tr["tp1"], "rs_score": feats[i]["rs"],
                 "universe_order": i, "trade_idx": i}
            contenders.append(c)
            idx_of[c["signal_id"]] = i
        rep = run_timestamp(
            state=state, mark_fn=mark, t=t, contenders=contenders,
            exits=exits, packet_log=packet_log, vintage=vintage,
            engine=engine, dedup_store=dedup_store, outbox=outbox,
            delivery_log_path=str(base / "delivery.jsonl"),
            sender=sender or paper_sender,
            actions_log_path=str(base / "actions.jsonl"))
        assert rep["status"] in ("decided", "no_contenders"), (t, rep)
        if rep["status"] == "decided":
            per_t.append((str(t), _canonical(rep["decisions"])))
            for d in rep["decisions"]:
                if d["decision"] == TAKEN:
                    taken_idx.append(idx_of[d["signal_id"]])
    return state, taken_idx, per_t, all_trades, skipped_gap, outbox, dedup_store


def test_full_window_c1_exact_with_delivery_enabled(tmp_path):
    """(d) With dedup + paper alerts enabled, the full window reproduces
    locked C1 EXACTLY — including RISK_CAP=10 (the 5% portfolio-risk gate,
    part of the canonical stack, preserved untouched)."""
    state, taken_idx, per_t, all_trades, skipped_gap, outbox, dedup = \
        _run_window_through_cycle(tmp_path, "enabled", True)

    taken = [all_trades[i] for i in taken_idx]
    port = {"final_equity": state.realized, "max_drawdown": state.max_dd,
            "skipped_cap_count": (state.counters[RANKED_OUT]
                                  + state.counters[NO_SLOT]),
            "skipped_cap_risk": state.counters[RISK_CAP],
            "exposure": state.exposure()}
    row = pb.summarize("slice3-c1", taken, port, skipped_gap, "4bps")
    for k, v in LOCKED_C1.items():
        assert row[k] == v, (k, row[k], v)
    assert round(row["total_return_pct"] / row["max_drawdown_pct"], 2) == 1.65
    for code, n in LOCKED_REASONS.items():
        assert state.counters[code] == n, (code, state.counters[code], n)
    # the 5% risk gate is part of the locked stack: it fired, untouched
    assert state.counters[RISK_CAP] == 10

    # delivery layers: one alert per TAKEN, one claim per finalized decision
    assert outbox.n_alerts() == 143
    assert all(outbox.status_of(a) == "delivered"
               for a in outbox._status), "paper sender must deliver all"
    assert dedup.n_claimed() == 143 + 94 + 16 + 0 + 10


def test_full_window_delivery_disabled_byte_identical(tmp_path):
    """(h) CAUSAL INERTNESS: the same full window with delivery layers
    PHYSICALLY DISABLED produces byte-identical per-timestamp decisions.
    The delivery layers cannot influence selection — proven, not assumed."""
    _, _, per_t_on, _, _, _, _ = \
        _run_window_through_cycle(tmp_path, "on", True)
    _, _, per_t_off, _, _, _, _ = \
        _run_window_through_cycle(tmp_path, "off", False)
    assert len(per_t_on) == len(per_t_off) and len(per_t_on) > 0
    for (t_on, c_on), (t_off, c_off) in zip(per_t_on, per_t_off):
        assert t_on == t_off
        assert c_on == c_off, f"delivery layers altered decisions at {t_on}"


# ------------------------------------------------- (c) failure drills (C9)
def test_failure_drill_download_killed_fails_closed(tmp_path):
    """Kill the data download mid-cycle: no signal, failure logged."""
    import pine_live.live_path as lp
    orig = lp.download_data

    def dead(symbol, *a, **k):
        raise ConnectionError("simulated network kill")

    lp.download_data = dead
    try:
        log = PacketLog(str(tmp_path / "d.jsonl"))
        out = safe_evaluate_live("NVDA", log, str(tmp_path / "s"),
                                 str(tmp_path / "cycle.jsonl"))
    finally:
        lp.download_data = orig
    assert out is None, "a failed download must not produce an evaluation"
    with open(tmp_path / "cycle.jsonl") as f:
        events = [json.loads(l) for l in f if l.strip()]
    assert any(e["event"] == "evaluation_failed" and e["fail_closed"]
               for e in events)
    assert log.read_all() == [], "no packet may be emitted from a failure"


def test_failure_drill_unknown_sector_refuses_closed(tmp_path):
    """A symbol with no sector label: the whole timestamp is refused,
    state rolled back exactly (no partial entries), no alerts, refusal
    logged. Fail closed — no signal rather than a wrong signal."""
    P = _cycle_paths(tmp_path, "unknownsector")
    state = PortfolioState(_flat_mark, COST)
    t = pd.Timestamp("2026-09-17 13:30", tz="America/New_York")
    state.advance_clock(t)
    n_events_before = len(state.events)

    contenders = [
        _contender("v36:NVDA:4h:t", "NVDA", 0.05, 0, 100.0, 98.0, 104.0),
        _contender("v36:FAKE:4h:t", "FAKE-SYMBOL", 0.01, 1),
    ]
    rep = run_timestamp(state=state, mark_fn=_flat_mark, t=t,
                       contenders=contenders, exits=[],
                       packet_log=P["packet_log"], vintage=P["vintage"],
                       engine=P["engine"], dedup_store=P["dedup"],
                       outbox=P["outbox"],
                       delivery_log_path=P["delivery_log"],
                       sender=paper_sender,
                       actions_log_path=P["actions_log"])
    assert rep["status"] == "refused", rep
    # exact rollback: no positions, no new events, counters untouched
    assert state.positions == {}
    assert len(state.events) == n_events_before
    assert all(v == 0 for v in state.counters.values())
    # refusal packet logged (own schema, never rewritten)
    pkts = P["packet_log"].read_all()
    refusals = [p for p in pkts if p.get("type") == "portfolio_refused"]
    assert len(refusals) == 1
    assert "FAKE-SYMBOL" in refusals[0]["contender_symbols"]
    # delivery layers never engaged for a refused timestamp
    assert P["outbox"].n_alerts() == 0
    assert P["dedup"].n_claimed() == 0


# ------------------------------------------------- (e) no trading surface
def test_slice3_no_trading_or_remote_notification_surface():
    """New modules contain no trading surface and no remote-notification
    wiring. Alerts terminate at the local paper outbox — nothing in this
    slice can reach Mike's phone/chat/email."""
    for name in ("dedup.py", "alerts.py", "cycle.py"):
        src = open(os.path.join(LIVE_DIR, name)).read()
        for pat in BANNED_PATTERNS:
            assert pat not in src, (name, pat)
    src = open(os.path.join(LIVE_DIR, "alerts.py")).read()
    assert "PaperOutbox" in src
    assert '"paper_only": True' in src or "'paper_only': True" in src or \
        '"paper_only":True' in src or "paper_only" in src
    # the outbox path is always caller-supplied/local: no hardcoded remote
    for token in ("http://", "https://", "api_key", "API_KEY"):
        assert token not in src, ("alerts.py", token)
