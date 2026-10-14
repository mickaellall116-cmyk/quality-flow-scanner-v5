# TD Sentinel Proxy Adapter — Result

**Task:** QF-TD-SENTINEL-PROXY-ADAPTER-20261014-07 r1 (ChatGPT assignment,
Issue #1 comment 6161574975; auto-approved under Mike's standing rule).
Executed by Muse (subagent), 2026-10-14.
**Cap:** 60 minutes incl. at most one ≤15-min repair pass — used: one
repair pass (~5 min, a connection-class defect in my own new code,
below). **Scope honored:** zero vendor calls, zero credits, zero spend,
no merge, no production changes, no semantics/feed/performance claims.
The live credit ledger `research_notes/pilot_harness/credit_ledger.json`
is byte-identical before and after (sha256
`ce515aa6fd53b297b693762e4236b2ea203874641ce745e482ba76daf1a67c59`).

## Disposition

The -06 preflight's resolution (a) is implemented: the adapter now has
explicit HTTPS CONNECT proxy support for vault-surrogate requests. The
Sentinel FAIL-AS-IS blocker is corrected at the adapter layer and
proven offline (41/41 proofs). The one-credit §4 screen is still NOT
executed and still needs its own authorization — it remains the
one-step live check that proves end-to-end substitution on the wire.
**Live dispatch remains HOLD.**

---

## 1. Implementation (`td_http_transport_adapter.py`, v1.0.0 → v1.1.0)

- **Engagement condition** (`_proxy_required`): proxy egress is
  mandatory exactly where Sentinel substitution can occur — the bound
  API key is an `hsurr:*` surrogate AND the request is HTTPS AND the
  host is non-loopback. Fixture keys, plain-HTTP loopback tests, and
  every other request keep the historical direct path byte-for-byte,
  which is why all 32 prior proofs pass unchanged.
- **Resolution** (`_resolve_proxy`): the proxy is resolved from the
  environment's `*_proxy` configuration the way the platform resolves
  it — `urllib.request.getproxies()`, scheme `https` — the same
  discovery the -06 probe used to identify the sanctioned channel
  (`https → http://hatch-egress-proxy:3128`). Resolution runs BEFORE
  any connection object exists. `no_proxy` is deliberately NOT
  consulted for surrogate requests: the proxy is mandatory, and a
  bypass entry naming the vendor host would recreate the direct path
  this correction exists to close.
- **Tunnel** (`_exchange`): an `http.client.HTTPSConnection` is
  addressed to the PROXY and `set_tunnel(target_host, target_port)` is
  set, so `connect()` dials the proxy, issues CONNECT, and only then
  starts the TLS handshake with the target (platform CA via the
  default context — unchanged, verification ON, hostname checked).
  The client never dials the target on this path.
- **No direct fallback, fail-closed categories** (sanitized tokens
  only; proxy host/port/credentials and key material never appear in
  any error, log, or artifact):
  - `proxy_unavailable` — no https proxy configured.
  - `proxy_malformed` — unparseable URL, missing host, invalid port,
    or a non-`http` proxy scheme (`http.client` cannot speak TLS to a
    proxy; the sanctioned egress is plain-HTTP CONNECT — any other
    scheme fails closed here instead of downgrading or improvising).
  - `proxy_credentials_rejected` — the proxy URL carries a
    username/password; such credentials are never used, propagated,
    or recorded.
  - `proxy_connect_failed` — the proxy answered CONNECT with a
    non-200 status (http.client surfaces this as an OSError whose
    text names the tunnel failure; the text selects the category and
    is never propagated).
  - Existing categories unchanged on this path: `tls_failure`,
    `connect_timeout`, `read_timeout` (phase-based), `protocol_error`,
    `connection_error`, `body_cap_exceeded`, redirect tokens.
- **Preserved guarantees:** exactly one attempt / no retries at any
  layer (resolution and tunnel happen inside the single `_exchange`
  per redirect hop; same-host redirect policy unchanged, each hop
  re-tunnels to the same validated host); connect 10s / read 30s
  timeouts separately enforced (CONNECT + TLS handshake run under the
  connect budget, matching the direct path's semantics); 64 MiB body
  cap; byte-exact non-200 passthrough; sanitized exceptions with no
  chaining (`raise ... from None`); the adapter still emits no logs.

## 2. Proofs (persisted; suite 41/41 PASS)

Evidence: `td_transport_adapter/test_evidence_sentinel_proxy_20261014/`
(`results.json` sha256 `2731b191…`, `test_output.txt` sha256
`27012c5f…`). Environment: Python 3.12.3; pinned venv rebuilt from
`integration_requirements.lock` (pandas 2.2.3,
pandas_market_calendars 4.5.1). All 27 pre-existing proofs + the 5
-06 dispatch-gate proofs pass unchanged (32/32 prior set intact).

New `ProxyLevel` proofs (9) — local recording CONNECT proxy + local
TLS targets (test CA reaches the adapter only via `SSL_CERT_FILE`,
the same platform mechanism as the production egress bundle); a
`DialRecorder` tripwire on `socket.create_connection` attributes
every TCP dial (the test proxy dials upstream on a raw socket, so
recorded dials are the adapter's alone):

1. `test_proxy_happy_path_one_connect_one_request_apikey_last` —
   exactly one `CONNECT vendor.test:<port>` line, exactly one
   upstream dial, adapter dialed ONLY the proxy, exactly one request
   at the target with parameters in contract order and **apikey
   LAST**, 200 body passed through byte-exact.
2. `test_proxy_absent_fails_closed_zero_dials` — no proxy configured
   → `proxy_unavailable`, ZERO dials of any kind, zero target hits.
3. `test_proxy_malformed_fails_closed_zero_dials` — no-host,
   socks5-scheme, https-scheme, and non-numeric-port proxy URLs →
   `proxy_malformed`, zero dials, zero target hits.
4. `test_proxy_credentials_rejected_sanitized_zero_dials` —
   credential-bearing proxy URL → `proxy_credentials_rejected`, zero
   dials; the error text contains neither the proxy user, password,
   surrogate, nor the string `apikey`.
5. `test_proxy_connect_refused_zero_direct_target_connections` —
   proxy answers CONNECT with 403 → `proxy_connect_failed`; the
   adapter's only dial was to the proxy; proxy upstream dials 0;
   target accepts unchanged and target requests 0.
6. `test_proxy_tls_failure_after_tunnel_established` — tunnel
   established (proxy upstream dial 1) but the target presents an
   untrusted cert → `tls_failure` (verification stays ON through the
   tunnel); zero HTTP requests reached the target.
7. `test_proxy_blackhole_connect_timeout_no_retry` — proxy accepts
   TCP but never answers CONNECT → `connect_timeout` inside the
   connect budget; exactly one CONNECT line and one dial (no retry).
8. `test_proxy_read_timeout_after_tunnel` — slow target behind a
   working tunnel → `read_timeout`; one upstream dial.
9. `test_vault_surrogate_collector_round_trip_via_proxy_isolation` —
   full collector round trip via the production vault binding (authd
   fetch stubbed to a fake surrogate) through the proxy to the TLS
   target: outcome COMPLETE, one CONNECT, one upstream dial, one
   adapter dial (the proxy), target saw the surrogate LAST; then the
   secret-isolation byte-scan over every runtime artifact (state,
   receipts, lifecycle, ledger): no surrogate, no fixture key, and
   no `apikey` string in any `.json`/`.jsonl` artifact.

`assert_clean_error` additionally byte-checks every new failure
category's `str`/`repr` for the surrogate, fixture key, proxy
credentials, proxy/target hosts, and `apikey` — all clean.

**Probe update** (`sentinel_probe.py`, sha256 `84641245…`; results
`test_evidence_sentinel_proxy_20261014/sentinel_probe_results.json`,
sha256 `3f8afbfd…`): static evidence now records the getproxies /
set_tunnel support; dynamic construction interception (recorder
classes, no socket ever created) shows the vendor-host construction
is DIRECT with no tunnel for a fixture key, and addressed to the
environment-configured proxy with `set_tunnel("api.twelvedata.com",
443)` for a surrogate. Verdict: `direct_path_receives_substitution`
still **false** (the -06 finding stands for the direct path);
`surrogate_requests_route_via_connect_proxy` **true**;
`fixture_key_requests_stay_direct` **true**.

## 3. Repair pass (disclosed)

First suite run: 37/41 — every tunneled case returned
`protocol_error`. Root cause was in my new code, not the harness:
the proxy branch keyed the connection class on the PROXY scheme, so
an HTTP proxy produced a plain `HTTPConnection` with a tunnel — the
request then went through the tunnel in cleartext and the TLS
target dropped it. (A standalone manual-tunnel check isolated this
in one step.) Fix: the connection class follows the TARGET scheme
(`HTTPSConnection` addressed to the proxy + `set_tunnel`, letting
http.client tunnel-then-wrap), and proxy-scheme validation tightened
to plain `http` only (see §1). Second run: **41/41**. Test changes
in the repair were limited to adding the https-scheme proxy URL to
the malformed variants. No prior proof was altered.

## 4. Pins (corrected set)

| Artifact | sha256 |
|---|---|
| `td_transport_adapter/td_http_transport_adapter.py` (CORRECTED, v1.1.0) | `ae8f4837b3d11a53990cfd56f207d5ec96c40b8fe4c1280f15fb08452cc43343` |
| `td_transport_adapter/driver.py` (unchanged) | `671f4d0ce25a76bc4967f1ca8cbb16fcda037f0e0ce71529c2aa385dce33fed1` |
| `td_transport_adapter/test_transport_adapter.py` (updated) | `b7fa2dc922ac0395171bb25a033d2c78d1a53ea0d962f169eee142bf0cf8e1c9` |
| `td_transport_adapter/sentinel_probe.py` (updated) | `8464124554662ad14860c8d540dd3d04d0024456ba6f965dc1b98701f4a24d02` |
| `test_evidence_sentinel_proxy_20261014/results.json` (41/41) | `2731b1911678c99e6727e3a0c522dcf41c7fdd09a83aaf031620cf08237f4c14` |
| `test_evidence_sentinel_proxy_20261014/test_output.txt` | `27012c5f9fcc650e76e878d675d2cc44067970581dd23fbe78329171114cda17` |
| `test_evidence_sentinel_proxy_20261014/sentinel_probe_results.json` | `3f8afbfd660cb1c9c51825b162f0b27ae5ac5e6840c696889f8b52254fe39f49` |
| Live credit ledger (UNCHANGED, checkpoint) | `ce515aa6fd53b297b693762e4236b2ea203874641ce745e482ba76daf1a67c59` |
| Collector pin (unchanged) | `bd003c3cd5866172c04b0165d6ee60ec16be8487f28e90b4e6e1df046f8d489b` |
| Limiter pin (unchanged) | `06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64` |

Prior evidence directories (`test_evidence/`,
`test_evidence_vault_binding_20261014/`,
`test_evidence_combined_preflight_20261014/`) are preserved untouched.

## 5. Updated combined-tree plan (supersedes -06 §3.1 Side B pins)

The -06 order of operations is unchanged; only the Side B bytes move:

1. **Land Side B first** — now: driver `671f4d0c…` (unchanged),
   adapter **`ae8f4837…`** (was `85c67977…`), test suite
   **`b7fa2dc9…`** (was `b758d5e5…`), probe **`84641245…`** (was
   `59468511…`), plus the -06 preflight note and this result note.
   The other Side B pins (limiter, validate_input, verify_sources,
   manifest, contract) are unchanged from -06 §3.1.
2. **Re-run the merge simulation** against the new `main`
   (`git merge-tree --write-tree main
   origin/research/td-lifecycle-repair-20261012` must exit 0, no
   conflicted files). Path sets remain disjoint (this task touches
   only `research_notes/td_transport_adapter/*` + this note), so the
   -06 clean result is expected to carry over; the re-run is the
   verification.
3. **Land Side A** — cherry-pick `411457d` + `f64d12f` (recommended
   in -06 §3.3-C1) or merge PR #8 if GitHub's state clears.
4. **Post-land verification** (all offline), updated for the new
   bytes: collector loads at pin `bd003c3c…`; adapter suite **41/41**
   in the combined tree (was 32/32 in -06); pinned-integration suite
   16/16 with the pinned venv; live ledger sha256 unchanged
   (`ce515aa6…`).
5. **Documentation supersession** as in -06 step 5, plus: the -06
   note's §2 blocker text is historical — the correction it named as
   resolution (a) is this task; do not edit the -06 note.

Blocker ledger after this task: #1 raw-key bypass CLOSED (-06);
**#2 Sentinel — adapter-layer correction implemented and proven
offline; closes fully only when the §4 screen (or equivalent first
live request) returns the -06 one-step verdict on the wire**; #3
combined tree — plan updated above, landing still separately
authorized. Conflict register C1–C5 from -06 is unaffected.

## 6. Residual risks / notes

- **Substitution itself is still unproven on the wire.** Everything
  here is construction- and loopback-level proof against the
  documented egress mechanism. The §4 screen remains the decisive
  one-step check and remains gated.
- **CONNECT exposes the target authority** (host:port) to the proxy —
  inherent to CONNECT and to the sanctioned-egress design; the
  query string (and the surrogate) stays inside TLS.
- **`proxy_connect_failed` classification keys on http.client's
  OSError text** ("Tunnel connection failed"). On this environment's
  pinned Python (3.12.3) it is exact; a future stdlib wording change
  would coarsen refused-CONNECT to `connection_error` — still
  fail-closed, only the token would lose precision.
- **HTTPS-scheme proxies fail closed** (`proxy_malformed`): if the
  sanctioned egress ever changes to a TLS proxy, this adapter needs
  a new correction rather than a configuration change.
- **Same-host redirects re-tunnel per hop** (each hop re-resolves and
  re-CONNECTs); bounded by the unchanged MAX_REDIRECTS=3 within the
  single attempt, and any hop's proxy failure fails the whole
  request closed.
