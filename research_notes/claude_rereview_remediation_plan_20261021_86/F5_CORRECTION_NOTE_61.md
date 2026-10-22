# F5 — CORRECTION NOTE: THE -61 MEMO'S JULY-3 LABEL
## (EXECUTED in this package — original text preserved; this note is the correction of record)

**Document corrected:** `research_notes/
td_req_s2_boundary_shim_synthetic_20261020_61/CLOSURE_MEMO.md`
(sha256 ac4c9eccefd94bad2dd7d67ce951118176b192a9881188d5f3cfcad49a333d04).
The -61 memo is NOT edited; this note supersedes one label in it by
reference — the same method as the -82 item-6 correction of the -56
memo (package d2cca9c, which flagged this -61 instance at its
"Related instance" section and left it for adjudication).

## The original passage (quoted exactly, -61 CLOSURE_MEMO.md, "July-3 parity outcome" section)

> ## July-3 parity outcome — REFUSED (not established)
>
> Recorded in the harness source and restated here, NOT reconciled:
> artifact fact — 2026-07-03 is absent from the pinned schedule's
> sessions (non-session), 2026-07-02 present with close 16:00.
> Gate-7 lineage label — "-56 CLOSURE_MEMO: candidate 2026-07-03
> early-close fact = True". Gate source fact — dispatch_gate_r4.py
> derive_calendar emits 'closed_2026_07_03': xnys_schedule(
> '2026-07-03') is None. Whether the label and the source fact are
> the same claim is expressly NOT adjudicated in -61; the spec
> assigns it to the parallel Claude CP1 continuation. The shim's
> adjacency binds to the artifact only, and no §7 case depended on
> the disputed label (case 2 uses the Thanksgiving-2025 boundary:
> 2025-11-27 non-session, 2025-11-28 close 13:00) — but no case
> executed, so this design intent is unevidenced by this run.

## The correction

**2026-07-03 is a CLOSED / non-session date** (Independence Day
observed — July 4, 2026 falls on a Saturday). It is not an early
close, and no pinned source asserts an early close for it. The
"label" the passage carries — "candidate 2026-07-03 early-close
fact = True", inherited from the -56 memo's Gate-7 spot check — is
a downstream reporting label, not a source fact, and it is wrong
about the world wherever it appears in the -56/-61 lineage. The
authorities are the ones the -62 necessity audit established
(`td_s2_necessity_source_audit_20261020_62/AUDIT_MEMO.md`, §3):

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

## What this correction does and does not change in -61

- The -61 memo's own artifact fact was already correct ("absent
  from the pinned schedule's sessions (non-session)"), and its
  section outcome — July-3 parity REFUSED, not established — is
  unaffected and stands.
- The -61 memo expressly left the label-vs-source question "NOT
  adjudicated in -61" and assigned it to the Claude CP1
  continuation. Claude's -82 re-review (Slack TS
  1792628218.568909) required this correction; this note is the
  adjudication's correction of record for the -61 instance,
  completing the pair with the -82 correction of the -56 origin.
- Any future citation of the -61 passage must read the lineage
  label as corrected here: **2026-07-03 — CLOSED (non-session).**
  The -61 memo's bytes remain as written.

**Status: EXECUTED (documentation).** Owner: Muse. Effective on
adoption of this package by adjudication; no separate GO is
required for a by-reference label correction, and none was taken.
