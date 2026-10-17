# PLACEMENT PROOF — custom.twelvedata status-query parameter (-17)

**Proven parameter name: `apikey`.** Established read-only, WITHOUT
resolving any credential, WITHOUT invoking the sanctioned helper, and
without printing any surrogate/token/credentialized URL.

## Evidence chain

1. **Helper contract (source).** Sanctioned helper
   `dynamic_credentials.py`, sha256
   `8b1f42e80a76710edf0ff2abf8a51b0cde35b06474af865de108a7ca27d6728d`
   (byte-identical at both sanctioned paths:
   `/opt/hatch/skills/skill-creator/bin/` and
   `/opt/muse/skills/custom-connector-setup/bin/`).
   `url_with_surrogate_query_param(url, credential_name, *,
   entry_name='access_token', allowed_hosts)` reads the credential
   entry's `placement` dict and appends exactly one pair
   `(placement["query_param"], surrogate)` to the URL's query via
   `urllib.parse.urlencode`. The parameter NAME therefore comes from
   the vault registration's placement record — never from the helper
   source and never from the entry name.
2. **Registered placement (sanitized attestation, committed).**
   `research_notes/td_transport_adapter/TD_VAULT_BINDING_CORRECTION_RESULT_20261014.md`,
   sha256 `54c92d9b24b8dce9c2c32d6060fc8f841191e74a31171616847e1505aa8132d4`
   (commit 1597988, verified on origin/main): a pre-coding read-only
   authd probe of `custom.twelvedata` returned an `hsurr:*` surrogate
   with registered placement `{"query_param": "apikey"}`; the
   production driver fails closed unless the placement is exactly
   that. Only the placement and value prefix/length classes were
   observed; no value was recorded.
3. **Behavioral confirmation (committed).**
   `research_notes/TD_FIRST_LIVE_SCREEN_RESULT_20261014.md`, sha256
   `bfa431e7cc16ba749fcad180cf1d299e5b4764b495b43e5bdfe7e2b50dc946b6`
   and `td_first_live_screen_evidence_20261014/screen_evidence.json`,
   sha256 `ce76ed4ea2c9ff9e565ee86b9d9224214b4c350e2e1753049390785d34ff5211`:
   the 2026-10-14 live screen ran through this exact helper path with
   `placement query_param=apikey enforced by driver` — Twelve Data
   accepted the produced URLs.

## What the helper produces for the pinned status URL

`https://api.twelvedata.com/api_usage` (no pre-existing query) gains
exactly one query pair: key `apikey`, value the `hsurr:*` surrogate
(urlencode-encoded). No other query effects. The vault ENTRY name is
`access_token` — that is the entry_name selector, NOT the query
parameter; the -15 boundary conflated the two.

## Boundary derivation (-17 candidate)

`live_readiness_executor_r3.py` pins `PLACEMENT_QUERY_PARAM = "apikey"`
as an input fact citing this proof (file + hashes above), and its
`_validate_status_url` requires exactly that one key, exactly one
occurrence, non-empty value, on the final credentialized URL.
