"""REQ-S2 split-exclusion transform — offline candidate v1.

Separately versioned; NOT integrated into any live or candidate chain.
Pure deterministic transform at the 4H dataset-assembly boundary:
constructed bars + candidate entries in, post-exclusion bars + entries
out. Downstream indicators/folds must recompute from the output.

Rule: for each split event with XNYS effective session D, exclude that
symbol's bars and candidate entries for sessions {prev(D), D, next(D)}
using XNYS session adjacency (pandas_market_calendars NYSE), never
civil-day arithmetic. Union overlapping windows. No imputation, no
replacement, no fill, no synthetic bars. Inputs are never mutated.
Fails closed on any contract violation (see CONTRACT.md).
"""

import copy

import pandas as pd
import pandas_market_calendars as mcal

MODULE_VERSION = "s2_split_exclusion_v1"
_NY = "America/New_York"
_EVENT_FIELDS = ("symbol", "effective_session", "source", "provenance",
                 "as_of", "version")


class S2Refusal(Exception):
    def __init__(self, code, detail):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def xnys_sessions(start, end):
    """Ordered list of XNYS session dates (datetime.date) in [start, end]."""
    cal = mcal.get_calendar("NYSE")
    sched = cal.schedule(start_date=start, end_date=end)
    return [ts.date() for ts in sched.index]


def _parse_date(value, field):
    try:
        return pd.Timestamp(value).date()
    except Exception:
        raise S2Refusal("BAD_DATE", f"{field}={value!r} is not a date")


def _check_record_session(rec, kind, sessions_set):
    """Return the record's session date, failing closed on any ambiguity."""
    label = rec.get("session")
    if not label:
        raise S2Refusal("MISSING_FIELD", f"{kind} missing session: {rec!r}")
    ts_raw = rec.get("bar_start") if kind == "bar" else rec.get("entry_time")
    if not ts_raw:
        raise S2Refusal("MISSING_FIELD", f"{kind} missing timestamp: {rec!r}")
    ts = pd.Timestamp(ts_raw)
    if ts.tzinfo is None:
        raise S2Refusal("TZ_NAIVE", f"{kind} timestamp has no offset: {ts_raw!r}")
    ny_date = ts.tz_convert(_NY).date()
    label_date = _parse_date(label, f"{kind}.session")
    if ny_date != label_date:
        raise S2Refusal(
            "SESSION_LABEL_MISMATCH",
            f"{kind} label {label_date} != NY date {ny_date} of {ts_raw!r}")
    if label_date not in sessions_set:
        raise S2Refusal(
            "SESSION_LABEL_MISMATCH",
            f"{kind} session {label_date} is not an XNYS session")
    return label_date


def _validate_events(split_events, sessions_set):
    """Deduplicate identical events; refuse missing/conflicting ones."""
    seen = {}
    for ev in split_events:
        for f in _EVENT_FIELDS:
            if f not in ev:
                raise S2Refusal("MISSING_FIELD", f"split event missing {f}: {ev!r}")
            if ev[f] is None or (isinstance(ev[f], str) and not ev[f].strip()):
                raise S2Refusal("EMPTY_FIELD", f"split event empty {f}: {ev!r}")
        d = _parse_date(ev["effective_session"], "effective_session")
        if d not in sessions_set:
            raise S2Refusal(
                "NON_SESSION_EFFECTIVE",
                f"effective_session {d} is not an XNYS session")
        key = (ev["symbol"], d.isoformat())
        canon = tuple(str(ev[f]) for f in _EVENT_FIELDS)
        if key in seen and seen[key] != canon:
            raise S2Refusal(
                "DUPLICATE_CONFLICTING_EVENT",
                f"conflicting events for {key}")
        seen[key] = canon
    return seen


def apply_split_exclusion(bars, entries, split_events, acquisition_receipt,
                          calendar_start, calendar_end):
    """Apply REQ-S2. Returns a new result dict; inputs are not mutated."""
    sessions = xnys_sessions(calendar_start, calendar_end)
    sessions_set = set(sessions)
    index_of = {d: i for i, d in enumerate(sessions)}

    events = _validate_events(split_events, sessions_set)

    # Excluded sessions per symbol, with causing event keys.
    excluded = {}  # symbol -> {session_date: [event_key,...]}
    for (symbol, d_iso), _canon in sorted(events.items()):
        d = _parse_date(d_iso, "effective_session")
        i = index_of[d]
        if i == 0 or i == len(sessions) - 1:
            raise S2Refusal(
                "WINDOW_EDGE",
                f"effective_session {d} lacks a prev/next session in range")
        for s in (sessions[i - 1], d, sessions[i + 1]):
            excluded.setdefault(symbol, {}).setdefault(s, [])
            if (symbol, d_iso) not in excluded[symbol][s]:
                excluded[symbol][s].append((symbol, d_iso))

    def _partition(records, kind, id_field):
        kept, removed_ids = [], []
        seen_ids = set()
        for rec in records:
            rid = rec.get(id_field)
            if not rid:
                raise S2Refusal("MISSING_FIELD", f"{kind} missing {id_field}")
            if rid in seen_ids:
                raise S2Refusal("SESSION_LABEL_MISMATCH",
                                f"duplicate {kind} id {rid}")
            seen_ids.add(rid)
            sess = _check_record_session(rec, kind, sessions_set)
            sym = rec.get("symbol")
            if not sym:
                raise S2Refusal("MISSING_FIELD", f"{kind} missing symbol")
            if sess in excluded.get(sym, {}):
                removed_ids.append(rid)
            else:
                kept.append(copy.deepcopy(rec))
        return kept, sorted(removed_ids)

    bars_out, removed_bar_ids = _partition(bars, "bar", "bar_id")
    entries_out, removed_entry_ids = _partition(entries, "entry", "entry_id")

    removed_ledger = [
        {"symbol": sym, "session": s.isoformat(),
         "caused_by": [list(k) for k in sorted(causes)]}
        for sym in sorted(excluded)
        for s, causes in sorted(excluded[sym].items())
    ]

    def _counts(records):
        out = {}
        for r in records:
            out[r["symbol"]] = out.get(r["symbol"], 0) + 1
        return out

    return {
        "module": MODULE_VERSION,
        "bars_out": bars_out,
        "entries_out": entries_out,
        "removed_bar_ids": removed_bar_ids,
        "removed_entry_ids": removed_entry_ids,
        "removed_sessions_ledger": removed_ledger,
        "counts": {
            "bars_before": _counts(bars), "bars_after": _counts(bars_out),
            "entries_before": _counts(entries),
            "entries_after": _counts(entries_out),
        },
        # Carried through untouched: exclusion never rewrites acquisition
        # completeness (an INCOMPLETE receipt stays INCOMPLETE).
        "acquisition_receipt": copy.deepcopy(acquisition_receipt),
    }
