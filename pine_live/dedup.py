"""Duplicate suppression — SLICE 3.

CAUSAL SEPARATION (Mike's contract): this module is STRUCTURALLY incapable
of influencing trading logic. It imports nothing from pine_live except
nothing at all — stdlib only. It operates solely on finalized decision
identity (signal_id + decision bar + portfolio-state version) AFTER the
decision engine has run and the packet has been logged. It can only answer
one question: "has this exact finalized decision already been acted on?"

The dedup check therefore can NEVER alter eligibility, ranking, sector-cap,
or risk-gate decisions: those are computed by pine_live.portfolio BEFORE
this module is ever consulted, and this module has no import path back to
them. Verified by test_slice3.test_dependency_direction_static (AST-level
import-graph assertion).

Key design: dedup_key = sha256(signal_id | decision_time | state_seq_after).
state_seq_after is the portfolio state's event-log sequence AFTER the
decision was applied (packet field state_event_log_range[1]). It pins the
exact portfolio-state version the decision was finalized against, so a
rerun/retry/overlapping cycle that reproduces the same finalized decision
produces the same key, while any genuine state change produces a new key.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def dedup_key(signal_id: str, decision_time_iso: str,
              state_seq_after: int) -> str:
    """Deterministic identity of one finalized decision.

    Same finalized decision (same signal, same bar, same resulting state
    version) -> same key, always. Any difference -> different key.
    """
    body = _canonical({
        "signal_id": signal_id,
        "decision_time": decision_time_iso,
        "state_seq_after": int(state_seq_after),
    })
    return "ddq:" + hashlib.sha256(body.encode("utf-8")).hexdigest()[:32]


class DedupStore:
    """Persistent record of acted-on finalized decisions.

    Append-only JSONL. check_and_claim returns True exactly once per key
    (the first time): that is the single permitted "act". Every later call
    with the same key returns False ("duplicate_suppressed") and records
    the suppression. The store never sees, touches, or influences the
    decision logic — it only sees keys.
    """

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._claimed: set = set()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    if rec.get("event") == "claimed":
                        self._claimed.add(rec["key"])

    def is_claimed(self, key: str) -> bool:
        return key in self._claimed

    def check_and_claim(self, key: str, record: dict) -> bool:
        """Atomically (for this process) test-and-set one key.

        Returns True if this call claimed it (action permitted — exactly
        once per key, ever). Returns False if already claimed (the action
        must be skipped). Both outcomes are logged; the log is the proof
        of exactly-once action.
        """
        if key in self._claimed:
            self._append({"event": "duplicate_suppressed", "key": key,
                          "at": _utcnow_iso(),
                          "signal_id": record.get("signal_id")})
            return False
        self._claimed.add(key)
        rec = {"event": "claimed", "key": key, "at": _utcnow_iso()}
        rec.update(record)
        self._append(rec)
        return True

    def n_claimed(self) -> int:
        return len(self._claimed)

    def _append(self, rec: dict) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(_canonical(rec) + "\n")
            f.flush()
            os.fsync(f.fileno())
