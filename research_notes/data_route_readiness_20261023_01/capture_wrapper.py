"""Offline fixture capture wrapper — QF-DATA-ROUTE-READINESS-20261023-01.

Candidate, NOT adopted, executes nothing against any vendor. The wrapper
takes a transport callable so the dry run can inject (a) a disabled
transport, proving fail-closed behavior with the network off, and (b)
synthetic payload fixtures, proving schema/timezone/duplicate/gap
validation and hash-chained receipt emission.

Rules enforced (from capture_manifest.json policies):
- a refused leg emits NO receipt (absence is the failure signal);
- duplicate detection compares UTC instants, never wall-clock
  (the -94 lesson: equal instants in the repeated fall hour must not
  compare unequal, and distinct instants must not collapse);
- a response at exactly outputsize rows is a truncation suspect;
- non-finite or negative-volume values are refused.
"""
import hashlib
import json
import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
OUTPUTSIZE = 5000


class NetworkDisabledError(Exception):
    pass


class CaptureRefused(Exception):
    def __init__(self, reason, detail):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _parse_stamp(s):
    # Vendor stamps: ISO bar-open in America/New_York (offset-bearing).
    try:
        dt = datetime.fromisoformat(s)
    except (ValueError, TypeError):
        raise CaptureRefused("SCHEMA_VIOLATION", f"unparseable datetime {s!r}")
    if dt.tzinfo is None:
        raise CaptureRefused("TIMEZONE_VIOLATION", f"naive datetime {s!r}")
    # The stamp's offset must equal the true ET offset at that instant.
    as_et = dt.astimezone(ET)
    if dt.utcoffset() != as_et.utcoffset() or dt.astimezone(timezone.utc) != as_et.astimezone(timezone.utc):
        raise CaptureRefused("TIMEZONE_VIOLATION", f"offset inconsistent with America/New_York at {s!r}")
    return dt.astimezone(timezone.utc)


def validate_payload(payload, leg):
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        raise CaptureRefused("SCHEMA_VIOLATION", "status != ok")
    meta = payload.get("meta") or {}
    if meta.get("symbol") != leg["symbol"] or meta.get("interval") != "1h":
        raise CaptureRefused("SCHEMA_VIOLATION", "meta symbol/interval mismatch")
    values = payload.get("values")
    if not isinstance(values, list) or not values:
        raise CaptureRefused("SCHEMA_VIOLATION", "values missing/empty")
    if len(values) >= OUTPUTSIZE:
        raise CaptureRefused("TRUNCATION_SUSPECT", f"{len(values)} rows >= outputsize {OUTPUTSIZE}")
    instants = []
    for row in values:
        for col in ("open", "high", "low", "close", "volume"):
            try:
                x = float(row[col])
            except (KeyError, TypeError, ValueError):
                raise CaptureRefused("SCHEMA_VIOLATION", f"bad {col} in row {row!r}")
            if not math.isfinite(x):
                raise CaptureRefused("NONFINITE_VALUE", f"non-finite {col}")
            if col == "volume" and x < 0:
                raise CaptureRefused("NONFINITE_VALUE", "negative volume")
        instants.append(_parse_stamp(row["datetime"]))
    if len(set(instants)) != len(instants):
        raise CaptureRefused("DUPLICATE_INSTANT", "duplicate UTC instant in leg")
    if instants != sorted(instants):
        raise CaptureRefused("SCHEMA_VIOLATION", "bars not in ascending order")
    # Continuity: consecutive bars may not skip more than the leg's
    # class allows (equity fixture legs: 1h within the synthetic span;
    # the real completeness adjudication is the checker's session-table
    # job at qualification, not the wrapper's).
    max_gap = leg.get("max_gap_seconds", 3600)
    for a, b in zip(instants, instants[1:]):
        if (b - a).total_seconds() > max_gap:
            raise CaptureRefused("GAP_VIOLATION", f"gap {(b - a).total_seconds():.0f}s after {a.isoformat()}")
    return instants


def run_leg(transport, leg, manifest_root, prev_hash):
    """Execute one leg through the injected transport. Returns a receipt
    dict on success; raises CaptureRefused (no receipt emitted) otherwise."""
    try:
        payload = transport(leg)
    except NetworkDisabledError:
        raise CaptureRefused("NETWORK_DISABLED", "transport reports network disabled")
    instants = validate_payload(payload, leg)
    body_bytes = _canon(payload)
    receipt = {
        "kind": "capture_receipt",
        "manifest_root_digest_sha256": manifest_root,
        "leg_id": leg["leg_id"],
        "symbol": leg["symbol"],
        "window": leg["window"],
        "request": {"endpoint_class": "/time_series", "interval": "1h",
                    "adjust": "splits", "outputsize": OUTPUTSIZE,
                    "start_date": leg["start_date"], "end_date": leg["end_date"],
                    "attempt": leg.get("attempt", 1)},
        "provider": {"name": "Twelve Data", "request_id": None,
                     "response_timestamp_utc": "FIXTURE"},
        "response": {"sha256": hashlib.sha256(body_bytes).hexdigest(),
                     "rows": len(instants),
                     "first_bar": instants[0].isoformat(),
                     "last_bar": instants[-1].isoformat(),
                     "expected_rows": leg.get("expected_rows"),
                     "row_delta": (len(instants) - leg["expected_rows"]) if leg.get("expected_rows") else None},
        "chain": {"prev_receipt_hash": prev_hash},
        "credits": {"api_usage_before": None, "leg_credits": 1},
    }
    receipt["chain"]["receipt_hash"] = hashlib.sha256(_canon(receipt)).hexdigest()
    return receipt


def disabled_transport(leg):
    raise NetworkDisabledError("network disabled for dry run")
