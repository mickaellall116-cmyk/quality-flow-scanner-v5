# CP1 Follow-up Evidence Package
**Date:** 2026-10-05 | **Branch:** `recovery-4h-20261004`
**Assignment:** ChatGPT bounded forensic evidence collection, Issue #1 comment 5986944792
**Scope:** FORENSIC EVIDENCE COLLECTION ONLY. No corrected performance computed or opened.

## Files

| File | Content | Tag basis |
|---|---|---|
| `cache_hashes_pinned.txt` | SHA-256 of all 52 `backtest_cache/v3/h4_*.pkl` files, pinned BEFORE inspection | COMPUTED |
| `audit_52symbol.py` | Reproducible audit code (read-only; never mutates originals) | — |
| `audit_52symbol.json` | Machine-readable per-symbol audit: bars, tz, start/end, monotonicity, duplicates, missing/extra vs expected grid, off-grid label counts | COMPUTED |
| `audit_52symbol.md` | Human-readable audit summary table | COMPUTED |
| `trade_intersection.py` | Reproducible intersection code | — |
| `trade_intersection.json` | Machine-readable: all 240 trades with EST-regime flags and gap references (T145 PFE, T146 GOOGL). T192 SOL intersection WITHDRAWN — zero SOL trades intersect exact gaps. 51 equity shifted-regime entries + 31 crypto calendar entries. | COMPUTED |
| `FINDINGS.md` | Concise findings/unknowns table for all 6 tasks, every finding tagged COMPUTED / SOURCE/CODE VERIFIED / REPRODUCED / UNRESOLVED | — |

## Reading notes

- `audit_52symbol.json`: XNYS comparator classifies slots as 14,986 shifted (the DST fixed-UTC-grid defect scope) + 44 true absent (2 each on 22 symbols: 2026-01-30 afternoon + 2026-02-02 morning) + 225 scheduled early-close truncations. The 82 calendar-period entries split into 51 equity shifted-regime entries (defect exposure) + 31 crypto EST-calendar entries (calendar membership only, NOT a defect).
- `trade_intersection.json`: "gap_refs" enumerates temporal coincidence only. The file's `disclaimer` field states plainly that overlap is not proof of performance impact.
- Originals preserved: no cache file was modified; hashes pinned before inspection.

## Constraints honored

No corrected aggregate performance computed. No holdout access. No V5.4 production changes. No strategy tuning. No new data fetched.
