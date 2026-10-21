#!/usr/bin/env python3
"""Production transport/credential binding — TD probe Day-1 LIVE
execution (task -69, QF-TD-PROBE-DAY1-EXECUTION-20261021).

New file added for the authorized Day-1 execution only. It plugs
into the ACCEPTED -68 candidate (probe_runner.py) through its
designed --transport-module injection point; no candidate logic is
modified.

What it does:
- fetch(url_no_key) -> (status, scrubbed_headers, body), mirroring
  the frozen pilot UrllibTransport semantics (30s timeout; HTTPError
  preserved with real status/body; only true timeout/connection
  errors raise TimeoutError).
- Credential: attached at fetch time ONLY via the sanctioned helper
  /opt/hatch/skills/skill-creator/bin/dynamic_credentials.py
  (url_with_surrogate_query_param, credential name
  "custom.twelvedata", allowed host api.twelvedata.com only). The
  raw key never enters this process; the helper's surrogate is
  swapped by the egress layer. No key material is printed, logged,
  or written anywhere.
- Hard budget backstop (Mike's Day-1 authorization: expected 6,
  HARD ceiling 12 credits for the day): a process-wide counter
  shared by the usage and data transports refuses — BEFORE any
  transmission — any fetch that would exceed 12 total calls.
- G-USE backstop: the data transport, before its first fetch,
  reads the preflight receipt the DailyUsageSession persisted in
  the store and refuses (before transmitting) unless
  plan_limit - current_usage >= 12 (Day-1 worst case).

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
HARD_CALL_CEILING = 12
REQUIRED_REMAINING_HEADROOM = 12

KEY_RE = re.compile(r"apikey=[^&\s]*", re.IGNORECASE)
SAFE_HEADERS = {
    "content-type", "content-length", "date", "retry-after",
    "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset",
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
            headers={"User-Agent": "qf-td-probe-day1/69",
                     "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, \
                    _scrub_headers(dict(resp.headers)), resp.read()
        except urllib.error.HTTPError as e:
            try:
                body = e.read()
            except Exception:
                body = b""
            return e.code, _scrub_headers(dict(e.headers or {})), body
        except (urllib.error.URLError, TimeoutError, ConnectionError,
                OSError) as e:
            raise TimeoutError(_scrub(str(e))) from e


class UsageTransport(_BaseTransport):
    kind = "usage"


class DataTransport(_BaseTransport):
    kind = "data"

    def __init__(self):
        self._headroom_checked = False

    def _enforce_usage_headroom(self) -> None:
        """G-USE: before the first data transmission, the persisted
        preflight receipt must show remaining headroom >= the Day-1
        worst case (12). Fail closed before any data fetch."""
        store = os.environ.get("TD_PROBE_STORE", "")
        receipt_path = Path(store) / "api_usage.D1.receipt.json"
        try:
            receipt = json.loads(receipt_path.read_text())
            cur = receipt["current_usage"]
            lim = receipt["plan_limit"]
        except Exception as e:
            raise RuntimeError(
                f"G_USE_REFUSAL: preflight receipt unreadable ({e})"
            ) from e
        if receipt.get("verdict") != "PASS":
            raise RuntimeError("G_USE_REFUSAL: preflight not PASS")
        if lim - cur < REQUIRED_REMAINING_HEADROOM:
            raise RuntimeError(
                f"G_USE_REFUSAL: remaining headroom {lim - cur} "
                f"< {REQUIRED_REMAINING_HEADROOM} "
                f"(current_usage={cur}, plan_limit={lim})")
        self._headroom_checked = True

    def fetch(self, url_no_key: str):
        if not self._headroom_checked:
            self._enforce_usage_headroom()
        return super().fetch(url_no_key)


def make_data_transport():
    return DataTransport()


def make_usage_transport():
    return UsageTransport()


def make_clock():
    return time.time


def make_sleeper():
    return time.sleep
