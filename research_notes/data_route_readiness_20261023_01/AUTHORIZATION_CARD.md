# AUTHORIZATION CARD — QF-DATA-ROUTE-READINESS-20261023-01

## NOT EXECUTED / USER GO REQUIRED

Nothing in this package authorizes or executes a vendor call. The
card below is the smallest signable sequence, in order. Each step
is a separate GO; a GO for one step is not a GO for the next
(Policy A discipline: a ceiling is not a GO).

## Step 1 — PILOT GO (the smallest one-time action)

- **Provider / endpoint class:** Twelve Data `/time_series` (1h,
  `adjust=splits`, `outputsize=5000`) + one `/api_usage` preflight
  (never retried).
- **Scope:** 5 session-bound symbols, full span (HO + DEV legs) +
  BTC-USD's 6 date-bounded chunks — **19 credits expected /
  37 worst case** (BLOCK-BRACKET-10).
- **Purpose:** confirm crypto stamp phase, per-leg row counts vs
  calendar expectation, and the receipt chain end-to-end on real
  bytes before the full capture is authorized.
- **Destination:** qf-data-archive `captures/td_pilot_<date>/`
  (append-only, write-once, SHA256SUMS re-fetch verified) +
  byte-identical local store.
- **Credentials/quota:** the existing vault Twelve Data key is
  sufficient; free tier 800/day vs a 37-credit worst case; $0.
  Program spend to date: 8 credits (Day-1 probe).
- **Abort conditions (any one stops the pilot, partial bytes are
  quarantined UNQUALIFIED):** `/api_usage` shows
  `plan_daily_limit` ≠ 800 (the -69 misread is checked explicitly:
  `daily_usage` and `plan_daily_limit` fields, not the per-minute
  limit); any leg returns exactly 5000 rows (truncation defect);
  any leg exhausts its 2-attempt bracket; any receipt-chain break;
  TSLA-class volume-completeness failure on a pilot leg.

## Step 2 — CAPTURE GO (only after the pilot qualifies)

- **Scope:** the remaining legs of `capture_manifest.json` —
  program totals **146 expected / 289 worst case** including the
  pilot and 2 `/api_usage` preflights, over two execution days.
- **Ceiling decision (Mike's, open since -93):** 300 credits
  (margin 11 over worst case) vs ~320 (margin ~31). The capture GO
  must name the ceiling; spend stops at the ceiling regardless of
  completion state.
- **Retention obligation:** archive copies are append-only;
  deletion only on Mike's explicit approval (standing rule).
- **Rollback:** there is nothing to roll back in production — the
  capture writes only to the archive namespace and a local store.
  Abort = stop spending; quarantined bytes are labeled, never
  silently completed by re-chunking or pagination.

## What this card does NOT include

No adoption of guard v3 / checker v3 (G3/G4 stay separate GOs), no
holdout use (captured W-HO bytes are qualification input only), no
performance computation, no shadow launch, no production change.
