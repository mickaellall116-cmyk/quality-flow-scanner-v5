# CLAUDE CHECKPOINT 1 (CP1) — FULL FORENSIC BUNDLE

**Protocol:** Claude two-checkpoint protocol, Checkpoint 1 — FULL FORENSIC
**Subject:** Canonical 4H recovery, `backtest_cache/v3/h4_*.pkl` cache files and 240-trade C1 baseline
**Assembled:** 2026-10-04
**Branch:** `recovery-4h-20261004`

## Scope statement

This bundle contains raw evidence only. It contains no diagnosis, no statement
of what the "correct" grid is, no preferred fix, and no expected conclusion.
The 240-trade C1 ledger below is the baseline as computed; no corrected
performance data is included.

## Contents

### 01_cache_grid/
| File | Description |
|------|-------------|
| `h4_cache_hashes.json` | SHA-256 hashes of all 52 `backtest_cache/v3/h4_*.pkl` files, keyed by symbol |
| `bar_timestamps_raw.json` | Per file: bar count, column list, index timezone, first/last timestamp, full timestamp list. No grid classification applied. |

### 02_c1_ledger/
| File | Description |
|------|-------------|
| `c1_240_trade_ledger.json` | 240 trade records as computed: symbol, signal_time, entry_time, entry, stop, exit, exit_time, and additional fields per trade. Verbatim copy of `pine_execution/c1_corrected_baseline_20261003.json`. |

### 03_manifests/
| File | Description |
|------|-------------|
| `complete_manifest_rev2.json` | SHA-256 hashes for 8 source files; 51-symbol universe definition (symbols listed, definition hash); 51-entry sector map hash; per-file hashes for 52 cache files; SPY daily hash; note on raw 1H inputs. |

### 04_constructor/
| File | Description |
|------|-------------|
| `resampler_source.py` | Verbatim source of `resample_closed_4h` (scanner_rules.py:87) and `resample_closed_4h_session_anchored` (scanner_rules.py:149), extracted lines 87–267. File SHA-256 recorded in header. |
| `call_sites_factual.json` | Every `*.py` reference to each function name: file, line number, and whether the line is the function definition or a reference. No role labels. Bundle's own copy excluded from the scan. |

### 05_data_tier/
| File | Description |
|------|-------------|
| `data_tier_metadata.md` | Observed date range and index timezones across cache files; intended walk-forward data spec (Yahoo 1H parameters, universe, coverage rule); evidence-tier classification as stated in preregistration rev 2 §2; note on raw 1H input availability. |

### 06_fixtures/
| File | Description |
|------|-------------|
| `phase_a_results.json` | 11 fixture names with pass/fail booleans; comparison (a): input hash, row counts, identical flag, column/attr deltas; comparison (b): per-symbol bar counts, first/last timestamps, observed UTC slots, local label regimes. |
| `test_4h_fixtures.py` | Fixture source code: synthetic 1H builders (deterministic OHLCV formulas documented in docstrings), expected-bar computation, and all test functions. |

## GitHub commits

| File | Commit |
|------|--------|
| `CP1_BUNDLE_INDEX.md` | _pending_ |
| `01_cache_grid/h4_cache_hashes.json` | _pending_ |
| `01_cache_grid/bar_timestamps_raw.json` | _pending_ |
| `02_c1_ledger/c1_240_trade_ledger.json` | _pending_ |
| `03_manifests/complete_manifest_rev2.json` | _pending_ |
| `04_constructor/resampler_source.py` | _pending_ |
| `04_constructor/call_sites_factual.json` | _pending_ |
| `05_data_tier/data_tier_metadata.md` | _pending_ |
| `06_fixtures/phase_a_results.json` | _pending_ |
| `06_fixtures/test_4h_fixtures.py` | _pending_ |
