# TD PROBE OFFLINE CLOCK ALIGN — task -68 r1 RESULT

Task: QF-TD-PROBE-OFFLINE-CLOCK-ALIGN-20261021-68 r1
Spec: Issue #1 comment 6312788212 (-67 adjudication; basis -67
precommit be83d9c / result 7a6ca59, terminal
TD_PROBE_OFFLINE_CLOSURE_HOLD__Q11_RECEIPT_TS_FUTURE accepted).
Scope: ONE minimal successor package, new files only; -65/-66/-67
immutable. ONE implementation/test attempt after precommit;
first-failure stop. No vendor/network/API/model calls beyond the
read-only spec fetch; no credentials; zero credits; synthetic only.

## TERMINAL

TD_PROBE_OFFLINE_CLOCK_ALIGN_PASS__INDEPENDENT_REVIEW_REQUIRED__USER_GO_STILL_REQUIRED

## The single allowed change — harness clock alignment

-67's harness clock NOW_MS = 1_700_000_000_000 (2023-11-14
22:13:20 UTC) predates the committed fixture receipts
(BASE_TS_MS = 1_760_000_000_000, 2025-10-09 08:53:20 UTC; maximum
fixture receipt = base + 7d = 1_760_604_800_000), so the mandatory
RECEIPT_TS_FUTURE check correctly refused every fixture receipt
and the -67 attempt stopped at Q11.

-68 constant (tests_qualification.py, NOW_S / NOW_MS, with the
derivation documented in a comment at the constant):

  NOW_MS = 1_762_730_000_000  = 2025-11-09 23:13:20 UTC
  NOW_S  = 1762730000.0       (matching seconds value)

  Derivation: 1_760_000_000_000 (fixture epoch)
            + 31 * 86_400_000   (base + 31 days = 1_762_678_400_000,
                               2025-11-09 08:53:20 UTC)
            + 51_600_000        (advanced within the same UTC date
                               to 23:13:20 UTC — see disclosure)

The constant is strictly after the maximum fixture receipt
timestamp and at least base + 31 days, per spec. The CLI
subprocess fake clock (TD_FAKE_NOW_S in Q19) carries the same
aligned instant ("1762730000").

Disclosure — why 23:13:20 UTC and not plain base+31d (08:53:20):
B06 (cross-midnight usage cache) steps the session clock +1h from
NOW and asserts the UTC date rolls. As committed in -67, that
case could not pass at ANY 08:53 or 22:13 UTC clock — its date
literals ("2023-11-15" for NOW+1h) were already inconsistent with
-67's own 22:13:20 UTC clock; the case simply never ran (the -67
attempt stopped at Q11). This is a second latent harness defect,
in the test expectations, not in the closure logic. Within the
spec's latitude ("at least base +31 days; e.g. 1_762_678_400_000"),
the aligned instant was placed at 23:13:20 UTC on the base+31d
date so the +1h step crosses the UTC boundary the case exercises,
and B06's three literal date expectations were updated
mechanically to the aligned epoch (2025-11-09 / 2025-11-10).
No case construction, ordering, or acceptance semantics changed.

Complete diff vs -67 tests_qualification.py (nothing else):
 - docstring provenance label "task -68 r1"; stdout harness label
   "td68_qualification_r1" (provenance labels only);
 - NOW_S / NOW_MS constants + derivation comment (above);
 - Q19 TD_FAKE_NOW_S "1700000000" -> "1762730000";
 - B06 literal dates 2023-11-14 -> 2025-11-09 (x2),
   2023-11-15 -> 2025-11-10.

## Byte-equality vs -67 (logic files — all EQUAL)

  account_preflight.py  aae93734fe7e60d18f9e38e9099045af52b3a5cd246a1283b38014e4c73a2886
  probe_analyzer.py     ebea8272f33786676140b22b408eca46d87237a747be0f9e43600e9038933a0d
  probe_manifest.json   1bb86e17ee7907bae67db9c22b0a74cc61027c495c1f1ed74d65df17585a53e1
  probe_runner.py       e486636f35b59caafd59bd0787caf42f7355176c0c6187241b8c33f707e7bd6c
  temporal_gate.py      f882dd29bdf229264fb60eb12d7121d7bdc60536d5d71b16d893e236dc41e17e
  make_fixtures.py      28733bed43bff4e25d4c604ffd76d50c57faf3282c73722fde403a15b66c495a
  fixtures/ (56 files)  recursive diff vs -67: identical
  tests_qualification.py  2f1a279bdeaf1a2272578caaa0ecede6448f20797abb9009940a5a6ce05c3967 (changed only as itemized above)

Manifest scope/budget, fixture contents, acceptance semantics,
and case ordering are unchanged (byte-identical where applicable).

## Qualification — ONE attempt, 38/38 PASS, repeat byte-identical

Command: python3 -W error tests_qualification.py
Run 1: exit 0, stderr empty (0 bytes),
  stdout sha256 fe2817335d8b0f42f22205ab28549fc023e8a9fcab69e8bbbf43c8f8a5133aba
  (preserved verbatim as QUALIFICATION_RESULTS.json).
Permitted byte-identity repeat: exit 0, stderr empty,
  stdout sha256 fe2817335d8b0f42f22205ab28549fc023e8a9fcab69e8bbbf43c8f8a5133aba
  — byte-identical (cmp clean).

All 38 case outcomes (in order, all PASS):
Q01_scope_isolation, Q02_none_splits_mapping,
Q03_attempt_ceiling_arithmetic, Q04_attempt_cap_live,
Q05_no_pagination, Q06_usage_failure_before_data,
Q07_d1_run_and_usage_once_per_day, Q08_sanitized_receipts,
Q09_base_linkage, Q10_temporal_boundaries,
Q11_uniform_factor_pass, Q12_mixed_ohlc_fail,
Q13_volume_conventions, Q14_missing_volume,
Q15_revision_identical_different, Q16_malformed_evidence,
Q17_decimal_rounding_boundary, Q18_cli_refusals,
Q19_cli_end_to_end_days, Q20_no_global_verdict,
A01_mixed_volume_conventions, A02_swapped_request_ids,
A03_bar_set_defects, A04_meta_mismatch, A05_edited_usage_pass,
A06_cross_manifest_cache, A07_weaker_cached_headroom,
A08_stale_usage_timestamp, A09_future_usage_timestamp,
A10_coverage_empty, B01_legacy_argument_omission,
B02_blank_or_ambiguous_expectations,
B03_identical_meta_wrong_revision,
B04_identical_out_of_window_revision,
B05_identical_duplicate_revision, B06_cross_midnight_usage_cache,
B07_wrong_usage_endpoint_params, B08_malformed_numeric_strings.

This is the first execution evidence for the -67 source closures
(Q12-Q38 never ran in -67): mandatory expectations, C5
structure-before-identical, UTC execution-date cache binding,
endpoint-param re-verification, and malformed-numerics -> HOLD
are now test-proven on synthetic fixtures — candidate evidence
only, not adoption, and not a global S2 verdict (analyzer outputs
remain sampled-window PASS | DATA_UNQUALIFIED | HOLD only).

## Pins, elapsed, attestation

Precommit: 8a160dba5bbb3c3e8c3b4977f0d08488e01d6c79 (source/
manifest/fixtures/SHA manifest committed and pushed BEFORE
execution; verified ancestor of origin/main before the run).
Result commit: this commit (see git log); SHA256_MANIFEST.txt
regenerated at result to cover the final package.
Elapsed: ≈7 min from spec fetch to verified result push, of the
≤20 min cap. Repair minutes: 0 (first attempt passed; no in-run
repair; the B06 expectation issue was resolved inside the single
pre-precommit build, within the spec's clock latitude, and is
disclosed above).
Zero-call / zero-secret attestation: no vendor, network, API, or
model calls beyond the read-only spec fetch; no credentials read
or resolved; zero credits spent; synthetic fixtures only; no real
ADJ/S4/REV; no scheduling; no adoption or integration into
frozen/live paths; no S2 change; no -61 rerun; no performance,
holdouts, production, or trading touched.
State separation: REQ-S2 / data qualification / corrected
performance remain HOLD; entries PAUSED; the live probe remains
USER-GO HOLD. This PASS is candidate evidence for independent
review only.
