"""Shadow SIGNAL-ONLY observer core — successor to the task -80 design.

WHY THIS MODULE EXISTS (ChatGPT expedite review of -80, Issue #1
comment 6353427339): the -80 package's synthetic safety suite passed
6/6 but its runner was not deployable. Four blockers, and how this
successor closes each BY CONSTRUCTION:

  B1  -80's runner main() unconditionally raised "design-stage
      module" — no operational entrypoint existed.
      HERE: shadow_signal_runner.main() is a real entrypoint. It
      runs a dry-run mode on synthetic fixtures with no network, and
      its live mode is gated by a launch-authorization artifact
      (Mike's GO) instead of a blanket raise. The gate is an
      authorization check, not a missing entrypoint.

  B2  -80's observe_once() set health["market_ok"] = True
      unconditionally; build_frames() swallowed a market-frame
      failure and still labeled the cycle healthy — a blind cycle
      could read HEALTHY / no-signal.
      HERE: the core DEFAULTS market_ok to False when the binding
      does not positively supply it, and the runner derives
      market_ok from an actual market-frame fetch result. A blind
      or incomplete cycle is recorded DEGRADED with named reasons
      and records NO signals.

  B3  -80 never compared signal_bar_close_at to a frozen
      prospective launch instant: stale signals could be accepted
      on first launch (prohibited backfill) and a lifecycle could
      be simulated retrospectively.
      HERE: the launch watermark T0 is frozen into a launch
      manifest inside the shadow root at first initialization and
      can never move (reopening with a different T0 refuses). A
      signal is recorded only if its bar CLOSED strictly after T0
      and at or before the cycle instant (a bar that has not
      closed yet is a partial bar and is refused). Refusals are
      themselves appended as evidence records. Stage 1 simulates
      NOTHING, so there is no retrospective-fill surface at all.

  B4  -80's crash seam: a crash between the log append and the
      state save could mark a signal seen while its lifecycle was
      lost (state and log were separate artifacts).
      HERE: there is no state file. The append-only log is the
      ONLY record; the seen-set is rebuilt from the log at every
      startup, so a committed record can never be lost and can
      never be duplicated by a restart. A torn final line (an
      append interrupted mid-write) is detected at startup and
      truncated — it was never a committed record — and the
      recovery is itself logged.

SCOPE (stage 1, per the assignment): record the frozen strategy's
qualified signals, prospectively, as timestamped SHADOW_OBSERVATION
records with counts_as_trade = False. NO hypothetical entries, NO
exit simulation, NO fills of any kind. The pinned Mode B exit
tracker is deliberately NOT imported: there is nothing to simulate
at this gate. Lifecycle/hypothetical mode, if ever wanted, is a
separate later candidate with its own catch-up and crash-seam
tests.

ISOLATION: this module imports only the Python standard library.
Every write is rooted at the caller-supplied shadow root: the
launch manifest and the append-only log, nothing else. It opens
no production path and imports no production module.

Nothing in this file launches anything. Launch requires Mike's
explicit GO naming a prospective start instant (see
LAUNCH_READINESS.md).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

COHORT_LABEL = "SHADOW_OBSERVATION"
SCHEMA_VERSION = "shadow-signal-v1"
LOG_FILENAME = "shadow_log.jsonl"
MANIFEST_FILENAME = "launch_manifest.json"

ET = ZoneInfo("America/New_York")
# The frozen V5.4 4H grid: bar opens at 09:30 and 13:30 ET.
GRID_OPEN_WALL = {(9, 30), (13, 30)}


class ShadowError(RuntimeError):
    """Fail-closed error: the observer refuses to proceed."""


def _parse_ts(value: Any) -> Optional[datetime]:
    """Parse an ISO timestamp; None unless it is tz-aware."""
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        return None
    return dt


class SignalObserver:
    """Append-only prospective signal recorder (one shadow root).

    root: the shadow namespace directory — the ONLY directory this
    object writes to. launch_t0: the frozen prospective watermark
    (tz-aware). A signal is recordable only if its bar closed
    strictly after launch_t0. clock: injectable for tests.
    """

    def __init__(self, root: str, launch_t0: datetime,
                 clock: Optional[Callable[[], datetime]] = None):
        if launch_t0.tzinfo is None or launch_t0.utcoffset() is None:
            raise ShadowError("launch T0 must be tz-aware")
        self.root = os.path.abspath(root)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.log_path = os.path.join(self.root, LOG_FILENAME)
        self.manifest_path = os.path.join(self.root, MANIFEST_FILENAME)
        os.makedirs(self.root, exist_ok=True)
        self.t0 = self._init_manifest(launch_t0)
        self.seen_signal_ids: set = set()
        self.signal_count = 0
        self._load_log()

    # -- launch manifest: the frozen watermark ----------------------

    def _init_manifest(self, launch_t0: datetime) -> datetime:
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, encoding="utf-8") as fh:
                    manifest = json.load(fh)
            except Exception as exc:
                raise ShadowError(f"launch manifest unreadable: {exc}")
            if manifest.get("cohort") != COHORT_LABEL:
                raise ShadowError("launch manifest cohort mismatch")
            recorded = _parse_ts(manifest.get("launch_t0_utc"))
            if recorded is None:
                raise ShadowError("launch manifest T0 unparseable")
            if recorded != launch_t0:
                raise ShadowError(
                    "launch T0 is frozen at first initialization "
                    f"({recorded.isoformat()}); refusing a different "
                    f"T0 ({launch_t0.isoformat()}) — a moved watermark "
                    "would admit backfill")
            return recorded
        manifest = {
            "schema": SCHEMA_VERSION,
            "cohort": COHORT_LABEL,
            "counts_as_trade": False,
            "launch_t0_utc": launch_t0.astimezone(timezone.utc).isoformat(),
            "created_at_utc": self.clock().isoformat(),
            "mode": "signal_only",
            "simulated_fills": False,
        }
        tmp = self.manifest_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.manifest_path)
        return launch_t0

    # -- the log is the only state -----------------------------------

    def _load_log(self) -> None:
        """Rebuild the seen-set from the log; repair a torn tail.

        A final line that does not parse is the tail of an append
        interrupted mid-write: it was never committed, so the file
        is truncated back to the last complete record and the
        recovery is logged as its own record. Complete records are
        never altered.
        """
        if not os.path.exists(self.log_path):
            return
        good_offset = 0
        torn = False
        with open(self.log_path, "rb") as fh:
            while True:
                line = fh.readline()
                if not line:
                    break
                try:
                    rec = json.loads(line.decode("utf-8"))
                except Exception:
                    torn = True
                    break
                good_offset = fh.tell()
                if rec.get("record_kind") == "shadow_signal":
                    sid = rec.get("shadow_id")
                    if sid:
                        self.seen_signal_ids.add(sid)
                        self.signal_count += 1
        if torn:
            with open(self.log_path, "r+b") as fh:
                fh.truncate(good_offset)
            self._append({
                "event": "torn_tail_recovered",
                "detail": "an interrupted append left an incomplete "
                          "final line; it was truncated because it "
                          "was never a committed record",
            }, "shadow_recovery", self.clock())

    def _append(self, record: Dict[str, Any], kind: str,
                now: datetime) -> Dict[str, Any]:
        rec = dict(record)
        rec["record_kind"] = kind
        rec["schema"] = SCHEMA_VERSION
        rec["cohort"] = COHORT_LABEL
        rec["counts_as_trade"] = False
        rec["logged_at"] = now.isoformat()
        if rec.get("cohort") != COHORT_LABEL or \
                rec.get("counts_as_trade") is not False:
            raise ShadowError("refusing to write an unlabeled record")
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return rec

    # -- signal validation (the B3 gate) ------------------------------

    def _validate_candidate(self, row: Dict[str, Any],
                            now: datetime) -> Optional[str]:
        """None if recordable, else the named refusal reason."""
        if not row.get("signal_id") or not row.get("symbol"):
            return "MALFORMED_SIGNAL_ROW"
        start = _parse_ts(row.get("signal_bar_start_at"))
        close = _parse_ts(row.get("signal_bar_close_at"))
        if start is None or close is None:
            return "TZ_NAIVE_OR_UNPARSEABLE_STAMPS"
        if close <= start:
            return "BAR_CLOSE_NOT_AFTER_START"
        start_et = start.astimezone(ET)
        if (start_et.hour, start_et.minute) not in GRID_OPEN_WALL:
            return "OFF_GRID_BAR_START"
        if close <= self.t0:
            return "PRELAUNCH_SIGNAL"
        if close > now:
            return "PARTIAL_BAR_NOT_CLOSED"
        return None

    # -- one cycle ------------------------------------------------------

    def run_cycle(self, candidates: List[Dict[str, Any]],
                  health: Optional[Dict[str, Any]] = None,
                  now: Optional[datetime] = None) -> Dict[str, Any]:
        """Run one observation cycle.

        health (binding-supplied, defaults are fail-closed):
          market_ok: must be positively True — the market frame was
            actually fetched this cycle. Absent/False = blind.
          scan_complete: the frozen scan covered the full cohort.
          degraded_symbols: symbols the binding could not serve.
        A blind or incomplete cycle is recorded DEGRADED with named
        reasons and records NO signals and NO refusals — degraded
        data is never reinterpreted.
        """
        now = now or self.clock()
        health = health or {}
        market_ok = health.get("market_ok") is True
        scan_complete = health.get("scan_complete") is True
        degraded_symbols = sorted(health.get("degraded_symbols") or [])
        reasons = []
        if not market_ok:
            reasons.append("MARKET_FRAME_NOT_OK")
        if not scan_complete:
            reasons.append("SCAN_INCOMPLETE")
        if degraded_symbols:
            reasons.append("DEGRADED_SYMBOLS")
        healthy = not reasons

        recorded, refused, duplicates = 0, [], 0
        if healthy:
            for row in candidates:
                sid = "shadow:" + str(row.get("signal_id"))
                if sid in self.seen_signal_ids:
                    duplicates += 1
                    continue
                reason = self._validate_candidate(row, now)
                if reason is not None:
                    refused.append({"signal_id": row.get("signal_id"),
                                    "symbol": row.get("symbol"),
                                    "reason": reason})
                    self._append({
                        "shadow_id": sid,
                        "source_signal_id": row.get("signal_id"),
                        "symbol": row.get("symbol"),
                        "reason": reason,
                        "signal_bar_start_at":
                            row.get("signal_bar_start_at"),
                        "signal_bar_close_at":
                            row.get("signal_bar_close_at"),
                        "launch_t0_utc": self.t0.isoformat(),
                    }, "shadow_refusal", now)
                    continue
                self._append({
                    "shadow_id": sid,
                    "source_signal_id": row["signal_id"],
                    "symbol": row["symbol"],
                    "grade": row.get("v54_grade"),
                    "signal_bar_start_at":
                        row["signal_bar_start_at"],
                    "signal_bar_close_at":
                        row["signal_bar_close_at"],
                    "detected_at_utc": now.isoformat(),
                    "launch_t0_utc": self.t0.isoformat(),
                    "stop": row.get("stop"),
                    "tp1": row.get("tp1"),
                    "market_gate": row.get("market_gate"),
                    "snapshot": {
                        k: row.get(k) for k in (
                            "symbol", "theme", "timeframe",
                            "signal_bar_start_at", "signal_bar_close_at",
                            "state", "entry", "price", "stop", "tp1",
                            "risk_reward", "market_gate",
                            "market_regime", "daily_trend",
                            "weekly_trend", "rel_vol", "adx",
                            "v54_grade", "v54_rule_version")
                    },
                }, "shadow_signal", now)
                self.seen_signal_ids.add(sid)
                self.signal_count += 1
                recorded += 1

        summary = {
            "status": "HEALTHY" if healthy else "DEGRADED",
            "degraded_reasons": reasons,
            "market_ok": market_ok,
            "scan_complete": scan_complete,
            "degraded_symbols": degraded_symbols,
            "candidates_seen": len(candidates),
            "new_signals_recorded": recorded,
            "signals_refused": refused,
            "duplicates_skipped": duplicates,
            "total_signals_recorded": self.signal_count,
            "launch_t0_utc": self.t0.isoformat(),
            "at_utc": now.isoformat(),
        }
        self._append(summary, "shadow_cycle", now)
        return summary
