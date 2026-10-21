# TEST EVIDENCE — task -82 fixtures (items 4 and 5)

Environment: `unshare -n` (no network), CPython 3.12.3, pandas 2.2.3,
numpy 1.26.4, pandas_market_calendars 4.5.1, exchange_calendars 4.13.2
(the pinned wheelhouse set; venv `qf35_work_20261019/venv`).
First run 2026-10-21 ~23:53Z; full repeat run immediately after —
both suites exit 0 with identical PASS counts (14/14 and 7/7).
All fixtures are synthetic. No vendor data, no holdout data, no real
symbol measurements anywhere in this directory.

## Item 4 — test_tsla_completeness_check.py (14/14 PASS, exit 0)

```
PASS  A_clean_overall  QUALIFIED_CLEAN
PASS  A_clean_count
PASS  A_clean_anomaly
PASS  A_clean_step  [{'effective': '2024-06-12', 'factor': 3.0, 'observed_step': 1.0, 'status': 'PASS'}]
PASS  B_overall_completeness_fail  COMPLETENESS_FAIL
PASS  B_anomaly_count_is_5  5
PASS  B_convention_lane_untouched  PASS
PASS  B_count_lane_pass
PASS  C_overall_convention_suspect  CONVENTION_BREAK_SUSPECT
PASS  C_step_observed_near_reciprocal_factor  0.333333
PASS  C_completeness_lane_untouched  PASS
PASS  D_overall_still_clean  QUALIFIED_CLEAN
PASS  D_flat_classified_separately  flat=2
PASS  E_missing_bar_count_fail  ['2024-06-11 11:30:00-04:00']

14/14 checks passed
```

Reading: case B is the TSLA-shaped defect (zero-volume price-moving
bars) and it lands in the COMPLETENESS lane only — the convention lane
stays PASS, so the check cannot emit an "inconsistent convention"
verdict for a completeness artifact. Case C is a true mixed-basis
series and lands in the CONVENTION lane only (observed boundary step
0.333333 = 1/3, the reciprocal of the declared 3:1 factor), with the
completeness lane untouched.

## Item 5 — test_constructor_hardening.py (7/7 PASS, exit 0)

```
constructor copy pin verified: d47e8df14ec5…
PASS  T1_index_equality  got ['2024-01-02 09:30:00-05:00', '2024-01-02 13:30:00-05:00', '2024-01-03 09:30:00-05:00', '2024-01-03 13:30:00-05:00', '2024-07-03 09:30:00-04:00']
PASS  T1_aggregation  open 100.0 vs 100.0; vol 406.0 vs 406
PASS  T1_early_close_single_bar
PASS  T2_filter_engaged_control
PASS  T2_warnings_as_errors_construction
PASS  T3_deterministic  run1=frame/26cc2504475d466d run2=frame/26cc2504475d466d
T3_BEHAVIOR: constructor does NOT reject duplicates; duplicated bar is silently merged (09:30 bin Volume=507 vs single-copy expectation 406)
PASS  T3_behavior_recorded  merged; bin volume 507 vs 406 (double-counted)

7/7 checks passed
```

FINDING (from T3, stated plainly): the pinned constructor, invoked
directly, does NOT reject duplicate 1H timestamps. It sorts and
aggregates, so a duplicated bar is silently merged into its bin and
its volume is double-counted (507 vs 406 on the fixture). The behavior
is DETERMINISTIC (two runs byte-identical, output sha 26cc2504…), so
the fixture's determinism bar is met — but duplicate safety is a
VALIDATOR-layer property (the cleared entrypoint runs validate_input
first; the fold materializer raises DUPLICATE_TIMESTAMP), not a
constructor property. See 05_CONSTRUCTOR_HARDENING_SPEC.md, H3.
