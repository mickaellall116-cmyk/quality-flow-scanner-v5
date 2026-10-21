# S2 VENDOR-CONVENTION DESK PACKET — task -63 r1

Task: QF-TD-S2-VENDOR-CONVENTION-DESK-PACKET-20261020-63 r1
Spec: Issue #1 comment 6307501961 (-62 adjudication; basis -62 audit
commits dec682e / ee19a07, verdict HOLD accepted).
Scope: ≤35 min, ONE read-only desk pass. No code/test execution, no
Twelve Data API endpoint calls, no credentials, no credits/spend, no
market-data acquisition. This packet REQUESTS a future authorization;
it authorizes nothing itself.
Governing frame (Mike, 2026-10-20): S2 stands or falls on DEMONSTRATED
data-quality purpose, never on return improvement. Binding corrections:
gap/volume patterns are anomaly screens, not authoritative
reconciliation; a later last_change timestamp does not prove earlier
bars invalid — version/consistency evidence is required.

## Terminal verdict (verbatim)

TD_S2_VENDOR_CONVENTION_DESK_PASS__PROBE_AUTHORIZATION_REQUIRED

## 1. Sole ownership

Pre-check before ANY file operation: no td63 stage dir, no td63
worktree, no -63 commit on origin/main, no owner lease (parent
pre-check re-verified by this worker). Atomic owner lease
(O_CREAT|O_EXCL) acquired OUTSIDE the stage at
~/workspace/qf_td63_owner_lease.json; task-unique detached worktree
~/workspace/qf_td63_wt at origin/main 9b6239d. Main working tree never
touched (pre-existing UU forward_test/kama_shadow.json intact); no
stash touched. Lease released LAST, after result-commit remote
verification.

## 2. Documentation snapshots (evidence base)

Three public pages fetched once, hashed, stored in doc_snapshots/
(full receipt: DOC_FETCH_RECEIPT.md):

- time_series.md — sha256 fa940cf49fd05838… (7,888 bytes)
- splits.md — sha256 1afefb8aeb561384… (3,671 bytes)
- last_changes.md — sha256 5b6f9a4a9c0cfb6f… (2,801 bytes)

Disclosure: these are live, mutable vendor pages. The hashes pin the
bytes adjudicated here; they are not a permanence guarantee.

## 3. DOCUMENTED FACTS (from the snapshots only)

time_series (doc_snapshots/time_series.md):
- F1. `adjust` — "Adjusting mode for prices"; available values `all`,
  `splits`, `dividends`, `none`; DEFAULT VALUE: `splits`.
- F2. Cost: "API credits cost: `1` per symbol".
- F3. `outputsize` — "Supports values in the range from `1` to
  `5000`. Default `30` when no date parameters are set, otherwise set
  to maximum."
- F4. Bar datetime semantics: "`datetime` (string) — Datetime at local
  exchange time referring to when the bar with specified interval was
  opened." `timezone` default `Exchange`; timezone applies only to
  intraday intervals; for 1day/1week/1month it is ignored and data is
  strictly Exchange local time. `start_date`/`end_date` default
  location for Stocks is where the exchange is located.
- F5. Response carries OHLC + `volume` per bar; no adjusted/unadjusted
  flag is returned per bar.

splits (doc_snapshots/splits.md):
- F6. Cost and plan gate: "API credits cost: `20` per symbol"; "This
  API endpoint is available on the Grow plan (individual) and the
  Venture plan (business) and above."
- F7. Response fields: `date` ("Stands for the split date"),
  `description` ("Specification of the split event"), `ratio`
  (definition in §5), `from_factor` ("From factor of the split"),
  `to_factor` ("To factor of the split"). Query supports `range`
  (default `last`), `start_date`, `end_date`.
- F8. No announcement, declaration, ex-date-vs-payable, or as-of/PIT
  field exists in the documented response.

last changes (doc_snapshots/last_changes.md):
- F9. Cost: "API credits cost: `1` per request". Purpose: "provides
  the most recent updates to fundamental data for a specified dataset…
  a timestamp indicating when the data was last modified". The
  `endpoint` value list is fundamentals-only and INCLUDES `splits` and
  `dividends`; `time_series` is NOT among the values. Response field
  `last_change`: "The date and time of last changes", format
  `2006-01-02 15:04:05`. Example URL path is `/last_change/…`
  (singular).

## 4. NOT DOCUMENTED (unknowns — never inferred)

- N1. VOLUME adjustment: the `adjust` parameter is documented as a
  mode "for prices" only. Whether adjust="splits" scales volume, and
  by what factor convention, is NOT DOCUMENTED. (-62 unknown U2 stays
  open after the desk step.)
- N2. Intraday-vs-daily adjustment consistency: NOT DOCUMENTED.
- N3. Split-day treatment (which bars sit on which basis around the
  effective date; the boundary bar's basis): NOT DOCUMENTED.
- N4. Request-time back-adjustment as a guarantee (that historical
  bars are always re-based to the current split basis at request
  time): the adjust modes imply a basis choice, but no statement
  guarantees uniform re-basing of previously served bars. NOT
  DOCUMENTED as a guarantee.
- N5. Bar REVISION behavior: whether previously served time_series
  bars are ever rewritten is NOT DOCUMENTED anywhere in the three
  pages, and the only documented change-tracking endpoint
  (last_change) does not cover time_series at all (F9). There is no
  documented vendor mechanism for detecting bar revisions — the
  program's own byte-receipt + repeat-pull machinery (REV legs) is
  the only instrument. (-62 U3 stays open.)
- N6. Split `date` semantics beyond "the split date": ex-date vs
  effective vs payable is NOT DOCUMENTED; no PIT/announcement time
  exists (F8). (-62 E3 gate cannot be satisfied from /splits docs.)
- N7. Pagination basis stability (whether separately paged responses
  share one adjustment basis): pagination is not mentioned on the
  time_series page at all; only the 5000 cap is documented (F3). NOT
  DOCUMENTED. (-62 U4 stays open.)
- N8. Cross-page basis stability between endpoints (e.g. splits
  factors vs time_series adjusted prices): NOT DOCUMENTED.

Net desk result: the documented convention establishes the BASIS
CHOICE (default splits, prices) and the COSTS. Every behavior S2
actually worries about — volume scaling, split-day boundary,
back-adjustment uniformity, revisions — is undocumented. The S4
verification therefore cannot be satisfied from documentation; it
requires the probe bytes in §6. This completes -62 path step 1 with a
negative-but-decisive answer: documentation alone does not qualify
the convention.

## 5. The ratio contradiction (spec item 3)

Both passages are from the SAME official snapshot
(doc_snapshots/splits.md, sha256 1afefb8aeb561384…):

Prose definition of `ratio` (verbatim):
> "The ratio by which the number of a company's outstanding shares of
> stock are increased following a stock split. For example, a
> `4-for-1 split` results in four times as many outstanding shares,
> with each share selling at one forth of its pre-split price"
> [sic — "one forth" is the vendor's spelling]

Example response for that same 4-for-1 split (verbatim):
> `"date": "2020-08-31"`, `"description": "4-for-1 split"`,
> `"ratio": 0.25`, `"from_factor": 4`, `"to_factor": 1`

Adjudication: read literally, the prose defines ratio as the
share-count multiplier — 4 for a 4-for-1 split. The example returns
0.25, which is the PRICE multiplier (and equals to_factor/from_factor
= 1/4). The page nowhere states ratio = to/from or from/to, so the
snapshot does not resolve which quantity the field encodes; the
from/to factors are consistent with both readings of the example.
CLASSIFICATION: **AMBIGUOUS—KNOWN-SPLIT PROBE REQUIRED**. The probe
that resolves it is already designed: the ADJ legs (§6) return bars
across splits whose factors are independently known (NVDA 10:1,
TSLA 3:1); a single authorized /splits response for NVDA or TSLA —
IF entitlement ever exists (F6: Grow+; the account evidence on file
is Basic/Free, see §6 note) — compared against those known factors
settles the field's orientation. Note the S4 price checks in §6 do
NOT consume the /splits ratio field; they verify prices directly, so
the probe program is not blocked on this ambiguity.

## 6. PROBE AUTHORIZATION PACKET (request only — authorizes nothing)

Reconciled against the EXISTING designs; nothing redesigned:
- Frozen manifest TD-PILOT-MANIFEST-R3-20261010
  (research_notes/pilot_harness/request_manifest.json, sha256
  a0a001b7458993ff…): defaults endpoint /time_series, adjust="splits",
  outputsize=5000, expected_credits_per_request=1 — consistent with
  F1/F2/F3 (note: "splits" is also the documented default; the
  manifest's explicit pin is retained as hygiene, behavior identical
  either way on the documented convention).
- ADJ legs as designed in the manifest and in
  TD_ACQUISITION_ADAPTER_PREFLIGHT_20261013.md (sha256
  a5beb9ab9807…), L43 + P7: split behavior checked across the NVDA
  2024-06-10 and TSLA 2022-08-25 split-adjusted start dates.
- Amendment v1 S4 instrument (-62 §4): deterministic pre/post
  price-ratio checks + OHLC-consistency checks across each split,
  DATA_UNQUALIFIED on failure (S5).
- Revision machinery: manifest REV7/REV30 legs (base_request_id
  linkage) and preflight P6 (re-pull identical identities at T+7/T+30,
  byte-compare vs original receipts). This packet requests the
  S2-scoped subset only (ADJ-window re-pulls); the full 20-symbol
  REV program belongs to the separate FRESH-screen authorization and
  is NOT requested here.

### 6a. Exact requests requested

Immediate (single authorized day; all /time_series, interval=1h,
timezone=America/New_York, outputsize=5000, order=ASC; byte receipts
via the existing pilot_acquire receipt machinery — UTC-ms timestamps,
byte counts, SHA-256 of exact response bodies, sanitized params):

| ID | Symbol | Window | adjust | Source design |
|----|--------|--------|--------|---------------|
| (preflight) /api_usage | — | — | — | 1 call; verifies account standing + remaining credits before any data call (-18 precedent) |
| REQ-ADJ-01 | NVDA | 2023-12-13T00:00:00 → 2024-06-21T23:59:59 | splits | manifest ADJ leg (split eff. 2024-06-10, 10:1) |
| REQ-ADJ-02 | TSLA | 2022-03-07T00:00:00 → 2022-09-09T23:59:59 | splits | manifest ADJ leg (split eff. 2022-08-25, 3:1) |
| REQ-ADJ-03 | AAPL | 2026-02-19T00:00:00 → 2026-08-24T23:59:59 | splits | manifest ADJ leg (dividend-window control, P7) |
| REQ-ADJ-01N | NVDA | identical to REQ-ADJ-01 | none | -62 §6 step-2 twin (S4 comparison basis) |
| REQ-ADJ-02N | TSLA | identical to REQ-ADJ-02 | none | -62 §6 step-2 twin (S4 comparison basis) |

Waiting legs (identical request identities/params as REQ-ADJ-01/02,
adjust="splits", new receipt set, base-linked):
- REV+7: REQ-ADJ-01R7, REQ-ADJ-02R7 — execute NO EARLIER than 7 days
  after the immediate leg's acquisition day.
- REV+30: REQ-ADJ-01R30, REQ-ADJ-02R30 — execute NO EARLIER than 30
  days after the immediate leg's acquisition day.
No other calls are requested. In particular: /splits calls are NOT
requested (F6 plan gate Grow+ vs Basic/Free account evidence on file
— entitlement unproven; adding them is a separate decision, and a
plan change would be Mike's purchase decision, outside this packet);
REQ-ADJ-03 gets no `none` twin (its designed role is the
dividend-window record on the splits basis, P7 — the S4 split checks
do not need it); /last_change is not requested (F9: it does not cover
time_series, and per Mike's correction it could not adjudicate bar
validity in any case).

### 6b. Credit ceiling (every assumption explicit)

Documented unit costs (F2, F9): /time_series = 1 credit per
request/symbol; /api_usage = 1 (program record -09). Assumptions:
A1 one credit is charged per HTTP request regardless of rows
returned (docs state per-symbol for time_series; the manifest's
expected_credits_per_request=1 agrees);
A2 ADJ windows return ≈903–917 rows (preflight bound), far below the
5000 cap, so the manifest pagination trigger (exactly 5000 rows)
CANNOT fire on any requested window — pagination allowance = 0;
A3 each request is attempted at most twice (1 initial + 1 retry),
fail-closed after the second failure — a tighter cap than the
manifest's max_attempts=3, adopted for this packet;
A4 the /api_usage preflight is called exactly once per execution day
(immediate day, +7 day, +30 day).

Ceiling arithmetic:
- Immediate day: 6 first attempts (1 usage + 5 data) + ≤6 retries =
  ≤12 credits.
- Each REV day: 3 first attempts (1 usage + 2 data) + ≤3 retries =
  ≤6 credits.
- PROGRAM CEILING: ≤24 credits total across all three days
  (expected case, no retries: 12 credits).
Context, not authorization: this packet is NOT covered by Policy A
(Mike, 2026-10-17), whose 52-credit ceiling applies to the FRESH
screen day only. This packet needs its own authorization from Mike.
The $0/free-tier context (800/day plan allowance on file) is noted
for scale only; credit cost is counted regardless of tier.

### 6c. Precommitted comparisons (performance-blind; frozen now)

C1. adjust=splits vs adjust=none over the identical ADJ-01/02
windows: per-bar OHLC ratio (none/splits) must equal the known
factor (NVDA 10, TSLA 3) for every pre-split bar and 1.0 for every
post-split bar, within the vendor's decimal rounding (dp default);
any bar deviating = S4 failure evidence.
C2. Volume scaling: per-bar volume ratio (splits/none) identifies
the volume convention (×factor pre-split, ×1, or other) — reported
as measured fact; an inconsistent per-bar volume factor inside one
series = mixed-basis evidence.
C3. Split-day treatment: the factor flip's location relative to the
effective session (2024-06-10 / 2022-08-25) is read off C1/C2 and
recorded; no assumption imported.
C4. Amendment v1 S4 checks verbatim on the splits-basis bytes:
deterministic pre/post price-ratio + OHLC-consistency across each
split; failure ⇒ DATA_UNQUALIFIED (S5).
C5. Revision: REV+7/+30 receipts byte-compared against the immediate
receipts; identical bytes = version-stability evidence for those
windows; any difference is enumerated bar-by-bar (preflight P6) and
C1/C4 are re-run on the revised bytes before any conclusion. A byte
difference is revision EVIDENCE, never by itself a contamination
verdict.
C6. Overlap/page consistency: confirm no requested response hit the
5000-row trigger (row counts recorded); if one ever does, the seam
bars are compared across pages under C1 before the series is used.
Explicitly excluded as proof: price-gap or volume-pattern anomaly
screens. An anomaly may only trigger a re-check under C1–C5; it can
never carry a KEEP/REPLACE decision (Mike's correction).

### 6d. Terminal rules for the future probe task

- KEEP S2: C1/C4 fail on acquired bytes (non-uniform scaling, split-
  day basis mixing, or revision rewrites of split-window bars under
  C5 that change C1/C4 outcomes) ⇒ demonstrated data-quality purpose;
  S2 stands and the -60 E1–E5 gates proceed.
- REPLACE S2: C1–C5 all pass on both probes (uniform known-factor
  scaling incl. a consistent volume convention, byte-identical
  revisions) ⇒ no demonstrated purpose for Twelve-Data-adjusted
  data; S2 is retired or narrowed to a pagination-seam guard via
  contract amendment (a governance act, not part of the probe).
- HOLD: any requested leg fails to execute, receipts incomplete,
  entitlement blocks a requested call, or C5 differences cannot be
  classified ⇒ no change; S2 stays frozen as-is.
No outcome of this probe authorizes performance computation; the
probe is performance-blind by construction (historical windows,
adjustment arithmetic only).

### 6e. What completes when

- Immediately on the authorized day: F-convention verification
  against bytes (C1–C4, C6) and the S4 verdict for both known splits.
- Only after +7 days: first revision evidence (C5, REV+7).
- Only after +30 days: the revision leg completes (C5, REV+30) and
  the KEEP/REPLACE/HOLD decision can close. Until then the honest
  interim state is "adjustment verified / revision pending" at best.

## 7. Controls honored

Research-only; zero vendor API calls (public documentation pages
only); no credentials touched; 0 credits spent; no ADJ/REV execution;
no sealed data; no S2 implementation; no -61 rerun; no performance
calculation; no production/trading change; REQ-S2 and corrected
performance remain HOLD; entries PAUSED; no Yahoo/Issue-9/models/
holdouts/tuning. One desk pass; no in-run repair.

## 8. Timing / disclosures

Elapsed: spec fetch 2026-10-21T03:58Z → result-commit remote
verification 2026-10-21T04:03:07Z ≈ 5 min (≤35 budget; this line was
completed in the labeled timing follow-up commit after remote
verification). Repair minutes: 0. Disclosures: (i) the three
documentation pages are mutable vendor content — hashes in
DOC_FETCH_RECEIPT.md pin what was read; (ii) the /splits entitlement
question is recorded from the program's own preflight (§6.1:
Basic/Free standing on file), not from any account probe in this
task; (iii) no required page was inaccessible, so no first-failure
HOLD is recorded.
