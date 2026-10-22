# TEST EVIDENCE — task -84 (executed, synthetic fixtures only)

Environment: CPython 3.12.3 / pandas 2.2.3 (pinned wheelhouse venv),
`unshare -n` (no network), 2026-10-21. Each suite was run TWICE;
the two outputs are byte-identical for both suites (repeat-identical).
Outputs below are verbatim from run 1 of each suite.

Disclosure (build history, one repair): the producer suite's first
execution stopped at case P8 with a TypeError raised inside the TEST
file — the fixture passed `datetime.date` objects back into the
Calendar constructor, whose contract is ISO strings. The fixture was
corrected (`.isoformat()`); the producer core was not modified.
The corrected suite's full run is what appears below.

================================================================
PART A — guard/test_constructor_guard.py — exit 0 — 12/12 PASS
================================================================
constructor copy pin verified: d47e8df14ec5…
unguarded T3 reference: 09:30 bin Volume=507 (the -82 silent-merge value; single-copy expectation 406)
PASS  G1_t3_input_refused  error: CONSTRUCTOR_GUARD_DUPLICATE_TIMESTAMP: stage=input_1h duplicated_timestamp_count=2 duplicated_timestamps=['2024-01-02 10:30:00-05:00']
PASS  G1_refusal_named_error  
PASS  G1_refusal_deterministic  
PASS  G2_conflicting_duplicate_refused  error: CONSTRUCTOR_GUARD_DUPLICATE_TIMESTAMP: stage=input_1h duplicated_timestamp_count=2 duplicated_timestamps=['2024-01-02 10:30:00-05:00']
PASS  G3_clean_byte_identical  guarded 077e0c6b81509624 vs unguarded 077e0c6b81509624
PASS  G3_clean_frame_equal  
PASS  G4_index_equality_through_guard  
PASS  G4_index_assertion_live_negative_control  
PASS  G5_filter_engaged_control  
PASS  G5_warnings_as_errors_through_guard  
PASS  G6_constructor_not_invoked_on_refusal  spy calls=0
PASS  G6_spy_clean_path_invokes_once  

12/12 checks passed

================================================================
PART B — producer/test_split_event_producer.py — exit 0 — 23/23 PASS
================================================================
PASS  P1_state_ok  
PASS  P1_sorted_and_shaped  
PASS  P1_s2_contract_fields  
PASS  P1_envelope_stamps  
PASS  P2_saturday_normalized  
PASS  P2_holiday_normalized  
PASS  P3_early_close_flagged  
PASS  P4_modeA_excludes  
PASS  P4_modeB_includes_flagged  
PASS  P4_mode_unset_refuses  raised E3_MODE_UNSET: E3 PIT mode must be set explicitly; the rule is UNFROZEN
PASS  P5_identical_duplicate  raised DUPLICATE_OR_CONFLICTING_EVENT: records 0 and 1 share (symbol, effective_date)=('NVDAX', '2024-06-10')
PASS  P5_conflicting_duplicate  raised DUPLICATE_OR_CONFLICTING_EVENT: records 0 and 1 share (symbol, effective_date)=('NVDAX', '2024-06-10')
PASS  P6_no_producer_output_state  
PASS  P6_covered_empty_is_ok_zero  
PASS  P7_uncovered_symbol  raised COVERAGE_INCOMPLETE: requested symbols ['MSFTX'] not covered
PASS  P7_window_beyond_coverage  raised COVERAGE_INCOMPLETE: bars window 2024-06-03..2024-09-15 exceeds coverage 2024-05-01..2024-08-31
PASS  P8_calendar_range  raised CALENDAR_RANGE_INSUFFICIENT: calendar must extend >=1 session beyond the bars span on both sides
PASS  P9_missing_acquired_at  raised PROVENANCE_UNBOUND: source batch lacks an acquisition timestamp
PASS  P9_asof_after_cutoff  raised AS_OF_AFTER_DATASET_CUTOFF: NVDAX event as_of 2024-07-25T20:05:00+00:00 is after dataset as_of 2024-07-20T00:00:00+00:00
PASS  P10_deterministic_envelope  
PASS  P11_adjacency_scope  
PASS  P12_missing_field  raised MISSING_FIELD: record 0: field 'source' missing/empty
PASS  P12_invalid_factor  raised INVALID_FACTOR: record 0: factor_num=0 is not a positive integer

23/23 checks passed
