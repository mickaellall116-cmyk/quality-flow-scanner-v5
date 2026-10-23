# TEST EVIDENCE — QF-TD-PILOT-ADJUDICATION-20261023-02

All runs OFFLINE under `unshare -n`, pinned venv
`~/workspace/qf35_work_20261019/venv` (CPython 3.12.3 / pandas
2.2.3), `-B` (no bytecode writes). Working dir: this package.

## Inputs verified before any run

- Pilot store integrity: `sha256sum -c SHA256SUMS` in
  `~/workspace/qf_td_pilot_20261023/store` → **22/22 OK** (the
  store is byte-identical to qf-data-archive commit `45496f8`).
- Session table pin: sha256 of
  `research_notes/shadow_closeout_20261022/session_table.json`
  (extracted from origin/main) =
  `00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f`
  — matches the shadow-closeout pin; the driver re-verifies this
  hash at runtime and refuses on mismatch.
- Checker copies: sha256 of `checker/tsla_completeness_check.py`
  (`4fdc31cb…`) and `checker/crypto_session_model.py`
  (`248442f1…`) equal the origin/main bytes of
  `research_notes/repair_94_20261022/checker/` — verified by
  hashing `git show` output against the copies.

## Run 1 — actual-byte checker (the adjudication run)

```
unshare -n ~/workspace/qf35_work_20261019/venv/bin/python -B \
  run_actual_byte_check.py <pinned session_table.json> \
  ~/workspace/qf_td_pilot_20261023/store
```
Stdout (verbatim copy: `run_stdout.txt`):

```
NVDA/HO: raw_rows=1583 admitted=1583 excluded=0 raw_overall=CONVENTION_BREAK_SUSPECT admitted_overall=CONVENTION_BREAK_SUSPECT admitted_anomalies=0
NVDA/DEV: raw_rows=3654 admitted=3653 excluded=1 raw_overall=COMPLETENESS_FAIL_AND_CONVENTION_BREAK_SUSPECT admitted_overall=CONVENTION_BREAK_SUSPECT admitted_anomalies=0
TSLA/HO: raw_rows=1583 admitted=1583 excluded=0 raw_overall=CONVENTION_BREAK_SUSPECT admitted_overall=CONVENTION_BREAK_SUSPECT admitted_anomalies=0
TSLA/DEV: raw_rows=3655 admitted=3653 excluded=2 raw_overall=COMPLETENESS_FAIL_AND_CONVENTION_BREAK_SUSPECT admitted_overall=CONVENTION_BREAK_SUSPECT admitted_anomalies=0
AAPL/HO: raw_rows=1583 admitted=1583 excluded=0 raw_overall=CONVENTION_BREAK_SUSPECT admitted_overall=CONVENTION_BREAK_SUSPECT admitted_anomalies=0
AAPL/DEV: raw_rows=3655 admitted=3653 excluded=2 raw_overall=COMPLETENESS_FAIL_AND_CONVENTION_BREAK_SUSPECT admitted_overall=CONVENTION_BREAK_SUSPECT admitted_anomalies=0
SPY/HO: raw_rows=1583 admitted=1583 excluded=0 raw_overall=CONVENTION_BREAK_SUSPECT admitted_overall=CONVENTION_BREAK_SUSPECT admitted_anomalies=0
SPY/DEV: raw_rows=3655 admitted=3653 excluded=2 raw_overall=COMPLETENESS_FAIL_AND_CONVENTION_BREAK_SUSPECT admitted_overall=CONVENTION_BREAK_SUSPECT admitted_anomalies=0
SMCI/HO: raw_rows=1584 admitted=1583 excluded=1 raw_overall=COMPLETENESS_FAIL_AND_CONVENTION_BREAK_SUSPECT admitted_overall=COMPLETENESS_FAIL_AND_CONVENTION_BREAK_SUSPECT admitted_anomalies=19 classification=NOT_EVALUABLE_PROVIDER_VOLUME
```

Full per-lane detail (COUNT missing/extra lists, ANOMALY stamps,
STEP results, VBASIS counts, endpoints): `checker_report.json`.
Reading of the CONVENTION_BREAK_SUSPECT composites — VBASIS-only,
with the disposition — is ADJUDICATION.md Result 1; completeness
(the gate this task owns) is PASS on all 8 receipted legs'
admitted bytes and FAIL on SMCI/HO admitted bytes (ANOMALY 19).

## Run 2 — pilot-artifact regression fixtures (new)

```
unshare -n ~/workspace/qf35_work_20261019/venv/bin/python -B \
  fixtures/test_pilot_artifact_regressions.py
```
Stdout (verbatim copy: `fixtures/fixtures_stdout.txt`):

```
PASS F-PH1 flat zero-volume stub: raw COUNT extra = the 15:30 stub; admission excluded exactly 1 row; admitted PASS
PASS F-PH2 nonflat nonzero-volume stub: raw COUNT extra = the 15:30 stub; admission excluded exactly 1 row; admitted PASS
PASS F-ZV (raw): 19 price-moving zero-volume bars flagged, 1 flat control = NO_TRADE_FLAT, COUNT PASS, classification NOT_EVALUABLE_PROVIDER_VOLUME
PASS F-ZV (admitted): 19 price-moving zero-volume bars flagged, 1 flat control = NO_TRADE_FLAT, COUNT PASS, classification NOT_EVALUABLE_PROVIDER_VOLUME
ALL PILOT-ARTIFACT REGRESSION FIXTURES PASS
```
**4/4 fixture groups PASS.**

## Run 3 — checker candidate-2 regression suite (lineage re-run)

`fixtures/test_completeness_check_v94_regression.py` is a
byte-identical copy of the -94 suite
(`research_notes/repair_94_20261022/checker/test_completeness_check_v94.py`),
renamed only; it is run with the package's `checker/` dir on
PYTHONPATH so it exercises THIS package's copied module:

```
unshare -n env PYTHONPATH=checker \
  ~/workspace/qf35_work_20261019/venv/bin/python -B \
  fixtures/test_completeness_check_v94_regression.py
```
Tail (verbatim copy: `fixtures/v94_regression_stdout.txt`):
`18/18 checks passed`.

## Production pins (before/after, identical)

v54_forward_harness.py `ce7c902c…`, scanner_rules.py `62aa743a…`,
masterscanner_api.py `c3e95b25…`, v54_engine.py `bde32883…`,
v54_rules.py `1b55dedc…` — hashed before the first run and after
the last; identical. `forward_test/PAUSE_NEW_ENTRIES` present
throughout. The pre-existing working-tree state (UU
`forward_test/kama_shadow.json`, harness-regenerated snapshots)
was never touched; commits were made via a temp index only.

— Muse
