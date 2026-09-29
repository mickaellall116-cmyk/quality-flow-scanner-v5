"""Paper alert delivery — SLICE 3.

CAUSAL SEPARATION (Mike's contract): this module is STRUCTURALLY incapable
of influencing trading logic or portfolio state. It imports nothing from
pine_live — stdlib only. It consumes FINALIZED decisions (plain dicts,
already decided and packet-logged by the pipeline) and does three things:

  1. build_alert_payload: derive the alert payload from the finalized
     decision packet's fields ONLY (copy/rename — never recompute, never
     invent). A missing required field raises KeyError rather than being
     defaulted.
  2. PaperOutbox.enqueue: record the alert in a local append-only JSONL
     outbox. Idempotent on alert_id: re-enqueueing the same alert is a
     no-op returning the existing record.
  3. deliver_pending: attempt delivery of queued alerts through an
     INJECTABLE sender callable. ANY exception from the sender is caught,
     logged as a parity-spec category-7 (alert-delivery mismatch) event,
     and NEVER propagates. deliver_pending itself never raises.

Paper destination: the local outbox file. NOTHING here can reach Mike's
phone/chat/email — wiring real notifications is a separate, explicit
Mike decision (see SLICE3.md). Retries reuse the same alert_id, so the
dedup key makes retries safe and idempotent.

Failure semantics (parity spec C9): an alert failure must NOT mutate
portfolio state, must NOT trigger strategy recalculation, and must NOT
suppress the decision packet (the packet is written BEFORE this module
is ever called — see cycle.py).
"""

from __future__ import annotations

import hashlib
import json
import os
import traceback
from datetime import datetime, timezone

ALERT_SCHEMA = "slice3-v1"
DELIVERY_CATEGORY = 7  # parity spec mismatch taxonomy, category 7
MAX_DELIVERY_ATTEMPTS = 3


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def alert_id_for(signal_id: str, decision_time_iso: str) -> str:
    """Deterministic alert id. Same finalized decision -> same id, so
    retries and re-enqueues are idempotent by construction."""
    body = _canonical({"signal_id": signal_id,
                       "decision_time": decision_time_iso})
    return "alert:" + hashlib.sha256(body.encode("utf-8")).hexdigest()[:32]


# Fields the payload is allowed to carry, and where each comes from in the
# finalized portfolio-decision packet. This table IS the "derived, never
# recomputed" guarantee: the builder below may only copy these.
_PAYLOAD_FIELDS = (
    # (payload key, packet decision-entry key or packet-level key)
    ("signal_id", "signal_id"),
    ("symbol", "symbol"),
    ("decision", "decision"),
    ("reason_detail", "reason_detail"),
    ("rs_score", "rs_score"),
    ("rank", "rank"),
    ("contested", "contested"),
    ("marked_equity_at_t", "marked_equity_at_t"),
    ("decision_time", "@decision_time"),  # packet-level
)


def build_alert_payload(packet: dict, decision_entry: dict) -> dict:
    """Build the paper-alert payload from a finalized decision.

    Pure field copy from the packet + decision entry. No recomputation,
    no defaults: a missing field raises KeyError instead of being invented.
    """
    payload = {"alert_schema": ALERT_SCHEMA}
    for pkey, src in _PAYLOAD_FIELDS:
        if src == "@decision_time":
            payload[pkey] = packet["decision_time"]
        else:
            payload[pkey] = decision_entry[src]  # KeyError if absent: fail loud
    payload["alert_id"] = alert_id_for(payload["signal_id"],
                                       payload["decision_time"])
    payload["paper_only"] = True
    payload["note"] = ("paper alert: derived from finalized decision packet; "
                       "no execution, no real notification wired")
    return payload


def paper_sender(payload: dict) -> bool:
    """Default sender: paper delivery. Records nothing external; returning
    True means 'delivered to the paper outbox'. Injectable for tests —
    pass a sender that raises to drill delivery failure."""
    return True


class PaperOutbox:
    """Local append-only outbox (JSONL, event-sourced).

    Events: alert_queued, alert_delivered, alert_failed (retryable),
    alert_exhausted. Current status per alert_id is derived by replaying
    the log. Nothing leaves this machine.
    """

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._status: dict = {}
        self._attempts: dict = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    ev = json.loads(line)
                    aid = ev.get("alert_id")
                    if not aid:
                        continue
                    if ev["event"] == "alert_queued":
                        self._status.setdefault(aid, "queued")
                    elif ev["event"] == "alert_delivered":
                        self._status[aid] = "delivered"
                    elif ev["event"] == "alert_failed":
                        self._attempts[aid] = ev.get("attempt", 0)
                        self._status[aid] = "failed_retryable"
                    elif ev["event"] == "alert_exhausted":
                        self._status[aid] = "exhausted"

    def enqueue(self, payload: dict) -> dict:
        """Idempotent enqueue: same alert_id twice -> existing record, no
        duplicate write. Returns the alert record."""
        aid = payload["alert_id"]
        if aid in self._status:
            return {"alert_id": aid, "status": self._status[aid],
                    "duplicate_enqueue": True}
        self._append({"event": "alert_queued", "at": _utcnow_iso(),
                      "alert_id": aid, "payload": payload})
        self._status[aid] = "queued"
        self._attempts[aid] = 0
        return {"alert_id": aid, "status": "queued",
                "duplicate_enqueue": False}

    def pending(self) -> list:
        """alert_ids eligible for a delivery attempt."""
        return [aid for aid, st in self._status.items()
                if st in ("queued", "failed_retryable")
                and self._attempts.get(aid, 0) < MAX_DELIVERY_ATTEMPTS]

    def queued_payloads(self) -> dict:
        """alert_id -> payload for currently known alerts (rebuilt from log)."""
        out = {}
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    ev = json.loads(line)
                    if ev.get("event") == "alert_queued":
                        out[ev["alert_id"]] = ev["payload"]
        return out

    def n_alerts(self) -> int:
        return len(self._status)

    def status_of(self, alert_id: str):
        return self._status.get(alert_id)

    def _append(self, ev: dict) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(_canonical(ev) + "\n")
            f.flush()
            os.fsync(f.fileno())


def deliver_pending(outbox: PaperOutbox, delivery_log_path: str,
                    sender=paper_sender) -> dict:
    """Attempt delivery of pending alerts. NEVER raises: every sender
    exception is caught and logged as a category-7 delivery event.

    Returns a report {attempted, delivered, failed, errors}. A failure
    changes nothing except the outbox/delivery logs — it cannot reach
    portfolio state or the decision engine (this function has no reference
    to either, by construction).
    """
    os.makedirs(os.path.dirname(os.path.abspath(delivery_log_path)),
                exist_ok=True)
    payloads = outbox.queued_payloads()
    report = {"attempted": 0, "delivered": 0, "failed": 0, "errors": []}
    for aid in outbox.pending():
        payload = payloads.get(aid)
        attempt = outbox._attempts.get(aid, 0) + 1
        report["attempted"] += 1
        try:
            ok = sender(payload)
        except Exception as exc:  # noqa: BLE001 — the whole point: never propagate
            ok = False
            err = {"error_type": type(exc).__name__, "error": str(exc),
                   "traceback_tail": traceback.format_exc(limit=3)}
        else:
            err = None
        if ok:
            outbox._append({"event": "alert_delivered", "at": _utcnow_iso(),
                            "alert_id": aid, "attempt": attempt})
            outbox._status[aid] = "delivered"
            report["delivered"] += 1
        else:
            report["failed"] += 1
            if attempt >= MAX_DELIVERY_ATTEMPTS:
                outbox._append({"event": "alert_exhausted",
                                "at": _utcnow_iso(), "alert_id": aid,
                                "attempt": attempt})
                outbox._status[aid] = "exhausted"
            else:
                outbox._append({"event": "alert_failed", "at": _utcnow_iso(),
                                "alert_id": aid, "attempt": attempt,
                                "retryable": True})
                outbox._status[aid] = "failed_retryable"
            outbox._attempts[aid] = attempt
            event = {"event": "alert_delivery_failed",
                     "category": DELIVERY_CATEGORY,
                     "at": _utcnow_iso(), "alert_id": aid,
                     "signal_id": (payload or {}).get("signal_id"),
                     "attempt": attempt,
                     "retryable": attempt < MAX_DELIVERY_ATTEMPTS,
                     "error": err}
            with open(delivery_log_path, "a", encoding="utf-8") as f:
                f.write(_canonical(event) + "\n")
                f.flush()
                os.fsync(f.fileno())
            report["errors"].append({"alert_id": aid, "attempt": attempt,
                                    "error": err})
    return report
