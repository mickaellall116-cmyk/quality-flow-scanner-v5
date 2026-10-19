# NYSE historical notice recovery — QF-NYSE-HISTORICAL-NOTICE-RECOVERY-20261019-32 r1 (2026-10-19)

**Verdict: `HISTORICAL_PRIMARY_RECOVERY_INCOMPLETE`** — incomplete by exactly one
field (regular core hours for 2024–2025). Every dated closure, early-close, and
ad-hoc semantic missing after -31 is recovered from ICE-published bytes.
One read-only pass, ~13 min of the ≤25 hard cap, repair minutes 0.
Spec: Issue #1 comment `6259589343` (accepts -31 as
`OFFICIAL_SOURCE_CAPTURE_PARTIAL_ACCEPTED__2024_2025_PRIMARY_RECOVERY_REQUIRED`).
Frozen interval **[2024-09-16, 2026-10-16]**, not narrowed. Package:
`research_notes/nyse_historical_notice_recovery_20261019_32/`
(`RECOVERY_RECEIPT.json`, `GAP_MATRIX.md`, `FETCH_LOG.txt`, `raw/` bytes,
`SHA256_MANIFEST.txt`). The -31 package (commit `5d2060b`) is preserved unedited;
this package supersedes its coverage conclusions by reference only.

## Recovered (all ICE-published, live origin ir.theice.com, hash-pinned)

1. **NYSE Group calendar release dated Nov 10, 2023** ("Announces 2024, 2025 and
   2026 Holiday and Early Closings Calendar"), 80,348 B, sha256 `564de593…`.
   2024 column + footnotes: 10 dated closures; 13:00 ET early closes Wed Jul 3,
   Fri Nov 29, Tue Dec 24, 2024. In-interval (Sep 16→): closures Nov 28 + Dec 25;
   early closes Nov 29 + Dec 24.
2. **NYSE Group calendar release dated Nov 8, 2024** ("Announces 2025, 2026 and
   2027 …"), 94,403 B, sha256 `3b8a67d9…`. 2025 column + footnotes: 10 dated
   closures (Jan 1, Jan 20, Feb 17, Apr 18, May 26, Jun 19, Jul 4, Sep 1, Nov 27,
   Dec 25); 13:00 ET early closes Thu Jul 3, Fri Nov 28, Wed Dec 24, 2025.
   Independently corroborates the 2023 release's 2025 column, byte set for byte set.
3. **Carter closure announcement dated Dec 30, 2024** ("The New York Stock
   Exchange Will Close Markets on January 9 … National Day of Mourning"),
   72,441 B, sha256 `e1cd4c1a…`. The official dated notice spec item 3 asked for:
   NYSE Group equity and options markets closed **Thursday, January 9, 2025** for
   the National Day of Mourning for former President Jimmy Carter. The January
   2025 count delta from -31 is now dated primary evidence, not an observation.

Count cross-check (arithmetic only): 261 weekdays in 2025 − 11 weekday closures
= 250 trading days = the pinned Nov-2025 Trading_Days vintage; the Dec-2024
vintage (251) predates the Dec 30, 2024 announcement. Both vintages now reconcile
exactly with the dated record.

## Still unresolved (the reason for INCOMPLETE)

- **Regular core hours for 2024-09-16..2025-12-31.** No captured NYSE/ICE artifact
  states the 9:30 a.m.–4:00 p.m. ET core session for those years (zero `9:30`
  hits in all three releases; the releases give early-close and late-session
  times only and point to the hours page, whose historical captures are shells).
  The standing hours were not back-projected from the 2026 page.
- **Ad-hoc mechanism as a general rule** remains unstated by any captured source
  (all years) — but the interval's one ad-hoc event now carries its own dated
  official notice, which is what spec item 3 required.
- **Trader Updates route (spec item 1):** the live history page is a JS shell
  (pinned as route evidence, semantics NONE); a Wayback CDX probe of
  `nyse.com/publicdocs/nyse/updates/*` for Dec 2024–Jan 2025 returned no
  captures. No Trader Update PDF bytes were obtained; the semantics they would
  have carried are covered instead by the ICE releases above.

Per spec item 6, the pinned source package is handed off for independent review.
**No session list was generated, no calendar library was run, no environment was
built or installed, and no timestamps/OHLC were consumed.**

## Prohibitions — explicit confirmation

Public unauthenticated GETs only; search results used as locators only and never
saved or classified as evidence; zero credentials/logins; zero vendor/API keys;
zero market/OHLC data; zero schedule generation (no `XNYS_SESSION_SCHEDULE_V2`);
zero performance/backtests; zero strategy execution or imports; zero holdout
access in any form; zero installs; zero live/production/ledger writes; zero
Issue #9 work; no prior frozen record edited. TD txn
`QF-TD-READINESS-LIVE-20261017-20` remains UNUSED and untouched.
