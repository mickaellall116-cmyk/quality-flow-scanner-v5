# TEST EVIDENCE -93

Environment: `~/workspace/qf35_work_20261019/venv` — CPython
3.12.3 / pandas 2.2.3 (verified at run time). All suites run
offline under `unshare -n`. Synthetic fixtures only; no vendor
calls, no credits, no holdout bytes, no snapshot reads.

## Regressions — prior suites vs their PRISTINE modules

Prior packages extracted byte-exact from their commits
(`959d61e` = -89, `db9e0f3` = -91) into a scratch tree; suites run
against the modules they were written for:

| Suite | Result |
|---|---|
| -84 floor `test_constructor_guard.py` (from -89 pkg) | **12/12** |
| -89 guard v2 `test_constructor_guard_v2.py` | **15/15** |
| -89 checker v2 `test_completeness_check_v2.py` | **38/38** (embedded -82 v1 floor section: 10/14 — the -82 fixture divergence documented in -89) |
| -91 checker repair `test_completeness_check_repair91.py` | **11/11** |
| -91 guard sabotage `test_constructor_guard_repair91.py` | **8/8** |
| -91 package's carried -84/-89 copies | 12/12, 15/15, 38/38 (same tallies) |

## New v3 suites (this package)

| Suite | Result |
|---|---|
| `guard/test_constructor_guard_v3.py` | **16/16** |
| `checker/test_completeness_check_v3.py` | **20/20** |

Guard v3 coverage: version anchor; clean path byte-identical with
calendar binding satisfied (spy exactly 1); NaN Close / NaN Volume
/ +inf High refusals (spy 0); placeholder all-NaN row refusal;
shadow-NaN divergence demonstrated (shadow excludes silently,
guard refuses); interval-end both conventions pass; truncated end
refused; truncated 3-of-4 bin named by the assert and refused by
the wrapper; calendar binding wrong-hash refusal, tamper named,
hash determinism (order-insensitive, content-sensitive);
column-less frame no-op at the guard layer.

Checker v3 coverage: version anchor; clean equity control
QUALIFIED_CLEAN; DUPLICATE_TIMESTAMP; TZ_NAIVE;
TZ_NOT_SESSION_ZONE (UTC equity); ORDER_VIOLATION;
ZERO_OR_NEGATIVE_PRICE (all-zero bar); HIGH_LT_LOW;
PRICE_OUT_OF_RANGE; NaN at declared boundary →
UNTESTABLE_NAN_BOUNDARY + untestable list + NAN_VALUE both
reported; declared boundary outside span → overall UNTESTABLE;
floor re-proofs (zero-volume price-moving → COMPLETENESS_FAIL;
missing session → COMPLETENESS_FAIL; clean declared split →
QUALIFIED_CLEAN / CONTINUOUS_ADJUSTED); crypto: clean NY-stamped
QUALIFIED_CLEAN, UTC-stamped identical verdict (ET attribution),
missing hour named, missing date with 24 expected starts,
declared-split caller-error refusal, duplicate stamp flagged.

## Compatibility — prior suites vs the v3 modules

| Suite vs v3 module | Result |
|---|---|
| Guard -84 floor | **12/12** |
| Guard -91 sabotage | **8/8** |
| Guard -89 v2 suite | **14/15** — sole failure `V2_version_anchor` (the v2 version-string assertion; v3's bump is deliberate, per Claude's pin-minting condition) |
| Checker -89 v2 suite | **38/38** |
| Checker -91 repair suite | **11/11** |
| Checker -82 v1 floor | **10/14** — the identical four checks that fail against the pristine v2 module (A_clean_overall, B_overall, B_convention_lane_untouched, D_overall_still_clean), all from the -82 fixture's embedded undeclared 3:1-shaped step documented in -89. Zero new divergence attributable to v3. |

## CH-1 archive verification (SPEC §5)

Fresh clone of `qf-data-archive` at HEAD `6de1517` (descendant of
`f47823b` + `4f6d470`), 2026-10-22:
`captures/ch1_core_hours_evidence_20261021_90/` —
`NYSE_2023_Annual_Guidance_Letter.pdf` sha256
`81a16c40d26aff312b05f21795153f8b27be6ee9fddf2b4d5916b5d4e30d0df7`,
`NYSE_RB-23-043.pdf` `7d94f9c7521a14cb2c7991dddf0476e766557c619a64bf6beb3d0f9cb090bdb1`,
`NYSE_RB-23-116.pdf` `e1dec9117f42bfdf1d6840e5ce0493c82bcde11cb924e52f6824a8d8b02f2b73`
— all three byte-exact vs the -90 EVIDENCE.md pins;
`sha256sum -c SHA256SUMS` 7/7 OK; `SHA256SUMS_ADDENDUM` 4/4 OK.

## Consolidated pin (§4.6 recipe, eight fixed entries)

`258aea36cf9b07f33bfa38cbbe85fed13dd655980f1cdf681730a56e6932fd34`
(inputs: calendar ext 8d659dde…, calendar dev 3358f2d9…,
checker v3 file 7b541382…, constructor d47e8df1…, guard v3 file
42e8704a…, -88 commit 6b0f5d0…, -91 commit db9e0f3…, UX51
b5d8877e… — full values in MANIFEST_AMENDMENT §4.6 and this
package's SHA256_MANIFEST).
