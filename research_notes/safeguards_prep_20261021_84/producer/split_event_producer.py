#!/usr/bin/env python3
"""
split_event_producer.py — DETERMINISTIC CORE candidate for a split-event
producer satisfying GATE-E1…E5 (task -84, Part B).

STATUS: isolated candidate module, synthetic inputs only. NOT
integrated, NOT adopted, and NOT connected to any real event source.
The -82 item-2 finding stands: no producer exists in the record and no
qualified event SOURCE exists yet (Twelve Data /splits is Grow+
paid-tier and excluded; any vendor or filing-derived source needs its
own authorization + qualification — see ../SPEC_SPLIT_PRODUCER.md).
This module proves the deterministic core such a producer would run
once a qualified source feeds it.

WHAT IT DOES: given a source batch (synthetic records + a coverage
declaration + an acquisition timestamp + a source pin), a pinned
session calendar, a requested symbol set and bars window, and the E3
mode, produce the split-event list in exactly the record shape the S2
exclusion transform consumes (-59 contract: {symbol,
effective_session, source, provenance, as_of, version} — all fields
required — plus factor and audit extensions), or REFUSE, fail-closed.

FAIL-CLOSED SEMANTICS (ProducerRefusal with a stable code; nothing is
ever guessed):
  E3_MODE_UNSET / E3_MODE_INVALID — the E3 PIT rule is UNFROZEN, so the
    producer refuses to run without an explicit mode. Mode "A"
    (decision-time) and mode "B" (retrospective) are both implemented;
    there is no default.
  PROVENANCE_UNBOUND — a present source batch without an acquisition
    timestamp (GATE-E3: provenance must bind to the receipt).
  AS_OF_AFTER_DATASET_CUTOFF — an event whose announced_at (as_of) is
    after the dataset as_of cutoff (GATE-E3).
  COVERAGE_INCOMPLETE — requested symbols/window exceed the source's
    declared coverage (GATE-E2: a missing event fails silently
    downstream, so coverage must be proven, not assumed).
  CALENDAR_RANGE_INSUFFICIENT — the calendar does not extend at least
    one session beyond the bars span on both sides (GATE-E4), or an
    event's stated date cannot be normalized within the calendar.
  DUPLICATE_OR_CONFLICTING_EVENT — two records for the same
    (symbol, stated effective date), identical or not.
  MISSING_FIELD / INVALID_FACTOR / INVALID_TIMESTAMP — malformed
    records (mirroring the S2 transform's own refusal vocabulary).

STATES: a MISSING source batch is not an error and not an empty list:
produce() returns an envelope with state NO_PRODUCER_OUTPUT and
events=None, so "no producer ran" can never be mistaken downstream
for "the producer ran and there were no splits". A covered source with
zero in-scope events returns state OK with events=[] — visibly
different from NO_PRODUCER_OUTPUT.

CALENDAR EDGES (deterministic, never silent):
  - An event whose stated effective date is NOT a session is
    normalized to the NEXT session and flagged
    EDGE_NONSESSION_STATED_DATE (the stated date is preserved). The
    S2 transform refuses non-session effectives
    (NON_SESSION_EFFECTIVE), so the producer must never emit one.
  - An event effective on an early-close session keeps that session
    and is flagged EDGE_EARLY_CLOSE_SESSION.
  - Inclusion range is [prev_session(first bars session),
    next_session(last bars session)]: an event effective one session
    outside the bars window still moves the window's edge sessions
    under S2's {prev, D, next} rule, so it is in scope (GATE-E4).

PIT (behind the UNFROZEN E3 switch):
  - Mode A: events with announced_at after the decision instant are
    EXCLUDED from the event list and recorded in the envelope's
    excluded ledger with reason PIT_ANNOUNCED_AFTER_DECISION.
  - Mode B: such events are INCLUDED, flagged
    pit_status=ANNOUNCED_AFTER_DECISION, and the envelope basis
    becomes RETROSPECTIVE_NON_TRADABLE (an included-after event can
    never silently look decision-time).

DETERMINISM: events are sorted by (symbol, effective_session);
the envelope carries a SHA-256 over the canonical JSON of the event
list; identical inputs produce byte-identical envelopes.
"""

import hashlib
import json
from datetime import date, datetime

PRODUCER_VERSION = "split-producer-core-candidate-1"
SCHEMA_VERSION = "split-events-v1"

STATE_OK = "OK"
STATE_NO_PRODUCER_OUTPUT = "NO_PRODUCER_OUTPUT"

BASIS_DECISION_TIME = "DECISION_TIME"
BASIS_RETROSPECTIVE = "RETROSPECTIVE_NON_TRADABLE"


class ProducerRefusal(Exception):
    """Fail-closed refusal with a stable machine-readable code."""

    def __init__(self, code, detail):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _parse_date(s, field):
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        raise ProducerRefusal("INVALID_TIMESTAMP", f"{field}={s!r} is not an ISO date")


def _parse_ts(s, field):
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        raise ProducerRefusal("INVALID_TIMESTAMP", f"{field}={s!r} is not an ISO timestamp")
    if dt.tzinfo is None:
        raise ProducerRefusal("INVALID_TIMESTAMP", f"{field}={s!r} lacks a timezone")
    return dt


class Calendar:
    """A pinned session calendar: ordered sessions + early-close set,
    carrying its own provenance (source, version, pin) for GATE-E5."""

    def __init__(self, sessions, early_closes, source, version, pin):
        self.sessions = sorted(_parse_date(s, "session") for s in sessions)
        self.session_set = set(self.sessions)
        self.early_closes = {_parse_date(s, "early_close") for s in early_closes}
        if not self.early_closes <= self.session_set:
            raise ProducerRefusal("INVALID_CALENDAR", "early close not a session")
        self.source = source
        self.version = version
        self.pin = pin

    def is_session(self, d):
        return d in self.session_set

    def next_session(self, d):
        for s in self.sessions:
            if s >= d:
                return s
        return None

    def prev_session_before(self, d):
        prev = None
        for s in self.sessions:
            if s < d:
                prev = s
            else:
                break
        return prev

    def next_session_after(self, d):
        for s in self.sessions:
            if s > d:
                return s
        return None

    def sessions_between(self, a, b):
        return [s for s in self.sessions if a <= s <= b]


REQUIRED_RECORD_FIELDS = ("symbol", "effective_date", "factor_num",
                          "factor_den", "announced_at", "source")


def _validate_record(rec, idx):
    for f in REQUIRED_RECORD_FIELDS:
        if f not in rec or rec[f] in (None, ""):
            raise ProducerRefusal("MISSING_FIELD", f"record {idx}: field {f!r} missing/empty")
    for f in ("factor_num", "factor_den"):
        v = rec[f]
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
            raise ProducerRefusal("INVALID_FACTOR",
                                  f"record {idx}: {f}={v!r} is not a positive integer")


def produce(source_batch, calendar, *, symbols, bars_start, bars_end,
            dataset_as_of, decision_instant, e3_mode):
    """
    Run the producer core. Returns an envelope dict (state OK or
    NO_PRODUCER_OUTPUT) or raises ProducerRefusal. See module docstring.
    """
    # E3 mode gate first: an unfrozen rule is never defaulted.
    if e3_mode is None:
        raise ProducerRefusal("E3_MODE_UNSET",
                              "E3 PIT mode must be set explicitly; the rule is UNFROZEN")
    if e3_mode not in ("A", "B"):
        raise ProducerRefusal("E3_MODE_INVALID", f"e3_mode={e3_mode!r}")

    # Absent source is a STATE, not an empty result.
    if source_batch is None:
        return {
            "state": STATE_NO_PRODUCER_OUTPUT,
            "producer_version": PRODUCER_VERSION,
            "schema_version": SCHEMA_VERSION,
            "e3_mode": e3_mode,
            "events": None,
            "excluded": None,
            "note": "no source batch was supplied; no producer output exists. "
                    "This is NOT evidence that the window contains no splits.",
        }

    # GATE-E3 provenance: a present batch must carry its receipt binding.
    acquired_at = source_batch.get("acquired_at")
    if not acquired_at:
        raise ProducerRefusal("PROVENANCE_UNBOUND",
                              "source batch lacks an acquisition timestamp")
    _parse_ts(acquired_at, "acquired_at")
    source_pin = source_batch.get("source_pin")
    if not source_pin:
        raise ProducerRefusal("PROVENANCE_UNBOUND", "source batch lacks a source pin")
    coverage = source_batch.get("coverage")
    if not coverage:
        raise ProducerRefusal("COVERAGE_INCOMPLETE", "source batch declares no coverage")

    bars_start_d = _parse_date(bars_start, "bars_start")
    bars_end_d = _parse_date(bars_end, "bars_end")
    dataset_as_of_dt = _parse_ts(dataset_as_of, "dataset_as_of")
    decision_dt = _parse_ts(decision_instant, "decision_instant")

    # GATE-E2 coverage: requested symbols x window must be inside the
    # declared coverage, exactly — a missing event fails silently in S2.
    cov_symbols = set(coverage.get("symbols") or [])
    if not set(symbols) <= cov_symbols:
        raise ProducerRefusal(
            "COVERAGE_INCOMPLETE",
            f"requested symbols {sorted(set(symbols) - cov_symbols)} not covered")
    cov_start = _parse_date(coverage.get("window_start"), "coverage.window_start")
    cov_end = _parse_date(coverage.get("window_end"), "coverage.window_end")
    if bars_start_d < cov_start or bars_end_d > cov_end:
        raise ProducerRefusal(
            "COVERAGE_INCOMPLETE",
            f"bars window {bars_start}..{bars_end} exceeds coverage "
            f"{coverage.get('window_start')}..{coverage.get('window_end')}")

    # GATE-E4 calendar range: at least one session beyond the bars
    # span on BOTH sides, derived from the span itself.
    in_window = calendar.sessions_between(bars_start_d, bars_end_d)
    if not in_window:
        raise ProducerRefusal("CALENDAR_RANGE_INSUFFICIENT",
                              "calendar has no session inside the bars window")
    first_sess, last_sess = in_window[0], in_window[-1]
    prev_sess = calendar.prev_session_before(first_sess)
    next_sess = calendar.next_session_after(last_sess)
    if prev_sess is None or next_sess is None:
        raise ProducerRefusal(
            "CALENDAR_RANGE_INSUFFICIENT",
            "calendar must extend >=1 session beyond the bars span on both sides")

    records = source_batch.get("records")
    if records is None:
        raise ProducerRefusal("MISSING_FIELD", "source batch has no 'records' field")

    # Duplicate/conflict gate (identity is irrelevant: any repeat of a
    # (symbol, stated date) pair is ambiguous provenance).
    seen = {}
    for i, rec in enumerate(records):
        _validate_record(rec, i)
        key = (rec["symbol"], rec["effective_date"])
        if key in seen:
            raise ProducerRefusal(
                "DUPLICATE_OR_CONFLICTING_EVENT",
                f"records {seen[key]} and {i} share (symbol, effective_date)={key}")
        seen[key] = i

    events = []
    excluded = []
    for rec in records:
        if rec["symbol"] not in symbols:
            continue  # covered source, out-of-scope symbol: not our window
        stated = _parse_date(rec["effective_date"], "effective_date")
        announced = _parse_ts(rec["announced_at"], "announced_at")
        # GATE-E3: provenance bound to the dataset cutoff.
        if announced > dataset_as_of_dt:
            raise ProducerRefusal(
                "AS_OF_AFTER_DATASET_CUTOFF",
                f"{rec['symbol']} event as_of {rec['announced_at']} is after "
                f"dataset as_of {dataset_as_of}")

        flags = []
        eff = calendar.next_session(stated)
        if eff is None:
            raise ProducerRefusal(
                "CALENDAR_RANGE_INSUFFICIENT",
                f"{rec['symbol']} stated effective {stated} has no session "
                "at or after it in the calendar")
        if eff != stated:
            flags.append("EDGE_NONSESSION_STATED_DATE")
        if eff in calendar.early_closes:
            flags.append("EDGE_EARLY_CLOSE_SESSION")

        # Scope: S2 adjacency means events one session outside the
        # bars window still affect its edge sessions.
        if not (prev_sess <= eff <= next_sess):
            continue

        pit = ("ANNOUNCED_ON_OR_BEFORE_DECISION" if announced <= decision_dt
               else "ANNOUNCED_AFTER_DECISION")
        event = {
            # --- the six fields the S2 transform contract requires ---
            "symbol": rec["symbol"],
            "effective_session": eff.isoformat(),
            "source": rec["source"],
            "provenance": source_pin,
            "as_of": rec["announced_at"],
            "version": SCHEMA_VERSION,
            # --- factor + audit extensions ---
            "effective_date_stated": rec["effective_date"],
            "factor_num": rec["factor_num"],
            "factor_den": rec["factor_den"],
            "announced_at": rec["announced_at"],
            "edge_flags": flags,
            "pit_status": pit,
        }
        if pit == "ANNOUNCED_AFTER_DECISION" and e3_mode == "A":
            excluded.append({**event, "excluded_reason": "PIT_ANNOUNCED_AFTER_DECISION"})
        else:
            events.append(event)

    events.sort(key=lambda e: (e["symbol"], e["effective_session"]))
    excluded.sort(key=lambda e: (e["symbol"], e["effective_session"]))
    basis = BASIS_DECISION_TIME
    if e3_mode == "B" and any(e["pit_status"] == "ANNOUNCED_AFTER_DECISION"
                              for e in events):
        basis = BASIS_RETROSPECTIVE
    canonical = json.dumps(events, sort_keys=True, separators=(",", ":"))
    return {
        "state": STATE_OK,
        "producer_version": PRODUCER_VERSION,
        "schema_version": SCHEMA_VERSION,
        "e3_mode": e3_mode,
        "basis": basis,
        "calendar": {"source": calendar.source, "version": calendar.version,
                     "pin": calendar.pin},
        "coverage": {"symbols": sorted(cov_symbols),
                     "window_start": coverage.get("window_start"),
                     "window_end": coverage.get("window_end")},
        "source_pin": source_pin,
        "acquired_at": acquired_at,
        "inclusion_range": [prev_sess.isoformat(), next_sess.isoformat()],
        "events": events,
        "excluded": excluded,
        "event_count": len(events),
        "events_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
    }
