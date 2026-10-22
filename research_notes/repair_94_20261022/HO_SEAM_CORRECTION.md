# HO equity seam correction — by reference to -93 MANIFEST_AMENDMENT §4.3

Status: correction BY REFERENCE. The -93 package (commit 96cd2bb)
is NOT edited; this note corrects one sentence of its
MANIFEST_AMENDMENT.md for every future reader and for the capture
manifest that will cite it. Trigger: ChatGPT -94 review, boundary
note 3 (Issue #1 comment 6353306848).

## The defective sentence (-93 MANIFEST_AMENDMENT §4.3, final paragraph)

> "Equity seam analog: XNYS sessions are discrete; HO ends at the
> 2024-09-15 session and DEV begins at 2024-09-16's — disjoint by
> the adopted calendar itself, verified by the same union COUNT."

## Why it is wrong

2024-09-15 was a **Sunday**. There is no XNYS session on that
date, so HO cannot "end at the 2024-09-15 session."

Verified three ways (2026-10-22, offline):
1. Weekday: 2024-09-13 Friday, 2024-09-15 Sunday, 2024-09-16
   Monday (calendar arithmetic).
2. The adopted 751-session union (V2 schedule 524 sessions +
   -81 extension 227 sessions, adopted in the three-gate freeze
   a126ce5): contains 2024-09-13 and 2024-09-16; does NOT contain
   2024-09-14 or 2024-09-15.
3. The holdout segment (extension artifact, coverage from
   2023-10-19): its last session ≤ 2024-09-16 is 2024-09-13, and
   the DEV segment (V2 schedule) coverage starts 2024-09-16.

## The corrected statement

> Equity seam: XNYS sessions are discrete; the holdout window's
> last XNYS session is **Friday 2024-09-13** and the development
> window's first XNYS session is **Monday 2024-09-16** — disjoint
> by the adopted calendar itself, verified by the same union
> COUNT. No equity session exists on 2024-09-14/15 (weekend).

## Scope of the correction

- The CRYPTO side of §4.3 is unaffected and stands as written:
  every ET date is a crypto session, so "the holdout window's
  last crypto session is the ET date 2024-09-15" is correct for
  crypto. The two calendars keep separate seams — equity at the
  09-13/09-16 session boundary, crypto at the 2024-09-16 09:30 ET
  instant boundary — exactly as §4.3's first paragraphs state.
- No other -93 clause is corrected by this note. The -93 checker
  and guard candidates never read the seam sentence; the error
  was documentary, in a manifest amendment that remains a
  candidate (not adopted). If the manifest amendment is adopted,
  it must be adopted WITH this correction attached.
