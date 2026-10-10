#!/usr/bin/env python3
"""Twelve Data pilot acquisition wrapper — FROZEN.

Task: QF-TD-PILOT-READINESS-R2-20261010-04 (Issue #1 comments
6098718465 / 6098722040). Addresses r1 defect 5: the wrapper is
IMPLEMENTED and pinned BEFORE any request, reusing the accepted
fd03906 modules (rate_limiter.py v4, verify_sources.py). It does NOT
reopen fd03906: no harness fixture is modified; wrapper behavior is
covered by its own bounded fixture file
(tests/test_acquisition_wrapper.py, W01–W10).

Scope: vendor acquisition only — request, receipt, snapshot store.
Construction stays on the cleared pilot_build.py chain (separate stage).

Pinned rules (see TD_PILOT_READINESS_R2_20261010.md):
  - one shared RollingCreditLimiter ledger; fail closed on refusal
  - idempotent: existing snapshot -> skip (resume); O_EXCL no-overwrite
  - per-request receipts: UTC-ms request/receipt times, bytes, SHA-256,
    sanitized params, scrubbed HTTP status; no key material anywhere
  - retry: max 3 attempts/request (1+2); qualifying 429/502/503/504/
    timeout; backoff 60s then 300s; each retry re-acquires a credit
  - terminal: 401/403 -> stop run; 404 -> INSUFFICIENT (continue only
    when spec.allow_404_continue, e.g. TWTR delisted leg); 200 with
    schema break -> quarantine + stop
  - measurable 429 stop: 2 consecutive 429s on one request after
    backoff -> stop request+run; 3 total 429s across distinct requests
    within any 10-minute window -> stop run
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")

from rate_limiter import RollingCreditLimiter  # noqa: E402
import verify_sources  # noqa: E402

try:
    from dynamic_credentials import (
        DynamicCredentialError,
        url_with_surrogate_query_param,
    )
except Exception:  # pragma: no cover - fixtures never touch the network
    DynamicCredentialError = RuntimeError  # type: ignore
    url_with_surrogate_query_param = None  # type: ignore

CRED = "custom.twelvedata"
ALLOWED_HOSTS = ["api.twelvedata.com"]
BASE_URL = "https://api.twelvedata.com/time_series"

# --- pinned retry rule -------------------------------------------------
MAX_ATTEMPTS = 3            # 1 initial + 2 retries, per request
BACKOFF_S = (60, 300)       # sleep after attempt 1, then attempt 2
RETRYABLE_STATUS = {429, 502, 503, 504}
TERMINAL_AUTH = {401, 403}
# measurable 429 stop rule
CONSECUTIVE_429_STOP = 2    # on one request, after backoff
WINDOW_429_STOP = 3         # distinct requests, rolling 10 minutes
WINDOW_429_S = 600

KEY_RE = re.compile(r"apikey=[^&\s]*", re.IGNORECASE)


def scrub(text: str) -> str:
    """Remove credential-bearing material from logs/errors."""
    return KEY_RE.sub("apikey=REDACTED", text)


@dataclass(frozen=True)
class RequestSpec:
    request_id: str          # stable, e.g. REQ-P1H-01
    symbol: str
    interval: str            # 1h | 4h
    start_date: str          # datetime-precision, request tz
    end_date: str            # datetime-precision, request tz
    timezone: str            # America/New_York
    outputsize: int          # 5000
    order: str               # ASC
    adjust: str              # splits (pinned default, explicit)
    leg: str                 # PAR | ADJ | SPOT | REV7 | REV30
    day_offset: int          # execution day relative to D0
    output_name: str         # snapshot file name
    max_attempts: int = MAX_ATTEMPTS
    allow_404_continue: bool = False  # TWTR delisted leg only


@dataclass
class RequestOutcome:
    request_id: str
    outcome: str             # OK | SKIPPED_RESUMED | INSUFFICIENT_404 |
                             # RETRIES_EXHAUSTED | AUTH_STOP |
                             # SCHEMA_QUARANTINE | LEDGER_REFUSED | RATE_STOP
    attempts: int = 0
    receipt: dict = field(default_factory=dict)


class Transport:
    """Network boundary. Fixtures inject a fake; production uses Urllib."""

    def fetch(self, url_no_key: str) -> tuple[int, dict, bytes]:
        raise NotImplementedError


class UrllibTransport(Transport):
    """Real transport: attaches the authd surrogate at the last moment."""

    def fetch(self, url_no_key: str) -> tuple[int, dict, bytes]:
        if url_with_surrogate_query_param is None:
            raise RuntimeError("credential helper unavailable")
        try:
            url = url_with_surrogate_query_param(
                url_no_key, CRED, allowed_hosts=ALLOWED_HOSTS
            )
        except DynamicCredentialError as e:
            raise RuntimeError("credential unavailable") from e
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "qf-pilot-acquire/1.0",
                     "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except Exception as e:  # timeout / connection -> retryable
            raise TimeoutError(scrub(str(e))) from e


class AcquisitionWrapper:
    def __init__(self, store_dir: Path, ledger: RollingCreditLimiter,
                 transport: Transport, clock=None, sleeper=None,
                 preflight=None):
        self.store_dir = Path(store_dir)
        self.ledger = ledger
        self.transport = transport
        self.clock = clock or time.time
        self.sleeper = sleeper or time.sleep
        self.preflight = preflight or self._default_preflight
        self._429_times: list[float] = []

    @staticmethod
    def _default_preflight() -> list[str]:
        return verify_sources.verify_directory(
            verify_sources.ARCHIVAL_DIR, verify_sources.PINNED)

    def _build_url(self, spec: RequestSpec) -> tuple[str, dict]:
        params = {
            "symbol": spec.symbol,
            "interval": spec.interval,
            "start_date": spec.start_date,
            "end_date": spec.end_date,
            "timezone": spec.timezone,
            "outputsize": str(spec.outputsize),
            "order": spec.order,
            "adjust": spec.adjust,
        }
        url = BASE_URL + "?" + urllib.parse.urlencode(params)
        return url, params  # params carry NO key material by construction

    @staticmethod
    def _schema_ok(payload: object) -> bool:
        if not isinstance(payload, dict):
            return False
        if payload.get("status") != "ok":
            return False
        values = payload.get("values")
        if not isinstance(values, list):
            return False
        for v in values:
            if not isinstance(v, dict):
                return False
            for k in ("datetime", "open", "high", "low", "close"):
                if not isinstance(v.get(k), str):
                    return False
        return True

    def _write_snapshot(self, name: str, body: bytes) -> Path:
        """Atomic, no-overwrite: O_EXCL refuses when the file exists."""
        self.store_dir.mkdir(parents=True, exist_ok=True)
        final = self.store_dir / name
        tmp = self.store_dir / (name + ".tmp")
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, body)
        finally:
            os.close(fd)
        try:
            fd2 = os.open(str(final),
                          os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd2)
        except FileExistsError:
            tmp.unlink(missing_ok=True)
            raise
        os.replace(str(tmp), str(final))
        return final

    def run(self, specs: list[RequestSpec]) -> list[RequestOutcome]:
        failures = self.preflight()
        if failures:
            raise RuntimeError("preflight source verification failed: "
                               + "; ".join(failures[:3]))
        outcomes: list[RequestOutcome] = []
        for spec in specs:
            oc = self._run_one(spec)
            outcomes.append(oc)
            if oc.outcome in ("AUTH_STOP", "SCHEMA_QUARANTINE",
                              "RETRIES_EXHAUSTED", "LEDGER_REFUSED",
                              "RATE_STOP"):
                break  # fail closed: stop the run, report the blocker
        return outcomes

    def _note_429(self, now: float) -> bool:
        """True when the rolling 429 window trips the run stop."""
        self._429_times = [t for t in self._429_times
                           if now - t < WINDOW_429_S]
        self._429_times.append(now)
        return len(self._429_times) >= WINDOW_429_STOP

    def _run_one(self, spec: RequestSpec) -> RequestOutcome:
        snap = self.store_dir / spec.output_name
        if snap.exists():
            return RequestOutcome(spec.request_id, "SKIPPED_RESUMED")
        url, params = self._build_url(spec)
        consecutive_429 = 0
        attempts = 0
        last_receipt: dict = {}
        while attempts < spec.max_attempts:
            if not self.ledger.try_acquire(1, label=spec.request_id):
                return RequestOutcome(spec.request_id, "LEDGER_REFUSED",
                                      attempts, last_receipt)
            attempts += 1
            t0 = self.clock()
            try:
                status, headers, body = self.transport.fetch(url)
            except TimeoutError:
                status, body = 0, b""
                headers = {}
            t1 = self.clock()
            receipt = {
                "request_id": spec.request_id,
                "request_ts_ms": int(t0 * 1000),
                "receipt_ts_ms": int(t1 * 1000),
                "http_status": status,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "params": params,          # sanitized: no key material
                "attempt": attempts,
            }
            last_receipt = receipt
            if status == 200:
                try:
                    payload = json.loads(body)
                except Exception:
                    payload = None
                if self._schema_ok(payload):
                    try:
                        self._write_snapshot(spec.output_name, body)
                    except FileExistsError:
                        return RequestOutcome(spec.request_id,
                                              "SKIPPED_RESUMED",
                                              attempts, receipt)
                    (self.store_dir /
                     (spec.request_id + ".receipt.json")).write_text(
                        json.dumps(receipt, indent=2))
                    return RequestOutcome(spec.request_id, "OK",
                                          attempts, receipt)
                return RequestOutcome(spec.request_id,
                                      "SCHEMA_QUARANTINE", attempts, receipt)
            if status in TERMINAL_AUTH:
                return RequestOutcome(spec.request_id, "AUTH_STOP",
                                      attempts, receipt)
            if status == 404:
                if spec.allow_404_continue:
                    return RequestOutcome(spec.request_id,
                                          "INSUFFICIENT_404",
                                          attempts, receipt)
                return RequestOutcome(spec.request_id,
                                      "SCHEMA_QUARANTINE", attempts, receipt)
            if status in RETRYABLE_STATUS or status == 0:
                if status == 429:
                    consecutive_429 += 1
                    if consecutive_429 >= CONSECUTIVE_429_STOP:
                        return RequestOutcome(spec.request_id, "RATE_STOP",
                                              attempts, receipt)
                    if self._note_429(t1):
                        return RequestOutcome(spec.request_id, "RATE_STOP",
                                              attempts, receipt)
                if attempts < spec.max_attempts:
                    self.sleeper(BACKOFF_S[attempts - 1])
                    continue
                return RequestOutcome(spec.request_id,
                                      "RETRIES_EXHAUSTED", attempts, receipt)
            # any other status: terminal, no retry
            return RequestOutcome(spec.request_id, "SCHEMA_QUARANTINE",
                                  attempts, receipt)
        return RequestOutcome(spec.request_id, "RETRIES_EXHAUSTED",
                              attempts, last_receipt)
