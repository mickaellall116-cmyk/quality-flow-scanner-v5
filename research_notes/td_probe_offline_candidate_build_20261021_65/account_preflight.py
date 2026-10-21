#!/usr/bin/env python3
"""Account-preflight adapter — TD probe candidate (task -65 r1).

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
  count, SHA-256, sanitized params) in the pilot receipt shape.
- once per execution day: the session writes an O_EXCL receipt file
  api_usage.<DAY>.receipt.json into the store; a second check for the
  same day in the same store verifies and reuses it instead of
  calling again.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

USAGE_URL = "https://api.twelvedata.com/api_usage"
MAX_ATTEMPTS = 2
RETRYABLE_STATUS = {429, 502, 503, 504}


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
                "request_id": "API-USAGE-PREFLIGHT",
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
                        f"{self.required_headroom} > limit { lim}")
                receipt["current_usage"] = cur
                receipt["plan_limit"] = lim
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


class DailyUsageSession:
    """Once-per-execution-day binding used as the ManifestDriver
    preflight callable: performs the AccountPreflight check on first
    invocation, persists its receipt O_EXCL, and on any later
    invocation for the same day verifies + reuses the stored receipt
    instead of calling again. Returns [] on pass (pilot preflight
    convention), [reason] on failure — which the wrapper turns into a
    fail-closed abort BEFORE any data request is fetched."""

    def __init__(self, store_dir: Path, day: str,
                 preflight: AccountPreflight):
        self.store_dir = Path(store_dir)
        self.day = day
        self.preflight = preflight
        self.receipt_path = self.store_dir / f"api_usage.{day}.receipt.json"
        self.receipt: dict | None = None

    def __call__(self) -> list[str]:
        if self.receipt_path.exists():
            try:
                stored = json.loads(self.receipt_path.read_text())
            except Exception as e:
                return [f"USAGE_RECEIPT_MALFORMED: {e}"]
            if stored.get("verdict") != "PASS" or \
                    stored.get("day") != self.day:
                return ["USAGE_RECEIPT_INVALID"]
            self.receipt = stored
            return []
        try:
            receipt = self.preflight.check()
        except PreflightRefusal as e:
            return [str(e)]
        receipt = dict(receipt)
        receipt["day"] = self.day
        self.store_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.receipt_path),
                     os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, json.dumps(receipt, indent=2).encode())
        finally:
            os.close(fd)
        self.receipt = receipt
        return []
