# -53 CLOSURE MEMO — receipt-extractor correction

Task: QF-TD-ROUTE-TRANSACTION-RECEIPT-EXTRACTOR-CORRECTION-CLOSURE-20261020-53 r1
Spec: Issue #1 comment 6295378552 (Slack TS 1792512475.680019).
Pre-execution commit: d0db7b26f2b33a6a08e0f9d7e9e1dc82d3af47ec.

## Terminal verdict

`TD_ROUTE_TRANSACTION_PROOF_HOLD__P1_CLOCK_SUITE_RUN`

The extractor correction is PROVEN and the -52 stop point is closed:
the pinned -52 receipt verified identical and the corrected extractor
produced the Gate-5/6/7 evidence from it. The run then stopped at the
next never-before-executed step, the P1 clock/adapter suite, whose
loader refuses the staged candidate gate on an r4 pin (below).

## What was executed and passed

- Hash gates (driver, in-attempt): ALL PASS — -48 package 19/19;
  route pins 3/3; -49 candidates 2/2; frozen full-length pins
  (validator ca3bafd87e7cb4…, CLI constructor 3f432e7e…, entrypoint
  84ccd2c6…); frozen checker driver v2 68998a90… byte-identical;
  frozen driver v4 d2605bb4… byte-identical; manifest v3 canonical
  9573118c…; -52 receipt gate matrix b523b148… (== spec pin);
  TD lock 08b38cfa…; wheelhouse manifest 210b8273…; -46 F1 object
  bd550433….
- PIN NOTE (disclosed): the spec states the -52 proof-results pin as
  d31e41c3b9f1128d741…; the bytes at the spec's own cited immutable
  result commit a2b334f hash to
  d31e41c3469c9d8546feb04513372193273817d0864c354fb061b85eade1df52
  (prefix d31e41c3 matches; the stated full expansion matches no
  committed object — the corrupted-expansion pattern disclosed in
  -49). The driver gates the actual committed bytes; the gate passed.
- P0 receipt: PASS (accepted -50 record; v3 status live-read
  IMPLEMENTED_BY_CANDIDATE__EXECUTION_PROOF_PENDING).
- Staging §B preflight: PASS — git-aware shadow on the workspace
  disk; standalone collector-blob proof from the staged REPO:
  sha256 b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c
  == PIN_COLLECTOR.
- P1 gate receipt (suite NOT rerun, per spec): canonical comparison
  of the pinned -52 candidate matrix vs the accepted -11 run-2
  matrix — IDENTICAL, 751/751 cells, first_divergence null.
- P1 Gate-5/6/7 evidence (CORRECTED extractor on the pinned
  receipt): SATISFIED. G01_green_dry_run and
  H05_helper_real_sanctioned_path both record status PASS, check
  all_12_pass, facts gates_passed=12, failed_gates=[],
  gate_codes=[], decision PASS_DRY_RUN; top level 46/46, 332 checks,
  old_spot8_state_unchanged=true, real_pilot_ledger_unchanged=true.
  Extractor output: gate5 PASS, gate6 PASS, gate7 PASS,
  all_12_pass true. The -52 HOLD__P1_GATE567_NOT_EVIDENCED point is
  closed on executed evidence.

## Extractor schema finding + self-tests (pre-execution record)

True schema and static binding: see STAGING_PLAN.md. Self-tests
(extractor_self_tests.py, committed pre-execution): 10/10 PASS —
positive on the pinned matrix; negatives rejected fail-closed
(gates_passed=11; nonempty failed_gates/gate_codes; missing all-12
check; wrong status; wrong decision; missing facts; top-level
n_pass=45); static binding verified (runner aggregation lines;
unique gate ids 1..12 in evaluate_gates).
Driver v5 sha256: 33681f79b6c859ede5568f4f5399c5ea5b2771741c8f5a6faedda95aac0ec018
(v4→v5 diff: driver_v4_v5.diff, 8 hunks — identity/paths, receipt
hash gates, extractor + receipt-reuse P1 head; nothing else).

## First failure (verbatim) — P1_CLOCK_SUITE_RUN

The clock/adapter suite subprocess exited 1 before producing a
matrix. Stderr tail (recorded in proof_results.json):

```
File ".../td_status_query_placement_20261017_17/r4_dry_run_adapter.py", line 43, in <module>
    R = _load_runner()
  File ".../td_status_query_placement_20261017_17/r4_dry_run_adapter.py", line 34, in _load_runner
    raise RuntimeError("PIN_MISMATCH:r4_gate")
RuntimeError: PIN_MISMATCH:r4_gate
```

Characterization (labeled post-hoc; adjudication's call): the -19
clock runner loads the -17 placement adapter
(td_status_query_placement_20261017_17/r4_dry_run_adapter.py), which
at import time loads the dispatch gate and pin-checks it against the
ORIGINAL r4 gate bytes. In the shadow, the -11 gate path holds the
r5 candidate (the staging plan's designed substitution), so the
-17 module's r4 pin refuses — fail-closed, before any trial ran.
This step has never executed in any proof run (-49 stopped at P0;
-50 at the gate regression; -52 at gate567), so the interaction is
newly reached, not newly introduced. The accepted -19 run-2 matrix
was recorded with the r4 gate in place. Whether the clock regression
should run against the original gate bytes (its subject is the
adapter/executor clock binding) or the -17 pin belongs to the chain
an adoption would re-pin is adjudication's question. No candidate
defect is indicated: the pin check detected exactly the substitution
it exists to detect.

## Not run (stop discipline)

- P1 Gate-7 spot check (follows the clock suite inside p1()).
- P2 (driver integration suite + proof-digest presence).
- P3 (binding identity; CLI refusal as executed; F1 byte-identity).
  The CLI refusal remains IMPLEMENTED_BY_CANDIDATE__EXECUTION_PROOF_PENDING
  in manifest v3 — still accurate; no execution claim is made.

## Environment / elapsed / state

- One offline attempt (unshare -n): probes NETWORK_DENIED (curl
  exit 7); venv --no-index --require-hashes from the pinned
  wheelhouse; CPython 3.12.3 / pandas 2.2.3 / PMC 4.5.1;
  FREEZE_EQUALS_LOCK (08b38cfa…). Run window 16:42:43Z→16:43:34Z.
- Elapsed vs ≤45 cap: execution start (first command of the run,
  spec fetch) 2026-10-20T16:29Z → results remote-verified ≈16:50Z
  ≈ 21 min. Repair minutes beyond the authorized extractor
  correction: 0.
- Post-run: driver rehash confirms pinned originals unchanged;
  pilot ledger 7e5ccef0… = pre-run value (also in env_receipt.txt).
- Cleanup: driver removed the shadow worktree (remove_rc 0);
  main-repo status unchanged; run-repo head still the pre-execution
  commit; stage root and the td53_wt worktree removed after the
  results commit (worktree list pruned — verified in the delivery
  record). Main tree untouched; its pre-existing
  UU forward_test/kama_shadow.json merge state intact.

## Prohibitions honored

P1 gate suite NOT rerun (receipt reuse mandatory — honored); no
candidate/checker-logic change beyond the extractor step (v5 diff is
the record); nothing adopted or re-pinned; LIVE chain never executed
(candidates only inside the isolated shadow); E1 and full A/D/B/NLQUAL
not repeated; REQ-S2 untouched — UNIMPLEMENTED__HARD_HOLD; no
vendor/API/model calls during execution (pre-run read-only spec
fetches only); 0 credits/spend; fixtures only, no real market data;
no SPT-08; no backtests/performance; no holdout; no state/ledger/
production changes (V5.4 harness untouched); no Issue #9; no Yahoo
work; no second attempt; no in-run repair.
