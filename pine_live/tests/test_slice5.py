"""Slice 5 acceptance tests: live exit evaluation.

Run:  cd ~/workspace/quality-flow-scanner-v5 && python3 -m pytest pine_live/tests/test_slice5.py -x -q

Mike's contract: exit decisions call canonical V3.6 reference logic (the
reference manage block has no standalone function to import — it is a
character-faithful extraction in pine_live/exits.py, pinned by a 263-trade
differential proof); every exit decision gets an fsync'd replayable packet
(pre-exit position + hash-pinned bar snapshot); packet-only replay
reproduces the exit decision and resulting state exactly; tampered
snapshots are rejected; ordering stays exits-before-entries; exit symbol
order cannot affect results; the full research window stays EXACTLY on
locked C1; malformed events / snapshot-hash failures / evaluator
exceptions fail closed with state hash unchanged and no partially applied
exit; delivery stays causally inert.

Acceptance:
  (a) differential: the pure exit walk reproduces all 263 research-window
      reference trades exactly (exit_time, exit_px, reason, tp1_hit,
      hold_bars);
  (b) exits.py is import-isolated (no pine_live.* imports, stdlib+pandas+
      pine_backtest only), carries no banned patterns, and contains no
      time-based exit (there is none in the V3.6 reference — the 30-bar max
      hold belongs to the V5.4 Mode-B exit, a different system; adding one
      here would be a strategy change and would break (a));
  (c) every applied live exit gets an fsync'd packet; packet-only replay
      reproduces the exit decision and resulting state exactly; a tampered
      snapshot is rejected;
  (d) the full research window driven through run_cycle(live_exits=True)
      reproduces locked C1 EXACTLY (143 / +0.337R / 52.25% / 31.63% /
      1.65, TAKEN 143 / RANKED_OUT 94 / SECTOR_CAP 16 / NO_SLOT 0 /
      RISK_CAP 10) — the live exit path adds zero drift;
  (e) crafted same-timestamp exits+entries scenario: the exit frees the
      slot the entries contend for (INTC TAKEN, XLF RANKED_OUT), while the
      no-exit control leaves both RANKED_OUT; live-evaluated exits feed
      byte-identical entry decisions as externally supplied exit events;
  (f) exit symbol/input order cannot affect results;
  (g) fail-closed: per-position provider/evaluator failures are skipped
      with the position left open and the failure logged; malformed exit
      events are rejected before the engine; a packet-write failure fails
      the whole timestamp closed (state hash unchanged, logs rolled back,
      no partially applied exit);
  (h) delivery stays causally inert on the exit path (raising sender;
      enabled vs physically disabled byte-identical);
  (i) static: no trading surface in the new code.

Explicitly NOT built (out of scope): reconciliation (slice 6), real
notifications, trading/order integration, strategy changes.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

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
from pine_live.sector import sector_of
from pine_live.packets import (
    PacketLog, _canonical, engine_version_extended,
    append_exit_packet, build_exit_packet, read_exit_packets,
    write_exit_bars_snapshot, load_exit_snapshot, EXIT_PACKET_SCHEMA,
)
from pine_live.exits import evaluate_position_exit, EXIT_REASONS
from pine_live.dedup import DedupStore
from pine_live.alerts import PaperOutbox, paper_sender
from pine_live.multicycle import (
    run_cycle, _check_exit_events_wellformed,
)
from pine_live.replay import replay_portfolio_decision, replay_exit_decision

from pine_live.tests.test_slice1 import BANNED_PATTERNS
from pine_live.tests.test_slice2 import (
    _research, COST, LOCKED_C1, LOCKED_REASONS,
)
from pine_live.tests.test_slice4 import (
    _provider_factory, _cycle_paths, _mark_flat,
)

LIVE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Crafted scenario: NFLX exits (reference stop, TP1 was hit) at T while
# INTC and XLF contend for entries. Five seeded positions, so the exit
# frees the only slot.
T_EXIT = pd.Timestamp("2026-04-17 13:30:00-0400", tz="America/New_York")
FILLER_SYMBOLS = ["MSFT", "GOOGL", "APP", "HOOD"]
FILLER_RISK_DOLLARS = 20.0


@pytest.fixture(scope="module")
def research():
    all_trades, closes, data, bench, feats, skipped_gap = _research()
    # Memoize indicator computation on both bindings multicycle/live_path
    # use (pure function of the frame; behavior-identical, keeps the
    # full-window suite fast).
    orig_lp, orig_pb = lp.add_pine_indicators, pb.add_pine_indicators
    cache = {}

    def cached(bars):
        key = id(bars)
        if key not in cache:
            cache[key] = orig_pb(bars)
        return cache[key]

    lp.add_pine_indicators = cached
    pb.add_pine_indicators = cached
    yield all_trades, closes, data, bench, feats, skipped_gap
    lp.add_pine_indicators = orig_lp
    pb.add_pine_indicators = orig_pb


def _sha(obj) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def _nflx_trade(all_trades):
    return next(tr for tr in all_trades
                if tr["symbol"] == "NFLX"
                and pd.Timestamp(tr["exit_time"]) == T_EXIT)


def _mkpos(symbol, entry_px, stop_px, tp1_px, entry_time, signal_id,
           risk_dollars=FILLER_RISK_DOLLARS):
    rf = (float(entry_px) - float(stop_px)) / float(entry_px)
    return {"symbol": symbol, "signal_id": signal_id,
            "sector": sector_of(symbol),
            "entry_px": float(entry_px), "stop_px": float(stop_px),
            "tp1_px": float(tp1_px),
            "entry_time": pd.Timestamp(entry_time).isoformat(),
            "risk_dollars": float(risk_dollars), "risk_frac": float(rf),
            "size": float(risk_dollars / rf)}


def _seed_exit_scenario(research):
    """Five open positions at T_EXIT: the real NFLX trade (exits at T_EXIT
    per the reference) plus four fillers entered on the previous bar whose
    single-bar exit walk provably does not trigger (asserted below)."""
    all_trades, closes, data, bench, feats, skipped_gap = research
    mark = lambda sym, t: reference_mark(closes, sym, t)  # noqa: E731
    state = PortfolioState(mark, COST)
    state.advance_clock(T_EXIT)
    nflx = _nflx_trade(all_trades)
    state.positions["NFLX"] = _mkpos(
        "NFLX", nflx["entry"], nflx["stop"], nflx["tp1"],
        nflx["entry_time"], "v36:NFLX:4h:seed")
    prev_bar = data["NFLX"].index[
        int(data["NFLX"].index.get_loc(
            T_EXIT.tz_convert(data["NFLX"].index.tz))) - 1]
    for sym in FILLER_SYMBOLS:
        d = data[sym]
        bar = d.loc[prev_bar.tz_convert(d.index.tz)]
        e, a = float(bar["Close"]), float(bar["atr"])
        # Setup invariant, verified not assumed: the filler's one-bar walk
        # (entry bar only) must not trigger.
        assert not (float(bar["Close"]) < float(bar["e55"])
                    or (float(bar["e21"]) < float(bar["e55"])
                        and float(bar["Close"]) < float(bar["e200"]))), \
            (sym, "filler would trigger on its entry bar")
        state.positions[sym] = _mkpos(
            sym, e, e - 0.5 * a, e + 2.0 * a, prev_bar.isoformat(),
            f"v36:{sym}:4h:seed")
    assert state.n_open() == 5
    return state, mark, prev_bar


def _exit_cycle_paths(tmp_path, tag):
    P = _cycle_paths(tmp_path, tag)
    P["exit_packet_log"] = str(Path(P["snapshot_dir"]).parent
                               / "exit_packets.jsonl")
    # Causally-inert reconciliation artifact (slice 6): the full ordered
    # settlement timeline the live run visited, including cycles that
    # produced no packets but still settled/marked equity. Written once,
    # after the run; never read by the trading path.
    P["recon_manifest"] = str(Path(P["snapshot_dir"]).parent
                              / "reconciliation_manifest.json")
    return P


def _run_exit_cycle(research, tmp_path, tag, state, mark, symbols,
                    delivery_enabled=True, sender=paper_sender,
                    live_exits=True, exits=None, frame_provider=None):
    all_trades, closes, data, bench, feats, skipped_gap = research
    P = _exit_cycle_paths(tmp_path, tag)
    provider = frame_provider or _provider_factory(data)
    rep = run_cycle(
        symbols=symbols, bar_time=T_EXIT, state=state, mark_fn=mark,
        packet_log=P["packet_log"], snapshot_dir=P["snapshot_dir"],
        vintage=P["vintage"], engine=P["engine"],
        dedup_store=P["dedup"] if delivery_enabled else None,
        outbox=P["outbox"] if delivery_enabled else None,
        delivery_log_path=P["delivery_log"],
        sender=sender, actions_log_path=P["actions_log"],
        cycle_log_path=P["cycle_log"],
        frame_provider=provider, spy_daily=bench.get("SPY"),
        live_exits=live_exits, exits=exits,
        exit_packet_log=P["exit_packet_log"] if live_exits else None,
        signal_bar="previous")
    return rep, P


# ------------------------------------------------- (a) differential proof
def test_exit_walk_matches_reference_on_all_trades(research):
    """The pure exit walk reproduces every one of the 263 research-window
    reference trades exactly: exit_time, exit_px, reason, tp1_hit,
    hold_bars. The extraction is character-faithful to the reference
    manage block — this is the pin, not an import."""
    all_trades, closes, data, bench, feats, skipped_gap = research
    assert len(all_trades) == 263
    for tr in all_trades:
        df = data[tr["symbol"]]
        entry_idx = int(df.index.get_loc(pd.Timestamp(tr["entry_time"])))
        res = evaluate_position_exit(
            symbol=tr["symbol"], entry_px=tr["entry"], stop_px=tr["stop"],
            tp1_px=tr["tp1"], entry_idx=entry_idx, ind=df,
            eval_end_idx=len(df) - 1)
        assert res["triggered"], (tr["symbol"], tr["entry_time"])
        assert pd.Timestamp(res["fill_bar_time"]) == pd.Timestamp(tr["exit_time"]), \
            (tr["symbol"], res["fill_bar_time"], tr["exit_time"])
        assert res["reason"] == tr["reason"], (tr["symbol"], res["reason"])
        assert res["tp1_hit"] == tr["tp1_hit"], (tr["symbol"], res["tp1_hit"])
        assert abs(res["exit_px"] - tr["exit"]) < 1e-12, \
            (tr["symbol"], res["exit_px"], tr["exit"])
        assert res["hold_bars"] == tr["hold_bars"], (tr["symbol"], res["hold_bars"])


def test_exit_walk_is_pure_function_of_bars(research):
    """Same inputs -> identical outputs; no hidden state. A missed cycle
    cannot corrupt the walk: the next cycle simply walks further."""
    all_trades, closes, data, bench, feats, skipped_gap = research
    tr = _nflx_trade(all_trades)
    df = data["NFLX"]
    entry_idx = int(df.index.get_loc(pd.Timestamp(tr["entry_time"])))
    kw = dict(symbol="NFLX", entry_px=tr["entry"], stop_px=tr["stop"],
              tp1_px=tr["tp1"], entry_idx=entry_idx, ind=df,
              eval_end_idx=len(df) - 1)
    r1 = evaluate_position_exit(**kw)
    r2 = evaluate_position_exit(**kw)
    assert r1 == r2
    # walking further (later eval_end) does not move the first trigger
    r3 = evaluate_position_exit(**{**kw, "eval_end_idx": entry_idx + 5})
    assert r3["triggered"] is False  # trigger is later; nothing invented


# ------------------------------------------------- (b) import isolation
def test_exits_module_import_isolation():
    """exits.py: stdlib + pandas + pine_backtest only. It cannot import
    pine_live.dedup / alerts / cycle / portfolio — exit evaluation cannot
    reach delivery or state, structurally."""
    path = os.path.join(LIVE_DIR, "exits.py")
    tree = ast.parse(open(path).read())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    assert imports <= {"__future__", "os", "sys", "pandas", "pd",
                       "pine_backtest"}, imports
    src = open(path).read()
    assert "from pine_live" not in src and "import pine_live" not in src, \
        "exits.py must not import pine_live modules"


def test_exits_module_has_no_banned_patterns():
    with open(os.path.join(LIVE_DIR, "exits.py")) as f:
        src = f.read()
    for pat in BANNED_PATTERNS:
        assert pat not in src, ("exits.py", pat)


def test_no_time_based_exit_in_v36():
    """Pin the reference-behavior finding: the V3.6 exit set is exactly
    {stop, ema55-break, ema55-bear}. There is no 30-bar (or any) max-hold
    exit in the reference — adding one would be a strategy change and
    would break the 263-trade differential proof."""
    assert set(EXIT_REASONS) == {"stop", "ema55-break", "ema55-bear"}
    # No time-based exit identifiers in the CODE (the module docstring
    # discusses the 30-bar V5.4 behavior in prose to pin the distinction,
    # so strip docstrings/comments before checking).
    tree = ast.parse(open(os.path.join(LIVE_DIR, "exits.py")).read())
    code = ast.dump(tree)
    for ident in ("max_hold", "maxhold", "time_exit"):
        assert ident not in code, ("exits.py", ident)
    # TRAIL_ATR comes from the reference by import, never a literal 2.5 in
    # the walk logic.
    assert "pb.TRAIL_ATR" in open(os.path.join(LIVE_DIR, "exits.py")).read()


# ------------------------------------------------- (c) packet + replay
def _portfolio_packets(packet_log):
    return [p for p in packet_log.read_all()
            if p.get("type") == "portfolio_decision"]


def test_exit_packet_replay_exact_and_tamper_rejected(research, tmp_path):
    """One live exit through the full cycle path: the packet replays
    exactly from its snapshot alone (decision + resulting state), and a
    tampered snapshot is rejected, not papered over."""
    state, mark, _prev = _seed_exit_scenario(research)
    before = state.to_dict()
    rep, P = _run_exit_cycle(research, tmp_path, "replay", state, mark,
                             ["XLF", "INTC"])
    assert rep["timestamp"]["status"] == "decided"
    assert rep["exit_packets"] == 1

    packets = read_exit_packets(P["exit_packet_log"])
    assert len(packets) == 1
    p = packets[0]
    assert p["packet_schema"] == EXIT_PACKET_SCHEMA
    assert p["symbol"] == "NFLX"
    assert p["decision_time"] == T_EXIT.isoformat()
    # pre-exit position is the exact seeded position
    assert p["position"]["entry_px"] == before["positions"]["NFLX"]["entry_px"]
    # exact pre-exit book: 5 open, NFLX still in positions
    assert len(p["pre_exit_state"]["positions"]) == 5
    assert "NFLX" in p["pre_exit_state"]["positions"]
    # exact post-exit book: 4 open, NFLX gone, realized moved by the exit
    assert len(p["post_exit_state"]["positions"]) == 4
    assert "NFLX" not in p["post_exit_state"]["positions"]
    assert (p["post_exit_state"]["realized"]
            == p["pre_exit_state"]["realized"]
            + p["position"]["risk_dollars"] * p["exit"]["net_r"])
    # ground truth from the applied close event
    close_ev = next(e for e in state.events if e.get("kind") == "close")
    assert p["exit"]["net_r"] == close_ev["net_r"]
    assert p["realized_after"] == close_ev["realized_after"]
    # engine pins exits.py
    assert "exits.py" in p["engine_version"]["reference_sha256"]

    # packet-only replay reproduces the exit decision and resulting state
    r = replay_exit_decision(p)
    assert r["replayed"] is True and r["exact"] is True, r["diffs"]

    # tampered snapshot -> rejected
    snap_path = p["bars_snapshot_ref"]["path"]
    raw = open(snap_path).read()
    tampered = raw.replace('"c":', '"c": 999999.0, "c_orig":', 1)
    assert tampered != raw
    bad_dir = tmp_path / "replay" / "tampered_snaps"
    bad_dir.mkdir(parents=True, exist_ok=True)
    bad_path = str(bad_dir / "tampered.json")
    open(bad_path, "w").write(tampered)
    p2 = dict(p)
    p2["bars_snapshot_ref"] = dict(p["bars_snapshot_ref"], path=bad_path)
    r2 = replay_exit_decision(p2)
    assert r2["replayed"] is False and "hash" in r2["reason"].lower(), r2

    # missing snapshot -> refused, never guessed
    p3 = dict(p)
    p3["bars_snapshot_ref"] = dict(p["bars_snapshot_ref"],
                                   path="/nonexistent/x.json")
    r3 = replay_exit_decision(p3)
    assert r3["replayed"] is False

    # malformed packet -> refused by the appender, never logged
    with pytest.raises(RuntimeError):
        append_exit_packet(P["exit_packet_log"], {"symbol": "NFLX"})
    assert len(read_exit_packets(P["exit_packet_log"])) == 1


def test_entry_packet_replays_from_post_exit_state(research, tmp_path):
    """The exit feeds entries ONLY through the book: INTC's portfolio
    packet re-decides identically from the post-exit state (pre-cycle
    state + the cycle's own close event). This is the replay-side proof
    that exits never alter qualification/ranking/reason codes
    retroactively — the entry decision is a pure function of the book
    the packet pins."""
    state, mark, _prev = _seed_exit_scenario(research)
    before = state.to_dict()
    rep, P = _run_exit_cycle(research, tmp_path, "entryreplay", state, mark,
                             ["XLF", "INTC"])
    assert rep["timestamp"]["status"] == "decided"
    close_ev = next(e for e in state.events if e.get("kind") == "close")
    assert close_ev["symbol"] == "NFLX"

    # Reconstruct the exact post-exit state the engine decided from.
    st = PortfolioState.from_dict(before, mark)
    st.process_exits(T_EXIT, [{"symbol": close_ev["symbol"],
                               "exit_px": close_ev["exit_px"],
                               "reason": close_ev["exit_reason"],
                               "universe_order": 0}])
    assert st.n_open() == 4 and "NFLX" not in st.positions

    pkts = [p for p in _portfolio_packets(P["packet_log"])
            if p["decision_time"] == T_EXIT.isoformat()]
    assert len(pkts) == 1
    r = replay_portfolio_decision(pkts[0], st.to_dict(), mark)
    assert r["replayed"] is True and r["exact"] is True, r["diffs"]

    # And the pre-exit state genuinely does NOT reproduce the decision
    # (the exit mattered): replaying from the 5-open book fails the
    # pre-check rather than silently agreeing.
    r2 = replay_portfolio_decision(pkts[0], before, mark)
    assert r2["replayed"] is False
    assert r2["reason"] == "state-before mismatch"


# ------------------------------------------------- (d) full-window parity
def _run_window_live_exits(research, tmp_path, tag, delivery_enabled,
                           ref_taken_set):
    """Mirror of test_slice4._run_window_via_cycle with live_exits=True:
    no external exit events — every exit comes from the canonical walk."""
    all_trades, closes, data, bench, feats, skipped_gap = research
    spy = bench.get("SPY")
    assert spy is not None
    P = _exit_cycle_paths(tmp_path, tag)
    provider = _provider_factory(data)
    mark = lambda sym, t: reference_mark(closes, sym, t)  # noqa: E731
    state = PortfolioState(mark, COST)

    entries_by_t, exits_by_t = defaultdict(list), defaultdict(list)
    for idx, tr in enumerate(all_trades):
        entries_by_t[tr["entry_time"]].append(idx)
        exits_by_t[tr["exit_time"]].append(idx)
    times = sorted(set(entries_by_t) | set(exits_by_t))

    by_signal_bar = defaultdict(list)
    for t in times:
        for i in entries_by_t.get(t, []):
            by_signal_bar[t].append((all_trades[i]["symbol"], i))

    taken_idx = []
    idx_of = {}
    n_live_exits = 0
    manifest_rows = []
    for t in times:
        syms = [s for s, _ in by_signal_bar.get(t, [])]
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
            live_exits=True, exit_packet_log=P["exit_packet_log"],
            signal_bar="previous")
        ts = rep["timestamp"]
        assert ts["status"] in ("decided", "no_contenders"), (t, ts)
        # the live walk must fire exactly the reference exits at every
        # timestamp: no invented exits, no missed ones.
        live_syms = {e["symbol"] for e in rep["live_exits"]["evaluated"]
                     if e["triggered"]}
        ref_syms = {all_trades[i]["symbol"]
                    for i in exits_by_t.get(t, []) if i in ref_taken_set}
        assert live_syms == ref_syms, (t, live_syms, ref_syms)
        n_live_exits += rep["exit_packets"]
        sig_ids = {e["signal_id"] for e in rep["signals"]}
        for s, i in by_signal_bar.get(t, []):
            tr = all_trades[i]
            want = f"v36:{s}:4h:{tr['signal_time']}"
            assert want in sig_ids, (s, t, "research candidate not signaled")
            idx_of[want] = i
        if ts["status"] == "decided":
            for d in ts["decisions"]:
                tr = all_trades[idx_of[d["signal_id"]]]
                assert d["rs_score"] == feats[idx_of[d["signal_id"]]]["rs"]
                if d["decision"] == TAKEN:
                    taken_idx.append(idx_of[d["signal_id"]])
        manifest_rows.append({
            "t": pd.Timestamp(t).isoformat(),
            "status": ts["status"],
            "n_exit_packets": rep["exit_packets"],
            "n_signals": len(rep["signals"]),
        })
    # Slice-6 reconciliation manifest: the exact settlement timeline the
    # engine visited. Causally inert (write-only; the trading path never
    # reads it). fsync'd like every other packet artifact.
    manifest = {
        "manifest_schema": "recon-manifest-v1",
        "run_tag": tag,
        "n_timestamps": len(times),
        "timeline": [r["t"] for r in manifest_rows],
        "timestamps": manifest_rows,
    }
    with open(P["recon_manifest"], "w", encoding="utf-8") as f:
        f.write(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return state, taken_idx, all_trades, skipped_gap, P, n_live_exits


def test_live_exits_full_window_c1_exact(research, tmp_path):
    """(d) The full research window through run_cycle(live_exits=True)
    reproduces locked C1 EXACTLY — the live exit path adds zero drift
    versus the reference exit feed. 143 exits, all packetized, all
    replayable."""
    from pine_live.tests.test_slice2 import _run_full_window
    _ref_state, ref_taken_idx, _pkts, _tr, _cl, _sg = _run_full_window()
    ref_taken_set = set(ref_taken_idx)
    assert len(ref_taken_set) == 143

    state, taken_idx, all_trades, skipped_gap, P, n_live_exits = \
        _run_window_live_exits(research, tmp_path, "parity-live", True,
                               ref_taken_set)

    # the live path took exactly the reference trades
    assert set(taken_idx) == ref_taken_set, \
        (set(taken_idx) ^ ref_taken_set)
    assert n_live_exits == 143
    assert state.n_open() == 0  # every position closed in-window

    taken = [all_trades[i] for i in taken_idx]
    port = {"final_equity": state.realized, "max_drawdown": state.max_dd,
            "skipped_cap_count": (state.counters[RANKED_OUT]
                                  + state.counters[NO_SLOT]),
            "skipped_cap_risk": state.counters[RISK_CAP],
            "exposure": state.exposure()}
    row = pb.summarize("slice5-c1", taken, port, skipped_gap, "4bps")
    for k, v in LOCKED_C1.items():
        assert row[k] == v, (k, row[k], v)
    assert round(row["total_return_pct"] / row["max_drawdown_pct"], 2) == 1.65
    for code, n in LOCKED_REASONS.items():
        assert state.counters[code] == n, (code, state.counters[code], n)
    assert state.counters[RISK_CAP] == 10

    # every exit packet matches its reference trade and replays exactly
    ref_by_key = {(tr["symbol"], pd.Timestamp(tr["entry_time"]).isoformat()): tr
                  for tr in all_trades}
    exit_packets = read_exit_packets(P["exit_packet_log"])
    assert len(exit_packets) == 143
    for p in exit_packets:
        key = (p["symbol"], p["position"]["entry_time"])
        tr = ref_by_key[key]
        assert abs(p["exit"]["exit_px"] - tr["exit"]) < 1e-12, key
        assert p["trigger"]["reason"] == tr["reason"], key
        assert p["trigger"]["tp1_hit"] == tr["tp1_hit"], key
        assert p["exit"]["hold_bars"] == tr["hold_bars"], key
        r = replay_exit_decision(p)
        assert r["replayed"] is True and r["exact"] is True, (key, r["diffs"])

    # contender prices still match the reference for every candidate
    px_by_key = {}
    for pkt in _portfolio_packets(P["packet_log"]):
        for c in pkt["contenders"]:
            px_by_key[(pkt["decision_time"], c["signal_id"])] = c
    n_checked = 0
    for tr in all_trades:
        key = (pd.Timestamp(tr["entry_time"]).isoformat(),
               f"v36:{tr['symbol']}:4h:{tr['signal_time']}")
        c = px_by_key.get(key)
        assert c is not None, ("candidate missing from packet log", key)
        assert c["entry_px"] == tr["entry"], key
        assert c["stop_px"] == tr["stop"], key
        assert c["tp1_px"] == tr["tp1"], key
        n_checked += 1
    assert n_checked == 263, n_checked

    # delivery: one paper alert per TAKEN, one claim per finalized decision
    assert P["outbox"].n_alerts() == 143
    assert P["dedup"].n_claimed() == 143 + 94 + 16 + 0 + 10


# ------------------------------------------------- (e) exits free capacity
def test_exit_before_entries_frees_capacity(research, tmp_path):
    """Crafted same-timestamp exits+entries: with 5 seeded positions the
    book is full, so without the NFLX exit both candidates are RANKED_OUT;
    the live exit frees the one slot INTC (top-ranked) takes while XLF
    stays RANKED_OUT. Exit reason codes are untouched."""
    state, mark, _prev = _seed_exit_scenario(research)
    nflx = _nflx_trade(research[0])
    before = state.to_dict()
    before_hash = _sha(before)

    rep, P = _run_exit_cycle(research, tmp_path, "freed", state, mark,
                             ["XLF", "INTC"])
    ts = rep["timestamp"]
    assert ts["status"] == "decided", ts

    # the exit was evaluated from the canonical walk and applied first
    ev = rep["live_exits"]["evaluated"]
    nflx_ev = next(e for e in ev if e["symbol"] == "NFLX")
    assert nflx_ev["triggered"] is True
    assert all(not e["triggered"] for e in ev if e["symbol"] != "NFLX")
    assert "NFLX" not in state.positions
    close_ev = next(e for e in state.events if e.get("kind") == "close")
    assert close_ev["symbol"] == "NFLX"
    assert close_ev["exit_reason"] == nflx["reason"] == "stop"
    assert close_ev["exit_px"] == nflx["exit"]
    assert close_ev["t"] == T_EXIT.isoformat()

    # the freed slot flows into entries; reason codes are unaffected
    got = {d["symbol"]: d["decision"] for d in ts["decisions"]}
    assert got == {"INTC": TAKEN, "XLF": RANKED_OUT}, got
    assert state.n_open() == 5  # 4 fillers + INTC

    # control: no exits at all -> book stays full -> both RANKED_OUT
    state0, mark0, _p0 = _seed_exit_scenario(research)
    rep0, _P0 = _run_exit_cycle(research, tmp_path, "freed-ctrl", state0,
                                mark0, ["XLF", "INTC"], live_exits=False,
                                exits=[])
    got0 = {d["symbol"]: d["decision"]
            for d in rep0["timestamp"]["decisions"]}
    assert got0 == {"INTC": RANKED_OUT, "XLF": RANKED_OUT}, got0
    assert state0.n_open() == 5 and "NFLX" in state0.positions

    # the exit is what changed the entries, nothing else: the control
    # state's hash differs from the live run's only by the exit+entry
    assert _sha(state0.to_dict()) != _sha(state.to_dict())
    assert before_hash == _sha(before)  # the `before` snapshot is intact


def test_live_exits_match_external_exits_entry_decisions(research, tmp_path):
    """Entry decisions are byte-identical whether exits come from live
    evaluation or from externally supplied exit events: the entry path
    cannot tell the difference (criterion: exits never alter entry
    decisions retroactively)."""
    state, mark, _p = _seed_exit_scenario(research)
    rep_live, _P = _run_exit_cycle(research, tmp_path, "equiv-live", state,
                                   mark, ["XLF", "INTC"])
    close_ev = next(e for e in state.events if e.get("kind") == "close")
    ext_exits = [{"symbol": close_ev["symbol"],
                  "exit_px": close_ev["exit_px"],
                  "reason": close_ev["exit_reason"],
                  "universe_order": 0}]

    state2, mark2, _p2 = _seed_exit_scenario(research)
    rep_ext, _P2 = _run_exit_cycle(research, tmp_path, "equiv-ext", state2,
                                   mark2, ["XLF", "INTC"], live_exits=False,
                                   exits=ext_exits)
    d_live = rep_live["timestamp"]["decisions"]
    d_ext = rep_ext["timestamp"]["decisions"]
    assert d_live == d_ext
    assert _sha(state.to_dict()) == _sha(state2.to_dict())


# ------------------------------------------------- (f) order independence
def test_exit_symbol_order_independence(research, tmp_path):
    """Exit evaluation order (sorted symbols) and contender input order
    cannot affect results: shuffled inputs give identical decisions,
    states, and exit packets."""
    recs = []
    for tag, symbols in (("order-a", ["XLF", "INTC"]),
                         ("order-b", ["INTC", "XLF"])):
        state, mark, _p = _seed_exit_scenario(research)
        rep, P = _run_exit_cycle(research, tmp_path, f"order-{tag}", state,
                                 mark, symbols)
        recs.append((rep, P, state))
    (rep_a, P_a, st_a), (rep_b, P_b, st_b) = recs
    assert (rep_a["timestamp"]["decisions"]
            == rep_b["timestamp"]["decisions"])
    assert _sha(st_a.to_dict()) == _sha(st_b.to_dict())
    pkts_a = read_exit_packets(P_a["exit_packet_log"])
    pkts_b = read_exit_packets(P_b["exit_packet_log"])
    assert len(pkts_a) == len(pkts_b) == 1
    # packets compared field-by-field except computed_at wall-clock and
    # filesystem paths (same content: the snapshot sha256 must match)
    def _norm(pkt):
        pkt = {k: v for k, v in pkt.items()
               if k not in ("computed_at", "data_vintage")}
        ref = dict(pkt["bars_snapshot_ref"])
        ref.pop("path", None)
        pkt["bars_snapshot_ref"] = ref
        return pkt
    for pa, pb_ in zip(pkts_a, pkts_b):
        assert _norm(pa) == _norm(pb_)


# ------------------------------------------------- (g) fail-closed
def test_exit_evaluation_failure_fails_closed(research, tmp_path):
    """A position whose frame cannot be fetched (or whose walk raises) is
    skipped: it stays open, the failure is logged, the rest of the cycle
    proceeds, and no exit packet is written for it."""
    all_trades, closes, data, bench, feats, skipped_gap = research
    state, mark, _p = _seed_exit_scenario(research)

    real_provider = _provider_factory(data)

    def flaky(symbol):
        if symbol == "NFLX":
            raise RuntimeError("simulated download failure")
        return real_provider(symbol)

    rep, P = _run_exit_cycle(research, tmp_path, "failskip", state, mark,
                             ["XLF", "INTC"], frame_provider=flaky)
    ts = rep["timestamp"]
    assert ts["status"] == "decided"
    skipped = {s["symbol"]: s for s in rep["live_exits"]["skipped"]}
    assert skipped["NFLX"]["reason"] == "exit_evaluation_failed"
    # NFLX stays open; no close event; no exit packet for it
    assert "NFLX" in state.positions
    assert not [e for e in state.events if e.get("kind") == "close"]
    assert read_exit_packets(P["exit_packet_log"]) == []
    assert rep["exit_packets"] == 0
    # the failure is in the cycle log
    cycle_events = [json.loads(line) for line in
                    open(P["cycle_log"]) if line.strip()]
    assert any(e.get("event") == "exit_evaluation_failed"
               and e.get("symbol") == "NFLX" for e in cycle_events)
    # entries still decided on the (full) book: both RANKED_OUT
    got = {d["symbol"]: d["decision"] for d in ts["decisions"]}
    assert got == {"INTC": RANKED_OUT, "XLF": RANKED_OUT}, got


def test_malformed_exit_event_rejected_before_engine():
    """Generated exit events are validated before the engine: a malformed
    event raises ValueError naming the problem (the caller fails the
    timestamp closed with state untouched)."""
    good = {"symbol": "NFLX", "exit_px": 99.9, "reason": "stop",
            "universe_order": 0}
    _check_exit_events_wellformed([good])  # no raise
    _check_exit_events_wellformed([])  # no raise
    for bad in ({"symbol": "NFLX", "reason": "stop", "universe_order": 0},
                {"symbol": "NFLX", "exit_px": float("nan"),
                 "reason": "stop", "universe_order": 0},
                {"symbol": "NFLX", "exit_px": -5.0,
                 "reason": "stop", "universe_order": 0},
                {"symbol": "NFLX", "exit_px": "oops",
                 "reason": "stop", "universe_order": 0}):
        with pytest.raises(ValueError):
            _check_exit_events_wellformed([bad])


def test_exit_packet_failure_fails_timestamp_closed(research, tmp_path):
    """If exit packets cannot be written, the whole timestamp fails
    closed: state hash unchanged, append-only logs rolled back, the
    failure logged, no partially applied exit."""
    state, mark, _p = _seed_exit_scenario(research)
    before = state.to_dict()
    before_hash = _sha(before)

    P = _exit_cycle_paths(tmp_path, "pktfail")
    # point the exit packet log at a directory: appends raise
    os.makedirs(P["exit_packet_log"], exist_ok=True)
    provider = _provider_factory(research[2])
    rep = run_cycle(
        symbols=["XLF", "INTC"], bar_time=T_EXIT, state=state, mark_fn=mark,
        packet_log=P["packet_log"], snapshot_dir=P["snapshot_dir"],
        vintage=P["vintage"], engine=P["engine"],
        dedup_store=P["dedup"], outbox=P["outbox"],
        delivery_log_path=P["delivery_log"], sender=paper_sender,
        actions_log_path=P["actions_log"], cycle_log_path=P["cycle_log"],
        frame_provider=provider, spy_daily=research[3].get("SPY"),
        live_exits=True, exit_packet_log=P["exit_packet_log"],
        signal_bar="previous")

    assert rep["timestamp"]["status"] == "failed_closed", rep["timestamp"]
    assert "exit_packet_failure" in rep["timestamp"]["reason"]
    # state hash unchanged: no exit applied, no entry taken
    assert _sha(state.to_dict()) == before_hash
    assert state.n_open() == 5 and "NFLX" in state.positions
    assert not [e for e in state.events if e.get("kind") == "close"]
    # logs rolled back to pre-timestamp: a retried cycle rebuilds clean
    # delivery state from the truncated files (the in-memory objects belong
    # to the failed attempt's caller, as in production). The pre-boundary
    # signal evaluations remain — they are facts about the market data,
    # not portfolio state — but no portfolio decision packet was kept.
    assert DedupStore(P["dedup"].path).n_claimed() == 0
    assert PaperOutbox(P["outbox"].path).n_alerts() == 0
    only = P["packet_log"].read_all()
    assert len(only) == 2, only
    assert all(p.get("decision") == "signal" for p in only), only
    assert not any(p.get("type") == "portfolio_decision" for p in only)
    cycle_events = [json.loads(line) for line in
                    open(P["cycle_log"]) if line.strip()]
    assert any(e.get("event") == "timestamp_failed_closed" for e in
               cycle_events)


# ------------------------------------------------- (h) causal inertness
def test_delivery_inert_on_exit_path(research, tmp_path):
    """On the live-exit path: a raising sender cannot mutate state or
    cause recalculation, and delivery enabled vs PHYSICALLY DISABLED is
    byte-identical in decisions and state."""
    def raising_sender(payload):
        raise RuntimeError("simulated alert transport failure")

    state, mark, _p = _seed_exit_scenario(research)
    rep_raise, P_raise = _run_exit_cycle(
        research, tmp_path, "inert-raise", state, mark, ["XLF", "INTC"],
        sender=raising_sender)
    assert rep_raise["timestamp"]["status"] == "decided"
    assert rep_raise["exit_packets"] == 1
    assert "NFLX" not in state.positions
    got_raise = {d["symbol"]: d["decision"]
                 for d in rep_raise["timestamp"]["decisions"]}
    assert got_raise == {"INTC": TAKEN, "XLF": RANKED_OUT}
    # the transport failure is a category-7 log event, not an exception
    delivery_events = [json.loads(line) for line in
                       open(P_raise["delivery_log"]) if line.strip()]
    assert any(e.get("category") == 7 for e in delivery_events)

    # enabled vs physically disabled: byte-identical
    recs = []
    for tag, enabled in (("on", True), ("off", False)):
        s, m, _p = _seed_exit_scenario(research)
        rep, P = _run_exit_cycle(research, tmp_path, f"inert-{tag}", s, m,
                                 ["XLF", "INTC"],
                                 delivery_enabled=enabled)
        dec = rep["timestamp"]["decisions"]
        recs.append((_sha(s.to_dict()), _sha(dec),
                     rep["exit_packets"], len(read_exit_packets(P["exit_packet_log"]))))
    assert recs[0] == recs[1], recs


# ------------------------------------------------- (i) static
def test_no_trading_surface_in_new_code():
    """exits.py and the slice-5 additions carry no alert/trading/network
    surface (the ban-list glob in test_slice1 already covers pine_live/,
    this pins the new modules explicitly)."""
    for name in ("exits.py", "multicycle.py", "packets.py", "replay.py",
                 "portfolio.py"):
        with open(os.path.join(LIVE_DIR, name)) as f:
            src = f.read()
        for pat in BANNED_PATTERNS:
            assert pat not in src, (name, pat)


def test_exit_import_graph_causal_separation():
    """multicycle.py (decision path) may read the exit evaluator, but
    exits.py cannot reach the delivery layers: dedup/alerts import stdlib
    only (slice-3 proof, re-asserted here because exits flow through the
    same cycle)."""
    for mod, path in (("pine_live.dedup", os.path.join(LIVE_DIR, "dedup.py")),
                      ("pine_live.alerts", os.path.join(LIVE_DIR, "alerts.py"))):
        tree = ast.parse(open(path).read())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    imports.add(node.module.split(".")[0])
        stdlib = {"os", "sys", "json", "hashlib", "time", "datetime",
                  "pathlib", "typing", "collections", "dataclasses",
                  "enum", "math", "functools", "__future__", "traceback"}
        assert imports <= stdlib, (mod, imports)
