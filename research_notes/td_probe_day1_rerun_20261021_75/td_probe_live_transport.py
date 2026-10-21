#!/usr/bin/env python3
"""Production transport/credential binding — TD probe Day-1 LIVE
RERUN (task -75, QF-TD-PROBE-DAY1-RERUN-20261021-75).

Authorization: Mike, direct in chat, 2026-10-21 17:28 ET —
"Yes — Day 1 rerun GO (≤12 credits)". Scope DAY 1 ONLY.
Candidate: accepted -74 package (precommit b223595, result
71eee93; 70/70 synthetic PASS), accepted by ChatGPT.

New file added for this authorized rerun only. It plugs into the
-74 candidate (probe_runner.py) through its designed
--transport-module injection point; NO candidate logic is
modified — in particular the preflight (account_preflight.py)
decides pass/refuse by its own frozen rules.

Modeled on the -69 binding (td_probe_day1_execution_20261021_69)
with exactly two changes, both forced by the -70..-74 candidate
repairs and disclosed in the -75 result memo:

  CHANGE 1 (headers): the scrub allowlist additionally passes
  `api-credits-used` / `api-credits-left`. The -74 preflight
  captures exactly these two headers from the usage response
  and reconciles them against the body (they can only refuse,
  never waive the daily gate). The -69 binding dropped them
  because the -68 preflight had no header reconciliation.
  Values are vendor credit counters; no credential material can
  appear in them, and every value still passes the key scrub.

  CHANGE 2 (data-transport backstop): the -69 backstop required
  plan_limit - current_usage >= 12 before the first data fetch.
  That arithmetic encoded the DEFECTIVE -68 semantics
  (plan_limit is the per-minute bucket, not a daily budget) and
  would override the repaired candidate's own frozen gate —
  which the task forbids. The -75 backstop instead requires the
  persisted usage receipt to be a COMMITTED PASS
  (verdict == "PASS" and commit_state == "1", the -73/-74
  monotonic-commit state) before any data transmission. The
  candidate's DailyUsageSession has already enforced the
  explicit daily gate (daily_usage + headroom 10 <= the pinned
  800/day) before returning PASS; this backstop is
  defense-in-depth on the commit state only and derives no
  headroom of its own.

Unchanged from -69:
- fetch(url_no_key) -> (status, scrubbed_headers, body),
  mirroring the frozen pilot UrllibTransport semantics (30s
  timeout; HTTPError preserved with real status/body; only true
  timeout/connection errors raise TimeoutError).
- Credential attached at fetch time ONLY via the sanctioned
  helper /opt/hatch/skills/skill-creator/bin/
  dynamic_credentials.py (url_with_surrogate_query_param,
  credential name "custom.twelvedata", allowed host
  api.twelvedata.com only). The raw key never enters this
  process and is never printed, logged, or written.
- Hard budget backstop (Mike's authorization: expected 6, HARD
  ceiling 12 credits for the day): a process-wide counter
  shared by the usage and data transports refuses — BEFORE any
  transmission — any fetch that would exceed 12 total calls.

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

KEY_RE = re.compile(r"apikey=[^&\s]*", re.IGNORECASE)
SAFE_HEADERS = {
    "content-type", "content-length", "date", "retry-after",
    "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset",
    # -75 change 1: the two credit counters the -74 preflight
    # captures and reconciles (refuse-only; see module docstring).
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
            headers={"User-Agent": "qf-td-probe-day1/75",
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
        self._commit_checked = False

    def _enforce_committed_pass(self) -> None:
        """Backstop (-75 change 2): before the first data
        transmission, the usage receipt the DailyUsageSession
        persisted in the store must be a COMMITTED PASS
        (verdict PASS, commit_state "1"). Fail closed before any
        data fetch. No headroom is derived here — the
        candidate's frozen daily gate already decided."""
        store = os.environ.get("TD_PROBE_STORE", "")
        receipt_path = Path(store) / "api_usage.D1.receipt.json"
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
