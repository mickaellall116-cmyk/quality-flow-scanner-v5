# QF-CALENDAR-BACKWARD-EXTENSION-AUDIT-20261021-79 r1 — COVERAGE MEMO

**Terminal: `CALENDAR_EXTENSION_AUDIT_HOLD__STOP_FIRST_UNCOVERED_2023-10-19`**

Offline, desk-only audit. Zero vendor calls, zero credits, no network acquisition,
no downloads, no library execution, no generation run, no performance computation,
no holdout access (window metadata only, from the pinned -25 preregistration).
Dispatched as the single ranked next action of the -77 readiness audit
(`research_notes/edge_readiness_gate_audit_20261021_77/READINESS_GATE_MATRIX.md`,
commit `22b6903`, §4 RANK 1).

**Question:** does pinned official evidence cover EVERY XNYS session in the
holdout window **2023-10-19 → 2024-09-15** (-25), so that the qualified calendar
(`XNYS_SESSION_SCHEDULE_V2`, -35) could be extended backward over that window
under the -34 contract?

**Answer: NO.** The pinned record contains no dated evidence for calendar 2023
at all. The chronological walk stops at the first date of the window.

---

## 1. Single-dispatch check (before any file operation) + renumber

- At dispatch, no `research_notes/*78*` package existed and no stage
  directory existed; `git log origin/main` search found only the parent's
  dispatch record itself (`8b57859`, "bridge: -77 readiness audit
  READINESS_HOLD 0/51; -78 calendar extension audit dispatched"). No
  pre-execution commits, no parallel lane for THIS audit. **No collision —
  proceeded.**
- **Renumber (parent instruction, 2026-10-21 19:17 ET):** ChatGPT
  independently released a different task numbered -78
  (QF-CLAUDE-CP1-TARGETED-PACKAGE-20261021-78, a CP1 evidence bundle) at
  19:12:55 ET. This audit is renumbered **-79**; it was renamed before any
  commit, and nothing from this audit is committed under a -78 name.
  (Re-checked at rename time: no -78-named package exists in the
  `origin/main` tree.)

## 2. Pins verified (every input, before use)

| Input | Pin | Verified |
|---|---|---|
| -35 artifact `XNYS_SESSION_SCHEDULE_V2.json` (r2 package) | sha256 `3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88` | **MATCH** (r1 copy byte-identical as well); 524 sessions, 2024-09-16 → 2026-10-16 |
| -34 `SOURCE_SET_MANIFEST.json` — 9 primary sources | per-file sha256 (see §3) | **9/9 MATCH** (recomputed from disk) |
| Package manifests `SHA256_MANIFEST.txt` | -31: 23 files; -32: 11; -33: 10; -34: 5; -35 r2: 33; -25: 7 | **ALL OK** (-25 manifest is repo-root-relative; verified from repo root) |
| -25 `PREREGISTRATION.md` | sha256 `ccf1a988a93026a2032f5cb94f6c6d9e78705e5121ca049d60ec2a1272473c24`; line 17: `HOLDOUT_WINDOW = 2023-10-19 … 2024-09-15` | **MATCH** |

No pin mismatch occurred. PMC key discipline: no calendar library was invoked
in this audit at all, so neither the pinned native `NYSE` key nor the FORBIDDEN
`XNYS` mirror key was used; qualification here is evidence coverage only,
exactly per the -34 contract ("Qualification = date-by-date parity … against
the primary record + the pinned session counts").

## 3. Evidence chain — what the pinned record contains, by source

Primary record (per -34 §1, priority: official event notice > dated calendar
release > count cross-check):

| Source (sha256 prefix) | Content relevant to the window |
|---|---|
| SEC Release 34-103356 / SR-NYSE-2025-21 (`5f0263f7…`, -33) | NYSE Rule 1.1(d) text: Core Trading Hours 09:30–16:00 ET. Filing Jun 2025 — **after** the window. |
| NYSE RM-24-12, dated 2024-09-13 (`305fab2e…`, -33) | Operative in-block core-hours use; expiration day 2024-09-20. Dated at the window's final days; concerns a date **after** the window end. |
| ICE/NYSE Group release, Nov 10, 2023 (`564de593…`, -32) | Dated holiday + early-close tables for **2024 / 2025 / 2026 only** (full-text extraction verified: the table's year columns are exactly 2024, 2025, 2026; "2023" occurs only as the release date and boilerplate). 2024 column: 10 closures; 13:00 early closes Wed 2024-07-03, Fri 2024-11-29, Tue 2024-12-24. |
| ICE/NYSE Group release, Nov 8, 2024 (`3b8a67d9…`, -32) | Dated tables 2025 / 2026 / 2027 — outside the window except as 2025 corroboration. |
| NYSE/ICE Carter notice, Dec 30, 2024 (`e1cd4c1a…`, -32) | Exceptional closure 2025-01-09 — outside the window. |
| NYSE hours page capture (`79602f7b…`, -31) | Dated 2026 calendar + hours — outside the window. |
| Trading_Days.pdf, current vintage (`f90b6d08…`, -31) | Monthly/annual counts for **2026 / 2027 / 2028** only. |
| Trading_Days.pdf, Dec-2024 vintage (`dd349170…`, -31) | Counts for **2024 / 2025 / 2026** (2024 = 252). |
| Trading_Days.pdf, Nov-2025 vintage (`414d2ed3…`, -31) | Counts for **2025 / 2026 / 2027** (2025 = 250, final). |

Also on disk and re-checked: the -31 archived hours-page captures
(2024-12-17, 2025-01-09, 2025-12-30) are JavaScript app shells — grep finds
**zero** holiday-table content (Thanksgiving/Christmas counts 0 in all three);
`closings.pdf` is retired (last 200-status PDF vintage 2015, per -31) and its
current fetch is an HTML shell. Neither carries dated semantics for any year.

**No pinned artifact states anything dated about calendar 2023: no closure
list, no early-close list, no session count, at any priority tier.**

## 4. The walk — stop at first uncovered date

Method: chronological walk from 2023-10-19; a date is COVERED only if the
pinned record determines its status (regular session 09:30–16:00 / scheduled
13:00 early close / full-day closure). First indeterminate date ends the run
(bounded-task discipline, per -77 §4 and the task spec). No candidate session
list was generated (also per -77 §4: "no generation run inside this action").

### Segment A — 2023-10-19 → 2023-12-31 (74 calendar days, 52 weekdays): UNCOVERED

- **First uncovered date: 2023-10-19 (Thursday) — the first date of the
  window.** Classifying it (or any 2023 date) as a regular session requires
  the demonstrated absence of a closure/early close on that date, which only
  a dated 2023 enumeration can establish. None exists in the pinned record
  (§3). The walk therefore stops at the window's first date.
- The uncovered span includes the dates on which 2023's remaining scheduled
  closures and early closes would fall (late-November Thanksgiving block,
  Christmas) — the pinned record can neither confirm nor exclude any of them.
  All 52 weekdays of the segment are listed as UNCOVERED in
  `coverage_segment_a_uncovered.csv`.
- Independent second gap (recorded, not needed for the STOP): -33's core-hours
  proof rests on documents dated 2024-09-13 and 2025-06-30 — at/after the
  window's end. The lane's own standard (-32: standing hours "were not
  back-projected" without in-period proof) means segment A also lacks in-era
  dated core-hours proof. This gap is downstream of the STOP and was not
  adjudicated here.

### Segment B — 2024-01-01 → 2024-09-15 (185 weekdays): covered by the pinned record

Reported for completeness **from the record**; NOT re-enumerated
session-by-session, because the run stopped in Segment A:

- Dated (ICE Nov 10, 2023 release, 2024 column): in-window closures
  2024-01-01, 01-15, 02-19, 03-29, 05-27, 06-19, 07-04, 09-02 (8);
  in-window early close 2024-07-03 (13:00). (Out-of-window remainder of the
  2024 column: closures 11-28, 12-25; early closes 11-29, 12-24.)
- Core hours: -33 chain (Rule 1.1(d) text + RM-24-12 dated 2024-09-13,
  inside this segment's final days).
- Count cross-check (tier 3): CY2024 has 262 weekdays; 262 − 10 dated
  closures = **252** = the Dec-2024 Trading_Days vintage count. Consistent.
- A future separately-authorized audit could re-walk Segment B
  session-by-session from these pinned inputs; nothing in this memo
  pre-judges that walk.

### Boundary continuity at 2024-09-16

Date-level facts (the only level available — no candidate artifact exists):

- Holdout window end **2024-09-15 is a Sunday** (non-session). The last
  weekday of the window, Fri **2024-09-13**, is a regular session under the
  ICE 2024 column (not a closure, not an early close).
- The -35 artifact's first session is **Mon 2024-09-16, 09:30–16:00**
  (verified from the pinned artifact bytes).
- Therefore an extension ending 2024-09-15 would abut the -35 artifact with
  **no overlap and no date gap**. Artifact-to-artifact continuity is
  **NOT APPLICABLE** — no candidate extension was produced; the run stopped
  in Segment A.

## 5. What would close the gap (future task only — nothing fetched here)

An exchange-published dated artifact covering Oct–Dec 2023 obtained under its
own authorization, e.g. the ICE/NYSE Group release announcing the 2023 holiday
and early-closings calendar (the Nov-2022 predecessor of the pinned Nov-2023
release), a rendered capture of the NYSE hours page as published in 2023, or
NYSE trader-update notices for the period — hash-pinned on capture, then a
re-run of this audit. Counts alone cannot close it (tier-3 cross-check only;
they cannot enumerate closures or early closes).

## 6. Disclosures

- Inputs were read from the repo working tree and every relied-upon byte was
  hash-verified against its pin first (§2); no input was missing from disk.
- The only network operation was the `git fetch` required by the
  single-dispatch check and the final commit push — no web acquisition of
  any kind.
- The -35 artifact and all pinned packages (-25, -31, -32, -33, -34) are
  unmodified. No candidate artifact was produced, adopted, or pinned.
- This memo makes no claim about the actual historical 2023 NYSE calendar —
  only about what the pinned evidence does and does not establish.

— Muse (task QF-CALENDAR-BACKWARD-EXTENSION-AUDIT-20261021-79)
