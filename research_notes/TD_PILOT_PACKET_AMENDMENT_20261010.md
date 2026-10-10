# Twelve Data Pilot — Packet Amendment (2026-10-10)

**Task:** QF-TD-PILOT-PACKET-20261010-02 (Issue #1 comments 6097910497 / 6097915716)
**Amends:** `research_notes/PILOT_EXECUTION_PLAN.md` v7 (does not replace it; v7 stays the frozen base)
**Status:** PROPOSAL — for ChatGPT review. No vendor calls authorized by this document.
**Actual effort:** ~24 minutes.

## A1. Frozen request manifest (20-symbol pilot)

| Field | Frozen value |
|---|---|
| Endpoint | `https://api.twelvedata.com/time_series` only |
| Symbols | 20 per v7 §1 (AAPL, MSFT, NVDA, AMD, TSLA, META, GOOGL, QQQ, PLTR, HOOD, ANET, SMCI, SOFI, RKLB, NIO, BBAI, ONDS, DRAM, SPCX, TWTR); TWTR fallback → 19 symbols per frozen §1 rule (C5 INSUFFICIENT, not a deviation) |
| Parity window | 2026-09-08 → 2026-10-06 (20 trading days) |
| Warmup acquisition | 1H from 2026-04-01 (215 4H bars preceding 2026-09-08 per §2d) |
| Adjustment windows | NVDA 2024-05-20→2024-06-21; TSLA 2022-08-10→2022-09-09; AAPL 2026-07-27→2026-08-24 |
| Spot windows | DST spring-forward 2026-03-09→13; fall-back 2025-11-03→07; early close 2025-11-28; closed day 2026-07-03 (AAPL, QQQ) |
| Params | `interval` ∈ {1h, 4h}; `timezone=America/New_York`; `outputsize=5000`; `order=ASC`; `start_date`/`end_date` per window |
| Auth | `custom.twelvedata` via authd surrogate; raw key never handled/logged/persisted |

Boundary note (from Stage-0 offline report): date-only `end_date` behaved **exclusive** in the Stage-0 response (coverage through Oct 5 for `end_date=2026-10-06`). Window definitions above are calendar windows; the wrapper records actual returned coverage per request and any shortfall is a recorded discrepancy, not silent.

## A2. Endpoint weight with entitlement evidence

- **`/time_series` = 1 credit per symbol per request.** Evidence: (a) public plan documentation per feed-gate adjudication 6049455862 (Basic: 8 credits/min, 800/day); (b) **empirical**: Stage-0 executed 2 requests, shared limiter ledger records exactly 2 credits spent (commit 4a4680e).
- **Corporate-action endpoint: weight UNKNOWN — stale "2 credits each" assumption REMOVED.** The v7 budget table's "20 × corporate-action pulls (2 credits each)" line is withdrawn (the assumption was already disavowed in text; it is now removed from the budget). The packet never names the corporate-action endpoint. **Dependent leg disposition: HOLD.** Until the endpoint is named with entitlement evidence for its weight, no corporate-action requests are made; the C3 Twelve Data action-list leg is recorded **INSUFFICIENT EVIDENCE** (restricted verdict), and adjustment-rule validation proceeds only on documented ex-date/split conventions + the Yahoo action leg.
- **"20 × symbol metadata" line: REMOVED.** No endpoint named in v7; excluded from the budget. If a metadata endpoint is needed later, it requires its own named-weight amendment.

## A3. Credit reconciliation and limiter (corrected)

- v7 §5's "token-bucket limiter" language is **corrected**: the accepted limiter is the v4 **`RollingCreditLimiter`** (rolling 60-second window + hard 800/day cap, persisted ledger, fail-closed) at `research_notes/pilot_harness/credit_ledger.json`. It is **shared** across Stage-0 and the pilot — one ledger, no substitutes.
- **Already spent:** 2 credits (Stage-0, 2026-10-10). The pilot budget below counts forward from the ledger state at execution time.

## A4. Call/credit budget (recomputed, stale lines removed)

| Leg | Requests | Credits | Ceiling |
|---|---|---|---|
| Parity 1H (20 symbols, incl. warmup from 2026-04-01) | 20 | 20 | — |
| Parity 4H diagnostic | 20 | 20 | — |
| Warmup pagination reserve (if outputsize cap hit) | ≤20 | ≤20 | — |
| Adjustment-window 1H (NVDA/TSLA/AAPL extra windows) | 12 | 12 | — |
| DST/early-close/closed-day spots (AAPL, QQQ × 4 × 1H) | 8 | 8 | — |
| Retry buffer (transient 429/5xx only, backoff, counted) | ≤40 | ≤40 | — |
| T+7d re-pull 1H | 20 | 20 | — |
| T+30d re-pull 1H | 20 | 20 | — |
| **Peak day total** | | **≤ 100** | hard stop |

- **Retries:** zero-retry default per request (Stage-0 rule carried forward). The 40/day buffer covers transient HTTP 429/5xx with backoff only; each retry consumes budget. Buffer exhaustion = stop, report, await direction.
- **Stop criteria:** daily 800 hard cap (fail-closed, never queues); HTTP 401/403 = stop (request question before key question; reconnect only via approved flow); sustained 429 = stop and report; any schema break = quarantine the leg and stop; any credential-bearing string in logs = stop and purge.
- **Per-leg ceilings:** parity leg ≤ 60/day; adjustment+spot legs ≤ 60/day; revision legs ≤ 20 each. Any leg exceeding its ceiling = stop.

## A5. Acquisition wrapper + source checks (pinned BEFORE execution)

No pilot vendor call until the wrapper is frozen, committed, and ChatGPT-cleared. The wrapper must:

1. Use the shared `RollingCreditLimiter` (persisted ledger); fail closed on refusal.
2. Record per [B3]: request time (UTC, ms), receipt time (UTC), raw bytes + SHA-256, sanitized params (no key material), scrubbed HTTP status/headers.
3. Write snapshots to the private immutable store; **no-overwrite / idempotent**: refuse if the snapshot exists; resume by skipping completed requests (fail-closed resumability).
4. Enforce redaction: error strings and logs never carry key material or credential-bearing URLs.
5. Run `verify_sources.py` (pinned archival SHAs) before any construction; construction only via the cleared `pilot_build.py` chain.

## A6. Pre-execution checklist additions (from Stage-0 offline findings)

1. **Interval-label contract provenance:** v7 §3 asserts Twelve Data 1h bars are "labeled at interval start." The Stage-0 response does not document this (no `interval_end` column, no labeling contract in payload). The assertion requires a cited vendor-documentation source before pilot 1H→4H construction; until then, construction on Twelve Data bars is **INSUFFICIENT** per `STAGE0_OFFLINE_REPORT_20261010.md`. This is a named pre-execution item, not a silent assumption.
2. **Receipt timestamps:** Stage-0 manifest lacked per-request receipt timestamps — the pilot wrapper records them per A5(2) (wrapper gap, fixed by requirement).
3. **Straddle disposition:** recorded per bar in the pilot (v7 §3 rejects straddling intervals as C1 hard fail).

## A7. Warmup initialization — separate gate (unchanged)

Per v7 §2d: warmup is 215 bars in the evaluated (4H) timeframe. **No decision-impact evidence is promoted while the warmup leg is INSUFFICIENT.** `pilot_decision_impact.csv` is produced only where the decision-impact leg is not INSUFFICIENT.

## A8. Effort ceilings

| Phase | Ceiling |
|---|---|
| Prep (wrapper freeze, checklist) | 60 min |
| Execution (active; excludes rate-limit spacing) | 30 min |
| Report | 45 min |
| ChatGPT review | async — no execution until clearance |
| Repair (per defect) | 60 min |
| Maintenance | 30-day deletion obligation on subscription termination (retention envelope v7) |

## A9. ARCH-A/B/C vs do-not-repeat list

Checked 2026-10-10 against `research_notes/execution_audit_inventory_20261010.md` (do-not-repeat list, 8 items). **All three stay design-only; no study is authorized by this amendment.**

- **ARCH-A (daily 60-session-high breakout):** NO DIRECT DUPLICATE. Closest neighbor is the unexecuted QF-R2 breakout+volume prereg (inventory #17, HELD) — ARCH-A would overlap QF-R2's breakout territory if both were run; coordinate before any prereg. Not on the do-not-repeat list.
- **ARCH-B (weekly RS rotation, top-quintile):** PARTIAL OVERLAP — WARNING. Killed item #1 (TOP-50/quarterly/liquidity+RS composite universe filter, Mike 2026-10-04) is a different construction (quarterly TOP-50 composite vs weekly rotation top-quintile), so ARCH-B is not literally the same experiment — but it sits in the same RS-selection family that failed. Any future prereg must explicitly distinguish its construction from the killed one; the failure-memory rule applies (new experiment ID, genuinely different hypothesis or held-out evidence).
- **ARCH-C (daily 2-ATR overshoot reversal):** NO DIRECT DUPLICATE. Mechanism differs from killed/failed item #7 (capitulation-harami entry trigger — candle-pattern, 15 trades, −0.049R). **Constraint:** if the design includes a short side, it collides with do-not-repeat #5 (short-side daily equity systems are structural losers across three independent readings) — the short leg would need long-only scoping or separate justification.

## A10. What this amendment does not do

No vendor calls, no spending, no feed switching, no CP2, no holdout access, no performance computation, no strategy-code changes, no credential publication. P4 (ChatGPT spec clearance) remains the gate before any pilot execution, plus Mike's word per the standing authorization record.
