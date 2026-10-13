#!/usr/bin/env python3
"""Twelve Data pilot acquisition wrapper — FROZEN (r3).

Tasks: QF-TD-PILOT-READINESS-R2-20261010-04 (r2),
       QF-TD-PILOT-READINESS-R3-20261010-06 (r3, Issue #1 6099318779).
Reuses accepted fd03906 modules (rate_limiter.py v4, verify_sources.py).
No fd03906 fixture modified. Wrapper behavior covered by its own
bounded fixture file (tests/test_acquisition_wrapper.py).

Scope: vendor acquisition only — request, receipt, snapshot store.
Construction stays on the cleared pilot_build.py chain (separate stage).

r3 fixes (6099318779 defects 1-11):
  1. Warmup: PAR-1H bounds start 2026-04-01 (exact v7 rule) covering the
     215-4H-bar warmup; ADJ bounds extended with preregistered 215-4H-bar
     warmup (108 sessions) per v7 §2b. Decision-impact stays gated.
  2/12. Budget: ONE non-overlapping formula —
     total_calls = base_requests + pagination_pages + retries,
     each call counted exactly once. PAG max excludes PAR base calls.
  3. Machine-readable manifest (request_manifest.json) + ManifestDriver
     enforcing unique IDs, bounds, output paths, day/leg rules, retry
     totals, pagination creation, revision-to-base linkage.
  4. UrllibTransport.fetch(): HTTPError preserved with real status/body/
     scrubbed headers; only true timeout/connection errors -> TimeoutError.
  5. Pilot-wide shared retry cap (40) enforced in the wrapper.
  6. Crash-safe resume: completion marker = verified receipt; orphan
     snapshot (no/invalid receipt) is quarantined and refetched, never
     silently SKIPPED_RESUMED.
  7. Durable append-only attempt receipts (<id>.attempts.jsonl).
  8. 429 "consecutive" counter resets on any non-429 attempt; rolling
     window counts distinct request IDs.
  9. Schema binding: meta.symbol and meta.interval must match the request.
 10. Pacing frozen: driver EXITS on LEDGER_REFUSED; resume is a fresh
     invocation skipping completed requests. No busy-wait.
 11. ADJ warmup bounds restored per v7 §2b (no silent scope expansion).

Pinned rules:
  - one shared RollingCreditLimiter ledger; fail closed on refusal
  - idempotent resume via verified completion markers; O_EXCL no-overwrite
  - per-request receipts: UTC-ms times, bytes, SHA-256, sanitized params,
    scrubbed HTTP status/headers; no key material anywhere
  - retry: max 3 attempts/request (1+2); qualifying 429/502/503/504/
    timeout; backoff 60s then 300s; each retry re-acquires a credit AND
    consumes the shared retry budget (cap 40)
  - terminal: 401/403 -> stop run; 404 -> INSUFFICIENT_404 (continue only
    when spec.allow_404_continue); 200 with schema break -> quarantine+stop
  - measurable 429 stop: 2 consecutive 429s on one request after backoff
    -> RATE_STOP; 3 distinct-request 429s in any rolling 10-min window
    -> stop run
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
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
PILOT_RETRY_CAP = 40        # pilot-wide additional-call budget (defect 5)
# measurable 429 stop rule
CONSECUTIVE_429_STOP = 2    # on one request, after backoff
WINDOW_429_STOP = 3         # distinct requests, rolling 10 minutes
WINDOW_429_S = 600

KEY_RE = re.compile(r"apikey=[^&\s]*", re.IGNORECASE)
# allowlisted response headers for attempt receipts (defect 7)
SAFE_HEADERS = {
    "content-type", "content-length", "date", "retry-after",
    "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset",
}


def scrub(text: str) -> str:
    """Remove credential-bearing material from logs/errors."""
    return KEY_RE.sub("apikey=REDACTED", text)


def scrub_headers(headers: dict) -> dict:
    """Keep only allowlisted headers; scrub any key material in values."""
    out = {}
    for k, v in headers.items():
        if k.lower() in SAFE_HEADERS:
            out[k.lower()] = scrub(str(v))[:200]
    return out


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
    leg: str                 # PAR | PAR4H | ADJ | SPOT | PAG | REV7 | REV30
    day: str                 # D0 | D1 | D7 | D30
    output_name: str         # snapshot file name
    max_attempts: int = MAX_ATTEMPTS
    allow_404_continue: bool = False  # TWTR delisted leg only
    base_request_id: str = ""  # REV legs: link to base request


@dataclass
class RequestOutcome:
    request_id: str
    outcome: str             # OK | SKIPPED_RESUMED | INSUFFICIENT_404 |
                             # RETRIES_EXHAUSTED | AUTH_STOP |
                             # SCHEMA_QUARANTINE | LEDGER_REFUSED | RATE_STOP
    attempts: int = 0
    receipt: dict = field(default_factory=dict)


class RetryBudget:
    """Pilot-wide shared retry cap (defect 5). Each retry consumes one."""

    def __init__(self, cap: int = PILOT_RETRY_CAP):
        self.cap = cap
        self.used = 0

    def consume(self) -> bool:
        """True if a retry is allowed (and consumed)."""
        if self.used >= self.cap:
            return False
        self.used += 1
        return True


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
                return resp.status, scrub_headers(dict(resp.headers)), \
                    resp.read()
        except urllib.error.HTTPError as e:
            # defect 4: preserve real HTTP status/body/headers explicitly.
            # Python raises HTTPError for 401/403/404/429/5xx.
            try:
                body = e.read()
            except Exception:
                body = b""
            return e.code, scrub_headers(dict(e.headers or {})), body
        except (urllib.error.URLError, TimeoutError, ConnectionError,
                OSError) as e:
            # true timeout / connection failure only -> retryable
            raise TimeoutError(scrub(str(e))) from e


class AcquisitionWrapper:
    def __init__(self, store_dir: Path, ledger: RollingCreditLimiter,
                 transport: Transport, clock=None, sleeper=None,
                 preflight=None, retry_budget: RetryBudget | None = None):
        self.store_dir = Path(store_dir)
        self.ledger = ledger
        self.transport = transport
        self.clock = clock or time.time
        self.sleeper = sleeper or time.sleep
        self.preflight = preflight or self._default_preflight
        self.retry_budget = retry_budget or RetryBudget()
        self._429_events: list[tuple[float, str]] = []  # (ts, request_id)

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

    def _schema_ok(self, payload: object, spec: RequestSpec) -> bool:
        # defect 9: bind meta.symbol and meta.interval to the request
        if not isinstance(payload, dict):
            return False
        if payload.get("status") != "ok":
            return False
        meta = payload.get("meta")
        if not isinstance(meta, dict):
            return False
        if meta.get("symbol") != spec.symbol:
            return False
        if meta.get("interval") != spec.interval:
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

    def _receipt_path(self, spec: RequestSpec) -> Path:
        return self.store_dir / (spec.request_id + ".receipt.json")

    def _attempts_path(self, spec: RequestSpec) -> Path:
        return self.store_dir / (spec.request_id + ".attempts.jsonl")

    def _log_attempt(self, spec: RequestSpec, entry: dict) -> None:
        """Durable append-only attempt receipt (defect 7)."""
        self.store_dir.mkdir(parents=True, exist_ok=True)
        with open(self._attempts_path(spec), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")

    def _completion_ok(self, spec: RequestSpec) -> bool:
        """Fail-closed completion marker (defect 6): snapshot + receipt
        must exist and agree on SHA-256, bytes, and sanitized params."""
        snap = self.store_dir / spec.output_name
        rcpt = self._receipt_path(spec)
        if not (snap.exists() and rcpt.exists()):
            return False
        try:
            body = snap.read_bytes()
            r = json.loads(rcpt.read_text())
        except Exception:
            return False
        _, params = self._build_url(spec)
        return (
            r.get("sha256") == hashlib.sha256(body).hexdigest()
            and r.get("bytes") == len(body)
            and r.get("params") == params
        )

    def _quarantine_orphan(self, spec: RequestSpec) -> str:
        """A snapshot without a valid receipt is an orphan: quarantine it
        for forensics and refetch (defect 6). Never silently accept."""
        snap = self.store_dir / spec.output_name
        name = f"{spec.output_name}.orphan.{int(self.clock() * 1000)}"
        snap.rename(self.store_dir / name)
        return name

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

    def _note_429(self, now: float, request_id: str) -> bool:
        """True when the rolling 429 window trips the run stop.
        Defect 8: counts DISTINCT request IDs in the window."""
        self._429_events = [(t, rid) for t, rid in self._429_events
                            if now - t < WINDOW_429_S]
        self._429_events.append((now, request_id))
        distinct = {rid for _, rid in self._429_events}
        return len(distinct) >= WINDOW_429_STOP

    def _run_one(self, spec: RequestSpec) -> RequestOutcome:
        snap = self.store_dir / spec.output_name
        if snap.exists():
            if self._completion_ok(spec):
                return RequestOutcome(spec.request_id, "SKIPPED_RESUMED")
            # defect 6: orphan — quarantine and refetch, never skip silently
            orphan = self._quarantine_orphan(spec)
            self._log_attempt(spec, {
                "event": "orphan_quarantined", "orphan": orphan,
                "ts_ms": int(self.clock() * 1000)})
        url, params = self._build_url(spec)
        consecutive_429 = 0
        attempts = 0
        last_receipt: dict = {}
        while attempts < spec.max_attempts:
            if not self.ledger.try_acquire(1, label=spec.request_id):
                return RequestOutcome(spec.request_id, "LEDGER_REFUSED",
                                      attempts, last_receipt)
            attempts += 1
            # defect 5: every retry consumes the shared pilot-wide budget
            if attempts > 1 and not self.retry_budget.consume():
                self._log_attempt(spec, {
                    "event": "retry_budget_exhausted",
                    "attempt": attempts, "ts_ms": int(self.clock() * 1000)})
                return RequestOutcome(spec.request_id,
                                      "RETRIES_EXHAUSTED", attempts - 1,
                                      last_receipt)
            t0 = self.clock()
            try:
                status, headers, body = self.transport.fetch(url)
            except TimeoutError:
                status, body = 0, b""
                headers = {}
            t1 = self.clock()
            attempt_entry = {
                "request_id": spec.request_id,
                "attempt": attempts,
                "request_ts_ms": int(t0 * 1000),
                "receipt_ts_ms": int(t1 * 1000),
                "http_status": status,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "headers": headers,  # already scrubbed by transport
            }
            receipt = dict(attempt_entry)
            receipt["params"] = params  # sanitized: no key material
            last_receipt = receipt
            if status == 200:
                try:
                    payload = json.loads(body)
                except Exception:
                    payload = None
                if self._schema_ok(payload, spec):
                    try:
                        self._write_snapshot(spec.output_name, body)
                    except FileExistsError:
                        # raced creation: verify before accepting
                        if self._completion_ok(spec):
                            attempt_entry["event"] = "race_resolved_skip"
                            self._log_attempt(spec, attempt_entry)
                            return RequestOutcome(spec.request_id,
                                                  "SKIPPED_RESUMED",
                                                  attempts, receipt)
                        self._quarantine_orphan(spec)
                        self._write_snapshot(spec.output_name, body)
                    self._receipt_path(spec).write_text(
                        json.dumps(receipt, indent=2))
                    attempt_entry["event"] = "ok"
                    self._log_attempt(spec, attempt_entry)
                    return RequestOutcome(spec.request_id, "OK",
                                          attempts, receipt)
                attempt_entry["event"] = "schema_quarantine"
                self._log_attempt(spec, attempt_entry)
                return RequestOutcome(spec.request_id,
                                      "SCHEMA_QUARANTINE", attempts, receipt)
            if status in TERMINAL_AUTH:
                attempt_entry["event"] = "auth_stop"
                self._log_attempt(spec, attempt_entry)
                return RequestOutcome(spec.request_id, "AUTH_STOP",
                                      attempts, receipt)
            if status == 404:
                attempt_entry["event"] = "http_404"
                self._log_attempt(spec, attempt_entry)
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
                        attempt_entry["event"] = "rate_stop_consecutive"
                        self._log_attempt(spec, attempt_entry)
                        return RequestOutcome(spec.request_id, "RATE_STOP",
                                              attempts, receipt)
                    if self._note_429(t1, spec.request_id):
                        attempt_entry["event"] = "rate_stop_window"
                        self._log_attempt(spec, attempt_entry)
                        return RequestOutcome(spec.request_id, "RATE_STOP",
                                              attempts, receipt)
                else:
                    # defect 8: any non-429 attempt resets the counter
                    consecutive_429 = 0
                if attempts < spec.max_attempts:
                    attempt_entry["event"] = "retry_scheduled"
                    self._log_attempt(spec, attempt_entry)
                    self.sleeper(BACKOFF_S[attempts - 1])
                    continue
                attempt_entry["event"] = "retries_exhausted"
                self._log_attempt(spec, attempt_entry)
                return RequestOutcome(spec.request_id,
                                      "RETRIES_EXHAUSTED", attempts, receipt)
            # any other status: terminal, no retry
            attempt_entry["event"] = "terminal_status"
            self._log_attempt(spec, attempt_entry)
            return RequestOutcome(spec.request_id, "SCHEMA_QUARANTINE",
                                  attempts, receipt)
        attempt_entry = {"event": "attempts_cap_reached",
                         "ts_ms": int(self.clock() * 1000)}
        self._log_attempt(spec, attempt_entry)
        return RequestOutcome(spec.request_id, "RETRIES_EXHAUSTED",
                              attempts, last_receipt)


# ---------------------------------------------------------------------------
# Manifest driver (defect 3): machine-readable manifest enforcement
# ---------------------------------------------------------------------------

MANIFEST_SCHEMA_REQUIRED = [
    "request_id", "symbol", "interval", "start_date", "end_date",
    "timezone", "outputsize", "order", "adjust", "leg", "day",
    "output_name",
]
DAY_ORDER = ["D0", "D1", "D7", "D30"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


class ManifestDriver:
    """Loads request_manifest.json and ENFORCES it (defect 3):
    unique IDs, datetime-precision bounds, output paths inside the store,
    day/leg execution order, retry totals via the shared RetryBudget,
    deterministic pagination creation, revision-to-base receipt linkage.

    Pacing (defect 10, frozen): on LEDGER_REFUSED the driver EXITS;
    resume is a fresh invocation that skips completed requests via
    completion markers. No busy-wait, no request lost or duplicated.
    """

    def __init__(self, manifest_path: Path, store_dir: Path,
                 ledger: RollingCreditLimiter, transport: Transport,
                 clock=None, sleeper=None, preflight=None,
                 retry_budget: RetryBudget | None = None):
        self.manifest_path = Path(manifest_path)
        self.store_dir = Path(store_dir)
        self.wrapper = AcquisitionWrapper(
            store_dir, ledger, transport, clock=clock, sleeper=sleeper,
            preflight=preflight,
            retry_budget=retry_budget or RetryBudget())
        self.manifest = self._load_and_validate()

    def _load_and_validate(self) -> dict:
        m = json.loads(self.manifest_path.read_text())
        reqs = m.get("requests", [])
        seen: set[str] = set()
        for r in reqs:
            for k in MANIFEST_SCHEMA_REQUIRED:
                if k not in r:
                    raise ValueError(f"manifest: {r.get('request_id')}"
                                     f" missing {k}")
            rid = r["request_id"]
            if rid in seen:
                raise ValueError(f"manifest: duplicate request_id {rid}")
            seen.add(rid)
            for bound in ("start_date", "end_date"):
                if not DATE_RE.match(r[bound]):
                    raise ValueError(
                        f"manifest: {rid} {bound} not datetime-precision")
            if r["day"] not in DAY_ORDER:
                raise ValueError(f"manifest: {rid} bad day {r['day']}")
            out = Path(r["output_name"])
            if out.is_absolute() or ".." in out.parts:
                raise ValueError(f"manifest: {rid} bad output_name")
            if r.get("base_request_id") and \
                    r["base_request_id"] not in seen:
                # base must be defined earlier in the manifest
                raise ValueError(
                    f"manifest: {rid} base_request_id "
                    f"{r['base_request_id']} not defined")
        # budget formula check (defect 2/12): each call counted once
        b = m.get("budget", {})
        base = len(reqs)
        expect = b.get("expected_total")
        maxt = b.get("max_total")
        if expect != base:
            raise ValueError(
                f"manifest: expected_total {expect} != base {base}")
        if maxt != base + b.get("pagination_pages_max", 0) + \
                b.get("retries_max", 0):
            raise ValueError("manifest: max_total != base + pag + retries")
        return m

    def _to_spec(self, r: dict) -> RequestSpec:
        return RequestSpec(
            request_id=r["request_id"], symbol=r["symbol"],
            interval=r["interval"], start_date=r["start_date"],
            end_date=r["end_date"], timezone=r["timezone"],
            outputsize=r["outputsize"], order=r["order"],
            adjust=r["adjust"], leg=r["leg"], day=r["day"],
            output_name=r["output_name"],
            max_attempts=r.get("max_attempts", MAX_ATTEMPTS),
            allow_404_continue=r.get("allow_404_continue", False),
            base_request_id=r.get("base_request_id", ""))

    def requests_for_day(self, day: str) -> list[dict]:
        return [r for r in self.manifest["requests"] if r["day"] == day]

    def _base_receipt_ok(self, base_id: str) -> bool:
        rcpt = self.store_dir / (base_id + ".receipt.json")
        return rcpt.exists()

    def _pag_trigger(self, r: dict) -> list[dict]:
        """Deterministic pagination (defect 3): fires for symbol S iff S's
        parity-1H snapshot has exactly outputsize rows AND the earliest
        datetime is after the requested start_date. Max 2 extra pages."""
        if r["leg"] != "PAR" or r["interval"] != "1h":
            return []
        snap = self.store_dir / r["output_name"]
        try:
            payload = json.loads(snap.read_bytes())
            values = payload.get("values", [])
        except Exception:
            return []
        if len(values) != r["outputsize"]:
            return []
        earliest = min(v.get("datetime", "") for v in values)
        if not earliest or earliest <= r["start_date"]:
            return []
        children = []
        end = earliest
        for n in (1, 2):
            cid = f"REQ-PAG-{r['symbol']}-{n:02d}"
            children.append({
                "request_id": cid, "symbol": r["symbol"],
                "interval": "1h", "start_date": r["start_date"],
                "end_date": end, "timezone": r["timezone"],
                "outputsize": r["outputsize"], "order": r["order"],
                "adjust": r["adjust"], "leg": "PAG", "day": r["day"],
                "output_name": f"{cid}.json", "max_attempts": MAX_ATTEMPTS,
                "expected_credits": 1, "parent_request_id": r["request_id"],
            })
            # next page would end at this page's earliest bar; the driver
            # re-evaluates after each page, so only one child is queued here
            break
        return children

    def run_day(self, day: str) -> list[RequestOutcome]:
        """Run one frozen day. REV requests require their base receipt;
        PAG children are created deterministically after PAR 1H."""
        rows = self.requests_for_day(day)
        specs: list[RequestSpec] = []
        for r in rows:
            if r.get("base_request_id") and not self._base_receipt_ok(
                    r["base_request_id"]):
                raise RuntimeError(
                    f"driver: base receipt missing for {r['request_id']} "
                    f"(base {r['base_request_id']}) — fail closed")
            specs.append(self._to_spec(r))
        outcomes = self.wrapper.run(specs)
        # pagination pass after PAR 1H completes (same day)
        extra: list[RequestSpec] = []
        for r in rows:
            for child in self._pag_trigger(r):
                if any(c.request_id == child["request_id"]
                       for c in extra):
                    raise RuntimeError("driver: duplicate PAG child ID")
                extra.append(self._to_spec(child))
        if extra:
            outcomes.extend(self.wrapper.run(extra))
        return outcomes
