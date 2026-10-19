# Gap matrix — QF-NYSE-HISTORICAL-NOTICE-RECOVERY-20261019-32 r1

Frozen interval: **[2024-09-16, 2026-10-16]** (unchanged). This matrix updates the -31
coverage for the missing block **2024-09-16..2025-12-31** only; the -31 package
(commit `5d2060b`) is preserved unedited and remains the record for 2026 and for
session counts. Sources here: NYSE/ICE-published bytes fetched live from ICE's
official investor-relations origin `ir.theice.com` (PRIMARY_CURRENT, pinned by
SHA-256 in `RECOVERY_RECEIPT.json`). Search results were used as locators only.

## Coverage for the previously missing block

| Period | Regular core hours | Full-day closures (dated) | Scheduled 13:00 ET early closes (dated) | Ad-hoc closure |
|---|---|---|---|---|
| 2024 (Sep 16–Dec 31) | **MISSING** (unchanged) | **PRIMARY_CURRENT — RECOVERED**: Thanksgiving Thu Nov 28, 2024; Christmas Wed Dec 25, 2024 (ICE calendar release dated Nov 10, 2023, 2024 column) | **PRIMARY_CURRENT — RECOVERED**: Fri Nov 29, 2024; Tue Dec 24, 2024 — each "close early at 1:00 p.m." (same release, footnotes ** and ***) | No ad-hoc closure occurred in this window in any captured source; no notice required or found |
| 2025 (full year) | **MISSING** (unchanged) | **PRIMARY_CURRENT — RECOVERED**: 10 scheduled closures — Jan 1, Jan 20, Feb 17, Apr 18, May 26, Jun 19, Jul 4, Sep 1, Nov 27, Dec 25 (ICE calendar release dated Nov 8, 2024, 2025 column; corroborated by the 2023 release's 2025 column) — **plus** the exceptional closure Thu Jan 9, 2025 (Carter notice, below) = 11 dated full-day closures | **PRIMARY_CURRENT — RECOVERED**: Thu Jul 3, 2025; Fri Nov 28, 2025; Wed Dec 24, 2025 — each "close early at 1:00 p.m." (2024 release, footnotes *, **, ***) | **PRIMARY_CURRENT — RECOVERED (dated official notice)**: NYSE/ICE announcement dated **Dec 30, 2024** — "it will close all NYSE Group equity and options markets on **Thursday, January 9, 2025**, in observance of the National Day of Mourning in recognition of the passing of former President Jimmy Carter." This is the dated evidence for the one-session January 2025 delta that -31 could record only as a count observation. |

## What remains unresolved (exact fields)

- **Regular core hours, 2024-09-16..2025-12-31 — still MISSING.** None of the
  recovered ICE releases states the 9:30 a.m.–4:00 p.m. ET core session (verified:
  zero `9:30` occurrences in all three artifacts). The releases state early-close
  times (1:00 p.m.), crossing-session and late-session times (5:00 p.m.) only, and
  refer readers to the hours page — whose current bytes -31 classified as 2026+
  and whose 2024/2025 captures are JS shells. The standing hours were **not**
  back-projected onto 2024/2025.
- **Ad-hoc closure mechanism as a general stated rule — not stated by any captured
  source** (unchanged from -31 for all years). What -32 adds is the dated official
  notice for the interval's one actual ad-hoc event (Jan 9, 2025), which closes
  spec item 3's test; no general mechanism text was found or fabricated.

## Attempted URLs (this pass)

Qualifying (200, pinned): the three `ir.theice.com/press/news-details/...` URLs in
`RECOVERY_RECEIPT.json`.
Attempted, no qualifying bytes:
- `https://www.nyse.com/trader-update/history` — 200, JS app shell; no dated
  notice text/tables/PDF links in raw bytes (spec item 1 route; pinned as route
  evidence, semantics NONE).
- Wayback CDX for `nyse.com/publicdocs/nyse/updates/*` (Dec 2024–Jan 2025 window)
  — returned no captures; no Trader Update PDF bytes obtained under this route.
- Search-engine indexes (locators only, never evidence): located the ICE IR
  originals above; third-party republications (nasdaq.com, businesswire
  syndication, blogs) were located but deliberately **not** captured or classified.

## Cross-checks performed (bytes vs bytes, no inference)

- The 2025 closure/early-close set is stated identically by two independently
  dated ICE releases (Nov 10, 2023 and Nov 8, 2024) — agreement inside the
  exchange's own published record.
- Session-count consistency (arithmetic cross-check only; no count used as dated
  evidence): calendar 2025 has 261 weekdays; the recovered dated record removes
  11 weekday closures (10 scheduled + Jan 9 ad-hoc) → **250 trading days**, of
  which 3 are early-close days — exactly the Nov-2025 Trading_Days vintage count
  (250) pinned in -31. The Dec-2024 vintage (251 = 261 − 10) predates the
  Carter closure announcement (Dec 30, 2024), which is precisely the one-session
  January delta -31 observed. The dated list and the official counts now agree
  in both vintages.

## Verdict

**HISTORICAL_PRIMARY_RECOVERY_INCOMPLETE** — by exactly one field: regular core
hours for 2024-09-16..2025-12-31 lack an exchange-published dated statement in
any captured artifact. Every other missing semantic from -31 (dated closures,
dated 13:00 early closes, and the January 2025 ad-hoc closure notice) is
recovered from immutable-pinned ICE-published bytes. Per spec item 6, the pinned
source package is handed off for independent review; no session list was
generated, no library was run, no timestamps/OHLC were consumed.
