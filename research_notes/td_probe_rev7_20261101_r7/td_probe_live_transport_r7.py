#!/usr/bin/env python3
"""Production transport/credential binding — TD probe REV7 (R7)
live re-pull, 2026-11-01.

Authorization: Mike's fresh GO in direct chat 2026-11-01 ("And can
we do the r7"). Scope: R7 leg ONLY of the S2 split probe — the
/api_usage preflight plus the two frozen REV7 re-pulls
(REQ-ADJ-01R7 NVDA splits, REQ-ADJ-02R7 TSLA splits) defined by
the accepted -74 candidate manifest (sha256 1bb86e17...).
Expected 3 credits; HARD ceiling 6 credits for the whole run.

Modeled on the -75 Day-1 binding (td_probe_live_transport.py)
with exactly three changes, all forced by this task's terms and
disclosed in the R7 result memo:

  CHANGE 1 (ceiling): HARD_CALL_CEILING = 6 (this task's
  authorization), not 12.

  CHANGE 2 (single attempt): the task's terms are one attempt
  per call, fail-closed, NO retry. The frozen candidate retries
  429/502/503/504/timeout outcomes (max_attempts=2). This binding
  therefore converts any retryable outcome — a retryable HTTP
  status, or a timeout/connection failure — into a recorded
  hard stop: the outcome is appended to
  r7_transport_failures.jsonl in the store, then a RuntimeError
  (NOT TimeoutError, so neither the preflight nor the driver
  treats it as retryable) aborts the run before any second
  transmission. Non-retryable statuses (200, 401/403, 400, 404)
  return normally to the candidate's own terminal handling,
  which is single-attempt by construction.

  CHANGE 3 (backstop day): the data-transport backstop requires
  the D7 usage receipt (api_usage.D7.receipt.json) to be a
  COMMITTED PASS (verdict == "PASS", commit_state == "1")
  before the first data transmission — the -75 change-2 rule
  applied to the D7 receipt instead of D1.

Unchanged from -75:
- fetch(url_no_key) -> (status, scrubbed_headers, body);
  HTTPError preserved with real status/body; credential
  attached at fetch time ONLY via the sanctioned helper
  /opt/hatch/skills/skill-creator/bin/dynamic_credentials.py
  (url_with_surrogate_query_param, credential name
  "custom.twelvedata", allowed host api.twelvedata.com only).
  The raw key never enters this process and is never printed,
  logged, or written.
- Process-wide call budget refuses — BEFORE transmission — any
  fetch that would exceed the ceiling.

Store path is passed via env TD_PROBE_STORE (absolute path).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")

from dynamic_credentials import (  # noqa: E402
    DynamicCredentialError,
    url_with_surrogate_query_param,
)

CRED = "custom.twelvedata"
ALLOWED_HOSTS = ["api.twelvedata.com"]
HARD_CALL_CEILING = 6
RETRYABLE_STATUS = {429, 502, 503, 504}

KEY_RE = re.compile(r"apikey=[^&\s]*", re.IGNORECASE)
SAFE_HEADERS = {
    "content-type", "content-length", "date", "retry-after",
    "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset",
    "api-credits-used", "api-credits-left",
}


def _scrub(text: str) -> str:
    return KEY_RE.sub("apikey=<redacted>", text)


def _scrub_headers(headers: dict) -> dict:
    out = {}
    for k, v in headers.items():
        if k.lower() in SAFE_HEADERS:
            out[k.lower()] = _scrub(str(v))[:200]
    return out


class _CallBudget:
    """Process-wide hard ceiling across usage + data fetches."""

    def __init__(self):
        self.used = 0

    def acquire(self, what: str) -> None:
        if self.used + 1 > HARD_CALL_CEILING:
            raise RuntimeError(
                f"CALL_CEILING_REFUSAL: {what} would exceed the "
                f"authorized hard ceiling of {HARD_CALL_CEILING} "
                f"calls (already used {self.used})")
        self.used += 1


_BUDGET = _CallBudget()


def _record_failure(kind: str, detail: dict) -> None:
    """Append the retryable outcome to the store sidecar BEFORE
    raising, so the stopped attempt leaves durable evidence even
    though the candidate's own attempt log never sees it."""
    store = os.environ.get("TD_PROBE_STORE", "")
    if not store:
        return
    try:
        path = Path(store) / "r7_transport_failures.jsonl"
        entry = {"ts_ms": int(time.time() * 1000), "kind": kind}
        entry.update(detail)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # the raise below is the fail-closed act; never mask it


class _BaseTransport:
    kind = "base"

    def fetch(self, url_no_key: str):
        _BUDGET.acquire(self.kind)
        try:
            url = url_with_surrogate_query_param(
                url_no_key, CRED, allowed_hosts=ALLOWED_HOSTS)
        except DynamicCredentialError as e:
            raise RuntimeError("credential unavailable") from e
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "qf-td-probe-r7/20261101",
                     "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status = resp.status
                headers = _scrub_headers(dict(resp.headers))
                body = resp.read()
        except urllib.error.HTTPError as e:
            try:
                body = e.read()
            except Exception:
                body = b""
            status = e.code
            headers = _scrub_headers(dict(e.headers or {}))
        except (urllib.error.URLError, TimeoutError, ConnectionError,
                OSError) as e:
            _record_failure(self.kind, {
                "outcome": "transport_error",
                "error": _scrub(str(e))[:300]})
            raise RuntimeError(
                f"R7_SINGLE_ATTEMPT_STOP: {self.kind} fetch failed "
                f"with a retryable transport error: "
                f"{_scrub(str(e))[:200]}") from e
        if status in RETRYABLE_STATUS:
            import hashlib
            _record_failure(self.kind, {
                "outcome": "retryable_http_status",
                "http_status": status,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "headers": headers})
            raise RuntimeError(
                f"R7_SINGLE_ATTEMPT_STOP: {self.kind} fetch returned "
                f"retryable HTTP {status}; task terms forbid retry")
        return status, headers, body


class UsageTransport(_BaseTransport):
    kind = "usage"


class DataTransport(_BaseTransport):
    kind = "data"

    def __init__(self):
        self._commit_checked = False

    def _enforce_committed_pass(self) -> None:
        """Backstop: before the first data transmission, the D7
        usage receipt persisted in the store must be a COMMITTED
        PASS (verdict PASS, commit_state "1"). Fail closed."""
        store = os.environ.get("TD_PROBE_STORE", "")
        receipt_path = Path(store) / "api_usage.D7.receipt.json"
        try:
            receipt = json.loads(receipt_path.read_text())
        except Exception as e:
            raise RuntimeError(
                f"G_USE_REFUSAL: preflight receipt unreadable ({e})"
            ) from e
        if receipt.get("verdict") != "PASS":
            raise RuntimeError("G_USE_REFUSAL: preflight not PASS")
        if receipt.get("commit_state") != "1":
            raise RuntimeError(
                "G_USE_REFUSAL: preflight receipt not in the "
                f"committed state (commit_state="
                f"{receipt.get('commit_state')!r})")
        self._commit_checked = True

    def fetch(self, url_no_key: str):
        if not self._commit_checked:
            self._enforce_committed_pass()
        return super().fetch(url_no_key)


def make_data_transport():
    return DataTransport()


def make_usage_transport():
    return UsageTransport()


def make_clock():
    return time.time


def make_sleeper():
    return time.sleep
