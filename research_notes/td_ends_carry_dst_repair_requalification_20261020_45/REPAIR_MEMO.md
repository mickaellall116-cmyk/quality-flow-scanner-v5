# QF-TD-ENDS-CARRY-DST-REPAIR-REQUALIFICATION-20261020-45 r1 — REPAIR MEMO

**Terminal label (verbatim, as emitted):**
`TD_ENDS_CARRY_DST_REPAIR_HOLD__UNEXPECTED_ERROR`

**Characterized first-failure key (post-hoc, see §3):**
`FAMILY_D_DRIVER_CHECK_VALUES_ITERATION_TZ_STRIPPED` — the failure is in
this task's own proof driver, **not** in the entrypoint candidate.

**Status:** HOLD — awaiting independent review. Neither candidate is
adopted or re-pinned anywhere. The accepted -41 supplement and pin
chain are untouched. Repair minutes beyond the single authorized
candidate build: **0**. One candidate build, one offline attempt,
first-failure stop honored (Family D stopped at its first map check,
inside the driver's own inspection helper; Families B and C not run).
The PASS-only route-binding candidate record (spec point 8) was **not**
emitted.

Spec: Issue #1 comment `6283646014` (adjudication of -44 +
QF-TD-ENDS-CARRY-DST-REPAIR-REQUALIFICATION-20261020-45 r1 dispatch).

---

## 1. The candidate

- File (this package): `pilot_build_v6_dstfix.py`
- SHA-256: `442e56cc16bbbb7ba8f3a62910d92bfcd07d85d0bb88ca2346d26b0bdcd2cba6`
- Separately versioned copy of the pinned entrypoint
  (`research_notes/pilot_harness/pilot_build.py`, sha256
  `257d5bb99bcbae50442491b71429abb6b37b8c5cbcd1e4bf93b6010ad9e5a508`).
  The original was **never edited**: hash verified `257d5bb9…` before
  the run, inside the run's hash gates, and again after the run (see
  `env_receipt.txt`). `construct_4h.py` (`d47e8df1…`) and the original
  validator (`1b83cdcd…`) likewise verified unchanged before and after.
- Exact diff: `candidate.diff` (this package). It contains ONLY:
  1. the docstring version-identification block (v6 candidate, task id,
     the v5 hash it supersedes for review only), and
  2. the `interval_ends` decoder: a new `_decode_validated_ends()`
     helper plus its call site, moved inside `main()`'s existing
     `except (TypeError, ValueError)` construction block. The decoder
     parses each report key/value as an instant, explicitly rejects
     tz-naive or malformed keys/values (no silent localization),
     canonicalizes aware mixed-offset instants through UTC into
     homogeneous `America/New_York` DatetimeIndexes, and fails closed
     on duplicate canonical key instants. CLI/API, validation,
     construction, schemas, error meanings, calendar code, and all
     other logic are unchanged — proven structurally in Family A (§2).
- Bound pair: validator candidate `ca3bafd8…` (-44, byte-identical
  file, hash-gated) + this entrypoint candidate + unchanged
  constructor `d47e8df1…` + unchanged reference resampler `2a4994a2…`;
  lock/freeze `08b38cfa…`, wheelhouse manifest `210b8273…`, CPython
  3.12.3, PMC 4.5.1 (see `env_receipt.txt`, `proof_results.json`).

## 2. Family results

Environment (one offline attempt, `unshare -n`, network probes failed
as required — see `env_receipt.txt`): CPython 3.12.3, pandas 2.2.3,
pandas_market_calendars 4.5.1; venv built `--no-index
--require-hashes` from the pinned wheelhouse (manifest `210b8273…`);
freeze byte-identical to the TD lock `08b38cfa…`
(`FREEZE_EQUALS_LOCK`). All hash gates passed pre-run (construct_4h
`d47e8df1…`, pilot_build `257d5bb9…`, original validator `1b83cdcd…`,
fetch_4h `2a4994a2…`, collector `b683d277…`, validator candidate
`ca3bafd8…`, entrypoint candidate `442e56cc…`). Bindings were explicit:
candidate validator loaded by absolute path and registered in
`sys.modules["validate_input"]`, pinned constructor registered in
`sys.modules["construct_4h"]`, **before** the entrypoint candidate was
loaded, so the candidate's own imports resolved to the bound modules.
-43 E1 (761 dates) was NOT repeated, per spec (calendar mechanism
unchanged — the validator candidate is the byte-identical -44 file).

### Family A — structural: **PASS (all 10 checks)**
- v5 object-dtype rebuild absent; `_decode_validated_ends` present.
- AST discipline vs pinned v5: `main()` argument signature identical;
  the **only** added top-level item is `_decode_validated_ends`;
  nothing removed; the **only** changed top-level body is `main()`.
- The decode call sits inside `main()`'s existing
  `except (TypeError, ValueError)` block whose handler returns 2 —
  decoder failures route through the entrypoint's existing handled
  construction path (CONSTRUCTION FAILED, exit 2).
- Binding identity checks: the loaded entrypoint candidate's
  `validate`/`ValidationError` **are** the candidate validator's, and
  its `construct_4h` **is** the pinned constructor's.

### Family D — decoder contract proof: **STOPPED AT FIRST CHECK (driver defect)**
The first check (`single_offset_real_report`, a real candidate-
validator report map for 2025-01-08) raised, inside the proof driver's
own `_instants()` inspection helper:

```
TypeError: Cannot convert tz-naive Timestamp, use tz_localize to localize
```

at `proof_driver.py` line 214 (`_instants(list(s.values))`), before any
decoder assertion for that map could complete. No Family D counters
were recorded (`family_d_contract: null` in `proof_results.json`).
Per the first-failure protocol the run stopped; nothing was repaired
and nothing was rerun.

### Family B — E2 F1–F8 rerun: **NOT RUN** (stopped at Family D).
### Family C — NLQUAL 28-case regression: **NOT RUN** (requires E2 8/8 first).
The staged NLQUAL fixtures are preserved in this package for the
record: `nlqual_supplement_staged.json` (NL candidate supplement
`9c712330…` with ONLY `calendar.mechanism_module_sha256` re-pinned to
the validator candidate hash — a staged test fixture, not an adoption)
and `nlqual_runner.diff` (the accepted `run_nlqual_matrix.py` with ONLY
its two embedded mechanism-hash expectations updated to the candidate
hash) — both carried over byte-identical from the -44 staging.

## 3. Root cause of the Family D failure (post-hoc analysis; NO rerun)

The defect is in this task's proof driver, not in the candidate:

- In pandas 2.2.3, iterating `Series.values` of a tz-aware
  `datetime64[ns, America/New_York]` Series yields **naive
  `numpy.datetime64`** values (the UTC-normalized instants with the
  timezone stripped). The driver's `_instants()` helper did
  `pd.Timestamp(t).tz_convert("UTC")` over `list(s.values)`, and
  `tz_convert` on a tz-naive Timestamp raises exactly the recorded
  `TypeError`. Iterating the Series itself (or `.array`) yields proper
  tz-aware Timestamps. (Verified post-hoc in the pinned env —
  `POST_HOC_DIAGNOSTIC.txt`.)
- The candidate decoder's output for the same input was verified
  post-hoc to be exactly the documented contract: index and values
  both `datetime64[ns, America/New_York]`, `Series.dt.tz` ==
  `America/New_York` — the property `construct_4h` requires at its
  `cends.dt.tz` access (`construct_4h.py:141`). The exception was
  raised by the driver **while inspecting** a correctly-typed Series;
  no decoder assertion had failed, and none had yet completed either —
  the contract proof therefore remains **unproven**, not passed and
  not failed on its merits.
- Consequence: the candidate's assigned repair is structurally sound
  and its output type contract is post-hoc-verified, but the
  requalification cannot PASS on a stopped attempt. Any re-dispatch
  needs the driver helper fixed (iterate the Series / `.array`, never
  `.values`) — a driver change, not a candidate change — and a full
  rerun from Family D (spec point 5 requires the E2 family rerun in
  one invocation in any case, because the entrypoint bytes are new).

## 4. Confirmations

No vendor calls; no model/API calls during execution (the only network
use was the read-only public fetch of the spec comment before
execution; the proof ran in a network-isolated namespace with all
probes failing — `NETWORK_DENIED`, curl exit 7); no spend and no
credits; no SPT-08; no holdout access; no performance/backtest work;
no production/state/ledger change (V5.4 harness and all existing
sources untouched — every pinned original hash-identical before and
after the run); no trading restart; no route adoption; neither
candidate is re-pinned in any supplement, gate, driver, or chain.
E2 inputs were synthetic fixtures; no real market data was used.
Exact command: `unshare -n bash run_proof.sh` (script in this
package), single execution; the driver recorded the HOLD verdict in
`proof_results.json`.

## 5. Timing

Dispatch ~2026-10-20T04:58Z; single offline execution
2026-10-20T05:09:52Z → 05:10:13Z (see `env_receipt.txt`); elapsed
dispatch → remote-verified package and repair minutes (0 beyond the
candidate build) are stated in the WORK RESULT post.
