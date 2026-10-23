# PILOT CARD — QF-COINBASE-CRYPTO-ROUTE-READINESS-20261023-06

## NOT EXECUTED / USER GO REQUIRED

Nothing in this card authorizes or executes an API call. It is the
minimum one-symbol pilot that would convert the -06 readiness paper
into actual-byte evidence, in the Card A discipline that caught both
Twelve Data crypto defects for 6 credits.

## Pre-execution gate G0 — PERSISTENCE (currently BLOCKING)

The -06 verdict is HOLD with blocker **PERSISTENCE_UNPROVEN**
(READINESS.md §2): the pinned Coinbase Market Data Terms of Use do
not affirmatively permit the immutable research archive this pilot's
receipt discipline requires. **This card may not execute until G0 is
resolved affirmatively** (written consent, or terms text permitting
internal archival) — and then still requires Mike's GO naming this
card. The §3.5 AI/agent clause scope is part of the same G0
resolution. No workaround (ephemeral-only capture, unarchived bytes)
is offered: unarchived bytes cannot carry receipts and would be
unverifiable by construction.

## Scope (if G0 clears and GO is given)

- **Symbol:** BTC-USD only — internal ID unchanged; candidate
  provider product_id `BTC-USD` (availability is itself a pilot
  proof, not a premise).
- **Endpoint:** Coinbase Exchange REST
  `GET /products/BTC-USD/candles`, `granularity=900`, explicit
  ISO `start`/`end` per slice below. Public endpoint; no key, no
  credits, $0.
- **Slices** (session-date spans under the frozen S-C contract;
  computed in request_arithmetic.py):

| Slice | Session dates | Proves | Bars | Pages |
|---|---|---|---|---|
| S1 | 2023-10-19..2023-10-25 | 2023 reach from the exact HO start; schema incl. volume on 100% of rows; normal-week bins | 672 | 3 |
| S2 | 2023-11-03..2023-11-05 | Fall DST: 25h session 2023-11-04; 01:30 absorbing bin = 20 bars; repeated wall hour = distinct UTC instants | 292 | 1 |
| S3 | 2024-03-08..2024-03-10 | Spring DST: 23h session 2024-03-09; absorbing bin = 12 bars; nonexistent 02:00 is not a missing bar | 284 | 1 |
| S4 | 2024-01-08..2024-01-17 | Pagination: 4 pages, seam dedupe, partial terminal page (60) | 960 | 4 |

- **Request budget:** 9 candle requests + 1 product-availability
  read = **10 expected**; **hard ceiling 20** (≤1 retry per request,
  fail-closed after; any second failure aborts the run). Pacing ≤1
  request / 2 s (documented public limit 10 req/s per IP — the
  conservative pace is deliberate, not required).
- **Destination (post-G0 only):** `qf-data-archive`
  `captures/coinbase_btc_pilot_<date>/` (append-only, SHA256SUMS
  re-fetch verified) + byte-identical local store; receipts
  hash-chained per the -01 receipt schema lineage.
- **Page discipline:** 1-bar overlap at every seam, dedupe by UTC
  instant; each page's declared span is its exact request window.

## Abort conditions (any one stops the run; partial bytes quarantined
UNQUALIFIED, never silently completed)

- Product-availability read fails or BTC-USD not served.
- Any response deviating from the documented schema; **volume
  absent or null on any row** (the TD defect class) → SCHEMA abort.
- Any bar off the 900s UTC grid, any conflicting duplicate instant,
  any response exceeding 300 candles, any window rejected by the
  provider (e.g. range beyond served history — that is S1's reach
  test failing, recorded as REACH_FAIL, not retried with shifted
  windows).
- Adapter completeness failure on actual bytes (interior GAP,
  wrong DST bin counts) → quarantine + stop.
- Any price-moving zero-volume anomaly class (SMCI rule,
  generalized) → quarantine + stop.
- Receipt-chain break at any point.
- Request count would exceed the hard ceiling of 20.

## Qualification sequence (on actual bytes, in order)

1. Receipt integrity: chain recompute + archive re-fetch byte
   equality.
2. Schema: volume present on 100% of rows; field order/keys as
   documented; row counts equal pre-stated expectations per slice
   (672 / 292 / 284 / 960).
3. Reach: S1's first admitted bar is the 15m bar opening the HO
   window (session 2023-10-19, bin 09:30 ET) — reach proven by
   content, not by HTTP 200.
4. Composability: the offline adapter aggregates every slice to the
   frozen S-C bins with exact expected counts (S2 absorbing bin 20,
   S3 absorbing bin 12); zero split bars, zero shifted stamps.
5. Pagination: S4 seams dedupe to a contiguous 960-bar span with no
   gap and no duplicate.
6. Independent verification (ChatGPT/Claude) before any further
   chunk, pair, or full-span step is contemplated.

## What this pilot does NOT do

No other crypto pair (ETH/SOL/DOGE/AVAX/LINK/XRP stay untested after
it); no equities; no full capture (2,457-request program); no
baseline; no performance; no holdout strategy use (any HO-window
bytes remain qualification-only, holdout sealed); no production or
frozen-strategy change; no shadow launch; no purchase.
