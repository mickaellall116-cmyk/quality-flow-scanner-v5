# Twelve Data Pilot — Readiness R3 (2026-10-10)

**Task:** QF-TD-PILOT-READINESS-R3-20261010-06 (Issue #1 6099318779)
**Builds on:** c56dd48 / e5c101b (R2 readiness packet, wrapper, fixtures)
**Budget:** 45-min cap, one pass. ZERO vendor calls, ZERO new credits, ZERO performance computations.
**Actual effort:** ~38 min (code+manifest+fixtures ~30, doc ~8).

## Defect fixes (r2 adjudication defects 1–11)

1. **Warmup restored (exact v7 rule).** PAR-1H/4H bounds now `2026-04-01T00:00:00` → `2026-10-06T23:59:59` (v7 §2a/§2d: 1H acquisition from 2026-04-01 covers the 215-4H-bar warmup with margin). ADJ bounds extended with the preregistered 215-4H-bar (≈108-session) warmup per v7 §2b:
   - REQ-ADJ-01 NVDA: `2023-12-13T00:00:00` → `2024-06-21T23:59:59`
   - REQ-ADJ-02 TSLA: `2022-03-07T00:00:00` → `2022-09-09T23:59:59`
   - REQ-ADJ-03 AAPL: `2026-02-19T00:00:00` → `2026-08-24T23:59:59`
   All warmup spans fit outputsize 5000 (longest ≈ 240 sessions × 7 ≈ 1680 bars). Decision-impact stays gated (INSUFFICIENT unless separately pinned init rule).

2/12. **Budget: ONE non-overlapping formula.** `total_calls = base_requests + pagination_pages + retries`, each call counted exactly once. PAG max (40) excludes PAR base calls (r2 double-count withdrawn).
   - Base 91 (PAR 40 + ADJ 3 + SPOT 8 + REV7 20 + REV30 20); PAG pages ≤ 40; retries ≤ 40 (pilot-wide).
   - Expected 91 / max 171 (+2 Stage-0 spent, tracked separately).
   - Day maxima: D0 40/80, D1 11/91 (11 base + 40 PAG + ≤40 retries, global cap shared), D7 20/60, D30 20/60.

3. **Machine-readable manifest + enforcing driver.** `research_notes/pilot_harness/request_manifest.json` (91 base requests, stable unique IDs, no ranges; REV rows carry `base_request_id`). `ManifestDriver` (in `pilot_acquire.py`) enforces at load: unique IDs, datetime-precision bounds, output paths inside the store (no traversal), day/leg membership; at run: revision-to-base receipt linkage (fail-closed), deterministic PAG creation (trigger: parity-1H snapshot has exactly `outputsize` rows AND earliest datetime > requested start — max 2 extra pages/symbol, IDs `REQ-PAG-<SYM>-<nn>`), retry totals via the shared `RetryBudget`.

4. **HTTPError boundary fixed.** `UrllibTransport.fetch()` now catches `urllib.error.HTTPError` separately and returns `(status, scrubbed_headers, body)` — 401/403/404/429/5xx reach their advertised branches. Only true timeout/connection errors (`URLError`, `TimeoutError`, `ConnectionError`, `OSError`) become `TimeoutError`. Fixture W11 (monkeypatched urlopen) proves both paths.

5. **Shared retry counter implemented.** `RetryBudget(cap=40)`; every retry (attempt > 1) consumes one; exhaustion → `RETRIES_EXHAUSTED`. No longer documentation-only. Fixture W13.

6. **Crash-safe resume.** Completion marker = receipt file whose `sha256`/`bytes`/`params` all verify against the snapshot. Snapshot without valid receipt = orphan → quarantined (`<name>.orphan.<ts>`) and refetched; never silently `SKIPPED_RESUMED`. Fixtures W02/W03/W12. The old W02/W03 "skip pre-existing snapshot" expectations were updated to the new fail-closed semantics.

7. **Durable attempt receipts.** `<request_id>.attempts.jsonl`, append-only, one line per attempt: attempt #, UTC-ms times, HTTP status, bytes, SHA-256, allowlisted scrubbed headers (content-type/length, date, retry-after, x-ratelimit-*), event class. No key material. Fixture W19.

8. **429 semantics exact.** `consecutive_429` resets on any non-429 attempt; the rolling 10-min window counts DISTINCT request IDs (`_429_events` stores `(ts, request_id)` pairs). Fixture W17 (reset case + 3-distinct-429 window stop).

9. **Schema binding.** `meta.symbol` and `meta.interval` must equal the request's symbol/interval; a status-ok payload for another symbol/interval → `SCHEMA_QUARANTINE`. Fixture W18. (Bar-level validation stays in the cleared `pilot_build.py` chain.)

10. **Pacing frozen.** On `LEDGER_REFUSED` the driver EXITS (no busy-wait); resume is a fresh invocation that skips completed requests via verified completion markers. Fixture W16: refusal mid-list → exit → fresh-window resume → all 3 requests complete exactly once, zero lost/duplicated.

11. **ADJ warmup claims reconciled.** Bounds extended per v7 §2b (see defect 1); no silent scope expansion — the extension is the frozen preregistered rule, documented here.

## Pins

- Wrapper `pilot_acquire.py`: r3 rewrite (r2 blob `a6d2570ff…` superseded)
- Fixtures: `tests/test_acquisition_wrapper.py` **10/10 PASS** (W02/W03 updated to orphan semantics), `tests/test_acquisition_wrapper_r3.py` **9/9 PASS** (W11–W19)
- Manifest: `research_notes/pilot_harness/request_manifest.json` (`TD-PILOT-MANIFEST-R3-20261010`, 91 requests, budget formula machine-checked by driver)
- No fd03906 fixture modified. Zero vendor calls/credits/performance.

## Remaining gates (not cleared by this packet)

- **P4 (ChatGPT spec clearance)** — no pilot execution authorized by this packet.
- Corporate-action endpoint leg: INSUFFICIENT, excluded from manifest.
- Decision-impact (C2): INSUFFICIENT unless separately pinned init rule.
