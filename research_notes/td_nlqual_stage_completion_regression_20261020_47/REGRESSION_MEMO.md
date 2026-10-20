# QF-TD-NLQUAL-STAGE-COMPLETION-REGRESSION-20261020-47 r1 — REGRESSION MEMO

**Terminal verdict (verbatim, as emitted by the single offline attempt):**
`TD_NLQUAL_REGRESSION_PASS__ROUTE_CANDIDATE_AWAITING_REVIEW`

**Status:** PASS — Family C executed at last. The candidate pair is
**not** adopted or re-pinned anywhere; the route-binding candidate
record emitted with this package (spec point 6) carries status
`AWAITING_INDEPENDENT_REVIEW`. Repair minutes: **0**. One stage
assembly + one network-isolated orchestration containing the two
matrix invocations; no failure occurred, so the first-failure stop was
never triggered.

Spec: Issue #1 comment `6284741482` (adjudication of -46 +
QF-TD-NLQUAL-STAGE-COMPLETION-REGRESSION-20261020-47 r1 dispatch).
ACK was posted to Slack #qualityflowscaner before execution.

---

## 1. What this task was

-46 (commits `d0fef7c` + `8cd6b8f`) executed-proved Families A (10/10),
D (decoder contract, full) and B (E2 8/8), but Family C — the NLQUAL
28-case regression — never executed: the staged `nlqual/pilot_harness/`
omitted `verify_sources.py`, and the collector died at import
(`ModuleNotFoundError` at `td_min_collector.py:35`; 0/28 cases).
Adjudication accepted A/D/B and dispatched -47 as the regression-only
rerun with a **complete** stage. -47 changes no candidate, no source,
no fixture expectation and no classification logic — only the stage
assembly and its receipts.

## 2. Stage completeness (the point of this task)

The collector's local import closure was derived **statically (AST)**
inside the run, before any matrix execution (`IMPORT_CLOSURE.json`,
`proof_results.json#import_closure`):

- `td_min_collector.py` (`b683d277…`) requires locally:
  `rate_limiter`, `validate_input`, `verify_sources` (top-level lines
  34–35 from the sibling `pilot_harness`; `validate_input` again
  deferred at lines 529/632). No other local imports; no unclassified
  imports anywhere in the closure.
- `run_nlqual_matrix.py` (staged) requires locally: `rate_limiter`,
  `validate_input`; the collector is loaded by absolute path.
- `validate_input.py` (candidate), `rate_limiter.py`,
  `verify_sources.py`: no local imports (stdlib + numpy/pandas/PMC
  only).
- Unsatisfied local imports: **none**.

Runtime data closure, also verified before execution:
`verify_sources.ARCHIVAL_DIR` resolves relative to the **staged**
`verify_sources.py` to
`<stage>/nlqual/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1`,
and `Collector.run()` → preflight → `check_prerequisites` calls
`verify_directory(ARCHIVAL_DIR, PINNED)` on every matrix batch. The
stage therefore carries the two PINNED archival sources at exactly
that resolved path; the PINNED dict was extracted by AST from the
staged `verify_sources.py` bytes and both targets hash-match it
(`pine_backtest.py` `447a9a13…`, `scanner_rules.py` `7db282dd…` —
both `True` in the closure record).

**`verify_sources.py` is staged and hash-verified:
`a0bd2e4cdce44be5d9fcc1d7c21046391d36c9bd366a959df03bf5d19c9a79e0`**
(repo pin, `research_notes/pilot_harness/verify_sources.py`) — the
-46 omission is closed. Full inventory: `STAGE_INVENTORY.md`.

Hash gates (20, all verified pre-run in `proof_results.json`):
validator candidate `ca3bafd8…` (mechanism position + gate copy),
entrypoint candidate `442e56cc…` (gate copy; Family C drives the
collector, not the entrypoint), collector `b683d277…`, shipped
supplement `cccd5226…`, staged runner `91cfa59b…` (repo runner +
`nlqual_runner.diff` only — reproduced byte-identically), staged
supplement `7fe1fd2f…`, lock `08b38cfa…`, wheelhouse manifest
`210b8273…`, preserved body `3339c341…`, SPOT8 manifest file
`ddff040f…`, repo originals unchanged (`validate_input.py`
`1b83cdcd…`, `pilot_build.py` `257d5bb9…`, `construct_4h.py`
`d47e8df1…`, `rate_limiter.py` `06ad383d…`).

Environment: one offline orchestration inside `unshare -n`; network
probes failed as required (`NETWORK_DENIED`, curl exit 7); venv built
`--no-index --require-hashes` from the pinned wheelhouse; freeze
byte-identical to the TD lock (`FREEZE_EQUALS_LOCK`); CPython 3.12.3,
pandas 2.2.3, pandas_market_calendars 4.5.1 (`env_receipt.txt`).

## 3. Family C — NLQUAL regression: **PASS, 28/28 twice, byte-identical**

Exact command (run inside the venv, once per run; only `--out`
differs):

```
/tmp/td47/venv/bin/python /tmp/td47_stage/run_nlqual_matrix.py --mode pristine \
  --candidate-dir /tmp/td47_stage/nlqual/td_lifecycle_repair_candidate \
  --supplement /tmp/td47_stage/nlqual_supplement.json \
  --preserved-body <repo>/research_notes/twelve_data_stage0/snapshots/acquisition_state_spot8/receipts/REQ-SPT-07.rejected.bin \
  --manifest <repo>/research_notes/td_v2_spot_batch_preflight_evidence_20261014/acquisition_manifest_v2_spot8.json \
  --lock /tmp/td47_stage/integration_requirements.lock \
  --out /tmp/td47_out/nlqual_matrix_run{1,2}.json
```

- Run 1: **28/28** (`{"total": 28, "passed": 28}`), output sha256
  `2d992abc11d6d71950b6d45f360cf27afd3269f13d7eb8aa6cbe7094eb561cb0`.
- Run 2: **28/28**, output sha256
  `2d992abc11d6d71950b6d45f360cf27afd3269f13d7eb8aa6cbe7094eb561cb0`.
- **Byte-identical across runs: YES** (same digest; the two runs are
  separate processes with separate temp roots — the only persisted
  outputs are the two `--out` files; zero state leakage).
- Failed cases: **none**. All 28 cases pass, including `provenance`,
  `calendar_sanity` (mechanism sha check against the candidate),
  `REAL07_preserved_request_and_body`, and
  `ELIG08_spt08_eligible_no_dispatch` — whose internal checks confirm
  the classifier proof under the candidate mechanism (PMC 4.5.1,
  mechanism `ca3bafd8…`) with `no_dispatch: true`: **SPT-08 was NOT
  dispatched and NOT attempted**; transport never fired for it.
- Recorded environment in the matrix output: mechanism
  `ca3bafd8…` (= candidate validator), collector `b683d277…`,
  supplement `7fe1fd2f…`, lock `08b38cfa…`, PMC `4.5.1`.
- First divergence/traceback: **none** (no failure of any kind).

With this, every family of the post-acquisition route proof is now
executed evidence: E1 761/761 (-43, `01af2fee`), Families A/D/B (-46,
`d0fef7c`/`8cd6b8f`), Family C 28/28 ×2 (this task).

## 4. Route-binding candidate record

Emitted per spec point 6 (PASS-only): `ROUTE_BINDING_CANDIDATE.md` in
this package, referencing E1 at `01af2fee`, Family D + E2 at
`d0fef7c`/`8cd6b8f`, NLQUAL 28/28 twice here, both frozen candidate
hashes and all receipts. Status `AWAITING_INDEPENDENT_REVIEW`. It
adopts nothing and re-pins nothing.

## 5. Prohibitions — all honored

No vendor/API/model calls during execution (fully network-isolated
namespace; the only pre-run network use was the read-only public fetch
of the spec comment); no credits/spend; no real market data (NLQUAL
uses its preserved offline fixtures and synthetic bodies only); **no
SPT-08 dispatch** (eligibility evaluated without dispatch, as in the
original NLQUAL; the matrix's fake transport is in-process only); no
backtests/performance; no holdout access; no state/ledger/production
changes (V5.4 harness untouched — post-run re-hash in
`env_receipt.txt` confirms all pinned originals unchanged); no trading
restart; no candidate or existing-source modification (all pins
hash-identical before, in-gate, and after the run); no route adoption
or chain re-pin; no Issue #9 work; no Yahoo work; E1 / Family A /
Family D / E2 **not** repeated (spec point 5); no second attempt and
no in-run repair of any kind.

## 6. Timing

Dispatch 2026-10-20T06:27:10Z → single offline orchestration
2026-10-20T06:32–06:34Z (see `env_receipt.txt`) → package committed
and remote-verified 2026-10-20T06:39:09Z (commit `ce1adf5`).
Elapsed ≈ 12 min of the ≤30 min cap. Repair minutes: **0**.
(Correction, labeled per the -39/-40/-42/-46 precedent: the first
committed version of this memo stated ≈11 min; the true
dispatch→remote-verified elapsed is 11m59s ≈ 12 min. No other
content changed; SHA256_MANIFEST.txt regenerated for this file.)
