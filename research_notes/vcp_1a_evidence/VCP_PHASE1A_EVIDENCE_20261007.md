# VCP Phase 1A — Proof-of-Evidence Package (QF-VCP-1A-EVIDENCE-20261007-02)

**Date:** 2026-10-07/08 | **Task:** Issue #1 comment 6050055081
**Scope:** Evidence collection only. Zero vendor requests, zero performance reruns, zero sealed-validation access, zero parameter changes.

## 1. Published Artifacts

| File | SHA256 (full) | Source timestamp (UTC) |
|------|---------------|------------------------|
| `RUN_PLAN_FROZEN_20261001.md` | `367bddea6d5184d5831d08bcd5b66b05ce935f44895182a35a5891207c38a869` | 2026-10-01 04:42:18 |
| `analyze.py` | `80315ceff4fd7a962e7e9ad3cd1b96636271d71f6b61eee578527ebb84297fbb` | 2026-10-01 04:42:14 |
| `results_phase1a.json` | `c6b0f98a4a5baaba7d1ebd19a171c55bf8d918fd7832af4eb905bab5ba78a05d` | 2026-10-03 13:10:49 |

No sanitization needed — no secrets, credentials, or PII in any file.

## 2. Variant 2 Reconciliation (from the pre-result plan only)

**The apparent ambiguity:** The frozen SPEC (2026-09-30) says "Variant 2 = Variant 1 plus the frozen 12-month trend condition." The inventory summary said "price above 150/200/250DMA."

**Resolution — citing the frozen RUN PLAN (2026-10-01, before any result):**

> §4 Trend variants (frozen):
> - Variant 1: adjClose > 150DMA AND adjClose > 200DMA.
> - Variant 2: Variant 1 AND adjClose > 250DMA.
>   (250 trading days ≈ 12 months: operationalization of the source video's "price above 12-month moving average". **Documented as judgment call.**)

Both statements describe the SAME rule. The inventory's "price above 150/200/250DMA" is the plan's operationalization (V1 = >150DMA AND >200DMA; V2 = V1 AND >250DMA). The plan explicitly documents that "250 trading days ≈ 12 months" is the judgment-call operationalization of the spec's "12-month trend condition." No semantic reinterpretation occurred post-result; the analysis code implements exactly this rule (MA windows 150/185/230 minimum bars on adjClose, observation-date inclusive).

## 3. Complete Interim Table — Both Variants × All Horizons

Panel: 39,672 rows → 30,826 after $2B–$100B PIT mcap filter. Months 2010-01-29 to 2025-12-31.
Design: Fama–MacBeth d_m = mean(qual fwd ret) − mean(ctrl fwd ret), equal-weighted within month; block bootstrap (block 12, 9,999 resamples, seed 42, recentered p); 8 non-overlapping 2Y subperiods.
Persistence PASS needs: mean(d)>0 AND ≥5/8 subperiods AND bootstrap p<0.05.

### VARIANT 1 (adjClose > 150DMA AND > 200DMA)

| Horizon | n months used | Excess mean (m) | Excess ann. | 95% CI | p (2-sided) | Subpos /8 | Qual obs | Ctrl obs | Qual mean ret | Ctrl mean ret | vs SPY ann. |
|---------|---------------|-----------------|-------------|--------|-------------|-----------|----------|----------|---------------|---------------|-------------|
| 3M | 192/192 | −0.003557 | −4.27% | [−0.0097, +0.0012] | 0.2113 | **3/8** | 19,249 | 11,577 | +3.16% | +4.63% | −1.37% |
| 6M | 192/192 | −0.005406 | −6.49% | [−0.0174, +0.0042] | 0.3282 | **3/8** | 19,249 | 11,577 | +6.65% | +8.51% | −3.86% |
| 12M | 188/192 | −0.012434 | −14.92% | [−0.0384, +0.0109] | 0.3187 | **3/8** | 18,815 | 11,214 | +13.33% | +17.33% | −14.30% |

V1 subperiods (monthly excess, mean): 2010-11 +0.0006, 2012-13 −0.0088, 2014-15 +0.0003, 2016-17 −0.0051, 2018-19 +0.0022, 2020-21 −0.0060, 2022-23 −0.0070, 2024-25 −0.0016 (3M shown; 6M/12M patterns similar, 3/8 positive each).

### VARIANT 2 (V1 AND adjClose > 250DMA)

| Horizon | n months used | Excess mean (m) | Excess ann. | 95% CI | p (2-sided) | Subpos /8 | Qual obs | Ctrl obs | Qual mean ret | Ctrl mean ret | vs SPY ann. |
|---------|---------------|-----------------|-------------|--------|-------------|-----------|----------|----------|---------------|---------------|-------------|
| 3M | 192/192 | −0.003845 | −4.61% | [−0.0101, +0.0013] | 0.2030 | **3/8** | 18,786 | 12,040 | +3.12% | +4.63% | −1.75% |
| 6M | 192/192 | −0.006573 | −7.89% | [−0.0202, +0.0043] | 0.3030 | **3/8** | 18,786 | 12,040 | +6.59% | +8.53% | −4.45% |
| 12M | 188/192 | −0.014455 | −17.35% | [−0.0413, +0.0103] | 0.2745 | **3/8** | 18,368 | 11,661 | +13.24% | +17.33% | −15.31% |

V2 subperiods: 2010-11 +0.0005, 2012-13 −0.0045, 2014-15 +0.0007, 2016-17 −0.0071, 2018-19 +0.0034, 2020-21 −0.0117, 2022-23 −0.0099, 2024-25 −0.0014 (3M shown; 3/8 positive at each horizon).

### Persistence verdict (adverse evidence preserved, not softened)

**Both variants FAIL the frozen persistence rule at all three horizons.** Every cell fails on all three legs: negative full-sample mean, 3/8 subperiods (need ≥5), and p ≫ 0.05. The 12M annualized excess is deeply negative (−14.9% V1, −17.3% V2). Hit rates are near-identical between qualifiers and controls (3M: 61.7% vs 63.4% V1). Mean max adverse excursion is substantial (V1 12M: −13.5% mean, −9.9% median per qualifier stock-month). Breadth V1: mean 100 qualifiers/month (min 16, max 174); V2: mean 98 (min 15, max 168). Turnover ~0.167 for both.

**Missingness/exclusions:** 12M uses 188 months (Jan 2010–Sep 2025; Oct–Dec 2025 unobservable). Months with <5 qualifiers or <5 controls dropped per month (logged in analysis). Panel excludes ticker-months with no EDGAR shares coverage (pre-2010 XBRL gaps) and quarantined ticker-reuse intervals (545 quarantine.log rows). No sealed-validation data used.

## 4. Panel Artifact Manifest

| Artifact | SHA256 (first 16) | Rows/entries | Timestamp (UTC) |
|----------|-------------------|--------------|-----------------|
| month_ends.json | `f8a6038d94d7c326` | 192 | 2026-10-03 13:10:11 |
| universe.json | `1c651a624fa2aabb` | 3 (top-level keys) | 2026-10-01 04:09:24 |
| sp500_ticker_start_end.csv | `b2f4fe2f2e4dce8e` | 1,262 data rows | 2026-10-01 03:56:47 |
| panels/panel.jsonl | `553e9442145b1f5f` | 39,672 | 2026-10-03 13:10:38 |
| panels/quarantine.log | `5e6ebb8100f1226e` | 545 lines | 2026-10-03 13:10:38 |
| cik_validated.json | `c1976206cca754b9` | 24 tickers | 2026-10-03 11:40:26 |
| cik_dropped.json | `73836d7d7bbc6ba4` | 2 tickers (89 drop records) | 2026-10-03 11:40:26 |
| edgar_shares.json | `8b0cd327e095dc27` | 684 tickers | 2026-10-03 13:08:34 |

Raw licensed/vendor payloads (Tiingo EOD JSON, SEC companyconcept JSON) remain private and are not published.

## 5. Local-Only Readiness Results

### EDGAR-vs-Tiingo shares cross-check (local files only) — COMPLETE
Compared EDGAR `dei:EntityCommonStockSharesOutstanding` (point-in-time, quarter-end) against Tiingo `shareswa` (quarterly weighted average) for all locally available overlapping quarters:

| Ticker | Quarters matched | Mean abs diff | Max abs diff |
|--------|-----------------|---------------|--------------|
| AAPL | 12 | 0.30% | 0.91% |
| MSFT | 12 | 0.01% | 0.03% |
| WMT | 12 | 0.05% | 0.16% |

**Result:** EDGAR shares agree with Tiingo shareswa within <1% across all matched quarters. The small differences are consistent with the expected timing basis (quarter-end point vs quarterly weighted average). This validates the EDGAR shares source used for the PIT mcap filter. Limited to 3 tickers — Tiingo free-tier fundamentals cover DOW-30 only with 3 years of history, so universe-wide cross-check is not possible from local files.

### EFTS name validations — HOLD (no local-only path)
128 pending validations require Tiingo metadata API calls and/or SEC submissions API calls to resolve. `validate_efts.py` fetches both remotely. Zero vendor requests are permitted in this task, so no further validations were performed. Current state: 24 validated, 89 dropped (name mismatch), 128 pending/errors. **HOLD until a vendor-request window is authorized.**

## 6. Registry / Inventory Update

- Registry record `EXP-20261007-VCP-1A-EVIDENCE` added (state: HOLD pending ChatGPT adjudication of this evidence package).
- Exact code pins recorded (no "TBD"): run plan `367bddea…`, analyze.py `80315cef…`, results `c6b0f98a…`, all published in this commit.
- Actual effort: ~40 minutes (within 60-min budget).

## 7. Named Blockers / Remaining HOLDs

1. **EFTS validations** (128 pending) — need Tiingo metadata + SEC API access. HOLD.
2. **November 379-ticker batch** — deferred to ≥2026-11-01 (Tiingo 500-symbol/month cap). HOLD.
3. **EDGAR-vs-Tiingo shares cross-check** — universe-wide version blocked on Tiingo fundamentals coverage (DOW-30 only free tier). 3-ticker local check complete above.
4. **Phase 1B** — remains unpreregistered, cannot run.
5. **November full-universe run** — remains one preregistered run, pending evidence review + Nov 1 credit window.
6. **ChatGPT adversarial review** of this evidence package — pending.
