#!/usr/bin/env python3
"""
driver.py — binding between the accepted collector, the shared persisted
limiter, and td-http-transport-adapter, per adapter_contract.json
(QF-TD-TRANSPORT-ADAPTER-IMPLEMENT-20261013-03 r1).

Binding rules enforced here:
  - The collector module is loaded ONLY if its bytes hash to the accepted
    pin (bd003c3c..., PR #8 / f64d12f). Any other bytes fail closed.
  - The limiter is the SAME RollingCreditLimiter class the integration
    proved (research_notes/pilot_harness/rate_limiter.py, sha256
    06ad383d...), constructed credits_per_minute=8, daily_cap=800, with
    state_path defaulting to the contract path
    research_notes/pilot_harness/credit_ledger.json — the one persisted
    ledger for every Twelve Data run. (Tests pass a scratch ledger path;
    the live wiring is the default.)
  - The API key is sourced from the environment (the driver-side stand-in
    for a Secure Vault read: custom.twelvedata), held in memory only, and
    handed to the adapter. It is never written to disk, argv, logs, or
    exception text, and this module never prints it.
  - semantics_status stays "INSUFFICIENT" (ruling R3); non-blocking
    try_acquire only, via the collector (the blocking acquire() is never
    used anywhere in this binding).
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
COLLECTOR_PATH = RESEARCH / "td_lifecycle_repair_candidate" / "td_min_collector.py"
COLLECTOR_SHA256 = "bd003c3cd5866172c04b0165d6ee60ec16be8487f28e90b4e6e1df046f8d489b"
LIMITER_RELATIVE = Path("pilot_harness") / "rate_limiter.py"
LIMITER_SHA256 = "06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64"
DEFAULT_LEDGER_PATH = RESEARCH / "pilot_harness" / "credit_ledger.json"
CREDITS_PER_MINUTE = 8
DAILY_CAP = 800
API_KEY_ENV = "TWELVEDATA_API_KEY"  # vault-style source (custom.twelvedata)


class DriverError(Exception):
    """Sanitized driver failure (pin mismatch / missing key source)."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_collector_module(collector_path: Path = COLLECTOR_PATH):
    """Load td_min_collector ONLY at the accepted pin. The module inserts
    its own sibling pilot_harness into sys.path, which is how the pinned
    rate_limiter / verify_sources / validate_input are bound."""
    collector_path = Path(collector_path)
    if _sha256(collector_path) != COLLECTOR_SHA256:
        raise DriverError("collector bytes do not match the accepted pin")
    harness = collector_path.parent.parent / LIMITER_RELATIVE
    if _sha256(harness) != LIMITER_SHA256:
        raise DriverError("rate_limiter bytes do not match the accepted pin")
    spec = importlib.util.spec_from_file_location("td_min_collector",
                                                  collector_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["td_min_collector"] = mod
    spec.loader.exec_module(mod)
    return mod


def get_api_key(env_var: str = API_KEY_ENV) -> str:
    """Vault-style key source: read once, memory only."""
    key = os.environ.get(env_var)
    if not key:
        raise DriverError("API key source is not populated")
    return key


def build_collector(state_dir, manifest, prereq_path, api_key=None,
                    base_url=None, ledger_path: Path = DEFAULT_LEDGER_PATH,
                    collector_path: Path = COLLECTOR_PATH):
    """Construct (Collector, adapter) exactly as a live run would, minus
    any dispatch decision — constructing this object makes no requests.
    base_url defaults to the vendor origin; tests pass a loopback URL."""
    from td_http_transport_adapter import TDHttpTransportAdapter, VENDOR_BASE_URL
    mod = load_collector_module(collector_path)
    limiter = mod.RollingCreditLimiter(credits_per_minute=CREDITS_PER_MINUTE,
                                       daily_cap=DAILY_CAP,
                                       state_path=Path(ledger_path))
    adapter = TDHttpTransportAdapter(
        api_key=api_key if api_key is not None else get_api_key(),
        base_url=base_url if base_url is not None else VENDOR_BASE_URL)
    collector = mod.Collector(Path(state_dir), manifest, limiter,
                              transport=adapter.transport,
                              semantics_status="INSUFFICIENT",
                              prereq_path=Path(prereq_path))
    return collector, adapter
