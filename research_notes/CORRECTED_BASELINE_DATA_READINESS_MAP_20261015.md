# QF-CORRECTED-BASELINE-DATA-READINESS-MAP-20261015-07 r1

## Verdict

**BASELINE_DATA_HOLD**

No already-held dataset is presently eligible to support an unchanged-strategy corrected-baseline build. The one dataset that ever matched the C1 input contract's shape (D1, the `backtest_cache/v3` 52-file 4H store) is **destroyed** — its per-file SHA256 pins and forensic record survive in the CP1 bundle, its bytes do not. Every other held dataset fails the contract on universe, interval, adjustment-policy evidence, terms, or archival existence. This task produced no performance result. Elapsed: ~4 minutes by the VM clock (09:56:34Z first spec fetch → 10:00Z package verification; budget ≤45).

**Minimal next evidence action (one):** a scoped clean-capture + qualification task — pull Yahoo 1H for the frozen UNIVERSE_X 51 symbols under preregistration rev2 §2 policy (`auto_adjust=False`, `prepost=False`, frozen split-exclusion protocol), build session-anchored 09:30 ET 4H bars, gate them through the recovery-4h parity fixtures (DST boundary + two window lengths), and pin bytes + per-file SHA256 + coverage matrix *before* any baseline build is tasked.

## What exists (7 inventoried datasets; full machine-readable record in the package)

| ID | Dataset | State vs the C1 contract |
|---|---|---|
| D1 | Yahoo 1H→4H cache `backtest_cache/v3` (52 files, 75,311 bars, 2024-09-15→2026-09-15) | **ABSENT — destroyed** (VM replacement; git-ignored, never committed). Pins: CP1 bundle `01_cache_grid/h4_cache_hashes.json` |
| D2 | Yahoo watchlist 4H cache, 14 symbols (2023-10-25→2026-09-23) | Present, correct ET grid, diagnostics clean — **diagnostic-only**: wrong universe (watchlist ≠ UNIVERSE_X 51), adjustment policy unpinned |
| D3 | Tiingo EOD, 444 symbols, 1.54M rows (2009→2026-09-30) | Present, diagnostics clean — **daily-only** (contract needs 1h→4h), raw+adjusted fields both present (policy-ambiguous), terms HOLD |
| D4 | Twelve Data spot artifacts (AAPL 1h/4h, 28 days; SPOT8 receipts) | Spot evidence only; route **PARKED** (2026-10-15 adjudication) |
| D5 | Live forward artifacts (signal ledger; 3 daily-close sidecars) | Not price history; feed operational, no bar archive retained |
| D6 | Canonical re-baseline inputs (Sep 2026, 131 sym, yfinance runtime pulls) | **Never archived**; engine code absent from git (.pyc only) — result documented, inputs unrecoverable |
| D7 | Sealed 11-month holdout | Identity-only per spec; no holdout files exist on this VM; the seal designation survives in the research record; nothing opened |

## Contamination & derivatives (separated, per spec)

- **Known contaminated:** D1's defective fixed-UTC grid (CP1: 332 EST bars mislabeled; mixed index tz across files — 45 America/New_York + 7 UTC crypto files). Every derivative of D1 is a result *about lost bytes*: the original 240-trade baseline (disqualified), the 143-trade buggy figure (disqualified), the corrected-grid replay −15.23R and the C1 corrected +0.178R @4bps (both stand as recorded evidence; neither can be recomputed or extended today).
- **Unknown-provenance / policy-ambiguous:** D3 adjustment fields (raw + `adj*` both present vs the frozen `auto_adjust=False` policy); D2 adjustment policy unevidenced; D6 inputs unarchived.
- **Qualified reusable bytes for the C1 contract:** none. Zero of 51 symbols; zero contract-conformant days on disk.

## Diagnostics actually run (existing bytes only, per spec §3)

- D2 (14 files): 0 duplicate timestamps, all monotonic, 0 impossible-OHLC violations, bar times exclusively 09:30/13:30 ET (session-aligned across DST by tz-aware index); spans vary only by listing age (ASTX/DRAM/SPCX short).
- D3 (444 files): 0 duplicate dates, 0 non-monotonic, full raw+adjusted field sets present.
- D5 sidecars: 62–63 daily rows each, 2026-06-25→2026-09-23.
- D1/D6/D7: **no diagnostics possible — bytes absent** (failure ledger F-01/F-03/F-06 in `inventory.json`; logged, never silently excluded). Hash-stability check on D1 is one-directional: CP1 pins exist, bytes do not.

## Input-contract map (C1, unchanged)

51-symbol UNIVERSE_X + SPY/QQQ-class benchmarks + sector map; 4H bars from Yahoo 1H (`auto_adjust=False`, `prepost=False`); split-exclusion protocol; tier LIMITED (not PIT-clean); span target 2023-01-01/earliest-available (as-run 2024-09-15→2026-09-15); <80% history = COVERAGE-LIMITED; signals `pine_buy_signal` with int() trendScore casts; rs_top2 + sector cap + 5% risk; 4bps one-way. **Qualified coverage today: 0%.** The as-run study grid (UTC-anchored bins, DST caveat) also fails the standing parity gate — a rebuild must use session-anchored construction, which is part of why the minimal next action includes the parity fixtures rather than a bare re-download.

## Maximum contiguous qualified window

**None.** D2's 2023-10-25→2026-09-23 window is diagnostic-only and does not satisfy the frozen design; shortening or re-universing the baseline to fit held bytes would redefine the experiment, which the spec forbids.

## Routes (evidence-backed only)

Yahoo history: feed operationally recovered, historical bytes lost. Prospective clean capture: not yet captured; known limits are the ~730-day 1H reachback and tier-LIMITED status (no PIT-clean 1H source at zero cost, per prereg rev2). Twelve Data: PARKED. Tiingo: HOLD (terms + daily-only).

## Package

`research_notes/corrected_baseline_data_readiness_20261015/` — `inventory.json` (datasets, contamination register, contract map, route comparison, failure ledger, minimal next action), `coverage_matrix.csv` (per-symbol D2/D3), `diagnostics_results.json` (per-file diagnostics incl. sha256 for D2/D3/D5 files), `SHA256_MANIFEST.txt`.

Scope: read-only throughout — zero vendor/API/model calls, downloads, installs, mutations, backtests, holdout access, or production changes.

— Muse
