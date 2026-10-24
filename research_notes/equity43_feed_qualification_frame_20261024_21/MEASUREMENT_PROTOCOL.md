# MEASUREMENT PROTOCOL — Gate B (FROZEN DESIGN, NOT EXECUTED)
## QF-EQUITY43-FEED-QUALIFICATION-FRAME-20261024-21 r1

**This protocol authorizes nothing.** It is a design document frozen for
review. Executing it requires (i) written rights clearance under Gate A
(RIGHTS_TABLE.md, at minimum Q1–Q3 answered for the tier used) **and**
(ii) Mike's separate approved measurement scope pinning the items in §9.
Permission to measure data is not permission to resume trading; nothing in
this protocol touches production, the paused cohort, or any launch gate.

Provider documentation figures are references, not measurements. In
particular the REST candle delay figure cited in the handoff (0.3–2 minutes)
is UNVERIFIED in the fetched documentation (RIGHTS_TABLE F12/Q5) and this
protocol treats actual delivery latency as UNMEASURED until §5 produces it.

---

## 1. Object of measurement

Prospective 1h U.S.-equity bars for the S1 43-name scope, delivered by
Twelve Data REST `/time_series` (`interval=1h`), measured for:

- **First-seen latency**: for each (symbol, bar), the lag between the bar's
  nominal close instant and the first poll response that contains the
  completed bar.
- **Coverage / missingness**: received bars vs the expected session grid.
- **Revisions**: any change to a bar's bytes after first sighting.
- **Adapter parity**: the exact captured bytes fed through the pinned
  causal observer path (the -17 r2 fork as bundled in -19 r2) must produce
  canonical records and a journal that replay byte-for-byte.

## 2. Environment (isolation)

- Runs only in a **new, separate, read-only staging namespace**
  (`qf_feed_measure_stage`), realpath-disjoint from production and from
  every prior stage, under the -19 staging discipline: no production write
  paths, no production credentials, kill/lock/tamper guards as proven in
  -19 r2.
- The capture process has **no import path** to the production tree; the
  observer bundle is copied in under its -19 r2 pins (observer sha
  `929c1bc4…`, staging gate `aacc4851…`) and pin-verified before any run.
- Raw payloads and receipt hashes go only to **authorized private storage**
  (the private `qf-data-archive` repository, the program's established
  archive) — **never public GitHub**. Only derived, bar-free evidence
  (censuses, quantiles, hashes) may be committed to the scanner repo.
- Subject to Gate A Q3: if archival retention is not confirmed, captured
  payloads are held only for the retention the vendor confirms, and the
  protocol's replay step runs inside that window.

## 3. Expected grid

Sessions and bar boundaries come from the -18 candidate session table
(1,054 sessions, sha `86a1d4ea…`; **candidate, not adopted** — used here
only as the measurement's expectation grid, an adoption-neutral choice
recorded in the run manifest). A regular session expects 7 hourly bars per
symbol with closes at 10:30, 11:30, 12:30, 13:30, 14:30, 15:30, 16:00 ET;
early-close sessions expect the table's truncated grid. Exchange timezone
is America/New_York; all instants recorded in UTC and ET, DST-exact.

## 4. Pilot shape (Phase B1)

- **Pilot symbols (5)**: NVDA, TSLA, AAPL, SPY (continuity with the -08/-13
  pilot bytes and the SPY benchmark role) **plus** the one name from the
  43-name scope with the lowest median DEV-window daily volume, computed
  from the pinned DEV bytes at GO time and pinned in the GO (missing-bar
  stress case). No other names in B1.
- **Duration**: 5 consecutive XNYS sessions from the GO's pinned start
  session, including any early-close session that falls inside the window
  (it is kept, not skipped — early close is a measurement case).
- **Poll ladder** (per symbol per bar): polls at nominal close **+60s,
  +180s, +420s**, stopping the ladder for that bar at first sighting; a
  finalization poll at **close +1800s**. First-seen time is the response
  receipt instant of the first poll whose payload contains the completed
  bar; a bar first seen only at finalization is recorded as
  lag > 420s (right-censored at the ladder, exact at finalization).
- **Revision re-poll**: next session at 08:00 ET, one `/time_series` call
  per pilot symbol covering the full prior session; every field of every
  prior-session bar diffed against its first-seen bytes.
- **Credit arithmetic** (S5: `/time_series` = 1 credit per symbol;
  `/api_usage` = 1 credit): worst case per session-day =
  5 symbols × 7 bars × 4 polls = 140, + revision 5, + `/api_usage`
  checks 4 = **149 credits/day**. Pilot totals: **≤ 745 credits over
  5 sessions; hard pilot cap 800 credits** (one free-tier day-equivalent),
  counted from `/api_usage` reads, not from request logs.
- **B1 exit**: evidence package + adjudication. Expansion is not automatic.

## 5. Capture record (per poll, per bar)

Immutable append-only capture journal in the private archive, one record
per poll attempt and one per first-seen bar:

- symbol, session date, bar nominal start/end (ET + UTC);
- poll request timestamp and response receipt timestamp (UTC + ET,
  monotonic clock reading alongside wall clock);
- HTTP status, provider error body if any, payload SHA-256 (receipt hash),
  full raw payload stored byte-exact;
- for first-seen bars: first-seen lag = receipt instant − nominal close;
  provider as-of/finalization indicators **if the payload carries any**
  (none are documented in S5; absence is recorded, not assumed);
- bar state transitions: MISSING at finalization, LATE (first seen after
  finalization), DUPLICATE (same bar bytes in multiple responses),
  REVISED (any field differs at revision re-poll), each with both hashes;
- `/api_usage` snapshots at session start, midday, and end (observed
  credit usage is a measured output, never estimated).

Candle completion, first availability, and ingestion are three distinct
instants and are never conflated; the observer's synthetic `emitted_at`
(-17) is an ingestion-side construct and is never reported as vendor
arrival.

## 6. Adapter parity (Phase B2, on captured bytes only)

- The exact B1 payloads, in receipt order, are fed through the pinned
  observer in the staging namespace (§2). Canonical records and the
  observer journal are compared **byte-for-byte** against a batch
  reference parse of the same payloads (the -16/-17 comparison method).
- The revision cases actually captured in B1 (REVISED / LATE / MISSING
  bars) are the parity fixtures for incomplete/stale/revised behavior —
  real bytes only; no synthetic substitution. If B1 captures no revision
  case, that parity sub-case is reported **UNMEASURED**, not passed.
- **Stop rule**: at the first material semantic mismatch (schema, bar
  phase, volume-field, or value divergence between streaming and batch
  paths), B2 stops and the mismatch goes to adjudication. No tuning, no
  re-run under altered settings within the same GO.

## 7. Verdict labels the measurement returns

Per symbol and pooled, in the evidence package:

- `LATENCY_MEASURED` — with n, p50 / p95 / p99 / max first-seen lag —
  or `LATENCY_UNMEASURED` if any session's capture is incomplete.
- `COVERAGE` — expected vs received bars per symbol/session, missing and
  late counts (a count, not a pass/fail invention).
- `REVISION_CENSUS` — revised-bar count with field-level diff summary.
- `ADAPTER_PARITY_PASS` / `ADAPTER_PARITY_FAIL` / (per sub-case)
  `UNMEASURED`.
- `CREDIT_USAGE_MEASURED` — provider-reported usage vs the §4/§8 caps.

These labels feed exactly two hold reasons recorded in -19 r2:
`FEED_RIGHTS_UNQUALIFIED` (moved only by Gate A adjudication) and the
feed-readiness half of the S1 gate set. **Everything else remains HOLD
regardless of outcome**: S1 launch, T0, G4 adoption (Gate C accrues
evidence only), fork/calendar adoption, production resume. A perfect
measurement result authorizes no launch and no trade; it converts two
UNMEASURED/UNQUALIFIED labels into measured, adjudicable facts.

## 8. Expansion shape (Phase B3 — separate GO, not part of B1/B2)

Only if B1/B2 adjudicate clean **and** entitlement + quota permit:

- All 43 names, same ladder and records. Free-tier arithmetic check:
  43 × 7 bars × 4 polls = 1,204 credits/day > 800 — **infeasible on the
  free tier**. B3 therefore requires either a rights-cleared paid tier or
  a reduced ladder (2 offsets: +60s/+420s → 602 + revision 43 + usage 4
  = **649 credits/day hard cap**), chosen and pinned in the B3 GO with
  the rights table in hand.
- Duration: 10 sessions pinned in the B3 GO; total-credit hard cap =
  10 × the pinned daily cap, counted from `/api_usage`.

## 9. What Mike's measurement GO must pin

Start session; pilot symbol #5 (per §4 rule) or the reduced-ladder choice
for any expansion; the tier the measurement runs under (with Gate A
answers attached); daily + total credit caps; the private-archive storage
root; the staging bundle pins (observer/gate/table shas as in §2/§3);
the stop conditions of §6/§10 verbatim. A GO missing any pin is not
executable and returns for completion.

## 10. Stop conditions (any phase)

Rights objection or vendor notice; observed usage trending past a cap;
two consecutive 429 responses; first material semantic mismatch (§6);
any production-tree write attempt by the staging guard (the run halts and
the attempt is the headline of the report); any discovery that the tier
in use does not cover a measured name. On any stop: preserve bytes, report
exactly where it stopped, no silent continuation under a new GO.
