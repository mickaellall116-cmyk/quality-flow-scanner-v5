"""P8 — As-of signal / EXIT-path research telemetry (prospective).

QF-EQUITY43-DEV-MEASUREMENT-FIXES-20261025-29, item P8.

Implements the adopted telemetry spec as CODE for future research
capture: Mike's full-state journal direction (bridge 9087bf0, 2026-10-24)
and the -25 §A6 keys T1–T6. This module is prospective only: it records
events as they occur under frozen as-of semantics. It invents no
historical values, backfills nothing, and changes no production, pilot,
or S1 component — the shadow cohort adopts it only under its own launch
gates.

Record types
------------
SIGNAL_FIRE (T1 + T2 + price levels)
    Full signal-time state at every candidate fire, taken or not:
    entry-predicate values with thresholds and margins, ADX/DI,
    trendScore, SessionVWAP distance, relative volume, EMA geometry,
    rs with its benchmark as-of stamp, market-gate state, signal grade,
    gate/disposition reasons; admission state (open slots, sector
    occupancy, planned heat before/after, rank margin); and every price
    level (signal close, ATR, initial stop threshold, TP1, intended
    entry).
BAR_PATH (T4 + T5)
    Per-bar record for an open position: bar OHLC, the geometry series
    in force (entry, initial stop, TP1, runner), threshold events
    (first TP1 touch bar, first stop-threshold breach bar, breach count,
    bars under threshold) and MAE/MFE inputs for the bar.
EXIT_DECISION (T3 + T5 final)
    The exit-decision bar's OHLC (including its CLOSE — the field whose
    absence made the DEV overshoot split NOT_RECOVERABLE), the threshold
    values in force on that bar (runner, EMA55), the decision, and the
    resulting fill reference.
EXECUTION (T6)
    Order / acknowledgment / fill price + timestamps per leg. A
    signal-only feed cannot establish fills (-25 §A6), so a journal in
    signal-only mode REFUSES EXECUTION records; they are accepted only
    when the writer is constructed with execution_authorized=True (a
    separately authorized paper-execution lane).

As-of / causality guards (all fail-closed, raising TelemetryError)
------------------------------------------------------------------
  * bar_finalized must be True — nothing is recorded from an unfinished
    bar.
  * decision_time (bar completion) must equal signal_time + bar
    duration; a record whose decision precedes the bar's completion is
    lookahead and is refused.
  * recorded_at must be >= decision_time (no retro-stamped records).
  * Append-only monotonicity per (symbol): signal_idx strictly
    increasing across SIGNAL_FIRE records, and no record may carry a
    decision_time earlier than the stream's last appended decision_time
    (no backfill).
  * Strict schemas: unknown fields are refused (no silent drift), and
    every required field must be present and non-null.
  * Integrity: each line carries prev_hash and a sha256 record hash over
    its canonical JSON; verify_lines() re-walks the chain and reports
    the first tampered or out-of-order line.

Storage format: JSONL, one record per line, append-only.
"""
import hashlib
import json
import os

BAR_DURATION_HOURS = 4


class TelemetryError(ValueError):
    pass


def _req(d, fields, rtype):
    missing = [f for f in fields if f not in d or d[f] is None]
    if missing:
        raise TelemetryError(f"{rtype}: missing/null required fields "
                             f"{missing}")


def _no_unknown(d, allowed, rtype):
    extra = sorted(set(d) - set(allowed))
    if extra:
        raise TelemetryError(f"{rtype}: unknown fields refused {extra}")


SIGNAL_FIRE_FIELDS = {
    # identity / timing
    "symbol", "signal_idx", "signal_time", "decision_time", "recorded_at",
    "bar_finalized",
    # T1 signal state
    "predicates", "adx", "di_plus", "di_minus", "trend_score",
    "vwap_distance", "rel_volume", "ema_state", "rs", "benchmark_asof",
    "market_gate", "signal_grade", "gate_reasons",
    # T2 admission state
    "open_slots", "sector_occupancy", "heat_before", "heat_after",
    "rank_margin",
    # price levels
    "signal_close", "atr", "stop_threshold", "tp1_level", "intended_entry",
    "disposition",
}
BAR_PATH_FIELDS = {
    "symbol", "signal_idx", "bar_idx", "bar_time", "decision_time",
    "recorded_at", "bar_finalized", "open_px", "high", "low", "close",
    "entry", "stop_threshold", "tp1_level", "runner",
    "tp1_touched", "stop_breached", "breach_count", "bars_under_threshold",
    "mae_input", "mfe_input",
}
EXIT_DECISION_FIELDS = {
    "symbol", "signal_idx", "decision_bar_idx", "decision_bar_time",
    "decision_time", "recorded_at", "bar_finalized",
    "decision_bar_open", "decision_bar_high", "decision_bar_low",
    "decision_bar_close", "runner_in_force", "ema55_in_force",
    "decision", "exit_reason", "fill_time", "fill_price",
}
EXECUTION_FIELDS = {
    "symbol", "signal_idx", "leg", "order_time", "ack_time", "fill_time",
    "fill_price", "order_id", "recorded_at",
}
_SCHEMAS = {
    "SIGNAL_FIRE": SIGNAL_FIRE_FIELDS,
    "BAR_PATH": BAR_PATH_FIELDS,
    "EXIT_DECISION": EXIT_DECISION_FIELDS,
    "EXECUTION": EXECUTION_FIELDS,
}


def _parse_ts(s):
    from datetime import datetime
    return datetime.fromisoformat(s)


def validate_record(record, execution_authorized=False):
    """Fail-closed schema + causality validation of one record dict."""
    rtype = record.get("record_type")
    if rtype not in _SCHEMAS:
        raise TelemetryError(f"unknown record_type {rtype!r}")
    if rtype == "EXECUTION" and not execution_authorized:
        raise TelemetryError(
            "EXECUTION records refused in signal-only mode: a feed "
            "cannot establish fills (T6 requires a separately "
            "authorized execution lane)")
    body = {k: v for k, v in record.items()
            if k not in ("record_type", "prev_hash", "record_hash")}
    _no_unknown(body, _SCHEMAS[rtype], rtype)
    _req(body, _SCHEMAS[rtype], rtype)
    if rtype in ("SIGNAL_FIRE", "BAR_PATH", "EXIT_DECISION"):
        if body["bar_finalized"] is not True:
            raise TelemetryError(
                f"{rtype}: bar_finalized must be True — records are "
                f"taken only on completed bars")
    if rtype == "SIGNAL_FIRE":
        sig = _parse_ts(body["signal_time"])
        dec = _parse_ts(body["decision_time"])
        rec = _parse_ts(body["recorded_at"])
        from datetime import timedelta
        if dec != sig + timedelta(hours=BAR_DURATION_HOURS):
            raise TelemetryError(
                "SIGNAL_FIRE: decision_time must equal signal_time + "
                "bar duration (the bar's completion); an earlier "
                "decision is lookahead")
        if rec < dec:
            raise TelemetryError(
                "SIGNAL_FIRE: recorded_at precedes decision_time "
                "(retro-stamped record refused)")
    return True


def _canonical(record):
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def record_hash(record):
    body = {k: v for k, v in record.items() if k != "record_hash"}
    return hashlib.sha256(_canonical(body).encode()).hexdigest()


class TelemetryJournal:
    """Append-only, hash-chained telemetry writer (in-memory line list
    or a file path). Prospective: enforces per-symbol monotonicity so
    historical backfill is refused."""

    def __init__(self, path=None, execution_authorized=False):
        self.path = path
        self.execution_authorized = execution_authorized
        self.lines = []
        self._last_hash = "GENESIS"
        self._last_signal_idx = {}
        self._last_decision_time = {}
        if path and os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self._ingest_existing(json.loads(line))

    def _ingest_existing(self, record):
        if record.get("prev_hash") != self._last_hash:
            raise TelemetryError("existing journal chain broken on load")
        if record_hash(record) != record.get("record_hash"):
            raise TelemetryError("existing journal hash mismatch on load")
        self.lines.append(json.dumps(record))
        self._last_hash = record["record_hash"]
        self._track(record)

    def _track(self, record):
        rtype = record["record_type"]
        if rtype == "SIGNAL_FIRE":
            sym = record["symbol"]
            if record["signal_idx"] <= self._last_signal_idx.get(sym, -1):
                raise TelemetryError(
                    f"SIGNAL_FIRE: signal_idx not strictly increasing "
                    f"for {sym} (backfill or duplicate refused)")
            self._last_signal_idx[sym] = record["signal_idx"]
        dt = record.get("decision_time")
        if dt is not None:
            sym = record["symbol"]
            if dt < self._last_decision_time.get(sym, ""):
                raise TelemetryError(
                    f"{rtype}: decision_time earlier than the stream's "
                    f"last appended decision_time for {sym} (backfill "
                    f"refused)")
            self._last_decision_time[sym] = dt

    def append(self, record):
        record = dict(record)
        validate_record(record,
                        execution_authorized=self.execution_authorized)
        self._track(record)
        record["prev_hash"] = self._last_hash
        record["record_hash"] = record_hash(record)
        line = _canonical(record)
        self.lines.append(line)
        self._last_hash = record["record_hash"]
        if self.path:
            with open(self.path, "a") as f:
                f.write(line + "\n")
        return record


def verify_lines(lines):
    """Re-walk a journal's lines; return (ok, first_bad_index_or_None)."""
    prev = "GENESIS"
    for i, line in enumerate(lines):
        try:
            record = json.loads(line)
        except Exception:
            return False, i
        if record.get("prev_hash") != prev:
            return False, i
        if record_hash(record) != record.get("record_hash"):
            return False, i
        prev = record["record_hash"]
    return True, None
