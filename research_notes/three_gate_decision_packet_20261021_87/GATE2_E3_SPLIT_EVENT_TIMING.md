# GATE 2 — E3 SPLIT-EVENT TIMING FREEZE (task -87)

**Status: PROPOSED — not frozen.** Freezing requires Mike's GO in
the form at §5, naming the mode. Dependency position: second gate;
operative after Gate 1.

**Scope discipline (-86 F6, executed):** E3 denotes split-event
TIMING only — GATE-E3 of the -60 boundary-coverage contract. It does
NOT denote point-in-time universe selection; that axis is **UPIT**,
is governed by the Option A freeze + the disclosed survivorship
limitation, and is not touched, reopened, or laundered by anything
in this gate.

## 1. The two freeze texts (either is signable; §2 recommends A)

> **FREEZE TEXT F-A — E3 MODE A (DECISION-TIME).**
> (1) A split event may affect a strategy decision only if
> `announced_at ≤ decision_instant`, where `announced_at` is the
> event's independently sourced announcement timestamp and
> `decision_instant` is the earliest strategy decision the event
> would affect. Equality is INSIDE the rule (≤ semantics).
> (2) An event announced after the decision instant is EXCLUDED
> from that decision's event set and written to the run's excluded
> ledger with reason `PIT_ANNOUNCED_AFTER_DECISION`. Exclusion is
> never silent: the ledger is part of the run receipt.
> (3) PROVENANCE. `announced_at` must come from an independent
> timestamped record — an exchange notice, a filing timestamp, or a
> vendor field with documented announcement semantics. It must never
> be derived from the effective date, never restated from it, and
> never supplied by a vendor default. A record without
> `announced_at` is NOT evaluable under E3 and refuses
> (`MISSING_FIELD`): unknown timing is treated as not-proven-timely,
> never as timely.
> (4) An event whose `announced_at` is after the dataset's `as_of`
> cutoff refuses the entire assembly (`AS_OF_AFTER_DATASET_CUTOFF`)
> in any mode: that is a provenance defect, not a timing choice.
> (5) FAIL-CLOSED SWITCH. The rule has no default. Any component
> consuming split events refuses to run with the mode unset
> (`E3_MODE_UNSET`), exactly as the -84 producer core does.
> (6) BASIS LABEL. A run assembled entirely under this rule carries
> basis `DECISION_TIME`.

> **FREEZE TEXT F-B — E3 MODE B (RETROSPECTIVE).**
> Clauses (3), (4), (5) of F-A apply unchanged. In place of (1),
> (2), (6): (1′) Events are applied retrospectively for data-quality
> purposes regardless of `announced_at` relative to the decision
> instant. (2′) Every event with `announced_at > decision_instant`
> is flagged `ANNOUNCED_AFTER_DECISION` in the event list. (6′) If
> any such event is included, the run's basis is
> `RETROSPECTIVE_NON_TRADABLE`; a basis carrying that label may
> never be presented as, pooled with, or compared against a
> decision-time basis as if tradable, and may never serve as the
> corrected baseline's primary basis.

## 2. Recommendation: MODE A (labeled Muse recommendation)

1. **The baseline's question is tradability.** The corrected
   baseline exists to establish what the frozen strategy would have
   done with the information available at each decision. An event
   set built from announcements that postdate the decisions they
   alter answers a different, retrospective question. Under F-B the
   primary basis would be non-tradable BY CONSTRUCTION — the label
   says so — and the program would have spent its one clean baseline
   on a number it must immediately disclaim.
2. **A is the fail-closed direction.** Under A, every failure of
   knowledge (late announcement, missing timestamp, unknown source)
   resolves toward exclusion or refusal. Under B, the same failures
   resolve toward inclusion with a flag. For a rule whose entire
   purpose is point-in-time discipline, exclusion-on-doubt is the
   only coherent default.
3. **Optionality is asymmetric.** Freezing A does not destroy B:
   a B-labeled diagnostic assembly can still be produced later
   under its own design, clearly fenced. Freezing B as the primary
   rule would contaminate the primary claim in a way no later
   labeling can undo (the run would have to be redone under A to
   recover a tradable basis).
4. **Cost is zero.** The -84 producer core already implements both
   modes behind the switch (23/23 in -84; 11/11 against these freeze
   texts here). A asks nothing of the machinery that B does not.

## 3. Evidence

| Claim | Evidence |
|---|---|
| E3 definition + modes | -86 `F6_ERRATUM_E3_DEFINITION.md` (commit `62aab52`): E3 = GATE-E3 of the -60 contract (`td_req_s2_boundary_coverage_contract_20261020_60/CONTRACT_MEMO.md`, sha `c42a6b16…`); modes A/B as stated there |
| Switch refuses unset | -84 producer core `split_event_producer.py` (sha `ffa14a8d…`, package `f7725bf`): `E3_MODE_UNSET`, no default; mode A ledgering, mode B basis flip implemented |
| Freeze-text semantics executed | `fixtures/test_e3_freeze_modes.py` against a byte copy of the -84 core: **11/11 PASS** — unset/invalid refusal, A include/exclude/equality-boundary, B flag + basis flip, B clean stays DECISION_TIME, missing `announced_at` refuses in both modes, past-cutoff refuses in both modes (`fixtures/output_test_e3_freeze_modes.txt`) |
| Provenance requirements | -84 `SPEC_SPLIT_PRODUCER.md` §3 (qualification requirements 1–5: independent `announced_at`, coverage attestation, revision policy, archivable receipt bytes) and GATE-E3 in §1 |

## 4. Unresolved risks

- **No qualified event source exists.** Neither freeze text creates
  one. GATE-E1 (a pinned acquisition leg) remains unmet; the
  documented vendor route (`/splits`) is Grow+ paid-tier and was
  excluded in the -63 packet; a filing-derived enumeration is
  undesigned. This gate freezes the RULE so a source, when one is
  ever authorized and qualified, has a fixed contract to feed —
  it does not schedule the source.
- **Decision-instant granularity.** For a historical baseline, the
  "decision instant" is the run's earliest affected decision per
  event (the -84 core's `decision_instant` parameter). Freezing A
  fixes the semantics; the per-run decision grid is a run-design
  fact that must be pinned in the run's own preregistration.
- **Interaction with Gate 3.** If Gate 3 REJECTS S2, split events
  lose their baseline consumer — but not their only consumer: the
  -86 F4 checker-v2 design uses a declared-boundary table (event
  dates/factors) to keep genuine split-boundary gaps from
  false-flagging. That table is a data-quality device, and any
  future decision-adjacent use of event data inherits this freeze.
  Freezing E3 now is therefore not wasted under either Gate-3
  branch; under ADOPT it is a hard predecessor to the producer.

## 5. Minimal tests + the GO

Executed: **11/11** (above). SPECIFIED_NOT_RUN: none for the freeze
itself; source-qualification tests belong to a future GATE-E1 design
and do not exist yet because no source exists.

> **GO — Gate 2:** "Freeze E3 as mode A (decision-time) per freeze
> text F-A" — or, by substitution, "mode B per freeze text F-B".
> The GO names the mode; an unqualified "freeze E3" adopts nothing.
