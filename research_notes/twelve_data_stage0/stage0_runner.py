#!/usr/bin/env python3
"""Twelve Data Stage-0 bounded screen — FROZEN.

Scope (Mike authorization: 2026-10-10 direct, "Ok so run it"):
  - Exactly TWO /time_series requests, AAPL only:
      1. interval=1h
      2. interval=4h (diagnostic)
  - Frozen window: 2026-09-08 .. 2026-10-06
  - Two credits total, zero retries, zero extra endpoints, zero metadata calls.

Prerequisites (verified before execution):
  - custom.twelvedata credential present via authd surrogate (never raw key)
  - shared v4 RollingCreditLimiter ledger (8/min, 800/day) — fail closed
  - sanitized logging: key/redaction enforced; error strings never carry secrets

Outputs:
  - Private raw snapshots -> research_notes/twelve_data_stage0/snapshots/
    (git-ignored; licensed data is NEVER published)
  - Public manifest (hashes, sanitized params, counts) -> stage0_manifest.json
    in the same dir (committed; no raw bars)

Any failure = blocker report, exit non-zero. No retry, no expansion.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from dynamic_credentials import (  # noqa: E402
    DynamicCredentialError,
    url_with_surrogate_query_param,
)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "pilot_harness"))
from rate_limiter import RollingCreditLimiter  # noqa: E402

CRED = "custom.twelvedata"
ALLOWED = ["api.twelvedata.com"]
LEDGER = HERE.parent / "pilot_harness" / "credit_ledger.json"
SNAP_DIR = HERE / "snapshots"
MANIFEST = HERE / "stage0_manifest.json"

WINDOW_START = "2026-09-08"
WINDOW_END = "2026-10-06"
INTERVALS = ["1h", "4h"]
TIMEZONE = "America/New_York"


def fail(msg: str) -> int:
    print(json.dumps({"ok": False, "error": msg}))
    return 1


def main() -> int:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    limiter = RollingCreditLimiter(
        credits_per_minute=8, daily_cap=800, state_path=LEDGER
    )

    manifest = {
        "stage": "STAGE-0",
        "frozen_scope": {
            "symbol": "AAPL",
            "intervals": INTERVALS,
            "window_start": WINDOW_START,
            "window_end": WINDOW_END,
            "timezone": TIMEZONE,
            "max_credits": 2,
            "retries": 0,
        },
        "authorization": "Mike 2026-10-10 direct (Slack: 'Ok so run it')",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "requests": [],
    }

    for interval in INTERVALS:
        # Fail-closed credit acquisition: no credit, no request.
        if not limiter.try_acquire(1, label=f"stage0-aapl-{interval}"):
            return fail(f"limiter refused credit for {interval} (fail closed)")

        params = {
            "symbol": "AAPL",
            "interval": interval,
            "start_date": WINDOW_START,
            "end_date": WINDOW_END,
            "timezone": TIMEZONE,
            "outputsize": "5000",
            "order": "ASC",
        }
        url = "https://api.twelvedata.com/time_series?" + urllib.parse.urlencode(params)
        try:
            url = url_with_surrogate_query_param(url, CRED, allowed_hosts=ALLOWED)
        except DynamicCredentialError:
            return fail("credential unavailable (surrogate)")

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "qf-stage0/1.0",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                status = resp.status
        except urllib.error.HTTPError as e:
            # Zero retries: report the blocker exactly, stop.
            return fail(f"HTTP {e.code} on {interval} (no retry per frozen scope)")
        except Exception:
            return fail(f"request failed on {interval} (no retry per frozen scope)")

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return fail(f"non-JSON response on {interval}")

        snap_path = SNAP_DIR / f"aapl_{interval}_{WINDOW_START}_{WINDOW_END}.json"
        snap_path.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()

        values = payload.get("values") if isinstance(payload, dict) else None
        bar_count = len(values) if isinstance(values, list) else None

        manifest["requests"].append(
            {
                "interval": interval,
                "http_status": status,
                "bytes": len(body),
                "sha256": sha,
                "bar_count": bar_count,
                "snapshot": snap_path.name,
                # Sanitized params only — no key material anywhere.
                "params": params,
            }
        )
        # One call per interval; small gap to stay well under the per-minute cap.
        time.sleep(2)

    MANIFEST.write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"ok": True, "manifest": str(MANIFEST), "requests": manifest["requests"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
