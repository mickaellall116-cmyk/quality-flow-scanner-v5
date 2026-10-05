# Provenance Search Evidence — v3 h4 cache generator
**Date:** 2026-10-05 | **Method:** COMPUTED (commands run, outputs recorded verbatim)
**Scope:** Locate the actual generator of `backtest_cache/v3/h4_*.pkl` (52 files).

## Search 1: scripts referencing the cache path
Command: `grep -rl "backtest_cache/v3" --include="*.py" .`
Result: 13 files (listed below). Classification by write behavior:

| File | Role re v3/h4_*.pkl |
|---|---|
| `pine_entry_timing_backtest/fetch_resample_4h.py` | Documents convention; writes to `canonical_baseline/data/`, NOT v3 |
| `pine_execution/c1_corrected_baseline_20261003.py` | READER (loads via `load_bull()`); asserts grid |
| `pine_exit_fix/pine_exit_fix.py` | READER (docstring reference) |
| `pine_expansion/study1_agreement.py` | READER ("EXACT bars the Pine baseline used") |
| `pine_expansion/study3_timeframes.py` | READER (references d1_5y_*.pkl, different files) |
| `pine_live/tests/test_slice*.py` (4 files) | READER (test fixtures) |
| `canonical_baseline/scripts/build_pool.py` | READER (glob includes v3 in search patterns) |
| `research_notes/recovery_4h_20261004/*/test_4h_fixtures.py` | READER (fixtures) |
| `research_notes/recovery_4h_20261004/cp1_followup/audit_52symbol.py` | READER (this audit) |

## Search 2: write operations targeting h4_*.pkl in v3
Command: `grep -rn 'to_pickle.*backtest_cache/v3/h4_' --include="*.py" .`
Result: **zero matches.** No committed script writes h4 files to this path.

## Search 3: git history
Command: `git log --oneline --all -- backtest_cache/v3/`
Result: no cache-file commits (files never committed; only incidental merge references).

## Search 4: filesystem build logs
Command: `find . -name "*.log" -newer <repo-root-marker>` (2026-10-04)
Result: no build logs for the Sep-15 2026 generation run.

## Byte-feature mechanism identification (SOURCE/CODE VERIFIED)
The 52 files exhibit: 13:30/17:30 UTC grid, `SessionVWAP` column, `last_bar_*`
attrs, forming-bar exclusion. These match legacy `resample_closed_4h`
(`scanner_rules.py`, `origin="start_day"`, `offset="9h30min"`) on every tested
feature. This identifies the MECHANISM (feature-signature compatibility).

**Qualification (per review item D):** feature-signature compatibility is NOT
reproduced OHLCV byte equality. We have not re-run the legacy function on the
original 1H inputs (not retained) and compared output bytes. The builder claim
is therefore: mechanism identified by signature, exact builder UNRESOLVED.

## Verdict
| Claim | Tag |
|---|---|
| Mechanism = legacy `resample_closed_4h` (feature-signature match) | SOURCE/CODE VERIFIED |
| Exact invoking script/session/command/config | UNRESOLVED (permanent gap) |
| Byte-equality reproduction of builder | UNRESOLVED (original 1H inputs not retained) |
