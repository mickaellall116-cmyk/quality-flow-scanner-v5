# SPEC — SPLIT-EVENT PRODUCER (GATE-E1…E5) + DETERMINISTIC CORE (scoped spec + synthetic fixtures)

**Task:** QF-TD-SAFEGUARDS-PREP-20261021-84, Part B.
**Authority:** ChatGPT QF NEXT ACTION (Slack TS 1792627306.219339) +
Mike's direction (chat 2026-10-21 20:02 ET).
**Status: CANDIDATE — spec + isolated deterministic core + synthetic
fixtures. NOT integrated, NOT adopted, NO real event source connected,
NO vendor called, NO live split data fetched.**

## 1. Starting point (the -82 item-2 finding)

- **No producer exists.** Verified three ways in -82 (-60 contract
  edge G-EDGE-1 "NO producer"; repo-wide search — only the -59/-61
  consumers touch `split_events`, always with synthetic fixtures;
  -62 concurrence).
- **The consumer is ready and frozen-shaped.** The S2 exclusion
  transform (`s2_split_exclusion_v1.py`, sha 7791ca91…, -59, 16/16
  synthetic) consumes per-symbol event records
  `{symbol, effective_session, source, provenance, as_of, version}`
  (all fields required) and excludes bars+entries for
  {prev(D), D, next(D)} XNYS sessions per event. It fails closed with
  `NON_SESSION_EFFECTIVE` if an event's effective_session is not a
  session, and `MISSING_FIELD`/`EMPTY_FIELD` for incomplete records.
- **The assembly point is missing.** -62 found no assembly point
  upstream of indicators: nothing assembles constructed bars + the
  event list + candidate entries into the transform's inputs.
- The -60 contract specifies the gate a producer must pass:
  **GATE-E1** producer existence (a pinned acquisition leg — endpoint,
  request manifest, receipt schema — must exist before integration);
  **GATE-E2** coverage completeness (the inventory must provably
  cover every symbol × the full bar window; a missing event fails
  SILENTLY, so completeness needs an independent cross-check or a
  vendor attestation bound into a hash-pinned receipt whose
  symbol×window set equals the bars' set exactly; assembly refuses
  on any mismatch); **GATE-E3** PIT availability (each event carries
  `as_of`; assembly refuses if any event's as_of is after the
  dataset's as_of cutoff, if the receipt lacks an acquisition
  timestamp, or if provenance is not bound to the receipt bytes);
  **GATE-E4** calendar-range edge coverage (the calendar range must
  extend ≥1 XNYS session beyond the bars' span on both sides,
  derived from (event inventory ∪ bars span), never set
  independently); **GATE-E5** calendar source pinning (the assembly
  receipt records the calendar source + version the adjacency
  derivation used).

## 2. Producer interface (the spec a real source must feed)

**Input — source batch** (one hash-pinned acquisition receipt):

| field | meaning |
|---|---|
| `acquired_at` | acquisition timestamp (tz-aware ISO) — REQUIRED (E3) |
| `source_pin` | hash binding the batch to its receipt bytes — REQUIRED (E3) |
| `coverage` | `{symbols: [...], window_start, window_end}` — the source's declared completeness claim (E2) |
| `records[]` | `{symbol, effective_date, factor_num, factor_den, announced_at, source}` |

**Input — run parameters:** requested symbols; bars window
(start/end dates); `dataset_as_of` cutoff; `decision_instant` (the
earliest affected decision time, for PIT); `e3_mode` ∈ {"A","B"}
(see §5); a **pinned calendar object** (ordered sessions, early-close
set, and its own `source`/`version`/`pin` for E5).

**Output — envelope** (see §4 for the event schema): state, producer
+ schema versions, e3_mode, basis, the calendar stamp (E5), the
coverage declaration echoed, source pin + acquisition timestamp, the
inclusion range actually used, the event list (sorted by
(symbol, effective_session)), the PIT-excluded ledger, and a SHA-256
over the canonical JSON of the event list.

## 3. What a real event SOURCE must provide (qualification requirements)

The producer core does not create evidence; a source qualifies to
feed it only if it provides, per batch:

1. **Dated events with factors** — symbol, stated effective date,
   and the split factor as an exact numerator/denominator pair
   (floats derived from prose, e.g. "4-for-1", are not acceptable
   without the pair — cf. the -63 desk packet's ratio contradiction).
2. **An independent `announced_at`** per event — a timestamped
   announcement record (exchange notice, filing timestamp, vendor
   field with documented semantics), not the effective date restated.
   Without it, GATE-E3 cannot be evaluated and the batch is refused.
3. **A coverage attestation** — the exact symbol × window set the
   batch claims to enumerate completely, bound into the same pinned
   receipt (E2). "We returned what we found" is not coverage.
4. **A revision policy** — how corrections/re-issues are versioned,
   so a re-pulled batch is detectably different (new pin), never a
   silent overwrite.
5. **Receipt bytes** that can be hash-pinned and archived
   write-once (the qf-data-archive pattern), so the event list is
   re-derivable from the pinned input by re-running this core.

Candidate source classes (NONE selected, NONE authorized by this
task): a vendor corporate-actions endpoint (the documented one —
Twelve Data `/splits` — is Grow+ paid-tier and was **excluded** in
the -63 packet; using it or any alternative is a separate
authorization with cost/terms review); an exchange/SEC-filing-derived
offline enumeration (defensible provenance, but its completeness
evidence under E2 is the hard part and would need its own design).
See §7 for what remains.

## 4. Output event schema (what S2 consumes)

Each emitted event carries the six fields the -59 transform contract
requires, named identically, plus factor/audit extensions:

| field | source |
|---|---|
| `symbol` | record |
| `effective_session` | stated date normalized onto the calendar (§6) — always a session |
| `source` | record's source identifier |
| `provenance` | the batch `source_pin` (E3 binding) |
| `as_of` | the event's `announced_at` |
| `version` | producer schema version (`split-events-v1`) |
| `effective_date_stated` | the date as stated, before normalization |
| `factor_num`, `factor_den` | record (exact pair) |
| `announced_at` | record |
| `edge_flags` | `EDGE_NONSESSION_STATED_DATE`, `EDGE_EARLY_CLOSE_SESSION` |
| `pit_status` | `ANNOUNCED_ON_OR_BEFORE_DECISION` / `ANNOUNCED_AFTER_DECISION` |

## 5. PIT behavior behind the UNFROZEN E3 switch

E3 (the decision-time PIT rule) is **not frozen** — Mike's choice
between (A) a decision-time rule (an event is usable only if
independently sourced `announced_at` ≤ the earliest affected
decision) and (B) a retrospective data-quality exclusion labeled
non-tradable remains open, with no silent middle. The core therefore
**refuses to run with the mode unset** (`E3_MODE_UNSET`); there is
no default. With a mode set:

- **Mode A:** events announced after `decision_instant` are excluded
  from the event list and written to the envelope's `excluded`
  ledger with reason `PIT_ANNOUNCED_AFTER_DECISION`. Basis stays
  `DECISION_TIME`.
- **Mode B:** such events are included, flagged
  `pit_status=ANNOUNCED_AFTER_DECISION`, and if any is included the
  envelope `basis` becomes `RETROSPECTIVE_NON_TRADABLE` — an
  after-decision event can never silently look decision-time.

Independently of the mode, GATE-E3's dataset rule always applies:
an event whose `announced_at` is after `dataset_as_of` refuses the
whole run (`AS_OF_AFTER_DATASET_CUTOFF`) — that is a provenance
defect, not a PIT-mode question.

## 6. Determinism + fail-closed semantics

- **Refusals** (ProducerRefusal, stable codes): `E3_MODE_UNSET`,
  `E3_MODE_INVALID`, `PROVENANCE_UNBOUND` (no acquisition timestamp
  or no source pin), `AS_OF_AFTER_DATASET_CUTOFF`,
  `COVERAGE_INCOMPLETE` (requested symbols/window outside the
  declared coverage), `CALENDAR_RANGE_INSUFFICIENT` (calendar does
  not extend ≥1 session beyond the bars span on both sides, or a
  stated date has no session at/after it),
  `DUPLICATE_OR_CONFLICTING_EVENT` (two records sharing
  (symbol, stated effective date) — identical or conflicting;
  the core does not adjudicate duplicates), `MISSING_FIELD`,
  `INVALID_FACTOR`, `INVALID_TIMESTAMP` (the last three mirroring
  the S2 transform's vocabulary). A refusal produces NO event list.
- **Absent source ≠ empty result:** a missing batch returns state
  **`NO_PRODUCER_OUTPUT`** with `events=None` and an explicit note.
  A covered source with zero in-scope events returns state `OK`
  with `events=[]`. Downstream, "no producer ran" can never be
  mistaken for "there were no splits".
- **Calendar edges:** a stated effective date that is not a session
  normalizes to the NEXT session with flag
  `EDGE_NONSESSION_STATED_DATE` (stated date preserved) — the
  producer never emits a non-session effective (S2 would refuse it)
  and never drops the event silently. An event effective on an
  early-close session keeps that session, flagged
  `EDGE_EARLY_CLOSE_SESSION`.
- **Adjacency scope (E4):** inclusion range is
  [prev_session(first bars session), next_session(last bars
  session)] — an event effective one session outside the bars
  window still moves the window's edge sessions under S2's
  {prev, D, next} rule, so it is in scope; events further out are
  out of scope (not an error).
- **Determinism:** sorted output, canonical-JSON hash in the
  envelope; identical inputs produce byte-identical envelopes
  (fixture P10).

## 7. How S2 would consume this (the missing assembly point)

```
constructed bars (constructor chain) ──┐
                                       ├──► ASSEMBLY (to be built under its
producer envelope (this core, fed by   │     own GO): verify envelope state=OK,
 a qualified source, E3 mode frozen) ───┤     calendar pin == the pinned artifact,
                                       │     coverage == bars symbol×window set
candidate entries (from bars) ─────────┘     exactly (E2) ──► S2 transform (-59)
                                                    │  {prev,D,next} exclusion
                                                    ▼
                                     post-exclusion bars + entries ──► indicators
```

The assembly verifies, before the transform runs: envelope state is
OK (a NO_PRODUCER_OUTPUT envelope stops the build — S2 cannot run
on an absent producer); the envelope's calendar stamp matches the
pinned calendar artifact the fold materializer will use (E5); the
coverage set equals the bars' symbol×window set exactly (E2); the
E3 mode in the envelope is the FROZEN mode (an envelope produced
under the other mode, or with basis RETROSPECTIVE_NON_TRADABLE,
cannot feed a decision-time run). Only then does the -59 transform
consume `events` (its six required fields are a subset of §4).

## 8. Deterministic core + fixture evidence

- Module: `producer/split_event_producer.py`
  (`PRODUCER_VERSION = "split-producer-core-candidate-1"`), pure
  stdlib, no I/O, no network.
- Suite: `producer/test_split_event_producer.py` — synthetic
  calendar (Jun–Jul 2024 XNYS shape supplied as fixture data) and
  invented records. **Result: 23/23 checks PASS, repeat-identical**,
  pinned env (CPython 3.12.3 / pandas 2.2.3, `unshare -n`). Full
  output: `TEST_EVIDENCE.md`, Part B.

Checks: P1 enumeration + S2 fields + envelope stamps · P2 non-session
stated dates (Saturday; the Jul-4 holiday) normalized + flagged ·
P3 early-close session flagged, not moved · P4 mode A exclusion +
ledger / mode B inclusion + basis flip / unset refuses · P5
identical + conflicting duplicates refuse · P6 NO_PRODUCER_OUTPUT vs
covered-empty OK · P7 coverage refusals · P8 calendar-range refusal ·
P9 provenance refusals · P10 byte-identical repeat · P11 adjacency
scope · P12 missing-field / invalid-factor refusals.

## 9. What remains before this producer can run on real data

Stated plainly: **the core can be ready while S2 integration stays
gated.** Remaining, in dependency order:

1. **A qualified event SOURCE** (§3) — none exists. The documented
   vendor route (Twelve Data `/splits`) is Grow+ paid-tier and
   excluded; any vendor leg or filing-derived enumeration is a
   separate authorization (Mike) + adjudicated design (GATE-E1's
   "pinned acquisition leg" must be created, not assumed).
2. **The E3 PIT freeze** — Mike's (A) vs (B) decision. The core
   refuses to run without it; no fixture here sets it for real data.
3. **The assembly point** (§7) — a new component under its own GO,
   binding bars + envelope + entries, with the E2/E5 verifications.
4. **S2's purpose disposition** — per Mike's governing frame
   (2026-10-20) and the -62 audit: S2's exclusion still needs its
   demonstrated data-quality purpose resolved (the -75 sampled
   windows showed uniform adjustment) before integration is
   proposed — the producer being ready does not settle that
   question.
5. Adoption pins + re-proof for the producer/assembly as new chain
   elements (`REPROOF_PLAN.md`).
