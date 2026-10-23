# ROUTE COMPARISON — QF-DATA-ROUTE-READINESS-20261023-01

From documented repo evidence only; no external request was made.
Requirement: immutable corrected-grid raw 1h bytes for the frozen
UX51 cohort (44 XNYS + 7 crypto), windows W-HO 2023-10-19→2024-09-15
and W-DEV 2024-09-16→2026-10-16, with receipts strong enough to
qualify the bytes for a corrected-baseline run.

## Twelve Data (the -88 capture-manifest lineage)

- **Coverage 44+7: YES, by construction.** 88 session-bound legs +
  42 date-bounded crypto chunks = 130 data legs (manifest §3);
  expected rows are calendar-derived per leg, so completeness is
  checkable, not assumed. Crypto stamp phase is UNCONFIRMED until
  the pilot — it affects bar attribution, not request counts.
- **2023 reach: DEMONSTRATED.** The Day-1 probe (-75) pulled real
  2023-12→2024-06 NVDA 1h bars; it is the only route with
  demonstrated 2023 capability in the record (-77).
- **Receipts/versioning:** per-response bodies archived write-once
  in qf-data-archive with receipts and hash chain (schema in this
  package); the Day-1 archive (commit `2f223cf`) is the working
  precedent. Vendor bars carry no vendor-side versioning, but the
  capture receipt freezes exactly what was served, when — the
  as-of evidence is ours, and it is immutable.
- **Adjusted/unadjusted:** uniform `adjust=splits` basis (E3 Mode A;
  strategy math is invariant under uniform adjustment, -62). Probe
  proved splits back-adjust prices AND scale volume ×10, flip
  exactly on the split date (NVDA PASS).
- **Known defect:** TSLA 2022 legs returned 166 zero-volume bars
  with nonzero OHLC range → C2 frozen NOT_EVALUABLE. A vendor data-
  completeness risk the qualification checker exists to catch;
  scoped to the 2022 probe window, not observed in 2023/2024 legs.
- **Rate/cost:** free tier 800 credits/day, 8/min, $0 (live-verified
  -75: `plan_daily_limit=800`). Program 146 expected / 289 worst
  (BLOCK-BRACKET-10). Two execution days at the manifest's pacing.
- **Qualification gaps:** guard v3 / checker v3 (candidate-2) are
  built and fixture-proven but UNADOPTED (G3/G4 = Mike's GOs after
  adjudication); crypto stamp phase unconfirmed until pilot.

## Yahoo 1h capture (the already-approved live-feed route)

- **Coverage 44+7: NO for the required windows.** Yahoo 1h
  reachback is a rolling ~730-session window: Stage C (2026-09-29)
  already bottomed at 2023-10-31, 8 sessions short of the
  2023-10-19 window start, and the window recedes daily. The
  holdout window is structurally unacquirable from Yahoo (-77).
- **Receipts/versioning: NONE available.** No response receipts, no
  as-of evidence; bars are silently restated. The clean-capture
  lane built around this (QFAR1 + rev.3 executor) is PARKED by
  Mike's decision: candidate READY_FOR_SEPARATE_ADOPTION, never
  adopted, and this host (all-root) cannot provide the privileged
  trust anchor the design wanted. No Yahoo capture has ever been
  authorized or run under it.
- **Existing Stage C bytes:** fail qualification on coverage
  (38/44, 0/7 crypto), provenance (local mutable, no receipts),
  and window (see INVENTORY.md).
- **Status:** Yahoo remains the live scanning feed (recovered
  2026-10-14). Feed ≠ capture route.

## Tiingo (for completeness)

Terms bar persistence of the data → cannot be the immutable
archive route by construction. The degraded-mode observer proved
gap-fill feasibility only; no incumbency credit (spec rule).
Disposition (deletion) is Mike's pending decision. Not a candidate.

## Decisive line per route

- **Twelve Data:** the only route that can produce qualifying
  bytes — demonstrated 2023 reach, receipt-grade provenance,
  $0 within the free tier; cost is 146/289 credits and a capture GO.
- **Yahoo:** free and already connected, but the 2023 window is
  gone and unreceipted bars cannot qualify — structurally out.
- **Tiingo:** license bars the archive itself — out by terms.
