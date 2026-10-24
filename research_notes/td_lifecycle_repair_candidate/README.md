# Offline lifecycle repair candidate — October 12, 2026

Based on failed collector commit `411457df87595f908906c899043d21a76ae2cea1` and reviewer findings `6129566895`. This is a separately reviewable candidate, not acceptance or vendor execution clearance. Transport remains disabled. Original failed artifacts and all adverse results are preserved.

## Concrete changes

- RECEIVED never implies COMPLETED. A dispatched request lacking durable validated completion becomes HOLD on restart; no automatic repeat request.
- Persisted canonical manifest digest binds all request fields. Reuse also binds receipt hash/length, request digest, manifest digest and durable completion; bytes are revalidated.
- Every `Collector.run()` path checks manifest, source pins and entitlement/retention evidence before any dispatch.
- An exclusive nonblocking whole-run process lock protects state reconciliation, dispatch and receipts; state is reloaded under the lock.
- Explicit exchange/currency venue identity is required. Malformed response objects fail to HOLD with retained private evidence.
- Native 4H uses structural diagnostic validation, never the 1H constituent-completeness validator. A diagnostic completion is explicitly scoped, not feed qualification.
- Unbound legacy state is refused, not silently migrated or overwritten.
- Transport exception details are omitted from lifecycle reporting to avoid recording credential-bearing URLs.

## Validation actually performed

`python3 test_lifecycle_repair.py` — 19/19 PASS. Python compilation also passed. Tests exercise receipt/restart lifecycle, exact request changes, interrupted validation, prerequisite/source gating, corrupt/unbound state, malformed responses, venue mismatch, native-4H structural checks and contention against a separate process holding the same state lock. `test_output.txt` records output.

IMPORTANT: accepted source-verification, limiter and 1H-validator dependencies are stubbed in these probes to isolate lifecycle logic. The native-4H structural branch uses actual installed pandas/numpy. No vendor calls occurred. This test result is not full dependency integration or execution readiness.

## Required independent integration review before any acquisition

1. Resolve this directory's sibling `pilot_harness` dependencies against immutable accepted pins; do not import current unpinned copies.
2. Supply separately reviewed prerequisites and explicit venue manifest. The old manifest intentionally fails the new venue gate. Do not blindly infer ticker/exchange identities or alter acquisition windows.
3. Exercise actual accepted source verifier, shared persisted limiter and 1H validation under pinned dependencies. This environment lacks pandas_market_calendars; full calendar integration was not run.
4. Verify receipt response exchange/currency values against the provider's documented identities; unknown identity must HOLD, not be assumed.
5. Independently inject failure at receipt/event/state-write boundaries and verify no invalid completion, double dispatch or stale-manifest reuse. Test changed date/adjust/timezone/order/outputsize/venue and corrupt lifecycle records.
6. This code has no HTTP client. A real acquisition adapter needs separate reviewed redaction/timeout/retention/account integration before enabling calls.

The design trades automatic recovery for safety: interrupted requests remain HOLD. Manual review can recover validated evidence separately, but this candidate never reissues ambiguous attempts. Native 4H diagnostics do not validate expected session coverage. P4 remains HOLD until independent integration review, and full pilot/CP2/performance/Tiingo/production/holdout boundaries remain unchanged.

## Next work, already concrete

Review this candidate instead of commissioning another broad collector rewrite. Accept or reject against the enumerated original failures. If actual dependency integration reveals a blocker, report its exact counterexample and stop; do not reopen unlimited repair cycles.
