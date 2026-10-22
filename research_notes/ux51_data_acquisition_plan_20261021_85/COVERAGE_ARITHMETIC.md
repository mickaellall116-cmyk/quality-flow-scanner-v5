# COVERAGE ARITHMETIC — appendix to ACQUISITION_PLAN.md (task -85)

All counts below were recomputed in this task from the pinned calendar
artifacts (retrieved at origin/main, 2026-10-21). Nothing is copied from a
summary without recomputation; where a figure rests on a probe receipt,
the receipt package is named.

## A. Session counts (from the calendar artifacts' own bytes)

| Window | Source artifact | Sessions | Regular (close 16:00) | Early-close (close 13:00) |
|---|---|---|---|---|
| Holdout 2023-10-19 → 2024-09-15 | -81 candidate, sha 8d659dde9ccb51b9d86d6c45759abceb6ccd90ad7fa49e7478b13c2dc153a0a2 (CANDIDATE_NOT_ADOPTED) | 227 | 225 | 2 (2023-11-24, 2024-07-03) |
| Dev 2024-09-16 → 2026-10-16 | -35 r2 XNYS_SESSION_SCHEDULE_V2, sha 3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88 (commit 9c62e25) | 524 | 519 | 5 (2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28, 2025-12-24) |
| **Total** | | **751** | **744** | **7** |

Method: parsed both JSON artifacts; counted `sessions[]` by their `close`
field. Early-close dates listed verbatim from the artifacts.

## B. Bars per session — derivation

The pinned constructor (construct_4h, sha d47e8df1…; header of the -82
fixture byte-copy, fixtures/construct_4h_fixture_copy.py) defines session
bins from local session time:

- regular day: [09:30, 13:30) → labeled 09:30; [13:30, close) → labeled 13:30
- early-close day: single [09:30, 13:00) bin → labeled 09:30

Twelve Data 1h bars are timestamped at bar OPEN (-63 fact F4: "Datetime
at local exchange time referring to when the bar with specified interval
was opened"). The hourly bars opening inside a session are therefore:

- Regular session (09:30–16:00): opens 09:30, 10:30, 11:30, 12:30 (→ 09:30
  bin) and 13:30, 14:30, 15:30 (→ 13:30 bin) = **7 bars → 2 4H bars**.
- Early-close session (09:30–13:00): opens 09:30, 10:30, 11:30, 12:30
  (the 12:30 bar spans 12:30–13:00) = **4 bars → 1 4H bar**.

## C. Empirical verification of §B against -75 probe receipts

Two independent windows from the Day-1 probe (receipts in
research_notes/td_probe_day1_rerun_20261021_75/, result commit 8533a59)
match the derivation EXACTLY:

| Probe leg | Window | Sessions in window (from §A artifacts) | Predicted 1h rows @ §B | Actual rows in receipt |
|---|---|---|---|---|
| REQ-ADJ-01 NVDA (splits) | 2023-12-13 → 2024-06-21 | 131, all regular | 131 × 7 = **917** | **917** |
| REQ-ADJ-03 AAPL (control) | 2026-02-19 → 2026-08-24 | 129, all regular (per -35 r2) | 129 × 7 = **903** | **903** |

(The adjust=none twins returned identical row counts: 917 and 911 for
NVDA/TSLA respectively; TSLA's window is in 2022, outside both calendar
artifacts, and is not used as a verification case.)

## D. Bars per symbol and totals (session-bound names)

| Span | 1h bars / symbol | 4H bars / symbol |
|---|---|---|
| Holdout | 225×7 + 2×4 = **1583** | 225×2 + 2×1 = **452** |
| Dev | 519×7 + 5×4 = **3653** | 519×2 + 5×1 = **1043** |
| **Total** | **5236** | **1495** |

44 session-bound symbols: 44 × 5236 = **230,384** 1h bars → 44 × 1495 =
**65,780** 4H bars.

Crypto names (7): continuous market, not derivable from §A. Full-span
estimate: 2023-10-19 → 2026-10-16 = 1093 days × 24 hourly bars =
≈26,232 bars/symbol — **ESTIMATE**, exact figure UNCONFIRMED until the
capture manifest pins the crypto window convention.

## E. Request / credit arithmetic (Twelve Data)

Unit facts (-63): /time_series = 1 credit per symbol/request (F2);
`outputsize` max 5000 (F3); /api_usage = 1 credit. Attempt discipline:
≤2 attempts per request, fail-closed (-63 §6b A3 — tighter than the
pilot manifest's max_attempts=3).

- Chunks per session-bound symbol per basis: ceil(5236 / 5000) = **2**.
  Seam-aligned realization (holdout window 1583 rows + dev window 3653
  rows, each < 5000) is also 2 — no extra cost for provenance-clean
  chunking.
- Session-bound requests (single basis): 44 × 2 = **88 (firm)**.
- Crypto requests (single basis): ceil(26,232 / 5000) = 6 per symbol →
  7 × 6 = **≈42 (ESTIMATE)**.
- Usage preflights: 1 per execution day; plan schedules 2 execution days
  → **2**.
- **Expected total (single basis): 88 + 42 + 2 ≈ 132 credits**
  (88 firm; ≈44 estimated).
- **Worst case (every request attempted twice): ≈ 264 credits.**
- Dual-basis variant: expected ≈ 262; worst ≈ 524.
- Day-fit at the live-verified free allowance (800/day, -75 receipts):
  every scenario fits in ONE day (max 524 < 800). Rate floor at the
  documented minute limit (8/min): 132 requests ≥ 132/8 ≈ 16.5 → ≥17
  minutes of transmission.
- Fold headroom (context, -25/-77): dev 524 sessions ⇒ at most
  floor((524 − 252) / 63) = **4** full 63-session OOS blocks after a
  252-session expanding train. The holdout's 227 sessions are the sealed
  confirmation window, not a fold source (-25).

## F. Revision-leg arithmetic (probe C5, for gate 3)

Per -63 §6b: each REV day (R7, R30) = 1 usage + 2 data first attempts =
3; ≤6 with the ≤2-attempt cap. Both legs: expected 6 credits, worst 12.
Eligibility instants from the immutable -75 receipt instant
2026-10-21T21:33:00Z (-77 §3): R7 ≥ 2026-10-28T21:33:00Z;
R30 ≥ 2026-11-20T21:33:00Z.
