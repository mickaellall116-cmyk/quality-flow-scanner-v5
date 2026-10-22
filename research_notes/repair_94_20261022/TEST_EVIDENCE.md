# TEST_EVIDENCE — task -94 (2026-10-22)

Environment: pinned venv (CPython 3.12.3 / pandas 2.2.3), all
runs under `unshare -n` (offline). All fixtures synthetic. No
vendor calls, no snapshot bytes read, no holdout access.

## New suite — checker candidate-2 (this package)

`checker/test_completeness_check_v94.py` vs
`checker/tsla_completeness_check.py` (checker-v3-candidate-2)
+ `checker/crypto_session_model.py`:

**18/18 checks passed** (run twice, identical):
V94_C0 version · M1 counts 23/24/25 · M2/M3 span instants ·
M4 checker≡model instant-for-instant (2 DST weeks) · M5 zoneinfo
re-derivation of the 25h fall span · K1 clean normal sessions ·
K2 UTC stamps attributed · K3 clean spring (23 bars; missing
wall hour NOT flagged) · K4 clean fall (25 bars; repeated wall
hour NOT a duplicate) · K5 real missing bar fails (named in ET) ·
K6 real duplicate instant fails · K7 off-grid extra bar fails ·
K8 missing spring session (expected starts = 23) · K9
midnight-anchored legacy series FAILS (false pass closed) ·
K10 declared split refused · K11 naive index named, no crash ·
K12 equity floor clean.

Model parity (one-off, recorded here): the shipped model's spans
and assignment were compared against the ADOPTED -87 reference
implementation (crypto_calendar_spec.py) for all 1,096 session
dates 2023-01-01 → 2025-12-31 — spans identical, every expected
instant assigned to its own session. PASS.

## Regressions — pristine records intact

| suite | module | result |
|---|---|---|
| -93 guard v3 test_constructor_guard_v3 | pristine -93 | **16/16** |
| -93 checker v3 test_completeness_check_v3 | pristine -93 | **20/20** |
| -89 guard v2 test_constructor_guard_v2 | pristine -89 | **15/15** |
| -91 guard sabotage test_constructor_guard_repair91 | pristine -91 | **8/8** |

(Guard is not modified by -94; its suites re-run against their
pristine modules to prove the record this delta builds on.)

## Compatibility — prior checker suites vs candidate-2

| suite | result | divergences |
|---|---|---|
| -89 checker v2 (38) | **38/38** | none |
| -91 repair91 (11) | **11/11** | none |
| -82 v1 floor (14) | 10/14 | the SAME four checks as vs pristine v2 and v3 (A_clean_overall, B_overall_completeness_fail, B_convention_lane_untouched, D_overall_still_clean) — all trace to the -82 fixture's own embedded undeclared 3:1-shaped step at 2024-06-13 (the -89 finding). Zero new divergence. |
| -93 checker v3 (20) | 16/20 | exactly four, all expected: V3_C0 (version anchor — candidate-2 by design); V3_K1, V3_K2 (midnight-anchored "clean" crypto fixtures — misaligned under the adopted spec, now FAIL COUNT; this is the -94 correction closing the false pass); V3_K3 (same fixture family — its missing-bar assertion binds the superseded midnight anchor AND :00 stamp phase; adopted-anchored bars are :30-phase). All 13 equity cases and V3_K4/K5/K6 pass unchanged. |

## Findings (plain)

- **F-1 (ChatGPT's, confirmed):** -93 candidate-1's crypto model
  measured [00:00, 24:00) ET, not the adopted [09:30, +09:30)
  session. Fixed by this delta; the -93 record stands as
  delivered and is superseded by reference only for crypto mode.
- **F-2 (found during this build, fixed before evidence):** the
  first draft of the checker's session-attribution helper
  computed the prior session date by subtracting a 24h Timedelta
  from a tz-aware stamp — absolute arithmetic that, across the
  spring transition, attributed 2024-03-11 00:30 ET to session
  2024-03-09 (two dates back). The spring fixture caught it;
  attribution now uses calendar-date arithmetic. Disclosed
  because it is the same failure class (instant vs wall-clock
  confusion) the -94 review targets.
- **F-3 (documentary, corrected):** -93 MANIFEST_AMENDMENT §4.3
  called 2024-09-15 an equity session; it was a Sunday. See
  HO_SEAM_CORRECTION.md (verified against the adopted 751-session
  union three ways).
- No further mismatches found in the -93 package: its §4.3
  crypto seam text is consistent with the corrected model (HO's
  last crypto session is correctly the ET date 2024-09-15).
