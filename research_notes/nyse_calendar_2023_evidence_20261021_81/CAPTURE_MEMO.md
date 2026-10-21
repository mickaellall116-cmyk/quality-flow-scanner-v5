# QF-NYSE-CALENDAR-2023-EVIDENCE-20261021-81 — CAPTURE MEMO

**Terminal (Step 1): `OFFICIAL_2023_CALENDAR_EVIDENCE_CAPTURED__OFFICIAL_LIVE`**

Scoped official-source capture under Mike's Track-2 directive (chat,
2026-10-21 19:29 ET: "Get the missing 2023 NYSE calendar evidence"). This is
the closer named by the -79 backward-extension audit
(`CALENDAR_EXTENSION_AUDIT_HOLD__STOP_FIRST_UNCOVERED_2023-10-19`, commit
`a08e08c`), whose pinned record contained nothing dated about calendar 2023.
Single-dispatch check before any file operation: no -81 stage, package, or
pre-execution commit existed (origin/main tree/log scan clean) — proceeded.

## What was captured (source priority 1 — OFFICIAL_LIVE)

The official instrument: **"NYSE Group Announces 2023, 2024 and 2025 Holiday
and Early Closings Calendar"**, NYSE Group / Intercontinental Exchange press
release dated **December 21, 2022** (the dated predecessor of the pinned
Nov-10-2023 release; published *before* the holdout window, so it is in-era
prospective official evidence). Two renderings of the same instrument,
captured as raw bytes from the live official ICE investor-relations site:

| Artifact | URL | Retrieved (UTC) | HTTP | Bytes | SHA-256 |
|---|---|---|---|---|---|
| HTML page | `https://ir.theice.com/press/news-details/2022/NYSE-Group-Announces-2023-2024-and-2025-Holiday-and-Early-Closings-Calendar/default.aspx` | 2026-10-21T23:31:07Z..09Z | 200 | 79,672 | `4323bad770cd1769e78bab72d45408ce3e9d5ff67247fee3b8c714f0c5c46a15` |
| PDF (page's own PDF link; ICE IR-platform CDN `s2.q4cdn.com`) | `https://s2.q4cdn.com/154085107/files/doc_news/NYSE-Group-Announces-2023-2024-and-2025-Holiday-and-Early-Closings-Calendar-2022.pdf` | 2026-10-21T23:31:47Z..48Z | 200 | 164,298 | `8092099cfc8c408089257004d61da3fba4ca6b7161ed722aac1189fe83a67186` |

No Wayback capture and no distribution copy was needed — priority (1) was
available live, so neither fallback was used. No third-party calendar site was
used as evidence. Public unauthenticated GETs only; zero vendor calls, zero
credits.

**Archive:** private `qf-data-archive`, commit `58ad260`, path
`captures/nyse_calendar_2023_evidence_20261021/` (both payloads, both fetch
header records, `capture_manifest.json`, `SHA256SUMS`). Verified by fresh
re-fetch after push: `sha256sum -c` 5/5 OK; both payloads byte-identical to
the captured originals. (The HTML header record's `set-cookie` value was
redacted by the environment before archiving.)

## The document's own words — 2023 dated entries (quoted)

Lead: "NEW YORK--(BUSINESS WIRE)-- NYSE Group, part of Intercontinental
Exchange, Inc. (NYSE: ICE), … announced today the 2025 holiday calendar and
early closing dates for its cash equity markets: New York Stock Exchange, NYSE
American Equities, NYSE Arca Equities, NYSE Chicago, and NYSE National, as
well as the NYSE American Options, NYSE Arca Options and NYSE Bonds markets.
The 2023 and 2024 holiday and early closing dates are also set forth below."

2023 column of the dated table (closures), verbatim entries:

- New Year's Day — "Monday, January 2 (New Year's Day holiday observed)"
- Martin Luther King, Jr. Day — "Monday, January 16"
- Washington's Birthday — "Monday, February 20"
- Good Friday — "Friday, April 7"
- Memorial Day — "Monday, May 29"
- Juneteenth National Independence Day — "Monday, June 19"
- Independence Day — "Tuesday, July 4*"
- Labor Day — "Monday, September 4"
- Thanksgiving Day — "Thursday, November 23**"
- Christmas Day — "Monday, December 25"

2023 early closings, from the footnotes (verbatim):

- \* "Each market will close early at 1:00 p.m. (1:15 p.m. for eligible
  options) on **Monday, July 3, 2023**, Wednesday, July 3, 2024, and Thursday,
  July 3, 2025."
- \*\* "Each market will close early at 1:00 p.m. (1:15 p.m. for eligible
  options) on **Friday, November 24, 2023**, Friday, November 29, 2024, and
  Friday, November 28, 2025 (the day after Thanksgiving)."
- \*\*\* "Each market will close early at 1:00 p.m. (1:15 p.m. for eligible
  options) on **Tuesday, December 24, 2024, and Wednesday, December 24,
  2025**." — the December footnote enumerates 2024 and 2025 **only**: the
  instrument contains **no December 2023 early close**.

**Oct–Dec 2023, as the document states it (the segment the -79 walk could
not classify):**

- October 2023: no dated entries — no closure, no early close.
- Closure: **Thursday, November 23, 2023** (Thanksgiving Day).
- Early close 13:00: **Friday, November 24, 2023** (day after Thanksgiving).
- Closure: **Monday, December 25, 2023** (Christmas Day).
- No December 2023 early close exists in the instrument.

**Cross-validation against the pinned record:** the instrument's 2024
column is identical to the 2024 column of the pinned Nov-10-2023 ICE release
relied on by the -79 audit — 10 closures (01-01, 01-15, 02-19, 03-29, 05-27,
06-19, 07-04, 09-02, 11-28, 12-25) and 13:00 early closes 2024-07-03,
2024-11-29, 2024-12-24. The candidate input agrees with the pinned record on
their entire overlap. Artifact-derived count check: the 2023 column implies
260 CY2023 weekdays − 10 closures = **250 sessions** for calendar 2023.

— Muse (task QF-NYSE-CALENDAR-2023-EVIDENCE-20261021-81, Step 1)
