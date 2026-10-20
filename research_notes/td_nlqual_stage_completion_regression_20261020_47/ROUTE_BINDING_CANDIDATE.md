# ROUTE-BINDING CANDIDATE — post-acquisition TD construction route

**Status: `AWAITING_INDEPENDENT_REVIEW`**

Research-only record, emitted on the complete PASS of
QF-TD-NLQUAL-STAGE-COMPLETION-REGRESSION-20261020-47 r1 per spec
point 6 (Issue #1 comment `6284741482`), as originally required by
-45/-46. **This record adopts nothing and re-pins nothing.** The
accepted -41 supplement and pin chain are untouched; adoption of the
candidate pair remains a separate adjudicated act.

## The candidate pair (frozen)

| Role | File (package of origin) | SHA-256 |
|---|---|---|
| Validator candidate | `validate_input_v3_dstfix.py` (-44 package) | `ca3bafd87e7cb439d538ddf924aa08a029dd2c9bb32b485f61acbeea91429cc6` |
| Entrypoint candidate | `pilot_build_v6_dstfix.py` (-45 package) | `442e56cc16bbbb7ba8f3a62910d92bfcd07d85d0bb88ca2346d26b0bdcd2cba6` |

Unchanged route members they bind against: constructor
`construct_4h.py` `d47e8df1…`, collector `td_min_collector.py`
`b683d277…`, reference resampler `fetch_4h.py` `2a4994a2…`.

## Executed evidence chain (complete)

| Leg | Evidence | Where |
|---|---|---|
| E1 — calendar equivalence, 761/761 | -43 proof, PASS | commit `01af2fee…` (`td_constructor_equivalence_proof_20261019_43`) |
| Family A — structural/binding, 10/10 | -46 rerun, PASS | commits `d0fef7c` / `8cd6b8f` (`td_ends_carry_proof_harness_rerun_20261020_46`) |
| Family D — ends-decoder contract, full PASS | -46 rerun, PASS | same |
| Family B — E2 construction fixtures, 8/8 | -46 rerun, PASS | same |
| Family C — NLQUAL regression, **28/28 twice, byte-identical** (output sha256 `2d992abc11d6d71950b6d45f360cf27afd3269f13d7eb8aa6cbe7094eb561cb0`, both runs) | -47, PASS | this package (`td_nlqual_stage_completion_regression_20261020_47`) |

## Environment / receipts

CPython 3.12.3, pandas 2.2.3, pandas_market_calendars 4.5.1; TD lock
/ freeze `08b38cfa…`; wheelhouse manifest `210b8273…`; network
isolated (`unshare -n`, probes denied). Source, environment and
stage receipts: -43/-46 packages above and this package's
`REGRESSION_MEMO.md`, `STAGE_INVENTORY.md`, `IMPORT_CLOSURE.json`,
`proof_results.json`, `env_receipt.txt`, `freeze.txt`,
`SHA256_MANIFEST.txt`.

Adoption, supplement re-pinning, and any change to the live readiness
chain remain **separate adjudicated acts** — none is performed or
implied by this record.
