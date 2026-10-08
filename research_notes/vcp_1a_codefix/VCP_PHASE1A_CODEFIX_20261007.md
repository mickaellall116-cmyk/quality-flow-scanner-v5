# VCP Phase 1A Codefix — QF-VCP-1A-CODEFIX-20261007-03

Per ChatGPT adjudication (Issue #1 comment 6051281109). Load-bearing code
correction only — no strategy-rule changes, zero vendor requests, zero
real-data performance reruns, zero parameter changes, zero sealed access.

Published code (sha256):
- `analyze.py` — `998b3b79325856b02389154e0d4900ecf307bbeff9a197807fd3cc9aebb92520`
- `build_panels.py` — `be7128c7507354c53f2b838df1a36e05e7c60275b33b89ceaefb4`
- `test_vcp_phase1a_codefix.py` — `3c7021aa2a20793fdd89a5cb3889779649581797e6b6114ebe4c4e417ca8ac91`
- Synthetic tests: **22/22 PASS** (synthetic data only; T3 uses on-disk raw
  EOD calendars for trading-day counts — no vendor calls).

## Defect 1 — Wrong horizon annualization (FIXED)

`d_m` is already a 3M/6M/12M forward-return difference. The old code
multiplied every horizon's mean effect by 12. The frozen RUN_PLAN §7 line
"Effect size annualized (×12) also reported" is the documented source of the
bug; the adjudication overrides it as a load-bearing math error (not a
strategy change — the estimand is untouched).

Corrected reporting:
- **Primary:** raw per-window mean effect (`mean_window`).
- **Secondary (labeled):** linear horizon-equivalent annualized figure
  (`mean_ann_linear_equiv_SECONDARY`) = raw × 4 (r3) / × 2 (r6) / × 1 (r12).
- Same fix applied to vs-SPY "annualized" fields.

**INVALIDATED (original evidence report, preserved unchanged):** all
`mean_ann` magnitudes (e.g. reported −14.92% for V1 r12 was the raw −1.2434%
12M effect multiplied by 12 again) and all `vs_spy` annualized values. Do not
cite them.

## Defect 2 — Lexical date-boundary bug (FIXED)

SUBPERIODS bounds (`"2010-01"`..`"2011-12"`) were compared lexically against
full dates (`"2011-12-31"`), silently dropping every ending-December: 23
months per subperiod instead of the frozen 24. All month comparisons now use
month periods (`mth[:7]`). Synthetic tests prove 24 months in every complete
2Y subperiod and reproduce the old 23-month bug.

**INVALIDATED:** all previously reported `n_positive_subperiods` counts
(e.g. 3/8) — computed on 23-month subperiods. Corrected counts come from the
November full-universe run.

## Defect 3 — Hardcoded r12 cutoff replaced with data-derived cutoff (FIXED)

The old `mm > "2025-09"` string cutoff is replaced by `last_complete_month`:
the latest month where ≥95% of panel-active tickers have a complete forward
window by actual trading-day count (on-disk raw EOD; deterministic; the
denominator is panel-active tickers so delisted names cannot veto late
months).

**Material calendar finding:** on the frozen panel the data-derived r12
cutoff is **2025-08-29, not 2025-09**. September 2025's r12 window is
genuinely 1 trading day short (251 available < 252 required) — the
adjudication assumed September was complete; the actual calendar says
otherwise. r3/r6 cutoffs derive as 2025-12-31. r12 therefore still uses 188
months, but now for a principled reason rather than a string-comparison bug.

`build_panels.py` additionally emits per-row `fwd_complete_r3/r6/r12` flags
(True iff the full w-trading-day window is present). Truncated values are
retained for provenance but flagged; corrected `analyze.py` filters on flags
when present and falls back to the data-derived month cutoff on legacy
panels. No silent truncation remains.

## EFTS counts reconciled (by unit)

Scope: 127 EFTS tickers in the October batch (`efts_validation.log`).
- **24 tickers validated** (`cik_validated.json`: ticker→CIK map).
- **87 unique tickers dropped** — SEC name mismatch vs Tiingo metadata
  (`cik_dropped.json` "dropped" list; 87 records, 87 unique tickers).
- **39 unique tickers with fetch errors** — 128 error records (retries;
  mostly Tiingo HTTP 404) in `cik_dropped.json` "errors".
- Union: 24 + 87 + 39 − overlaps = 127; **zero unaccounted**. (Overlaps: 4
  validated tickers had transient errors before succeeding; 19 dropped
  tickers also logged errors.)
- Earlier conflicting figures resolved: the inventory's "2 dropped / ~61
  pending" was from an early partial validation pass; the evidence draft's
  "89 drop records / 128 pending" conflated records with tickers and
  miscounted drops (87, not 89). Ground truth is the file contents above.

## October batch selection rule (published)

- `batch_oct.txt` (445 tickers) = 5 pilot tickers (SPY, WMT, DIS, INTC, IBM)
  + 440 tickers in strict alphabetical order (A → LEG).
- `batch_nov.txt` (379 tickers) = strict alphabetical order (LEN → ZTS).
- 8 additional large-cap tickers in `batch_all.txt` (AAPL, ATVI, BAC, F, GE,
  KMI, MSFT, T) are assigned to neither batch file (unassigned/reserved).
- **Selection is alphabetical, NOT random.** The October interim is therefore
  descriptive only even after code correction — stated explicitly, no
  post-hoc reinterpretation.

## What was NOT done (per budget)

- No rerun of the real panel or real results. Corrected magnitudes and
  subperiod counts will come from the ONE full-universe November run
  (≥2026-11-01), after review of this package.
- No vendor requests, no parameter changes, no sealed-validation access.
- Phase 1B remains unpreregistered and blocked. No Claude checkpoint yet.

## Actual effort

~55 minutes (within the 60-minute budget).
