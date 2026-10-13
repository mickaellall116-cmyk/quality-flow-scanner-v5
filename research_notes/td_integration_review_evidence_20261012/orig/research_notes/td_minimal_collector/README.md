# Twelve Data Minimal Collector — QF-TD-MINIMAL-COLLECTOR-20261012-01 r1

**Spec:** GitHub Issue #1 comment 6125163484 (ChatGPT work order).
**Authorization:** Mike, direct, main chat 2026-10-12 12:48 ET — "Proceed
with Twelve Data task 6125163484 under the 60-minute budget." (Relays of
this approval were held four times; this build ran only on Mike's direct
word.)
**Budget:** 60 minutes total, hard stop, no second repair allocation.

## What this is

An ISOLATED, reduced-scope collector built from the accepted fd03906
pilot-harness modules (`rate_limiter.py`, `verify_sources.py`,
`validate_input.py`, `construct_4h.py` — imported and reused, not
copied or forked). It is NOT the R3 pilot wrapper and does not modify it.

**Removed from executable scope (per spec):** pagination, retries
(max_attempts = 1 for every request), REV7/REV30 revision legs.
**Not weakened:** pinned source verification, input validation,
timestamp/session checks, retention prerequisites, the shared persisted
rolling credit limiter (`pilot_harness/credit_ledger.json`, one ledger).

**Zero-call build:** this revision contains no vendor transport at all —
the only transport constructor raises `TransportDisabled`, and the
source contains no HTTP client. Dispatch logic is verified exclusively
through injected synthetic transports. **Zero Twelve Data requests,
zero credits, zero spend in this task.**

## Manifest

`manifest_reduced.json` — derived deterministically from the frozen R3
`pilot_harness/request_manifest.json`: legs PAR (20) + PAR4H (20) +
ADJ (3) + SPOT (8) = **51 requests, 51 credits if ever executed**, on the
frozen 20-symbol diagnostic universe (v7 §1; TWTR fallback rule noted,
never substituted by this collector). Every request carries: exact
identity string (symbol|endpoint|interval|window|timezone|adjust),
deterministic filename (`<request_id>.json`), credit weight 1 (pinned
evidence), `max_attempts=1`, `pagination=false`, and a
`one_response_bound_bars` derived from the pinned calendar bound
(calendar days × max bars/day: 1h→7, 4h→2), verified ≤ `outputsize`.
No silent truncation: a response at the output cap is terminal HOLD.

## Lifecycle (spec points 1–4)

- Manifest validation + `verify_directory` pinned-source verification +
  Basic entitlement/retention prerequisites (`prerequisites.json`)
  run before any dispatch; any failure blocks dispatch.
- Append-only `lifecycle.jsonl` (fsync per event) + atomic
  `pilot_state.json` (tmp + rename). States: CREDIT_RESERVED (recorded
  separately from attempt count) → STARTED (attempt=1) → RECEIVED
  (write-once receipt, SHA-256 recorded) → COMPLETED.
- STARTED-without-receipt on a later invocation = AMBIGUOUS → terminal
  HOLD, never auto-recalled. Receipt reuse only after exact
  hash/bytes/params/identity (meta symbol/interval) verification.
  Corruption, foreign, stale, or malformed receipts fail closed.
- Any error, incomplete coverage, or output-cap uncertainty =
  persistent terminal HOLD across invocations. Rejected payloads are
  preserved privately (bytes + hash) where retention permits.
- Bars validate through the accepted `validate_input.validate()` path
  with a mandatory tz-aware as-of. Session-aligned 1H→4H construction
  is **HOLD / INSUFFICIENT**: no officially sourced interval-start
  semantics exist in evidence (Stage-0 report; amendment A6.1), so
  construction never runs in this revision; native 4H is diagnostic
  only. Decision-impact warmup is likewise **HOLD / INSUFFICIENT**
  (unproven) — the PAR window includes the warmup acquisition span, but
  no decision-impact claim is made.

## Verification (spec point 5)

`tests/test_td_min_collector.py` — **26/26 PASS**
(`tests/synthetic_test_output.txt`): valid completion/reuse;
no-overwrite + foreign receipt; stale (hash) and malformed receipts;
crash after STARTED; persistent terminal error across restart;
missing/truncated (output-cap) response; HTTP/API/meta-binding
failures; limiter refusal; invalid manifest (retry/REV/bound);
session + as-of boundary checks through the accepted validation path;
zero-call source guarantee.

**Environment note:** the system Python lacks `pandas_market_calendars`
(the pilot harness's pinned dependency). Tests were executed in a
throwaway venv with the harness's own pinned `requirements.txt`
(pandas 2.2.3, pandas_market_calendars 4.5.1). No repo environment was
changed. Exact commands:

```
python3 td_min_collector.py validate-manifest   # manifest_errors: []
python3 td_min_collector.py preflight           # failures: [], dispatch BLOCKED (zero-call)
python3 tests/test_td_min_collector.py          # 26/26 (venv python, see above)
```

## Limitations (explicit, per spec)

Passing this collector's synthetic verification **cannot** establish:
revision stability of vendor data, corporate-action fidelity,
decision-impact warmup sufficiency, complete C1 parity, or strategy
edge. It also cannot establish: interval-start semantics (INSUFFICIENT),
the corporate-action endpoint leg (unnamed, weight unevidenced — out of
scope), C4 retention beyond the bounded, user-supplied-provenance
record, or any entitlement beyond the recorded Basic evidence. Pilot
execution itself remains gated (P4 clearance + Mike's authorization
for any actual vendor call) and is NOT performed by this revision.

## Effort (60-min ceiling)

- Implementation (manifest generation, collector, prerequisites): ~14 min
- Synthetic verification (incl. one defect found & fixed — string-OHLC
  numeric conversion before the accepted validation path — and a
  throwaway pinned-deps venv): ~11 min
- Packaging (README, registry, commit): ~8 min
- **Total: ~33 min of 60. Zero vendor calls. Zero credits. Zero spend.**
