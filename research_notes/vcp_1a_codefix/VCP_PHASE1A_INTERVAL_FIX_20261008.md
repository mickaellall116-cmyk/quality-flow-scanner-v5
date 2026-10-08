# VCP Phase 1A Interval Fix — QF-VCP-1A-INTERVAL-FIX-20261008-06

**Date:** 2026-10-08
**Per:** ChatGPT adjudication, Issue #1 comment 6053282451
**Scope:** Code/tests/manifests only. Zero vendor requests, zero panel rebuild, zero real-data performance calculation, zero strategy changes, zero sealed access. Actual effort: ~40 minutes (within 45-min budget).

## 1. What changed

**Problem:** `build_panels.py` derived forward-window closed/open status from membership-end alone (`series_closed = (me != "2200-01-01")`). The interval audit (QF-VCP-1A-INTERVAL-AUDIT-20261008-05) proved this wrong: 101 ordinary index removals were quarantined, dropping 8,071 valid membership-months, because an S&P removal does not end a company's trading series.

**Fix:** Interval admission and forward-window closed/open status are now driven by the pinned disposition manifest `interval_disposition_manifest.json` (manifest ID `VCP-1A-INTERVAL-DISPOSITION-20261008`), reproduced deterministically from the audit's local evidence (quarantine.log + series dates + ticker_cik_history.json):

| Disposition | N intervals | Forward-window semantics |
|---|---|---|
| `continuing/open` | 73 | Ordinary index removal, single stable CIK. Forward windows extend PAST membership end using actual post-removal bars; censor only at the dataset boundary. |
| `verified_terminal/flat-hold` | 4 | Exact pinned acquisition exceptions (ABMD, BXLT, CTXS, HOT). Frozen RUN_PLAN §5 last-close flat-hold; counted COMPLETE. No general "±30d = acquisition" rule created. |
| `ambiguous/quarantine` | 54 | 28 no-CIK-evidence cases + 26 ticker-reuse/data-deficient cases. Interval excluded (fail closed). |

Intervals absent from the manifest keep the legacy `reuse_guard` path unchanged.

## 2. Code changes

**`build_panels.py`:**
- `load_disposition_manifest()` — loads the pinned manifest; **hard error if missing** (fail closed, never silently reverts to membership-end-as-delist).
- `admit_interval(t, ms, me, s0, s1, disp_manifest)` — new production admission function returning `(admit, disposition, log_line)`. Manifest dispositions override the guard; unlisted intervals use legacy `reuse_guard`.
- `main()` uses `admit_interval`; `series_closed` now derives from disposition: `verified_terminal` → True, `continuing/open` → False, legacy → prior rule.

**`analyze.py`:**
- `resolve_horizon_filter()` now asserts the cross-field invariant as a hard accepted-run preflight: for every row and horizon, `fwd_complete_<h> == (fwd_status_<h> in {'complete','delisted_flat'})`. Violation → RuntimeError (fail closed). This was previously only a separate optional script.

## 3. Tests (all call production functions, synthetic data only)

**New `test_vcp_phase1a_intervalfix.py`: 21/21 PASS**
- I1: ordinary removal — window extends past membership end via actual bars (`complete`); still `censored` at dataset boundary
- I2: verified terminal — `delisted_flat`, exact flat-hold return (last/obs − 1), counted COMPLETE
- I3: ambiguous identity → `admit_interval` returns admit=False, QUARANTINED
- I4: ticker reuse (series starts after interval end) → rejected via legacy guard
- I5: cross-field invariant — consistent rows pass; corrupted row (complete=True, status=censored) → hard RuntimeError
- I6: disposition → series_closed routing (continuing→False, terminal→True, ambiguous never routes)

**Existing suites unaffected:** `test_vcp_phase1a_codedelta.py` 31/31 PASS; `preflight_invariant_check.py` ALL PASS.

## 4. Classification counts (deterministic reproduction)

- 131 END_MISMATCH intervals: 73 continuing/open + 4 verified terminal + 54 ambiguous/quarantine
- The 4 verified terminals: ABMD (me 2022-12-22, series end 2023-01-03), BXLT (me 2016-06-03, end 2016-06-16), CTXS (me 2022-10-03, end 2022-11-02), HOT (me 2016-09-23, end 2016-10-03)
- The 28 no-CIK cases: point-in-time EFTS CIK mappings exist in `cik_resolved.json` but do not constitute deterministic historical identity evidence → remain AMBIGUOUS/HOLD per adjudication. Available for future deterministic resolution; not silently admitted.

## 5. Unresolved

1. The 28 no-CIK tickers (AABA, ACS, AKS, ANRZQ, ARNC, AVP, AYE, BHGE, BJS, BMS, CAM, CERN, CVH, DAY, DISCA, DISCK, DNR, EVHC, FII, GAS, GENZ, HNZ, HRS, HSH, JEC, JNS, JOY, KORS): remain quarantined with explicit missingness. Point-in-time CIK mappings recorded in manifest entries but not treated as identity proof.
2. CTXS +30d tail staleness (from audit §8): flat-hold should start at the true delisting date; unresolved.
3. Whether Class-B forward windows may extend past membership-end (same company) or must cap at `me`: adjudicated YES for the 73 stable-CIK cases (same-company post-removal bars are observed forward returns). The frozen estimand question is closed by the adjudication's semantics ruling.

## 6. Next eligible

Per adjudication: after review, the next real computation remains the **single full-universe November run**. Do not rerun the partial October performance. November execution, Phase 1B, and Claude checkpoint remain HOLD pending ChatGPT's review of this fix.
