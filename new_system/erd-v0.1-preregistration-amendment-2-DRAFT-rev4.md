# ERD v0.1 — Preregistration Amendment 2 (DRAFT, rev 4)

**Status: DRAFT rev 4 — not frozen, not approved. For adversarial review only.
Rev 4 supersedes rev 3 on exactly two wording points (§1.2 data-independence
rule; Authority freeze language) per ChatGPT's 2026-09-28 REVIEW (PASS TO
MATERIALIZE PRE-DATA CONTRACT / NOT YET FREEZE-READY); all substantive
content is unchanged from rev 3.
Resolves all six required corrections from ChatGPT's REVIEW (2026-09-28,
issue #1): MAYBE / REDLINE REQUIRED — DO NOT FREEZE rev 2. No ERD performance
data may be generated under this amendment. No candidate-provider data may be
fetched until this amendment is frozen (Mike's explicit approval + ChatGPT
adversarial review sign-off) AND the full pre-data contract (§5) is frozen
and hashed.**

**Authority.** Rev 3 responds to ChatGPT's 2026-09-28 adversarial review of
rev 2. Mike has NOT approved this amendment. Draft for adversarial review
only — exact revised text + complete pre-data manifest are returned for
review BEFORE freeze or any candidate-provider data fetch.

**Preservation.** The original frozen preregistration (`new_system/DESIGN.md`,
frozen 2026-09-25) and Amendment 1 (frozen 2026-09-25) are unchanged. Where
this amendment conflicts with Amendment 1, it governs ONLY after freeze.

**Supersession.** Upon freeze, §15 (DATA GATE) of Amendment 1 is superseded in
its vendor-specificity by §§1–4 below — including its "≥10 BMO, ≥10 AMC"
sample stratification, which is replaced by §1.2/§1.2A. All other Amendment 1
sections (§§1–14, K1–K10, freeze attestation, checksums) are unchanged and
remain frozen.

**Scope note.** No development sample; every parameter fixed a priori.
"Primary candidate" = first to be gated, never pre-selected.

---

## 1. SOURCE-AGNOSTIC TIMING-INTEGRITY GATE

**1.1 Provider eligibility precondition.** Eligible as primary only with a
documented explicit exact-time field (HH:MM:SS or finer, stated timezone) at
≥90% field completeness, where the completeness denominator is the
independently frozen eligible-history frame (§1.2) — NOT provider-returned
rows, NOT the 50-event audit sample. Missing records count missing. Eras or
listing classes a provider does not claim to cover are declared in the frame's
coverage manifest BEFORE gating; claimed eras with missing records count
missing. This closes selection/survivorship leakage at the denominator.

**1.2 Sampling frame and validation sample (frozen before extraction).**
The 50-event sample is constructible ONLY from an independent pre-existing
frame, and the frame contains NO announcement-timing information whatsoever.

- **Frame definition (literal).** The frame is the ERD quarterly universe
  membership table per Amendment 1 §§7–8 (U.S. primary-listed common
  operating companies; 20-completed-session liquidity rule; permanent
  security ID as identity), for fiscal quarters with quarter-end date from
  2012-01-01 through the last complete calendar quarter-end before freeze.
  One row per (permanent security ID, fiscal year, fiscal quarter).
  Row fields: permanent security ID, fiscal year, fiscal quarter,
  quarter-end date, delisted flag (delisted as of freeze), ticker-change
  flag (≥1 ticker change in the security's history per the master),
  acquisition/entity-transition flag (per the master). NO announcement
  date, NO announcement time, NO timing code, NO expected-announcement
  window, NO vendor timing label of any kind.
- **Frame provenance (frozen in manifest item 2).** Securities-master vendor
  name + database version/date, price-data vendor name + version/date,
  universe build code, coverage manifest (claimed vs unclaimed eras/listing
  classes). The frame is built, hashed, and committed BEFORE any
  candidate-provider data fetch, trial/API access, licensed-feed extraction,
  or use of candidate-provider records in frame construction. Prior vendor
  inquiries/public-document review do not define frame membership and are
  retained in the search ledger. Independence is enforced by this build
  order plus the prohibition on using any candidate provider's data in
  frame construction — not by vendor naming.
- **Inclusion/exclusion (literal).** Include every frame row with
  quarter-end in [2012-01-01, last complete quarter-end at freeze].
  Exclude rows whose permanent security ID cannot be resolved to a single
  operating company; each such row is listed in the coverage manifest with
  its reason and can never enter the sample.
- **Event identity (literal).** A sampled event is identified ONLY by
  (permanent security ID, fiscal year, fiscal quarter, quarter-end date).
- **Stratification quotas (all provider-independent).** ≥8 distinct calendar
  years (by quarter-end date); ≥2 delisted names; ≥2 ticker-change events;
  acquisition/entity-transition coverage where the frame contains such
  cases (take up to 2; fewer if the frame holds fewer).
- **Draw mechanics (literal, deterministic).**
  1. Sort the eligible frame canonically (permanent security ID ascending,
     then fiscal year, then fiscal quarter).
  2. Seed a PRNG with the frozen literal seed **20260928**; Fisher–Yates
     shuffle the sorted list using only that PRNG (the frozen sampler code
     implements the shuffle; its SHA-256 is manifest item 4).
  3. Quota pass, in fixed priority order — (a) years: walk the shuffled
     list, admit the first member of each new quarter-end year until 8
     distinct years are represented; (b) delisted: walk the shuffled list,
     admit the first 2 delisted members not already admitted; (c)
     ticker-change: first 2 not already admitted; (d) acquisition/
     entity-transition: first 2 not already admitted.
  4. Fill pass: walk the shuffled list in order, admitting non-admitted
     members until the sample reaches exactly 50.
  5. Reproducibility self-check: re-running the frozen sampler on the
     frozen frame must reproduce the frozen 50-event list byte-for-byte.
- **Smaller-population fallback (literal).** If a quota class holds fewer
  members than the quota, take all available and record the shortfall in
  the audit log; the stress requirement is satisfied by the frame's
  maximum, never by borrowing from a candidate provider. If the eligible
  frame holds fewer than 50 members total, the gate is not runnable as
  specified: ERD halts and the halt is reported. No redraw from outside
  the frame under any circumstance.
- **Seed (frozen literal).** 20260928. Not delegated.

**1.2A BMO/AMC quotas removed from membership.** The ≥10 BMO / ≥10 AMC
quotas are REMOVED from sample membership: no timing label may determine
whether an event enters the 50, because no timing label exists in the
frame. After the 50 are frozen AND after provider/primary-source
verification is complete, the audit log reports the observed distribution
of primary-source-derived buckets (BTO / AMC / DTM / UNVERIFIABLE) as a
descriptive check. An observed count below 10 in BMO or AMC is recorded
as a coverage caveat; it does not trigger redraw, replacement, or gate
failure on its own (the §1.6 thresholds govern).

**1.3 Per-event comparison fields.** For each sampled event, record from the
candidate provider and verify against primary sources: ticker, permanent
security ID, fiscal period/year, actual report date, exact report time,
provider availability timestamp for the timing fields (when the record
became available — NEVER substitute event/report time for availability
time), provider timing code if any, derived BTO/DTM/AMC bucket (canonical
NYSE calendar, actual early closes — Amendment 1 §1 rules), EPS actual,
EPS consensus, surprise, confirmation status, update/revision evidence,
delisted-name handling, corporate-action/ticker-history handling. Source
document per event in the audit log.

**1.4 Primary-source timestamp semantics — ONE deterministic rule
(precedence-first).** The §1.4 hierarchy and the "earliest controls" rule
are replaced by the single rule below; no alternative reading is permitted.

1. Source classes in strict precedence order: (1) newswire timestamp
   (Business Wire / PR Newswire / GlobeNewswire) as published; (2) company
   IR press-release page publication time; (3) embedded document time, only
   if classes (1)–(2) yield no retrievable legitimate timestamp; (4) SEC
   filing acceptance time (8-K Item 2.02) as fallback availability
   evidence.
2. Use the HIGHEST-precedence class that yields a retrievable legitimate
   publication timestamp for the event. Lower-precedence classes are not
   consulted once a higher class yields a timestamp — even if a
   lower-precedence timestamp is earlier.
3. Within the controlling class, use the ORIGINAL/EARLIEST publication
   timestamp. A later update or correction time in the same class NEVER
   overrides the original.
4. Tie within the controlling class (two same-class sources, different
   times): the earliest controls; if still unresolvable, the event is
   AMBIGUOUS/FAIL per §1.5.
5. All timestamps normalized to America/New_York. If the source timezone
   cannot be determined from the source itself, the event is
   AMBIGUOUS/FAIL.
6. Amendment 1 §1 decision-clock rules are preserved exactly (actual NYSE
   open/close; early closes honored; during-session release → EXCLUDE
   bucket; timestamp exactly at close → EXCLUDE).

**1.5 Fixed denominator — no exclusions.** The denominator is fixed at 50. A
sampled event with missing, ambiguous, vendor-imputed, or conflicting timing
— or with no retrievable primary source — is coded UNVERIFIABLE/FAIL and
STAYS in the denominator. No redraw, no replacement. Primary-source
disagreement is resolved ONLY by the frozen §1.4 rule; unresolved
disagreement = FAIL.

**1.6 Pass criteria (frozen).**
- (a) ≥48/50 events are exact date+bucket matches (provider-derived bucket
      vs primary-source-derived bucket). UNVERIFIABLE counts as mismatch.
      Combined shortfall >2 FAILS.
- (b) Coverage ≥90%: valid-timing events ÷ eligible-history frame
      member-quarters (§1.1 denominator). Missing records count missing.
- (c) PIT/revision gate (mechanically decidable; detection AND evidence).
      Two time-separated pulls of the candidate's historical record (pull A
      at T1, pull B at T2, T2 − T1 ≥ **45 days**, frozen literal).
      Comparison uses the frozen timing-audit harness semantics (exact
      duplicates collapse and are counted; conflicting duplicates =
      vendor disagreement, investigated fail-closed, never silently
      resolved; revision matching prefers permanent security ID,
      ticker/date as documented fallback). Fixed transition sample:
      **N = 20** events, drawn by Fisher–Yates seeded shuffle of the
      frozen 50 with frozen literal seed **20260929**, first 20 taken —
      no revision-prone weighting, no judgmental oversampling.
      Pass requires ALL of: (i) ZERO unversioned historical changes to
      date/time/bucket fields between pulls in the transition sample —
      any unversioned change = backfill evidence = FAIL; (ii) the provider
      supplies versioned revision records carrying availability timestamps
      for the transition sample's timing fields, with record-version
      semantics documented in the build log BEFORE the gate runs —
      undocumented or contradicted version semantics = FAIL; (iii) the
      availability claim is corroborated by versioned provider evidence
      OR by an explicitly frozen independent archival equivalent (named
      and frozen before the gate; ad-hoc archives do not count) —
      otherwise provider PIT status is FAIL/UNVERIFIED. The two-pull test
      is a backfill tripwire: passing it alone NEVER establishes
      historical as-seen correctness. No current-state snapshot may
      establish historical PIT correctness.
- (d) Identifier integrity: every sampled event resolves to a permanent
      security ID and correct fiscal period/year; unresolvable counts
      against (a).
- (e) ZERO-TOLERANCE categories — immediate FAIL on ANY demonstrated
      instance, regardless of the 48/50 floor. The leakage category uses
      the canonical decision-time inequality:
      `available_at + LATENCY_BUFFER ≤ decision_time`,
      where `available_at` = the provider's versioned availability
      timestamp for the event's timing fields (never the event/report
      time), `LATENCY_BUFFER` = **15 minutes** (frozen literal), and
      `decision_time` = 09:30 ET on session S (the regular-session open of
      the reaction session derived under Amendment 1 §1). A record whose
      availability timestamp is missing or unversioned fails the
      availability claim for that event (UNVERIFIABLE/FAIL under (a));
      systematic absence of versioned availability = PIT status
      FAIL/UNVERIFIED under (c). Other zero-tolerance classes: systematic
      timestamp imputation; permanent-ID crossing (one ID spanning two
      distinct operating companies, or vice versa); survivorship
      substitution/redraw; decision-clock override (provider bucket
      contradicting its own exact-time field under Amendment 1 §1 rules);
      any revision/backfill mechanism capable of contaminating historical
      availability. These are not "two free errors."
- Any single failure halts ERD. No substitute provider without a new
  preregistration amendment.

**1.7 Audit log.** The 50-row audit log (fields, sources, per-candidate
verdict, observed bucket distribution per §1.2A, quota shortfalls if any)
is committed to the repo BEFORE any performance work begins.

---

## 2. PROVIDER SELECTION — PRE-PERFORMANCE ONLY

**2.1 Sealed performance.** No reaction, P&L, expectancy, or any
return-derived number is computed or inspected before the amended gate
passes. Provider choice cannot use returns — not to choose, not to break
ties.

**2.2 Pass/fail first.** A candidate is selectable ONLY if it passes EVERY
§1.6 threshold (including the zero-tolerance categories). Among passing
candidates, preference order: (i) reproducibility/PIT provenance strength
(versioned snapshots, documented revision semantics, stable field
definitions); (ii) timing-integrity score; (iii) coverage. Deterministic
tie-breaks frozen ex ante: provenance strength, then timing-integrity
score, then coverage, then lowest revision-incidence in the transition
sample, then alphabetical by provider name. Tiny 49/50 vs 50/50 sample
differences do NOT decide on their own — this is not a beauty contest.

**2.3 Decision rule.** Every candidate gets a full §1 gate report on the SAME
frozen 50-event sample. If NO candidate passes all hard gates, ERD halts — a
failing provider is never adopted because downstream returns would look good.

**2.4 Search ledger.** `new_system/TEST_LEDGER.md` retains EVERY provider
considered, rejected, unavailable, or partially audited, with reason and
date, plus all candidate gate scores and the selection decision — recorded
BEFORE any performance work. The full search path is preserved; no cycling
through vendors until one happens to pass.

**2.5 Current judgments (non-binding; selection by gate score only):**
Benzinga MAYBE — primary candidate for feasibility validation; EODHD MAYBE
backup/control; FMP FAIL as current primary exact-time source; Alpha Vantage
FAIL as primary event-time source, useful survivorship control. Changeable
only via new amendment.

---

## 3. DATA-ACCESS GOVERNANCE

No purchase, subscription, trial, contract, or API-key provisioning for any
candidate provider without Mike's explicit approval. Inquiry and written
quotes only until he says so. (Standing rule; this amendment does not
authorize spending.)

---

## 4. DECISION-PACKET COMPATIBILITY

Amendment 1 §14 already carries a per-event `timing_source` field; under
this amendment it records the selected provider (and provider field
versions) per event. No other schema change.

---

## 5. PRE-DATA CONTRACT — FULL MANIFEST (frozen and hashed at freeze)

At freeze, each artifact below is SHA-256 hashed and the manifest committed
to main BEFORE any candidate-provider data fetch. Nothing in this
amendment is "to be frozen at freeze" after approval — the complete
contract exists and is reviewable BEFORE provider access.

| # | Artifact | Content spec | SHA-256 |
|---|----------|--------------|---------|
| 1 | This amendment (rev 4 exact text) | this file, content above Checksums | `[RECORDED AT FREEZE]` |
| 2 | Sampling frame | frame build code + provenance log (securities-master vendor/version/date, price vendor/version/date, universe build code per Amd.1 §§7–8, coverage manifest with claimed/unclaimed eras and unresolvable-ID rows) + frozen frame file (canonical JSON, §1.2 row fields) | `[RECORDED AT FREEZE]` |
| 3 | Exact 50-event list | canonical JSON: sorted keys, UTF-8, LF; each event = (permanent security ID, fiscal year, fiscal quarter, quarter-end date); NO timing fields | `[RECORDED AT FREEZE]` |
| 4 | Sampler code + config | frozen sampler implementing §1.2 draw mechanics; config = seed 20260928, quota order, fill rule; reproducibility self-check log | `[RECORDED AT FREEZE]` |
| 5 | Manual verification procedure | §1.4 precedence-first rule + disagreement procedure (§1.5) + per-event source-documentation template; primary-source hierarchy frozen verbatim | `[RECORDED AT FREEZE]` |
| 6 | Calendar/timezone/environment versions | NYSE calendar source + version (actual early closes), tzdata version, Python version, America/New_York DST rules in effect | `[RECORDED AT FREEZE]` |
| 7 | PIT/revision test spec | transition sample definition (N=20, seed 20260929, Fisher–Yates on frozen 50, first 20) + T2−T1 ≥ 45 days + §1.6(c) pass/fail rule verbatim + version-semantics documentation requirement | `[RECORDED AT FREEZE]` |
| 8 | Provider-selection rule | §2.2 preference order + tie-breaks verbatim (alphabetical final tie-break) | `[RECORDED AT FREEZE]` |
| 9 | Availability/leakage spec | §1.6(e) canonical inequality verbatim: `available_at + 15min ≤ 09:30 ET on S`; availability-timestamp field definition; UNVERIFIABLE handling | `[RECORDED AT FREEZE]` |
| 10 | Issue #3 supersession annotation | exact annotation text from §6, posted to issue #3 at freeze | `[RECORDED AT FREEZE]` |
| 11 | Independent archival equivalent (if any) | named archive + freeze date + coverage statement; "none" is a valid frozen value (then versioned provider evidence alone must carry the availability claim per §1.6(c)(iii)) | `[RECORDED AT FREEZE]` |

## 6. ISSUE #3 SUPERSESSION ANNOTATION (frozen text — posted at freeze)

At freeze, issue #3 ("ERD v0.1 — non-Zacks earnings-data feasibility gate")
is annotated as SUPERSEDED on exactly one point, with the following frozen
text posted as an issue comment:

> SUPERSEDED (per ERD v0.1 Amendment 2, frozen <date>, commit <hash>): the
> pass-criteria bullet "events with missing/ambiguous timing are excluded
> by rule" is replaced. The validation sample denominator is fixed at 50;
> sampled events with missing, ambiguous, vendor-imputed, or conflicting
> timing — or with no retrievable primary source — are coded
> UNVERIFIABLE/FAIL and STAY in the denominator. No exclusion, no redraw,
> no replacement. All other issue #3 content is unchanged.

## Freeze attestation (all unchecked — completed at freeze)

- [ ] Mike's explicit approval (date/medium)
- [ ] ChatGPT adversarial review sign-off on this exact rev 4 text (TYPE + date)
- [ ] SHA-256 manifest (§5, all 11 artifacts) recorded on main
- [ ] Issue #3 supersession annotation posted (§6)
- [ ] GitHub commit of amendment on main
- [ ] Confirmation: no candidate-provider data fetched before freeze
- [ ] Confirmation: no ERD performance results generated before re-freeze

**Status after freeze: READY FOR DATA (amended gate) — integrity audit first,
then performance work.**

## Checksums (tamper-evident: SHA-256 of this document's content *above* this section)

- This amendment rev 4, content above this section (DRAFT — hashes recorded at freeze)
- Verify: `awk '/^## Checksums/{exit} {print}' erd-v0.1-preregistration-amendment-2-DRAFT-rev3.md | sha256sum`

## Disposition of the six 2026-09-28 review corrections

- C1 (provider-independent sample identity) → §1.2 rewritten: frame
  contains zero announcement-timing fields; event identity is (perm ID,
  fiscal year/quarter, quarter-end date) only; §1.2A removes BMO/AMC quotas
  from membership and replaces them with a post-immutability descriptive
  report; frame independence enforced by frozen build order (built+hashed
  before any candidate contact).
- C2 (no delegated choices) → every value frozen literally in-text:
  seed 20260928; transition interval ≥45 days; transition N=20; transition
  seed 20260929 with unweighted Fisher–Yates; smaller-population fallback
  (take-all + record shortfall; <50 total → gate not runnable → halt);
  alphabetical final tie-break; canonical serialization spec; full
  11-artifact manifest (§5) with hash placeholders filled at freeze.
- C3 (canonical decision-time inequality) → §1.6(e) rewritten:
  `available_at + 15min ≤ 09:30 ET on S`; event/report time never
  substitutes for availability; missing/unversioned availability =
  UNVERIFIABLE/FAIL per event, systematic absence = PIT FAIL/UNVERIFIED.
- C4 (§1.4 conflict) → §1.4 replaced by ONE precedence-first rule:
  highest-precedence available class controls; earliest original timestamp
  within that class; lower classes never consulted; ties/timezone
  ambiguity → AMBIGUOUS/FAIL.
- C5 (issue #3 consistency) → §6 freezes the exact supersession
  annotation; fixed-50 denominator (§1.5) governs from freeze.
- C6 (PIT evidence as gate) → §1.6(c) rewritten: two-pull (≥45d)
  tripwire PLUS mandatory versioned revision records with documented
  semantics PLUS corroboration by versioned evidence or a frozen
  independent archival equivalent; otherwise FAIL/UNVERIFIED. Two-pull
  pass alone never establishes PIT correctness.
