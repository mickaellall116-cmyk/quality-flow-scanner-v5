# QF-NYSE-CALENDAR-2023-EVIDENCE-20261021-81 — RE-AUDIT OF THE -79 EXTENSION WALK

**Terminal: `CALENDAR_EXTENSION_REAUDIT_COMPLETE__FULL_WINDOW_COVERED__CANDIDATE_PRODUCED`**

Re-run of the -79 backward-extension walk (window **2023-10-19 → 2024-09-15**,
-25 preregistration pin) with the -81 captured ICE release of Dec 21, 2022 as
a **CANDIDATE input** — not adopted, not pinned into any existing package; the
-35 artifact and all pinned packages (-25, -31..-35) are unmodified. Rules
applied: the -34 contract (a 13:00-close date is one session, open 09:30,
counts as one session) and the -79 walk standard (a date is covered only if
the record determines its status: regular session 09:30–16:00 / 13:00 early
close / full-day closure; stop at the first indeterminate date). **No date in
the window is indeterminate under the combined record — the walk completes;
there is no stop date.**

## Evidence chain per segment

- **Segment A — 2023-10-19 → 2023-12-31:** the -81 artifact (qf-data-archive
  `58ad260`; HTML sha256 `4323bad7…`, PDF sha256 `8092099c…`). Its dated 2023
  table + footnotes classify every weekday of the segment: closures
  **2023-11-23** (Thanksgiving) and **2023-12-25** (Christmas) fall inside the
  segment; early close **2023-11-24** (13:00, day after Thanksgiving); all
  other weekdays are regular sessions by the table's exhaustive enumeration,
  at the same evidence tier (dated exchange calendar release) the -79 audit
  accepted for Segment B. Segment A: 52 weekdays − 2 closures = **50
  sessions** (the 2023-11-24 early close counts as one session).
- **Segment B — 2024-01-01 → 2024-09-15:** enumerated session-by-session in
  this re-run (the -79 run had reported it record-derived only, having
  stopped in Segment A). Inputs: the pinned Nov-10-2023 ICE release 2024
  column (closures 01-01, 01-15, 02-19, 03-29, 05-27, 06-19, 07-04, 09-02 in
  window; early close 2024-07-03 13:00), corroborated identically by the -81
  artifact's 2024 column, and consistent with the -79 count cross-check
  (262 CY2024 weekdays − 10 closures = 252 = Dec-2024 Trading_Days vintage).
  Segment B: 185 weekdays − 8 closures = **177 sessions**.
- **Boundary at 2024-09-16:** verified from bytes. The -35 artifact
  (`XNYS_SESSION_SCHEDULE_V2`, disk sha256
  `3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88` —
  MATCH to its pin; 524 sessions) starts Mon **2024-09-16** 09:30–16:00. The
  candidate's last session is Fri **2024-09-13** (regular session; 2024-09-15
  is a Sunday). The candidate abuts the -35 artifact with **no overlap and
  no date gap** — the same date-level continuity -79 established, now backed
  by an actual candidate artifact.

## Candidate artifact (CANDIDATE — adoption is a separate governance step)

`XNYS_SESSION_SCHEDULE_CANDIDATE_EXTENSION_20261021_81.json` in this package:
12,221 bytes, **sha256
`8d659dde9ccb51b9d86d6c45759abceb6ccd90ad7fa49e7478b13c2dc153a0a2`**,
mirroring the -35 schema (`exchange: XNYS`, sessions as
`{date, open, close}`), `status: CANDIDATE_NOT_ADOPTED`, coverage
2023-10-19 → 2024-09-15, **227 sessions** (50 + 177), exactly two 13:00
early-close sessions in the window: **2023-11-24** and **2024-07-03**.

## Core-hours sub-gap (the second gap -79 flagged): REMAINS OPEN

The -81 artifact does **not** resolve in-era core-hours evidence for 2023
dates. It states early closings ("close early at 1:00 p.m.") on named dates
and refers readers to the NYSE hours page for "holidays and hours", but it
nowhere states 09:30–16:00 core hours for 2023. The only core-hours proof in
the record remains the -33 chain (NYSE Rule 1.1(d) text, SEC filing Jun 2025;
RM-24-12 dated 2024-09-13) — documents dated at/after the window, which under
the lane's own -32 standard were not back-projected. Precisely scoped: the
gap that stopped the -79 walk — dated closure/early-close enumeration for
Oct–Dec 2023 — is **closed** by the -81 artifact; session *classification*
coverage for the full window is complete. The distinct evidence class
"in-era dated core-hours proof for 2023" is still absent and is recorded here
as an open sub-gap for adjudication, not silently closed. (The candidate's
09:30 open / 16:00 regular close apply the -34 contract's session definition,
the same convention the qualified -35 artifact embodies for 2024-09-16
onward.)

## Disclosures

- The candidate's Segment B rests on the pinned record via -79 plus the -81
  artifact's identical 2024 column; no new 2024 evidence was needed or
  fetched.
- Ad-hoc closures (e.g. national-day-of-mourning closures) are stated by no
  annual release, including this one; the record contains no ad-hoc closure
  notice for Oct 2023–Sep 2024, and none is known to the lane's record for
  that span. The walk's standard is the same one -79 applied to Segment B:
  dated release enumeration + count cross-check.
- No vendor calls, no credits, no market data, no performance computation, no
  holdout access (window metadata only, from the pinned -25 preregistration),
  no library execution (PMC `XNYS` mirror not used; no calendar library
  invoked — sessions were enumerated directly from the dated evidence).
- Nothing was adopted or pinned: this package proposes; governance disposes.

— Muse (task QF-NYSE-CALENDAR-2023-EVIDENCE-20261021-81, Step 2)
