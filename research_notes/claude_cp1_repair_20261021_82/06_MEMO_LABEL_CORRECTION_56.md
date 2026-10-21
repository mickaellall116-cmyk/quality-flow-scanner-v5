# ITEM 6 — CORRECTION NOTE: THE -56 MEMO'S JULY-3 LABEL
## (Original text preserved; this note is the correction of record)

**Document corrected:** `research_notes/
td_route_transaction_collision_safe_remainder_20261020_56/
CLOSURE_MEMO.md` (sha256 30f0af0e68d6d725…). The -56 memo is NOT
edited; this note supersedes one label in it by reference.

## The original passage (quoted exactly)

> "Gate-7 spot check — EXECUTED WITH FACTS (the -55 gap closed):
> … Original and candidate derive_calendar facts IDENTICAL (4 facts
> each); **candidate 2026-07-03 early-close fact = True.** PASS."

## The correction

**2026-07-03 is a CLOSED / non-session date** (Independence Day
observed — July 4, 2026 falls on a Saturday). It is not an early
close, and no pinned source asserts an early close for it. The
-62 necessity audit (`td_s2_necessity_source_audit_20261020_62/
AUDIT_MEMO.md`, sha256 2ce48fd5b52ca6eb…, §3) established this from
both authoritative sources:

- **Gate-7 source** (`dispatch_gate_r4.py`, sha256 b53996454650…):
  the gate re-derives the calendar and requires
  `closed_2026_07_03 is True` (derivation:
  `xnys_schedule(pd.Timestamp('2026-07-03')) is None`). The word
  "early" appears ZERO times in that file; the gate has no
  early-close predicate for 2026-07-03. It asserts CLOSED.
- **Pinned artifact** (`XNYS_SESSION_SCHEDULE_V2.json`, sha256
  3358f2d9cc233142…, -35 r2 qualified): contains NO 2026-07-03
  session at all (sessions run 2026-07-02 → 2026-07-06). It asserts
  NON-SESSION.

The "early-close fact = True" in the -56 memo is therefore a
downstream reporting label attached to the validator's
derive_calendar output — the label the -62 audit identified as
existing "only as a downstream reporting label (Gate-7 spot summaries
in the -56/-61 lineage), not as a source fact." The -56 memo's
underlying comparison result (original and candidate facts IDENTICAL)
is not impugned by this correction: both sides carried the same
label, so the equality the spot check was testing still held. What
was wrong is the label's claim about the world, and any future
citation of the -56 memo must read that passage as corrected here:
**2026-07-03 — CLOSED (non-session).**

## The missing -56 fact JSON: UNVERIFIED

The memo reports derive_calendar "facts" (4 per side) but the -56
package contains no fact JSON recording them. Verified for this note:
the package's JSON artifacts (`run_artifacts/driver_matrix.json`,
`run_artifacts/proof_results.json`, `td56_self_check_results.json`,
`LEASE_EVIDENCE.json`) contain ZERO occurrences of "2026-07-03" or
"early". The 4-fact record exists only as the memo's prose. Per the
repair spec, the fact JSON is marked **UNVERIFIED — NOT PRESENT IN
THE PACKAGE**, and it is NOT reconstructed here: the derivation was a
live-calendar read at execution time, so any reconstruction would be
a new computation wearing the old one's name. If a future task needs
the fact record, it must re-derive it under its own receipt.

## Related instance (flagged, not corrected here)

The -61 closure memo (line 79) quotes the same "early-close fact =
True" label in its Gate-7 discussion. It is the same defect class,
inherited from the same lineage. Correcting -61 is outside this
item's scope; it is flagged for adjudication so the correction can
be extended by reference rather than discovered twice.

**Status: DOCUMENTED.** Owner: Muse. Effective on adoption of this
package by adjudication; the -56 memo's bytes remain as written.
