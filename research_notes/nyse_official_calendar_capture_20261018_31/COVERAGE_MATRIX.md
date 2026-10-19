# Coverage matrix — QF-NYSE-OFFICIAL-CALENDAR-CAPTURE-20261018-31 r1

Frozen interval: **[2024-09-16, 2026-10-16]**. Sources: only NYSE/ICE-published bytes
(current origin, or immutable web.archive.org captures of the exact original NYSE URLs).
Classifications per the -31 spec: PRIMARY_CURRENT / PRIMARY_ARCHIVED / MISSING.

## Per year × semantic

| Year (in interval) | Regular hours | Full-day closures (dated) | Scheduled 13:00 ET early closes (dated) | Trading-day counts (monthly) | Ad-hoc closure mechanism |
|---|---|---|---|---|---|
| 2024 (Sep 16–Dec 31) | MISSING | MISSING | MISSING | PRIMARY_ARCHIVED (Trading_Days.pdf, Dec-2024 capture `dd349170…`) | MISSING |
| 2025 (full year) | MISSING | MISSING | MISSING | PRIMARY_ARCHIVED (Trading_Days.pdf, Dec-2024 + Nov-2025 captures) | MISSING |
| 2026 (Jan 1–Oct 16) | PRIMARY_CURRENT (hours page `79602f7b…`) | PRIMARY_CURRENT (hours page) | PRIMARY_CURRENT (hours page footnotes) | PRIMARY_CURRENT (Trading_Days.pdf `f90b6d08…`) | MISSING |

## Why 2024/2025 dated semantics are MISSING (evidence, not inference)

- The live NYSE "Holidays & Trading Hours" page (redirected to `nyse.com/trade/hours-calendars`)
  now lists **2026–2028 only**; the 2024/2025 tables have rotated off.
- Immutable Wayback captures of that exact page exist for 2024/2025 (fetched: 2024-12-17,
  2025-01-09, 2025-12-30), but every archived copy is a **JavaScript app shell** — the holiday
  tables were client-rendered and are absent from the raw bytes (no holiday names, no year
  tables in 27–30 KB of HTML). They cannot serve as dated evidence.
- The legacy official document `nyse.com/pdfs/closings.pdf` is **retired (origin 404)**; its
  last 200-status archived PDF capture is from **2015**, a vintage that cannot state
  2024–2026 semantics.
- The surviving official document, `nyse.com/publicdocs/Trading_Days.pdf` (live + archived
  vintages captured and pinned), states **monthly trading-day counts only** — no dated
  closures, no early-close dates, no hours. It corroborates session counts; it cannot
  substitute for the dated calendar.
- No gap was filled from the calendar libraries, third-party sites, or inference.

## What the captured bytes DO establish (verbatim extraction, for the record)

From the PRIMARY_CURRENT hours page (`raw/hours_current_full.html`), 2026 column:

- **Regular hours:** Core Trading Session **9:30 a.m. to 4:00 p.m. ET**.
- **Full-day closures 2026 (10):** New Year's Day Thu Jan 1; Martin Luther King, Jr. Day
  Mon Jan 19; Washington's Birthday Mon Feb 16; Good Friday Fri Apr 3; Memorial Day
  Mon May 25; Juneteenth National Independence Day Fri Jun 19; Independence Day
  Fri Jul 3 (observed); Labor Day Mon Sep 7; Thanksgiving Day Thu Nov 26; Christmas Day
  Fri Dec 25.
- **Scheduled 13:00 ET early closes for 2026 (2 on the page):** **Fri Nov 27, 2026**
  (day after Thanksgiving; footnote ***) and **Thu Dec 24, 2026** (footnote ****).
  Both dates fall **after** the interval end 2026-10-16, so the scheduled 13:00 closes
  strictly inside the interval for 2026 number **0** (Jul 3, 2026 is a full closure,
  not an early close). The two dated entries are extracted here because the source
  table states the full 2026 year; only the through-Oct-16 portion is in-interval.
- **Counts cross-check (US Cash Equities):** Trading_Days.pdf current vintage gives
  2026 = 251 sessions; Dec-2024 vintage gives 2024 = 252, 2025 = 251; Nov-2025 vintage
  revises 2025 to 250 — the delta is January 2025 (21→20 US Cash Equities days between
  vintages), consistent with one unscheduled January 2025 closure visible only as an
  official count change. This is recorded as a count observation, NOT as dated evidence.

## Verdict

**OFFICIAL_CALENDAR_SOURCE_COVERAGE_INCOMPLETE.** Dated closure / early-close / hours
semantics for **2024-09-16 through 2025-12-31** lack any immutable exchange-published
source obtainable under this task's authority, and the ad-hoc closure mechanism is not
stated by any captured source for any year. Per spec item 6, **no hand-off** of artifacts
for a generation task is made; the pinned artifacts above stand as the partial record.
What would close the gap (for a future task to scope, not asserted here): an
exchange-published dated artifact for 2024–2025 (e.g., NYSE trader-update notices or a
rendered capture of the hours page as published in those years) obtained under its own
authorization.
