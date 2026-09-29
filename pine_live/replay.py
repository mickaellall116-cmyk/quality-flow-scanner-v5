"""Deterministic replay: packet + snapshot + reference code -> same decision.

Usage:
    python3 replay.py <packet_json_file_or_inline_json>

The replay loads the bar snapshot referenced by the packet, verifies its
sha256, re-runs the canonical reference functions (add_pine_indicators,
pine_buy_signal from pine_backtest), and diffs the recomputed decision and
indicator values against the packet. Exit 0 = exact reproduction.
"""

from __future__ import annotations

import json
import os
import sys

import pandas as pd

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from pine_backtest import add_pine_indicators, pine_buy_signal  # noqa: E402
from pine_live.packets import load_snapshot  # noqa: E402

TOL = 1e-10


def replay_packet(packet: dict, snapshot_dir: str | None = None) -> dict:
    """Recompute the decision from packet + snapshot. Returns the diff report."""
    if packet.get("decision") == "refused":
        return {"replayed": False,
                "reason": f"refused packet: {packet.get('refused_reason')}"}
    ref = packet.get("bars_snapshot_ref") or {}
    snap_path = ref.get("path")
    if snapshot_dir and snap_path and not os.path.isabs(snap_path):
        snap_path = os.path.join(snapshot_dir, os.path.basename(snap_path))
    if not snap_path or not os.path.exists(snap_path):
        return {"replayed": False, "reason": "snapshot not found"}
    bars = load_snapshot(snap_path, ref["sha256"])  # hash verified inside

    target = pd.Timestamp(packet["signal_bar_start"])
    matches = bars.index[bars.index == target]
    if len(matches) != 1:
        return {"replayed": False,
                "reason": f"signal bar {target} not unique in snapshot"}
    i = int(bars.index.get_loc(target))

    ind = add_pine_indicators(bars)
    decision = bool(pine_buy_signal(ind, i))
    expected = packet["decision"] == "signal"

    ind_diff = {}
    for k, v in packet["indicators_at_i"].items():
        rv = ind.iloc[i][k]
        if v is None and pd.isna(rv):
            continue
        if v is None or pd.isna(rv) or abs(float(rv) - float(v)) > TOL:
            ind_diff[k] = {"packet": v, "recomputed": None if pd.isna(rv) else float(rv)}

    ohlcv = packet["signal_bar_ohlcv"]
    bar = bars.iloc[i]
    px_diff = {
        k: {"packet": ohlcv[k2], "snapshot": float(bar[k2.capitalize()])}
        for k, k2 in (("open", "open"), ("high", "high"), ("low", "low"),
                      ("close", "close"), ("volume", "volume"))
        if abs(ohlcv[k2] - float(bar[{"open": "Open", "high": "High", "low": "Low",
                                      "close": "Close", "volume": "Volume"}[k2]])) > TOL
    }

    ok = (decision == expected) and not ind_diff and not px_diff
    return {
        "replayed": True,
        "signal_id": packet["signal_id"],
        "packet_decision": packet["decision"],
        "recomputed_decision": "signal" if decision else "no_signal",
        "decision_match": decision == expected,
        "indicator_diffs": ind_diff,
        "price_diffs": px_diff,
        "exact": ok,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    arg = sys.argv[1]
    packet = json.loads(arg) if arg.lstrip().startswith("{") else json.load(open(arg))
    report = replay_packet(packet)
    print(json.dumps(report, indent=1, default=str))
    return 0 if report.get("exact") else 1


# ------------------------------------------------- slice 2: portfolio replay
def replay_portfolio_decision(packet: dict, state_before: dict, mark_fn) -> dict:
    """Re-run decide_entries from a slice2-v2 packet + the serialized prior
    state. Returns the diff report; exact=True means the replay reproduced
    every contender's decision, rank, and reason bit-for-bit.

    state_before: PortfolioState.to_dict() captured BEFORE the decision.
    mark_fn: the same (symbol, t) -> price function the live path used.
    """
    from pine_live.portfolio import PortfolioState
    from pine_live.sector import sector_counts

    if packet.get("packet_schema") != "slice2-v2":
        return {"replayed": False,
                "reason": f"not a slice2-v2 packet: {packet.get('packet_schema')}"}
    st = PortfolioState.from_dict(state_before, mark_fn)
    t = pd.Timestamp(packet["decision_time"])

    # Pre-checks: the restored state's observable "before" must match the
    # packet, otherwise we are not replaying the same situation.
    pre_diffs = {}
    if sector_counts(st.positions) != packet["sector_counts_before"]:
        pre_diffs["sector_counts_before"] = {
            "packet": packet["sector_counts_before"],
            "state": sector_counts(st.positions)}
    if st.n_open() != packet["n_open_before"]:
        pre_diffs["n_open_before"] = {"packet": packet["n_open_before"],
                                     "state": st.n_open()}
    if pre_diffs:
        return {"replayed": False, "reason": "state-before mismatch",
                "pre_diffs": pre_diffs}

    contenders = [
        {"signal_id": c["signal_id"], "symbol": c["symbol"],
         "entry_px": c["entry_px"], "stop_px": c["stop_px"],
         "tp1_px": c["tp1_px"], "rs_score": c["rs_score"],
         "universe_order": c["universe_order"]}
        for c in packet["contenders"]
    ]
    decisions = st.decide_entries(t, contenders)

    diffs = []
    exp = {d["signal_id"]: d for d in packet["decisions"]}
    if [d["signal_id"] for d in decisions] != [d["signal_id"] for d in packet["decisions"]]:
        diffs.append({"order": "decision order differs"})
    for d in decisions:
        e = exp.get(d["signal_id"])
        if e is None:
            diffs.append({"signal_id": d["signal_id"], "missing": "in packet"})
            continue
        for k in ("decision", "reason_detail", "rank", "contested"):
            if d[k] != e[k]:
                diffs.append({"signal_id": d["signal_id"], k: {
                    "packet": e[k], "recomputed": d[k]}})
        if d["rs_score"] != e["rs_score"]:
            diffs.append({"signal_id": d["signal_id"], "rs_score": {
                "packet": e["rs_score"], "recomputed": d["rs_score"]}})
        if d["marked_equity_at_t"] != e["marked_equity_at_t"]:
            diffs.append({"signal_id": d["signal_id"], "marked_equity_at_t": {
                "packet": e["marked_equity_at_t"],
                "recomputed": d["marked_equity_at_t"]}})
    # Post-checks: the replayed state's "after" must match the packet too.
    if sector_counts(st.positions) != packet["sector_counts_after"]:
        diffs.append({"sector_counts_after": {
            "packet": packet["sector_counts_after"],
            "recomputed": sector_counts(st.positions)}})
    if st.n_open() != packet["n_open_after"]:
        diffs.append({"n_open_after": {"packet": packet["n_open_after"],
                                      "recomputed": st.n_open()}})

    return {
        "replayed": True,
        "decision_time": packet["decision_time"],
        "n_contenders": len(contenders),
        "diffs": diffs,
        "exact": not diffs,
    }


if __name__ == "__main__":
    sys.exit(main())


# --- Slice 5: exit replay --------------------------------------------------

def replay_exit_decision(packet: dict, snapshot_dir: str | None = None) -> dict:
    """Replay a slice-5 exit packet from its bars snapshot alone.

    The snapshot is hash-verified on load (tampering is rejected, not
    papered over). The pure exit walk is re-run over the whole snapshot
    (walked bars through the trigger bar, plus the fill bar); the
    recomputed trigger time / reason / tp1 flag / exit price / hold bars
    / net R / realized_after must match exactly. Returns
    ``{"replayed": True, "exact": bool, "diffs": {...}, ...}``; a packet
    that cannot be replayed returns ``replayed: False`` with a reason —
    never an exception, never a guess.
    """
    from pine_live.exits import evaluate_position_exit
    from pine_live.packets import (EXIT_PACKET_SCHEMA, load_exit_snapshot)
    from pine_backtest import _outcome

    def _no(reason: str) -> dict:
        return {"replayed": False, "reason": reason}

    if not isinstance(packet, dict):
        return _no("packet is not a dict")
    if packet.get("packet_schema") != EXIT_PACKET_SCHEMA:
        return _no(f"schema {packet.get('packet_schema')!r} != "
                   f"{EXIT_PACKET_SCHEMA!r}")
    ref = packet.get("bars_snapshot_ref") or {}
    snap_path = ref.get("path")
    if snapshot_dir and snap_path and not os.path.isabs(snap_path):
        snap_path = os.path.join(snapshot_dir, os.path.basename(snap_path))
    if not snap_path or not os.path.exists(snap_path):
        return _no("bars snapshot not found")
    try:
        bars = load_exit_snapshot(snap_path, ref.get("sha256", ""))
    except (RuntimeError, OSError, ValueError, KeyError) as e:
        return _no(f"snapshot rejected: {e}")

    pos = packet.get("position") or {}
    try:
        res = evaluate_position_exit(
            symbol=packet.get("symbol", "?"),
            entry_px=float(pos["entry_px"]), stop_px=float(pos["stop_px"]),
            tp1_px=float(pos["tp1_px"]), entry_idx=0, ind=bars,
            eval_end_idx=len(bars) - 1)
    except Exception as e:  # noqa: BLE001 - replay reports, never raises
        return _no(f"exit walk failed on replay: {e}")

    diffs: dict = {}
    exp_trigger = packet.get("trigger") or {}
    exp_exit = packet.get("exit") or {}
    if not res["triggered"]:
        diffs["triggered"] = {"packet": True, "recomputed": False}
    else:
        for key, exp_key in (("trigger_bar_time", "trigger_bar_time"),
                             ("fill_bar_time", "fill_bar_time")):
            if res[key] != exp_trigger.get(exp_key):
                diffs[key] = {"packet": exp_trigger.get(exp_key),
                              "recomputed": res[key]}
        if res["reason"] != exp_trigger.get("reason"):
            diffs["reason"] = {"packet": exp_trigger.get("reason"),
                               "recomputed": res["reason"]}
        if res["tp1_hit"] != exp_trigger.get("tp1_hit"):
            diffs["tp1_hit"] = {"packet": exp_trigger.get("tp1_hit"),
                                "recomputed": res["tp1_hit"]}
        if res["hold_bars"] != exp_exit.get("hold_bars"):
            diffs["hold_bars"] = {"packet": exp_exit.get("hold_bars"),
                                  "recomputed": res["hold_bars"]}
        if abs(res["exit_px"] - float(exp_exit.get("exit_px", "nan"))) > 1e-12:
            diffs["exit_px"] = {"packet": exp_exit.get("exit_px"),
                                "recomputed": res["exit_px"]}
    # Resulting state: rebuild the exact pre-exit PortfolioState from the
    # packet, apply exactly one exit through the real engine, and require
    # the resulting serialized state to equal the packet's post_exit_state
    # exactly. This proves the packet is a complete, replayable record —
    # not just a decision, but the state transition itself.
    from pine_live.portfolio import PortfolioState
    pre = packet.get("pre_exit_state") or {}
    post = packet.get("post_exit_state") or {}
    try:
        _, _, net_r, _ = _outcome(float(pos["entry_px"]),
                                  float(pos["stop_px"]),
                                  float(res.get("exit_px", float("nan"))),
                                  float(packet.get("cost", 0.0004)))
        if abs(net_r - float(exp_exit.get("net_r", "nan"))) > 1e-12:
            diffs["net_r"] = {"packet": exp_exit.get("net_r"),
                              "recomputed": net_r}
        st = PortfolioState.from_dict(pre, lambda sym, t: 0.0)
        st.process_exits(pd.Timestamp(packet.get("decision_time")), [{
            "symbol": str(packet.get("symbol", "?")).upper(),
            "exit_px": float(res.get("exit_px", float("nan"))),
            "reason": res.get("reason"),
            "universe_order": 0,
        }])
        got = st.to_dict()
        state_diffs = _dict_diffs(post, got)
        if state_diffs:
            diffs["post_exit_state"] = state_diffs
    except (KeyError, TypeError, ValueError) as e:
        diffs["state_recompute"] = {"error": str(e)}

    return {"replayed": True, "exact": not diffs, "diffs": diffs,
            "symbol": packet.get("symbol"),
            "n_bars_replayed": len(bars)}


def _dict_diffs(expected: dict, got: dict, path: str = "") -> dict:
    """Exact recursive diff of two JSON-round-tripped dicts.

    Floats must be bit-identical (JSON repr round-trips doubles
    exactly, and the engine recomputation is deterministic), so plain
    == is the right check — any difference is a real divergence, not
    noise. Returns {path: {"expected": ..., "got": ...}}.
    """
    diffs: dict = {}
    if isinstance(expected, dict) and isinstance(got, dict):
        for k in expected:
            if k not in got:
                diffs[f"{path}.{k}"] = {"expected": expected[k],
                                        "got": "<missing>"}
            else:
                diffs.update(_dict_diffs(expected[k], got[k],
                                         f"{path}.{k}"))
        for k in got:
            if k not in expected:
                diffs[f"{path}.{k}"] = {"expected": "<missing>",
                                        "got": got[k]}
    elif isinstance(expected, list) and isinstance(got, list):
        if len(expected) != len(got):
            diffs[path or "<root>"] = {
                "expected": f"len {len(expected)}",
                "got": f"len {len(got)}"}
        else:
            for i, (e, g) in enumerate(zip(expected, got)):
                diffs.update(_dict_diffs(e, g, f"{path}[{i}]"))
    else:
        if not (expected == got):
            diffs[path or "<root>"] = {"expected": expected, "got": got}
    return diffs
