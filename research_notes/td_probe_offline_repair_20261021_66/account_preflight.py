#!/usr/bin/env python3
"""Account-preflight adapter — TD probe candidate (task -66 r1,
successor of -65).

Performance-blind injectable interface for ONE /api_usage check per
execution day (closes -64 gap G4 for the probe candidate):

- transport is injected (fetch(url_no_key) -> (status, headers, body),
  the same shape as pilot_acquire.Transport). In this task only a
  synthetic fake implements it. NO network, NO credential resolution:
  a production binding would attach the credential at fetch time via
  the sanctioned helper exactly as pilot_acquire.UrllibTransport does,
  and could reuse the FRESH lineage's /api_usage call shape
  (dispatch_gate_r4.py, sha256 b53996454650dafc77e647a8497eba91beb37
  85fb52c13d70fa81768fd370117) ONLY through this adapter interface
  with that pin recorded — Policy-A authority and the FRESH manifest
  are never copied or inherited.
- max 2 attempts (retry only on 429/5xx/timeout); fail closed on
  non-200, malformed JSON, missing schema fields, or insufficient
  credit headroom for the day's remaining worst case.
- emits a byte receipt (request/receipt UTC-ms, HTTP status, byte
  count, SHA-256, sanitized params) in the pilot receipt shape, PLUS
  the sanitized response body and its digest, so the stored receipt
  is self-verifying.
- once per execution day: the session writes an O_EXCL receipt file
  api_usage.<DAY>.receipt.json into the store; a later invocation
  for the same day RE-VERIFIES the stored receipt before reusing it.

REPAIR over -65 (defect 3, adjudication comment 6310607516): the
-65 cached-PASS reuse trusted any JSON file with verdict=PASS and a
matching day — O_EXCL protected creation, not later verification.
The successor binds the cached receipt to the execution day, the
manifest SHA-256, the store marker, and the required headroom;
persists the sanitized response body + digest so current_usage /
plan_limit can be re-derived and cross-checked against the stored
fields; and rejects malformed, altered, stale/future,
weaker-headroom, or cross-manifest residue BEFORE any data
transport is constructed or used.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

USAGE_URL = "https://api.twelvedata.com/api_usage"
USAGE_REQUEST_ID = "API-USAGE-PREFLIGHT"
MAX_ATTEMPTS = 2
RETRYABLE_STATUS = {429, 502, 503, 504}
DAY_MS = 86_400_000
FUTURE_SKEW_MS = 300_000


class PreflightRefusal(Exception):
    def __init__(self, tag: str, detail: str = ""):
        super().__init__(f"{tag}: {detail}" if detail else tag)
        self.tag = tag


def parse_usage_body(body: bytes) -> tuple[int, int]:
    """Return (current_usage, plan_limit). Fail closed on any schema
    deviation — the /api_usage schema is execution-day-observed, so
    this candidate accepts only the documented integer pair shape."""
    try:
        payload = json.loads(body)
    except Exception as e:
        raise PreflightRefusal("USAGE_SCHEMA", f"bad JSON: {e}") from e
    if not isinstance(payload, dict):
        raise PreflightRefusal("USAGE_SCHEMA", "not a JSON object")
    cur = payload.get("current_usage")
    lim = payload.get("plan_limit")
    for name, v in (("current_usage", cur), ("plan_limit", lim)):
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            raise PreflightRefusal("USAGE_SCHEMA", f"{name} not int>=0")
    return cur, lim


def canonical_usage_payload(cur: int, lim: int) -> str:
    """Canonical sanitized payload for the usage response: exactly
    the two schema fields, deterministic key order/encoding."""
    return json.dumps({"current_usage": cur, "plan_limit": lim},
                      sort_keys=True, separators=(",", ":"))


class AccountPreflight:
    """Injectable /api_usage preflight. `required_headroom` is the
    day's remaining worst-case call count; the check passes only if
    current_usage + required_headroom <= plan_limit."""

    def __init__(self, transport, clock=None, sleeper=None,
                 required_headroom: int = 0):
        self.transport = transport
        self.clock = clock or time.time
        self.sleeper = sleeper or (lambda s: None)
        self.required_headroom = required_headroom
        self.attempts_made = 0

    def check(self) -> dict:
        last_status = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            t0 = self.clock()
            try:
                status, _headers, body = self.transport.fetch(USAGE_URL)
            except TimeoutError:
                status, body = 0, b""
            t1 = self.clock()
            self.attempts_made = attempt
            last_status = status
            receipt = {
                "request_id": USAGE_REQUEST_ID,
                "attempt": attempt,
                "request_ts_ms": int(t0 * 1000),
                "receipt_ts_ms": int(t1 * 1000),
                "http_status": status,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "params": {"endpoint": "/api_usage"},
            }
            if status == 200:
                cur, lim = parse_usage_body(body)  # raises on schema
                if cur + self.required_headroom > lim:
                    raise PreflightRefusal(
                        "USAGE_HEADROOM",
                        f"current {cur} + headroom "
                        f"{self.required_headroom} > limit {lim}")
                payload = canonical_usage_payload(cur, lim)
                receipt["current_usage"] = cur
                receipt["plan_limit"] = lim
                receipt["response_payload"] = payload
                receipt["response_sha256"] = hashlib.sha256(
                    payload.encode()).hexdigest()
                receipt["verdict"] = "PASS"
                return receipt
            if status in RETRYABLE_STATUS or status == 0:
                if attempt < MAX_ATTEMPTS:
                    self.sleeper(0)
                    continue
                raise PreflightRefusal(
                    "USAGE_RETRIES_EXHAUSTED", f"status {status}")
            raise PreflightRefusal("USAGE_TERMINAL_STATUS",
                                   f"status {status}")
        raise PreflightRefusal("USAGE_RETRIES_EXHAUSTED",
                               f"status {last_status}")


def store_marker_sha256(store_marker: str) -> str:
    return hashlib.sha256(store_marker.encode()).hexdigest()


class DailyUsageSession:
    """Once-per-execution-day binding used as the ManifestDriver
    preflight callable: performs the AccountPreflight check on first
    invocation, persists its receipt O_EXCL, and on any later
    invocation for the same day RE-VERIFIES + reuses the stored
    receipt instead of calling again. Returns [] on pass (pilot
    preflight convention), [reason] on failure — which the wrapper
    turns into a fail-closed abort BEFORE any data request is
    fetched.

    The stored receipt is integrity-bound (defect-3 repair): reuse
    requires verdict PASS, matching day, manifest SHA-256, store
    marker digest, and the session's required headroom; the stored
    canonical response payload must digest-match and re-derive the
    stored current_usage/plan_limit; headroom must still hold; and
    the receipt timestamp must be neither stale (> 1 day) nor
    future-dated. Any defect refuses before data transport."""

    def __init__(self, store_dir: Path, day: str,
                 preflight: AccountPreflight,
                 manifest_sha256: str, store_marker: str,
                 required_headroom: int, clock=None):
        self.store_dir = Path(store_dir)
        self.day = day
        self.preflight = preflight
        self.manifest_sha256 = manifest_sha256
        self.store_marker = store_marker
        self.required_headroom = required_headroom
        self.clock = clock or time.time
        self.receipt_path = self.store_dir / \
            f"api_usage.{day}.receipt.json"
        self.receipt: dict | None = None

    def _verify_cached(self, stored) -> str | None:
        """Return None if the cached receipt may be reused, else a
        refusal reason string."""
        if not isinstance(stored, dict):
            return "USAGE_CACHE_MALFORMED: not an object"
        if stored.get("verdict") != "PASS" or \
                stored.get("day") != self.day:
            return "USAGE_RECEIPT_INVALID"
        if stored.get("request_id") != USAGE_REQUEST_ID or \
                stored.get("http_status") != 200:
            return "USAGE_CACHE_IDENTITY"
        attempt = stored.get("attempt")
        if not isinstance(attempt, int) or isinstance(attempt, bool) \
                or not 1 <= attempt <= MAX_ATTEMPTS:
            return "USAGE_CACHE_IDENTITY: attempt out of range"
        if stored.get("manifest_sha256") != self.manifest_sha256:
            return "USAGE_CACHE_BINDING: manifest_sha256 mismatch"
        if stored.get("store_marker_sha256") != \
                store_marker_sha256(self.store_marker):
            return "USAGE_CACHE_BINDING: store marker mismatch"
        if stored.get("required_headroom") != self.required_headroom:
            return ("USAGE_CACHE_BINDING: required_headroom "
                    f"{stored.get('required_headroom')!r} != "
                    f"{self.required_headroom!r} (weaker cached "
                    "headroom is never reusable)")
        payload = stored.get("response_payload")
        digest = stored.get("response_sha256")
        if not isinstance(payload, str) or not isinstance(digest, str):
            return "USAGE_CACHE_BODY_MISSING"
        if hashlib.sha256(payload.encode()).hexdigest() != digest:
            return "USAGE_CACHE_BODY_ALTERED: payload digest mismatch"
        try:
            cur, lim = parse_usage_body(payload.encode())
        except PreflightRefusal as e:
            return f"USAGE_CACHE_BODY_ALTERED: {e}"
        if cur != stored.get("current_usage") or \
                lim != stored.get("plan_limit"):
            return ("USAGE_CACHE_BODY_ALTERED: payload fields != "
                    "stored fields")
        if cur + self.required_headroom > lim:
            return "USAGE_CACHE_HEADROOM"
        req_ts = stored.get("request_ts_ms")
        rcpt_ts = stored.get("receipt_ts_ms")
        for v in (req_ts, rcpt_ts):
            if not isinstance(v, int) or isinstance(v, bool):
                return "USAGE_CACHE_TIMESTAMP: non-integer ts"
        if req_ts <= 0 or rcpt_ts < req_ts:
            return "USAGE_CACHE_TIMESTAMP: insane ts order"
        now_ms = int(self.clock() * 1000)
        if rcpt_ts > now_ms + FUTURE_SKEW_MS:
            return "USAGE_CACHE_TIMESTAMP: future-dated receipt"
        if now_ms - rcpt_ts > DAY_MS:
            return "USAGE_CACHE_TIMESTAMP: stale receipt (>1 day)"
        return None

    def __call__(self) -> list[str]:
        if self.receipt_path.exists():
            try:
                stored = json.loads(self.receipt_path.read_text())
            except Exception as e:
                return [f"USAGE_CACHE_MALFORMED: {e}"]
            reason = self._verify_cached(stored)
            if reason is not None:
                return [reason]
            self.receipt = stored
            return []
        try:
            receipt = self.preflight.check()
        except PreflightRefusal as e:
            return [str(e)]
        receipt = dict(receipt)
        receipt["day"] = self.day
        receipt["manifest_sha256"] = self.manifest_sha256
        receipt["store_marker_sha256"] = store_marker_sha256(
            self.store_marker)
        receipt["required_headroom"] = self.required_headroom
        self.store_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.receipt_path),
                     os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, json.dumps(receipt, indent=2).encode())
        finally:
            os.close(fd)
        self.receipt = receipt
        return []
