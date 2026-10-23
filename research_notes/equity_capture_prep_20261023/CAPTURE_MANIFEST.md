# CAPTURE MANIFEST — EQUITY-ONLY, 39 UNATTEMPTED UX51 NAMES (Twelve Data, 1h)

## PREPARED ONLY — AUTHORIZES NOTHING · Task: QF equity-capture prep, 2026-10-23

**Status.** Prepared specification for ChatGPT adjudication and the
capture GO. It authorizes no vendor call, no spend, and no capture.
The capture fires only under the sequencing in `SEQUENCING.md`
(-09 adjudication clear → capture GO naming this manifest's root
digest). Machine-readable form: `capture_manifest_equity39.json`,
**root digest
`ca49892062f1ac5d4ec6d20eaadd37b519aec84ad0b23a995fb11db74dccfd64`**
(sha256 of the canonical serialization with the root fields omitted;
construction stated in the JSON).

**Authority chain.** Mike's equities-first direction (2026-10-23,
via task -08 and confirmed in chat); his parallel-prep instruction
(chat, 2026-10-23 ~16:26 ET); universe freeze Option A (`2705c02`);
three-gate freeze (`a126ce5`: calendar adopted, E3 Mode A, S2
rejected); lineage -88 manifest (`6b0f5d0`) → -91 BLOCK-BRACKET-10
accounting (`db9e0f3`) → -93 receipt-schema amendment (`96cd2bb`) →
-01 candidate re-issue (`edc44d9`, root `79ccdd12…`) → pilot Step 1
execution (`5d129fb`) and actual-byte adjudication -02 (`7823538`) →
-08 DEV exploratory preflight gates (`ca6edc6`).

**Credits are not a decision here.** Per Mike's ruling (chat,
2026-10-23 16:04 ET), Twelve Data credits are free on his plan and
credit counts/ceilings are not blockers or Mike-desk decisions on
the equity route. The totals in §3 are execution bookkeeping (the
BLOCK-BRACKET-10 reconciliation arithmetic the capture halts on),
sized to the work within the 800/day free tier. No ceiling is
presented for approval.

**DISCLOSED ASSUMPTION CH-1 (carried, per the freeze).** The adopted
751-session calendar rests on the NYSE Group/ICE release of
2022-12-21 for the 2023 window; in-era documentary proof of
09:30–16:00 core hours for 2023 does not exist in the record. CH-1
is carried in this manifest header, in every capture receipt header
for 2023-window legs, and in every downstream readout spanning 2023.

---

## 1. Membership (pinned)

- **Universe:** UX51, canonical membership sha256
  `b5d8877ee7d6ddd105904d7f4ca35901ebb611dac7afeab2f7676529c112e6a2`
  (Option A freeze).
- **Already captured full-span in pilot Step 1** (receipted,
  completeness-QUALIFIED on admitted bytes per -02): NVDA, TSLA,
  AAPL, SPY — **not** in this manifest.
- **The 39 names in this manifest** (UX51 source order):
  PLTR, SOFI, AMD, MSFT, META, COIN, MSTR, AVGO, GOOGL, AMZN, NFLX,
  CRM, MU, INTC, LRCX, AMAT, QCOM, ARM, HOOD, APP, NET, SNOW, DDOG,
  CRWD, SHOP, RKLB, ASTS, LUNR, PYPL, NU, MELI, IWM, SMH, ARKK, XLF,
  NIO, MRNA, PFE, F.
- **SMCI — separately-flagged line, NOT a leg of this manifest.**
  SMCI/HO was attempted in the pilot and is classified
  `NOT_EVALUABLE_PROVIDER_VOLUME` (-02); the body is quarantined
  (qf-data-archive, sha256
  `737cb24ad6dcb6185529dd629177cd34f6f1f5988b0dda86fb45131c898f43d3`).
  A Twelve Data re-ask of that leg is a retry of a documented
  provider-volume failure and **is not offered**. SMCI/DEV (1 leg)
  is unattempted and is held OUT of this manifest pending an
  SMCI/HO disposition: a DEV-only leg does not cure the HO hole and
  has no qualification value until a disposition exists (-02 Card
  B2 logic). Resolution path: `SMCI_RESOLUTION.md`.
- **Crypto (7 pairs): out of scope** — parked per Mike's
  equities-first sequencing (2026-10-23). UX51 itself is unchanged.
- **Status of every name in this manifest: NOT ACQUIRED /
  NOT QUALIFIED.** No name is called qualified anywhere in this
  package; qualification is per-name, after capture, at gates §4.

## 2. Windows, basis, calendar (pinned)

- **Calendar (adopted):** 751-session XNYS union — -81 extension
  227 sessions 2023-10-19→2024-09-15 + XNYS_SESSION_SCHEDULE_V2
  524 sessions 2024-09-16→2026-10-16 (744 regular + 7 early-close).
  Pinned session table:
  `research_notes/shadow_closeout_20261022/session_table.json`,
  sha256 `00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f`,
  version `XNYS-751-UNION-20261021`.
- **W-HO:** sessions 2023-10-19 → 2024-09-15. Capturing these bytes
  does NOT open the sealed holdout: bytes are qualification input
  only; the holdout's single governed use remains -25 §50,
  separately gated, LAST in the sequence (`SEQUENCING.md`).
- **W-DEV:** sessions 2024-09-16 → 2026-10-16. Dev-end rule: the
  window ends at the last session of the adopted calendar; no
  session after 2026-10-16 is captured under this manifest.
- **Basis:** single uniform split-adjusted basis (`adjust=splits`,
  vendor default per -63 F1). E3 frozen at Mode A; S2 rejected.

## 3. Request enumeration and accounting (BLOCK-BRACKET-10)

All legs: `interval=1h`, `adjust=splits`, `outputsize=5000`, order
ASC, bar datetimes at bar open, timezone America/New_York (-63 F4).
A response at exactly 5000 rows is a truncation suspect and aborts
the leg — no leg here can legitimately return 5000 rows (raw-row
expectation ≈ admitted expectation + at most the phantom-row class
observed in the pilot: HO 1,583 admitted, DEV 3,653 admitted).

| Leg (×39 names) | Bounds (ET dates) | Expected admitted rows |
|---|---|---|
| `<SYM>/HO` | 2023-10-19 → 2024-09-15 | 1,583 |
| `<SYM>/DEV` | 2024-09-16 → 2026-10-16 | 3,653 |

**78 data legs.** Accounting per repair -91 (unit cost 1 credit per
API call; strictly sequential attempts in manifest order in blocks
of ≤10 attempts; one `/api_usage` read opens the phase and one
closes every block, chained; block reconciliation
`u_k − u_{k−1} = attempts_k + 1`, any mismatch HALTS; ≤2 attempts
per leg; a leg exhausting its bracket STOPS the capture):

| Case | Attempts | Blocks | Usage reads | **Total credits** |
|---|---|---|---|---|
| Expected | 78 | 8 | 9 | **87** |
| Worst | 156 | 16 | 17 | **173** |

Free tier 800/day, $0: the manifest fits **one execution day** at
expected and at worst case. Program TD total before this capture:
24; after, at expected: 111 (bookkeeping only — see the credits
note in the header).

**Abort conditions (any one stops the run; partial bytes are
quarantined UNQUALIFIED, never silently completed):** preflight
`/api_usage` fields read explicitly as `daily_usage` /
`plan_daily_limit` (the -69 misread check; `plan_daily_limit` ≠ 800
= stop); any 5000-row response; any leg exhausting its 2-attempt
bracket; any receipt-chain break; any block-reconciliation
mismatch; any price-moving zero-volume anomaly class on raw bytes
(the SMCI rule, generalized) = leg quarantined and adjudicated —
never imputed, never silently dropped.

## 4. Qualification preflight gates (copied from -08 / -02 — applied per name after capture)

A name's bytes pass ALL gates, in order, or the name stays
UNQUALIFIED with the failing gate named. No gate may be waived by a
later gate's result.

- **G-1 Receipt integrity.** Hash chain over every capture receipt
  verified against this manifest's root digest; `SHA256SUMS`
  verified by re-fetching the qf-data-archive copies byte-for-byte.
  Any mismatch = HOLD, bytes quarantined.
- **G-2 Calendar-bound admission.** Admission = the generic -02
  rule ONLY: a bar is admitted iff its bar-open instant is an
  expected start of its session under the pinned 751-session table
  (calendar only — no symbol lists, no date lists, no shape tests).
- **G-3 Completeness exactness.** Admitted counts equal the
  calendar expectation exactly (HO 1,583 / DEV 3,653); admitted
  stamp sets equal the pinned-table expected sets (no missing bars,
  no missing sessions, no duplicates, strictly increasing).
  Zero-row session = `COMPLETENESS_FAIL`.
- **G-4 Phantom-row exclusion.** Rows outside the pinned sessions
  are excluded by the G-2 rule alone and enumerated in the receipt
  (observed class: a 15:30 bar-open on 13:00 early-close dates —
  2024-11-29, 2024-12-24 in DEV; 2024-07-03 in HO). No other
  exclusion mechanism is permitted.
- **G-5 Volume completeness.** Any **price-moving zero-volume bar**
  (volume = 0 with nonzero OHLC range) on admitted bytes =
  `NOT_EVALUABLE_PROVIDER_VOLUME` for that leg — the **TSLA-C2
  failure class** (-76 precedent) and the **SMCI failure class**
  (-02: 19 bars, 6 April-2024 dates). Flat zero-volume bars are
  `NO_TRADE_FLAT` count-flags, not failures. No imputation, ever.
- **G-6 Schema / instant hygiene.** All OHLCV finite and positive;
  duplicate UTC instant within a leg = fail-closed refusal (UTC
  instant comparison, never wall-clock — the -94 lesson); intra-leg
  continuity checked on UTC instants; gaps are coverage findings,
  never papered over.
- **G-7 VBASIS disclosure.** The checker candidate-2 VBASIS lane
  has printed `CONVENTION_BREAK_SUSPECT` from VBASIS alone on every
  Twelve Data leg examined to date (pilot + -08), with price-side
  STEP PASS / STEP-ALL 0 on the same bytes. The disclosure is
  carried into every per-name report, **not waived**; whether
  VBASIS at this calibration belongs in the adopted instrument is
  the G4-adoption question for adjudication (checker unadopted).

## 5. Receipt schema (identical to the pilot's)

Schema `QF-CAPTURE-RECEIPT-CANDIDATE-20261023-01` (-01
`receipt_schema.json`, extending the -93 kind-discriminated
amendment): `capture_receipt` emitted ONLY after a leg payload
passes every wrapper validation, hash-chained (`prev_receipt_hash`
→ `receipt_hash`; first receipt's prev = `GENESIS` bound to this
manifest's root digest). Refused legs emit **no** receipt — absence
is the failure signal, never a fabricated placeholder; refusals are
local `capture_refusal` log lines (NETWORK_DISABLED |
SCHEMA_VIOLATION | TIMEZONE_VIOLATION | DUPLICATE_INSTANT |
GAP_VIOLATION | TRUNCATION_SUSPECT | NONFINITE_VALUE) and never
enter the chain or the archive. Per -91, receipts carry `block_id`,
`block_position`, and the sha256 of their block's two bracket
reads; they do NOT carry per-leg `usage_before` / `usage_after` /
`credit_delta` fields (per-leg deltas are not claimed).

## 6. Destination

qf-data-archive (private), `captures/td_capture_equity39_<EXEC_DATE>/`
— append-only, write-once, `SHA256SUMS` verified by re-fetch;
byte-identical local store under `~/workspace`; deletion only on
Mike's approval.

— Muse
