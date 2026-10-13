# Independent integration review — Twelve Data collector lifecycle repair candidate

- **Candidate:** PR #8, commit `af49bf4a65acca08876a4bd9823a945ca8aa3d17`, directory `research_notes/td_lifecycle_repair_candidate/` (based on failed collector `411457d`).
- **Authorization:** Mike, direct, main chat 2026-10-12 22:07 EDT ("Yes do whatever chat got says") for this review assignment (Issue #1 comment `6135218247`).
- **Limits honored:** zero vendor calls / zero credits / zero spend; no HTTP adapter used (transport was an in-process callable returning synthetic bytes); no merge; no production or frozen-code changes; candidate and original `411457d` files untouched — all execution happened in scratch copies under `/tmp/tdreview/`.
- **Reviewer:** Muse (independent of the candidate's author-side tests; the candidate's own 19 tests stubbed every accepted dependency — this review used the actual ones).

## Environment and dependency pins (all verified before running)

Scratch tree assembled at `/tmp/tdreview/run/research_notes/` with `pilot_harness/`, `td_lifecycle_repair_candidate/`, and `recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/` as siblings (the layout the candidate's imports expect). Every file's git blob SHA was checked against the pinned commits:

| Module | Pin source | Blob SHA | Scratch copy |
|---|---|---|---|
| `pilot_harness/verify_sources.py` | `fd03906` | `0732b1f48f34d867c86d1cfd9ccddca864f12bb3` | MATCH |
| `pilot_harness/validate_input.py` | `fd03906` | `74424d2a41bc86a334f3525801aa899082953f4d` | MATCH |
| `pilot_harness/rate_limiter.py` (`RollingCreditLimiter`) | `fd03906` | `bf8a7db115a272029035dfb09905d1962f3dfebc` | MATCH |
| `pilot_harness/construct_4h.py` | `fd03906` | `fe76c48a22514e073e232811880fd82d963e54f1` | MATCH |
| candidate `td_min_collector.py` (+ tests, README) | `af49bf4` | per-commit blobs | MATCH |
| archival `pine_backtest.py` | `verify_sources.PINNED` (SHA-256) | `447a9a13…d160e5` | MATCH |
| archival `scanner_rules.py` | `verify_sources.PINNED` (SHA-256) | `7db282df…0cac` | MATCH |

(The `fd03906` pilot-harness blobs are byte-identical to those carried in `411457d`, so pins resolve unambiguously without moving `main`.)

Environment: Python 3.12.3, pandas 2.1.4, numpy 1.26.4, pytest 9.1.1. **`pandas_market_calendars` is NOT installed** (`ModuleNotFoundError`) — see coverage gap below. Prerequisites file: the original `411457d` `prerequisites.json` (plan Basic, retention `BOUNDED_RESOLVED`, 30-day condition recorded). Limiter: real `RollingCreditLimiter(8, 800, state_path=<scratch ledger>)`, persisted per scenario. Manifests: explicit venue manifest (`venue_identity = {exchange: NASDAQ, currency: USD}` on every request, canonical `identity` strings, `one_response_bound_bars` derived per the candidate's own rule).

## Commands run

```
git fetch origin pull/8/head:refs/review/pr8
git archive af49bf4… research_notes/td_lifecycle_repair_candidate | tar -x -C /tmp/tdreview/cand
git archive 411457d research_notes            | tar -x -C /tmp/tdreview/orig   (pilot_harness, td_minimal_collector)
git archive origin/main research_notes/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1 | tar -x -C /tmp/tdreview/run
python3 /tmp/tdreview/run_integration.py      # scenarios S0, S0b, a, b1, b2, c, d, f, g (actual deps)
python3 <inline driver>                        # scenario h against a tampered copy of the tree
```

## Results per counterexample

Control (S0): a native-4H request with a valid synthetic payload completed end-to-end through the real preflight (actual `verify_directory` against the real archival pins) and the real persisted limiter: `{"dispatched": 1, "reused": 0, "completed": 1, "outcome": "COMPLETE"}`. Restart with the identical manifest (S0b): `{"dispatched": 0, "reused": 1, "completed": 1, "outcome": "COMPLETE"}` — legitimate reuse still works.

**(a) Crash after RECEIVED, before validation — PASS.**
`_validate_bars` was replaced with a raising stub in the harness process only (simulating a crash); events before restart were exactly `CREDIT_RESERVED, STARTED, RECEIVED` with receipt bytes on disk and no `COMPLETED`. After restart with the real validator: `{"dispatched": 0, "reused": 0, "completed": 0, "outcome": "HOLD (persistent): AMBIGUOUS: REQ-P4H-01 dispatched without durable validation completion; no redispatch"}`. The interrupted request can never reach COMPLETE across this boundary — the exact defect that failed `411457d` is closed.

**(b) Changed request parameters on the same request_id — PASS (two layers).**
Manifest level (b1): against a completed state, changing any one of `start_date`, `adjust`, `order`, `outputsize`, or venue `exchange` in the manifest was refused for all five variants with `CollectorError: manifest binding changed; refusing receipt/state reuse` — no reuse, no dispatch. Receipt level (b2): with the on-disk binding file pre-swapped to the changed manifest's digest (so only the receipt check could catch it), the run returned `HOLD: receipt request/manifest binding mismatch`, `reused: 0`.

**(c) Concurrent second process — PASS.**
A separate OS process held `flock(LOCK_EX)` on the state directory's `collector.lock`; `run()` was refused with `CollectorError: another collector owns the state directory`, zero `STARTED` events were written, and the shared limiter ledger recorded no dispatch.

**(d) Malformed payload (JSON list instead of object) — PASS.**
No exception escaped; outcome `HOLD: malformed response object/meta for REQ-P4H-01`, state persisted as HOLD, and the raw payload was preserved as `receipts/REQ-P4H-01.rejected.bin` with an `ERROR_EVIDENCE` lifecycle event.

**(e) Native 4H routing — PASS.**
With the actual `validate_input.validate` temporarily bombed to raise if ever called, the native-4H request still completed, `validate` was never invoked, and the `COMPLETED` event records `validation_scope: native_4h_structural_diagnostic`. Native 4H takes the structural diagnostic path (finite OHLCV, geometry, window bounds), never the 1H completeness validator — and completion is explicitly scoped as diagnostic, not feed qualification.

**New counterexamples found by this review:**

- **(g) Receipt byte tamper, same length — PASS (no defect).** Flipping one byte of a completed receipt (length preserved) and restarting yields `HOLD: receipt hash mismatch vs lifecycle record (stale/corrupt)`, `reused: 0`.
- **(h) Pinned-source tamper — PASS (no defect).** Appending one byte to the scratch copy of `scanner_rules.py` makes the **actual** `verify_sources` fail preflight before any dispatch: `CollectorError: dispatch preflight failed: source: HASH MISMATCH: scanner_rules.py (expected 7db282ddfc150c9e…, got 57d0dbf3168590da…)`.

## Coverage gap (explicit)

**(f) The actual 1H calendar validation path cannot be exercised in this environment.** `validate_input.validate` imports `pandas_market_calendars` lazily inside `xnys_schedule`; the package is not installed here. A 1H request with well-formed synthetic bars therefore ends `HOLD: validation failed for REQ-P1H-01: No module named 'pandas_market_calendars'` — fail-closed (nothing silently completes), but the real XNYS session-completeness behavior (the seven-constituent check) is **unverified by this review**. No stub was substituted for it. Closing this gap requires an environment with `pandas_market_calendars` installed and a rerun of the 1H scenarios, including a causally-partial and an incomplete-session case.

Nothing in this review tested: any HTTP behavior, vendor response shapes beyond the synthetic payloads used, credit accounting against a real account, or the venue identities against provider documentation (README item 4 remains open). The candidate has no HTTP client by construction, so transport enabling still needs its own separately reviewed adapter.

## Verdict

**PASS (scoped): the repair candidate closes all five adjudicated `411457d` lifecycle defects under the actual pinned dependencies, with the 1H calendar-validation path explicitly UNVERIFIED due to the missing `pandas_market_calendars` dependency in this environment — acquisition and any vendor calls remain HOLD pending that integration and separate transport review.**
