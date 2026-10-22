# SESSION-HANDLING RULES — FREEZE TEXT (G2 EXTENDED)
## Task -88 · PREPARED FOR MIKE'S ONE-GO ADOPTION — NOT ADOPTED

**Provenance of this text.** The -82 preregistration draft R1–R5
(package `d2cca9c`, item 3), as amended by the -86 remediation plan
(amendments A1–A4, commit `62aab52`), restated for the world the
three-gate freeze (commit `a126ce5`) created: **S2 is REJECTED**, so
the rule-exclusion set is empty, and the only absent sessions a
position can ever meet are calendar non-sessions (absent by
construction) and data-absent sessions (missing or unqualified
bytes). Claude's F2 clarifications are incorporated. No entry,
exit, threshold, or sizing parameter appears anywhere in this
text; nothing here tunes a strategy. Adoption path: ChatGPT +
Claude adjudication of this exact text → Mike's GO → pinned as an
amendment to the -25 preregistration **by reference** (the
preregistration itself is never edited).

---

## THE TEXT PROPOSED FOR FREEZE

**§0 — Definitions.**
(a) *Frame:* the qualified constructed 4H frame for one symbol,
built by the pinned constructor from qualified captured bytes
against the adopted calendar (751-session XNYS union for
session-bound names; S-C1…S-C6 for crypto pairs).
(b) *Absent session:* a calendar session for which no qualified
constructed bar exists in the frame, for a data reason (missing,
incomplete, or failed-qualification bytes). Calendar non-sessions
are not absent sessions; they are never in the frame.
(c) *Rule exclusions:* **none.** REQ-S2 is retired (freeze
`a126ce5`); no rule removes sessions from a frame. If S2 ever
reopens under triggers T1–T3 and is re-adopted, this text must be
re-frozen before it applies.
(d) *GAP set:* for a position, the set of absent sessions its
holding period spans. *Split set:* the set of split effective
sessions (per the checker's convention record) its holding period
spans.

**§1 — Engine semantics (A1).** The corrected baseline inherits
the C1 engine semantics: exits are signal-driven and there is
**no maximum hold**. The V5.4 forward family's
`MAX_HOLD_BARS = 30` is not imported into the baseline family,
and the baseline's no-cap rule is not imported into any forward
claim. Hold counting under §3 counts toward no cap in this family.

**§2 — Fills (R1).** An entry or exit fill occurs only at the
open of a bar present in the frame. If the bar immediately
following a signal bar is absent, the fill defers to the next
present bar's open. No fill is ever priced from an absent session.

**§3 — Hold counting (R2).** Hold duration is counted in
constructed bars present in the frame, in frame order. Absent
sessions neither increment nor reset the count. A position
crossing absent sessions therefore lives longer in calendar time
by exactly those sessions; this is declared behavior, not an
accident to be corrected post hoc.

**§4 — Indicator windows (A2).** All frozen indicator windows
(EMA/ATR/ADX/breakout/volume) are **row-based**: a window of N is
the N preceding constructed bars, however much calendar time they
span. Calendar-aware padding or window invalidation is a strategy
change (new family), not a clarification, and is not adopted
here. When any indicator window feeding a position's entry signal
spanned an absent session, that fact is recorded on the trade
(§5 disclosure input).

**§5 — Subset flagging and readout accounting (R3 + A3).**
(a) A position whose entry fill, exit fill, or holding period
crosses one or more absent sessions is flagged **GAP_CROSSED**,
with the absent session dates enumerated from the qualification
record.
(b) A position whose holding period spans one or more split
effective sessions is flagged **SPLIT_SPANNING**, with the events
enumerated from the checker's convention record. Under the
uniform adjusted basis this flag is descriptive only: it changes
no price, no date, and no inclusion decision.
(c) Every readout reports, for each of the GAP_CROSSED and
SPLIT_SPANNING subsets: the subset count, its R sum, its share
of trades, and its share of |R| — alongside the pooled figures.
The worst trade in each flagged subset is always individually
reported.
(d) **Tripwire:** if the GAP_CROSSED subset exceeds **20% of
trades or 25% of |R|** in a readout, the readout is labeled
**GAP_DOMINATED** and the pooled headline is suspended pending
adjudication. (Values carried from the -86 A3 proposal into this
text for adoption as written.)
(e) The flags are descriptive; neither flag by itself changes any
inclusion decision.

**§6 — Symmetry (R4).** Absent sessions are absent for entries,
exits, and hold counting identically. No exit may be priced on a
session an entry could not have used. (With §0(c), this binds
data-absent sessions; there are no rule-excluded sessions to bind.)

**§7 — No silent repair; invalidation (R5 + A4).** If a missing
session is discovered inside a window already used for a readout:
the readout is entered in an **invalidation registry** (readout
id, frame pin, discovery record) and marked **INVALIDATED**;
bars are never back-filled into a frame after any outcome on that
frame has been observed; the only cure is re-materialization from
corrected qualified bytes and a full re-run under the same frozen
code, producing a new readout that cites the invalidated one as
**SUPERSEDED**. No downstream claim may cite an INVALIDATED
readout except as invalidated.

---

## Adoption block (unsigned)

Adopted by Mike: ____________________  Date: ____________

On adoption, this text is pinned as a preregistration amendment
by reference, and the fixtures specified in -86 (F2-T1 dual-engine
divergence, F2-T2 window-across-gap, F2-T3 disclosure + tripwire,
F2-T4 invalidation chain) become the conformance suite for any
engine claiming to implement it.
