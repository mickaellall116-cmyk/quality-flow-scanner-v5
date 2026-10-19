# NYSE official calendar capture — QF-NYSE-OFFICIAL-CALENDAR-CAPTURE-20261018-31 r1 (2026-10-18)

**Verdict: `OFFICIAL_CALENDAR_SOURCE_COVERAGE_INCOMPLETE`** (the spec's fail-closed return).
One read-only acquisition pass, ~14 min of the ≤25 hard cap, zero repairs to sources.
Spec: Issue #1 comment `6259246088`. Frozen interval **[2024-09-16, 2026-10-16]**, frozen
before any outcome input. Package: `research_notes/nyse_official_calendar_capture_20261018_31/`
(`CAPTURE_RECEIPT.json`, `COVERAGE_MATRIX.md`, `FETCH_LOG.txt`, `raw/` bytes, `SHA256_MANIFEST.txt`).

## What was captured (all NYSE/ICE-published; hashes in the receipt)

- **PRIMARY_CURRENT** — the live "Holidays & Trading Hours" page
  (`nyse.com/markets/hours-calendars` → 302 → `nyse.com/trade/hours-calendars`), 109,229 B,
  sha256 `79602f7b…`. It now lists **2026–2028 only**: regular hours (Core 9:30–16:00 ET),
  dated closures, and 13:00 early-close footnotes. The full **2026** year is therefore
  primary-covered; its in-interval (through Oct 16) portion has 10 dated closures and
  **zero scheduled 13:00 closes** (Jul 3, 2026 is a full closure; the page's two 2026
  early closes, Nov 27 and Dec 24, fall after the interval end).
- **PRIMARY_CURRENT + PRIMARY_ARCHIVED (counts only)** — `nyse.com/publicdocs/Trading_Days.pdf`,
  the retired closings document's functional successor: live vintage (2026–2028) plus two
  immutable archived vintages (Dec 2024: 2024=252 / 2025=251 sessions; Nov 2025: 2025
  revised to 250). It states **monthly trading-day counts only** — corroboration for
  session counts, never dated closures.
- **MISSING** — `nyse.com/pdfs/closings.pdf`: origin **404**; last 200-status archived PDF
  capture is from **2015**, a vintage that cannot state 2024–2026 semantics.

## Why coverage is incomplete (the decisive facts)

1. The dated semantics for **2024-09-16…2025-12-31** exist in no capturable immutable
   exchange-published bytes under this task's authority: the live page has rotated to
   2026–2028, and every Wayback capture of the hours page from 2024/2025 is a
   **JavaScript app shell** (27–30 KB, zero holiday tables) — the tables were
   client-rendered and never entered the archived bytes. Three such shells were fetched
   and are preserved in `raw/` as route evidence.
2. The ad-hoc closure mechanism is stated by **no** captured source for any year. (Its
   footprint is visible once, indirectly: the Nov-2025 Trading_Days vintage cuts January
   2025 by one US Cash Equities session versus the Dec-2024 vintage — recorded as a
   count observation in the matrix, not as dated evidence.)
3. No gap was filled from the calendar libraries, third-party sources, search snippets,
   or inference — per spec item 4/5, nothing was silently upgraded.

Per spec item 6, **no hand-off** for a generation task is made. Closing the gap needs a
future separately scoped step (e.g., NYSE trader-update notices or a rendered capture of
the hours page as published in 2024/2025), under its own authorization.

## Disclosed incident (evidence handling)

The first pass wrote captures to `/tmp`, which was wiped by the environment before
packaging. The full URL set was re-fetched directly into the package within the same
run; **all eight artifacts came back byte-identical (SHA-256 equal to the first pass)**,
so the capture is a two-pass-verified record, and the receipt says so. No source changed
between passes; no content was reconstructed.

## Prohibitions — explicit confirmation

Public unauthenticated GETs only; zero credentials/logins; zero vendor/API keys; zero
market/OHLC data; **zero schedule generation** (no `XNYS_SESSION_SCHEDULE_V2` artifact was
emitted); zero performance/backtests; zero strategy execution or imports; zero holdout
access in any form; zero installs; zero live/production/ledger writes; zero Issue #9 work;
no prior frozen record edited. TD txn `QF-TD-READINESS-LIVE-20261017-20` remains UNUSED
and untouched.

— Muse
