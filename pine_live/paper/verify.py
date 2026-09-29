"""Continuous reconciliation for the paper phase: replay + halt.

After every wake-up's cycles, EVERY new packet is replayed against the
canonical reference on its pinned bars:

  slice1-v1 signal packet  -> replay.replay_packet
  slice2-v2 decision       -> replay.replay_portfolio_decision
                             (needs the pre-cycle serialized state)
  slice5-v1 exit packet    -> replay.replay_exit_decision
  refused packets          -> not replayable (no snapshot by design);
                             logged as informational, never a mismatch.

ANY replay mismatch is a category 2-7 halt condition: the runner writes
paper_state/HALT with the diff plus a classification attempt, logs loudly,
and exits non-zero. The runner stays halted until a human clears HALT
(see PAPER.md) — clearing it is a human root-cause + sign-off decision,
never code.

Category-1 (data/vendor difference) handling: when a signal-packet replay
fails on indicator/price diffs, the verifier re-fetches the symbol's bars
and diffs the pinned snapshot against fresh bars. If the bars genuinely
differ (Yahoo revised a closed bar after the decision), the mismatch is
classified category 1 — still recorded in the HALT file for human review,
but the classification attempt is attached. (The runner halts either way:
a flipped decision needs a human to confirm the category-1 call before
paper continues. The halt file says which category the evidence points
to; the human decides.)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from pine_live.packets import EXIT_PACKET_SCHEMA
from pine_live.replay import (
    replay_exit_decision,
    replay_packet,
    replay_portfolio_decision,
)

PORTFOLIO_SCHEMA = "slice2-v2"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def halt_path(state_dir: str) -> str:
    return os.path.join(state_dir, "HALT")


def is_halted(state_dir: str) -> bool:
    return os.path.exists(halt_path(state_dir))


def write_halt(state_dir: str, *, reason: str, classification: dict,
               context: dict) -> str:
    """Write the HALT file. Returns its path. Never raises."""
    path = halt_path(state_dir)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    body = {
        "halted_at": _utcnow_iso(),
        "reason": reason,
        "classification": classification,
        "context": context,
        "how_to_clear": ("human root-cause required: fix the underlying "
                         "issue, document it, get explicit sign-off, then "
                         "delete this file. See pine_live/PAPER.md."),
    }
    line = json.dumps(body, indent=1, sort_keys=True, default=str)
    with open(path, "w", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())
    return path


def classify_packet(packet: dict) -> str:
    """Return 'signal' | 'portfolio' | 'exit' | 'refused' | 'unknown'."""
    if packet.get("decision") == "refused":
        return "refused"
    if packet.get("type") == "portfolio_refused":
        # Timestamp-level fail-closed refusal: a legitimate, expected
        # artifact (the engine refused rather than decide on bad state).
        # Nothing to replay; informational only.
        return "refused"
    schema = packet.get("packet_schema")
    if schema == PORTFOLIO_SCHEMA or packet.get("type") == "portfolio_decision":
        return "portfolio"
    if schema == EXIT_PACKET_SCHEMA:
        return "exit"
    if schema == "slice1-v1" or "signal_id" in packet:
        return "signal"
    return "unknown"


def verify_packet(packet: dict, *, snapshot_dir: str, mark_fn,
                  state_before: dict | None) -> dict:
    """Replay one packet. Returns a report dict with keys:
    replayed (bool), exact (bool), kind, detail (the replay diff), and
    packet identity (signal_id / decision_time / symbol). Never raises.
    """
    kind = classify_packet(packet)
    ident = {
        "kind": kind,
        "signal_id": packet.get("signal_id"),
        "symbol": packet.get("symbol"),
        "decision_time": packet.get("decision_time"),
    }
    try:
        if kind == "refused":
            return {**ident, "replayed": False,
                    "reason": "refused packet: nothing to replay",
                    "exact": True}
        if kind == "signal":
            rep = replay_packet(packet, snapshot_dir)
        elif kind == "portfolio":
            if state_before is None:
                return {**ident, "replayed": False,
                        "reason": "no pre-cycle state available",
                        "exact": False}
            rep = replay_portfolio_decision(packet, state_before, mark_fn)
        elif kind == "exit":
            rep = replay_exit_decision(packet, snapshot_dir)
        else:
            return {**ident, "replayed": False,
                    "reason": f"unknown packet schema "
                              f"{packet.get('packet_schema')!r}",
                    "exact": False}
    except Exception as exc:  # noqa: BLE001 — verification reports, never raises
        return {**ident, "replayed": False,
                "reason": f"replay raised {type(exc).__name__}: {exc}",
                "exact": False}
    return {**ident, "replayed": bool(rep.get("replayed", True)),
            "exact": bool(rep.get("exact", False)), "detail": rep}


def _attempt_category1(packet: dict, verify_report: dict,
                       fresh_provider) -> dict:
    """Cheap category-1 detector: re-fetch the symbol's bars and diff the
    packet's pinned snapshot against the fresh frame. If the bars the
    decision used differ from today's bars, the mismatch is a data/vendor
    difference (category 1), not a logic bug. Returns a classification
    dict; on any failure returns {'category': 'unclassified', ...}.
    """
    try:
        import pandas as pd
        from pine_live.packets import load_snapshot
        symbol = packet.get("symbol")
        ref = (packet.get("bars_snapshot_ref") or {})
        snap_path = ref.get("path")
        if not symbol or not snap_path or not os.path.exists(snap_path):
            return {"category": "unclassified",
                    "reason": "no pinned snapshot to compare"}
        pinned = load_snapshot(snap_path, ref.get("sha256", ""))
        fresh = fresh_provider(symbol)
        # Compare overlapping bars on OHLCV.
        common = pinned.index.intersection(fresh.index)
        if len(common) == 0:
            return {"category": "unclassified",
                    "reason": "no overlapping bars with fresh download"}
        diffs = []
        for col in ("Open", "High", "Low", "Close", "Volume"):
            a = pinned.loc[common, col].astype(float)
            b = fresh.loc[common, col].astype(float)
            bad = (a - b).abs() > 1e-8
            if bool(bad.any()):
                ix = common[bad][:5]
                diffs.append({"column": col,
                              "n_differing": int(bad.sum()),
                              "first": [pd.Timestamp(t).isoformat()
                                        for t in ix]})
        if diffs:
            return {"category": 1,
                    "layer": "data/vendor difference",
                    "evidence": "pinned snapshot bars differ from fresh "
                                "download (Yahoo revision after decision)",
                    "bar_diffs": diffs}
        return {"category": "unclassified",
                "reason": "bars identical to fresh download; mismatch is "
                          "NOT a vendor revision"}
    except Exception as exc:  # noqa: BLE001 — classification is best-effort
        return {"category": "unclassified",
                "reason": f"category-1 probe failed: "
                          f"{type(exc).__name__}: {exc}"}


def verify_wake_up(*, state_dir: str, new_packets: list,
                   state_before_by_t: dict, snapshot_dir: str, mark_fn,
                   fresh_provider=None) -> dict:
    """Replay every new packet from one wake-up.

    Returns {"n_packets", "n_replayed", "mismatches": [...],
    "halted": bool, "halt_file": path|None}. On the FIRST mismatch the
    HALT file is written and verification stops (one halt reason at a
    time; the human clears it, then the next wake-up re-verifies).
    """
    mismatches: list = []
    n_replayed = 0
    for packet in new_packets:
        t = packet.get("decision_time")
        rep = verify_packet(packet, snapshot_dir=snapshot_dir,
                            mark_fn=mark_fn,
                            state_before=state_before_by_t.get(t))
        if not rep.get("replayed"):
            # Refused packets: informational only.
            if rep.get("kind") == "refused":
                continue
            mismatches.append({**rep, "classification": {
                "category": "unclassified",
                "reason": rep.get("reason", "replay impossible")}})

            break
        n_replayed += 1
        if not rep.get("exact"):
            classification = {"category": "unclassified",
                              "reason": "not yet classified"}
            # Category-1 probe only for signal packets (the ones whose
            # inputs are pinned bars that Yahoo can revise).
            if rep.get("kind") == "signal" and fresh_provider is not None:
                classification = _attempt_category1(
                    packet, rep, fresh_provider)
            mismatches.append({**rep, "classification": classification})
            break

    result = {"n_packets": len(new_packets), "n_replayed": n_replayed,
              "mismatches": mismatches, "halted": False, "halt_file": None}
    if mismatches:
        m = mismatches[0]
        path = write_halt(
            state_dir,
            reason=f"replay mismatch on {m['kind']} packet "
                   f"{m.get('signal_id') or m.get('decision_time')}",
            classification=m["classification"],
            context={"packet_identity": {k: m.get(k) for k in
                                         ("kind", "signal_id", "symbol",
                                          "decision_time")},
                     "replay_detail": m.get("detail")})
        result["halted"] = True
        result["halt_file"] = path
    return result
