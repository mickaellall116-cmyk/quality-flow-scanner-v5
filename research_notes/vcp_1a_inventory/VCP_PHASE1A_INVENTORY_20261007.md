# VCP Phase 1A — Inventory & Status (QF-VCP-1A-INVENTORY-20261007-01)

Research-only inventory per ChatGPT adjudication (Issue #1 comment 6049455862).
**No reruns, no new computation, no vendor requests performed for this inventory.**
Inventory compiled 2026-10-07 ~20:30 EDT from on-disk evidence.

## Verdict summary

Phase 1A is **PARKED pending the November 379-ticker batch** (Tiingo free-tier
500-symbol/month cap; earliest start 2026-11-01 00:00 UTC). The interim
`results_phase1a.json` (Oct batch, 444/831 tickers ≈ 54% of universe) shows
**both setup variants below the persistence bar** — adverse evidence, preserved
per the standing adverse-evidence rule, NOT a lane verdict. The WORK RESULT is
one full-universe run away.

## 1. Frozen hypothesis / rules — PRESENT

| Artifact | Path | Hash / pin |
|---|---|---|
| Frozen spec | `goals/vcp-fundamental-momentum-probe-v0-1/hidden_files/vcp_probe_v01_SPEC_FREEZE_20260930.md` | sha256 `c8f103c58a38ab09d80da631572df6b6bd191f9ec6940a85aa5db9a83d08a2bc` (matches `.sha256` sidecar) |
| Frozen run plan | `.../hidden_files/phase1a/RUN_PLAN_FROZEN_20261001.md` | sha256 `367bddea6d5184d5…` (operationalization only, no spec change) |
| Spec copy in repo | `quality-flow-scanner-v5/research_notes/vcp_probe_v01_SPEC_FREEZE_20260930.md` | present |

## 2. Monthly-window design (Jan 2010 – Dec 2025) — PRESENT

| Artifact | Detail |
|---|---|
| `month_ends.json` | 192 months, 2010-01-29 → 2025-12-31, regenerated from Oct-batch SPY, verified identical on rebuild |
| Universe | `sp500_ticker_start_end.csv` (sha256 `b2f4fe2f2e4dce8e…`, 1,263 rows incl. header), 831 unique tickers; `universe.json` membership intervals; PIT inclusion rule = interval covers month-end |
| Trend variants | V1: adjClose > 150DMA & 200DMA; V2: V1 + 250DMA; min-bars 140/185/230 |
| Forward windows | 63/126/252 trading days on adjClose; complete-windows only (12M uses Jan 2010–Sep 2025) |
| Inference | Fama–MacBeth d_m; block bootstrap 9,999 resamples, block 12, seed 42, p recentered at 0 (bug fixed 2026-10-01) |
| Persistence gate | ≥5/8 non-overlapping 2Y subperiods positive AND full-sample mean>0 AND bootstrap p<0.05, per horizon |

## 3. October pull (data) — PRESENT, PARTIAL UNIVERSE

| Artifact | Detail |
|---|---|
| EOD pulls | `hidden_files/phase1a/raw/eod/` — **444 tickers** (Oct batch 445; ABC/ANTM/ADS etc. no-data); `pull_oct.log` ends `PULL COMPLETE` |
| Pilot | 12 tickers pulled 2026-10-01 (AAPL MSFT ATVI GE F BAC T KMI WMT DIS INTC IBM) |
| Ledger | `phase1a/ledger.json` — resume-safe, 3 keys; 90s→150s pacing after 2026-10-01 429 hard-stop (recovered same day) |
| November batch | `batch_nov.txt` — **379 tickers, NOT started**; deferred to ≥2026-11-01 00:00 UTC (Oct cap ~453/500 used). **MISSING/HOLD** |
| Code | `pull.py`, `universe.py`, `build_panels.py`, `analyze.py`, `make_calendar.py` under `hidden_files/phase1a/` |

## 4. EFTS name-validation outputs — PRESENT, PARTIAL

| Artifact | Detail |
|---|---|
| `cik_validated.json` | **24 validated** CIKs (Tiingo metadata name vs SEC name, fuzzy match) |
| `cik_dropped.json` | **2 dropped** (wrong-company data confirmed; includes 128 cosmetic-dupe error rows noted 2026-10-06) |
| Remainder | ~61 of ~87 attempted EFTS tickers **PENDING validation — MISSING/HOLD**; unvalidated EFTS CIKs excluded from mcap filter (logged, conservative) |
| Supporting | `efts_validation.log`, `cik_resolved.json`, `cik_validation.log`, `sec_ticker_map.json`, `resolve_cik.py`, `edgar_unmapped.txt` |

## 5. EDGAR shares (PIT market-cap source) — PRESENT

| Artifact | Detail |
|---|---|
| `edgar_shares.json` | 684 tickers with quarterly shares series (92.0% membership-month coverage); concept-fallback chain + 20x median unit-error cleaner; 220 bad frames dropped (`edgar_dropped_frames.log`) |
| Raw | `raw/edgar/` — 685 JSON files |
| Validation | Cross-check vs Tiingo shareswa for AAPL/MSFT (3yr overlap) — **MISSING/HOLD** (open pilot item) |
| Pre-2010 gaps | Ticker-months without EDGAR shares excluded + logged (documented limitation) |

## 6. Tiingo fundamentals — ABANDONED BY DESIGN

`raw/fund/` — 3 files (AAPL, MSFT, WMT) only. Tiingo free-tier fundamentals are
DOW-30 + 3yr only (pilot proof 2026-10-01); source switched to SEC EDGAR XBRL
for shares. No further fund pulls planned.

## 7. Panel / analysis status — PRESENT, INTERIM

| Artifact | Detail |
|---|---|
| `panels/panel.jsonl` | **39,672 rows** (built 2026-10-03 from Oct-batch data) |
| `panels/quarantine.log` | 545 quarantine entries (ticker-reuse END_MISMATCH guard, wrong-company exclusion) |
| `results_phase1a.json` | Interim: 192 months, v1 r3 mean_m −0.003557 (ann −4.27%), p 0.211; r6 mean_ann −6.49%, p 0.328; **3/8 positive subperiods** (need ≥5) → **below persistence bar**. Qualifiers 19,249 obs vs 11,577 control obs. |
| `_smoke/results.json` | 17-ticker pipeline smoke test (2,307 rows) — ran clean 2026-10-01 |
| Brief | `briefs/Phase 1A Interim Read (2026-10-04 04.27.22).html` — Letter sent 2026-10-04 (goal_briefing_4f4adf4adae8) |
| Adversarial review | **MISSING/HOLD** — Phase 1A result goes to ChatGPT before any 1B |

## 8. Failed / incomplete attempts (preserved, not overwritten)

1. **2026-10-01 Tiingo 429 hard-stop** — pull.py hit 3 consecutive 429s, HARD-STOPPED per policy (exit 42) at 9/445; window reset confirmed 06:33 UTC; resumed at --pace 150; completed same day.
2. **EFTS CIK resolution ~60% wrong** — never used unvalidated; validation via Tiingo metadata names; 2 correct DROPs so far.
3. **SEC companyconcept API incomplete** — companyfacts backfill required (ABT: 0 facts via concept API, 68 via companyfacts).
4. **Main-agent "parallel panel work" 2026-10-05** — announced in chat, never executed (no job ran per shepherd checks). Recorded as intent, not finding.
5. **Interim below-bar read** — adverse evidence preserved; no parameter tuning performed.

## 9. Explicit MISSING / HOLD list

- November 379-ticker EOD batch — deferred to ≥2026-11-01 00:00 UTC
- ~61 EFTS ticker validations — pending
- EDGAR-vs-Tiingo shares cross-check — open validation item
- ChatGPT adversarial review of Phase 1A — pending full-universe result
- VCP mechanical definition for 1B — not preregistered (blocked until 1A WORK RESULT reviewed)

## Constraints honored

No sealed validation access. No performance promotion. No acquisition. No
frozen-system changes. Evidence collection only. Zero Tiingo spend since
2026-10-01. V5.4/forward-test quarantine intact (all artifacts under the goal's
`hidden_files/`).
