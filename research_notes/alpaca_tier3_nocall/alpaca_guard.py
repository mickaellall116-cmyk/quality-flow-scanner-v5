#!/usr/bin/env python3
"""Offline, fail-closed preflight and payload validator for the Tier-3 Alpaca route.

This module performs no network calls. A future capture wrapper may inject a network
call only after preflight returns successfully. The committed manifest intentionally
has RIGHTS_GATE=HOLD, so the current package cannot reach credential or network code.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo


class GuardStop(RuntimeError):
    """A fail-closed stop with a stable machine-readable reason."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_manifest(path: Path, expected_sha256: str) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    actual = sha256_bytes(canonical_bytes(manifest))
    if actual != expected_sha256:
        raise GuardStop("MANIFEST_HASH_MISMATCH")
    return manifest


def preflight(
    manifest: Mapping[str, Any],
    env: Mapping[str, str],
    network_call: Callable[[], Any],
) -> dict[str, str]:
    """Stop before credentials/network unless all immutable gates are affirmative."""
    route = manifest["route"]
    if route.get("rights_gate") != "GO":
        raise GuardStop("RIGHTS_GATE_NOT_GO")
    rights_hash = route.get("adjudication_record_sha256")
    if not isinstance(rights_hash, str) or len(rights_hash) != 64:
        raise GuardStop("RIGHTS_RECORD_HASH_MISSING")
    if manifest.get("network_enabled") is not True:
        raise GuardStop("NETWORK_NOT_EXPLICITLY_ENABLED")

    # Credential lookup is deliberately below every policy/authority gate.
    key_name = manifest["credentials"]["key_id_env"]
    secret_name = manifest["credentials"]["secret_key_env"]
    if not env.get(key_name) or not env.get(secret_name):
        raise GuardStop("CREDENTIAL_MISSING")

    network_call()
    return {"rights_record_sha256": rights_hash}


def _parse_timestamp(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise GuardStop("TIMESTAMP_NOT_TIMEZONE_AWARE")
    return parsed


def validate_payload(
    payload: Mapping[str, Any],
    *,
    symbol: str,
    expected_sessions: Mapping[str, str],
    request_feed: str = "sip",
    request_timeframe: str = "30Min",
) -> dict[str, Any]:
    """Validate a decoded response without emitting prices or raw bars."""
    if not isinstance(payload, Mapping):
        raise GuardStop("HTTP_OR_NON_JSON_ERROR")
    if payload.get("symbol") != symbol:
        raise GuardStop("SYMBOL_MISMATCH")
    # Alpaca's response schema does not echo feed/timeframe; validate the pinned
    # request metadata supplied by the capture wrapper instead of inventing fields.
    if request_feed != "sip" or request_timeframe != "30Min":
        raise GuardStop("FEED_OR_TIMEFRAME_MISMATCH")
    if payload.get("next_page_token") is not None:
        raise GuardStop("UNEXPECTED_PAGE_TOKEN")
    bars = payload.get("bars")
    if not isinstance(bars, list):
        raise GuardStop("HTTP_OR_NON_JSON_ERROR")

    market_tz = ZoneInfo("America/New_York")
    expected_times: set[dt.datetime] = set()
    derived_row_count = 0
    for day, close_time in expected_sessions.items():
        session_day = dt.date.fromisoformat(day)
        close_hour, close_minute = (int(part) for part in close_time.split(":"))
        close_minutes = close_hour * 60 + close_minute
        if close_minutes <= 9 * 60 + 30 or (close_minutes - (9 * 60 + 30)) % 30:
            raise GuardStop("INVALID_SESSION_SCHEDULE")
        session_bucket_count = (close_minutes - (9 * 60 + 30)) // 30
        derived_row_count += (session_bucket_count + 1) // 2
        for minutes in range(9 * 60 + 30, close_minutes, 30):
            hour, minute = divmod(minutes, 60)
            local_stamp = dt.datetime.combine(
                session_day, dt.time(hour, minute), tzinfo=market_tz
            )
            expected_times.add(local_stamp.astimezone(dt.timezone.utc))

    seen: set[dt.datetime] = set()
    nonfinite_count = 0
    for bar in bars:
        if not isinstance(bar, Mapping):
            raise GuardStop("HTTP_OR_NON_JSON_ERROR")
        stamp = bar.get("t")
        if not isinstance(stamp, str):
            raise GuardStop("TIMESTAMP_MISSING")
        parsed_stamp = _parse_timestamp(stamp)
        if parsed_stamp.second or parsed_stamp.microsecond:
            raise GuardStop("OFF_GRID_BAR")
        utc_stamp = parsed_stamp.astimezone(dt.timezone.utc)
        if utc_stamp in seen:
            raise GuardStop("DUPLICATE_BAR")
        seen.add(utc_stamp)
        if utc_stamp not in expected_times:
            raise GuardStop("OFF_GRID_BAR")
        for field in ("o", "h", "l", "c", "v"):
            value = bar.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                nonfinite_count += 1
    if nonfinite_count:
        raise GuardStop("NONFINITE_VALUE")
    missing = expected_times - seen
    if missing:
        raise GuardStop("MISSING_BUCKET")

    return {
        "symbol": symbol,
        "raw_row_count": len(bars),
        "derived_row_count": derived_row_count,
        "session_count": len(expected_sessions),
        "duplicate_count": 0,
        "off_grid_count": 0,
        "missing_bucket_count": 0,
        "nonfinite_count": 0,
        "next_page_token_present": False,
    }


def validate_receipt(receipt: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
    allowed = set(manifest["receipt"]["public_fields"])
    forbidden = {x.lower() for x in manifest["receipt"]["forbidden_public_fields"]}
    keys = {str(k) for k in receipt}
    if not keys <= allowed:
        raise GuardStop("RECEIPT_FIELD_NOT_ALLOWLISTED")
    if {k.lower() for k in keys} & forbidden:
        raise GuardStop("RECEIPT_CONTAINS_FORBIDDEN_FIELD")


def hold_receipt(manifest: Mapping[str, Any], manifest_sha256: str) -> dict[str, Any]:
    return {
        "manifest_sha256": manifest_sha256,
        "rights_record_sha256": manifest["route"].get("adjudication_record_sha256"),
        "symbol": manifest["smoke_request"]["symbol"],
        "calls_used": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    manifest = load_manifest(args.manifest, args.expected_manifest_sha256)
    try:
        preflight(manifest, os.environ, lambda: (_ for _ in ()).throw(AssertionError("network disabled")))
    except GuardStop as exc:
        receipt = hold_receipt(manifest, args.expected_manifest_sha256)
        validate_receipt(receipt, manifest)
        print(json.dumps({"status": "STOP", "reason": str(exc), "receipt": receipt}, sort_keys=True))
        return 3
    raise GuardStop("UNREACHABLE_WITH_CURRENT_HOLD_MANIFEST")


if __name__ == "__main__":
    raise SystemExit(main())
