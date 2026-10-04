# Scanner Engineering Hardening — Evidence Package (2026-10-04)
Branch: `hardening-20261004` | Evidence tier: **builder-tested** (Muse)

## Pre-change hashes (SHA-256, first 16)
```
7db282ddfc150c9e  scanner_rules.py
1b55dedce3b17b16  v54_rules.py
bde3288307ac7b9b  v54_engine.py
731208b5618fb5d1  v54_forward_harness.py
c3e95b25b114a50c  masterscanner_api.py
```

## Item 1: filter_buy_now — call-site proof
**Definition:** `scanner_rules.py:340`
**Live call sites:**
- `masterscanner_api.py:375` — `valid=filter_buy_now(candidates,limit=limit)` in `/buy-now` FastAPI endpoint (ACTIVE)
- `tests/test_scanner_rules.py:142` — unit test
**V5.4 decision path:** NO references (verified by source grep + static invariant test).
- `v54_forward_harness.py`: no import of masterscanner_api, no filter_buy_now reference
- `v54_engine.py`: no reference
- `v54_rules.py:16`: docstring explicitly documents exclusion ("It never imports the V5.3 veto logic")
**Action taken:** NOT quarantined (has live API call site). Added clarifying docstring
documenting active use (API) vs non-use (V5.4). Added static invariant test
`test_v54_path_never_references_filter_buy_now`.

## Item 2: 4H resampler — call-site map
| File | Constructor used |
|---|---|
| `v54_forward_harness.py:204` (affected-cohort path) | legacy `resample_closed_4h` (PINNED — exits must use exact legacy grid) |
| `masterscanner_api.py:98` | legacy `resample_closed_4h` |
| `scanner_streamlit_v5_*.py:215` | legacy `resample_closed_4h` |
| `forward_test/kama_shadow_watcher.py:309` | legacy (aliased as production_resample) |
| `v6_short_v2/`, `pine_exit_fix/` | legacy (research, read-only) |
| `replay_4h_corrected.py`, `top_broad_performance.py`, `data_inventory/` | `resample_closed_4h_session_anchored` (corrected) |
| `tests/test_scanner_rules.py` | both (fixtures for each) |
**Action taken:** Rename BLOCKED by STOP condition — frozen V5.4 harness depends on
`resample_closed_4h` by name (affected-cohort pinned path). Added unmistakable
`LEGACY — DO NOT USE FOR NEW WORK` docstring header pointing at the corrected
constructor. Added `test_resampler_call_site_map` documenting the map.

## Item 3: version label
- Before: `"""Canonical bar construction and signal validation for MasterScanner V5.2."""`
- After: accurate V5.x shared-module description.
- Proof of doc-only: AST identical after docstring strip; `git diff` shows +17/-2 lines, all docstring.

## Item 4: score non-gating — behavioral differential test
- `tests/test_hardening_20261004.py`: 7 tests.
- Mutations: 14 extreme values × 3 score fields × 4 decision scenarios
  (eligible-A, eligible-B, eligible-C, ineligible) = 168 differential runs.
- All decision outputs byte-identical across every mutation.
- Supplement: static source check that `v54_grade`/`v54_hard_gates_pass` never
  reference score field names.

## Test results
- New hardening suite: **7/7 pass**
- Existing `test_scanner_rules.py`: **25/25 pass** (no drift)
- End-to-end decision parity (6 representative rows, before/after): **IDENTICAL**

## Post-change hashes
(see commit for full SHA-256)
- `scanner_rules.py`: docstring-only changes (module docstring, filter_buy_now docstring, resample_closed_4h LEGACY header)
- `tests/test_hardening_20261004.py`: new file
- No changes to: v54_rules.py, v54_engine.py, v54_forward_harness.py, masterscanner_api.py

## STOP-condition report
- Item 2 rename: NOT performed (frozen harness dependency). Documented instead.
- No decision drift detected anywhere. No strategy logic touched.
