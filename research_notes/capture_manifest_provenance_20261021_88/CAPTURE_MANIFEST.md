# CAPTURE MANIFEST — UX51 QUALIFIED CAPTURE (Twelve Data, 1h)
## Task -88 · PREPARED FOR ADJUDICATION — AUTHORIZES NOTHING

**Status.** This manifest is a prepared specification for ChatGPT
adjudication and Claude spot-review, and for Mike's capture GO. It
authorizes no vendor call, no spend, and no capture. The capture GO —
including the credit-ceiling decision — remains Mike's alone. Policy A
does NOT cover this capture (its 52-credit ceiling is for the FRESH
screen day only; -85 §3 gate 6).

**Authority chain.** Mike's instruction 2026-10-21 22:01 ET ("Advance
the capture manifest and data provenance work"); three-gate freeze
(commit `a126ce5`): calendar adopted, E3 frozen at Mode A, S2
REJECTED; universe freeze Option A (commit `2705c02`); plan -85
(commit `ad9fda5`); remediation -86 (commit `62aab52`); packet -87
(commit `186aa0a`).

**DISCLOSED ASSUMPTION CH-1 (carried, per the freeze).** The adopted
751-session calendar rests on the NYSE Group/ICE release of
2022-12-21 for the 2023 window; in-era documentary proof of
09:30–16:00 core hours for 2023 does not exist in the record (the
-33 chain is dated at/after the window). CH-1 is carried in this
manifest header, in every capture receipt header for 2023-window
legs, and in every downstream readout spanning 2023. Pursuit of the
retiring documentation proceeds in parallel (task -90) and does not
block this manifest.

---

## 1. Membership and calendars (pinned)

- **Universe:** UX51, canonical membership sha256
  `b5d8877ee7d6ddd105904d7f4ca35901ebb611dac7afeab2f7676529c112e6a2`
  (serialization: symbols sorted, LF-joined, trailing LF; -86 §1 —
  the one membership pin; the `d139d7bf…` figure in -77/-85 is
  superseded by reference for membership purposes).
  - **44 session-bound names** (source order): NVDA, PLTR, TSLA,
    SOFI, SMCI, AMD, AAPL, MSFT, META, COIN, MSTR, AVGO, GOOGL,
    AMZN, NFLX, CRM, MU, INTC, LRCX, AMAT, QCOM, ARM, HOOD, APP,
    NET, SNOW, DDOG, CRWD, SHOP, RKLB, ASTS, LUNR, PYPL, NU, MELI,
    SPY, IWM, SMH, ARKK, XLF, NIO, MRNA, PFE, F.
  - **7 crypto pairs:** BTC-USD, ETH-USD, SOL-USD, DOGE-USD,
    AVAX-USD, LINK-USD, XRP-USD.
- **Equity calendar (adopted, freeze `a126ce5`):** the union of the
  -81 extension (`8d659dde…`, 227 sessions, 2023-10-19→2024-09-15)
  and XNYS_SESSION_SCHEDULE_V2 (`3358f2d9…`, 524 sessions,
  2024-09-16→2026-10-16) = **751 sessions (744 regular + 7
  early-close)**.
- **Crypto calendar (adopted spec S-C1…S-C6, -87 Gate 1):** a
  session is one America/New_York calendar date, every date a
  session, spanning [D 09:30 ET, D+1 09:30 ET); six 4H bins anchored
  09:30/13:30/17:30/21:30/01:30/05:30 ET wall-clock; DST absorbed in
  one overnight bin; crypto bars never enter the XNYS constructor.

## 2. Windows and the dev-end rule (exact)

- **W-HO (holdout window):** XNYS sessions 2023-10-19 → 2024-09-15.
  Capturing these bytes does NOT open the sealed holdout: bytes are
  qualification input only; the holdout's single governed use
  remains -25 §50. Crypto W-HO = ET dates 2023-10-19 → 2024-09-15
  (**333 dates**).
- **W-DEV (development window):** XNYS sessions 2024-09-16 →
  **2026-10-16**. **Dev-end rule (exact):** the dev window ends at
  the last session of the adopted calendar, 2026-10-16. No session
  after 2026-10-16 is captured under this manifest; extending the
  dev window requires a calendar extension adopted under the same
  -34/-35 contract first, as a separate decision. Crypto W-DEV = ET
  dates 2024-09-16 → 2026-10-16 (**761 dates**).
- **Basis:** single uniform split-adjusted basis (`adjust=splits`,
  the vendor default documented in -63 F1). This is the S2-REJECT
  world of the freeze: no unadjusted twin legs, no split-session
  exclusion. (The -85 dual-basis variant, ≈262 expected / ≈524
  worst, is NOT part of this manifest.)

## 3. Request enumeration

All legs: `interval=1h`, `adjust=splits`, `outputsize=5000`,
bar datetimes at bar open, timezone America/New_York (-63 F4).
A response at exactly 5000 rows is a truncation suspect and triggers
seam verification, never silent pagination (-63 §6c C6). No leg in
this manifest can legitimately return 5000 rows: the largest
possible leg is 4,993 bars (§3.2), so a 5000-row response is a
fail-closed defect by construction.

### 3.1 Session-bound legs — 88 requests (FIRM)

Each of the 44 symbols × 2 window legs:

| Leg | Bounds (ET dates) | Expected rows | Cap check |
|---|---|---|---|
| `<SYM>/HO` | 2023-10-19 → 2024-09-15 | 1,583 | ≤ 5000 ✓ |
| `<SYM>/DEV` | 2024-09-16 → 2026-10-16 | 3,653 | ≤ 5000 ✓ |

Expected rows are calendar-derived (-85, verified exactly against
the -75 NVDA/AAPL probe windows: 131×7 = 917, 129×7 = 903). A leg
whose row count differs from the calendar expectation is not
silently accepted: the difference is enumerated in the receipt and
adjudicated by the completeness checker (PROVENANCE.md §4) before
the symbol is qualified.

### 3.2 Crypto legs — 42 requests (FIRM under the specified convention)

This section replaces -85's ≈42 UNCONFIRMED estimate with exact
arithmetic under S-C1…S-C6. Chunks are **date-bounded**: each chunk
covers at most **208 consecutive ET dates** of one window. A
208-date chunk contains at most 208×24 + 1 = **4,993 hourly bars**
(the +1 is the fall-back hour; spring-forward chunks contain fewer),
strictly under the 5000 cap **regardless of bar gaps or DST** —
so the request count is a property of the window definitions, not
of vendor coverage. Expected bar counts (complete coverage, vendor
stamps at bar open): W-HO 333 dates = **7,992 bars** (DST nets
zero: +1 fall 2023, −1 spring 2024); W-DEV 761 dates = **18,264
bars** (DST nets zero: +2 falls, −2 springs); **26,256 bars per
symbol** across both windows.

| Chunk | ET dates | Dates | Max bars |
|---|---|---|---|
| `<SYM>/HO-C1` | 2023-10-19 → 2024-05-13 | 208 | 4,993 |
| `<SYM>/HO-C2` | 2024-05-14 → 2024-09-15 | 125 | 3,001 |
| `<SYM>/DEV-C1` | 2024-09-16 → 2025-04-11 | 208 | 4,993 |
| `<SYM>/DEV-C2` | 2025-04-12 → 2025-11-05 | 208 | 4,993 |
| `<SYM>/DEV-C3` | 2025-11-06 → 2026-06-01 | 208 | 4,993 |
| `<SYM>/DEV-C4` | 2026-06-02 → 2026-10-16 | 137 | 3,289 |

6 chunks × 7 symbols = **42 requests (FIRM)**. What remains
conventional — stated precisely, and nothing else: (a) the chunk
boundary dates above are this manifest's convention (any
date-bounded split with ≤208-date chunks yields the same count);
(b) expected *bar* counts assume complete vendor coverage at :00
bar-open stamps — the stamp **phase is UNCONFIRMED until the pilot**
(-87 Gate 1 §3); phase affects bar attribution, not chunk counts;
(c) a chunk returning materially fewer bars than its date span
implies is a coverage finding for the checker, never a re-chunking
occasion.

### 3.3 Totals (recomputed)

| Item | Expected | Worst case |
|---|---|---|
| Session-bound data legs | 88 | 176 (≤2 attempts) |
| Crypto data legs | 42 | 84 (≤2 attempts) |
| /api_usage preflights (1 per execution day × 2 days; never retried) | 2 | 2 |
| **Program total** | **132 credits** | **262 credits** |

(-85's rounded worst case of 264 used a coarser bound — every call
including preflights doubled; this manifest's discipline gives 262.
Both sit under the proposed ceiling.) **Ceiling proposed for Mike's
capture GO: 300 credits** (Policy A discipline: a ceiling is not a
GO; each phase carries its own GO record). At the live-verified
free allowance (800/day, 8/min, $0; -75 receipts) the capture is
$0 and fits one day in every scenario; execution is nevertheless
scheduled over 2 days with the pilot gate between (§4).

## 4. Pilot design

**Pilot set (17 credits expected / 33 worst case):** the -85 pilot
five session-bound symbols full-span — NVDA, TSLA, AAPL (continuity
with the -75 receipts), SPY (ETF), SMCI (in-span 10:1 split,
Oct 2024 — seam/split stress) — 5 × 2 = 10 legs; **plus BTC-USD,
all 6 crypto chunks**, added to this manifest (a delta to -85's
pilot) because -87 Gate 1 §3 requires the crypto bar-stamp phase
pinned from pilot bytes before Phase 1; plus 1 /api_usage
preflight.

**Pass criteria (all required):** (i) every leg's receipt complete
per PROVENANCE.md §2 and hash-chained; (ii) session-bound row
counts equal the calendar expectations exactly, or every difference
is enumerated and explained by the completeness checker with zero
unexplained anomalies; (iii) checker-v2 verdict recorded for all 6
symbols (PROVENANCE.md §4); (iv) the BTC-USD stamp phase is
determined from the bytes and pinned as a manifest amendment;
(v) candle-parity machinery runs clean on the pilot bytes
(byte-identical construction, DST-spanning span included).

**Stop rules (any one halts the program, fail-closed):** a leg
fails twice; a 429 or limit refusal (hard stop for the day, per
-85); a 5000-row response; an unexplained completeness anomaly;
a receipt/hash-chain break; /api_usage showing daily_usage
inconsistent with the program ledger. A stopped pilot is reported
with evidence; Phase 1 is never requested on a failed or partial
pilot.
**Phase 1 (115 credits expected):** remaining 39 session-bound
symbols × 2 = 78 legs + remaining 6 crypto symbols × 6 = 36 legs
+ 1 preflight. Phase 1 requires its own GO after the pilot gate
passes (-85 decision 9).

## 5. Execution-day shape (under a future GO — not now)

1. **Preflight:** one /api_usage call before any data call;
   receipt persisted; abort if `plan_daily_limit` ≠ 800 or
   `daily_usage` disagrees with the program ledger (the -70
   minute-vs-daily semantics repair governs: the daily bucket is
   authoritative; the 8/min figure is a rate limit, not a budget).
2. **Rate discipline:** ≤ 8 requests/minute, paced; legs execute
   in manifest order, one at a time; no parallelism.
3. **Attempts:** ≤ 2 per leg, fail-closed; a second failure stops
   the day (§4 stop rules). No same-day retry beyond the attempt
   cap may amend the ceiling.
4. **Receipts:** every attempt — success or failure — is written
   by the transactional receipt writer (-71 design, -74 closure,
   70/70) with monotonic commit state before the next leg starts
   (PROVENANCE.md §2–§3).
5. **Archive-first:** raw bodies land only in qf-data-archive
   (§6), verified by re-fetch, before the phase is reported.
   Sanitized receipts may be committed to the scanner repo; raw
   vendor bars never enter the public repo — ever.

## 6. Storage layout

Private repo `qf-data-archive` (append-only, write-once; deletion
only on Mike's approval):

```
captures/ux51_td_capture_v1_pilot/
  capture_manifest.json     (this manifest's pin + phase GO record)
  SHA256SUMS
  raw/<SYM>__<LEG>.json     (vendor bodies, byte-exact)
  receipts/<SYM>__<LEG>.receipt.json
captures/ux51_td_capture_v1_phase1/   (same layout)
```

Local mirror: `~/workspace/qf_ux51_capture_v1/store/` with the
identical layout (git-ignored in the scanner repo; the -75 store
precedent). SHA256SUMS covers every file in the capture directory
and is verified by fresh re-fetch before any phase is reported
(the -75/-81 procedure; archive commits `2f223cf`, `58ad260`).

## 7. What remains for Mike's capture GO

1. ChatGPT adjudication of this manifest + Claude spot-review.
2. Mike's **capture authorization GO**: route (Twelve Data),
   ceiling (proposed 300), this manifest pin — unlocks the pilot.
3. **Phase-1 GO** after the pilot gate passes (§4).
4. Still ahead on the chain, independently: R1–R5 freeze
   (R1R5_FREEZE_TEXT.md, prepared in this package), guard-v2 /
   checker-v2 adoptions (-89 lane), R7 GO (eligible
   2026-10-28T21:33:00Z), R30 GO (eligible 2026-11-20T21:33:00Z).
   None of them is granted or implied by the capture GO.
