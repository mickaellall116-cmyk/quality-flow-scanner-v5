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
  - The API key is bound to the Secure Vault credential
    custom.twelvedata (QF-TD-VAULT-BINDING-CORRECTION-20261014-05 r1).
    The production source, get_api_key(), fetches the credential's
    hsurr:* SURROGATE from authd via the sanctioned helper
    /opt/muse/skills/custom-connector-setup/bin/dynamic_credentials.py.
    The raw key never enters this process: the surrogate is what the
    adapter places in the apikey query parameter, and Sentinel
    substitutes the real key on approved egress. The surrogate is held
    in memory only — never written to disk, argv, logs, or exception
    text, and this module never prints it. Retrieval failures fail
    closed as sanitized category tokens. There is NO environment
    fallback in the production path.
  - The environment-variable key source survives ONLY as the
    explicitly-named TEST FIXTURE source (get_test_fixture_key), used
    solely by the local-server proof suite. Production code never
    calls it.
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

# --- Secure Vault binding (production key source) ----------------------
VAULT_CREDENTIAL_NAME = "custom.twelvedata"
VAULT_ENTRY_NAME = "access_token"
VAULT_REQUIRED_QUERY_PARAM = "apikey"  # adapter contract: apikey LAST
DYNAMIC_CREDENTIALS_DIR = "/opt/muse/skills/custom-connector-setup/bin"

# --- Test fixture key source (TEST-ONLY; never used in production) -----
TEST_FIXTURE_KEY_ENV = "TWELVEDATA_TEST_FIXTURE_API_KEY"


class DriverError(Exception):
    """Sanitized driver failure (pin mismatch / key source failure).

    Messages are category tokens only — they never contain credential
    material, surrogate values, helper error text, or paths beyond what
    this module's own constants define."""


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


def _vault_entry() -> dict:
    """Fetch the custom.twelvedata credential entry from authd via the
    sanctioned dynamic_credentials helper. Returns the helper's entry
    dict (name / surrogate / placement). Any failure — helper missing,
    authd unreachable, credential absent — becomes a sanitized
    DriverError; the helper's own error text is never propagated (it
    can embed authd response text)."""
    try:
        if DYNAMIC_CREDENTIALS_DIR not in sys.path:
            sys.path.insert(0, DYNAMIC_CREDENTIALS_DIR)
        from dynamic_credentials import dynamic_credential_entry
    except Exception:
        raise DriverError("vault_helper_unavailable") from None
    try:
        return dynamic_credential_entry(VAULT_CREDENTIAL_NAME,
                                        VAULT_ENTRY_NAME)
    except Exception:
        raise DriverError("vault_credential_unavailable") from None


def get_api_key() -> str:
    """PRODUCTION key binding: Secure Vault credential custom.twelvedata.

    Returns the hsurr:* surrogate for the credential's access_token
    entry — never the raw key, which never enters this process. The
    surrogate is handed to the adapter, which places it in the apikey
    query parameter (the placement the vault registration declares and
    the adapter contract pins); Sentinel substitutes the real key on
    approved egress to the vendor host. Memory only.

    Fails closed: wrong placement for the adapter contract, a
    non-surrogate value, or any retrieval failure raises DriverError
    with a category token only. The environment is NEVER consulted for
    production key material — there is no fallback."""
    entry = _vault_entry()
    if not isinstance(entry, dict):
        raise DriverError("vault_entry_malformed")
    placement = entry.get("placement")
    if not (isinstance(placement, dict)
            and placement.get("query_param") == VAULT_REQUIRED_QUERY_PARAM):
        raise DriverError("vault_placement_mismatch")
    surrogate = str(entry.get("surrogate", "")).strip()
    if not surrogate.startswith("hsurr:"):
        raise DriverError("vault_non_surrogate_value")
    return surrogate


def get_test_fixture_key() -> str:
    """TEST-ONLY key source for the local-server proof suite.

    Reads the explicitly-named fixture environment variable. This is
    the sole surviving environment key source; it exists so the suite
    can run the full binding against loopback servers with a fake key.
    Production code paths never call this function, and
    build_collector's default key source is the vault binding above."""
    key = os.environ.get(TEST_FIXTURE_KEY_ENV)
    if not key:
        raise DriverError("test_fixture_key_source_not_populated")
    return key


def build_collector(state_dir, manifest, prereq_path,
                    key_source=None,
                    base_url=None, ledger_path: Path = DEFAULT_LEDGER_PATH,
                    collector_path: Path = COLLECTOR_PATH):
    """Construct (Collector, adapter) exactly as a live run would, minus
    any dispatch decision — constructing this object makes no vendor
    requests (the default key source makes one local authd surrogate
    fetch).

    KEY PATH (QF-TD-COMBINED-DISPATCH-PREFLIGHT-20261014-06 r1): there
    is NO raw-key parameter. The only key paths are (a) the production
    default — the vault surrogate binding get_api_key(), whose result
    is re-asserted here to be an hsurr:* surrogate — and (b) an
    explicit key_source callable, which exists solely so the proof
    suite can inject the named test fixture source
    (get_test_fixture_key). Handing this function a raw key — as a
    keyword (no such parameter: TypeError) or as a non-callable
    key_source (DriverError) — refuses construction BEFORE any
    transport object exists. base_url defaults to the vendor origin;
    tests pass a loopback URL."""
    from td_http_transport_adapter import TDHttpTransportAdapter, VENDOR_BASE_URL
    if key_source is not None and not callable(key_source):
        raise DriverError("key_source_not_callable")
    mod = load_collector_module(collector_path)
    limiter = mod.RollingCreditLimiter(credits_per_minute=CREDITS_PER_MINUTE,
                                       daily_cap=DAILY_CAP,
                                       state_path=Path(ledger_path))
    if key_source is not None:
        key = key_source()
    else:
        key = get_api_key()
        if not (isinstance(key, str) and key.startswith("hsurr:")):
            raise DriverError("vault_non_surrogate_value")
    adapter = TDHttpTransportAdapter(
        api_key=key,
        base_url=base_url if base_url is not None else VENDOR_BASE_URL)
    collector = mod.Collector(Path(state_dir), manifest, limiter,
                              transport=adapter.transport,
                              semantics_status="INSUFFICIENT",
                              prereq_path=Path(prereq_path))
    return collector, adapter
