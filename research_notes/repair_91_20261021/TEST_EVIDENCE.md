# TEST EVIDENCE — repair -91 (executed, synthetic fixtures only)

Environment: `unshare -n` (no network), CPython 3.12.3, pandas
2.2.3 — venv `qf35_work_20261019/venv` (the -82/-89 pinned set,
used unchanged). Every suite ran TWICE; outputs repeat-identical.

Headline counts (real, executed):
  checker test_completeness_check_v2.py        — exit 0 — 38/38 PASS
          (unchanged -89 suite against the repaired module)
  checker test_completeness_check_repair91.py  — exit 0 — 11/11 PASS
  guard   test_constructor_guard_v2.py         — exit 0 — 15/15 PASS
          (includes the -84 floor: 12/12 through the repaired module)
  guard   test_constructor_guard_repair91.py   — exit 0 — 8/8 PASS

================================================================
checker repair suite — verbatim (run 1)
================================================================
PASS R91_C1_clean_control_overall 
PASS R91_C1_clean_control_no_missing_sessions 
PASS R91_C2_mid_session_missing_flagged 
PASS R91_C2_count_fail 
PASS R91_C2_overall_completeness_fail 
PASS R91_C2_expected_bar_starts_named 
PASS R91_C3_first_session_missing_flagged 
PASS R91_C3_overall_completeness_fail 
PASS R91_C4_last_session_missing_flagged 
PASS R91_C4_overall_completeness_fail 
PASS R91_C5_session_table_required 

11/11 checks passed

================================================================
guard repair suite — verbatim (run 1)
================================================================
constructor copy pin verified: d47e8df14ec5…
PASS R91_G1_permuted_refused_spy0 
PASS R91_G1_equality_step_names_permutation 
PASS R91_G2_shifted_refused_index_mismatch 
PASS R91_G3_dropped_stamp_refused_index_mismatch 
PASS R91_G4_offgrid_refused_index_mismatch 
PASS R91_G5_no_session_table_refused 
PASS R91_G6_clean_byte_identical 
PASS R91_G6_clean_spy_invoked_once 

8/8 checks passed
