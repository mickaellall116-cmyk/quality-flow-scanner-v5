# Verification Record — v1.0.2 Wording Amendment

All steps run **offline** against the frozen inputs in
`tier3_inputs/` (hashes pinned inside the generator). No network data
call of any kind was made; the only network operations in producing
this amendment were the git fetch/push of the record itself.

## 1. Generator v1.2.1 — two runs, byte-identical

```
$ cd tier3_inputs && python3 generate_tier3_list_v1_2.py
stage counts: { s1 4328, s2 +3118, steps1-3 7446, step4 5905,
  step5 5862, step6 5655, step6b removed [GOOG], after6b 5654,
  step7 2560 }
candidates for liquidity step: 2560
wrote tier3_list_v1_2.json sha256=08b670c43b68e38d0fb720dddb6b90710e8acefe7d37f34ad485613a560d2bbd
selected: ['BE', 'ACN', 'IREN', 'CRDO', 'TWLO', 'AAOI', 'MPWR', 'SPOT',
           'BABA', 'COF', 'BLK']
$ python3 generate_tier3_list_v1_2.py   (second run)
08b670c43b68e38d0fb720dddb6b90710e8acefe7d37f34ad485613a560d2bbd
cmp run1 run2 → byte-identical
```

Generator v1.2.1 SHA-256:
`5a1e074539645f687c4b54842b63dedbdf51fdf12cad0a64221ace4bf7d01fa6`
(supersedes v1.2 `d67ded42c023f9437e03e5fe3dc307bcaa3e6d7c2f8f1bfdf8c3dd594d90ff36`).

## 2. List and numerics unchanged vs the v1.0.1 output (`fbb73446…`)

Programmatic comparison of the regenerated v1.2.1 output against the
committed v1.0.1 output file:

- `tier3_list` array identical: **True** — canonical-array SHA-256
  `6468dc73712206111bba732c1b8da61d300373e073cf421391b93510491a5200`
  in both files.
- Numeric stage counts: **no differences** (the renamed key's value is
  2549 in both, under the old label in v1.0.1 and the corrected label
  in v1.0.2); no stage keys added or dropped besides that rename.
- `parameters` identical: **True**. `input_hashes` identical: **True**.
- Container SHA-256 differs (`fbb73446…` → `08b670c4…`) solely from:
  the renamed stage key, the `generator_version` / `rule_version`
  strings (v1.2.1 wording amendment), and the added `derivation`,
  `rank_12`, and `rank_12_status` fields.

## 3. Rank-12 fixture — 10/10 PASS

```
$ python3 test_rank12_fixture.py
PASS: list has exactly 11 entries
PASS: ranks are contiguous 1..11
PASS: no rank-12 entry in the list
PASS: rank_12 is recorded as null
PASS: rank_12_status states UNKNOWN
PASS: corrected label present with value 2549
PASS: superseded fail_closed label absent from output
PASS: derivation recorded as residual_list
PASS: selected_count == 11 and shortfall == 1
PASS: symbols exactly the expected residual top-11, in order
FIXTURE RESULT: PASS
```

## 4. Label sweep

The superseded string `s8_candidates_without_frozen_aggregate_fail_closed`
appears in this package **only** where it is quoted as superseded
(`AMENDMENT_V10_2.md`, `CHANGELOG_V10_2.md`, this file, and the
fixture's absence assertion). It does not appear in the corrected
generator or its output. In the corrected operative artifacts, the
2,549 are described only as `aggregate_not_persisted__not_re_evaluated`
(evidence loss), and the step-8 result only as a residual list.
