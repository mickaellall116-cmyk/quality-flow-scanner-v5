# TWELVE DATA BTC STAMP-PHASE PILOT (Card A) — RESULT — 2026-10-23

Task `QF-TD-BTC-PHASE-PILOT-20261023-03`.

**States:** SENT (Issue #1 comment 6369065652) → ACK (Slack TS
1792772773.969219; bridge commit e091e89) → this RESULT. Independent
PASS/HOLD is ChatGPT's/Claude's step, not claimed here.

**Authorization:** Mike's direct GO in the main chat, 2026-10-23
12:21 ET ("Go dont wait for me anymore"), for Card A ONLY as pinned
in `research_notes/td_pilot_adjudication_20261023_02/CONTINUATION_CARD.md`
(commit 7823538), under the readiness manifest (edc44d9, root digest
`79ccdd128e0b36537f56f8ae36a731b719e989b9756f65856b7dc47344327122`).

## Outcome in one line

**HOLD — BTC stamp phase NOT CONFIRMED.** The run stopped at the
first chunk: the provider rejected the pinned symbol form
`BTC-USD` with HTTP 404 (invalid symbol). Zero chunks captured,
zero receipts emitted, remaining five chunks never attempted.
No retry, repair, or symbol substitution was made inside this GO.

## Credits (exact)

- Preflight `/api_usage` opening read: 2026-10-23T16:28:31Z,
  HTTP 200. Daily fields read per the -69 repair:
  `daily_usage=11`, `plan_daily_limit=800` → PASS (`plan_limit=8`
  is the per-minute limit and was not used). Remaining quota
  789 ≥ 15 cap.
- 1 data attempt (`BTC-USD/HO-C1`), HTTP 404,
  `api-credits-request: 1` per provider header.
- Closing `/api_usage` read: `daily_usage=13`,
  `plan_daily_limit=800`.
- **Incremental spend (BLOCK-BRACKET-10 model): 3 credits**
  (1 attempt + 2 reads) of the 15 hard max. **Program Twelve Data
  total: 18 → 21 credits.** $0, free tier, no upgrade. Provider
  daily counter moved 11 → 13 across the run window.

## Chunks

All chunks: `/time_series`, BTC-USD, interval 1h, `adjust=splits`,
`outputsize=5000`, `order=ASC`, timezone America/New_York,
start `T00:00:00` / end `T23:59:59` ET (the pinned form).

| Chunk | Window (ET dates) | Expected rows | Status |
|---|---|---|---|
| BTC-USD/HO-C1 | 2023-10-19 → 2024-05-13 | 4,992 | **REFUSED — HTTP 404 invalid symbol** |
| BTC-USD/HO-C2 | 2024-05-14 → 2024-09-15 | 3,000 | NOT ATTEMPTED (run stopped) |
| BTC-USD/DEV-C1 | 2024-09-16 → 2025-04-11 | 4,992 | NOT ATTEMPTED (run stopped) |
| BTC-USD/DEV-C2 | 2025-04-12 → 2025-11-05 | 4,993 | NOT ATTEMPTED (run stopped) |
| BTC-USD/DEV-C3 | 2025-11-06 → 2026-06-01 | 4,991 | NOT ATTEMPTED (run stopped) |
| BTC-USD/DEV-C4 | 2026-06-02 → 2026-10-16 | 3,288 | NOT ATTEMPTED (run stopped) |

Provider refusal body (202 bytes, sha256
`80cd61f4c6b2ad7484d5313f8a35bbc0ee32251fb030981338c54ef770a55fb7`):
`{"code":404,"message":"**symbol** or **figi** parameter is missing
or invalid. Please provide a valid symbol according to API
documentation: https://twelvedata.com/docs#reference-data","status":"error"}`.

## Stamp-phase verdict

**HOLD.** No BTC bytes were returned, so no stamp could be validated
against the S-C1…S-C6 grid (continuous [D 09:30 ET, D+1 09:30 ET)
sessions on UTC instants; 23/24/25-bar DST sessions). Pilot gate
criterion (iv) remains UNDETERMINED, exactly as before this run.
Root cause is a request-form defect, not a data defect: the pinned
form carries the UX51 universe name `BTC-USD`; Twelve Data's
documented crypto symbol form is the slash pair (`BTC/USD`). The
equity pilot never attempted a crypto leg, so the defect was latent.
Changing the symbol form amends the pinned request form/manifest
lineage and needs its own authorization; it was not done here, and
no vendor call was spent probing alternatives.

## Evidence & storage

- Private archive `qf-data-archive`, namespace
  `captures/td_pilot_btc_20261023/` (append-only): manifest pin,
  preflight record, run evidence (`attempts.jsonl`,
  `refusals.jsonl`, `run_summary.json`), `HOLD.md`, SHA256SUMS —
  verified by fresh re-fetch (see RESULT posts for the archive
  commit). Local store byte-identical:
  `~/workspace/qf_td_btc_pilot_20261023/store`.
- This public package carries the result + run evidence logs only.
  No raw vendor bars exist for this task — none were returned.

## Bounds kept

BTC-USD only; no equity/SMCI/other-crypto legs; no full Step-2
capture; no performance or holdout analysis; no production or
frozen-strategy change — PAUSED production pins re-verified
identical before/after (harness `ce7c902c…`, scanner_rules
`62aa743a…`, masterscanner_api `c3e95b25…`, v54_engine
`bde32883…`, v54_rules `1b55dedc…`; PAUSE_NEW_ENTRIES present, no
RESUME); no shadow launch; no purchase/upgrade. Single-dispatch
check was clean before staging (no stage dir, worktree,
pre-execution commit, or archive namespace for this task).
Capture window elapsed 18 s (16:28:31Z → 16:28:49Z).

## What this leaves open (for a future GO, not executed)

1. Amend the pinned crypto request form to the provider's
   documented slash symbol (`BTC/USD`), re-pin the manifest
   lineage, and re-run Card A under a new authorization
   (expected 8 / worst 15 incremental credits, unchanged math).
2. Until then: BTC stamp phase unconfirmed; crypto branch of any
   full capture unqualified; SMCI disposition (Card B) untouched
   and still separate.

— Muse
