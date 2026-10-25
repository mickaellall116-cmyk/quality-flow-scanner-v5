"""P8 (30 successor) — As-of signal / EXIT-path research telemetry.

QF-EQUITY43-DEV-MEASUREMENT-FIXES-20261025-30 — successor of the 29r
module of the same name, repaired per ChatGPT's -29r verdict (Slack
TS 1792941227.393299), which held P8 for prospective use on two
blockers plus a restart guard:

  * Calendar horizon. The journal now resolves bins through the
    UNION calendar (session_bins.load_union_table): the adopted
    751-session base table plus the committed, hash-pinned,
    versioned extension through 2027-12-31. The Oct 26-30 pilot week
    and any later forward record inside the declared horizon are
    accepted; dates in neither artifact still fail closed.
  * Rejected-append poisoning. In 29r, append() called _track()
    before committing the line, and _track mutated as it checked:
    a backdated SIGNAL_FIRE advanced _last_signal_idx and inserted
    _fire_bin BEFORE the stream-monotonicity check raised, leaving
    a ghost parent and an advanced index — a refusal that changed
    the journal. Tracking is now transactional: _validate_track()
    runs every link/order check against current state without
    mutating anything; only after validation AND the line commit
    does _apply_track() mutate. A refusal leaves lines, chain head,
    and every tracking dict byte-identical.
  * Restart guard. _ingest_existing() now re-runs validate_record()
    on every loaded line (after the chain/hash checks): a hash-valid
    but semantically invalid line (wrong bin end, retro-stamp,
    unknown field, unfinalized bar) is refused at load instead of
    becoming accepted state.

Everything else is the 29r design, unchanged (the 29r battery is
carried into this package's tests with exactly one fixture moved:
its beyond-table date 2026-11-02 is an extension session now, so the
beyond-horizon refusal is exercised at 2028-01-03 instead).

---

Original 29r documentation follows.

P8 (repaired, 29r) — As-of signal / EXIT-path research telemetry.

QF-EQUITY43-DEV-MEASUREMENT-FIXES-20261025-29r — successor of the -29
module of the same name, repaired per ChatGPT's independent -29
verdict (Slack TS 1792935577.054259): P8 was HELD on the same
session-time causality defect as P1, plus incomplete guards and a
look-ahead schema. The -29 module hard-coded BAR_DURATION_HOURS = 4
and required decision_time = signal_time + 4h — rejecting a valid
13:30->16:00 signal and accepting an invalid 17:30 completion;
BAR_PATH and EXIT_DECISION carried no bin-end or recorded-at guard at
all; and SIGNAL_FIRE / EXIT_DECISION mandated fields that are not yet
known at their event times (the actual next-open entry and the
entry-derived TP1 at fire time; the next-open fill at decision time).

Repairs (this module):
  * All bin completions resolve through the PINNED session table
    (session_bins.py; adopted 751-session table, sha256 00c5555c…):
    bins 09:30->13:30 and 13:30->16:00 ET, early closes via the table.
    decision_time must EQUAL the table bin_end of the record's bin —
    for SIGNAL_FIRE, BAR_PATH, and EXIT_DECISION alike. A bin absent
    from the table (non-session date, non-bin start, early-close
    second bin, beyond-table date) is refused fail-closed.
  * recorded_at >= decision_time is enforced for BAR_PATH and
    EXIT_DECISION as it already was for SIGNAL_FIRE (retro-stamped
    records refused); the new observed records carry the analogous
    recorded_at >= event-time guard.
  * Information is split by availability. SIGNAL_FIRE carries only
    signal-bar-knowable fields: the initial stop threshold is
    signal-derived (signal close - 1.5*ATR) and stays; the actual
    entry and the entry-derived TP1 move to ENTRY_OBSERVED, appended
    once the next bin's open is observable from the feed.
    EXIT_DECISION carries the decision and the decision bar's close;
    the fill moves to EXIT_FILL_OBSERVED, appended once the next
    bin's open is observable. Neither observed record is an execution
    fill: EXECUTION (T6) remains refused in signal-only mode, exactly
    as in -29.
  * Cross-record causality in the journal: ENTRY_OBSERVED requires a
    prior SIGNAL_FIRE for the same (symbol, signal_idx), and its
    entry_time must be the start of the bin immediately following
    the fire's bin (the table's next_bin_start of the signal bin:
    13:30 for a first-bin fire — the same instant as its
    decision_time — and the next session's 09:30 for a second-bin
    fire). EXIT_FILL_OBSERVED likewise requires a prior
    EXIT_DECISION, with fill_time the next bin start after the
    decision bar.

Everything else is the -29 design, unchanged: record types T1–T6 per
the -25 §A6 spec and Mike's full-state journal direction (bridge
9087bf0, 2026-10-24); append-only hash-chained JSONL; strict schemas
(unknown fields refused); per-symbol monotonicity (no backfill);
bar_finalized required on bar-derived records. Prospective only: it
records events as they occur, invents no historical values, and
changes no production, pilot, or S1 component.

Record types
------------
SIGNAL_FIRE (T1 + T2 + signal-time levels)
    Full signal-time state at every candidate fire, taken or not:
    entry-predicate values with thresholds and margins, ADX/DI,
    trendScore, SessionVWAP distance, relative volume, EMA geometry,
    rs with its benchmark as-of stamp, market-gate state, signal
    grade, gate/disposition reasons; admission state (open slots,
    sector occupancy, planned heat before/after, rank margin);
    signal-time price levels (signal close, ATR, initial stop
    threshold). NOT carried (not yet knowable): actual entry, TP1.
ENTRY_OBSERVED (availability split of T2 levels)
    The observed next-bin open (entry price), the ATR in force, and
    the entry-derived TP1, recorded once observable. An observed
    market price, not an execution fill.
BAR_PATH (T4 + T5)
    Per-bar record for an open position: bar OHLC, the geometry
    series in force (entry, initial stop, TP1, runner), threshold
    events (first TP1 touch bar, first stop-threshold breach bar,
    breach count, bars under threshold) and MAE/MFE inputs.
EXIT_DECISION (T3 + T5 final)
    The exit-decision bar's OHLC (including its CLOSE — the field
    whose absence made the DEV overshoot split NOT_RECOVERABLE), the
    threshold values in force on that bar (runner, EMA55), and the
    decision. NOT carried (not yet knowable): the next-open fill.
EXIT_FILL_OBSERVED (availability split of T5 final)
    The observed next-bin open after an exit decision (fill
    reference price), recorded once observable. An observed market
    price, not an execution fill.
EXECUTION (T6)
    Order / acknowledgment / fill price + timestamps per leg. A
    signal-only feed cannot establish fills (-25 §A6), so a journal
    in signal-only mode REFUSES EXECUTION records; they are accepted
    only when the writer is constructed with execution_authorized=
    True (a separately authorized paper-execution lane).
"""
import hashlib
import json
import os
from datetime import datetime

import session_bins


class TelemetryError(ValueError):
    pass


_TABLE = None


def _table():
    global _TABLE
    if _TABLE is None:
        _TABLE = session_bins.load_union_table()
    return _TABLE


def set_session_table(table):
    """Test hook: inject a SessionTable (the pinned one is the only
    table production callers get)."""
    global _TABLE
    _TABLE = table


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
    # signal-time price levels (entry / TP1 are NOT knowable here;
    # they arrive via ENTRY_OBSERVED)
    "signal_close", "atr", "stop_threshold",
    "disposition",
}
ENTRY_OBSERVED_FIELDS = {
    "symbol", "signal_idx", "entry_time", "entry_price", "atr",
    "tp1_level", "recorded_at",
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
    "decision", "exit_reason",
    # fill_time / fill_price are NOT knowable here; they arrive via
    # EXIT_FILL_OBSERVED
}
EXIT_FILL_OBSERVED_FIELDS = {
    "symbol", "signal_idx", "fill_time", "fill_price", "recorded_at",
}
EXECUTION_FIELDS = {
    "symbol", "signal_idx", "leg", "order_time", "ack_time", "fill_time",
    "fill_price", "order_id", "recorded_at",
}
_SCHEMAS = {
    "SIGNAL_FIRE": SIGNAL_FIRE_FIELDS,
    "ENTRY_OBSERVED": ENTRY_OBSERVED_FIELDS,
    "BAR_PATH": BAR_PATH_FIELDS,
    "EXIT_DECISION": EXIT_DECISION_FIELDS,
    "EXIT_FILL_OBSERVED": EXIT_FILL_OBSERVED_FIELDS,
    "EXECUTION": EXECUTION_FIELDS,
}
# The stream-ordering instant each record type contributes to the
# per-symbol append-only monotonicity track.
_STREAM_TIME_FIELD = {
    "SIGNAL_FIRE": "decision_time",
    "ENTRY_OBSERVED": "entry_time",
    "BAR_PATH": "decision_time",
    "EXIT_DECISION": "decision_time",
    "EXIT_FILL_OBSERVED": "fill_time",
}


def _parse_ts(s, rtype, field):
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        raise TelemetryError(f"{rtype}: unparseable timestamp "
                             f"{field}={s!r}")
    if dt.tzinfo is None:
        raise TelemetryError(f"{rtype}: naive timestamp {field}={s!r} "
                             f"refused (tz-aware instants required)")
    return dt


def _bin_end_or_refuse(ts, rtype, field):
    """Pinned-table bin_end for a bin start; any absence is a refusal."""
    try:
        return _table().bin_end(ts)
    except session_bins.SessionTableError as e:
        raise TelemetryError(f"{rtype}: {field} fails pinned "
                             f"session-table bin resolution: {e}")


def _check_bin_decision(body, rtype, start_field):
    """decision_time must equal the pinned bin_end of the record's
    bin, and recorded_at must not precede it. Returns the decision
    instant."""
    start = _parse_ts(body[start_field], rtype, start_field)
    dec = _parse_ts(body["decision_time"], rtype, "decision_time")
    rec = _parse_ts(body["recorded_at"], rtype, "recorded_at")
    end = _bin_end_or_refuse(start, rtype, start_field)
    if dec != end:
        raise TelemetryError(
            f"{rtype}: decision_time {body['decision_time']} != "
            f"pinned session-table bin_end {end.isoformat()} for bin "
            f"starting {body[start_field]} (a decision stamped at any "
            f"other instant is not the bar's completion)")
    if rec < dec:
        raise TelemetryError(
            f"{rtype}: recorded_at precedes decision_time "
            f"(retro-stamped record refused)")
    return dec


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
        _check_bin_decision(body, rtype, "signal_time")
    elif rtype == "BAR_PATH":
        _check_bin_decision(body, rtype, "bar_time")
    elif rtype == "EXIT_DECISION":
        _check_bin_decision(body, rtype, "decision_bar_time")
    elif rtype == "ENTRY_OBSERVED":
        entry = _parse_ts(body["entry_time"], rtype, "entry_time")
        rec = _parse_ts(body["recorded_at"], rtype, "recorded_at")
        _bin_end_or_refuse(entry, rtype, "entry_time")
        if rec < entry:
            raise TelemetryError(
                "ENTRY_OBSERVED: recorded_at precedes entry_time "
                "(the next bin's open cannot be recorded before it "
                "occurs; retro-stamped record refused)")
    elif rtype == "EXIT_FILL_OBSERVED":
        fill = _parse_ts(body["fill_time"], rtype, "fill_time")
        rec = _parse_ts(body["recorded_at"], rtype, "recorded_at")
        _bin_end_or_refuse(fill, rtype, "fill_time")
        if rec < fill:
            raise TelemetryError(
                "EXIT_FILL_OBSERVED: recorded_at precedes fill_time "
                "(retro-stamped record refused)")
    return True


def _canonical(record):
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def record_hash(record):
    body = {k: v for k, v in record.items() if k != "record_hash"}
    return hashlib.sha256(_canonical(body).encode()).hexdigest()


class TelemetryJournal:
    """Append-only, hash-chained telemetry writer (in-memory line list
    or a file path). Prospective: enforces per-symbol monotonicity and
    the cross-record availability links, so historical backfill and
    out-of-order observation records are refused."""

    def __init__(self, path=None, execution_authorized=False):
        self.path = path
        self.execution_authorized = execution_authorized
        self.lines = []
        self._last_hash = "GENESIS"
        self._last_signal_idx = {}
        self._last_stream_time = {}
        self._fire_bin = {}
        self._exit_bin = {}
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
        # Restart guard (-29r verdict): hashes prove the bytes are
        # the bytes that were written; they do NOT prove the record
        # is semantically valid. Re-run full record validation and
        # the link/order checks before the line becomes state.
        validate_record(record,
                        execution_authorized=self.execution_authorized)
        self._validate_track(record)
        self.lines.append(json.dumps(record))
        self._last_hash = record["record_hash"]
        self._apply_track(record)

    def _validate_track(self, record):
        """Every cross-record link / ordering check _track performed
        in 29r, computed against current state WITHOUT mutating
        anything. Raises TelemetryError on the first violation."""
        rtype = record["record_type"]
        sym = record["symbol"]
        if rtype == "SIGNAL_FIRE":
            if record["signal_idx"] <= self._last_signal_idx.get(sym, -1):
                raise TelemetryError(
                    f"SIGNAL_FIRE: signal_idx not strictly increasing "
                    f"for {sym} (backfill or duplicate refused)")
        elif rtype == "ENTRY_OBSERVED":
            key = (sym, record["signal_idx"])
            fire_bin = self._fire_bin.get(key)
            if fire_bin is None:
                raise TelemetryError(
                    f"ENTRY_OBSERVED: no prior SIGNAL_FIRE for {key} "
                    f"(an entry cannot be observed for a fire that "
                    f"was never recorded)")
            entry = _parse_ts(record["entry_time"], rtype, "entry_time")
            expected = _table().next_bin_start(fire_bin)
            if entry != expected:
                raise TelemetryError(
                    f"ENTRY_OBSERVED: entry_time {record['entry_time']} "
                    f"!= the next bin start {expected.isoformat()} "
                    f"after the fire's bin (the observed entry is the "
                    f"open of the bin following the signal bin)")
        elif rtype == "EXIT_FILL_OBSERVED":
            key = (sym, record["signal_idx"])
            exit_bin = self._exit_bin.get(key)
            if exit_bin is None:
                raise TelemetryError(
                    f"EXIT_FILL_OBSERVED: no prior EXIT_DECISION for "
                    f"{key} (a fill cannot be observed for a decision "
                    f"that was never recorded)")
            fill = _parse_ts(record["fill_time"], rtype, "fill_time")
            expected = _table().next_bin_start(exit_bin)
            if fill != expected:
                raise TelemetryError(
                    f"EXIT_FILL_OBSERVED: fill_time "
                    f"{record['fill_time']} != the next bin start "
                    f"{expected.isoformat()} after the decision bar "
                    f"(the observed fill is the open of the bin "
                    f"following the decision bar)")
        field = _STREAM_TIME_FIELD.get(rtype)
        if field is not None:
            t = _parse_ts(record[field], rtype, field)
            last = self._last_stream_time.get(sym)
            if last is not None and t < last:
                raise TelemetryError(
                    f"{rtype}: {field} earlier than the stream's last "
                    f"appended stream time for {sym} (backfill "
                    f"refused)")

    def _apply_track(self, record):
        """The mutations _track performed in 29r, and nothing else.
        Runs only after _validate_track has passed and the line is
        committed, so it cannot fail on a record that validated."""
        rtype = record["record_type"]
        sym = record["symbol"]
        if rtype == "SIGNAL_FIRE":
            self._last_signal_idx[sym] = record["signal_idx"]
            self._fire_bin[(sym, record["signal_idx"])] = \
                _parse_ts(record["signal_time"], rtype, "signal_time")
        elif rtype == "EXIT_DECISION":
            self._exit_bin[(sym, record["signal_idx"])] = \
                _parse_ts(record["decision_bar_time"], rtype,
                          "decision_bar_time")
        field = _STREAM_TIME_FIELD.get(rtype)
        if field is not None:
            self._last_stream_time[sym] = \
                _parse_ts(record[field], rtype, field)

    def append(self, record):
        """Transactional: validate the record, validate every
        link/order against current state, commit the line (file
        first, so an IO failure mutates nothing), and only then
        apply the tracking mutations. Any refusal leaves lines, the
        chain head, and all tracking state byte-identical."""
        record = dict(record)
        validate_record(record,
                        execution_authorized=self.execution_authorized)
        self._validate_track(record)
        record["prev_hash"] = self._last_hash
        record["record_hash"] = record_hash(record)
        line = _canonical(record)
        if self.path:
            with open(self.path, "a") as f:
                f.write(line + "\n")
        self.lines.append(line)
        self._last_hash = record["record_hash"]
        self._apply_track(record)
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
