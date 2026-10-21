"""Shadow-observation core — reference implementation for the TASK -80 design.

PURPOSE
    Record frozen-strategy signals and simulate their hypothetical
    lifecycles in a fully isolated namespace, for prospective OBSERVATION
    only. This is Mike's Track 1 (2026-10-21): a separately labeled
    SHADOW cohort. It is not the forward test, it opens no positions
    anywhere, and its records can never become trades.

HARD ISOLATION (by construction, verified by the safety suite)
    * This module imports ONLY the Python standard library plus, through
      load_pinned_tracker(), the single pinned production module
      v54_exit_tracker.py (a pure, I/O-free state machine) whose SHA-256
      is verified before import. Nothing else is imported.
    * It never imports the production harness or the production log
      writer, and contains no production path literals.
    * Every write it performs is rooted at the caller-supplied shadow
      root directory: one append-only JSONL log and one state file,
      both inside that root. It opens nothing else for writing.
    * The hypothetical lifecycle is computed by an in-memory instance of
      the frozen Mode B tracker owned by this object. The tracker's
      positions live only in this process and in the shadow state file.

RECORDS
    Every record carries: record_kind, schema, cohort (the shadow
    label), counts_as_trade = False, and logged_at (UTC). Signal
    records additionally carry the signal bar's start/close timestamps
    (exchange-local, as produced by the frozen engine) and
    detected_at_utc (when this process recorded the signal).

DELIBERATE DIVERGENCE FROM PRODUCTION (conservative, documented in
DESIGN.md): if a cycle in which a symbol's data was degraded intervenes
after a signal and before its hypothetical entry bar is processed, the
entry is marked unexecutable and never simulated. Production has a
narrower timing exception for single-blip deferrals; the shadow does
not replicate it — observation errs toward FEWER simulated fills.

Nothing in this file launches anything. See DESIGN.md and
LAUNCH_READINESS.md in this package.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

COHORT_LABEL = "SHADOW_OBSERVATION"
SCHEMA_VERSION = "shadow-obs-v1"
SHADOW_ID_PREFIX = "shadow:"
LOG_FILENAME = "shadow_log.jsonl"
STATE_FILENAME = "shadow_state.json"

# The one production module this core executes: the frozen Mode B exit
# state machine. It is imported only after its SHA-256 matches this pin
# (fail-closed). Pinned 2026-10-21 from the running stack.
PINNED_TRACKER_FILENAME = "v54_exit_tracker.py"
PINNED_TRACKER_SHA256 = (
    "3ee92864f1afe98ce543803b8b844c1677a6d0e0ce1a6e61d1b7ea74b329a9e0"
)

# Lifecycle statuses (shadow-side bookkeeping; never production statuses).
ST_AWAITING = "awaiting_entry"
ST_OPEN = "open"
ST_CLOSED = "closed"
ST_UNEXECUTABLE = "unexecutable"
ST_INVALID = "invalid_entry"
ST_SKIPPED_BUSY = "skipped_symbol_busy"


class ShadowError(RuntimeError):
    """Fail-closed error: the shadow refuses to proceed."""


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_pinned_tracker(module_dir: str):
    """Import the frozen Mode B tracker module after pin verification.

    Raises ShadowError on a missing file or a hash mismatch — the shadow
    never runs on unverified code.
    """
    sys.dont_write_bytecode = True  # imports must never write .pyc files
    path = os.path.join(module_dir, PINNED_TRACKER_FILENAME)
    if not os.path.exists(path):
        raise ShadowError(f"pinned tracker module missing: {path}")
    digest = sha256_file(path)
    if digest != PINNED_TRACKER_SHA256:
        raise ShadowError(
            f"pinned tracker hash mismatch: {digest} != {PINNED_TRACKER_SHA256}"
        )
    spec = importlib.util.spec_from_file_location("v54_exit_tracker_pinned", path)
    if spec is None or spec.loader is None:
        raise ShadowError("could not build import spec for pinned tracker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def shadow_id_for(source_signal_id: str) -> str:
    return SHADOW_ID_PREFIX + str(source_signal_id)


class ShadowObserver:
    """One isolated shadow-observation process (in-memory + own files).

    root: the shadow namespace directory. The ONLY directory this object
    writes to. clock: zero-arg callable returning a tz-aware datetime
    (defaults to real UTC now); injected in tests for determinism.
    """

    def __init__(self, root: str, tracker_module: Any,
                 clock: Optional[Callable[[], datetime]] = None):
        self.root = os.path.abspath(root)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.tracker_module = tracker_module
        os.makedirs(self.root, exist_ok=True)
        self.log_path = os.path.join(self.root, LOG_FILENAME)
        self.state_path = os.path.join(self.root, STATE_FILENAME)
        self._cycle_events: List[Dict[str, Any]] = []
        self.state = self._load_state()
        self._reconcile_from_log()
        self.tracker = tracker_module.ModeBTracker(event_sink=self._on_tracker_event)
        # Rehydrate hypothetical positions (plain dicts; the frozen
        # tracker treats re-fed bars as no-ops, so restart is safe).
        self.tracker.positions = self.state.get("tracker_positions", {})

    # -- state ----------------------------------------------------------

    def _load_state(self) -> Dict[str, Any]:
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, encoding="utf-8") as fh:
                    state = json.load(fh)
            except Exception as exc:  # corrupt state: fail closed
                raise ShadowError(f"shadow state unreadable: {exc}")
            if state.get("cohort") != COHORT_LABEL:
                raise ShadowError("shadow state cohort label mismatch")
            return state
        return {
            "schema": SCHEMA_VERSION,
            "cohort": COHORT_LABEL,
            "counts_as_trade": False,
            "created_at_utc": self.clock().isoformat(),
            "cycles": 0,
            "seen_shadow_ids": [],
            "lifecycles": {},
            "tracker_positions": {},
        }

    def _reconcile_from_log(self) -> None:
        """The append-only log is the source of truth (same rule as the
        production log). If a crash landed between a log append and the
        state save, the state can lag the log; on startup, union the
        log's signal ids into the seen set and mark any lifecycle the
        log already closed as closed, so nothing is ever recorded or
        closed twice.
        """
        if not os.path.exists(self.log_path):
            return
        seen = set(self.state.get("seen_shadow_ids", []))
        with open(self.log_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                sid = rec.get("shadow_id")
                if not sid:
                    continue
                if rec.get("record_kind") == "shadow_signal":
                    seen.add(sid)
                elif rec.get("record_kind") == "shadow_close":
                    lc = self.state.get("lifecycles", {}).get(sid)
                    if lc is not None:
                        lc["status"] = ST_CLOSED
        self.state["seen_shadow_ids"] = sorted(seen)

    def _save_state(self) -> None:
        self.state["tracker_positions"] = self.tracker.positions
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.state, fh, default=str)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.state_path)

    # -- record writing ---------------------------------------------------

    def _stamp(self, record: Dict[str, Any], kind: str,
               now: datetime) -> Dict[str, Any]:
        rec = dict(record)
        rec["record_kind"] = kind
        rec["schema"] = SCHEMA_VERSION
        rec["cohort"] = COHORT_LABEL
        rec["counts_as_trade"] = False
        rec["logged_at"] = now.isoformat()
        return rec

    def write_record(self, record: Dict[str, Any], kind: str,
                     now: datetime) -> Dict[str, Any]:
        """Append one labeled record to the shadow log (append-only).

        Defense in depth: a record that does not carry the cohort label
        and the explicit non-trade flag is refused, never written.
        """
        rec = self._stamp(record, kind, now)
        if rec.get("cohort") != COHORT_LABEL or rec.get("counts_as_trade") is not False:
            raise ShadowError("refusing to write an unlabeled record")
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
        return rec

    def _on_tracker_event(self, event: Dict[str, Any]) -> None:
        self._cycle_events.append(dict(event))

    def _flush_tracker_events(self, now: datetime) -> None:
        for ev in self._cycle_events:
            sid = ev.pop("signal_id", None)
            lc = self.state["lifecycles"].get(sid or "", {})
            self.write_record(
                {
                    "shadow_id": sid,
                    "symbol": lc.get("symbol"),
                    "source_signal_id": lc.get("source_signal_id"),
                    "detected_at_utc": now.isoformat(),
                    **ev,
                },
                "shadow_event",
                now,
            )
        self._cycle_events = []

    # -- signals ----------------------------------------------------------

    def _symbol_busy(self, symbol: str) -> bool:
        return any(
            lc.get("symbol") == symbol and lc.get("status") in (ST_AWAITING, ST_OPEN)
            for lc in self.state["lifecycles"].values()
        )

    def record_signal(self, row: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
        """Record one qualified frozen-strategy signal (dedup by id).

        Returns the lifecycle dict, or None when the signal_id was
        already seen (idempotent across restarts).
        """
        sid = shadow_id_for(row["signal_id"])
        if sid in self.state["seen_shadow_ids"]:
            return None
        self.state["seen_shadow_ids"].append(sid)
        busy = self._symbol_busy(row["symbol"])
        lifecycle: Dict[str, Any] = {
            "shadow_id": sid,
            "source_signal_id": row["signal_id"],
            "symbol": row["symbol"],
            "grade": row.get("v54_grade"),
            "signal_bar_start_at": row["signal_bar_start_at"],
            "signal_bar_close_at": row["signal_bar_close_at"],
            "detected_at_utc": now.isoformat(),
            "stop": float(row["stop"]),
            "tp1": float(row["tp1"]),
            "status": ST_SKIPPED_BUSY if busy else ST_AWAITING,
            "blind_during_entry_window": False,
            "entry_bar": None,
            "snapshot": {
                k: row.get(k)
                for k in (
                    "symbol", "theme", "timeframe", "signal_bar_start_at",
                    "signal_bar_close_at", "state", "entry", "protection",
                    "price", "stop", "tp1", "risk_reward", "market_gate",
                    "market_regime", "daily_trend", "weekly_trend",
                    "rel_vol", "adx", "v54_grade", "v54_rule_version",
                    "v53_state", "v53_entry", "v53_would_veto",
                )
            },
        }
        self.state["lifecycles"][sid] = lifecycle
        self.write_record(
            {
                "shadow_id": sid,
                "source_signal_id": row["signal_id"],
                "symbol": row["symbol"],
                "grade": row.get("v54_grade"),
                "signal_bar_start_at": row["signal_bar_start_at"],
                "signal_bar_close_at": row["signal_bar_close_at"],
                "detected_at_utc": now.isoformat(),
                "stop": float(row["stop"]),
                "tp1": float(row["tp1"]),
                "market_gate": row.get("market_gate"),
                "hypothetical": {
                    "entry_convention": "next_bar_open",
                    "exit_stack": "frozen Mode B (pinned v54_exit_tracker)",
                    "lifecycle_status": lifecycle["status"],
                },
            },
            "shadow_signal",
            now,
        )
        if busy:
            self.write_record(
                {
                    "shadow_id": sid,
                    "symbol": row["symbol"],
                    "source_signal_id": row["signal_id"],
                    "detected_at_utc": now.isoformat(),
                    "event": "signal_skipped_shadow",
                    "reason": "position already open/pending for symbol "
                              "(shadow mirrors the one-per-symbol rule; "
                              "the signal record above is preserved)",
                },
                "shadow_event",
                now,
            )
        return lifecycle

    # -- lifecycle advancement ---------------------------------------------

    def _advance_lifecycle(self, lc: Dict[str, Any],
                           frame: List[Dict[str, Any]], now: datetime) -> None:
        sid = lc["shadow_id"]
        bars = sorted(frame, key=lambda b: _parse_ts(b["bar_id"]))
        if lc["status"] == ST_AWAITING:
            after = [b for b in bars
                     if _parse_ts(b["bar_id"]) > _parse_ts(lc["signal_bar_start_at"])]
            if not after:
                return  # entry bar has not completed yet; keep waiting
            entry_bar = after[0]
            if lc.get("blind_during_entry_window"):
                lc["status"] = ST_UNEXECUTABLE
                self.write_record(
                    {
                        "shadow_id": sid,
                        "symbol": lc["symbol"],
                        "source_signal_id": lc["source_signal_id"],
                        "detected_at_utc": now.isoformat(),
                        "event": "hypothetical_entry_unexecutable",
                        "intended_fill_bar": entry_bar["bar_id"],
                        "intended_fill_open": float(entry_bar["open"]),
                        "reason": "symbol data was degraded during the "
                                  "entry window; retrospective hypothetical "
                                  "fill prohibited (shadow rule, stricter "
                                  "than production's single-blip exception)",
                    },
                    "shadow_event",
                    now,
                )
                return
            signal_dict = {
                "signal_id": sid,
                "symbol": lc["symbol"],
                "stop": lc["stop"],
                "tp1": lc["tp1"],
                "v54_grade": lc["grade"],
            }
            pos = self.tracker.open_position(
                signal_dict, float(entry_bar["open"]), entry_bar["bar_id"])
            self._flush_tracker_events(now)
            if pos is None:
                lc["status"] = ST_INVALID
                self.write_record(
                    {
                        "shadow_id": sid,
                        "symbol": lc["symbol"],
                        "source_signal_id": lc["source_signal_id"],
                        "detected_at_utc": now.isoformat(),
                        "event": "hypothetical_entry_invalid",
                        "intended_fill_bar": entry_bar["bar_id"],
                        "intended_fill_open": float(entry_bar["open"]),
                        "reason": "hypothetical entry <= structural stop",
                    },
                    "shadow_event",
                    now,
                )
                return
            lc["status"] = ST_OPEN
            lc["entry_bar"] = entry_bar["bar_id"]
        if lc["status"] == ST_OPEN:
            pos = self.tracker.positions.get(sid)
            if pos is None:
                raise ShadowError(f"tracker position missing for {sid}")
            entry_ts = _parse_ts(lc["entry_bar"])
            last = pos.get("last_processed_bar")
            last_ts = _parse_ts(last) if last else None
            for bar in bars:
                bts = _parse_ts(bar["bar_id"])
                if bts < entry_ts:
                    continue
                if last_ts is not None and bts <= last_ts:
                    continue  # already walked; tracker is idempotent too
                self.tracker.process_bar(sid, {
                    "bar_id": bar["bar_id"],
                    "open": float(bar["open"]),
                    "high": float(bar["high"]),
                    "low": float(bar["low"]),
                    "close": float(bar["close"]),
                    "scanner_state": bar.get("scanner_state"),
                })
            self._flush_tracker_events(now)
            pos = self.tracker.positions.get(sid)
            if pos is not None and pos.get("status") == "closed":
                self._finalize_close(lc, pos, now)

    def _finalize_close(self, lc: Dict[str, Any], pos: Dict[str, Any],
                        now: datetime) -> None:
        if lc["status"] == ST_CLOSED:
            return
        lc["status"] = ST_CLOSED
        summary = self.tracker_module.close_summary(pos, lc.get("snapshot") or {})
        record = dict(summary)
        record.update({
            "shadow_id": lc["shadow_id"],
            "source_signal_id": lc["source_signal_id"],
            "detected_at_utc": now.isoformat(),
            "hypothetical": True,
        })
        # close_summary keys its subject by the production field name;
        # inside the shadow namespace the subject is the shadow id.
        record["signal_id"] = lc["shadow_id"]
        self.write_record(record, "shadow_close", now)

    # -- one cycle ----------------------------------------------------------

    def run_shadow_cycle(self, candidates: List[Dict[str, Any]],
                         frames: Dict[str, List[Dict[str, Any]]],
                         health: Optional[Dict[str, Any]] = None,
                         now: Optional[datetime] = None) -> Dict[str, Any]:
        """Run one observation cycle. Never raises for data problems:
        degraded data produces a DEGRADED cycle record and no signals.

        candidates: frozen-engine qualified rows (engine-row shape).
        frames: symbol -> closed bars (bar dicts; a bar may carry
            "scanner_state" for the frozen EXIT evaluation).
        health: {"market_ok": bool, "scan_complete": bool,
                 "expected_symbols": [...], "degraded_symbols": [...]}.
            expected_symbols are the symbols this cycle's work touches
            (new candidates + live lifecycles); a cycle is DEGRADED
            when the market frame is not ok, the universe scan was
            incomplete, any expected symbol is degraded or lacks a
            usable frame, or any lifecycle had to be deferred.
        """
        now = now or self.clock()
        health = health or {}
        expected = list(health.get("expected_symbols") or
                        sorted({c["symbol"] for c in candidates} | set(frames)))
        degraded_symbols = set(health.get("degraded_symbols") or [])
        for sym in expected:
            if not frames.get(sym):
                degraded_symbols.add(sym)
        market_ok = bool(health.get("market_ok", True))
        scan_complete = bool(health.get("scan_complete", True))
        signals_allowed = market_ok and scan_complete and not any(
            s in degraded_symbols for s in expected)
        status = "HEALTHY" if signals_allowed else "DEGRADED"
        deferred_any = False

        new_signals = 0
        if signals_allowed:
            for row in candidates:
                if self.record_signal(row, now) is not None:
                    new_signals += 1

        # Lifecycle advancement: per symbol, on that symbol's valid data
        # only. A degraded symbol defers explicitly (never an invented
        # bar); an awaiting entry on a degraded symbol goes blind.
        for lc in list(self.state["lifecycles"].values()):
            if lc["status"] not in (ST_AWAITING, ST_OPEN):
                continue
            sym = lc["symbol"]
            if sym in degraded_symbols:
                deferred_any = True
                if lc["status"] == ST_AWAITING:
                    lc["blind_during_entry_window"] = True
                self.write_record(
                    {
                        "shadow_id": lc["shadow_id"],
                        "symbol": sym,
                        "source_signal_id": lc["source_signal_id"],
                        "detected_at_utc": now.isoformat(),
                        "event": "shadow_data_deferred",
                        "kind": "entry" if lc["status"] == ST_AWAITING else "exit",
                        "reason": "symbol data degraded this cycle; "
                                  "lifecycle not advanced on missing data",
                    },
                    "shadow_event",
                    now,
                )
                continue
            frame = frames.get(sym) or []
            if frame:
                self._advance_lifecycle(lc, frame, now)

        if deferred_any:
            status = "DEGRADED"
        self.state["cycles"] = int(self.state.get("cycles", 0)) + 1
        self.state["last_cycle_at_utc"] = now.isoformat()
        self.state["last_cycle_status"] = status
        summary = {
            "cycle": self.state["cycles"],
            "status": status,
            "market_ok": market_ok,
            "scan_complete": scan_complete,
            "expected_symbols": expected,
            "degraded_symbols": sorted(degraded_symbols),
            "new_signals": new_signals,
            "open_lifecycles": sum(
                1 for lc in self.state["lifecycles"].values()
                if lc["status"] in (ST_AWAITING, ST_OPEN)),
            "at_utc": now.isoformat(),
        }
        self.write_record(summary, "shadow_cycle", now)
        self._save_state()
        return summary
