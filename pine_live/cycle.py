"""Slice-3 orchestration: finalize -> dedup -> paper alerts, with failure isolation.

This module is the ONLY place the delivery layers meet the decision engine,
and the meeting is one-directional:

    portfolio (decides) -> packets (logs) -> dedup (exactly-once gate)
        -> alerts (paper outbox)

Data flows downstream only. dedup.py and alerts.py import nothing from
pine_live (stdlib only — see test_dependency_direction_static), so they
cannot reach back upstream. The decision engine never calls them; this
orchestrator calls the engine first, finalizes and logs the decision, and
only then consults the delivery layers.

Failure isolation (parity spec C9):
- Unknown sector label (or any decision-engine exception) at timestamp t:
  the state is rolled back to its exact pre-t snapshot, a refusal packet
  is logged, NO entries are taken at t, NO alerts fire. Fail closed.
- Alert delivery failure: caught inside alerts.deliver_pending (never
  raises) AND wrapped here defensively; portfolio state and the decision
  packet are already finalized and cannot be touched by delivery.
- Data download failure: safe_evaluate_live catches it, logs it, returns
  None. No signal is ever emitted from a failed download.

The 5% portfolio-risk gate (RISK_CAP) is part of the canonical locked
stack (Mike's correction, slice 3): it lives in pine_live.portfolio,
untouched by this module. This module never reorders, skips, or re-runs
decision branches.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pandas as pd

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from pine_live.portfolio import PortfolioState  # noqa: E402
from pine_live.packets import (  # noqa: E402
    PacketLog,
    _canonical,
    append_portfolio_packet,
    build_portfolio_packet,
    engine_version_extended,
)
from pine_live.sector import sector_counts  # noqa: E402
from pine_live.dedup import DedupStore, dedup_key  # noqa: E402
from pine_live.alerts import (  # noqa: E402
    PaperOutbox,
    build_alert_payload,
    deliver_pending,
    paper_sender,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: str, rec: dict) -> None:
    import json
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(_canonical(rec) + "\n")
        f.flush()
        os.fsync(f.fileno())


def run_timestamp(*, state: PortfolioState, mark_fn, t, contenders: list,
                  exits: list, packet_log: PacketLog, vintage: dict,
                  engine: dict | None = None,
                  dedup_store: DedupStore | None = None,
                  outbox: PaperOutbox | None = None,
                  delivery_log_path: str | None = None,
                  sender=paper_sender,
                  actions_log_path: str | None = None) -> dict:
    """Run one timestamp through decide -> packet -> dedup -> alerts.

    dedup_store=None AND outbox=None is the physically-disabled mode: the
    delivery layers are not merely idle, they are never invoked — used by
    the causal-inertness proof (enabled vs disabled must be byte-identical).

    Returns a report dict. Never raises for decision-engine or delivery
    failures (they become refusal / category-7 log events instead).
    """
    t_iso = pd.Timestamp(t).isoformat()
    engine = engine if engine is not None else engine_version_extended()
    state.advance_clock(t)
    applied_exits = state.process_exits(t, exits)

    report = {"t": t_iso, "status": None, "decisions": [],
              "n_exits_applied": len(applied_exits)}

    if not contenders:
        state.settle(t)
        report["status"] = "no_contenders"
        return report

    # --- decide (with exact rollback on ANY engine failure) ---------------
    before = state.to_dict()
    seq_before = len(state.events)
    free_before = state.free_slots()
    n_open_before = state.n_open()
    counts_before = sector_counts(state.positions)
    try:
        decisions = state.decide_entries(t, contenders)
    except Exception as exc:  # noqa: BLE001 — fail closed, never half-applied
        restored = PortfolioState.from_dict(before, mark_fn)
        state.__dict__.clear()
        state.__dict__.update(restored.__dict__)
        refusal = {
            "type": "portfolio_refused",
            "packet_schema": "slice3-v1",
            "decision_time": t_iso,
            "computed_at": _utcnow_iso(),
            "refused_reason": f"decision_engine_exception: {type(exc).__name__}: {exc}",
            "n_contenders": len(contenders),
            "contender_symbols": sorted({c["symbol"] for c in contenders}),
            "state_restored_to_seq": seq_before,
            "data_vintage": dict(vintage),
            "engine_version": dict(engine),
        }
        # PacketLog.append() forces the slice-1 schema; refusal packets carry
        # their own schema, so append directly (same fsync'd semantics).
        _append_jsonl(packet_log.path, refusal)
        state.settle(t)  # clock accounting still advances; no entries taken
        report["status"] = "refused"
        report["refused_reason"] = refusal["refused_reason"]
        return report

    state.settle(t)
    seq_after = len(state.events)

    # --- finalize: packet FIRST, delivery layers only after ----------------
    packet = build_portfolio_packet(
        decision_time=t, contenders=contenders, decisions=decisions,
        free_slots_at_t=free_before, n_open_before=n_open_before,
        n_open_after=state.n_open(),
        sector_counts_before=counts_before,
        sector_counts_after=sector_counts(state.positions),
        seq_before=seq_before, seq_after=seq_after,
        vintage=vintage, engine=engine)
    stored = append_portfolio_packet(packet_log, packet)
    report["decisions"] = decisions
    report["status"] = "decided"

    # --- delivery layers (downstream only; skipped entirely if disabled) --
    if dedup_store is None and outbox is None:
        report["delivery"] = "disabled"
        return report

    actions = []
    for d in stored["decisions"]:
        key = dedup_key(d["signal_id"], t_iso, seq_after)
        if dedup_store is not None:
            claimed = dedup_store.check_and_claim(
                key, {"signal_id": d["signal_id"], "symbol": d["symbol"],
                      "decision": d["decision"], "decision_time": t_iso})
        else:
            claimed = True  # no dedup configured: every decision acts once
        if claimed:
            action = "acted"
            if d["decision"] == "TAKEN" and outbox is not None:
                payload = build_alert_payload(stored, d)
                outbox.enqueue(payload)
        else:
            action = "duplicate_suppressed"
        actions.append({"t": t_iso, "signal_id": d["signal_id"],
                        "symbol": d["symbol"], "decision": d["decision"],
                        "dedup_key": key, "action": action})
    if actions_log_path is not None:
        for a in actions:
            _append_jsonl(actions_log_path, a)
    report["n_actions"] = sum(1 for a in actions if a["action"] == "acted")
    report["n_suppressed"] = sum(
        1 for a in actions if a["action"] == "duplicate_suppressed")

    # --- alert delivery: failures are category-7 log events, never raised --
    if outbox is not None and delivery_log_path is not None:
        try:
            drep = deliver_pending(outbox, delivery_log_path, sender=sender)
        except Exception as exc:  # noqa: BLE001 — defense in depth; deliver_pending never raises by contract
            drep = {"attempted": 0, "delivered": 0, "failed": 0,
                    "harness_error": f"{type(exc).__name__}: {exc}"}
            _append_jsonl(delivery_log_path, {
                "event": "delivery_harness_failed", "category": 7,
                "at": _utcnow_iso(), "error": str(exc)})
        report["delivery"] = drep
    return report


def safe_evaluate_live(symbol: str, packet_log: PacketLog, snapshot_dir: str,
                       cycle_log_path: str, **kwargs):
    """Evaluate one symbol live, failing closed on download (or any)
    failure: the failure is logged, None is returned, and NO signal is
    ever emitted from a failed evaluation. (Parity spec C9 drill 1.)"""
    from pine_live.live_path import evaluate_live
    try:
        return evaluate_live(symbol, packet_log=packet_log,
                             snapshot_dir=snapshot_dir, **kwargs)
    except Exception as exc:  # noqa: BLE001 — fail closed, log everything
        _append_jsonl(cycle_log_path, {
            "event": "evaluation_failed", "at": _utcnow_iso(),
            "symbol": symbol.upper(),
            "error_type": type(exc).__name__, "error": str(exc),
            "fail_closed": True})
        return None
