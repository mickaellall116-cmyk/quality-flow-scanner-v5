# ERD v0.1 — Preregistration Amendment 2 (DRAFT, rev 2)

**Status: DRAFT rev 2 — not frozen, not approved. For adversarial review only.
Incorporates all 10 required corrections from ChatGPT's ADVERSARIAL REVIEW
DECISION (2026-09-26/27, bridge thread; repo issue #3). No ERD performance
data may be generated under this amendment. No candidate-provider data may be
fetched until this amendment is frozen (Mike's explicit approval + ChatGPT
adversarial review sign-off) AND the full pre-data contract (§5) is frozen
and hashed.**

**Authority.** Rev 2 responds to ChatGPT's ADVERSARIAL REVIEW DECISION
(2026-09-26/27): MAYBE / REDLINE REQUIRED on the rev 1 draft. Mike has NOT
approved this amendment. Draft for adversarial review only — exact revised
text + SHA256 hash manifest are returned for review BEFORE any commit or any
candidate-provider data fetch.

**Preservation.** The original frozen preregistration (`new_system/DESIGN.md`,
frozen 2026-09-25) and Amendment 1 (frozen 2026-09-25) are unchanged. Where
this amendment conflicts with Amendment 1, it governs ONLY after freeze.

**Supersession.** Upon freeze, §15 (DATA GATE) of Amendment 1 is superseded in
its vendor-specificity by §§1–4 below. All other Amendment 1 sections (§§1–14,
K1–K10, freeze attestation, checksums) are unchanged and remain frozen.

**Scope note.** No development sample; every parameter fixed a priori.
"Primary candidate" = first to be gated, never pre-selected.

---

## 1. SOURCE-AGNOSTIC TIMING-INTEGRITY GATE

**1.1 Provider eligibility precondition.** Eligible as primary only with a
documented explicit exact-time field (HH:MM:SS or finer, stated timezone) at
>=90% field completeness, where the completeness denominator is the
independently frozen eligible-history frame (§1.2) — NOT provider-returned
rows, NOT the 50-event audit sample. Missing records count missing. Eras or
listing classes a provider does not claim to cover are declared in the frame's
coverage manifest BEFORE gating; claimed eras with missing records count
missing. This closes selection/survivorship leakage at the denominator.

**1.2 Sampling frame and validation sample (frozen before extraction).** The
50-event sample is constructible ONLY from an independent pre-existing frame:
**[DELEGATED — frozen on approval]** the independent frame (frozen ERD
quarterly universe from the securities master + price-data vendor; must be
independent of every candidate earnings-calendar provider — no candidate's
coverage may define the test set). Frozen with the frame: provenance,
inclusion/exclusion rules, coverage manifest (claimed vs unclaimed eras /
listing classes), stratification, seed **[DELEGATED — frozen on approval]**,
canonical serialization (canonical JSON, sorted keys, UTF-8, LF), and the
resulting 50 event identities (permanent security ID + fiscal period +
expected announcement window). Stratification: >=10 BMO, >=10 AMC, >=8
calendar years, >=2 delisted names, >=2 ticker-change events, and
acquisition/entity-transition coverage where the frozen frame contains such
cases — with smaller-population fallback: if the frame holds fewer than the
minimum, take all available and record the shortfall (the stress requirement
is satisfied by the frame's maximum, never by borrowing from a candidate
provider). All frozen and SHA-256 hashed BEFORE any candidate-provider data
pull and BEFORE any market-reaction inspection.

**1.3 Per-event comparison fields.** For each sampled event, record from the
candidate provider and verify against primary sources: ticker, permanent
security ID, fiscal period/year, actual report date, exact report time,
provider availability timestamp (when the record became available, if the
provider versions records — NEVER substitute event/report time for
availability time), provider timing code if any, derived BTO/DTM/AMC bucket
(canonical NYSE calendar, actual early closes — Amendment 1 §1 rules), EPS
actual, EPS consensus, surprise, confirmation status, update/revision
evidence, delisted-name handling, corporate-action/ticker-history handling.
Source document per event in the audit log.

**1.4 Primary-source timestamp semantics (frozen ex ante).** Hierarchy of
controlling timestamp: (1) newswire timestamp (Business Wire / PR Newswire /
GlobeNewswire) as published; (2) company IR press-release page publication
time; (3) embedded document time, only if (1)–(2) are unavailable; (4) SEC
filing acceptance time (8-K Item 2.02) as fallback availability evidence.
When several exist, the EARLIEST availability-evidencing timestamp controls
the bucket derivation. A later update time NEVER overrides the original
publication time. Timezone ambiguity that the hierarchy cannot resolve codes
the event AMBIGUOUS/FAIL per §1.5. Amendment 1 §1 decision-clock rules are
preserved exactly (actual NYSE open/close; early closes honored; during-
session release → EXCLUDE bucket; timestamp exactly at close → EXCLUDE).

**1.5 Fixed denominator — no exclusions.** The denominator is fixed at 50. A
sampled event with missing, ambiguous, vendor-imputed, or conflicting timing
— or with no retrievable primary source — is coded UNVERIFIABLE/FAIL and
STAYS in the denominator. No redraw, no replacement. Primary-source
disagreement is resolved ONLY by the frozen disagreement procedure (§1.4
hierarchy + documented tie rules); unresolved disagreement = FAIL.

**1.6 Pass criteria (frozen).**
- (a) >=48/50 events are exact date+bucket matches (provider-derived bucket
      vs primary-source-derived bucket). UNVERIFIABLE counts as mismatch.
      Combined shortfall >2 FAILS.
- (b) Coverage >=90%: valid-timing events ÷ eligible-history frame
      member-quarters (§1.1 denominator). Missing records count missing.
- (c) PIT/revision spot-check (mechanically decidable): two time-separated
      pulls of the candidate's historical record (pull A at T1, pull B at T2,
      T2 − T1 >= 30 days **[DELEGATED — frozen on approval]**). Comparison
      uses the frozen timing-audit harness semantics (exact duplicates
      collapse and are counted; conflicting duplicates = vendor disagreement,
      investigated fail-closed, never silently resolved; revision matching
      prefers permanent security ID, ticker/date as documented fallback).
      Any change to historical date/time/bucket fields between pulls must be
      accompanied by a versioned revision record carrying an availability
      timestamp; unversioned historical changes = backfill evidence = FAIL.
      Fixed transition sample: **[DELEGATED — frozen on approval]** N events
      (e.g., 20) drawn by frozen seed from the frame, weighted to
      revision-prone cases, with smaller-population fallback. Explicit
      pass/fail: ZERO unversioned historical changes in the transition
      sample. No current-state snapshot may establish historical PIT
      correctness.
- (d) Identifier integrity: every sampled event resolves to a permanent
      security ID and correct fiscal period/year; unresolvable counts
      against (a).
- (e) ZERO-TOLERANCE categories — immediate FAIL on ANY demonstrated
      instance, regardless of the 48/50 floor: future-data leakage
      (availability timestamp after the derived bucket's session);
      systematic timestamp imputation; permanent-ID crossing (one ID
      spanning two distinct operating companies, or vice versa);
      survivorship substitution/redraw; decision-clock override (provider
      bucket contradicting its own exact-time field under Amendment 1 §1
      rules); any revision/backfill mechanism capable of contaminating
      historical availability. These are not "two free errors."
- Any single failure halts ERD. No substitute provider without a new
  preregistration amendment.

**1.7 Audit log.** The 50-row audit log (fields, sources, per-candidate
verdict) is committed to the repo BEFORE any performance work begins.

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
tie-breaks frozen ex ante: provenance strength, then timing-integrity score,
then coverage, then lowest revision-incidence in the transition sample, then
the frozen seed's candidate order. Tiny 49/50 vs 50/50 sample differences do
NOT decide on their own — this is not a beauty contest.

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

## 5. PRE-DATA CONTRACT — HASH MANIFEST (frozen and hashed at freeze)

At freeze, the following artifacts are each SHA-256 hashed and the manifest
committed to main BEFORE any candidate-provider data fetch:

1. This amendment (rev 2 exact text)
2. Sampling frame (provenance, inclusion/exclusion rules, coverage manifest)
3. Exact 50-event list (canonical serialization)
4. Sampler code + config + seed
5. Manual verification procedure + primary-source hierarchy/disagreement rules
6. Calendar/timezone/environment versions
7. PIT/revision test spec (transition sample definition + pass/fail rule)
8. Provider-selection rule (§2.2 tie-breaks)

## Freeze attestation (all unchecked — completed at freeze)

- [ ] Mike's explicit approval (date/medium)
- [ ] ChatGPT adversarial review sign-off on this exact rev 2 text (TYPE + date)
- [ ] SHA-256 manifest (§5) recorded on main
- [ ] GitHub commit of amendment on main
- [ ] Confirmation: no candidate-provider data fetched before freeze
- [ ] Confirmation: no ERD performance results generated before re-freeze

**Status after freeze: READY FOR DATA (amended gate) — integrity audit first,
then performance work.**

## Checksums (tamper-evident: SHA-256 of this document's content *above* this section)

- This amendment rev 2, content above this section (DRAFT — hash recorded at freeze)
- Verify: `awk '/^## Checksums/{exit} {print}' erd-v0.1-preregistration-amendment-2.md | sha256sum`

[Disposition of R1–R5 per the review decision: R1 → §1.5/§1.6(a): UNVERIFIABLE
stays in the denominator as FAIL; R2 → §1.2: delisted/ticker-change kept,
acquisition/entity-transition added with smaller-population fallback; R3 →
§1.1: >=90% completeness against the frozen independent frame denominator;
R4 → §1.6(c): PIT/revision provenance is a hard gate, not a tie-break; R5 →
§1.5 rewritten (no "excluded" language), §1.1 denominator defined, §1.6(c)
revision mechanics specified.]
