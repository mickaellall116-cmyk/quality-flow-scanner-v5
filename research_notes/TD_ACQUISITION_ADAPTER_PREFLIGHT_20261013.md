# TD Acquisition-Adapter Preflight Package — 2026-10-13

Task: QF-TD-ACQUISITION-ADAPTER-PREFLIGHT-20261013-01 r1 (Issue #1 comment
6158529341), under Mike's 2026-10-13 standing rule (Muse↔ChatGPT research
loop is auto). **Synthetic + primary-documentation only: zero vendor calls,
zero credits, zero spend, no code changed.** This package satisfies the five
minimal acquisition prerequisites recorded in
`research_notes/TD_PINNED_INTEGRATION_REVIEW_20261013.md` on paper, so that a
future acquisition step can be *proposed* against pinned artifacts. It does
not authorize, schedule, or perform any acquisition.

Evidence folder: `research_notes/td_acquisition_adapter_preflight_evidence_20261013/`
(manifest, prerequisites, adapter contract, validation transcript, SHA-256
pins). All file pins are in that folder's `SHA256_MANIFEST.txt`.

## 0. Offline validation result (the preflight proof)

The package was validated with the accepted collector's own code, extracted
byte-identical from `f64d12f` (collector sha256 `bd003c3c…`, limiter
`06ad383d…` — both match the integration evidence pins):

- `validate-manifest` → `manifest_errors: []`, 51 requests, exit 0.
- `preflight` → `manifest_errors: []`, `prerequisite_failures: []`
  (including pinned archival-source verification), exit 0.
- Dispatch remains **BLOCKED (zero-call build: no vendor transport)** —
  the correct terminal state for this package.

Transcript: `validation_output.txt` in the evidence folder.

## 1. Prerequisite 1 — Revised acquisition manifest, supplied and pinned

**File:** `acquisition_manifest_v1.json` — manifest_id
`TD-ACQUISITION-MANIFEST-V1-20261013`, file sha256 `66a31e10…`, canonical
manifest digest `e1cb648d…` (collector `canonical_digest`).

It supersedes `TD-PILOT-MANIFEST-R3-20261010`. Scope is exactly what an
acquisition run WOULD request — nothing else:

| Leg | Requests | Content |
|---|---|---|
| PAR | 20 × 1h | Frozen 20 symbols, 2026-04-01 → 2026-10-06 (parity + warmup window) |
| PAR4H | 20 × 4h | Same window, native 4H (diagnostic only, per ruling R2) |
| ADJ | 3 × 1h | NVDA split window 2023-12-13 → 2024-06-21; TSLA split window 2022-03-07 → 2022-09-09; AAPL dividend window 2026-02-19 → 2026-08-24 |
| SPOT | 8 × 1h | AAPL+QQQ: DST-spring week 2026-03-09→13, DST-fall week 2025-11-03→07, early close 2025-11-28, closed day 2026-07-03 |

Every request pins: endpoint `https://api.twelvedata.com/time_series`,
`timezone=America/New_York`, `outputsize=5000`, `order=asc`,
`adjust=splits`, `max_attempts=1`, `credit_weight=1`, `expected_credits=1`,
the collector's canonical `identity` string, `one_response_bound_bars`
(derived exactly as the collector derives it), and `venue_identity`
{exchange, mic_code, currency} per the frozen plan §1 + ISO 10383
(NASDAQ/XNAS ×14, NYSE/XNYS ×5, Cboe BZX/BATS ×DRAM; USD throughout).

**Budget: 51 requests = 51 credits expected = 51 credits maximum.**
Expected equals maximum by construction: one attempt each, no pagination,
no retries — the R3 machinery (91 base + up to 40 pagination + 40 retries =
171 max) is gone. Plan caps (Basic): 8 credits/min, 800/day — the whole run
is ~6.4 limiter-minutes and 6.4% of one day's cap.

**Expected volumes** (XNYS sessions = weekdays − NYSE holidays; early-close
sessions return 4 bars instead of 7, a small downward variance in long
windows): PAR 1h ≈ 910 rows/symbol (130 sessions; bound 1,323);
PAR 4h ≈ 260 rows/symbol (bound 378); ADJ ≈ 903–917 rows (bounds
1,309–1,344); SPOT weeks 35 rows; 2025-11-28 exactly 4 rows expected;
2026-07-03 exactly 0 rows expected (any bar = hard fail). Pre-declared
short-history exceptions (not completeness failures): SPCX (IPO 2026-06-12,
≈567 rows expected), DRAM (launched Apr 2026), TWTR (delisted 2022-11-08 —
an error/empty response is the expected outcome; if it blocks the run, the
frozen fallback applies by manifest revision: record C5 INSUFFICIENT,
proceed at 19 symbols — never by in-run continuation).

Revision deltas vs R3 are recorded inside the manifest itself
(`revision_deltas_vs_r3`), including: REV7/REV30 legs removed from
collector scope (see protocol P6), `order` normalized to the lowercase
`asc` the collector and vendor docs both use, and `allow_404_continue`
dropped (the collector HALTs on any non-200 with evidence preserved).

## 2. Prerequisite 2 — One named adapter, pinned (design only)

**Name:** `td-http-transport-adapter` v1.0.0-preflight.
**File:** `adapter_contract.json` (sha256 `db6c44a2…`).

The candidate has no HTTP client. This contract is the pinned spec an
adapter must be built and reviewed against in a separate step; nothing was
implemented here. It binds:

- **Interface:** `transport(req) -> (status:int, body:bytes)`, raising on
  transport-level failure — exactly what the accepted collector consumes.
  Only the disabled built-in transport is replaced; no collector logic
  changes.
- **Request construction:** GET, parameters in one fixed order copied
  verbatim from the manifest request; `format=JSON`; auth by `apikey`
  query parameter (the vendor's documented example form), key sourced by
  the driver from the Secure Vault (`custom.twelvedata`), memory-only,
  never in disk/argv/logs/events/exception text. Venue parameters are NOT
  sent — venue is enforced on receipt meta (collector design). `prepost`
  is Pro-tier and out of scope; `dp` is left at the vendor default so
  returned precision is the vendor's own.
- **Timeout/error contract (sanitized):** connect 10s / read 30s; total
  attempts per request = 1; **no retries at any layer**. Any non-200 —
  including 429 — returns (status, body) untouched; the collector
  preserves raw bytes as private error evidence and HOLDs. A 429 is
  additionally recorded as a limiter/vendor divergence in the run report.
  Transport exceptions propagate with type only; the adapter emits no
  logs of its own and no string it produces may contain the key, the
  request URL, or response headers. HTTPS only, cert verification on,
  cross-host redirects fail closed, 64 MiB body cap.
- **Shared LIVE limiter path:** the same `RollingCreditLimiter`
  (pilot_harness/rate_limiter.py, sha256 `06ad383d…`) the integration
  proved, constructed `credits_per_minute=8, daily_cap=800`, with
  `state_path = research_notes/pilot_harness/credit_ledger.json` — the
  one persisted ledger Stage-0 already used (2 credits, 2026-10-10). The
  adapter/driver uses non-blocking `try_acquire` only, through the
  collector; refusal ends the run REFUSED and resumption is a fresh
  invocation with receipt revalidation. No second limiter, no per-run
  ledger, no blocking `acquire()`.

**Account/retention terms from PRIMARY vendor documentation** (accessed
2026-10-13; paraphrased, sources cited in `prerequisites.json`):

- Pricing page (twelvedata.com/pricing): Individual Basic is $0/mo,
  8 API credits/min with an 800/day cap, US markets, "internal
  non-display usage only"; individual plans are for personal, internal,
  non-commercial use.
- API docs (/time_series page): the endpoint costs **1 API credit per
  symbol**; `outputsize` range 1–5000; `order` asc/desc (default desc);
  `adjust` ∈ all/splits/dividends/none (default splits); `timezone`
  accepts IANA names; response meta carries symbol, interval, currency,
  exchange_timezone, exchange, mic_code, type.
- Terms of Use (twelvedata.com/terms, last updated January 1, 2026):
  the data license grants storing Data "solely for Internal Use"
  (§2.2(a)); storing beyond timeframes specified in the Documentation
  is prohibited (§2.3(g)) — and no Basic-plan Documentation page read in
  this pass specifies a retention timeframe; retention is capped at the
  "duration permitted by subscription" (§16.1) and, on termination or
  expiration, all Data must be deleted within 30 days, with deletion
  certification if requested, while audit-trail data may be kept for
  compliance (§16.2).

The collector-facing prerequisites file is `prerequisites.json`
(sha256 `038ccaf3…`): plan `Basic`, endpoint weight 1 with doc evidence,
retention `BOUNDED_RESOLVED` with the 30-day condition, interval
semantics `INSUFFICIENT` (see ruling R3).

## 3. Prerequisite 3 — Semantics rulings (fixed in writing, before any data)

- **R1 — COMPLETE means validated-receipt completion only.** A request
  is COMPLETE only when a durable COMPLETED lifecycle event exists,
  emitted after the receipt bytes were persisted (RECEIVED) and passed
  the accepted validation path under the same request digest and
  manifest digest. HTTP 200, a RECEIVED event, or a receipt file alone
  never constitutes completion. A run outcome of COMPLETE means every
  manifest request reached that state, counting reuse only after full
  revalidation (digests, byte length, sha256, meta binding, fresh
  validation pass).
- **R2 — Native-4H diagnostics say nothing about session coverage.**
  Native 4H validation scope is `native_4h_structural_diagnostic`:
  finite OHLCV, price geometry, label containment in the request window.
  It asserts nothing about session coverage, constituent completeness,
  or session anchoring. Native 4H can never qualify the feed and never
  substitutes for 4H constructed from validated 1H.
- **R3 — The 1H start-label is a declared convention, not vendor
  semantics proof.** The vendor docs describe the values `datetime` as
  the exchange-local time at which the bar opened. That documentation
  statement is recorded as evidence but does not establish the returned
  bytes' behavior. The project convention stands as declared (labels =
  interval starts in America/New_York; canonical ends = next start or
  session close, validator-carried), `interval_semantics` stays
  **INSUFFICIENT**, the collector is constructed with
  `semantics_status="INSUFFICIENT"`, and 1H→4H construction for
  decision-impact use stays CONSTRUCTION_HOLD until protocol check P2
  passes on acquired receipts.

## 4. Prerequisite 4 — Private retention plan

Basis: Terms §2.2(a)/§16.1/§16.2 as read above, plus the bounded reading
recorded 2026-10-08 (user-supplied vendor AI-support transcript,
unauthenticated, corroborated in substance by §16).

- **Store:** raw receipts and rejected-payload evidence live only in a
  private local store (working-tree directory excluded from git; raw
  vendor payloads are NEVER committed, posted, or published — only
  manifests, hashes, counts, and summaries are, per the standing rule).
- **Inventory:** the retention envelope covers primary receipts, error
  evidence (`*.rejected.bin`), any backups or shared copies of them,
  and the collector state directory. Every copy counts; there are no
  exempt copies.
- **Derived data:** constructed 4H series are resampled series
  recoverable to the underlying bars, so they are treated as Data under
  the same retention envelope (conservative ruling). Non-reconstructible
  artifacts — manifests, hashes, lifecycle logs, counts, pass/fail
  outcomes, signal decisions — are audit trail and may be retained for
  compliance per §16.2(c).
- **Termination trigger:** if the account is terminated, expires, or is
  downgraded out of the recorded terms, ALL retained Data (receipts,
  error evidence, derived bar series, and every copy) is deleted within
  30 days, and the deletion is recorded in the run record. No indefinite
  or post-termination retention is claimed or planned.
- **Comparator hygiene:** no Tiingo-held input is used as a comparator
  anywhere in this package or the protocol below (Tiingo HOLD stands;
  Tiingo material was not touched). The comparator is prospective Yahoo
  1H capture only (frozen plan §3 [B7]).

## 5. Prerequisite 5 — Comparison / qualification protocol (pre-declared, frozen)

This protocol qualifies the DATA ROUTE only. It is frozen by this
package before any acquisition is proposed. No unchanged-strategy
baseline may be computed until every check below has passed and the
dataset/code/cost/fill/validation splits are fixed in a separate frozen
document; nothing in this protocol computes strategy performance.

- **P1 — Timestamps.** Compare vendor labels per session against the
  XNYS calendar (pinned `pandas_market_calendars` 4.5.1) under the
  declared convention: naive stamps are exchange-local America/New_York;
  requested timezone is America/New_York on every request. First and
  last labels per session type must match the frozen 1H spec (regular:
  09:30…15:30; early close: 09:30…12:30; closed: none).
- **P2 — Bar-boundary / semantics evidence.** The SPOT legs are the
  empirical semantics test: DST-spring week (EDT), DST-fall week (EST),
  the 2025-11-28 early close (exactly 4 bars, last label 12:30), and
  2026-07-03 (exactly 0 bars). All four must match the declared
  convention exactly for `interval_semantics` to be proposed as
  SOURCED; any miss keeps INSUFFICIENT and CONSTRUCTION_HOLD in force.
- **P3 — Date-end inclusion.** Windows are inclusive calendar ranges:
  a session belongs to the window iff its date is within
  [start_date, end_date]; the final session must be fully present
  (all expected constituents with ends ≤ end_date 23:59:59 ET) and no
  bar may fall outside the window (collector-enforced for 4H; validator
  grid for 1H). Revision re-pulls use byte-identical windows.
- **P4 — Venue coverage.** For every receipt, record meta exchange /
  mic_code / currency and check against the manifest pin (any mismatch
  already HOLDs the run at receipt time). Additionally, detect
  single-venue scope: compare per-bar volume against the prospective
  Yahoo comparator over the PAR window and report the volume-ratio
  distribution per symbol (thin names BBAI/ONDS are the named probes);
  a systematic consolidated-vs-single-venue discrepancy is reported as
  a qualification finding with numbers, never assumed away.
- **P5 — Missing bars.** Per-session expected constituents come from
  the frozen 1H grid (7 regular / 4 early-close / 0 closed). Any
  missing constituent = session INCOMPLETE = that symbol fails the
  completeness check; no interpolation, no fabrication, no silent
  acceptance. Short-history exceptions are exactly the pre-declared
  ones in §1 (SPCX/DRAM/TWTR) and nothing else.
- **P6 — Revision stability.** At T+7 and T+30 days after an
  authorized acquisition, re-pull the 20 PAR 1H requests under new
  manifests with identical request identities (same windows, same
  identity strings; new manifest_ids, pinned when issued) and
  byte-compare against the original receipts. Any differing bytes are
  enumerated bar-by-bar and reported as vendor revision/backfill
  evidence with counts. (This replaces the R3 REV7/REV30 legs, which
  the collector's scope excludes.)
- **P7 — Adjustment basis.** One basis per comparison, never mixed:
  acquisition legs are `adjust=splits`. Split behavior is checked on
  the ADJ windows across the NVDA 2024-06-10 and TSLA 2022-08-25
  split-adjusted start dates; the AAPL window records dividend-window
  behavior on the splits-only basis (dividend drop remains in prices)
  against the comparator pulled on the same basis. Corporate-action
  endpoint weights are NOT assumed — no corporate-action endpoint is
  in this manifest, and none may be added without entitlement evidence
  named in advance.

## 6. What could NOT be satisfied from public primary documentation

Stated exactly, per instructions — none of these were improvised around:

1. **Live account standing.** The plan actually attached to the API key
   and its current usage are observable only through the authenticated
   account/`api_usage` — an authenticated call, out of bounds here.
   Record relies on: public pricing (Basic terms) + the Oct 2026
   account evidence already on file (Basic/Free subscribed; Stage-0
   2 requests HTTP 200). A future authorized run's first act is the
   collector preflight + limiter state, not an account probe.
2. **Empirical interval semantics.** The docs' bar-open statement is a
   claim about returned bytes that only acquired receipts can confirm
   (protocol P2). Status stays INSUFFICIENT by ruling R3.
3. **DRAM venue strings.** The exact `exchange`/`mic_code` strings the
   vendor returns for the Cboe BZX-listed DRAM are not exemplified in
   public docs. The pin uses the frozen plan's exchange + ISO 10383
   MIC; a mismatch fails closed at that receipt (evidence preserved,
   run HOLDs, manifest revision required). It cannot silently pass,
   but it may cost the DRAM PAR credits before halting.
4. **Served intraday depth on Basic.** Public docs state no per-plan
   intraday history-depth limit for /time_series. Whether 1H back to
   2026-04-01 (and the 2022/2023 ADJ windows) is actually served to
   this account is exactly what an authorized acquisition would test;
   the pre-declared insufficiency handling in §1/P5 governs the
   outcomes.

## 7. What remains gated after this preflight

- **Adapter implementation** — a separate step, built to
  `adapter_contract.json` and independently reviewed before use.
- **PR #8 merge** — the collector still lives on an unmerged branch;
  acquisition uses it only after the normal merge path clears.
- **Any vendor call / credit spend** — requires the standing
  authorization path (Mike, per the research loop's hard gates);
  this package makes acquisition *proposable*, not approved.
- **Semantics upgrade + construction un-HOLD** — only via protocol P2
  evidence on real receipts, separately adjudicated.
- **Baseline computation** — only after P1–P7 pass and splits are
  frozen in a separate document.
- **Tiingo** — untouched and unusable as comparator; HOLD unchanged.

## 8. Effort

Completed inside the 60-minute cap (one pass; no repair pass needed).
Zero vendor calls, zero credits, zero spend. No collector, harness,
frozen, or production code was modified; the registry was not touched.
Deliverables are commit-ready only (not committed).
