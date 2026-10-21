#!/usr/bin/env python3
"""Temporal eligibility gate — TD probe candidate (task -65 r1).

Closes the additional -64 adjudication gap: pilot DAY_ORDER /
base_request_id enforce ordering and existence only. This gate proves
ELAPSED TIME for REV7/REV30 legs from the immutable base receipt:

    eligible  <=>  now_utc_ms >= base_receipt_ts_ms + min_elapsed_ms

Fail closed on: missing receipt/snapshot, malformed JSON, missing or
non-integer timestamps, request_ts > receipt_ts, future-dated receipt
(receipt_ts > now), snapshot bytes whose SHA-256/length disagree with
the receipt (mutable or tampered evidence), or receipt params that do
not exactly match the manifest-derived expected params for the base
request.

The immediate day needs no gate entry here: it is allowed only by
explicit invocation (the runner has no default day).

Offline candidate only. No network, no credentials.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

DAY_MS = 86_400_000
REV_MIN_ELAPSED_MS = {"REV7": 7 * DAY_MS, "REV30": 30 * DAY_MS}


class GateRefusal(Exception):
    """Fail-closed refusal with a stable machine-readable tag."""

    def __init__(self, tag: str, detail: str = ""):
        super().__init__(f"{tag}: {detail}" if detail else tag)
        self.tag = tag


def expected_params(manifest_req: dict) -> dict:
    """Rebuild the sanitized params pilot_acquire._build_url emits."""
    return {
        "symbol": manifest_req["symbol"],
        "interval": manifest_req["interval"],
        "start_date": manifest_req["start_date"],
        "end_date": manifest_req["end_date"],
        "timezone": manifest_req["timezone"],
        "outputsize": str(manifest_req["outputsize"]),
        "order": manifest_req["order"],
        "adjust": manifest_req["adjust"],
    }


def load_base_evidence(store_dir: Path, manifest: dict,
                       base_request_id: str) -> tuple[dict, int]:
    """Verify base receipt + snapshot integrity; return (receipt,
    receipt_ts_ms). Raises GateRefusal on any defect."""
    reqs = {r["request_id"]: r for r in manifest["requests"]}
    base_req = reqs.get(base_request_id)
    if base_req is None:
        raise GateRefusal("BASE_NOT_IN_MANIFEST", base_request_id)
    rcpt_path = Path(store_dir) / (base_request_id + ".receipt.json")
    snap_path = Path(store_dir) / base_req["output_name"]
    if not rcpt_path.exists():
        raise GateRefusal("BASE_RECEIPT_MISSING", str(rcpt_path.name))
    if not snap_path.exists():
        raise GateRefusal("BASE_SNAPSHOT_MISSING", str(snap_path.name))
    try:
        receipt = json.loads(rcpt_path.read_text())
    except Exception as e:
        raise GateRefusal("BASE_RECEIPT_MALFORMED", str(e)) from e
    if not isinstance(receipt, dict):
        raise GateRefusal("BASE_RECEIPT_MALFORMED", "not a JSON object")
    if receipt.get("request_id") != base_request_id:
        raise GateRefusal("BASE_RECEIPT_IDENTITY", "request_id mismatch")
    if receipt.get("http_status") != 200:
        raise GateRefusal("BASE_RECEIPT_IDENTITY", "http_status != 200")
    if receipt.get("params") != expected_params(base_req):
        raise GateRefusal("BASE_RECEIPT_PARAMS", "params mismatch")
    body = snap_path.read_bytes()
    if receipt.get("sha256") != hashlib.sha256(body).hexdigest():
        raise GateRefusal("BASE_EVIDENCE_TAMPERED", "sha256 mismatch")
    if receipt.get("bytes") != len(body):
        raise GateRefusal("BASE_EVIDENCE_TAMPERED", "bytes mismatch")
    ts = receipt.get("receipt_ts_ms")
    req_ts = receipt.get("request_ts_ms")
    if not isinstance(ts, int) or isinstance(ts, bool) or ts <= 0:
        raise GateRefusal("BASE_TS_MALFORMED", "receipt_ts_ms")
    if not isinstance(req_ts, int) or isinstance(req_ts, bool) \
            or req_ts > ts:
        raise GateRefusal("BASE_TS_MALFORMED", "request_ts_ms > receipt")
    return receipt, ts


def check_rev_eligibility(store_dir: Path, manifest: dict,
                          rev_request: dict, now_utc_ms: int) -> dict:
    """Return an eligibility proof dict, or raise GateRefusal."""
    leg = rev_request["leg"]
    min_elapsed = REV_MIN_ELAPSED_MS.get(leg)
    if min_elapsed is None:
        raise GateRefusal("NOT_A_REV_LEG", rev_request["request_id"])
    base_id = rev_request.get("base_request_id", "")
    if not base_id:
        raise GateRefusal("BASE_LINK_MISSING", rev_request["request_id"])
    _, base_ts = load_base_evidence(store_dir, manifest, base_id)
    if base_ts > now_utc_ms:
        raise GateRefusal("BASE_TS_FUTURE",
                          f"base {base_ts} > now {now_utc_ms}")
    eligible_at = base_ts + min_elapsed
    if now_utc_ms < eligible_at:
        raise GateRefusal(
            "REV_NOT_YET_ELIGIBLE",
            f"now {now_utc_ms} < eligible_at {eligible_at}")
    return {
        "request_id": rev_request["request_id"],
        "base_request_id": base_id,
        "base_receipt_ts_ms": base_ts,
        "min_elapsed_ms": min_elapsed,
        "eligible_at_ms": eligible_at,
        "now_utc_ms": now_utc_ms,
        "eligible": True,
    }


def check_day_eligibility(store_dir: Path, manifest: dict, day: str,
                          now_utc_ms: int) -> list[dict]:
    """All REV legs of `day` must be eligible. Immediate days (no REV
    legs) return []. Raises GateRefusal on the first defect."""
    proofs = []
    for r in manifest["requests"]:
        if r["day"] == day and r["leg"] in REV_MIN_ELAPSED_MS:
            proofs.append(check_rev_eligibility(
                store_dir, manifest, r, now_utc_ms))
    return proofs
