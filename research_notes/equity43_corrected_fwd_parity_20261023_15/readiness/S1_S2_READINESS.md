# EQUITY43-CORRECTED-FWD-v1 — two-stage readiness (S1 / S2)

**Task:** QF-EQUITY43-CORRECTED-FORWARD-PARITY-BUILD-20261023-15 r1.
**State: BOTH STAGES UNACTIVATED.** This document specifies the stages and
their gates; it launches nothing. Production V5.4 remains PAUSED
(harness `ce7c902c…`, PAUSE_NEW_ENTRIES present) and untouched by design.

The stages are strictly separated: **S1 can never produce positions,
orders, cash or P&L**, and S1 observations alone never validate an edge.
S2 is a different, separately gated authorization.

---

## Stage S1 — corrected signal-only observation (NOT launched)

**Purpose.** Prove, prospectively and at decision time, that the
corrected 43-equity observer reproduces the -13 research engine's
decisions on live-shaped inputs — the forward analogue of this build's
offline parity — with zero trading semantics.

**Form.**
* Membership: exactly the 43 contract names (CONTRACT.md §1). No other
  symbol is scanned; there is **no 250-symbol Yahoo sweep** and no
  duplicate scan of any kind.
* Inputs: prospective 1h bars meeting the contract's input policy
  (§4), admitted against the pinned session table; corrected 4H bins;
  decisions journaled at bin close only.
* Journal: a NEW append-only hash-chained journal (contract §5),
  anchored outside the writer's store after every session seal.
* Records per session: per-symbol session outcome (complete / gap /
  poisoned), each emitted 4H bar's identity, every candidate event with
  its signal-event key, its decision instant, and its portfolio-gate
  disposition **as an observation** (taken-would-be / skipped with
  reason), plus explicit no-signal sessions. Zero positions, zero
  orders, zero cash, zero P&L fields anywhere in the journal schema.
* No retroactive signals: a session finalized incomplete is a permanent
  gap; late bars are refused (no backfill), exactly as in this build's
  T09/T10 fixtures.

**Gate evidence required BEFORE an S1 activation decision may be taken**
(all must be named in the activation record):
1. This build's verdict: offline parity READY (synthetic suite +
   actual-byte decision parity vs -13) — see RESULT.md.
2. A prospective 1h data route that demonstrably meets the contract's
   bar/basis/input policy for the 43 names, evidenced on actual bytes
   (not documentation alone), INCLUDING an adopted disposition of
   G4/VBASIS. **Current state: FEED_NOT_READY** — no route is qualified
   today: the Twelve Data captures are historical receipts for the DEV
   window, not a qualified prospective feed under an adopted basis
   convention, and the legacy Yahoo route is the off-grid/defective-
   basis route this cohort exists to replace.
3. A predeclared future T0 (below).
4. The sentinel discipline: S1 runs only while its own activation
   record stands; the production PAUSE sentinel continues to govern the
   legacy stack independently (the observer's armed-mode gate withholds
   decision events while a PAUSE sentinel is present — fixture T17).

**T0: UNSET.** No earliest deterministic future T0 is named in this
build, because a T0 must be grounded jointly by the exchange calendar
AND a qualified feed's first fully-observable session; with the feed
unqualified (gate 2), any date would be invented. The activation
decision must name: the first XNYS session such that the qualified feed
can deliver every 1h bar for all 43 names from 09:30 ET of that session,
with the journal genesis anchored before that session's first bin close
(13:30 ET).

**Owners.** Build/operate: Muse. Adjudication of gate evidence and of
any parity exception: ChatGPT (independent validation). Activation
decision: Mike only.

**STOP conditions (S1 halts and reports; it never self-repairs):**
any session where the observer's decisions cannot be reproduced from
its journal inputs; any poisoned leg (whole-symbol quarantine, others
continue); any chain/anchor verification failure; any feed session that
cannot be classified complete/gap within its finalization window; any
pressure to admit off-grid, backfilled, or basis-unadopted data.

---

## Stage S2 — prospective paper validation cohort (NOT launched,
## separately gated)

**Purpose.** A genuine forward edge test of the corrected strategy —
the first prospective performance evidence, preregistered before T0.

**Additional gates beyond S1's** (each named in a SEPARATE S2
authorization; S1 completion does not imply S2 approval):
1. S1 completed with actual-byte parity demonstrated prospectively
   (observer decisions == research-engine decisions on the same
   journaled inputs, independently rechecked).
2. Data qualifications closed, including the **G4/VBASIS adoption** —
   no candidate-grade inputs in a performance cohort.
3. Independent event/portfolio parity to -13 re-run on the S2 engine
   build (the build that will run S2, not a predecessor).
4. **Costs predeclared at 25bps** (the frozen conservative view);
   cost/position-sizing audit of the paper executor before T0.
5. Paper-only fills at the next eligible bar after each decision
   instant, under the frozen conventions; stop / TP1 / EMA55 exit
   states and the Ruling-B terminal-censoring treatment for positions
   open at the cohort end.
6. **Observation targets frozen:** 50 closed paper trades = interim
   checkpoint (report only, no verdict), 100 closed paper trades =
   full evaluation. No early stopping for performance, no extension
   past 100 without a new preregistration.
7. **Predeclared failure criteria:** the cohort FAILS (and the strategy
   returns to research) if 25bps closed-trade expectancy ≤ 0 at the
   100-trade evaluation, or if any parity/integrity STOP fires and
   cannot be dispositioned without touching recorded observations.
   Regime stratification (market-gate state at entry, per the frozen
   gate taxonomy) is recorded for every trade so the verdict can be
   read by regime, never re-sliced after the fact.
8. No live execution at any point under S2; promotion beyond S2 is a
   separate Mike decision on S2's completed record.

**Owners.** Executor build/operate: Muse. Preregistration review and
verdict adjudication: ChatGPT. Authorization and any promotion
decision: Mike only.

---

## The narrow next-launch gate (what a future activation decision
## must name — nothing else is required, nothing less suffices)

A single activation record, signed by Mike after ChatGPT's adjudication
of the evidence, naming:
**(a)** the qualified prospective 1h feed route + its actual-byte
evidence and the adopted G4/VBASIS disposition;
**(b)** the deterministic future T0 session per the S1 rule above;
**(c)** the journal genesis anchor location (outside the writer's
store);
**(d)** the S1 STOP conditions verbatim;
**(e)** explicit scope: S1 only (signal-only, zero positions/orders/
P&L), 43 names only.
S2 requires its own later record naming its §-gates 1–8.
