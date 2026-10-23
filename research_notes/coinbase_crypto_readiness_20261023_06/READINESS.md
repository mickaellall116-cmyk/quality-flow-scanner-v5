# QF-COINBASE-CRYPTO-ROUTE-READINESS-20261023-06 r1 — READINESS

**Type:** bounded OFFLINE readiness package. Official documentation and
terms reading only, pinned source, synthetic fixtures. **No Coinbase /
Twelve Data / exchange API calls, no candle downloads, no credits, no
spending, no capture, no performance/holdout work.** Nothing here adopts
a provider or authorizes acquisition.
**Governing task:** Issue #1 comment 6372124967 (ChatGPT), advancing
Path A of the -05 disposition (`e23f0a9`, bridge `d55ee7d`; independent
source review 6371950296). Frozen UX51 and the adopted S-C1…S-C6
contract are unchanged. Twelve Data stays the equity route; its crypto
branch remains NOT_EVALUABLE_SCHEMA_AND_PHASE.
**All documentation retrieved 2026-10-23 (America/New_York).**

## Verdict: HOLD — exact blocker: PERSISTENCE_UNPROVEN

The documented contract, the request arithmetic, and the offline
adapter all check out (§§1–5). The pilot card (PILOT_CARD.md) is
returned NOT EXECUTED because the pinned terms text does **not**
affirmatively permit the immutable research archive that the program's
Card-A receipt discipline requires (§2). Per the governing task: no
workaround is offered. Unblocking requires (a) a terms resolution that
affirmatively permits internal archival (e.g. written consent, or a
terms revision that says so), and (b) Mike's GO on the card. Both are
governed decisions outside this package.

---

## 1. Primary-source contract — FACT (documented)

Source: Coinbase Developer Documentation, "Get product candles",
Exchange REST API — https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles
(page stamp: Updated 2026-02-11T16:58:57Z; retrieved 2026-10-23).

- Endpoint class: `GET /products/{product_id}/candles` (Exchange REST).
- `granularity` must be one of `{60, 300, 900, 3600, 21600, 86400}`
  seconds — **900 = fifteen minutes** — "or your request is rejected".
- **Max candles:** "If your selection of start/end time and
  granularity results in more than `300` data points, your request is
  rejected. To retrieve fine granularity data over a larger time range,
  you must make multiple requests with new start/end ranges." A
  response "may contain as many as `300` candles and some of those
  candles may precede your declared `start` value."
- `start` / `end`: ISO timestamps for the aggregation range; if either
  is omitted both are ignored and a range ending now is selected.
- **Response items (documented):** each bucket is an array of `time`
  (bucket start), `low`, `high`, `open`, `close`, **`volume` (volume
  of trading activity during the bucket interval)**. NOTE: the page's
  "Additional Details" summary line prints the schema as [timestamp,
  price_low, price_high, price_open, price_close] without volume; the
  Response Items list — the operative schema section — includes
  volume. The discrepancy is recorded, not resolved by inference; the
  pilot's first slice would settle it on actual bytes.
- Response ordering is not stated on the pinned page. The adapter is
  order-agnostic (sorts by UTC instant; fixture-proven).

Rate limits — FACT. Source: "Exchange Rate Limits Overview",
https://docs.cdp.coinbase.com/exchange/introduction/rate-limits-overview
(retrieved 2026-10-23): REST **public endpoints: 10 requests/second
per IP, burst up to 15**, lazy-fill token bucket. There is no credit
system and no documented usage-accounting endpoint for public REST;
budgeting is request counts plus pacing (§3).

Product IDs — internal IDs UNCHANGED: **BTC-USD, ETH-USD, SOL-USD,
DOGE-USD, AVAX-USD, LINK-USD, XRP-USD** (frozen UX51 members,
`pine_backtest.UNIVERSE_X`, Option A freeze).
- INFERENCE: Coinbase `product_id` strings use the same BASE-QUOTE
  form, so the candidate provider alias for each pair is the identical
  string.
- **UNTESTED: per-pair availability.** No primary source in this
  package proves any of the seven pairs is currently listed/served;
  the docs' product-list endpoint is a data call and out of scope.
  Availability is pilot-provable only (BTC first).

Historical reach — **UNTESTED.** The pinned documentation specifies
the start/end mechanism but states no earliest-available date and no
maximum history depth. Whether 15m candles are served back to
2023-10-19 is exactly what pilot slice S1 exists to prove. No reach
claim is made here.

## 2. Terms — PERSISTENCE_UNPROVEN

Governing text pinned: **Coinbase Market Data Terms of Use**,
https://www.coinbase.com/legal/market_data (page stamp: Last updated
August 7, 2026; retrieved 2026-10-23). (Coinbase's own trading
agreements route API market data to these terms; e.g. the Master
Trading Agreement §7 subjects data "made available … through … any
application programming interface(s)" to the Market Data Terms of
Use.)

What the text says (FACT, quoted/paraphrased by section):
- §1: "Market Data" = all data made available by Coinbase, including
  order and transaction information related to trading on Coinbase
  exchanges.
- §2: a nonexclusive, nontransferable, revocable, limited license;
  use "exclusively for you or your entity's **personal or research
  purposes**".
- §3.2: absent prior express written consent, no redistribution,
  display, or dissemination of Market Data or Derived Works to any
  third party outside your organization.
- §3.5: absent consent, no use of Market Data "to … develop, train,
  fine-tune, teach, **validate, benchmark**, or otherwise improve any
  artificial intelligence or machine learning model, **algorithm,
  chatbot, agent, or other automated system** … or for any other
  purpose related to the research, development, or operation of
  artificial intelligence technologies."
- §4.1: Market Data is exclusively Coinbase's property; "Coinbase
  reserves all rights in the Market Data not expressly granted."

**No clause in the pinned text affirmatively permits storing or
archiving Market Data into an immutable research archive.** Per the
governing instruction — no inference from silence — the state is
**PERSISTENCE_UNPROVEN**. This matters mechanically: the program's
capture discipline (Card A shape, -01 receipt schema) requires
immutable archival in `qf-data-archive` plus hash-chained receipts;
executing a capture whose archival step is not affirmatively
permitted would repeat, in reverse, the Tiingo failure mode the -05
route matrix already excludes ("terms permit immutable archival"
is Path A pilot-evidence item 4).

Two recorded cautions, neither resolved here:
- §3.5's scope over an agent-operated validation pipeline is a real
  question for the same terms-resolution conversation; interpreting
  it is a governed/legal call, not a desk inference.
- A different agreement (Coinbase Bermuda User Agreement, Appendix 4
  §1.4(E)) expressly prohibits storing/archiving Market Data "to
  create … any standalone database". That text governs Coinbase
  Bermuda services and is **not** cited as governing the US Exchange
  API; it is recorded only to prevent conflation and to show the
  direction of Coinbase's terms drafting.

## 3. Request arithmetic (computed, asserted — request_arithmetic.py)

Page ceiling 300 (documented). Spans are the frozen S-C session-date
ranges of manifest candidate -01: HO dates 2023-10-19..2024-09-15,
DEV dates 2024-09-16..2026-10-16, abutting exactly at 2024-09-16
09:30 ET. Elapsed bars from absolute UTC spans (DST-exact).

| Span | Dates | Elapsed h | 15m bars/pair | Pages (no overlap) | Pages (1-bar overlap) |
|---|---|---|---|---|---|
| HO | 333 | 7,992 | 31,968 | 107 | 107 |
| DEV | 761 | 18,264 | 73,056 | 244 | 245 |
| **Full / pair** | **1,094** | **26,256** | **105,024** | **351** | **352** |
| **Full × 7 pairs** | | | **735,168** | **2,457** | **2,464** |

- Chunk structure follows the frozen rule (≤208 consecutive ET dates
  per chunk): 1,094 dates → 6 chunks per pair, each chunk paginated
  internally at ≤300.
- Hard worst: ≤1 retry per request, fail-closed after → **4,914**
  (no-overlap) / 4,928 (overlap) requests for full 7-pair coverage.
- Receipt/status reads: no provider credit exists to read; receipt
  discipline models +1 product-availability read per pair per
  execution day. Cost **$0** at every count above.
- Pacing: at the program's conservative 1 request / 2 s, full
  coverage ≈ **82 minutes** of pacing (per pair ≈ 12 min); at
  5 req/s (half the documented public limit) ≈ 8.2 min of pure
  request time.

## 4. Feasibility assessment

- **Operational reasonableness: YES on volume.** 2,457 expected
  requests for the entire frozen crypto scope is small against the
  documented public limit; even the fail-closed hard worst (4,914)
  paces inside ~2.7 hours at the conservative rate. No credits, no
  key, no spend at any point.
- **Gap/duplicate safety: achievable by construction.** Pages are
  disjoint, pre-declared UTC windows on a fixed 900s grid; the
  adapter dedupes exact-identical seam rows, refuses conflicting
  duplicates, refuses bars outside the declared span (which also
  neutralizes the documented "candles may precede your start"
  behavior — a page's declared span is its window, nothing outside
  it is admitted silently), and refuses any missing interior instant
  under completeness. The 1-bar-overlap variant costs +7 requests
  total program-wide and is the recommended seam discipline.
- **Residual UNTESTED risks** (pilot-provable, not paper-provable):
  historical depth to 2023-10-19; per-pair availability; the
  schema-line discrepancy in §1; actual response behavior at page
  seams across a DST transition.

## 5. Offline adapter + fixtures (adapter/, TEST_EVIDENCE.md)

`coinbase_15m_adapter.py` (stdlib only) aggregates synthetic
Coinbase-shaped 15m arrays into the frozen S-C bins: wall-anchored
bin boundaries (09:30/13:30/17:30/21:30/01:30/05:30 ET) resolved to
UTC instants; honest OHLCV (first/max/min/last/sum); volume carried
end-to-end; fail-closed on schema (incl. absent/null volume — the TD
defect class), misalignment, conflicting duplicates, out-of-span
bars, and interior gaps. **13/13 fixtures PASS** under `unshare -n`,
including spring 23h (absorbing 01:30 bin = 12 bars) and fall 25h
(20 bars, both repeated-hour bars inside the 01:30 bin), overlap
dedupe, reversed provider order, partial terminal bin, and the
300-row page boundary. Canonical output hashes are pinned in
TEST_EVIDENCE.md. Two pre-evidence corrections (elapsed-anchored →
wall-anchored bins; test bin index) are disclosed there — the
fixtures caught the first before any evidence was taken from it.

## 6. Decision boundary

This package, if its HOLD is lifted by a terms resolution, unlocks
exactly one thing: a responsible one-BTC pilot (PILOT_CARD.md) that
could prove reach, schema+volume, :30 composability, pagination, and
receipts on actual Coinbase bytes. It does **not** unlock: UX51
qualification of any pair, full capture, baseline computation,
performance, or shadow — each remains gated on an actual-byte pilot
plus independent verification, and (for execution) Mike's GO.
Equities-only scope change (Path B) is untouched by this task and
remains a separate fallback requiring Mike's explicit decision.

**Recommendation: HOLD** — blocker PERSISTENCE_UNPROVEN (§2). The
route is the first crypto candidate to clear schema, phase,
arithmetic, and adapter readiness on paper; it stops at the same
gate that correctly stopped Tiingo: do not build an immutable
archive on terms that do not affirmatively permit one.

## Bounds kept

Offline only; documentation/terms pages read as text (no API or
candle endpoint called, no data downloaded); zero credits; program
TD total unchanged at 24; PAUSED production pins identical
before/after (harness `ce7c902c…`, PAUSE_NEW_ENTRIES present); no
production/frozen-strategy change; no holdout strategy use; no
performance; no shadow launch. Prior packages byte-untouched.
