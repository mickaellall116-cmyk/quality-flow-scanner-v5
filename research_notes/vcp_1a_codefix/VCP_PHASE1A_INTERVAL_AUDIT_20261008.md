# VCP Phase 1A Interval Audit — QF-VCP-1A-INTERVAL-AUDIT-20261008-05

**Date:** 2026-10-08
**Per:** ChatGPT adjudication, Issue #1 comment 6052011174
**Scope:** Local/read-only evidence only. Zero vendor requests, zero real-data performance calculations, zero strategy/parameter changes, zero sealed access. Correction proposal ONLY — no production code changes in this task.

## 1. Question

The frozen `reuse_guard` (build_panels.py) requires a closed S&P-membership interval's EOD series to end within ±9 **calendar** days of the membership end, else `END_MISMATCH` → quarantine. ChatGPT's hypothesis: an ordinary index removal keeps trading, so the guard may quarantine valid historical constituents and their forward returns. The evidence cited 545 quarantine-log rows.

## 2. Pinned inputs (exact hashes of files as read)

| File | SHA256 |
|---|---|
| `panels/quarantine.log` | `5e6ebb8100f1226e3351a66add63d71a8739286168f3135e4e264edc5df240b7` |
| `sp500_ticker_start_end.csv` | `b2f4fe2f2e4dce8eaf0eb4fbd3946a32a20c1ddfe69687dfca3b6b59a0b71f9f` |
| `universe.json` | `1c651a624fa2aabbe9433e8d898be12ff4083cd0974341d5f6c6109d1665d254` |
| `pull_oct.log` | `88920ea521e77456bbfb1466c0f00a388d0bb583bed2e90d5de822c8a8254fd3` |
| `month_ends.json` | `f8a6038d94d7c3266937f38756ad03c7de504975f2c012ea80f4ec0206d34dde` |
| `ticker_cik_history.json` | `95ffc960002c265f522d54e8a1eff233743cc5f294a48b3508afedbd5c67f96c` |
| `raw/eod/` (444 files, names-list sha256) | `7fc296a35e9579d02071228df488b2c64b91c91e79f83b51e45eec9ea19311a0` |

Panel months: 192, `2010-01-29` .. `2025-12-31`. Universe: 831 tickers (444 Oct-batch + 379 Nov-batch + 8 pilot/overlap).

## 3. Quarantine.log breakdown (545 rows)

| Reason | Rows | Disposition |
|---|---|---|
| `END_MISMATCH closed` | 131 | ticker-interval quarantines (the audited set) |
| `no EOD data` | 408 unique tickers | 379 = November batch (not yet pulled — expected); 29 = October-batch pull failures (Tiingo 404s: ATGE, BF.B, EKDKQ, BBBY, …). Data absence, not a guard-logic error. |
| `WARN late series start (kept, clamped)` | 6 | **Admitted**, not quarantined (BRCM, CVC, FOX, FOXA, HAR, IR). Log noise only. |

## 4. Classification of the 131 END_MISMATCH closed intervals

Method (local evidence only): for each row, `d_end` = (series_end − membership_end) in calendar days; series coverage vs the membership interval; CIK-count from `ticker_cik_history.json` (1 = stable identity, 0 = absent from file).

| Class | N | Rule | Meaning |
|---|---|---|---|
| **A** — terminates near interval end | 4 | −30d ≤ d_end ≤ +30d | Genuine delisting/acquisition/bankruptcy. **Eligible for frozen §5 last-close flat-hold.** |
| **B** — ordinary removal, series continued | 101 | d_end > +30d, series covers interval | Index removal; same company keeps trading. **Valid series, quarantine incorrect.** |
| **C** — reuse / data-deficient | 26 | series starts after interval end (s0 > me) | Ticker reused by a different company (e.g. ADT, APC) or trivially short series (e.g. BK: 5 bars — Tiingo pull deficiency). **Quarantine correct.** |

Class A detail (all genuine acquisitions; the guard's ±9d calendar window was too tight for settlement/data lag):
- ABMD: me 2022-12-22, series ends 2023-01-03 (+12d; J&J acquisition)
- BXLT: me 2016-06-03, series ends 2016-06-16 (+13d; Shire acquisition)
- CTXS: me 2022-10-03, series ends 2022-11-02 (+30d; Vista/Tibco acquisition; tail likely stale bars)
- HOT: me 2016-09-23, series ends 2016-10-03 (+10d; Marriott acquisition)

Class B identity evidence: 73/101 have exactly 1 CIK (stable company identity); 28/101 are absent from the CIK file (n_ciks=0) — spot-checked recognizable same-company continuations (AABA/Altaba, AKS/AK Steel→Cleveland-Cliffs, BHGE/Baker Hughes, AVP/Avon→Natura). Median d_end in Class B = 1,956 days (5.4 years) — these are unambiguous multi-year continuations, e.g. AMD (removed 2013-09-23, series to 2026-09-30), AAL (removed 2024-09-23, series to 2026-09-30).

Class C detail: 25 with series starting strictly after the interval end (clear reuse — new company holds the ticker); 1 data-deficient (BK, 5-bar series).

## 5. Lost observation months

Panel months overlapping each quarantined interval (clamped to 2010-01..2025-12):

| Class | Lost months | Unique tickers |
|---|---|---|
| A (delisting — flat-hold eligible) | 299 | 4 |
| **B (ordinary removal — valid history)** | **8,071** | **101** |
| C (reuse/data-deficient — correctly excluded) | 1,836 | 26 |
| **Total** | **10,206** | 131 |

**Material finding confirmed:** 8,071 membership-months of valid same-company history were dropped from the October panel because `reuse_guard` cannot distinguish an ordinary index removal from ticker reuse. For Class B, forward windows from any month in the interval are genuinely observable in the continued EOD series (same company, CIK-stable where recorded).

Note: some Class B tickers have a second, admitted interval (e.g. AMD re-added 2017-03-20) — the loss is the early interval's history, not the ticker entirely. The 8,071 figure counts only months inside the quarantined intervals.

## 6. Flag/status invariant preflight (task 5)

Implemented deterministic preflight check: for every row and horizon h ∈ {r3, r6, r12},
`fwd_complete_<h> == (fwd_status_<h> in {'complete','delisted_flat'})`,
using the **production** `forward_window()` and `resolve_horizon_filter()` from `research_notes/vcp_1a_codefix/`.

Results (synthetic trading-day dates only, no real data):
- 4 producer-built scenarios (open mid-series, open near boundary, closed past-end, closed fits): **0 violations — PASS**. Statuses produced: complete/True, censored/False, delisted_flat/True as expected.
- Adversarial hand-corrupted row (status=censored, complete=True): **caught**.
- Missing-flag schema → `resolve_horizon_filter` hard-errors (fail-closed confirmed).
- Script: `/tmp/preflight_invariant.py` (session-ephemeral); procedure reproducible from §6 text.

## 7. Correction proposal (ONLY — no code changed)

1. **Class B (101 intervals): admit as OPEN series.** Observation months within [ms, me] are eligible; forward windows use actual observed bars of the continued (same-company) series; censor only at the dataset boundary. Do NOT treat membership-end as a delisting. Recovers 8,071 observation months. Forward windows extending past `me` use the same company's post-removal returns — adjudicate whether the frozen estimand permits this or caps at `me`.
2. **Class A (4 intervals): admit as closed with frozen §5 flat-hold.** Widen the guard's end-match window from ±9 calendar days to ±30 calendar days (or trading-day-aware) so genuine delistings with settlement lag are not quarantined.
3. **Class C (26 intervals): keep quarantined.** No change.
4. **Add the §6 preflight invariant check as an execution-time gate** before the November run (producer-side; `resolve_horizon_filter` alone does not assert the cross-field invariant).
5. **Invalidate the delta code's assumption** `series_closed = (me != 2200-01-01)` ⟹ delisting: for Class-B-type intervals the membership interval is closed but the *series* is open. Closed/open for forward-window status must derive from actual series termination (guard admission + series-end proximity), not membership-end alone.
6. Apply before the November panel build — the 379 November-batch tickers will hit the same guard.

## 8. Unresolved ambiguities

1. 28 Class B tickers absent from the CIK history file — identity by series continuity + recognizable corporate history (spot-checked), not by CIK record. Recommend admit-with-flag or manual review.
2. CTXS's +30d tail: stale post-delisting bars vs actual trading; flat-hold start should use the true delisting date.
3. BK's 5-bar series: Tiingo pull deficiency, not reuse — same disposition (quarantine), different cause.
4. The ±30d Class A boundary is a judgment call; raw d_end distribution reported in §4 for adjudication.
5. Whether Class B forward windows may extend past membership-end (same company) or must cap at `me` — needs ChatGPT adjudication.

## 9. Effort

~35 minutes (within 45-min budget). Zero vendor requests, zero real-data performance calculations, zero strategy/parameter changes, zero sealed access. Panel NOT rebuilt; no results produced.
