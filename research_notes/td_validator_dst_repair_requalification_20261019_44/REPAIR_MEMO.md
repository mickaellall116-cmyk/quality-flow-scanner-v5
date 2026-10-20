# QF-TD-VALIDATOR-DST-REPAIR-REQUALIFICATION-20261019-44 r1 — REPAIR MEMO

**Terminal label (verbatim, as emitted):**
`TD_VALIDATOR_DST_REPAIR_HOLD__UNEXPECTED_ERROR`

**Characterized first-failure key (post-hoc, see §3):**
`E2_F3_CONSTRUCT_4H_ENDS_SERIES_OBJECT_DTYPE`

**Status:** HOLD — awaiting independent review. The candidate is NOT
adopted and NOT re-pinned anywhere. The accepted -41 supplement and the
-41 pin chain are untouched. Repair minutes beyond the single authorized
candidate build: **0**. One candidate build, one offline attempt,
first-failure stop honored (families stopped at B/F3; family C not run).

Spec: Issue #1 comment `6282707139` (adjudication of -43 +
QF-TD-VALIDATOR-DST-REPAIR-REQUALIFICATION-20261019-44 r1 dispatch).

---

## 1. The candidate

- File (this package): `validate_input_v3_dstfix.py`
- SHA-256: `ca3bafd87e7cb439d538ddf924aa08a029dd2c9bb32b485f61acbeea91429cc6`
- Separately versioned copy of the pinned v2 validator
  (`research_notes/pilot_harness/validate_input.py`, sha256
  `1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58`).
  The original was **never edited**: hash verified `1b83cdcd…` before the
  run, inside the run's hash gates, and again after the run
  (see `env_receipt.txt`, pre-run hash gates + post-run re-hash).
- Exact diff: `candidate.diff` (this package). It contains ONLY:
  1. the docstring version-identification block (v3, task id, the v2 hash
     it supersedes for review only), and
  2. the V8 window-enumeration loop: civil-date enumeration localized to
     `America/New_York` (`_civil_day = ws.date()` …
     `pd.Timestamp(_civil_day).tz_localize(NY)`) replacing the absolute
     24h `day += pd.Timedelta(days=1)` stepping of tz-aware day keys.
  Function API, error taxonomy (V1–V11), schemas, and the calendar
  mechanism (`xnys_schedule`, `expected_1h_starts`) are unchanged —
  proven structurally in Family A (§2).

## 2. Family results

Environment (one offline attempt, `unshare -n`, network probes failed as
required — see `env_receipt.txt`): CPython 3.12.3, pandas 2.2.3,
pandas_market_calendars 4.5.1; venv built `--no-index --require-hashes`
from the pinned wheelhouse (manifest `210b8273…`); freeze byte-identical
to the TD lock `08b38cfa…` (`FREEZE_EQUALS_LOCK`). All hash gates passed
pre-run (construct_4h `d47e8df1…`, pilot_build `257d5bb9…`, original
validator `1b83cdcd…`, fetch_4h `2a4994a2…`, collector `b683d277…`,
candidate `ca3bafd8…`). The proof was bound explicitly to the candidate:
loaded by absolute path via importlib and registered in
`sys.modules["validate_input"]` before `construct_4h` was imported — no
import-precedence ambiguity. -43 E1 (761 dates) was NOT repeated, per
spec (calendar code unchanged — proven by the Family A AST check).

### Family A — structural: **PASS (all checks)**
- Defect line absent; civil-date enumeration present.
- Public API unchanged (AST argument signatures identical).
- AST bodies identical to v2 for **every** top-level function/class
  except `validate` itself; `xnys_schedule` and `expected_1h_starts`
  AST-identical (calendar mechanism unchanged).
- Midnight probe: during a `validate()` call over the F3 DST-spanning
  window (2025-03-07 → 2025-03-14), all **56** recorded `xnys_schedule`
  day arguments were local midnights (00:00:00 America/New_York).

### Family B — constructor route (-43 E2 rerun vs candidate)
- **F1 (regular day): PASS** — 2 bars, cleared vs `resample_4h`
  byte-identical.
- **F2 (early close): PASS** — 1 bar, byte-identical.
- **F3 (DST-spring week): FIRST FAILURE — STOP.** Validation under the
  candidate **PASSED** (the `VALIDATOR_DAY_ENUMERATION_DST_DRIFT` defect
  is repaired: no false V8; execution proceeded into construction).
  Construction then crashed in `construct_4h` — see §3. Verbatim error:
  `AttributeError: Can only use .dt accessor with datetimelike values`
  at `construct_4h.py:141` (`cends.dt.tz`), reached via the
  pilot_build-identical `validated_ends` carry (driver traceback in
  `proof_results.json`).
- **F4–F8: NOT RUN** (first-failure stop).

### Family C — NLQUAL 28-case regression: **NOT RUN**
Stopped before Family C per first-failure protocol. The staged fixtures
for the run are preserved in this package for the record:
`nlqual_supplement_staged.json` (NL candidate supplement `9c712330…`
with ONLY `calendar.mechanism_module_sha256` re-pinned to the candidate
hash — a staged test fixture, not an adoption) and
`nlqual_runner.diff` (the accepted `run_nlqual_matrix.py` with ONLY its
two embedded mechanism-hash expectations updated to the candidate hash).
The regression remains outstanding and must accompany any re-dispatch.

## 3. Root cause of the F3 failure (post-hoc static analysis; NO rerun)

The driver's `cleared_route` replicates `pilot_build.py:128-130`
byte-for-byte in behavior: `validated_ends = pd.Series({pd.Timestamp(k):
pd.Timestamp(v) for k, v in ends_map.items()})` from the validator
report's ISO-string `interval_ends`. ISO strings from a DST-spanning
window carry mixed fixed offsets (`-05:00` before 2025-03-09, `-04:00`
after), so the reconstructed Series cannot unify to one datetimelike
dtype and stays **object** dtype (verified post-hoc in the pinned env:
mixed-offset map → `dtype: object`; single-offset map →
`datetime64[ns, UTC-05:00]`). `construct_4h` then raises AttributeError
on `cends.dt` — outside the `(TypeError, ValueError)` pair `pilot_build`
catches, so the real cleared entrypoint would crash identically.

Conclusions:
- This is a **second, distinct latent defect** in the cleared route's
  ends-carrying step (`pilot_build`/`construct_4h` interface), **not**
  a defect of the candidate validator and **not** a driver artifact:
  the driver's construction is the entrypoint's own code shape.
- It was previously **masked** by the validator DST defect: with v2,
  any DST-spanning window failed validation (V8) before construction
  was reached. The candidate removed the mask.
- The candidate's assigned repair is therefore **proven on its own
  terms** (Family A full PASS; F3 validation passes; F1/F2
  byte-identical), but the route-level requalification cannot PASS
  until the ends-carrying defect is separately addressed under its own
  authorization. Per this task's zero-repair rule, nothing was fixed
  and nothing was rerun.

## 4. Confirmations

No vendor calls; no model/API calls (the only network use was the
read-only public fetch of the spec comment before execution; the proof
ran in a network-isolated namespace with all probes failing); no spend
and no credits; no holdout access; no performance calculation; no
production change (V5.4 harness and all existing sources untouched —
original validator hash identical before and after); no trading
restart; no route adoption; the candidate is not re-pinned in any
supplement, gate, driver, or chain. E2 inputs were synthetic fixtures;
no real market data was used. Exact command: `unshare -n bash
run_proof.sh` (script in this package), single execution, exit 0
(driver records the HOLD verdict in `proof_results.json`).

## 5. Timing

Dispatch ~2026-10-20T03:59Z; single offline execution inside
`env_receipt.txt` run window; package remote-verified shortly after
(elapsed vs the ≤45-min cap and the commit hash are stated in the
WORK RESULT post; repair minutes beyond the candidate build: 0).
