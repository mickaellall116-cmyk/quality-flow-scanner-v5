# ERD v0.1 — Preregistration Amendment 2 (DRAFT)

**Status: DRAFT — not frozen, not approved. For adversarial review only. No ERD
performance data may be generated under this amendment. No candidate-provider
data may be fetched until this amendment is frozen (Mike's explicit approval +
ChatGPT adversarial review sign-off) AND the validation sample and selection
algorithm are frozen and hashed.**

**Authority.** This draft responds to ChatGPT's TYPE: RESEARCH PROPOSAL
(2026-09-26, bridge thread; permanent record: repo issue #3), which found
Benzinga Earnings API to be the first non-Zacks source materially matching the
frozen ERD timing requirement. Mike has NOT approved this amendment. It is a
draft for adversarial review only — ChatGPT's explicit instruction is that the
exact text plus intended path/hash procedure be reviewed BEFORE any commit or
any candidate-provider data fetch.

**Preservation.** The original frozen preregistration (`new_system/DESIGN.md`,
frozen 2026-09-25) and Amendment 1 (frozen 2026-09-25) are unchanged. Where this
amendment conflicts with Amendment 1, this amendment governs ONLY after it is
frozen. Nothing outside this amendment changes.

**Supersession.** Upon freeze, §15 (DATA GATE) of Amendment 1 is superseded in
its vendor-specificity by §1–§3 below. All other Amendment 1 sections (§§1–14,
kill criteria K1–K10, freeze attestation, checksums) are unchanged and remain
frozen.

**Scope note.** ERD v0.1 has no development sample: every parameter below is
fixed a priori. "PASS" always refers to validation evidence, never development
data. "Primary candidate" means first to be gated — never pre-selected.

---

## 1. SOURCE-AGNOSTIC TIMING-INTEGRITY GATE — REQUIRED

The 50-event timing-integrity audit is generalized from Intrinio/Zacks-specific
to source-agnostic. Intrinio/Zacks remains an eligible candidate: if eval
access arrives, it runs this same gate with no favoritism.

**1.1 Provider eligibility precondition.** A candidate is eligible as primary
only if it documents an explicit exact-time field (HH:MM:SS or finer, with
stated timezone) at >=90% field completeness over its covered history. A
candidate with no documented exact timestamp, or with timing null/imputed, is
ineligible as primary on current documentation. (This is the current basis for
EODHD's MAYBE-as-backup-only and FMP's FAIL-as-primary judgments; the
judgments are re-evaluated only via new amendment, never silently.)

**1.2 Validation sample (frozen before extraction).** 50 qualifying events:
stratified to include >=10 BMO and >=10 AMC, spanning >=8 distinct calendar
years, and including >=2 delisted names and >=2 ticker-change events where the
primary-source record supports them (identifier-integrity stress). The event
list AND the selection algorithm are frozen and SHA-256 hashed BEFORE any
provider data is pulled and BEFORE any market reaction is inspected.

**1.3 Per-event comparison fields.** For each sampled event, record from the
candidate provider and verify against primary sources (company IR press
release, Business Wire/PR Newswire/newswire timestamp): ticker, permanent
security ID, fiscal period/year, actual report date, exact report time,
provider timing code if any, derived BTO/DTM/AMC bucket (canonical NYSE
calendar, actual early closes honored — Amendment 1 §1 rules), EPS actual, EPS
consensus, surprise, confirmation status, update/revision evidence,
delisted-name handling, corporate-action/ticker-history handling. Record the
source document per event in the audit log.

**1.4 Manual verification procedure.** The IR/SEC/newswire verification
procedure (which sources count as primary, search order, how timestamps are
read, how disagreements between two primary sources are resolved) is written
and hashed ex ante and applied symmetrically to every event and every
candidate provider.

**1.5 Exclusion rule (carried from frozen gate).** Missing, ambiguous,
vendor-imputed, or conflicting timing is EXCLUDED by rule, never replaced.
A sampled event with no retrievable primary source is excluded and never
replaced.

**1.6 Pass criteria (frozen).**
- (a) >=48/50 sampled events are EACH both verifiable against a primary
      source AND an exact date+bucket match (provider-derived bucket vs
      primary-source-derived bucket). Unverifiable and mismatched events
      count identically against the 48; a combined shortfall >2 FAILS.
- (b) Coverage >=90%: events with valid timing classification divided by
      universe-member-quarters, averaged over the study window (carried).
- (c) Zero evidence of systematic revision/backfill patterns (carried).
- (d) Identifier integrity: every sampled event resolves to a permanent
      security ID and correct fiscal period/year; any unresolvable event
      counts against (a).
- Any single failure halts ERD. No substitute provider without a new
  preregistration amendment.

**1.7 Audit log.** The 50-row audit log (fields, sources, per-candidate
verdict) is committed to the repo BEFORE any performance work begins.

---

## 2. PROVIDER SELECTION — PRE-PERFORMANCE ONLY

**2.1 Sealed performance.** No reaction, P&L, expectancy, or any return-derived
number is computed or inspected before the amended gate passes. Provider
choice cannot use returns.

**2.2 Selection criteria (frozen, in order):** (i) timing integrity — the §1.6
match rates; (ii) coverage; (iii) PIT/revision behavior (no backfill; late
revisions versioned, never silently overwritten); (iv) identifier integrity
(permanent IDs, ticker-change/delist handling); (v) survivorship handling;
(vi) reproducibility (documented fields, stable API semantics, versioned
snapshots).

**2.3 Decision rule.** Each candidate gets a full §1 gate report on the SAME
frozen 50-event sample. The primary is the candidate with the highest timing-
integrity score among those passing ALL §1.6 thresholds; ties broken by
coverage, then by revision-behavior cleanliness. If NO candidate passes, ERD
halts — a failing provider is never adopted because downstream returns would
look good.

**2.4 Recording.** All candidate gate scores and the selection decision are
recorded in `new_system/TEST_LEDGER.md` BEFORE any performance work.

**2.5 Current judgments (non-binding; selection is by gate score only):**
Benzinga MAYBE — advance to feasibility validation as primary candidate;
EODHD MAYBE as backup/control — insufficient alone on current exact-time
documentation; FMP FAIL as current primary exact-time source; Alpha Vantage
FAIL as primary event-time source — useful survivorship control. These
judgments change only via new amendment.

---

## 3. DATA-ACCESS GOVERNANCE

No purchase, subscription, trial, contract, or API-key provisioning for any
candidate provider without Mike's explicit approval. Inquiry and written
quotes only until he says so. (Standing rule; this amendment does not
authorize spending.)

---

## 4. DECISION-PACKET COMPATIBILITY

Amendment 1 §14 already carries a per-event `timing_source` field. Under this
amendment it records the selected provider (and provider field versions) per
event. No schema change beyond populating it.

---

## Freeze attestation (to be completed at freeze — all unchecked)

- [ ] Mike's explicit approval (date/medium)
- [ ] ChatGPT adversarial review sign-off on this exact text (TYPE + date)
- [ ] SHA-256 of this amendment at freeze: (recorded below)
- [ ] GitHub commit of amendment on main: (recorded below)
- [ ] Validation sample + selection algorithm frozen and hashed: (hashes)
- [ ] Manual verification procedure frozen and hashed: (hash)
- [ ] Confirmation: no candidate-provider data fetched before freeze
- [ ] Confirmation: no ERD performance results generated before re-freeze

**Status after freeze: READY FOR DATA (amended gate) — integrity audit first,
then performance work.**

## Checksums (tamper-evident: SHA-256 of this document's content *above* this section)

- This amendment, content above this section (DRAFT — hash recorded at freeze):
- Verify: `awk '/^## Checksums/{exit} {print}' erd-v0.1-preregistration-amendment-2.md | sha256sum`

[REVIEW POINTS for ChatGPT — judgment calls I want redlined, not silently kept:
R1. §1.6(a): combined verifiable+mismatch bar of >=48/50 — right strictness, or
    should unverifiable events fail harder than mismatches?
R2. §1.2: >=2 delisted + >=2 ticker-change minimums — necessary stress or
    over-constraining the sample?
R3. §1.1: >=90% exact-time field completeness as primary-eligibility
    precondition — right filter, or too lax/strict?
R4. §2.3 tie-break order (timing integrity > coverage > revision behavior) —
    correct priority?
R5. Anything in §§1–4 that weakens Amendment 1's frozen protections.]
