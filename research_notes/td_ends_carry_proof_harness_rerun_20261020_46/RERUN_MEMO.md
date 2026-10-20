# QF-TD-ENDS-CARRY-PROOF-HARNESS-RERUN-20261020-46 r1 — RERUN MEMO

**Terminal verdict (verbatim, as emitted by the single offline attempt):**
`TD_ENDS_CARRY_PROOF_HOLD__NLQUAL_REGRESSION`

**Status:** HOLD — awaiting independent review. Neither candidate is
adopted or re-pinned anywhere. The accepted -41 supplement and pin chain
are untouched. Repair minutes beyond the one authorized proof-driver
correction: **0**. One driver correction, one offline attempt,
first-failure stop honored (Family C's matrix subprocess failed to
start; nothing was repaired and nothing was rerun).

Spec: Issue #1 comment `6284381091` (adjudication of -45 +
QF-TD-ENDS-CARRY-PROOF-HARNESS-RERUN-20261020-46 r1 dispatch).
ACK was posted to Slack #qualityflowscaner before execution.

---

## 1. What this rerun was

-45 stopped at Family D's first check because the -45 proof driver's
own `_instants()` inspection helper used `list(s.values)` on a
tz-aware Series; under pandas 2.2.3 that yields tz-stripped naive
`numpy.datetime64` values, and `.tz_convert("UTC")` raised TypeError.
Adjudication: HOLD valid as a proof-driver defect, NOT a candidate
failure; both candidates frozen byte-identical; -46 = the narrow
rerun with exactly one driver correction.

## 2. The one authorized correction (proof harness only)

- -45 driver sha256: `a20b1ec3d24ca9aa2a2bc7962e8aa91431e25b74f836d2b6dc6350bc7e442d87`
- -46 driver sha256: `ec1cc4c2e96d4f7ab20a6204a50f2c5751ac3ed5ae0b0fe7fd672f1dcb510321`
- Exact old→new diff: `driver_old_new.diff` (this package). It contains
  ONLY: (1) the docstring/task-identity block (task id, spec comment,
  correction note), (2) the stage-path constant (td45→td46 staging),
  (3) the results task string, (4) **the one semantic correction** —
  `_instants(list(s.values))` → `_instants(list(s.array))` in Family
  D's `check_map`, and (5) the -46 terminal-label vocabulary strings.
  Expected instants, fixture generation, assertions, order, bindings,
  and candidate bytes are unchanged.
- Pre-run static proofs (spec point 3): `STATIC_PROOF.txt` — (a) all
  staged candidate/source bytes hash-equal to the frozen pins (no
  candidate/source diff); (b) every remaining `.values` occurrence in
  the corrected driver is a plain-dict iteration (classified line by
  line); no `Series.values`/`DataFrame.values` on tz-aware data
  remains; (c) Family D compares original report instants to
  candidate-output instants in UTC via `_instants()` while separately
  requiring homogeneous NY-aware index/value dtypes.
- Candidates re-verified byte-identical before the run (hash gates in
  `env_receipt.txt` / `proof_results.json`): validator candidate
  `ca3bafd87e7cb439d538ddf924aa08a029dd2c9bb32b485f61acbeea91429cc6`,
  entrypoint candidate
  `442e56cc16bbbb7ba8f3a62910d92bfcd07d85d0bb88ca2346d26b0bdcd2cba6`,
  constructor `d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd`,
  reference resampler `2a4994a26dbb98e244a14173a06697476835206c3d8d268ad21900dd43e0cbeb`,
  collector `b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c`,
  lock/freeze `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068`,
  wheelhouse manifest `210b8273…`; staged NLQUAL runner reproduced the
  -45 staged bytes exactly (`91cfa59b…` = repo runner +
  `nlqual_runner.diff` only); staged supplement `7fe1fd2f…` carried
  from -44/-45 staging unchanged.
- Environment: one offline attempt inside `unshare -n`; network probes
  failed as required (`NETWORK_DENIED`, curl exit 7); venv built
  `--no-index --require-hashes` from the pinned wheelhouse; freeze
  byte-identical to the TD lock (`FREEZE_EQUALS_LOCK`); CPython
  3.12.3, pandas 2.2.3, pandas_market_calendars 4.5.1. -43 E1 was NOT
  repeated, per spec.

## 3. Family results (executed evidence)

### Family A — structural/binding: **PASS, 10/10**
All ten checks true (decoder discipline vs pinned v5; binding identity:
the loaded entrypoint candidate's `validate`/`ValidationError` are the
validator candidate's; its `construct_4h` is the pinned constructor's).

### Family D — decoder contract: **PASS (full family)**
- `single_offset_real_report` (n=7, real candidate-validator report):
  dtype `datetime64[ns, America/New_York]`, key/value instants
  preserved in UTC, wall-clock truth holds.
- `mixed_offset_spring_real_report` (n=42; the report genuinely
  carries two distinct offsets): same, all true.
- `fall_dst_ambiguous_pair`: 3 entries, 3 distinct instants, wall
  clocks 00:30 / 01:30 / 01:30 with offsets −04:00 / −04:00 / −05:00
  preserved; `fall_dst_map` full check_map PASS.
- Fail-closed rejections — all five raised `ValueError` as required:
  naive key, naive value, malformed key, malformed value,
  duplicate-instant keys.

### Family B — E2 F1–F8: **PASS, 8/8**
- F1 (regular day): 2 bars, byte-identical to `resample_4h`
  (sha256 `bd550433…` both routes).
- F2 (early close 2024-11-29): 1 bar, byte-identical (`48f2d1a9…`).
- F3 (DST-spring week): validates AND constructs through the candidate
  pair; 12 bars, byte-identical (`b3276de1…`) — the -43/-44 blocking
  fixture now passes end to end.
- F4 (DST-fall week): 12 bars, byte-identical (`9a17db1b…`).
- F5 (two window lengths): all four equality checks true.
- F6 (closed day, stray bars): cleared route fails closed with
  validator **V4**; reference emits 1 bar — divergence expected,
  recorded, not promoted.
- F7 (missing due constituent 11:30): cleared route fails closed with
  validator **V6**; reference emits 2 bars — divergence expected,
  recorded, not promoted.
- F8 (mid-day as-of 14:30): cleared route emits exactly the completed
  09:30 bar (identical to F1's first bar); reference emits 2 —
  divergence expected, recorded, not promoted.

### Family C — NLQUAL 28-case regression: **NOT EXECUTED — subprocess failed to start (first failure, stop)**
The matrix runner (run 1 of the required two) exited 1 before any case
ran. First failure, verbatim from `proof_results.json`:

```
Traceback (most recent call last):
  File "/tmp/td46_stage/run_nlqual_matrix.py", line 72, in <module>
    spec.loader.exec_module(mod)
  File "/tmp/td46_stage/nlqual/td_lifecycle_repair_candidate/td_min_collector.py", line 35, in <module>
    from verify_sources import verify_directory, PINNED, ARCHIVAL_DIR  # noqa: E402
ModuleNotFoundError: No module named 'verify_sources'
```

**Root cause (post-hoc static analysis, labeled as such; NO rerun):**
a staging omission in THIS task's own stage assembly — not a candidate
defect and not an NLQUAL case failure (0 of 28 cases executed; no
classification result exists either way). `td_min_collector.py`
(lines 29–35) inserts its sibling `pilot_harness` directory into
`sys.path` and imports BOTH `rate_limiter` and `verify_sources` from
it. The -46 stage's `nlqual/pilot_harness/` contained
`validate_input.py` (the candidate, for the mechanism pin) and
`rate_limiter.py`, but omitted `verify_sources.py` (repo pinned bytes
`a0bd2e4cdce44be5d9fcc1d7c21046391d36c9bd366a959df03bf5d19c9a79e0`,
`research_notes/pilot_harness/verify_sources.py`). Per the
first-failure protocol the omission was NOT repaired and the matrix
was NOT rerun; a future re-dispatch needs only the completed stage —
every other element of this rerun (Families A, D, B) is executed PASS
evidence that stands on its own.

The PASS-only route-binding candidate record (spec point 6) was
therefore **not** emitted.

## 4. Prohibitions — all honored

No candidate or existing source modified (all pins hash-identical
before, in-gate, and after the run — see post-run re-hash in
`env_receipt.txt`); the only changed file is the proof driver, as
authorized; candidates adopted/re-pinned nowhere (staged NLQUAL
fixtures are stage/package records only); no vendor/API/model calls
during execution (fully network-isolated namespace; the only pre-run
network use was the read-only public fetch of the spec comment); no
credits/spend; no real market data (E2 fixtures synthetic, in-code;
NLQUAL uses its preserved offline fixtures); no SPT-08 dispatch (the
NLQUAL matrix never started); no backtests/performance; no holdout
access; no state/ledger/production changes (V5.4 harness untouched);
no trading restart; no Issue #9 work; no Yahoo work; no second attempt
or in-run repair of any kind.

## 5. Timing

Dispatch ~05:58Z → single execution inside the run script
(see `env_receipt.txt`) → package committed and remote-verified
06:07:46Z (commit `d0fef7c`). Elapsed ≈ 10 min of the ≤35 min cap.
Repair minutes beyond the one authorized driver correction: **0**.
(Correction, labeled per the -39/-40/-42 precedent: the first
committed version of this memo misstated the verification time as
~06:28Z / ≈30 min; the true remote-verification timestamp is
06:07:46Z. Corrected in the follow-up commit; no other content
changed.)
