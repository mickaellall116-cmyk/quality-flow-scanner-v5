# Item 5 — Manual verification procedure (frozen, quoted verbatim from Amendment 2 rev 4)

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
