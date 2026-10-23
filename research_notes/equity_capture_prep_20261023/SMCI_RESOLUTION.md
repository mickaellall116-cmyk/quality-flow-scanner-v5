# SMCI RESOLUTION OPTIONS — QF equity-capture prep, 2026-10-23

## PAPER ONLY — nothing executed, no recommendation made

SMCI is the one UX51 equity whose holdout leg cannot currently be
qualified. This note assembles, in one place: the defect facts
(§1), a **NOT-EXECUTED** bounded Alpaca sample card that is the
only evidenced route to new SMCI/HO evidence (§2), and the
disposition options already on record (§3), restated **without
recommendation** — the disposition is Mike's decision, informed by
ChatGPT/Claude adjudication.

---

## 1. Defect facts (Twelve Data SMCI/HO) — from -02 (`7823538`), verified record

- The pilot Step 1 SMCI/HO leg **aborted** the pilot at leg 9: the
  raw body carries **19 zero-volume bars with nonzero OHLC range**
  (price-moving zero-volume bars) across **6 April-2024 dates**.
  The body was quarantined byte-exact in qf-data-archive
  (`captures/td_pilot_20261023/`), sha256
  `737cb24ad6dcb6185529dd629177cd34f6f1f5988b0dda86fb45131c898f43d3`;
  **no receipt was fabricated, no retry was attempted.**
- Adjudication -02 ran the quarantined body through the identical
  calendar-bound checker: the generic pinned-session admission
  removed its one phantom row (2024-07-03 15:30), admitted count
  was **exact (1,583, 0 missing, 0 missing sessions)** — and the
  ANOMALY lane still failed on the same 19 bars, independently
  reproduced at the stamps ChatGPT enumerated:
  2024-04-08 ×4 (12:30, 13:30, 14:30, 15:30), 2024-04-09 ×1
  (10:30), 2024-04-10 ×6 (10:30–15:30), 2024-04-12 ×4 (09:30,
  10:30, 11:30, 13:30), 2024-04-15 ×2 (09:30, 15:30),
  2024-04-17 ×2 (11:30, 15:30).
- **Classification: `NOT_EVALUABLE_PROVIDER_VOLUME`** (TSLA C2
  precedent, -76): zero-volume bars WITH nonzero OHLC range are
  missing/zeroed provider volume, not no-trade bars. The defect
  survives the only legitimate generic repair (session admission),
  which is what makes the leg not evaluable rather than merely
  unfiltered. **No imputation, no retry, no alternate window, no
  silent symbol removal, no performance use.**
- SMCI/DEV was never attempted. Coverage consequence on record:
  4/44 equities full-span qualified (NVDA/TSLA/AAPL/SPY), SMCI/HO
  not evaluable, 39/44 unattempted (the manifest in this package),
  crypto 0/7. **The frozen UX51 × 751 baseline cannot be computed**
  while SMCI/HO stands not evaluable — a DEV-only leg cannot
  repair an HO hole.

## 2. NOT-EXECUTED sample card — Alpaca SMCI, April 2024

### ⛔ NOT EXECUTED — DOUBLE GATE, BOTH CURRENTLY CLOSED

- **Gate G0 (license):** the Alpaca screen in this package
  (`ALPACA_SCREEN.md`) returns **HOLD —
  LICENSE_NOT_AFFIRMATIVE**. This card may not run until a
  re-screen passes (cure: Alpaca's written consent covering
  internal immutable archival + personal algorithmic-research use,
  then re-screen).
- **Gate G1 (separate GO):** even with G0 passed, this card runs
  only on its own bounded sample GO (Mike, or a relayed GO inside
  an adjudicated task under the 2026-10-23 rule). **A GO for the
  39-name Twelve Data capture is NOT a GO for this card, and vice
  versa.**

| Field | Card |
|---|---|
| Purpose | Settle, on actual bytes from an independent source, whether the 19 TD-defect stamps are a Twelve Data provider-volume defect or a property of the underlying tape — and whether Alpaca SIP 1h bars land on the frozen XNYS session grid with volume intact. This is the smallest evidence step that can change SMCI/HO's disposition. |
| Symbol / window | **SMCI only**, April 2024: 2024-04-01 → 2024-04-30 ET (22 XNYS sessions; contains all 6 defect dates). One symbol, one month — nothing else. |
| Request form (documented, §2.3 of the screen) | Historical stock bars, `feed=sip`, timeframe `1Hour`, **`adjustment=split`** pinned explicitly (Alpaca default is `raw`), sort ASC. Bars are bar-open stamped (UTC ISO) per the documented contract. All data is years older than the 15-minute free-tier boundary. |
| Expected / ceiling | April 2024 1h bars ≈ 22 sessions × 7 = **154 bars → 1 page → 1 call expected**. **Hard ceiling: 4 calls** (≤2 attempts, ≤2 pages each). At the ceiling: STOP and report. Cost: $0 (Basic free tier, 200 calls/min). No Twelve Data credits involved. |
| Destination | qf-data-archive `captures/alpaca_smci_sample_<EXEC_DATE>/` (append-only, SHA256SUMS verified by re-fetch) + byte-identical local store; receipt hash-chained under a sample manifest root created at execution (same receipt discipline as the TD pilot). |
| Evaluation (offline, after capture) | (i) **Volume test:** the 19 defect stamps (dates/times in §1) — does Alpaca report nonzero volume there? Are OHLC ranges present and comparable to the quarantined TD body at the same stamps? (ii) **Grid test:** every returned bar-open instant against the pinned 751-session table (09:30/13:30/16:00 session geometry, early-close rule) — the frozen admission rule, unchanged. (iii) **Completeness:** April-2024 admitted count vs calendar expectation for the month. No strategy, no performance, no other symbol. |
| Decision rules (frozen in advance) | **Volume present at the 19 stamps AND grid/completeness pass** → SMCI/HO gains an *evidenced alternate-source route*: a full SMCI/HO Alpaca leg becomes a candidate requiring its own manifest amendment + adjudication (this card does NOT authorize it). **Same zero-volume class on Alpaca** → the defect is corroborated at the tape level on two independent sources; SMCI/HO stays NOT_EVALUABLE and the disposition defaults to the §3 options with materially stronger evidence. **Grid or completeness failure** → Alpaca equity bars fail the frozen qualification shape; the second-source route closes for SMCI (and the finding is reported for the whole equity program, not just SMCI). |
| Abort conditions | Any call beyond the ceiling; any response inconsistent with the documented contract (missing volume field, non-bar-open stamps); any receipt-chain break; account/credential prerequisite discovered at execution that was not in the screen (report, do not improvise around it). |
| What this card does NOT do | No other symbol (ChatGPT's lead also named AAPL regular/early-close samples — deliberately out of this card's scope; adjudication may add them as a separate card), no full SMCI/HO leg, no SMCI/DEV leg, no 39-name capture, no performance, no production change, no shadow launch, no paid subscription. |

## 3. Fallback options already on record (-02 Card B) — restated WITHOUT recommendation

- **B1 — Accept and proceed with disclosed 43/44 HO baseline.**
  Zero credits. Membership stays frozen; the SMCI/HO
  exclusion-by-classification is written into the baseline's own
  record; the C1 comparability break is disclosed. The decision is
  needed only when a baseline GO is drafted — it does not have to
  be taken now.
- **B2 — SMCI/DEV-only Twelve Data leg** (1 leg; -02 accounting:
  3 expected / 4 worst credits). Stated plainly in -02 and
  repeated here: **B2 does not cure the HO hole and has no
  qualification value until a B1/B3 disposition for HO exists** —
  it only pre-positions the DEV leg. (Recorded for completeness;
  it is why SMCI/DEV is held out of the 39-name manifest.)
- **B3 — Defer SMCI entirely** pending an SMCI/HO evidence route.
  Zero credits. The coverage record stands as the blocker. The
  §2 sample card is, as of this package, the only such route
  documented — and it is itself gated (G0 license + G1 GO).

**No option is recommended here.** The disposition belongs to
Mike, with ChatGPT adjudication and Claude replication in their
standing roles. What this package adds to the record is only: the
defect facts in one place, a frozen bounded card that can produce
decisive evidence, and the screen verdict that currently keeps
that card closed.

— Muse
