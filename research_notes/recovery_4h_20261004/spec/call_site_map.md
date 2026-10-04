# 4H BAR CONSTRUCTION — CALL-SITE MAP
**Recovery pre-run package — Phase A**
**Date:** 2026-10-04 | **Branch:** `recovery-4h-20261004`

Five distinct 4H construction paths exist in the repo. Every prior evidence
family is bound to exactly one path below.

---

## Path 1 — LEGACY `resample_closed_4h` (scanner_rules.py:87)
**Mechanism:** pandas `resample("4h", origin="start_day", offset="9h30min")`.
UTC-midnight-anchored; grid shifts with DST and download-window length.
**Known defect:** live forward test produced 06:30/10:30/14:30 ET bars instead of
09:30/13:30 (2026-09-15 through 2026-10-03).

**ADDITIONAL ROLE (rev 2, Gap 1):** This function (not Path 3) generated
`backtest_cache/v3/h4_*.pkl` (52 files, 2026-09-15) via an uncommitted process.
The UTC-anchored 13:30/17:30 grid, SessionVWAP column, and `last_bar_*` attrs
in the cache match this function's exact behavior. The 240-trade C1 baseline
(+0.178R) was built on this grid — see `spec/cache_provenance_forensic.md`
and `spec/cache_contamination_audit.md`.

| Call site | Role | Evidence family |
|-----------|------|-----------------|
| `masterscanner_api.py:98` | `/buy-now` endpoint | Live API signals |
| `scanner_streamlit_v5_1_morning_action.py:215` | Morning Streamlit scan | Morning reports |
| `scanner_streamlit_v5_mode_aware.py:215` | Mode-aware Streamlit scan | Mode-aware reports |
| `quantify_scanner_exit.py:51` | Exit quantification | Exit study |
| `build_affected_cohort_archive.py:93` | Affected-cohort archive | **Frozen cohort (4 open positions) — PINNED, do not change** |
| `v6_short_v2/data_2022.py:165` | 2022 short-study data | Short research (closed) |
| `pine_exit_fix/fetch_2022_extra.py:65` | 2022 extra data | Exit-fix research |
| `forward_test/kama_shadow_watcher.py:27,309` | Shadow watcher (aliased `production_resample_closed_4h`) | KAMA shadow log |

**Status:** FROZEN for the affected cohort. Preserved for forensic comparison.
New work must NOT use this path.

## Path 2 — SESSION-ANCHORED `resample_closed_4h_session_anchored` (scanner_rules.py:149)
**Mechanism:** Explicit session bins from local ET wall-clock; DST-safe; causal cutoff.
**Candidate canonical research path** (this recovery).

| Call site | Role | Evidence family |
|-----------|------|-----------------|
| `replay_4h_corrected.py:255` | Corrected 4H replay | Corrected-grid replay (−15.23R, adverse) |
| `top_broad_performance.py:63` | TOP-vs-BROAD performance | TOP-vs-BROAD (killed) |
| `tests/test_scanner_rules.py:241-278` | Unit tests | Constructor tests |
| `data_inventory_scratch_20261004/` | Bar-count inventory | Data inventory (counting only) |

## Path 3 — PER-DAY ORIGIN (canonical_baseline/scripts/fetch_4h.py:30)
**Mechanism:** Per-day `resample("4h", origin=day 09:30 local)`. Session-aligned
within each day but a third distinct implementation.

| Call site | Role | Evidence family |
|-----------|------|-----------------|
| `canonical_baseline/scripts/fetch_4h.py:80-81` | `canonical_baseline/data/h4_*.pkl` generation (137 files, 2026-09-25) | Canonical baseline data (clean 09:30/13:30 ET grid) |

**CORRECTION (rev 2, Gap 1):** Path 3 did NOT generate `backtest_cache/v3/h4_*.pkl`.
That claim in rev 1 was wrong. The v3 cache (52 files, 2026-09-15) was generated
by the legacy `resample_closed_4h` (Path 1 mechanism) via an uncommitted process —
see `spec/cache_provenance_forensic.md` for the full trace. Path 3's actual output
is the clean-grid `canonical_baseline/data/` set.

**Note:** `fetch_4h.py`'s per-day-origin output is byte-identical in OHLCV to the
session-anchored Path 2 on identical inputs (proven in Phase A fixtures).
Either could serve as the canonical grid; Path 2 is designated canonical for
its explicit DST handling and causal cutoff.

## Path 4 — VENDOR 4H (live harness)
**Mechanism:** `eng.m53.download_data(symbol, "4h", "180d")` — Yahoo vendor-resampled
4H bars. No repo constructor involved.

| Call site | Role | Evidence family |
|-----------|------|-----------------|
| `v54_forward_harness.py:1411` | Live forward-test 4H data | Forward test (degraded) |

## Path 5 — TEST/SYNTHETIC
`tests/test_scanner_rules.py` (both constructors), `tests/test_hardening_20261004.py`
(call-site map). No production evidence.

---

## Forensic preservation

- Path 1 (`resample_closed_4h`) is RETAINED UNCHANGED while the affected cohort
  has open positions (4 positions, entered 2026-09-15..10-03).
- Path 3 (`fetch_4h.py`) is RETAINED for forensic comparison against Path 2.
- No constructor code is modified by this pre-run package.
