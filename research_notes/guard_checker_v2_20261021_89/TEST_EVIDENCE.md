# TEST EVIDENCE — task -89 (executed, synthetic fixtures only)

Environment: `unshare -n` (no network), CPython 3.12.3, pandas
2.2.3, numpy 1.26.4, pandas_market_calendars 4.5.1,
exchange_calendars 4.13.2 — the pinned wheelhouse set, venv
`qf35_work_20261019/venv` (the exact venv -82 documented; it
exists on this host and was used unchanged). Each suite was run
TWICE; the two outputs of each suite are byte-identical
(repeat-identical). Outputs below are verbatim from run 1.

Headline counts (real, executed):
  guard   test_constructor_guard_v2.py   — exit 0 — 15/15 PASS
          (includes the -84 floor: 12/12 through the v2 module)
  checker test_completeness_check_v2.py  — exit 0 — 38/38 PASS
          (floor wrapper 3 + FI intents 12 + C15–C22 23; the -82
          floor suite itself reads 10/14 under v2 — see FINDING)

================================================================
FINDING — the -82 'clean' fixture embeds a second undeclared
split-shaped step (root-caused at this build; NOT a v2 regression)
================================================================
The byte-unchanged -82 floor suite reads 10/14 against checker v2.
The four divergent assertions (A_clean_overall,
B_overall_completeness_fail, B_convention_lane_untouched,
D_overall_still_clean) all trace to ONE property of the -82
fixture builder (fixtures/test_tsla_completeness_check.py,
build_series): it divides the raw path by the split factor at the
first bar of EVERY post-split session — `if not pre and k == 0:
raw = raw / 3.0` — so the series its docstring calls "clean
uniformly-adjusted data" in fact carries a SECOND 3:1-shaped
overnight step at 2024-06-13. Measured on the fixture series
itself, the overnight steps are:

  2024-06-10 -> 2024-06-11: 1.000000
  2024-06-11 -> 2024-06-12: 1.000000   (the declared boundary)
  2024-06-12 -> 2024-06-13: 0.333333   (undeclared, factor-shaped)

Checker v1 had no lane that examines undeclared boundaries, so
the defect was invisible to it. Checker v2's STEP-ALL lane — the
lane -86 F4 specified for exactly this signature — sees it and
fires CONVENTION_BREAK_SUSPECT, as designed. No v1 lane regresses
under v2: every COUNT / ANOMALY / declared-STEP assertion in the
floor still passes (see A_clean_step PASS with classification
CONTINUOUS_ADJUSTED in the output below), and the suite's FI-A…E
scenarios — the five -82 intents rebuilt on a corrected builder
(split applied once, at its effective date) — reproduce all five
v1 outcomes exactly, lane separation included. The floor's 10/14
is therefore pinned in the v2 suite as a documented divergence
with named assertions, not silently absorbed: if the divergence
set ever changes, the suite fails. The -82 package is NOT edited;
adjudication may wish to record this fixture defect against -82
by reference.

Build history (repairs inside this task, disclosed):
  * Checker suite, first run: the floor divergence above, plus
    one defect in THIS package's v2 module — STEP-ALL reported
    matched_anchor 0.25 for a 0.333333 step (first anchor within
    tolerance instead of the nearest). Fixed in the v2 module to
    nearest-anchor selection; C19 now asserts matched_anchor = 1/3
    and passes. No other module or suite changes were needed;
    the guard suite passed in full on its first run.

================================================================
PART A — guard/test_constructor_guard_v2.py — exit 0 — 15/15 PASS
================================================================
constructor copy pin verified: d47e8df14ec5…
guard version: guard-v2-candidate-1
PASS  V2_version_anchor  
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
PASS  V2_floor_subprocess_exit0  rc=0
PASS  V2_floor_12_of_12  
PASS  V2_1_swapped_bars_non_monotonic  error: CONSTRUCTOR_GUARD_NON_MONOTONIC: stage=input_1h first_violation_at_row=2 prev=2024-01-02 11:30:00-05:00 cur=2024-01-02 10:30:00-05:00 spy calls=0
PASS  V2_1_refusal_names_first_violation  CONSTRUCTOR_GUARD_NON_MONOTONIC: stage=input_1h first_violation_at_row=2 prev=2024-01-02 11:30:00-05:00 cur=2024-01-02 10:30:00-05:00
PASS  V2_2_naive_index_timezone  error: CONSTRUCTOR_GUARD_TIMEZONE: stage=input_1h required_tz=America/New_York found_tz=NAIVE spy calls=0
PASS  V2_4_utc_index_timezone  error: CONSTRUCTOR_GUARD_TIMEZONE: stage=input_1h required_tz=America/New_York found_tz=UTC spy calls=0
PASS  V2_3_fixed_offset_timezone  error: CONSTRUCTOR_GUARD_TIMEZONE: stage=input_1h required_tz=America/New_York found_tz=UTC-05:00 spy calls=0
PASS  V2_3_unguarded_silent_misalignment_pinned  unguarded csv sha 90cc21e7efdbec9a… 2024-03-11 bins [303, 312] (NY-true would be [406, 315]; no warning raised)
PASS  V2_5_guarded_byte_identical_to_unguarded  
PASS  V2_5_matches_84_clean_case  guarded csv sha 077e0c6b81509624…
PASS  V2_5_conservation_per_bin  per_bin={'2024-01-02 09:30:00-05:00': 406.0, '2024-01-02 13:30:00-05:00': 315.0, '2024-01-03 09:30:00-05:00': 406.0, '2024-01-03 13:30:00-05:00': 315.0, '2024-07-03 09:30:00-04:00': 406.0}
PASS  V2_5_conservation_total  total=1848.0
PASS  V2_6_sabotage_volume_conservation_refusal  error: CONSTRUCTOR_GUARD_VOLUME_CONSERVATION: constructed volumes diverge from constituent input volumes mismatches={'2024-01-02 09:30:00-05:00': {'expected': 406.0, 'got': 304.0}, '__total__': {'expected': 1848.0, 'got': 1746.0}} saboteur calls=1
PASS  V2_6_refusal_names_bin_and_values  CONSTRUCTOR_GUARD_VOLUME_CONSERVATION: constructed volumes diverge from constituent input volumes mismatches={'2024-01-02 09:30:00-05:00': {'expected': 406.0, 'got': 304.0}, '__total__': {'expected': 1848.0, 'got': 1746.0}}

15/15 checks passed

================================================================
PART B — checker/test_completeness_check_v2.py — exit 0 — 38/38 PASS
================================================================
FAIL  A_clean_overall  CONVENTION_BREAK_SUSPECT
PASS  A_clean_count  
PASS  A_clean_anomaly  
PASS  A_clean_step  [{'effective': '2024-06-12', 'factor': 3.0, 'observed_step': 1.0, 'classification': 'CONTINUOUS_ADJUSTED', 'status': 'PASS', 'basis_mismatch': False}]
FAIL  B_overall_completeness_fail  COMPLETENESS_FAIL_AND_CONVENTION_BREAK_SUSPECT
PASS  B_anomaly_count_is_5  5
FAIL  B_convention_lane_untouched  CONVENTION_BREAK_SUSPECT
PASS  B_count_lane_pass  
PASS  C_overall_convention_suspect  CONVENTION_BREAK_SUSPECT
PASS  C_step_observed_near_reciprocal_factor  0.333333
PASS  C_completeness_lane_untouched  PASS
FAIL  D_overall_still_clean  CONVENTION_BREAK_SUSPECT
PASS  D_flat_classified_separately  flat=2
PASS  E_missing_bar_count_fail  ['2024-06-11 11:30:00-04:00']

10/14 checks passed
PASS  V2_floor_reads_10_of_14  rc=1
PASS  V2_floor_divergences_exactly_the_documented_four  floor FAILs: ['FAIL  A_clean_overall  CONVENTION_BREAK_SUSPECT', 'FAIL  B_overall_completeness_fail  COMPLETENESS_FAIL_AND_CONVENTION_BREAK_SUSPECT', 'FAIL  B_convention_lane_untouched  CONVENTION_BREAK_SUSPECT', 'FAIL  D_overall_still_clean  CONVENTION_BREAK_SUSPECT']
PASS  V2_floor_v1_lanes_survive  
PASS  FI_A_clean_overall  QUALIFIED_CLEAN
PASS  FI_A_lanes_pass  
PASS  FI_B_overall_completeness_fail  COMPLETENESS_FAIL
PASS  FI_B_anomaly_count_is_5  
PASS  FI_B_convention_lane_untouched  
PASS  FI_B_count_lane_pass  
PASS  FI_C_overall_convention_suspect  CONVENTION_BREAK_SUSPECT
PASS  FI_C_step_observed_near_reciprocal_factor  0.333333
PASS  FI_C_completeness_lane_untouched  
PASS  FI_D_overall_still_clean  QUALIFIED_CLEAN
PASS  FI_D_flat_classified_separately  
PASS  FI_E_missing_bar_count_fail  ['2024-06-11 11:30:00-04:00']
PASS  C15_nan_volume_completeness_fail  COMPLETENESS_FAIL
PASS  C15_nan_defect_recorded  [{'ts': '2024-06-11 10:30:00-04:00', 'defect': 'NAN_VALUE'}]
PASS  C15_convention_lane_untouched  PASS
PASS  C16_negative_volume_completeness_fail  COMPLETENESS_FAIL
PASS  C16_negative_defect_recorded  [{'ts': '2024-06-11 10:30:00-04:00', 'defect': 'NEGATIVE_VOLUME'}]
PASS  C17_one_share_moving_completeness_fail  COMPLETENESS_FAIL
PASS  C17_one_share_defect_recorded  [{'ts': '2024-06-11 10:30:00-04:00', 'defect': 'SUB_PLAUSIBLE_VOLUME_PRICE_MOVING'}]
PASS  C17_one_share_flat_stays_clean  QUALIFIED_CLEAN
PASS  C17_one_share_flat_classified_no_trade  flat=['2024-06-11 10:30:00-04:00']
PASS  C18_vbasis_overall_suspect  CONVENTION_BREAK_SUSPECT
PASS  C18_vbasis_lane_fires  [{'boundary': '2024-06-06', 'observed_ratio': 3.0, 'status': 'CONVENTION_BREAK_SUSPECT'}, {'boundary': '2024-06-07', 'observed_ratio': 3.0, 'status': 'CONVENTION_BREAK_SUSPECT'}, {'boundary': '2024-06-10', 'observed_ratio': 3.0, 'status': 'CONVENTION_BREAK_SUSPECT'}]
PASS  C18_price_lanes_clean  
PASS  C18_completeness_clean  
PASS  C19_step_all_overall_suspect  CONVENTION_BREAK_SUSPECT
PASS  C19_step_all_lane_fires  [{'boundary': '2024-06-12', 'observed_step': 0.333333, 'matched_anchor': 0.3333333333333333, 'status': 'CONVENTION_BREAK_SUSPECT'}]
PASS  C19_completeness_clean  
PASS  C20_declared_gap_stays_clean  QUALIFIED_CLEAN
PASS  C20_boundary_classified_price_action  [{'effective': '2024-06-12', 'factor': 3.0, 'observed_step': 1.6, 'classification': 'PRICE_ACTION', 'status': 'PRICE_ACTION_NO_FLAG', 'basis_mismatch': False}]
PASS  C20_no_convention_flag  
PASS  C21_scaled_by_factor_note  [{'effective': '2024-06-12', 'note': 'SCALED_BY_FACTOR', 'observed_pre_post_ratio': 3.0}]
PASS  C21_no_fail  QUALIFIED_CLEAN
PASS  C22_unscaled_note  [{'effective': '2024-06-12', 'note': 'UNSCALED', 'observed_pre_post_ratio': 1.0}]
PASS  C22_no_fail  QUALIFIED_CLEAN

38/38 checks passed
