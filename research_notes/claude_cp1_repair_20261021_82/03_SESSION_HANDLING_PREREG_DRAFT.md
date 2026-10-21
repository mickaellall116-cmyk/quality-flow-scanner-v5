# ITEM 3 — MISSING / EXCLUDED-SESSION POSITION HANDLING
## PREREGISTRATION DRAFT — NOT ADOPTED, NOT A STRATEGY CHANGE

This document does two different things and labels them so they can
never be confused:

- **[IMPLIED]** rules state what the frozen code already does. They
  are descriptions of pinned behavior, cited to the pinned source.
  They are not proposals.
- **[DRAFT]** rules are proposed preregistration language for
  adjudication (ChatGPT + Claude) and freeze (Mike). Until frozen,
  they bind nothing, and no run may cite them.

No strategy tuning appears in either class: no entry, exit, threshold,
or sizing parameter is proposed, changed, or motivated here.

## What the frozen stack already implies [IMPLIED]

1. **Only constructed bars exist.** The pinned constructor
   (`construct_4h.py`, d47e8df1…) builds bars only for exchange-open
   dates; an unknown/closed date raises (the v1 16:00 fallback was
   removed in v2). A session with no qualified bars is therefore not
   "skipped" by a position — it is absent from the frame the strategy
   ever sees.
2. **Session integrity is fail-closed upstream.** The frozen fold
   materializer (`fold_materializer.py`, -25) raises on
   DUPLICATE_TIMESTAMP, NON_MONOTONIC, BAD_GRID (a session carrying
   other than its exact grid bars, weekend sessions), UNRESOLVED_GAP
   (a missing Mon–Fri session not in the declared-holiday set), and
   HOLDOUT_TOUCH. A missing session that is not a declared holiday
   therefore aborts materialization rather than silently shortening a
   position's life. A 13:00-close session is exactly one 09:30 bar and
   counts as one session (-34 contract; -27 suite, 18/18).
3. **Exclusion removes bars and entries together.** The -59 S2
   transform's recorded semantics: for each split event, the
   {prev(D), D, next(D)} sessions' bars AND candidate entries are
   removed together, the output is an exact subset of the inputs (no
   imputation, no fill, no synthetic bars), and every removal is
   written to a removed-session ledger citing its causing event.
   (The transform is qualified standalone; it is not integrated —
   item 2.)
4. **Hold counting is bar counting.** In the frozen design, a
   position's age (e.g., the 30-bar max hold) and its exit checks are
   evaluated on constructed bars in frame order. Sessions absent from
   the frame contribute no bar, no age increment, and no fill
   opportunity — by construction, not by a special case.

## Proposed preregistration language [DRAFT]

- **R1 (fills).** An entry or exit fill occurs only at the open of a
  bar present in the qualified constructed frame. If the bar
  immediately following a signal bar is absent from the frame
  (excluded session, unqualified session, or data gap that survived
  qualification), the fill defers to the next present bar's open.
  No fill is ever priced from an absent session.
- **R2 (hold counting).** Hold duration is counted in constructed
  bars present in the frame, in frame order. Absent sessions neither
  increment nor reset the count. A position crossing an excluded
  session therefore lives longer in calendar time by exactly the
  excluded sessions, and this is the intended, declared behavior —
  not an accident to be corrected post hoc.
- **R3 (gap flagging).** Any position whose entry fill, exit fill, or
  holding period crosses one or more absent sessions (per R1/R2) is
  flagged `GAP_CROSSED` in the trade ledger, with the absent session
  dates enumerated from the removed-session ledger (exclusions) or
  the qualification record (data gaps). The flag is descriptive; it
  changes no price, no date, and no inclusion decision by itself.
  Whether GAP_CROSSED trades are reported as a separate descriptive
  stratum at readout is a readout decision for the freeze, proposed
  here as: report pooled, with the gap-crossed subset's count always
  disclosed alongside.
- **R4 (excluded-session symmetry).** Sessions excluded by a frozen
  exclusion rule (e.g., REQ-S2, if and when integrated) are absent
  for entries, exits, and hold counting identically. No rule in this
  draft permits an exit to be priced on a session an entry could not
  have used.
- **R5 (no silent repair).** If qualification discovers a missing
  session inside a window already used for a readout, the readout is
  labeled with the discovery; bars are never back-filled into a frame
  after any outcome on that frame has been observed.

## Why this needs a freeze at all

Rules R1/R2 describe what the code does, but a *position* is an
engine-level object: the corrected-baseline engine's treatment of a
deferred fill (R1) and a gap-crossed hold (R2/R3) has never been
exercised on a qualified frame, because no qualified frame exists
(-77: 0/51). Freezing the language before the first qualified frame
exists is precisely what makes the first run a test instead of a
negotiation. Adoption path: adjudication (ChatGPT + Claude) → Mike
freezes → the frozen text is pinned as an amendment to the -25
preregistration by reference (the preregistration itself is never
edited).

**Status: DOCUMENTED (draft).** Owner: Muse (draft). Freeze:
**REQUIRES_SEPARATE_GO** (Mike, after adjudication).
