# TWELVE DATA PILOT — STEP 1 RESULT — 2026-10-23

**States:** SENT (Issue #1 comment 6366485895) → ACK (Slack TS
1792765630.868999) → this RESULT. Independent PASS/HOLD is
ChatGPT's/Claude's step, not claimed here.

**Authorization:** Mike's direct GO in the main chat, 2026-10-23
10:20 ET, for Step 1 ONLY, under the pinned readiness package
`edc44d9` (capture manifest root digest
`79ccdd128e0b36537f56f8ae36a731b719e989b9756f65856b7dc47344327122`).

## Outcome in one line

**Pilot STOPPED on a documented abort condition at leg 9 of 16.**
SMCI/HO returned a TSLA-class volume-completeness failure; the leg
is quarantined UNQUALIFIED, no receipt was emitted for it, and per
AUTHORIZATION_CARD.md the pilot halted. SMCI/DEV and all six
BTC-USD chunks were never attempted. **The pilot gate does NOT
pass** (-88 §4 criteria (i)/(ii) fail for SMCI; criterion (iv),
BTC stamp phase, undetermined). Step 2 is NOT requested.

## Credits (exact)

- Preflight `/api_usage` (once, never retried): 2026-10-23T14:28:55Z,
  HTTP 200. Daily fields read per the -69 repair: `daily_usage=1`,
  `plan_daily_limit=800` (PASS; `plan_limit=8` is the per-minute
  limit and was not used). Remaining daily quota 799 ≥ 37 cap.
- 9 data legs attempted, each 1 credit (provider header
  `api-credits-request: 1` on every leg), all first-attempt HTTP 200.
- **Incremental pilot spend: 10 credits** (1 preflight + 9 legs) of
  the 37 hard max. **Program Twelve Data total: 8 → 18 credits.**
  $0, free tier, no upgrade.

## Legs

All legs: `/time_series`, interval 1h, `adjust=splits`,
`outputsize=5000`, `order=ASC`, timezone America/New_York,
start `T00:00:00` / end `T23:59:59` ET (the -75 request form).

| Leg | Rows | Expected | Δ | First bar | Last bar | Status |
|---|---|---|---|---|---|---|
| NVDA/HO | 1,583 | 1,583 | 0 | 2023-10-19 09:30 | 2024-09-13 15:30 | RECEIPTED |
| NVDA/DEV | 3,654 | 3,653 | +1 | 2024-09-16 09:30 | 2026-10-16 15:30 | RECEIPTED, delta enumerated |
| TSLA/HO | 1,583 | 1,583 | 0 | 2023-10-19 09:30 | 2024-09-13 15:30 | RECEIPTED |
| TSLA/DEV | 3,655 | 3,653 | +2 | 2024-09-16 09:30 | 2026-10-16 15:30 | RECEIPTED, delta enumerated |
| AAPL/HO | 1,583 | 1,583 | 0 | 2023-10-19 09:30 | 2024-09-13 15:30 | RECEIPTED |
| AAPL/DEV | 3,655 | 3,653 | +2 | 2024-09-16 09:30 | 2026-10-16 15:30 | RECEIPTED, delta enumerated |
| SPY/HO | 1,583 | 1,583 | 0 | 2023-10-19 09:30 | 2024-09-13 15:30 | RECEIPTED |
| SPY/DEV | 3,655 | 3,653 | +2 | 2024-09-16 09:30 | 2026-10-16 15:30 | RECEIPTED, delta enumerated |
| SMCI/HO | 1,584 | 1,583 | +1 | — | — | **QUARANTINED — volume-completeness failure** |
| SMCI/DEV | — | — | — | — | — | NOT ATTEMPTED (pilot stopped) |
| BTC-USD HO-C1/C2, DEV-C1..C4 | — | — | — | — | — | NOT ATTEMPTED (pilot stopped) |

Response-body SHA-256 per leg is in the receipts (this package)
and in the archive SHA256SUMS.

## The abort: SMCI/HO volume-completeness failure

SMCI/HO contains **19 bars with volume `"0"` and nonzero OHLC
range**, on 6 dates in April 2024: 2024-04-08 ×4, 2024-04-09 ×1,
2024-04-10 ×6, 2024-04-12 ×4, 2024-04-15 ×2, 2024-04-17 ×2.
Prices are continuous with neighbouring bars (e.g. 2024-04-10
10:30–15:30 all zero-volume with full intraday ranges) — this is
missing/zeroed volume, not no-trade bars: the TSLA-class failure
of the -76 adjudication, and a named abort condition in the
authorization card. The body is preserved byte-exact in the
archive under `quarantine/` (sha256
`737cb24ad6dcb6185529dd629177cd34f6f1f5988b0dda86fb45131c898f43d3`),
labeled UNQUALIFIED; **no receipt was fabricated for it** — the
local capture_refusal record stays local per receipt_schema.json.
No retry, no repair, no window shift was attempted.

## Coverage findings on the receipted legs (enumerated, for the checker)

- Session-date coverage is exact: every HO leg spans 227 session
  dates, every DEV leg 524 — the adopted calendar's counts.
- All HO row counts are exact (Δ0). DEV deltas (+1/+2) are fully
  explained and enumerated in each receipt's `anomalous_dates`:
  on the 13:00 early-close dates **2024-11-29** (NVDA, TSLA, AAPL,
  SPY) and **2024-12-24** (TSLA, AAPL, SPY — absent for NVDA),
  Twelve Data appends a **phantom 5th bar stamped 15:30** after
  the four real bars (09:30–12:30). The SPY 2024-11-29 stub is
  flat (O=H=L=C, volume 0). This is a vendor binning artifact on
  early closes; whether it is dropped or adjudicated belongs to
  the completeness checker (qualification step 2), not to this
  capture. (SMCI/HO's quarantined body shows the same artifact on
  2024-07-03.)
- Split basis verified in force: NVDA/HO is continuous across the
  2024-06-10 10:1 split (May 2024 max close 115.17; Jun 2024 range
  113.09–138.99 — no 10× cliff), `adjust=splits` applied uniformly.
- No duplicates (UTC-instant comparison, fold-aware), no gaps
  within sessions, no non-finite values, no 5000-row truncation
  on any attempted leg. Zero-volume bars in receipted legs occur
  ONLY as the flat early-close stubs above (AAPL/DEV 1, SPY/DEV 1).

## Receipt integrity (qualification step 1, pilot scope)

Hash chain over the 8 capture receipts verified independently of
the capture code path: prev-hash linkage from
`GENESIS:79ccdd12…`, canonical-hash recompute, per-leg response
SHA-256 vs raw bytes, manifest root on every receipt — **8/8
PASS** (`receipts/chain_index.json`). Archive SHA256SUMS verified
by fresh re-fetch: **22/22 OK**, archive copy byte-identical to
the local store.

## Storage

- Private archive `qf-data-archive`, commit **`45496f8`**,
  namespace `captures/td_pilot_20261023/` (append-only):
  manifest pin, preflight body + record, `raw/` (8 receipted
  bodies), `receipts/` (8 receipts + chain index), `quarantine/`
  (SMCI/HO body + label), SHA256SUMS.
- Local store (byte-identical): `~/workspace/qf_td_pilot_20261023/store`.
- Raw vendor bars appear ONLY in the private archive and the
  local store — never in this public repo (receipts only here).

## Bounds kept

No Step 2 capture; no 250-symbol scan; no performance or holdout
analysis (W-HO bytes are sealed/qualification-only); no production
or frozen-strategy change — PAUSED production pins re-verified
identical before/after (harness `ce7c902c…`, scanner_rules
`62aa743a…`, masterscanner_api `c3e95b25…`, v54_engine
`bde32883…`, v54_rules `1b55dedc…`; PAUSE_NEW_ENTRIES present);
no shadow launch; no purchase/upgrade. Capture run elapsed 78 s
(14:28:55Z → 14:30:13Z, paced ≤ 8 requests/min).

## What this leaves open (for adjudication, not execution)

1. SMCI volume completeness on Twelve Data: the HO failure is a
   vendor-data fact, not a request defect — the same leg re-asked
   would presumably return the same zeroed volumes. Whether SMCI
   is NOT_EVALUABLE for the baseline (the TSLA C2 precedent
   outcome class) or a different disposition applies is an
   adjudication question.
2. The early-close phantom 15:30 stub bar needs a checker ruling
   before any grid reconstruction (qualification steps 2–3).
3. BTC-USD stamp phase remains UNCONFIRMED — the crypto legs
   were never attempted; a resumed pilot would need its own GO
   naming the remaining legs (SMCI/DEV + BTC ×6; 7 legs, 8 calls
   with no new preflight assumption — stated for the record,
   NOT requested here).

— Muse
