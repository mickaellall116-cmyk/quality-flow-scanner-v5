# TD Vault-Binding Correction — Result

**Task:** QF-TD-VAULT-BINDING-CORRECTION-20261014-05 r1 (ChatGPT assignment,
Issue #1 comment 6160434903; auto-approved under Mike's 2026-10-13 standing
rule). Executed by Muse, 2026-10-14.
**Scope honored:** correction of the key sourcing in the adapter that holds
SYNTHETIC IMPLEMENTATION PASS / LIVE USE HOLD. Zero vendor calls, zero
credits, zero spend. No PR merge (PR #8 untouched). No semantics or feed
claims. Nothing committed — commit-ready only, for central commit.

## The defect

`driver.py` sourced the Twelve Data API key from a plain environment
variable (`TWELVEDATA_API_KEY`) — a stand-in for a vault read. ChatGPT's
hold condition: live use requires the key bound to the Secure Vault
credential `custom.twelvedata`.

## What the binding is now

The production key source is `driver.get_api_key()`, bound to the Secure
Vault credential **`custom.twelvedata`** through this environment's
sanctioned credential facility — the same mechanism the legacy connectors
use (per `custom.legacy-tiingo/CONNECTOR.md`: Python CLIs import
`/opt/muse/skills/custom-connector-setup/bin/dynamic_credentials.py`):

1. `_vault_entry()` calls `dynamic_credential_entry("custom.twelvedata",
   "access_token")`, which POSTs to authd over its unix socket
   (`/run/hatch/auth/authd.sock`) and returns a credential entry whose
   value is an **`hsurr:*` surrogate — never the raw key**. The raw key
   never enters this process, this repo, or any artifact.
2. `get_api_key()` fails closed unless the entry's placement is exactly
   `{"query_param": "apikey"}` (the placement the vault registration
   declares and the adapter contract pins: apikey LAST) and the value is
   an `hsurr:*` surrogate. Violations raise sanitized `DriverError`
   category tokens (`vault_placement_mismatch`, `vault_non_surrogate_value`,
   `vault_entry_malformed`).
3. Retrieval failures are sanitized at the seam: any helper/authd failure
   becomes `DriverError("vault_credential_unavailable")` (or
   `vault_helper_unavailable` if the helper cannot be imported), raised
   `from None`; the helper's error text (which can embed authd response
   text) is never propagated.
4. The returned surrogate is held in memory only and handed to the
   adapter, which places it in the `apikey` query parameter; Sentinel
   substitutes the real key on approved egress. It is never written to
   disk, argv, logs, or exception text.
5. **There is no environment fallback in the production path.** The
   environment-variable source survives ONLY as the explicitly-named test
   fixture source `get_test_fixture_key()`, reading
   `TWELVEDATA_TEST_FIXTURE_API_KEY`, used solely by the local-server
   proof suite. `build_collector` resolves key material in the order:
   explicit `api_key` argument → explicit `key_source` callable → the
   production vault binding (default).

The adapter (`td_http_transport_adapter.py`) required **no change**: it is
transport-only and agnostic to whether the key string it holds is a raw key
or a surrogate. Its bytes are unchanged (sha256 `85c67977…`, the accepted
pin). One docstring phrase in it ("sourced by the driver from the
vault-style environment") is now superseded by this correction; the bytes
were deliberately left identical to preserve the accepted implementation
pin, and the stale phrase is flagged here for adjudication rather than
silently rewritten.

## Retrieval: proven live against authd (offline, no vendor contact)

Before coding, the sanctioned retrieval path was probed once in this
environment: `dynamic_credential_entry("custom.twelvedata", "access_token")`
**succeeded** — the credential exists, the returned value is an `hsurr:*`
surrogate, and the registered placement is `{"query_param": "apikey"}`.
The surrogate value itself was never printed, logged, or recorded (only
its prefix class, length class, and placement were observed). So the
binding is not an interface stub: retrieval works in this sandbox today.

## Proof (all local; loopback servers only)

- **Baseline:** the pre-correction suite was run first — 20/20 PASS —
  so the correction round starts from a verified-green baseline.
- **Corrected suite:** `test_evidence_vault_binding_20261014/` —
  **27/27 PASS**: all 20 original proofs intact and passing (including
  the local-server success round-trip, the 429 HOLD-with-evidence proof,
  and the fixture-key secret-isolation sweep), plus 7 new BindingLevel
  proofs against the corrected binding path:
  1. `test_vault_binding_returns_surrogate_despite_poisoned_env` — with
     both env vars poisoned with the fake key, the production binding
     returns the (stubbed) vault surrogate, not any env value.
  2. `test_vault_binding_sends_surrogate_as_apikey_last` — the surrogate
     reaches the local server as the `apikey` parameter, LAST in the
     contract's fixed parameter order.
  3. `test_vault_binding_failure_sanitized_no_env_fallback` — a helper
     failure carrying sensitive text surfaces only as the bare token
     `vault_credential_unavailable`; no env fallback occurs.
  4. `test_vault_binding_wrong_placement_fails_closed`.
  5. `test_vault_binding_non_surrogate_fails_closed`.
  6. `test_fixture_source_explicit_and_separate` — the fixture source
     reads only its own named variable; the old production env-var name
     no longer appears anywhere in `driver.py`.
  7. `test_vault_sourced_round_trip_and_secret_isolation` — a full
     collector round trip keyed by the **production binding** (authd
     fetch stubbed to a fake surrogate) completes COMPLETE, and the
     secret-isolation byte-scan over every runtime artifact (state,
     receipts, lifecycle, ledger) finds neither the surrogate, nor the
     fixture key, nor the string `apikey` in any JSON/JSONL artifact.
- **Live credit ledger untouched:** `research_notes/pilot_harness/credit_ledger.json`
  sha256 `ce515aa6fd53b297b693762e4236b2ea203874641ce745e482ba76daf1a67c59`
  before the baseline run, after the baseline run, and after the
  corrected run — identical. (All suite runs use scratch ledgers.)
- **Environment:** Python 3.12.3, pandas 2.2.3,
  pandas_market_calendars 4.5.1 (pinned-dependency venv), matching the
  prior round's evidence exactly. `vendor_calls: 0, credits: 0`.

## Residual limitations (stated plainly)

1. **Egress substitution is not proven — and cannot be proven offline.**
   The surrogate→real-key substitution is performed by Sentinel on
   approved outbound requests. Exercising it requires a live vendor
   request, which this task forbids and LIVE USE HOLD still gates. The
   first separately-authorized live acquisition remains the first
   end-to-end proof of substitution.
2. **Connection path nuance:** the adapter speaks `http.client` directly
   and does not consume the `http_proxy`/`https_proxy` configuration
   present in this sandbox. Whether the platform's substitution applies
   identically to a direct connection from the eventual live runner is a
   platform property to confirm at first live use — it is not assumed
   here.
3. **Suite determinism:** inside the test suite the authd fetch is
   stubbed (`drv._vault_entry`) so runs are deterministic; the real
   retrieval was proven separately by the one-off probe above, not
   inside the suite.
4. This correction addresses the **sourcing** hold condition only. It is
   not a live-use authorization, changes no acquisition prerequisites,
   and leaves the adapter's SYNTHETIC IMPLEMENTATION PASS / LIVE USE
   HOLD status otherwise exactly as adjudicated.

## Pins

| Artifact | sha256 |
|---|---|
| `driver.py` (corrected) | `be8c0bb74e2acfc4b4f0e5087fc636bb5f5461c43ecc231eb345618c1aa07cec` |
| `td_http_transport_adapter.py` (unchanged) | `85c67977d176e36135751e588cc81d1bb1f21e56821189796cf87bdaab389d31` |
| `test_transport_adapter.py` (updated) | `ce243f9695487ca1292bef77a02fd04ecb7a50f67f2fb9ea24cb1c74096d8ce2` |
| `test_evidence_vault_binding_20261014/results.json` | `20f0fe60d37845d51dc1f7f98851362afe649718403ad8b20b18073cf0afcc21` |
| `test_evidence_vault_binding_20261014/test_output.txt` | `a4bd4d0b6b875dd3a295a3c498425cfd6a6dd88f1733f74e6d1d20bab0844bb2` |
| Collector pin (unchanged) | `bd003c3cd5866172c04b0165d6ee60ec16be8487f28e90b4e6e1df046f8d489b` |
| Limiter pin (unchanged) | `06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64` |
| Live credit ledger (unchanged) | `ce515aa6fd53b297b693762e4236b2ea203874641ce745e482ba76daf1a67c59` |
| Sanctioned helper `dynamic_credentials.py` | `8b1f42e80a76710edf0ff2abf8a51b0cde35b06474af865de108a7ca27d6728d` |

Prior-round evidence (`test_evidence/`, 20/20 under the env stand-in) is
preserved untouched as the record of the superseded binding.

**Effort:** one session, one pass — baseline run, correction, corrected
run (27/27 on the first corrected run; no repair rounds consumed).
