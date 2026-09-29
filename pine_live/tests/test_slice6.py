"""Slice 6 acceptance tests: the Part-B reconciliation job.

Acceptance gates (commissioned 2026-09-18):
  1. full-window historical replay -> PASS, zero category 2-7 mismatches
  2. paper/live packet replay with delivery physically disabled -> PASS
  3. category-1 isolation: a genuine vendor bar revision lands ONLY in
     bucket 1; the job still passes
  4. first divergence reproducible from stored packets/snapshots alone
     (the job has no download path at all)
  5. read-only + causally inert: input hashes byte-identical before/after,
     delivery modules never invoked, import graph is read-only reuse
  6. deterministic repeated output
  7. corruption drills: tampered snapshot hash and mutated packet field
     detected and localized to the exact packet
  8. strategy-contamination drill: a time-based exit is flagged as
     category 6 (V3.6 has NO time exit; the 30-bar cap is V5.4 Mode B)
  9. no time-based exit exists in the frozen V3.6 exit code (static AST
     scan + behavioral 130-bar hold test)

Read-only and causally inert throughout: nothing here mutates trading
state, sends anything, or touches the network.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import numpy as np
import pytest

import pine_backtest as pb
import pine_live.live_path as lp
from pine_live.portfolio import PortfolioState, reference_mark
from pine_live.sector import SECTOR
from pine_live.packets import PacketLog, engine_version_extended
from pine_live.reconcile import (
    run_reconciliation, _canonical, reference_signal_decision,
    result_digest,
)
from pine_live.multicycle import run_cycle
from pine_live.alerts import paper_sender
from pine_live.exits import evaluate_position_exit, EXIT_REASONS
from pine_live.tests.test_slice2 import (
    _research, _run_full_window, _signal_id, COST,
)
from pine_live.tests.test_slice4 import _provider_factory, _cycle_paths
from pine_live.tests.test_slice5 import _run_window_live_exits

LIVE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(LIVE_DIR)
for _p in (REPO_ROOT,):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _norm_iso(ts) -> str:
    return pd.Timestamp(ts).isoformat()


@pytest.fixture(scope="module")
def research():
    all_trades, closes, data, bench, feats, skipped_gap = _research()
    # Same indicator memoization the slice-5 fixture uses (pure function
    # of the frame; keeps the full-window work fast).
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


@pytest.fixture(scope="module")
def env(research, tmp_path_factory):
    """One full-window live run (delivery enabled) plus the canonical
    reference bundle the reconciliation job consumes."""
    all_trades, closes, data, bench, feats, skipped_gap = research
    _ref_state, ref_taken_idx, _, _, _, _ = _run_full_window()
    ref_taken_set = set(ref_taken_idx)
    tmp_path = tmp_path_factory.mktemp("slice6")
    state, taken_idx, _, _, P, n_live_exits = _run_window_live_exits(
        research, tmp_path, "recon-full", True, ref_taken_set)

    taken_by_t = defaultdict(list)
    for idx in ref_taken_idx:
        tr = all_trades[idx]
        taken_by_t[_norm_iso(tr["entry_time"])].append(_signal_id(tr))
    signal_ids = [_signal_id(tr) for tr in all_trades]
    bundle = {
        "id": "C1-research",
        "frames": data,
        "signal_ids": signal_ids,
        "signal_index": {sid: i for i, sid in enumerate(signal_ids)},
        "trades": all_trades,
        "feats": feats,
        "trade_by_key": {
            (tr["symbol"], _norm_iso(tr["entry_time"])): tr
            for tr in all_trades
        },
        "taken_by_t": dict(taken_by_t),
        "sectors": {sym: SECTOR[sym] for sym in data},
        "cost": COST,
    }
    mark = lambda sym, t: reference_mark(closes, sym, t)  # noqa: E731
    return {
        "research": research, "bundle": bundle, "mark": mark,
        "paths": P, "tmp": tmp_path, "n_live_exits": n_live_exits,
        "ref_taken_idx": ref_taken_idx,
    }


def _recon(env, tag, *, outbox=True, dedup=True, reference=None,
           base=None, now=None, manifest=True):
    """Run the reconciliation job against the module fixture's live
    artifacts. base: optional alternate artifact tree (for drills).
    manifest: pass the live run's settlement manifest (default True;
    the drill trees inherit it via _copy_tree)."""
    e = env
    P = e["paths"]
    if base is not None:
        packet_log = str(Path(base) / "packets.jsonl")
        exit_packet_log = str(Path(base) / "exit_packets.jsonl")
        snapshot_dir = str(Path(base) / "snapshots")
        outbox_p = str(Path(base) / "outbox.jsonl")
        dedup_p = str(Path(base) / "dedup.jsonl")
        manifest_p = str(Path(base) / "reconciliation_manifest.json")
    else:
        packet_log = P["packet_log"].path
        exit_packet_log = P["exit_packet_log"]
        snapshot_dir = P["snapshot_dir"]
        outbox_p = P["outbox"].path
        dedup_p = P["dedup"].path
        manifest_p = P["recon_manifest"]
    report = run_reconciliation(
        packet_log=packet_log,
        exit_packet_log=exit_packet_log,
        snapshot_dir=snapshot_dir,
        exit_snapshot_dir=snapshot_dir,
        reference=reference or e["bundle"],
        mark_fn=e["mark"],
        outbox_path=outbox_p if outbox else None,
        dedup_path=dedup_p if dedup else None,
        manifest_path=manifest_p if manifest else None,
        output_dir=str(e["tmp"] / tag),
        now=now,
    )
    return report, report["report_path"]


def _logic_counts(report):
    return {c: report["result"]["counts_by_category"].get(c, 0)
            for c in ("2", "3", "4", "5", "6", "7")}


def _R(report):
    return report["result"]


# --------------------------------------------------------------------------
# Gate 1: full-window historical replay -> PASS, zero category 2-7
# --------------------------------------------------------------------------

def test_full_window_historical_replay_zero_logic_mismatches(env):
    report, path = _recon(env, "r-full")
    res = _R(report)
    assert res["verdict"] == "PASS", _canonical(res)
    assert _logic_counts(report) == {c: 0 for c in ("2", "3", "4", "5",
                                                    "6", "7")}
    assert res["integrity_errors"] == []
    # scale of what was actually reconciled
    assert res["n_signal_packets"] == 263
    assert res["n_exit_packets"] == 143
    assert res["n_portfolio_packets"] > 0
    # the written report is self-describing: the sha256 it prints
    # verifies against the canonical result section
    with open(path, "r", encoding="utf-8") as f:
        on_disk = json.load(f)
    assert on_disk["result"]["report_sha256"] == \
        result_digest(on_disk["result"])
    assert on_disk["result"]["report_sha256"] == res["report_sha256"]
    assert os.path.exists(path)


# --------------------------------------------------------------------------
# Gate 2: paper/live packet replay, delivery physically disabled
# --------------------------------------------------------------------------

def test_live_packet_replay_delivery_disabled_still_passes(env):
    report, _ = _recon(env, "r-nodelivery", outbox=False, dedup=False)
    res = _R(report)
    assert res["verdict"] == "PASS", _canonical(res)
    assert _logic_counts(report) == {c: 0 for c in ("2", "3", "4", "5",
                                                    "6", "7")}
    assert any("not_configured_skipped" in str(n)
               for n in res["notes"])


# --------------------------------------------------------------------------
# Gate 3: category-1 isolation — genuine vendor bar revision
# --------------------------------------------------------------------------

def _t0_setup(env):
    all_trades = env["research"][0]
    data = env["research"][2]
    entries_by_t = defaultdict(list)
    for idx, tr in enumerate(all_trades):
        entries_by_t[tr["entry_time"]].append(idx)
    t0 = sorted(entries_by_t)[0]
    syms = [all_trades[i]["symbol"] for i in entries_by_t[t0]]
    return all_trades, data, t0, syms


def test_vendor_revision_isolated_as_category_1(env, tmp_path):
    """A vendor-revised bar (one close changed AFTER the signal bar, so the
    decision itself cannot move) is classified as category 1 only: the
    job still passes and no 2-7 bucket gets anything."""
    all_trades, data, t0, syms = _t0_setup(env)
    symbol = syms[0]
    bars = data[symbol]
    loc = int(bars.index.get_loc(pd.Timestamp(t0).tz_convert(bars.index.tz)))
    rev_loc = loc + 3  # after the signal bar: decision cannot move

    def provider(s):
        frame = data[s]
        if s.upper() == symbol.upper():
            frame = frame.copy()
            idx = frame.index[rev_loc]
            frame.at[idx, "Close"] = frame.at[idx, "Close"] * 1.003
        return frame

    base = tmp_path / "drill-cat1"
    P = _cycle_paths(tmp_path, "cat1")
    state = PortfolioState(env["mark"], COST)
    run_cycle(
        symbols=syms, bar_time=t0, state=state, mark_fn=env["mark"],
        packet_log=P["packet_log"], snapshot_dir=P["snapshot_dir"],
        vintage=P["vintage"], engine=P["engine"],
        dedup_store=None, outbox=None, delivery_log_path=P["delivery_log"],
        sender=paper_sender, actions_log_path=None,
        cycle_log_path=P["cycle_log"],
        frame_provider=provider, spy_daily=env["research"][3].get("SPY"),
        live_exits=False, exits=None, exit_packet_log=None,
        signal_bar="previous")
    # one cycle -> one timestamp in scope
    bundle = dict(env["bundle"])
    bundle["id"] = "C1-drill-cat1"
    bundle["signal_ids"] = sorted(
        {_signal_id(tr) for tr in all_trades if tr["entry_time"] == t0})
    bundle["taken_by_t"] = {k: v for k, v in
                            env["bundle"]["taken_by_t"].items()
                            if k == _norm_iso(t0)}
    # no exits in this drill: the engine writes no exit log, so plant the
    # empty one the job requires (a missing file stays a configuration
    # error by design — it must never silently reconcile zero exits).
    (tmp_path / "cat1" / "exit_packets.jsonl").write_text("",
                                                         encoding="utf-8")

    report = run_reconciliation(
        packet_log=P["packet_log"].path,
        exit_packet_log=str(tmp_path / "cat1" / "exit_packets.jsonl"),
        snapshot_dir=P["snapshot_dir"],
        exit_snapshot_dir=P["snapshot_dir"],
        reference=bundle, mark_fn=env["mark"],
        outbox_path=None, dedup_path=None,
        output_dir=str(base))
    res = report["result"]
    assert res["verdict"] == "PASS", _canonical(res)
    assert _logic_counts(report) == {c: 0 for c in ("2", "3", "4", "5",
                                                    "6", "7")}
    assert res["counts_by_category"].get("1", 0) == 1
    line = res["digest_category_1"][0]
    assert line["symbol"] == symbol.upper()
    assert line["cause"] == "vendor_revision"
    assert line["detail"]["decision_flipped"] is False
    # reference comparisons for the revised symbol were honestly skipped
    assert any(symbol.upper() in str(n) for n in res["notes"])


def test_reference_signal_decision_flip_branch(env):
    """The flip-check primitive: True on the real bars for a known
    signal, False when the bars are mangled badly enough to kill the
    signal (volume zeroed -> volume_ok fails), None when the signal
    bar is absent from the frame."""
    all_trades, _, data = env["research"][:3]
    tr = all_trades[0]
    sym = tr["symbol"]
    packet = {"signal_bar_start": _norm_iso(
        data[sym].index[tr["signal_idx"]])}
    assert reference_signal_decision(packet, data[sym]) is True
    mangled = data[sym].copy()
    mangled["Volume"] = 0
    assert reference_signal_decision(packet, mangled) is False
    cut = data[sym].iloc[:tr["signal_idx"]]  # signal bar excluded
    assert reference_signal_decision(packet, cut) is None


# --------------------------------------------------------------------------
# Gate 4: first divergence reproducible from stored artifacts alone
# --------------------------------------------------------------------------

def _copy_tree(env, tag):
    src = Path(env["paths"]["packet_log"].path).parent
    dst = Path(env["tmp"]) / tag
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst


def _mutate_exit_packet(dst, mutate):
    path = dst / "exit_packets.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    packets = [json.loads(line) for line in lines if line.strip()]
    target = packets[0]
    mutate(target)
    packets[0] = target
    path.write_text("\n".join(json.dumps(p) for p in packets) + "\n",
                    encoding="utf-8")
    return target


def test_first_divergence_reproducible_from_artifacts(env):
    dst = _copy_tree(env, "drill-diverge")
    target = _mutate_exit_packet(
        dst, lambda p: p["exit"].__setitem__("exit_px",
                                             p["exit"]["exit_px"] * 1.01))
    report, _ = _recon(env, "r-diverge", base=dst)
    res = report["result"]
    assert res["verdict"] == "FAIL"
    assert res["first_divergence"] is not None
    assert res["first_divergence"]["timestamp"] == \
        target["decision_time"]
    assert res["first_divergence"]["signal_id"] == target["signal_id"]
    assert res["first_divergence"]["category"] == 6
    # the job's signature proves the offline property: there is no
    # provider, downloader, or network parameter anywhere
    params = set(inspect.signature(run_reconciliation).parameters)
    assert not (params & {"provider", "download", "downloader",
                          "network", "fetch", "client"})


# --------------------------------------------------------------------------
# Gate 5: read-only + causally inert
# --------------------------------------------------------------------------

def _tree_hashes(root):
    out = {}
    for dirpath, _, filenames in os.walk(root):
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root)] = hashlib.sha256(
                    f.read()).hexdigest()
    return out


def test_reconciliation_is_read_only(env):
    root = str(Path(env["paths"]["packet_log"].path).parent)
    before = _tree_hashes(root)
    report, _ = _recon(env, "r-readonly")
    after = _tree_hashes(root)
    assert report["result"]["verdict"] == "PASS"
    assert before == after, "reconciliation mutated its inputs"


def test_import_graph_isolation():
    """reconcile.py may only import stdlib, pandas, the canonical
    reference, and the read-only live reuse modules. It must not name
    delivery, dedup-store, or cycle-execution machinery at all."""
    src = Path(LIVE_DIR, "reconcile.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    allowed_roots = {"__future__", "hashlib", "json", "os", "sys",
                     "datetime", "pandas", "pine_backtest", "pine_live"}
    allowed_live_subs = {"packets", "replay", "portfolio", "dedup",
                         "alerts", "exits", "reconcile"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name.split(".")[0] in allowed_roots, a.name
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")
            assert mod[0] in allowed_roots, node.module
            if mod[0] == "pine_live" and len(mod) > 1:
                assert mod[1] in allowed_live_subs, node.module
    forbidden = {"PaperOutbox", "DedupStore", "paper_sender",
                 "deliver_pending", "run_cycle", "run_timestamp",
                 "evaluate_frame", "multicycle", "live_path"}
    # code identifiers only (ast.Name / ast.Attribute): prose in
    # docstrings and comments may mention these modules
    code_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            code_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            code_names.add(node.attr)
    for name in forbidden:
        assert name not in code_names, name
    # and the live execution modules really are absent after import
    code = ("import sys, pine_live.reconcile; "
            "bad=[m for m in sys.modules if m in "
            "('pine_live.multicycle','pine_live.cycle','pine_live.live_path')];"
            "print('BAD:'+','.join(bad) if bad else 'CLEAN')")
    proc = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT,
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "CLEAN", proc.stdout


# --------------------------------------------------------------------------
# Gate 6: deterministic repeated output
# --------------------------------------------------------------------------

def test_repeated_runs_byte_identical(env):
    # fixed `now`: the only wall-clock input. With identical inputs the
    # entire written file — not just the result section — must be
    # byte-identical.
    now = "2026-09-18T00:00:00+00:00"
    r1, p1 = _recon(env, "r-det1", now=now)
    r2, p2 = _recon(env, "r-det2", now=now)
    assert r1["result"]["verdict"] == r2["result"]["verdict"] == "PASS"
    b1 = Path(p1).read_bytes()
    b2 = Path(p2).read_bytes()
    assert b1 == b2, "repeated runs must be byte-identical for identical inputs"
    # and the result section carries the same self-verifying digest
    assert _canonical(r1["result"]).encode("utf-8") == \
        _canonical(r2["result"]).encode("utf-8")
    assert result_digest(r1["result"]) == result_digest(r2["result"])


# --------------------------------------------------------------------------
# Gate 7: corruption drills — detected AND localized
# --------------------------------------------------------------------------

def test_tampered_snapshot_detected_and_localized(env):
    dst = _copy_tree(env, "drill-tamper")
    path = dst / "exit_packets.jsonl"
    packets = [json.loads(line) for line in
               path.read_text(encoding="utf-8").splitlines() if line.strip()]
    target = packets[0]
    snap_name = os.path.basename(target["bars_snapshot_ref"]["path"])
    snap_path = dst / "snapshots" / snap_name
    raw = bytearray(snap_path.read_bytes())
    raw[len(raw) // 2] ^= 0xFF  # flip one byte mid-file
    snap_path.write_bytes(bytes(raw))
    report, _ = _recon(env, "r-tamper", base=dst)
    res = report["result"]
    assert res["verdict"] == "FAIL"
    kinds = [e["kind"] for e in res["integrity_errors"]]
    assert "exit_snapshot_tampered" in kinds
    hit = next(e for e in res["integrity_errors"]
               if e["kind"] == "exit_snapshot_tampered")
    assert hit["signal_id"] == target["signal_id"]
    assert hit["timestamp"] == target["decision_time"]
    assert hit["packet_sha256"]  # the exact tampered packet is pinned


def test_mutated_packet_field_detected_and_localized(env):
    dst = _copy_tree(env, "drill-mutate")
    target = _mutate_exit_packet(
        dst, lambda p: p["exit"].__setitem__("exit_px",
                                             p["exit"]["exit_px"] * 1.01))
    report, _ = _recon(env, "r-mutate", base=dst)
    res = report["result"]
    assert res["verdict"] == "FAIL"
    hits = [m for m in res["mismatches"]
            if m["signal_id"] == target["signal_id"] and m["category"] == 6]
    assert hits, "mutated exit_px must surface as category 6"
    layers = {m["layer"] for m in hits}
    assert "exit-walk" in layers  # the canonical walk re-derives it
    assert res["first_divergence"]["signal_id"] == target["signal_id"]


def _mutate_portfolio_packet(dst, mutate):
    path = dst / "packets.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    packets = [json.loads(line) for line in lines if line.strip()]
    # first slice2-v2 portfolio packet with a single contender (rank
    # order cannot move under a score mutation)
    target = next(p for p in packets
                  if p.get("packet_schema") == "slice2-v2"
                  and p["n_candidates"] == 1)
    mutate(target)
    path.write_text("\n".join(json.dumps(p) for p in packets) + "\n",
                    encoding="utf-8")
    return target


def test_mutated_ranking_score_detected_as_category_4(env):
    """A mutated contender rs_score must surface as category 4
    (ranking): the replayed decision is unchanged (single contender —
    rank order cannot move), but the packet's score no longer matches
    the reference features."""
    dst = _copy_tree(env, "drill-rank")
    target = _mutate_portfolio_packet(
        dst, lambda p: p["contenders"][0].__setitem__(
            "rs_score", p["contenders"][0]["rs_score"] * 1.01))
    sid = target["contenders"][0]["signal_id"]
    report, _ = _recon(env, "r-rank", base=dst)
    res = report["result"]
    assert res["verdict"] == "FAIL"
    hits = [m for m in res["mismatches"]
            if m["signal_id"] == sid and m["category"] == 4]
    assert hits, "mutated rs_score must surface as category 4 (ranking)"
    assert any(m["layer"] == "ranking" for m in hits)
    assert all(m["packet_sha256"] for m in hits)
    # clean classification: nothing outside bucket 4
    other = [m for m in res["mismatches"] if m["category"] != 4]
    assert not other, _canonical(other)
    assert res["first_divergence"]["signal_id"] == sid
    assert res["first_divergence"]["category"] == 4
    assert res["first_divergence"]["timestamp"] == \
        target["decision_time"]


def test_mutated_sector_label_detected_as_category_5(env):
    """A mutated contender sector label must surface as category 5
    (sector cap): the entry decision itself is recomputed from the
    symbol, so only the label check fires."""
    dst = _copy_tree(env, "drill-sector")
    target = _mutate_portfolio_packet(
        dst, lambda p: p["contenders"][0].__setitem__(
            "sector", "WRONG_SECTOR"))
    sid = target["contenders"][0]["signal_id"]
    report, _ = _recon(env, "r-sector", base=dst)
    res = report["result"]
    assert res["verdict"] == "FAIL"
    hits = [m for m in res["mismatches"]
            if m["signal_id"] == sid and m["category"] == 5]
    assert hits, "mutated sector must surface as category 5"
    assert any(m["layer"] == "sector-label" for m in hits)
    other = [m for m in res["mismatches"] if m["category"] != 5]
    assert not other, _canonical(other)
    assert res["first_divergence"]["signal_id"] == sid
    assert res["first_divergence"]["category"] == 5


def test_mutated_portfolio_state_detected_as_category_6(env):
    """A mutated portfolio state observable (n_open_before) must surface
    as category 6 (state/slot): the replay's state-before pre-check
    rejects the packet before any decision is recomputed."""
    dst = _copy_tree(env, "drill-state")
    target = _mutate_portfolio_packet(
        dst, lambda p: p.__setitem__(
            "n_open_before", p["n_open_before"] + 1))
    report, _ = _recon(env, "r-state", base=dst)
    res = report["result"]
    assert res["verdict"] == "FAIL"
    hits = [m for m in res["mismatches"]
            if m["category"] == 6 and m["layer"] == "state-chain"]
    assert hits, "mutated n_open_before must surface as category 6"
    assert any(m["timestamp"] == target["decision_time"] for m in hits)
    other = [m for m in res["mismatches"] if m["category"] != 6]
    assert not other, _canonical(other)
    assert res["first_divergence"]["category"] == 6
    assert res["first_divergence"]["timestamp"] == \
        target["decision_time"]


# --------------------------------------------------------------------------
# Gate 8: strategy-contamination drill — a time-based exit is category 6
# --------------------------------------------------------------------------

def test_time_based_exit_flagged_as_strategy_contamination(env):
    dst = _copy_tree(env, "drill-contam")
    target = _mutate_exit_packet(
        dst, lambda p: p["trigger"].__setitem__("reason", "time_exit"))
    report, _ = _recon(env, "r-contam", base=dst)
    res = report["result"]
    assert res["verdict"] == "FAIL"
    hits = [m for m in res["mismatches"]
            if m["signal_id"] == target["signal_id"]]
    assert any(m["layer"] == "strategy-contamination" and
               m["category"] == 6 for m in hits), \
        "a time-based exit must be flagged as V3.6 strategy contamination"
    assert res["first_divergence"]["signal_id"] == target["signal_id"]


# --------------------------------------------------------------------------
# Gate 9: V3.6 has no time-based exit — static + behavioral guard
# --------------------------------------------------------------------------

def test_no_time_based_exit_in_frozen_v36():
    src = Path(LIVE_DIR, "exits.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    # docstrings may *discuss* the absence of a time exit; only code
    # literals matter here
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if (isinstance(first, ast.Expr) and
                    isinstance(first.value, ast.Constant) and
                    isinstance(first.value.value, str)):
                docstrings.add(id(first.value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for operand in (node.left, *node.comparators):
                assert not (isinstance(operand, ast.Name) and
                            operand.id == "hold_bars"), \
                    "hold_bars must never be compared in V3.6 exits"
        if isinstance(node, ast.Name):
            assert node.id.lower() not in {
                "max_hold", "max_hold_bars", "time_exit",
                "holding_period", "max_holding"}, node.id
        if (isinstance(node, ast.Constant) and
                isinstance(node.value, str) and
                id(node) not in docstrings):
            assert node.value.strip().lower() not in {
                "time_exit", "max_hold", "max_hold_bars",
                "holding_period"}, node.value
    assert set(EXIT_REASONS) == {"stop", "ema55-break", "ema55-bear"}


def test_position_can_hold_past_30_bars_without_exiting():
    """Behavioral half of the V3.6/V5.4 pin: a gentle 130-bar uptrend
    never triggers the frozen exit walk. The 30-bar cap is V5.4 Mode B
    only — if it ever appears here, gate 8's drill catches it."""
    n = 130
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    close = pd.Series(100.0 * (1.0015 ** np.arange(n)), index=idx)
    bars = pd.DataFrame({
        "Open": close.shift(1).fillna(100.0),
        "High": close * 1.002,
        "Low": close * 0.998,
        "Close": close,
        "Volume": 1_000_000,
    }, index=idx)
    assert bars["Close"].notna().all()
    ind = pb.add_pine_indicators(bars)
    entry_idx = 60  # past indicator warmup (e21/e55/e200/atr all defined)
    entry_px = float(bars["Open"].iloc[entry_idx])
    atr = float(ind["atr"].iloc[entry_idx])
    stop_px = entry_px - 1.5 * atr
    tp1_px = entry_px + 2.0 * atr
    res = evaluate_position_exit(
        symbol="TEST", entry_px=entry_px, stop_px=stop_px, tp1_px=tp1_px,
        entry_idx=entry_idx, ind=ind, eval_end_idx=n - 1)
    assert res["triggered"] is False
    assert res["n_bars_walked"] == n - entry_idx
