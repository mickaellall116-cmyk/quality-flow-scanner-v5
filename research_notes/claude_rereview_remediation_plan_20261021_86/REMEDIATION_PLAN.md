# REMEDIATION PLAN — Claude's independent -82 re-review (task -86)
## DESIGN/FIXTURE PLAN ONLY — nothing is executed except F5 and F6 (documentation)

**Authority:** ChatGPT's relay of Claude's verdict, Slack TS
1792628218.568909 (2026-10-21 20:16:58 ET, read firsthand), under
Mike's standing direction (finish blockers, no research
expansion, evidence not status).

**Claude's verdict, for traceability.** Package integrity PASS
(-83 handoff 15/15; -82 manifest 13/13; synthetic suites 14/14
and 7/7 independently reproduced). **PASS:** TSLA label
correction; July-3 (-56) correction; split-event absence
disclosure. **HOLD:** UX51 designation; R1–R5 session handling;
constructor; the completeness instrument (the TSLA *label*
passed; the *checker* did not). NO CP2, no performance run, no
shadow activation, no vendor calls/spend, no holdout access —
all preserved by this plan.

**Scope discipline.** This package DESIGNS every remediation and
names the smallest synthetic test that would prove each. It
EXECUTES only the two documentation corrections Claude's method
already sanctions (F5, F6). No code is changed, no pin is moved,
no prior package is edited; corrections to prior documents are
by reference only. Each finding names its owner and the separate
GO it needs.

## Dependency order (across findings)

0. **F6** (executed here) — the corrected E3 definition unblocks
   correct language in every later document.
1. **F5** (executed here) — the -61 label correction.
2. **S2 DISPOSITION FIRST** (F2's dependency): whether S2's
   exclusion exists at all decides what "excluded sessions" the
   session policy governs. S2 waits on the C5 revision evidence
   (R7 ≥ 2026-10-28T21:33:00Z; R30 ≥ 2026-11-20T21:33:00Z) and
   ChatGPT adjudication (-85 gate 4). No F2 freeze before it.
3. **F1 universe ruling (Mike)** — independent of S2; may land
   in parallel. The capture manifest (DATA_ROUTE_DELTA_85.md
   D-85-2) cannot freeze until both S2 and F1 have landed.
4. **F2 freeze package** (R1–R5 + A1–A4) — after S2, post
   adjudication, Mike freezes (GO G2, extended scope).
5. **F4 checker v2 build + adoption** — buildable in parallel;
   adoption (GO G4) gates the -75 snapshot re-analysis and the
   qualification instrument of record.
6. **F3 guard v2 build + adoption** — buildable in parallel;
   adoption (GO G3-v2) + route re-proof is a hard predecessor
   to construction of captured bytes (D-85-3).
7. **F7 parity scope statement** — documented in this plan
   (§F7); takes effect as claim language on adoption of this
   package. No build proposed.

---

## F1 — Universe: crypto membership, hashed pin, the -82 rationale error, hindsight

**Evidence & options:** `UNIVERSE_OPTIONS.md` (this package) —
the four-source membership comparison computed from pinned
bytes; ONE hashed membership pinned (UX51 canonical sha256
`b5d8877e…`); the -82 rationale error stated plainly and
corrected by reference (§2 there); the exact hindsight framing
(§3); options **A** (UX51 intact, dual calendar), **B**
(equity-only 44, new family), **C** (canonical PIT 131, new
family), each with C1-comparability / calendar / -85-math /
family-ledger consequences (§4). **Nothing is designated.**

**Remediation design.** On Mike's ruling, a designation-
amendment package pins: the ruled membership (hash per
UNIVERSE_OPTIONS §1 serialization), its calendar binding(s)
(per-symbol, exactly one calendar per symbol), the family-ledger
entry (existing family for A; new family + preregistration path
for B/C), and the reporting disambiguation rules (mandatory
under B, per §4B).

**Smallest synthetic tests (specifications).**
- **F1-T1 — membership-pin regression.** Re-extract `UNIVERSE_X`
  from the three pinned sources (pine_backtest 447a9a13…,
  hybrid_exit_test 9140504f…, C1 script 4568823c… by its import)
  and assert list equality + canonical hash = the pinned hash.
  Expected: PASS on today's bytes; any silent list edit in any
  source fails the suite before any run can cite the membership.
- **F1-T2 — calendar-binding completeness.** Input: the ruled
  membership table. Assert every symbol binds to exactly one
  named calendar and every calendar named has a pinned spec.
  Expected: 51/51 bound under A (44 XNYS + 7 crypto-spec);
  44/44 under B; 131/131 under C. An unbound symbol fails.

**Files/commits.** This package: `UNIVERSE_OPTIONS.md`. Future:
a designation-amendment package (new research_notes package,
successor to -82 item 1 by reference). -82 item 1 is NOT edited;
its rationale error is corrected by UNIVERSE_OPTIONS §2.
**Owner:** Muse (evidence/options) → **Mike (ruling)**.
**GO: G6 — universe ruling (NEW).** R1–R5/E3 freezes do not
substitute for it (F6).

## F2 — Missing-session policy: the four clarifications (S2 decides first)

The -82 draft R1–R5 stands as drafted (untouched). Claude's
HOLD requires four clarifications the draft does not contain.
They are designed here as draft amendments **A1–A4** to the same
freeze package — [DRAFT] language for adjudication, binding
nothing until frozen under G2.

- **A1 — Engine-semantics declaration (C1 no-max-hold vs V5.4
  30-bar).** The record holds two different hold semantics: the
  C1/pine path has **no maximum hold** (no max-hold exists in
  `c1_corrected_baseline_20261003.py` 4568823c… or
  `pine_backtest.py` 447a9a13…; trades record `hold_bars`, exits
  are signal-driven), while the forward stack's ModeBTracker
  enforces **MAX_HOLD_BARS = 30** (`v54_exit_tracker.py` line
  29, "research MAX_HOLD = 30", 30-bar time exit). A1 declares,
  for the corrected-baseline family, WHICH engine semantics the
  baseline inherits, in one pinned paragraph, before any frame
  exists. R2's "hold counting" is meaningless until A1 says
  what is being counted toward what. The V5.4 30-bar rule may
  NOT be silently imported into the baseline family, nor the
  C1 no-cap rule into any forward claim.
- **A2 — Row-based indicator windows across gaps.** The frozen
  indicators (EMA/ATR/ADX/breakout/volume windows) are
  **row-based**: a window of N means the N preceding constructed
  bars, however much calendar time they span. Across an absent
  session the lookback therefore covers more calendar time at
  the same row count. A2 declares row-based semantics as the
  frozen semantics (the alternative — calendar-aware padding or
  window invalidation — changes indicator VALUES and is a
  strategy change = new family, not a clarification), and
  requires GAP_CROSSED positions (R3) to also disclose when any
  indicator window feeding their entry signal spanned an absent
  session.
- **A3 — Gap-crossed R contribution, tails, tripwires.** R3
  already requires the subset count disclosed. A3 adds the
  accounting: every readout reports (i) pooled R, (ii)
  GAP_CROSSED subset count AND its R sum, (iii) the subset's
  share of trades and of |R|. **Tripwire [PROPOSED values, set
  at freeze, not here]:** if the gap-crossed subset exceeds 20%
  of trades or 25% of |R|, the readout is labeled
  GAP_DOMINATED and the pooled headline is suspended pending
  adjudication. Tail rule: the worst trade in the subset is
  always individually reported, so a single gap-crossed tail
  cannot hide inside a pooled mean.
- **A4 — Re-derivation of invalidated readouts.** When a missing
  session is discovered inside a window already used (R5 labels
  the readout), A4 makes the consequence mechanical: the readout
  is entered in an **invalidation registry** (readout id, frame
  pin, discovery record) and marked INVALIDATED; the only cure
  is re-materialization from corrected qualified bytes and a
  full re-run under the same frozen code, producing a new
  readout that cites the invalidated one as SUPERSEDED. No
  readout is ever patched in place, and no downstream claim may
  cite an INVALIDATED readout except as invalidated.

**Smallest synthetic tests (specifications)** — all extend the
-82 item-3 draft's fixture style; none runs a strategy:
- **F2-T1 — dual-engine divergence.** One synthetic 35-bar
  position, no exit signal: under C1 semantics it remains open
  at bar 35; under ModeB semantics it time-exits at bar 30
  close. Expected: the divergence is exhibited and A1's declared
  choice is the one the baseline harness implements.
- **F2-T2 — window-across-gap enumeration.** A 20-row EMA input
  window spanning one absent session: assert the window contains
  exactly the 20 surrounding constructed bars (timestamps
  enumerated) and the A2 disclosure flag is set for a signal on
  the first post-gap bar.
- **F2-T3 — readout disclosure + tripwire.** A synthetic ledger
  with a known gap-crossed subset (e.g. 3 of 10 trades, known R)
  fed to the readout generator: expected output carries (i)–(iii)
  of A3 exactly, the worst-subset-trade line, and the tripwire
  state flips at the frozen thresholds (test both sides).
- **F2-T4 — invalidation chain.** Frame v1 with an undetected
  missing session → readout R_a. Discovery record → registry
  marks R_a INVALIDATED. Corrected frame v2 → re-derived R_b
  citing R_a as SUPERSEDED. Expected: the registry chain is
  complete and R_a cannot be cited as current by the readout
  tooling.

**Files/commits.** Future: a session-policy amendment package
(R1–R5 + A1–A4 as one freeze candidate, pinned as a -25
preregistration amendment by reference — the preregistration is
never edited). This plan touches no -82 file.
**Owner:** Muse (draft) → ChatGPT + Claude (adjudication) →
**Mike (freeze)**. **GO: G2 (extended scope), AFTER the S2
disposition.**

## F3 — Constructor: extend the -84 guard design to a fail-closed v2

Claude's HOLD: duplicates alone are not enough. The -84 H3b
candidate (wrapper between validator ca3bafd8… and constructor
d47e8df1…; 12/12 fixture-proven; refusal
`CONSTRUCTOR_GUARD_DUPLICATE_TIMESTAMP`; clean input
byte-identical) is the base. Guard v2 adds, by design:

- **Monotonic refusal.** Non-monotonic or descending input
  index → `CONSTRUCTOR_GUARD_NON_MONOTONIC`, constructor never
  invoked. (Today monotonicity is a materializer-layer raise;
  the constructor itself sorts — the same silent-repair class
  as the duplicate merge.)
- **Timezone refusal.** Input index must be tz-aware
  America/New_York (the chain's declared input basis). Naive
  index, fixed-offset index (e.g. UTC−05:00 year-round), or any
  other zone → `CONSTRUCTOR_GUARD_TIMEZONE`. A fixed offset
  cannot represent EST/EDT transitions; accepting one re-opens
  the 2026-10-03 candle-failure class at the input boundary.
- **Fixed-offset warning regression.** A DST-spanning fixture
  carrying fixed-offset stamps is run (a) through the guard —
  must refuse per the timezone class — and (b) recorded through
  the unguarded path under warnings-as-errors (extending -82
  T2): whatever pandas 2.2.3 does with that input (warning or
  silent misalignment) is pinned as the regression expectation,
  so an environment change that alters it fails loudly.
- **Volume conservation.** Post-construction assertion:
  per-bin output volume == sum of constituent input volumes
  (the -82 T1 identity, promoted to a whole-frame law) and
  Σ output volume == Σ input volume over the constructed span.
  Violation → `CONSTRUCTOR_GUARD_VOLUME_CONSERVATION`.
- **Refusal fixtures for every class**, each with the -84 spy
  property (constructor never invoked on refused input).

**Smallest synthetic tests (specifications)** — suite
`test_constructor_guard_v2.py`, an EXTENSION of -84's
`guard/test_constructor_guard.py` (its 12 cases carry over
unchanged as the regression floor):
- **V2-1** two swapped 1h bars → NON_MONOTONIC refusal, spy
  silent. **V2-2** naive index → TIMEZONE refusal. **V2-3**
  fixed-offset (−05:00) index spanning 2024-03-10 (DST) →
  TIMEZONE refusal; unguarded warnings-as-errors behavior
  recorded as the pinned expectation. **V2-4** wrong-zone
  (UTC) index → TIMEZONE refusal. **V2-5** the -82 T1 sessions:
  conservation identities hold per bin and in total through
  the guard; output byte-identical to the -84 clean case.
  **V2-6** sabotage control (a constituent bar dropped inside
  a test harness between validation and construction) →
  VOLUME_CONSERVATION refusal.

**Files/commits.** Future: guard v2 module + suite in a
successor safeguards package (successor to -84's
`guard/constructor_guard.py`). On adoption: successor
constructor pin; route manifest superseding 9573118c…; the
re-proof sequence is -84's REPROOF_PLAN (cited, unchanged —
its step 3 parity gate gains the V2-3 DST case and a
guard-active duplicate-injection case). No pinned file is
edited in place, ever.
**Owner:** Muse (build) → Claude + ChatGPT (review) →
**Mike (adoption)**. **GO: G3, scope extended to v2 (G3-v2).**
Per D-85-3 this adoption is a hard predecessor to construction
of captured bytes.

## F4 — Completeness checker v2: the five missing flag classes + the false-flag guard

The -82 checker (COUNT / ANOMALY / STEP lanes; 14/14) passed
as an instrument design but Claude holds it incomplete. V2
extends the SAME checker (no second instrument), by design:

- **ANOMALY extensions** (completeness lane): **NaN** volume or
  NaN OHLC → COMPLETENESS_FAIL; **negative** volume →
  COMPLETENESS_FAIL; **1-share price-moving** bars (0 < v ≤ 1
  with high > low or close ≠ open) → COMPLETENESS_FAIL (a
  declared checker constant, `MIN_PLAUSIBLE_VOLUME = 2`,
  amendable only by governed amendment, never silently).
- **VBASIS lane (new):** a persistent step in volume scale
  (rolling median ratio outside [1/1.5, 1.5] sustained ≥ 5
  sessions) at a NON-declared boundary → CONVENTION_BREAK_
  SUSPECT (volume-basis step — the signature of an unadjusted
  basis change inside one series).
- **STEP-ALL:** the existing STEP lane checks only DECLARED
  boundaries. V2 scans ALL boundaries for factor-shaped price
  steps: step ≈ a plausible split factor or its reciprocal
  (tolerance as the -82 STEP lane's log-tolerance) at an
  undeclared boundary → CONVENTION_BREAK_SUSPECT (undeclared
  split signature).
- **Declared-boundary classification (the false-flag guard).**
  At a DECLARED boundary the step is classified, not merely
  tolerated: ≈1 → continuous (adjusted); ≈factor or
  ≈1/factor → mixed-basis suspect (existing STEP behavior);
  **anything else — including a genuine +60% gap — is price
  action and raises NO flag.** A declared split followed by a
  momentum gap is a market fact, not a basis break; the -82
  lane's tolerance (abs(log step) ≤ log 1.5 passes) already
  implies this, and v2 makes the classification explicit with
  a fixture so it cannot regress.
- **Scale-step-by-split-factor check.** At a declared boundary,
  v2 also measures the VOLUME scale step and compares it to
  the declared factor: step ≈ factor → records the
  SCALED_BY_FACTOR convention note (the behavior -75 proved
  for NVDA/TSLA on Twelve Data); step ≈ 1 → records an
  UNSCALED convention note. Either note is information for the
  S2 disposition; neither is a failure — a *mismatch between
  the price-basis classification and the volume note* is what
  feeds CONVENTION_BREAK_SUSPECT.

**Smallest synthetic tests (specifications)** — extension of
-82's `fixtures/test_tsla_completeness_check.py` (14 cases
carry over as the floor):
- **C15** one NaN-volume price-moving bar → COMPLETENESS_FAIL.
  **C16** one negative-volume bar → COMPLETENESS_FAIL. **C17**
  one 1-share price-moving bar → COMPLETENESS_FAIL; and a
  1-share FLAT bar stays NO_TRADE_FLAT (no fail). **C18**
  volume scale ×3 step mid-series, prices continuous, no
  declared split → CONVENTION_BREAK_SUSPECT via VBASIS, price
  lanes clean. **C19** undeclared 3:1-shaped overnight price
  step → CONVENTION_BREAK_SUSPECT via STEP-ALL. **C20**
  declared 3:1 boundary + genuine +60% overnight gap (step
  ≈ 1.6 post-boundary move, not factor-shaped) →
  QUALIFIED_CLEAN, no convention flag (THE false-flag guard).
  **C21** declared boundary, volume step = declared factor →
  SCALED_BY_FACTOR note, no fail. **C22** declared boundary,
  volume step ≈ 1 with adjusted prices → UNSCALED note, no
  fail; completeness lane clean throughout C18–C22 except
  where designed.

**Files/commits.** Future: checker v2 module + extended suite
in a successor repair package (successor to -82
`fixtures/tsla_completeness_check.py`, which is NOT edited).
Adoption makes v2 the qualification instrument of record
(D-85-6) and unlocks the -75 snapshot re-analysis.
**Owner:** Muse (build) → adjudication. **GO: G4**
(re-analysis of the -75 snapshots under v2 + adoption of v2
as the instrument; the TSLA corrected label itself already
PASSED Claude's review and its adoption travels with G4).

## F5 — The -61 July-3 label — EXECUTED in this package

`F5_CORRECTION_NOTE_61.md` (this package): the -61 passage is
quoted exactly and corrected BY REFERENCE to CLOSED /
non-session, on the -62 §3 authorities, by the -82 item-6
method; the -61 memo's bytes (sha ac4c9ecc…) are untouched and
its REFUSED outcome stands. **Owner:** Muse (executed).
**GO: none** beyond this package's adoption by adjudication.

## F6 — E3 definition — EXECUTED in this package

`F6_ERRATUM_E3_DEFINITION.md` (this package): E3 =
split-event TIMING (`announced_at` ≤ decision instant; modes
A/B) — the GATE-E3 of the -60 contract. E3 does NOT denote
PIT universe selection; that axis is named UPIT for future
documents and is decided under F1/G6. Errata E-1…E-4 list
every conflated usage (-82 item 1, -83 Q1, -85 gate 2) and
the one verified-correct usage (-84), each corrected by
reference; no prior package is edited. **Owner:** Muse
(executed). **GO: none** beyond adoption by adjudication.

## F7 — Parity scope: what the corrected baseline may and may not claim

**The finding.** The forward harness
(`v54_forward_harness.py`, ce7c902c…) contains NO C1 ranking /
caps / risk-gate layer: its imports are the universe modules,
`v54_engine`, `scanner_rules`, and the ModeB exit tracker — it
does NOT import `pine_ranking` (compute_features), the
`pine_exposure` SECTOR caps, or `pine_signal_quality` — the
portfolio-decision layer the C1 script (4568823c…) runs on.
This is the Oct-3 forensic conclusion restated at the current
pins: the live pipeline tested a different system.

**The parity scope statement (remediation = this statement,
pinned here, governing all future claim language):**
- **CAN be claimed:** membership-byte parity (the same
  UNIVERSE_X list, hash b5d8877e…, feeds the C1 script and
  the forward UX51 cohort); signal-component parity (same
  pine signal family); exit-component parity (ModeBTracker
  semantics in the forward stack; the baseline's exit stack as
  declared under A1).
- **CANNOT be claimed:** OOS C1 parity; portfolio-decision
  parity (ranking, sector caps, risk gate absent forward);
  forward results as confirmation of C1 (or of any corrected
  baseline); pooled statistics across the two families.
- The corrected baseline's walk-forward OOS (-25 folds) is
  internal to the baseline family. The forward cohort is
  evidence about the forward system only.
- Any future C1-parity claim requires building the missing
  decision layer into a harness — a new component under its
  own adjudicated task. It is NOT proposed here.

**Smallest synthetic test (specification).**
- **F7-T1 — import-surface tripwire.** Statically parse the
  pinned harness's import set and assert the decision-layer
  modules (`pine_ranking`, `pine_exposure`,
  `pine_signal_quality`) are absent. Expected on today's pin:
  assertion holds (documenting the finding); if a future
  harness gains the layer, the tripwire fails and this
  statement must be revisited before any parity claim is
  repeated.

**Files/commits.** This plan only. A future decision-layer
harness would be a new package/component. **Owner:** Muse
(statement) → adjudication (adoption as claim language).
**GO: G7 — decision-layer harness (NEW, not requested, not
recommended at this time); the statement itself needs no GO
beyond package adoption.**

---

## Consolidated GO table

| GO | Decision | Owner of the decision | Gates |
|---|---|---|---|
| G6 (NEW) | Universe ruling — Option A / B / C | Mike | capture manifest freeze; family identity |
| S2 | Disposition on C1–C6 incl. C5 (KEEP / REPLACE / HOLD) | ChatGPT adjudication on R7/R30 evidence; legs need Mike's GO each | F2 freeze; producer predecessor (-85 gate 4) |
| G2 (extended) | Freeze R1–R5 + A1–A4 as a -25 amendment | Mike, after S2 + adjudication | any baseline run |
| G4 | Adopt checker v2 + re-analyze -75 snapshots under it; adopt the corrected TSLA label into reporting | adjudication (ChatGPT/Claude) | qualification instrument of record |
| G3-v2 | Adopt guard v2 (successor constructor pin + route re-proof) | Mike, after review | construction of captured bytes (D-85-3) |
| G1 | Split-event producer creation (unchanged from -82; needed only on a KEEP branch) | Mike + adjudicated task | S2 integration |
| G7 (NEW) | Decision-layer harness for any C1-parity claim | Mike (not requested) | any parity claim beyond §F7 |
| — | Calendar adoption; capture authorization (ceiling per D-85-2); Phase-1; baseline-run GO | Mike (per -85, as amended by the delta) | the -85 chain |

**What stands unchanged:** Claude's HOLDs stand until the
re-reviews of the built remediations land; -82's PASSED items
need no further work; the forward test remains paused with its
frozen classification; the shadow design remains inactive;
no performance number in this package exists or is implied.

**Status: PLAN DOCUMENTED; F5 + F6 EXECUTED (documentation).**
Owner: Muse. Next step: ChatGPT adjudication of this plan,
then the builds it sequences — each under its own task, none
bundled into this one.
