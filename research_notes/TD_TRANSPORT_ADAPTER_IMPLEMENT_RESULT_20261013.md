# TD Transport Adapter — Implementation Result — 2026-10-13

Task: QF-TD-TRANSPORT-ADAPTER-IMPLEMENT-20261013-03 r1 (Issue #1 comment
6159623983), under Mike's 2026-10-13 standing rule (Muse↔ChatGPT loop
auto). Builds ONLY the pinned adapter from the CONDITIONAL-PASS preflight
(`TD_ACQUISITION_ADAPTER_PREFLIGHT_20261013.md` /
`adapter_contract.json` sha256 `db6c44a2…`) plus its driver binding.
**Synthetic/local test servers only. Zero authenticated vendor calls,
zero credits, zero spend, no PR merge, no performance claims, no
baseline work.**

## Verdict

**BUILT AND PROVEN LOCALLY — 20/20 tests PASS** against self-hosted
127.0.0.1 HTTP/HTTPS test servers, with the accepted collector (pinned
bytes `bd003c3c…`, extracted from `f64d12f` and sha-verified in-suite)
and the real shared persisted limiter (`rate_limiter.py` `06ad383d…`).
Full output persisted: `test_evidence/test_output.txt`,
`test_evidence/results.json`.

## What was built (`research_notes/td_transport_adapter/`)

| File | sha256 | Role |
|---|---|---|
| `td_http_transport_adapter.py` | `85c67977d176e36135751e588cc81d1bb1f21e56821189796cf87bdaab389d31` | `td-http-transport-adapter` v1.0.0, stdlib `http.client` only |
| `driver.py` | `198b733bb3f4cdc389057303e543a63e25aab7bce813a825133c621c7387cf24` | Collector/limiter/adapter binding; pin-enforcing loader |
| `test_transport_adapter.py` | `4085b28615fb56802066ca08ed7ec816e8e2f8c5a67760f3b6aabafef1b0a44d` | 20-test synthetic proof suite |
| `test_evidence/results.json` | `9450c752220c1baf203ed124ad22ae9619b673d11ea1d9c44a2feea3c1397889` | Machine-readable run record (0 vendor calls, 0 credits) |
| `test_evidence/test_output.txt` | `eea411e083b03aafc15cec28539c3a1a78bf27fc4cc93299c31e8bb488e8d6e0` | Full test transcript |

Adapter design, per contract: `transport(req) -> (status, body)`; GET
with parameters in the pinned fixed order (symbol, interval, start_date,
end_date, timezone, outputsize, order, adjust, format=JSON, apikey
last), values verbatim from the manifest request; venue parameters never
sent; HTTPS-only with certificate verification on (plain HTTP accepted
only for loopback test origins); connect 10s / read 30s enforced
separately; 64 MiB body cap; exactly one attempt — no retries at any
layer; same-host redirects followed (≤3) inside the single attempt,
cross-host/downgrade redirects fail closed; the adapter emits no logs.

Driver binding: refuses to load collector bytes that do not hash to the
accepted pin (and re-verifies the limiter pin); constructs
`RollingCreditLimiter(credits_per_minute=8, daily_cap=800)` with
`state_path` defaulting to the contract path
`research_notes/pilot_harness/credit_ledger.json`; key sourced from the
environment (vault-style stand-in for `custom.twelvedata`), memory only;
`semantics_status="INSUFFICIENT"` per ruling R3. Tests passed a scratch
ledger — **the live ledger is byte-identical before/after**
(sha256 `ce515aa6…`, still the Stage-0 2-credit record).

## What each proof establishes (all 20 in `test_output.txt`)

- **Secret isolation.** Key arrives at the server only as the `apikey`
  query parameter (server records parameter names/order + a match
  boolean, never the value). After a full collector round-trip, every
  runtime artifact produced (state dir, receipts, lifecycle log, ledger)
  was byte-scanned: no key, and no `apikey` string in any JSON/JSONL
  artifact. Exception strings/reprs contain neither the key, the
  parameter name, the host, nor any URL. The fake key exists as a
  literal only in the test source, never in outputs.
- **Parameter construction.** Recorded parameter order at the server
  equals the contract order exactly; values match the request.
- **One attempt, no retries.** Server hit counters: 429 → 1 hit,
  500 → 1 hit, slow/timeout → 1 hit, body-cap → 1 hit. No code path in
  the adapter repeats a request.
- **Non-200 passthrough.** 429 and 500 return `(status, body)` byte-exact
  to the collector; a 200 with `status:"error"` passes through as body.
  At collector level, the 429 run HOLDs with `HTTP 429`, preserves the
  body byte-identical as `AAPL_FIXTURE.rejected.bin`, emits
  ERROR_EVIDENCE, and dispatches exactly once.
- **Sanitized exceptions.** Every failure raises `TransportError` whose
  message is a bare category token (`read_timeout`, `connection_error`,
  `tls_failure`, `body_cap_exceeded`, `redirect_rejected`,
  `malformed_request`); underlying exceptions are never chained
  (`from None`), so tracebacks cannot leak URLs or headers.
- **Timeouts.** Read timeout enforced behaviorally (0.5s budget vs 3s
  server delay: raised `read_timeout` in <2.5s); pinned defaults
  asserted at exactly 10s/30s. Connect-side: refusal raises
  `connection_error`; the unroutable-address probe fails closed,
  sanitized, in bounded time (see limitation L1).
- **TLS.** A local HTTPS server with a self-signed certificate is
  REJECTED (`tls_failure`) — verification is on. Cross-host redirect is
  rejected before any request reaches the other host (its hit counter
  stayed 0); same-host redirect is followed to the 200 body.
- **Shared persisted limiter.** Scratch ledger at the contract file
  name: after 8 credits are granted in one process, a NEW python
  process (true restart) is refused and reads `daily_spent == 8` from
  the persisted file; a collector run against the exhausted ledger ends
  REFUSED with a LIMITER_REFUSED event and **zero** server hits.
- **Full synthetic round-trip.** Driver-built collector + adapter +
  local server: outcome COMPLETE, receipt bytes byte-identical to the
  served validated payload, lifecycle shows CREDIT_RESERVED → STARTED →
  RECEIVED → COMPLETED (+CONSTRUCTION_HOLD under INSUFFICIENT
  semantics), ledger spent = 1, exactly 1 server hit; a second run
  reuses the receipt with no further call.

## Limitations / remaining live risks (exact)

- **L1 — True connect-timeout not producible in this sandbox.** The
  unroutable-address probe terminated at the TLS layer (sandbox egress
  behavior), so the locally observed category was `tls_failure`, not
  `connect_timeout`. The connect budget IS wired (socket timeout set
  before connect; phase-tracked category exists and is unit-shaped),
  but a genuine SYN-drop connect timeout against the real vendor origin
  has not been observed and cannot be without a vendor call.
- **L2 — Vendor redirect behavior unknown.** Whether
  api.twelvedata.com ever redirects is unobservable offline. The policy
  follows the contract either way (same-host only, fail closed
  otherwise); if the vendor cross-host redirects in production, the
  first live run would fail closed at that request — by design, with
  evidence preserved, not silently.
- **L3 — TLS proven by rejection only.** No locally trusted certificate
  chain to the real vendor CA exists offline; what is proven is that
  verification is ON and rejects an untrusted chain. A successful live
  TLS session is unproven by construction of this task.
- **L4 — Body-cap proof used a reduced cap** (1 KiB vs 4 KiB body, plus
  the 64 MiB default asserted). The read path is identical; a live
  64 MiB+ response is not expected (5000-bar JSON is far smaller).
- **L5 — PR #8 still unmerged.** The driver binds the collector at the
  contract path `research_notes/td_lifecycle_repair_candidate/`; on this
  branch that path does not yet exist, so the suite exercised a
  byte-identical, sha-verified copy extracted from `f64d12f`. Once PR #8
  merges, the same driver loads it in place with no changes.
- **L6 — Live-account standing, real 429 semantics, and empirical
  interval semantics remain exactly as the preflight recorded them**
  (INSUFFICIENT; protocol P2 on real receipts only). Nothing here
  upgrades any semantics, qualifies the feed, or authorizes acquisition:
  any vendor call still requires the standing authorization path.

## Effort

Inside the 60-minute cap, including the one ≤15-min repair pass (first
run 19/20: the connect-probe category expectation was widened after the
sandbox's TLS-layer termination was observed, and the limitation is
recorded as L1 rather than hidden). Zero vendor calls, zero credits,
zero spend. No collector, harness, frozen, or production code modified;
the registry and the live credit ledger were not touched. Commit-ready
only (not committed).
