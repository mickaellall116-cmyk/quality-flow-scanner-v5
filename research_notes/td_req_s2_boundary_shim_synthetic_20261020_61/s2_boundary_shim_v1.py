"""REQ-S2 boundary shim — offline candidate v1 (task -61, synthetic only).

Separately versioned NEW file. NOT integrated into any live or
candidate chain; never edits frozen candidate code. Implements the -60
CONTRACT_MEMO sec.4 cutpoint:

  constructor-output rows -> deterministic adapter -> boundary gates
  (E2 completeness / E3 PIT / E4 edge / unmatched-symbol) ->
  -59 S2 transform with entries=[] -> entries recomputed downstream
  from filtered bars (stub) ; fold boundaries materialized on the
  PRE-exclusion schedule, membership intersected after exclusion.

Calendar adjacency binds ONLY to the pinned schedule artifact
XNYS_SESSION_SCHEDULE_V2 (sha256-pinned below). The -59 transform's
runtime-PMC session function is replaced by an artifact-bound one and
its mcal handle is poisoned: any PMC consultation fails closed.
"""

import copy
import hashlib
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

MODULE_VERSION = "s2_boundary_shim_v1"
_NY = ZoneInfo("America/New_York")
_PKG = Path(__file__).resolve().parent
_TRANSFORM_PATH = (_PKG.parent / "td_req_s2_split_exclusion_20261020_59"
                   / "s2_split_exclusion_v1.py")
SCHEDULE_SHA256_PIN = ("3358f2d9cc233142f0927d3a16c3a353e935ed4310"
                       "0c563ac046352dcf75d2b88")
TRANSFORM_SHA256_PIN = ("7791ca91eb18e63f11d35514926ed40a885e5a1d9e"
                        "e2079121c612b7993c956b")


class ShimRefusal(Exception):
    def __init__(self, code, detail):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class _NoPMC:
    def get_calendar(self, *a, **k):
        raise ShimRefusal("PMC_FORBIDDEN",
                          "runtime PMC consultation is forbidden in -61")


# ------------------------------------------------------------ schedule
def load_schedule(path, expected_sha256=SCHEDULE_SHA256_PIN):
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise ShimRefusal("SCHEDULE_PIN_MISMATCH",
                          f"{path} sha256 {digest} != pin")
    doc = json.loads(raw)
    sessions = [s["date"] for s in doc["sessions"]]
    close_of = {s["date"]: s["close"] for s in doc["sessions"]}
    if sessions != sorted(sessions) or len(set(sessions)) != len(sessions):
        raise ShimRefusal("SCHEDULE_MALFORMED", "sessions not sorted/unique")
    return {"sha256": digest, "sessions": sessions, "close_of": close_of,
            "coverage": (doc["coverage_start"], doc["coverage_end"])}


def _prev_next(schedule, date_iso):
    ss = schedule["sessions"]
    i = ss.index(date_iso)
    prev_s = ss[i - 1] if i > 0 else None
    next_s = ss[i + 1] if i < len(ss) - 1 else None
    return prev_s, next_s


def artifact_session_fn(schedule):
    ss = schedule["sessions"]

    def _sessions(start, end):
        s = start.isoformat() if hasattr(start, "isoformat") else str(start)
        e = end.isoformat() if hasattr(end, "isoformat") else str(end)
        s, e = s[:10], e[:10]
        from datetime import date
        return [date.fromisoformat(d) for d in ss if s <= d <= e]

    return _sessions


def load_transform(schedule):
    """Load the -59 transform by path; bind its sessions to the artifact."""
    digest = hashlib.sha256(_TRANSFORM_PATH.read_bytes()).hexdigest()
    if digest != TRANSFORM_SHA256_PIN:
        raise ShimRefusal("TRANSFORM_PIN_MISMATCH",
                          f"transform sha256 {digest} != pin")
    spec = importlib.util.spec_from_file_location("s2_transform_v1",
                                                  _TRANSFORM_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.xnys_sessions = artifact_session_fn(schedule)
    mod.mcal = _NoPMC()  # poison: any PMC use after binding fails closed
    return mod


# ------------------------------------------------------------- adapter
def adapt_constructor_rows(rows):
    """Constructor-output rows -> transform bar records (strict)."""
    out = []
    last_start = {}
    for row in rows:
        sym = row.get("symbol")
        raw = row.get("bar_start")
        tag = row.get("session")
        if not sym or not raw or not tag:
            raise ShimRefusal("ADAPTER_MISSING_FIELD", f"row: {row!r}")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            raise ShimRefusal("TZ_NAIVE", f"bar_start has no offset: {raw!r}")
        ny_date = dt.astimezone(_NY).date().isoformat()
        # The constructor's own session tag must agree with the timestamp:
        # a swapped/misaligned row (values vs timestamps) breaks this.
        if ny_date != tag:
            raise ShimRefusal(
                "ADAPTER_INDEX_ALIGNMENT",
                f"{sym} bar_start {raw} -> NY date {ny_date} != tag {tag}")
        if dt.astimezone(_NY).strftime("%H:%M") not in ("09:30", "13:30"):
            raise ShimRefusal("BAR_ANCHOR", f"bar_start not a 4H anchor: {raw}")
        prev = last_start.get(sym)
        if prev is not None and raw <= prev:
            raise ShimRefusal(
                "ADAPTER_INDEX_ALIGNMENT",
                f"{sym} bar_start not strictly increasing: {prev} -> {raw}")
        last_start[sym] = raw
        out.append({
            "bar_id": f"{sym}|{raw}",
            "symbol": sym,
            "session": tag,
            "bar_start": raw,
            "open": float(row["open"]), "high": float(row["high"]),
            "low": float(row["low"]), "close": float(row["close"]),
            "volume": float(row["volume"]),
        })
    return out


# -------------------------------------------------------- boundary asm
def assemble(bars, split_events, ledger_coverage, receipt, dataset_cutoff,
             schedule, transform):
    """Boundary gates (fail closed), then the -59 transform, entries=[]."""
    cutoff = datetime.fromisoformat(dataset_cutoff)
    if cutoff.tzinfo is None:
        raise ShimRefusal("TZ_NAIVE", "dataset_cutoff has no offset")
    sessions_set = set(schedule["sessions"])

    # E3 PIT gate: every event's as_of must be known by the cutoff.
    for ev in split_events:
        as_of = datetime.fromisoformat(ev["as_of"])
        if as_of.tzinfo is None:
            raise ShimRefusal("TZ_NAIVE", f"event as_of naive: {ev!r}")
        if as_of > cutoff:
            raise ShimRefusal(
                "PIT_LATE",
                f"event as_of {ev['as_of']} after cutoff {dataset_cutoff}")

    # E2 completeness gates: receipt + ledger coverage declarations.
    if receipt.get("status") != "COMPLETE":
        raise ShimRefusal(
            "ACQUISITION_INCOMPLETE",
            f"receipt status {receipt.get('status')!r} != COMPLETE")
    bar_symbols = {b["symbol"] for b in bars}
    for sym in sorted(bar_symbols):
        if sym not in ledger_coverage:
            raise ShimRefusal("LEDGER_COVERAGE_MISSING",
                              f"no ledger coverage declaration for {sym}")
    for ev in split_events:
        if ev["symbol"] not in ledger_coverage:
            raise ShimRefusal("LEDGER_COVERAGE_MISSING",
                              f"event symbol {ev['symbol']} not in ledger")

    # Unmatched-event gate: an event for a symbol with no bars must
    # refuse, never silently no-op (alias-mismatch risk, CP1 finding 3).
    for ev in split_events:
        if ev["symbol"] not in bar_symbols:
            raise ShimRefusal(
                "UNMATCHED_EVENT_SYMBOL",
                f"event for {ev['symbol']} but no bars for that symbol")

    # E4 edge gates (per symbol, against that symbol's observed span).
    span = {}
    for b in bars:
        span.setdefault(b["symbol"], set()).add(b["session"])
    span = {s: sorted(v) for s, v in span.items()}
    for ev in split_events:
        sym, d = ev["symbol"], ev["effective_session"]
        if d not in sessions_set:
            raise ShimRefusal("NON_SESSION_EFFECTIVE",
                              f"{d} is not an artifact session")
        sym_span = span[sym]
        if d not in sym_span:
            raise ShimRefusal(
                "EDGE_EVENT_OUT_OF_SPAN",
                f"{sym} event D={d} outside observed span "
                f"{sym_span[0]}..{sym_span[-1]}; window would touch "
                "unobserved sessions (GATE-E4)")
        if d == sym_span[0] or d == sym_span[-1]:
            raise ShimRefusal(
                "EDGE_EVENT_AT_SPAN_EDGE",
                f"{sym} event D={d} at observed-span edge; window "
                "extends into unobserved sessions (GATE-E4)")

    # Calendar range for the transform: artifact sessions extended one
    # session beyond the global span on both sides (inventory u span).
    all_sessions = sorted({b["session"] for b in bars})
    lo, _ = _prev_next(schedule, all_sessions[0])
    _, hi = _prev_next(schedule, all_sessions[-1])
    if lo is None or hi is None:
        raise ShimRefusal("WINDOW_EDGE", "span at artifact coverage edge")
    result = transform.apply_split_exclusion(
        bars, [], split_events, receipt, lo, hi)
    return result


# ------------------------------------------------- downstream consumers
def recompute_entries_stub(bars_out):
    """Pinned-logic stand-in: signal = 09:30 bar with close > open;
    fill = next surviving bar of the same symbol. Proves wiring only;
    entries reference surviving bars by construction (no orphans)."""
    by_sym = {}
    for b in bars_out:
        by_sym.setdefault(b["symbol"], []).append(b)
    entries = []
    for sym in sorted(by_sym):
        rows = sorted(by_sym[sym], key=lambda r: r["bar_start"])
        for i, b in enumerate(rows):
            if b["bar_start"][11:16] == "09:30" and b["close"] > b["open"]:
                if i + 1 < len(rows):
                    fill = rows[i + 1]
                    entries.append({
                        "entry_id": f"{sym}|entry|{b['bar_id']}",
                        "symbol": sym,
                        "signal_bar_id": b["bar_id"],
                        "fill_bar_id": fill["bar_id"],
                        "entry_time": fill["bar_start"],
                        "session": fill["session"],
                    })
    return entries


def materialize_folds(session_dates, block=3):
    """Fold boundaries from the given (pre-exclusion) session list."""
    folds = []
    for k in range(0, len(session_dates), block):
        members = session_dates[k:k + block]
        folds.append({"fold": k // block, "start": members[0],
                      "end": members[-1], "members": members})
    return folds
