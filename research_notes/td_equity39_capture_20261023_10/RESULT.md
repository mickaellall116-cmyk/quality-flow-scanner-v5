# QF-TD-EQUITY39-CAPTURE-20261023-10 — RESULT

**STOPPED AT LEG 1 ON A DOCUMENTED ABORT — honest partial coverage: 0 of 78 legs captured, 0 receipts, 1 leg attempted and quarantined, 77 legs unattempted. No name is qualified; no name carries the `CAPTURED_G1_G6_CANDIDATE_G4_UNADOPTED` label, because no leg was accepted.**

Re: Issue #1 comment 6374269350 (ChatGPT capture GO; Slack GO TS 1792787921.216909, ACK TS 1792788402.297069, bridge ACK `5ee92bf`). Single-dispatch check was CLEAR before any file operation (no -10 stage dir, no `td_capture_equity39_*` archive namespace, no pre-execution commits for this task ID on origin/main).

## Manifest verification (before the first call)

Root digest recomputed from the committed `a3ec37e` bytes (canonical sorted/compact JSON, `root_digest_sha256` + `root_digest_construction` omitted): **`ca49892062f1ac5d4ec6d20eaadd37b519aec84ad0b23a995fb11db74dccfd64` — MATCH.** 78 unique legs, 39 unique names, 0 SMCI legs, every leg `NOT_ACQUIRED` at GO time.

## Preflight — PASS

One `/api_usage` read (never retried), daily fields read explicitly: `daily_usage = 17`, **`plan_daily_limit = 800`** (the per-minute `plan_limit = 8` was NOT read as the daily limit — the -69 check). Headroom 783 ≥ 173 worst-case arithmetic. Provider body archived (`preflight/api_usage.body.json`, sha256 `4092c68f…`).

## The stop — PLTR/HO, price-moving zero-volume anomaly (SMCI rule)

Leg 1 of 78, **PLTR/HO** (2023-10-19..2024-09-15), attempt 1, HTTP 200, 1,583 raw rows, 227 dates, all standard per-date bar counts, schema/finite/duplicate/continuity validations passed — but the raw bytes carry **3 price-moving zero-volume bars** (volume = 0 with nonzero OHLC range), the TSLA-C2 / SMCI failure class, at ordinary in-session stamps that the generic G-2 admission rule would NOT exclude:

| Bar-open (ET) | O | H | L | C | Volume |
|---|---|---|---|---|---|
| 2024-04-09 10:30 | 22.69 | 22.72 | 22.47 | 22.64 | 0 |
| 2024-04-10 09:30 | 22.09 | 22.68 | 22.06 | 22.64 | 0 |
| 2024-04-10 10:30 | 22.65 | 22.71 | 22.42 | 22.56 | 0 |

Per the frozen manifest abort conditions ("any price-moving zero-volume anomaly class on raw bytes = quarantine leg + adjudication, capture continues only if the wrapper's fail-closed rules permit — default STOP and report") and the GO ("on first required stop, report partial leg coverage and blocker rather than continuing with modified rules"), the leg was quarantined byte-exact and the capture STOPPED. No retry on the anomaly, no receipt fabricated, no imputation. The same April-2024 window as the SMCI cluster (SMCI: Apr 8/9/10/12/15/17) — a provider-volume failure pattern in that period, now observed on a second symbol; classification of PLTR/HO follows the -02 precedent: **NOT_EVALUABLE_PROVIDER_VOLUME** (capture-stage finding, G-5 class).

Quarantined body: 199,669 bytes, sha256 **`bad09adc737acc3bde90a369965345fcca1ba9840ea169eba89f3e2b7f6521ec`**, archived at qf-data-archive `captures/td_capture_equity39_20261023/quarantine/PLTR__HO.json` with `QUARANTINE.md`.

## Accounting (BLOCK-BRACKET-10) — reconciled

| Item | Count |
|---|---|
| API calls made by this run | 3 (R0 preflight read + 1 leg attempt + R1 block-close read) |
| Blocks closed | 1 (block 1: 1 attempt; `u 17 → 19`, Δ2 = 1 attempt + 1 closing read — reconciled exactly) |
| Legs attempted | 1 / 78 |
| Legs accepted / receipts issued | 0 / 0 |
| Provider daily counter | 17 (R0) → 19 (R1 close) |
| Program TD total (desk call-count convention) | 24 → 27 |
| Cost | $0 (free tier) |

Expected/worst-case arithmetic for the full manifest (87 / 173) was preflight-verified for headroom only; the run consumed 3.

## Per-name qualification outcome (gates G-1..G-6, G-7 carried)

- **PLTR — STOPPED AT CAPTURE (G-5 class).** HO quarantined `NOT_EVALUABLE_PROVIDER_VOLUME`; DEV unattempted. No gates passed; not labeled captured.
- **The other 38 names (SOFI, AMD, MSFT, META, COIN, MSTR, AVGO, GOOGL, AMZN, NFLX, CRM, MU, INTC, LRCX, AMAT, QCOM, ARM, HOOD, APP, NET, SNOW, DDOG, CRWD, SHOP, RKLB, ASTS, LUNR, PYPL, NU, MELI, IWM, SMH, ARKK, XLF, NIO, MRNA, PFE, F) — NOT ATTEMPTED.** Both legs of each remain `NOT_ACQUIRED`. The capture halted at the first required stop by rule; no per-name inference is drawn from PLTR's failure about any other name's bytes, which were never requested.
- **Names labeled `CAPTURED_G1_G6_CANDIDATE_G4_UNADOPTED`: none.** G-7/VBASIS was not reached for any name (no accepted bytes) and remains disclosed-not-waived for the route.

## Archive

qf-data-archive commit **`db1b43d`** (ancestor of the archive remote `main`), namespace `captures/td_capture_equity39_20261023/`: manifest, preflight bodies, both bracket-read bodies, quarantine (body + note), receipts/chain_index.json (zero receipts, documented), run evidence (run_summary.json, attempts.jsonl, refusals.jsonl, brackets.jsonl), SHA256SUMS — **re-fetch verified 13/13 byte-equal from a fresh clone of the pushed tree.**

## Bounds held

SMCI untouched (not in the manifest). No Alpaca, no crypto, no spending, no new vendor, no credential change. HO bytes were captured as raw qualification input only — the single attempted HO leg was validated for schema/volume classes only; no signals, no backtest, no holdout readout, and the sealed evaluation is untouched. No production/frozen changes. **PAUSED pins identical before/after:** harness `ce7c902ce182683ca1723468a0109747abd80db287c39556ea4db78210a0833d`, PAUSE_NEW_ENTRIES present, RESUME absent. Explicitly: **no qualified edge, no performance run.**

## What unblocks

The frozen rules leave the continuation to adjudication: PLTR/HO's disposition (accept the G-5 finding per the -02 precedent and treat the leg under a governed exception, or a second-source sample) and whether the remaining 77 legs proceed under a new GO that names this stop. Nothing here was continued under modified rules.

— Muse
