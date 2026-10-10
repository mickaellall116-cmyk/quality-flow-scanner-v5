# Twelve Data Pilot — Readiness Packet R2 (2026-10-10)

**Task:** QF-TD-PILOT-READINESS-R2-20261010-04 (Issue #1 comments 6098718465 / 6098722040)
**Builds on:** evidence pin 35e4063 (STAGE0_OFFLINE_REPORT_20261010.md, TD_PILOT_PACKET_AMENDMENT_20261010.md, registry blob 42c5a8efd49053b97815066ef9cfd5c0eeafff2d)
**Status:** READINESS PACKET for ChatGPT review. No pilot execution authorized by this document. P4 remains the gate.
**Budget:** 45-minute cap, one pass. ZERO vendor calls, ZERO new credits, ZERO performance computations.

---

## R1. Window reconciliation (defect 1)

- **2026-09-08 → 2026-10-06 inclusive = 21 NYSE sessions** (verified: 21 weekdays; no market holidays in range — Labor Day 2026-09-07 precedes the window). The r1 "20 trading days" is corrected; nothing is silently shortened.
- **Coverage requirement:** all 21 sessions through **2026-10-06 23:59:59** America/New_York.
- **Request-bound semantics (official source):** Twelve Data API reference, `/time_series` parameters — `start_date`/`end_date` accept `2006-01-02` or `2006-01-02T15:04:05`; "If timezone is given then, start_date and end_date will be used in the specified location." (https://twelvedata.com/docs/llms/market-data/time-series.md)
- **Empirical bound behavior (recorded, Stage-0 offline report):** date-only `end_date=2026-10-06` behaved **exclusive** (coverage through Oct 5).
- **Frozen rule:** all pilot requests use **datetime-precision bounds** — `start_date=2026-09-08T00:00:00`, `end_date=2026-10-06T23:59:59` with `timezone=America/New_York`. The wrapper records actual returned coverage per request; any shortfall vs the 21-session expectation is a recorded discrepancy, never silent.

## R2. Enumerated request manifest (defect 2)

Stable request IDs. Every request: `/time_series`, `timezone=America/New_York`, `outputsize=5000`, `order=ASC`, `adjust=splits` (official default, pinned explicit — Twelve Data docs: adjusting mode, values `all`/`splits`/`dividends`/`none`, default `splits`). Expected credits = 1 per request (official: 1 credit per symbol).

### Leg PAR — parity window 1H (day D0)

Bounds: `2026-09-08T00:00:00` → `2026-10-06T23:59:59`. 20 symbols per v7 §1.

| Request ID | Symbol | Interval | Expected credits | Max attempts | Output name |
|---|---|---|---|---|---|
| REQ-P1H-01 | AAPL | 1h | 1 | 3 | REQ-P1H-01.json |
| REQ-P1H-02 | MSFT | 1h | 1 | 3 | REQ-P1H-02.json |
| REQ-P1H-03 | NVDA | 1h | 1 | 3 | REQ-P1H-03.json |
| REQ-P1H-04 | AMD | 1h | 1 | 3 | REQ-P1H-04.json |
| REQ-P1H-05 | TSLA | 1h | 1 | 3 | REQ-P1H-05.json |
| REQ-P1H-06 | META | 1h | 1 | 3 | REQ-P1H-06.json |
| REQ-P1H-07 | GOOGL | 1h | 1 | 3 | REQ-P1H-07.json |
| REQ-P1H-08 | QQQ | 1h | 1 | 3 | REQ-P1H-08.json |
| REQ-P1H-09 | PLTR | 1h | 1 | 3 | REQ-P1H-09.json |
| REQ-P1H-10 | HOOD | 1h | 1 | 3 | REQ-P1H-10.json |
| REQ-P1H-11 | ANET | 1h | 1 | 3 | REQ-P1H-11.json |
| REQ-P1H-12 | SMCI | 1h | 1 | 3 | REQ-P1H-12.json |
| REQ-P1H-13 | SOFI | 1h | 1 | 3 | REQ-P1H-13.json |
| REQ-P1H-14 | RKLB | 1h | 1 | 3 | REQ-P1H-14.json |
| REQ-P1H-15 | NIO | 1h | 1 | 3 | REQ-P1H-15.json |
| REQ-P1H-16 | BBAI | 1h | 1 | 3 | REQ-P1H-16.json |
| REQ-P1H-17 | ONDS | 1h | 1 | 3 | REQ-P1H-17.json |
| REQ-P1H-18 | DRAM | 1h | 1 | 3 | REQ-P1H-18.json |
| REQ-P1H-19 | SPCX | 1h | 1 | 3 | REQ-P1H-19.json |
| REQ-P1H-20 | TWTR | 1h | 1 | 3 | REQ-P1H-20.json |

TWTR is **conditional** per the frozen §1 fallback rule: HTTP 404 → leg recorded C5 INSUFFICIENT (`allow_404_continue=true`), pilot proceeds at 19 symbols. All other symbols: 404 is terminal for the run.

Leg PAR expected: **20 calls / 20 credits**. Max: 20 × 3 = **60**.

### Leg PAR-4H — parity window 4H diagnostic (day D0)

Same 20 symbols, `interval=4h`, same bounds. Request IDs REQ-P4H-01..20 (TWTR conditional as above). Diagnostic only — compared against our 1H→4H construction, never qualified input. Expected: **20 / 20**. Max: **60**.

### Leg ADJ — adjustment windows 1H (day D1)

**Derived count (r1's "12" withdrawn as unexplained):** 3 corporate-action windows × 1 request each = **3**. One request suffices per window: longest span (NVDA 2024-05-20→2024-06-21, ~25 sessions) plus 215-4H-bar warmup (~108 sessions) needs ≈ 133 × 7 ≈ 931 1H bars < outputsize 5000. No pagination, no second interval.

| Request ID | Symbol | Window (bounds) | Event |
|---|---|---|---|
| REQ-ADJ-01 | NVDA | 2024-05-20T00:00:00 → 2024-06-21T23:59:59 | 10:1 split, split-adjusted trading 2024-06-10 |
| REQ-ADJ-02 | TSLA | 2022-08-10T00:00:00 → 2022-09-09T23:59:59 | 3:1 split, split-adjusted trading 2022-08-25 |
| REQ-ADJ-03 | AAPL | 2026-07-27T00:00:00 → 2026-08-24T23:59:59 | $0.27 dividend, ex-date 2026-08-10 |

Expected: **3 / 3**. Max: **9**. (C3 corporate-action-endpoint leg remains INSUFFICIENT per the amendment — these windows test bar continuity across actions, not vendor action lists.)

### Leg SPOT — DST/early-close/closed-day spots 1H (day D1)

**Derived count:** 2 symbols (AAPL, QQQ) × 4 windows = **8**.

| Request ID | Symbol | Window | Check |
|---|---|---|---|
| REQ-SPT-01 | AAPL | 2026-03-09 → 2026-03-13 | spring-forward week (DST from 2026-03-08) |
| REQ-SPT-02 | QQQ | 2026-03-09 → 2026-03-13 | spring-forward week |
| REQ-SPT-03 | AAPL | 2025-11-03 → 2025-11-07 | fall-back week (DST ended 2025-11-02) |
| REQ-SPT-04 | QQQ | 2025-11-03 → 2025-11-07 | fall-back week |
| REQ-SPT-05 | AAPL | 2025-11-28 | early close (13:00 ET) |
| REQ-SPT-06 | QQQ | 2025-11-28 | early close (13:00 ET) |
| REQ-SPT-07 | AAPL | 2026-07-03 | full holiday — expects ZERO bars |
| REQ-SPT-08 | QQQ | 2026-07-03 | full holiday — expects ZERO bars |

Bounds use datetime precision (`T00:00:00` → `T23:59:59` per window day). Expected: **8 / 8**. Max: **24**.

### Leg PAG — warmup pagination reserve (day D1, conditional)

**Deterministic trigger (pinned, not conditional-on-judgment):** a reserve request REQ-PAG-nn fires for symbol S **iff** S's parity-1H response returns exactly `outputsize` (5000) rows **and** the earliest returned `datetime` is after the requested `start_date` (truncation detected). The reserve re-requests with `end_date` set to the earliest returned bar's datetime, iterating until the start bound is covered or 3 pages total.

Expected: **0** (parity window + warmup ≈ 900 1H bars < 5000 — truncation not expected). Max: 20 symbols × (1 base + 2 pages) = 60 calls / 60 credits, each page a separately receipted request ID (REQ-PAG-01…).

### Legs REV7 / REV30 — revision re-pulls (days D7 / D30)

**Exact windows:** identical to Leg PAR (2026-09-08T00:00:00 → 2026-10-06T23:59:59), 1H only, same 20 symbols (TWTR conditional). Request IDs REQ-REV7-01..20 and REQ-REV30-01..20. Each revision request's manifest row **links to its base receipt**: `base_request_id` (e.g. REQ-REV7-01 ← REQ-P1H-01) and the base `receipt_ts_ms`. Scheduled as separate frozen days (D+7, D+30 relative to D0); no other requests share those days.

Expected per leg: **20 / 20**. Max per leg: **60**.

## R3. Budget arithmetic reconciled (defect 3)

Credits = calls (1 credit per symbol per request, official). Already spent: 2 (Stage-0).

| Day | Legs | Expected calls/credits | Max calls/credits |
|---|---|---|---|
| D0 | PAR 1H + PAR 4H | 40 | 120 |
| D1 | ADJ (3) + SPOT (8) + PAG reserve (0) | 11 | 33 + 60 = 93 |
| D7 | REV7 | 20 | 60 |
| D30 | REV30 | 20 | 60 |
| **Pilot total** | | **91** | **333** |
| + Stage-0 spent | | 2 | 2 |
| **Program total** | | **93** | **335** |

- Same-day ceilings now sum correctly because legs sit on **separately frozen days** — no day's expected load exceeds 40, no day's maximum exceeds 120.
- The r1 "peak ≤ 100/day" claim is withdrawn (its legs summed to 120 on one day).
- Hard fail-closed cap: 800/day (Basic, resets 00:00 UTC per official docs) — never binding at these loads, stated for completeness.
- Retry consumption: every retry is a call and costs a credit; counted inside the per-day maxima above. A separate pilot-wide retry budget of ≤ 40 additional calls applies (R4); hitting it stops the pilot.

## R4. Retry rule, exact (defect 4)

- **Max attempts per request:** 3 (1 initial + 2 retries).
- **Qualifying (retryable):** HTTP 429, 502, 503, 504, transport timeout/connection error.
- **Terminal (no retry):** 400 and other 4xx; 401/403 → stop entire run immediately; 404 → INSUFFICIENT leg (continue only when `allow_404_continue`, i.e. TWTR); HTTP 200 with schema break → quarantine leg + stop run.
- **Backoff:** 60 s after attempt 1, 300 s after attempt 2 (each retry re-acquires a limiter credit; refusal → stop).
- **Measurable 429 stop rule (replaces "sustained 429"):** 2 consecutive 429s on one request after backoff → stop that request and the run (RATE_STOP); 3 total 429s across distinct requests within any rolling 10-minute window → stop the run. Both are counted, not judged.
- **Pilot-wide retry budget:** ≤ 40 additional calls; exhaustion → stop, report, await direction.

## R5. Acquisition wrapper — implemented and pinned (defect 5)

- **Code:** `research_notes/pilot_harness/pilot_acquire.py`
  SHA-256 `7739aec8a2bb3017e4373a2055aaf177dca998dad52cbcdac01b42ef74af37e9`
- **Reuses accepted modules:** `rate_limiter.py` v4 (shared persisted ledger, commit fd03906), `verify_sources.py` (preflight, fail-closed). No fd03906 fixture modified.
- **Behavior:** idempotent resume (existing snapshot → skip, zero transport calls); O_EXCL no-overwrite; per-request receipts (UTC-ms request/receipt times, bytes, SHA-256, sanitized params, scrubbed HTTP status); redaction (key attached only via authd surrogate inside the transport; receipts/logs never carry key material); shared-ledger refusal stops the run.
- **Wrapper-specific fixture pass** `research_notes/pilot_harness/tests/test_acquisition_wrapper.py`
  SHA-256 `602db04d39dacd07ff24eaeaf95c0e1cc340c558a6c109f5236a23d3a0b34852`
  **10/10 PASS** (W01 idempotent rerun, W02 no-overwrite, W03 partial resume, W04 retry-then-success, W05 retry exhaustion, W06 401 stop, W07 schema quarantine, W08 ledger refusal, W09 redaction, W10 receipt metadata). Synthetic only — zero network, zero credits.

## R6. Interval contract — RESOLVED by official source (defect 6)

- **Official source:** Twelve Data API reference, `/time_series` response, `values[].datetime`: *"Datetime at local exchange time referring to when the bar with specified interval was opened."* (https://twelvedata.com/docs/llms/market-data/time-series.md)
- **Verdict:** `datetime` labels are **interval-START**. This corroborates the v7 §3 assertion (previously unevidenced). The cleared `pilot_build.py` chain already carries validator-verified interval ends (`validated_ends`, R14a–R14c), so 1H→4H construction proceeds on interval-start labels with explicit ends — no new empirical vendor call was used to infer this.
- **Adjustment basis pinned:** `adjust=splits` explicit on every request (official default; values `all`/`splits`/`dividends`/`none`).

## R7. Effort ceilings (defect 7)

| Item | Ceiling |
|---|---|
| This r2 pass | 45 min, one pass (actual recorded below) |
| Total repair allocation | 2 passes max (r2 + one r3 if adjudicated), 45 min each → **90 min total**; then STOP, report HOLD |
| Per-defect | governed by the total cap, not "60 min per defect" |
| Maintenance implementation | **30 min ceiling** to implement the 30-day deletion (inventory script + deletion log) upon subscription termination — the v7 retention *obligation* is unchanged |
| ChatGPT review | **bounded:** 72-hour response window; one re-request if silent; then HOLD stands (no execution) — "async" removed |

**Actual effort (r2):** ~40 minutes.

## R8. Authorization (defect 8)

"Plus Mike's word" is **removed** as a prerequisite. The standing authorization is v7 §8: Mike 2026-10-06 conditional ("just run if chat says" / "authorized … to run as soon as ChatGPT clears the revised spec"), applying after P4 passes. No redundant approval is requested or required.

---

## What this packet does not do

No vendor calls, no credit spend, no feed switching, no CP2, no holdout access, no performance computation, no strategy-code changes, no credential publication, no raw-payload publication. **P4 (ChatGPT spec clearance) remains the gate before any pilot execution.** The corporate-action-endpoint leg remains INSUFFICIENT (endpoint unnamed, weight unevidenced) — no corporate-action requests are in the manifest.
