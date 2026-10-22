# GATE 3 — S2 DISPOSITION (task -87)

**Status: PROPOSED — not disposed.** Disposition requires Mike's GO
in one of the forms at §6. Dependency position: third gate; the
branch analysis assumes Gate 1 adopted (adjacency is computed over
the combined 751-session calendar).

**What S2 is.** REQ-S2: for each split event with effective session
D, exclude sessions {prev(D), D, next(D)} for that symbol — bars AND
candidate entries removed together (the -59 transform,
`s2_split_exclusion_v1.py` sha `7791ca91…`, 16/16 synthetic, never
integrated). It was inherited as a governance constant from the
Yahoo unadjusted preregistration.

**Governing test (Mike, 2026-10-20, standing).** The only question
is whether S2 has a DEMONSTRATED data-quality purpose in Twelve
Data's feed. Returns, expectancy, and backtest outcomes are
inadmissible in this gate, in either direction. Two verification
corrections bind the evidence: a normal-looking price gap or volume
pattern proves nothing about adjustment correctness (anomaly screens
only), and a later `/last_change` timestamp does not prove earlier
bars invalid — version/consistency evidence is required.

## 1. RECOMMENDATION: REJECT (labeled Muse recommendation)

Retire REQ-S2 as a requirement for the corrected baseline, recorded
as a **documented non-requirement with automatic reopen triggers**
(§5). The reasoning, on the purpose test only:

1. **No demonstrated purpose exists on the record.** The -62
   necessity audit (HOLD) found S2 inherited PROSE_ONLY from the
   Yahoo preregistration, never derived from Twelve Data evidence,
   with **zero contamination instances in either direction** — no
   mixed-basis series has ever been observed in this program, in
   any feed.
2. **The direct vendor evidence now points the other way.** -62's
   HOLD was issued before any split probe had run. The -75 Day-1
   probe is the first instrument capable of seeing the corruption
   S2 guards against, applied to a real 10:1 split (NVDA,
   2024-06-10): Twelve Data's `adjust=splits` back-adjusts prices
   AND scales volume **uniformly by the exact factor, flipping on
   the effective date** (C1/C3/C4/C6 PASS; C2 convention
   SCALED_BY_FACTOR, uniform). The strategy's inputs are provably
   invariant under exactly this representation (fixture S2-1:
   non-seam returns untouched, the flat seam reads 0.0000 instead
   of a manufactured −0.9000, seam TR/close 0.0 instead of 9.0,
   seam relative volume 1.0× instead of a 10× false spike). Where
   the corruption was looked for with a proper instrument, it was
   not there.
3. **The one defect actually observed is not S2's defect.** TSLA's
   -75 failure was a **completeness** failure (166 zero-volume
   pre-split bars in BOTH bases; -76: nonzero OHLC range — missing
   volume, not a basis break). S2 excludes sessions around splits;
   it does nothing for missing volume, and the completeness checker
   (-82, 14/14; v2 designed in -86 F4) is the instrument aimed at
   the observed class.
4. **The residual risk is detectable without exclusion.** A
   mixed-basis seam is a factor-shaped step in the bars themselves
   (fixture S2-2: the seam step ratio recovers the factor exactly),
   and checker v2's design lanes (STEP-ALL for undeclared
   factor-shaped splits, VBASIS for volume-basis steps — -86 F4)
   detect it from captured bytes, per symbol-window, failing that
   window closed. Detection removes the DEFECT; S2 removes three
   valid sessions per split whether or not any defect exists.
5. **ADOPT is not currently executable at any price the record
   supports.** S2 consumes an event list. No producer exists and
   GATE-E1 is unmet: the vendor's `/splits` is Grow+ paid-tier and
   excluded; a filing-derived enumeration has no design and an
   unsolved completeness proof (GATE-E2). Adopting S2 therefore
   does not buy protection — it buys a hard predecessor program of
   unknown duration standing in front of the baseline, guarding
   against a corruption with zero observed instances. The -85
   earliest-qualified estimate (Nov 27 – Dec 1, 2026) does not
   survive an ADOPT branch.
6. **REJECT is reversible on evidence, by construction.** The R7/R30
   legs — the program's own version/consistency instrument — are
   already scheduled, and §5 wires them (plus the checker's lanes)
   as automatic reopen triggers. Rejecting on today's record while
   pre-committing to reopen on tomorrow's is the disposition the
   evidence supports; an unconditional HOLD merely defers the same
   decision to a date when the only new evidence will be exactly
   those legs.

**What REJECT does not claim.** It does not claim Twelve Data never
revises bases, never mixes bases on other symbols/windows, or that
splits are harmless in general. It claims: on the demonstrated
record, the exclusion has no demonstrated purpose, its function is
covered by detection, and its cost (an unbuildable predecessor +
deleted valid sessions) is certain while its benefit is
hypothetical.

## 2. Branch analysis — ADOPT vs REJECT (required mechanics)

Written against the -86 F2 draft amendments A1–A4 (unfrozen; the G2
freeze sets final values). "Excluded session" = one element of a
{prev(D), D, next(D)} triple (fixture S2-3: triples follow SESSION
adjacency over the combined calendar — across closures and across
the extension/-35 boundary, e.g. D = 2024-07-03 ⇒ {07-02, 07-03,
07-05}; D = 2024-09-16 ⇒ {09-13, 09-16, 09-17}).

**Positions spanning excluded sessions.**
- ADOPT: the -59 transform removes bars and candidate entries
  together, so a position cannot span a triple: an entry signaled
  before D whose hold would cross the triple is truncated from the
  frame, and its R never enters any readout. This is a silent
  selection effect concentrated in exactly the highest-volatility
  windows (split neighborhoods), and it compounds A1: under C1
  no-max-hold semantics a spanning position's lifetime is unbounded,
  so the set of truncated positions is not knowable from the event
  list alone — it depends on signal timing. Every readout under
  ADOPT must therefore disclose the truncated-position count per
  A3-style accounting, a disclosure the current A-drafts do not
  yet contain (a gap an ADOPT branch must close at the G2 freeze).
- REJECT: positions span split sessions normally. On a uniformly
  adjusted series the split is invisible to entry/stop/TP/R math
  (basis-consistent on both sides — fixture S2-1), so a spanning
  position's R is well-defined. Reporting carries a named
  **SPLIT_SPANNING subset** (count + R sum), the honest analog of
  A3's gap accounting, so any split-window anomaly is visible
  rather than deleted.

**Indicator computation across exclusions.**
- ADOPT: indicators are row-based (A2) — a window of N means the N
  preceding CONSTRUCTED bars. Removing a triple makes the same
  nominal window span more calendar time for split-adjacent symbols
  than for others, so identical indicator values are computed over
  non-identical information sets across the cross-section; ranking
  (rs_top2) then compares unlike quantities. A2's disclosure flag
  (window spanned an absent session) would fire on rule-removed
  sessions exactly as on data-missing ones unless the two are
  distinguished.
- REJECT: windows are uniform row counts over complete series for
  every symbol; A2's flag fires only on genuine data gaps.

**Next-bar fills.**
- ADOPT: under the R1 fill rule (fills only at present-bar opens), a
  signal printed on the last bar before a triple fills at the next
  PRESENT bar's open — up to three sessions later, at a price no
  decision ever saw, across a corporate action. The fill is
  mechanically definable but economically fictitious.
- REJECT: fills at the next bar's open, uniformly, on a
  basis-consistent series.

**Gap-crossed R reporting.**
- ADOPT: rule-removed sessions manufacture artificial gaps. A3's
  GAP_CROSSED subset (with its PROPOSED tripwires: >20% of trades
  or >25% of |R| ⇒ GAP_DOMINATED) would conflate data gaps with
  exclusion gaps — every split-adjacent position becomes
  "gap-crossed," inflating the subset and potentially tripping the
  wire for reasons unrelated to data quality. An ADOPT branch must
  split the subset into GAP_DATA vs GAP_RULE at the G2 freeze, or
  A3's tripwire loses its meaning.
- REJECT: GAP_CROSSED remains a pure data-quality subset (missing
  sessions only), A3 works as drafted, and split exposure is
  reported through SPLIT_SPANNING instead — two clean subsets
  instead of one polluted one.

**Producer dependency (stated per branch, honestly).**
- ADOPT ⇒ the GATE-E1…E5 producer + a qualified event SOURCE are
  HARD PREDECESSORS to capture qualification: no event list, no
  baseline. Source status: none exists (paid route excluded,
  filing route undesigned); E3 freeze (Gate 2) is necessary but
  nowhere near sufficient. The -84 core is ready to be fed; nothing
  exists to feed it.
- REJECT ⇒ the producer is NOT required for the baseline and leaves
  the critical path. The -84 spec + core remain as candidates,
  reactivated automatically if a §5 trigger fires. Checker v2's
  declared-boundary table still wants event dates/factors, but at
  data-quality grade (its STEP-ALL lane can also derive boundaries
  from the bars themselves), a far weaker need than S2's
  decision-grade, coverage-attested list — it does not resurrect
  the predecessor.

## 3. Evidence

| Claim | Evidence |
|---|---|
| S2 origin + zero contamination | -62 AUDIT_MEMO (`research_notes/td_s2_necessity_source_audit_20261020_62/`): PROSE_ONLY inheritance; §2 invariance analysis; §4 zero instances; verdict HOLD on the pre-probe record |
| Uniform vendor adjustment | -75 EXECUTION_RESULT (package `td_probe_day1_rerun_20261021_75/`): NVDA C1/C3/C4/C6 PASS, C2 SCALED_BY_FACTOR uniform ×10 incl. volume, flip 2024-06-10; program spend 6 credits, receipts pinned |
| TSLA defect class | -75 (C2 FAIL, 166 zero-volume bars both bases) + -76 adjudication (missing/zeroed volume, nonzero range) + -82 label "C2 NOT_EVALUABLE — VOLUME COMPLETENESS FAILURE" |
| Docs silence (residual uncertainty) | -63 DESK_PACKET_MEMO §4: volume adjustment N1, intraday/daily consistency N2, boundary-bar basis N3, back-adjustment N4, revisions N5 — all NOT DOCUMENTED |
| Invariance + detectability | `fixtures/test_s2_invariance_and_seam.py`: **10/10 PASS** (S2-1 invariance family, S2-2 seam + factor recovery, S2-3 triple shapes over the pinned calendar bytes) |
| Transform exists, unintegrated | -59 CLOSURE_MEMO (16/16 synthetic; separately versioned candidate, no assembly point — -62 concurrence) |
| Checker as the detection instrument | -82 item 4 (independent completeness check 14/14); -86 F4 (v2 design: VBASIS, STEP-ALL, declared-boundary table) |
| R7/R30 as revision instrument | -62 §1 (REV7/REV30 designed, never run); -75 receipt instant 2026-10-21T21:33:00Z ⇒ R7 eligible ≥ 2026-10-28T21:33:00Z, R30 ≥ 2026-11-20T21:33:00Z; each leg needs Mike's own GO |

## 4. Unresolved risks of the REJECT branch (stated plainly)

- **Sampled-window limit.** Uniformity is demonstrated on ONE split
  window (NVDA) plus a dividend control; TSLA's window was
  uninformative on convention for its defect segment. Other symbols,
  other splits, and paginated multi-request assembly (the -62 §1
  seam mechanism — pages fetched at different times could in
  principle carry different bases) are NOT covered by -75. The
  mitigations are structural, not rhetorical: the capture assembles
  each symbol-window in single requests where the record allows
  (-85 chunking), checker v2 runs on every captured window before
  construction, and §5's triggers watch the rest.
- **Vendor revisions are unmeasured until R7/R30.** If Twelve Data
  rewrites a window's basis after the fact, only the re-pull legs
  see it. Until R30 (2026-11-20), REJECT rests on Day-1 evidence —
  which is why the triggers are written into the disposition
  itself, and why no baseline RUN is authorized by this gate in
  any case (the run GO remains last in the -85 chain, after R30).
- **Checker v2 is designed, not adopted.** F4's lanes (STEP-ALL,
  VBASIS) are fixture-specified in -86, not yet built/adopted;
  REJECT's detection leg depends on the G4 adoption landing before
  capture qualification. If G4 slips, REJECT's coverage slips with
  it — the dependency is named here so it cannot be forgotten.

## 5. Reopen triggers (part of the REJECT freeze text)

> S2 returns to adjudication automatically, before any baseline run
> on affected data, if ANY of: **T1** — an R7 or R30 re-pull shows
> any bar whose split-adjustment basis differs from its Day-1
> counterpart (version/consistency evidence, per the standing
> verification corrections — never price-pattern inference);
> **T2** — checker STEP-ALL or VBASIS fires on any symbol-window in
> the baseline capture; **T3** — vendor documentation or receipt
> evidence emerges that `adjust=splits` is applied non-uniformly
> (including per-page basis differences in paginated assembly).
> A trigger reopens the QUESTION; it does not pre-decide it — the
> disposition is re-argued on the new evidence under the same
> purpose test.

## 6. Minimal tests + the GOs

Executed: **10/10** (above). Cited, not rerun: the -59 transform
suite (16/16) and -61 shim — their pinned venv no longer exists;
under an ADOPT branch their re-proof is part of the adoption work,
under REJECT they are moot. SPECIFIED_NOT_RUN: checker v2 fixtures
C15–C22 (-86 F4 specifications; execution belongs to the G4 task).

> **GO — Gate 3 (recommended form):** "REJECT REQ-S2 for the
> corrected baseline — retire it as a documented non-requirement
> with reopen triggers T1–T3."
> **Alternative forms, with consequences in one line each:**
> "ADOPT REQ-S2" — the GATE-E1…E5 producer + a qualified event
> source become hard predecessors; the -85 timeline slips by that
> program; A3 must be amended (GAP_DATA vs GAP_RULE) at the G2
> freeze. "HOLD S2" — the producer question stays on the critical
> path undecided; the R1–R5 freeze cannot complete (its F2
> dependency is this disposition); nothing else moves.
