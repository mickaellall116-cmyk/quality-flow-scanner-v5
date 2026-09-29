"""V5.4 forward-test logger — append-only audit log.

The original signal snapshot (with raw context) is preserved verbatim at
qualification time. Lifecycle events and the final trade summary are
appended afterwards. History is never rewritten: updates are new lines,
not edits. signal_id is the stable key from qualification through final
exit.

JSONL format, one record per line:
  {"type": "signal", ...}  # immutable original snapshot
  {"type": "event", "signal_id": ..., ...}
  {"type": "close", "signal_id": ..., ...}  # frozen-schema final summary

Nothing here modifies V5.3.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class ForwardLog:
    """Append-only JSONL forward-test log."""

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    # -- writes (append-only) -------------------------------------------

    def _append(self, record: Dict[str, Any]) -> Dict[str, Any]:
        record = dict(record)
        record.setdefault("logged_at", datetime.now(timezone.utc).isoformat())
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
        return record

    def log_signal(self, signal_row: Dict[str, Any], entry_px: Optional[float] = None,
                   entry_bar_id: Optional[str] = None) -> Dict[str, Any]:
        """Preserve the original qualification snapshot verbatim, plus entry.

        Entry is unknown at detection time (it happens at the next bar's
        open), so entry_px/entry_bar_id default to None and the entry is
        recorded later via the tracker's "opened" event.
        """
        return self._append({"type": "signal", **signal_row,
                             "entry_px": entry_px, "entry_bar": entry_bar_id})

    def log_event(self, signal_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """Append a lifecycle event (tp1_taken, profit_protect_armed, ...)."""
        return self._append({"type": "event", "signal_id": signal_id, **event})

    def log_close(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Append the frozen-schema final trade summary."""
        return self._append({"type": "close", **summary})

    # -- reads (rebuild from the log; the log is the source of truth) ----

    def _iter(self):
        if not os.path.exists(self.path):
            return
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def signal_ids(self) -> List[str]:
        return [r["signal_id"] for r in self._iter() if r.get("type") == "signal"]

    def get_signal(self, signal_id: str) -> Optional[Dict[str, Any]]:
        for r in self._iter():
            if r.get("type") == "signal" and r.get("signal_id") == signal_id:
                return r
        return None

    def get_events(self, signal_id: str) -> List[Dict[str, Any]]:
        return [r for r in self._iter()
                if r.get("type") == "event" and r.get("signal_id") == signal_id]

    def get_close(self, signal_id: str) -> Optional[Dict[str, Any]]:
        closes = [r for r in self._iter()
                  if r.get("type") == "close" and r.get("signal_id") == signal_id]
        return closes[-1] if closes else None

    def grade_counts(self) -> Dict[str, int]:
        counts = {"A": 0, "B": 0, "C": 0}
        for r in self._iter():
            if r.get("type") == "signal":
                g = r.get("v54_grade")
                if g in counts:
                    counts[g] += 1
        return counts
