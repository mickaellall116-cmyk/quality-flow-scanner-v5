# -54 CLOSURE MEMO — dual-path clock-fixture continuation

Task: QF-TD-ROUTE-TRANSACTION-DUAL-PATH-CLOCK-CLOSURE-20261020-54 r1
Spec: Issue #1 comment 6296388979. One offline attempt; first
material failure stopped the run. Repair minutes: 0.

## Terminal verdict

`TD_ROUTE_TRANSACTION_PROOF_HOLD__P1_CLOCK_ADAPTER_REGRESSION`

First failure: `P1_CLOCK_ADAPTER_REGRESSION` — the -19 clock suite
RAN to completion under the dual-path staging (the -53 collision is
fixed), but its canonical comparison against the accepted -19 run-2
matrix diverged at exactly one trial (below). Gate-7 spot check,
P2 and P3 did not run (stop discipline).

## What passed before the stop (executed evidence)

- Hash gates: ALL PASS — -48 package 19/19; route pins; -49
  candidates; frozen full-length pins (validator ca3bafd87e7cb4…,
  CLI constructor 3f432e7e…, entrypoint v7 84ccd2c6…); checker
  driver v2 68998a90…; driver v4 d2605bb4…; driver v5 33681f79…
  (new v6 gate); -48 candidate pins; manifest v3 canonical +
  9573118c…; the §4 gate: -52 proof_results.json ==
  d31e41c3469c9d8546feb04513372193273817d0864c354fb061b85eade1df52;
  -52 gate matrix b523b148…; TD lock 08b38cfa…; wheelhouse
  210b8273…; -46 F1 object bd550433….
- P0 receipt: PASS (accepted -50 record; v3 status live-read
  IMPLEMENTED_BY_CANDIDATE__EXECUTION_PROOF_PENDING).
- Git-aware shadow + §B preflight: PASS, incl. standalone collector
  blob proof from the staged REPO (sha256
  b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c
  == PIN_COLLECTOR).
- P1 pinned receipt: canonical comparison vs the accepted -11
  run-2 matrix IDENTICAL (751/751 cells, first_divergence null);
  corrected extractor: Gate-5/6/7 evidence SATISFIED (gates 5, 6, 7
  PASS from the receipt's per-trial facts; suite not rerun).
- STAGE TRANSITION (§1/§3 dual-path preflight): ALL PROOFS PASS
  (results.stage_transition):
  - legacy path pre-transition sha256 = candidate
    94ef967ca832faea4a4a21c666e1a310395961b6df342e098963728ce622555b
    → post-transition = original
    b53996454650dafc77e647a8497eba91beb3785fb52c13d70fa81768fd370117;
  - candidate gate at its -48 package path untouched
    (94ef967c… == gated pin);
  - -17 adapter: static resolution OK (resolved gate path == the
    legacy shadow path; PIN_R4_GATE/PIN_R4_RUNNER match the staged
    files) AND executed subprocess import OK (exit 0,
    OLD_ADAPTER_IMPORT_OK; _load_runner's pin checks passed for
    real);
  - candidate adapter: GATE_PATH parts resolve the candidate gate,
    PIN_R4_GATE (94ef967c…) == its sha256;
  - candidate executor: ADAPTER_PATH parts resolve the candidate
    adapter, ADAPTER_SHA256 (6980b5b3c887…) == its sha256;
  - runner branch map OK: staged runner byte-identical to the
    accepted -19 runner; load sites found — reproduction → PKG17
    r4_dry_run_adapter; new tests → staged live_dry_run_adapter
    (candidate); binding → staged live_readiness_executor_r4
    (candidate executor).

## The failure (verbatim executed evidence)

Clock suite: exit 0; 20 trials; 31 checks; 30 passed
(suite stdout: {"all_ok": false, "checks": 31, "passed": 30,
"trials": 20}). Canonical comparison (comparator/canonicalization
unchanged): 82 cells compared; identical = false; first divergence
$.checks_passed — accepted "31" vs candidate "30".

Raw divergent leaf cells: exactly 10, ALL inside the rollup of one
trial — `repro_old` (the historical-reproduction branch):
- $.checks_passed 31→30; $.summary.passed 31→30;
  $.summary.all_ok true→false; $.trials.repro_old.ok true→false;
  $.trials.repro_old.checks.gates_11_of_12 true→false;
- $.trials.repro_old.gates[5] PASS→FAIL (gate 6);
  gates[6] PASS→FAIL (gate 7); gates[8] PASS→UNKNOWN (gate 9);
  gates[9] PASS→UNKNOWN (gate 10); gates[10] PASS→UNKNOWN
  (gate 11).
Candidate repro_old gate vector (verbatim):
[PASS, PASS, FAIL, PASS, PASS, FAIL, FAIL, PASS, UNKNOWN, UNKNOWN,
UNKNOWN, PASS] — gate 3 FAIL is the expected historical stale
result; the trial's other receipt checks all held (decision HOLD,
stale code ACCOUNT_EVIDENCE_STALE, clock frozen 08:00, injected
clock mode). All other 19 trials — every candidate-adapter and
candidate-executor trial — matched the accepted matrix exactly
(30/31 checks).

LABELED POST-HOC OBSERVATION (characterization is adjudication's
call; no rerun was made): the divergence is confined to the
reproduction branch's gate evaluation under the ORIGINAL gate
(gates 6/7 FAIL, 9–11 UNKNOWN) inside the -11 trial machinery as
driven by the -17 adapter in this shadow — while the standalone
blob proof passed in the same shadow minutes earlier and the -52
full gate suite passed 46/46 under the candidate gate. The matrix
records only PASS/FAIL strings for the repro gates (no codes), so
the cause is not determinable from this run's evidence alone. No
candidate adapter/executor behavior diverged anywhere.

## Not run (no claims)

Gate-7 spot check: NOT RUN. P2: NOT RUN. P3: NOT RUN — the CLI
refusal was NOT executed this run; manifest v3 status
IMPLEMENTED_BY_CANDIDATE__EXECUTION_PROOF_PENDING remains accurate.
Post-run driver rehash section: not reached (failure in p1());
unchanged-state proof instead from the shell receipt (below).

## Environment / elapsed / cleanup

- One attempt inside `unshare -n` (run window 17:38:17Z →
  ~17:39:07Z): probes NETWORK_DENIED (curl exit 7); venv
  --no-index --require-hashes from the pinned wheelhouse;
  CPython 3.12.3 / pandas 2.2.3 / PMC 4.5.1; FREEZE_EQUALS_LOCK
  (08b38cfa…) — run_status DRIVER_RAN proves the freeze gate held.
- Elapsed vs ≤45 cap (start convention: spec fetch, 16:59Z):
  dispatch→results-committed ≈ 44 min (stated in the results
  commit message; verified at push). Execution stage itself:
  ~11 min. Repair minutes: 0.
- Cleanup (driver-recorded): shadow removed (remove_rc 0);
  main-repo status unchanged; run-repo head still the pre-exec
  commit a6b998d at cleanup; stage root and td54_wt worktree
  removed + pruned after the results commit.
- Unchanged state: pilot ledger post-run sha256
  7e5ccef0e5fd7e2faa744c8fe7ee646c3162fa4f72fc4a9a85317d52b5d890ed
  == ledger_before (shell receipt rehash); pinned originals
  unchanged (receipt); main tree's pre-existing UU
  forward_test/kama_shadow.json untouched.

## Prohibitions — all honored

No closed family rerun (gate suite receipt-reused; no NLQUAL/E1/
A/D/B); no candidate/matrix/comparator/canonicalization/extractor/
expectation change (driver v6 = v5 + identity strings + driver-v5
hash gate + the one authorized stage transition); nothing adopted
or re-pinned live (the -17 pin untouched — staging satisfied it);
LIVE chain never executed (candidates only inside the isolated
shadow); REQ-S2 untouched, UNIMPLEMENTED__HARD_HOLD; no vendor/
API/model calls during execution (only the pre-run read-only
public fetch of spec comment 6296388979); 0 credits/spend; no real
market data (fixtures only); no SPT-08; no backtests/performance;
no holdout; no state/ledger/production changes (V5.4 harness
untouched); no Issue #9; no Yahoo work; no second attempt; no
in-run repair.

## Commits

- Pre-execution: a6b998d6a2769d977b36aefc4b34e21b6da79e98 (driver
  v6 3d02de026938c2a8f05a8ad7fee35f96b6d2bfd5eb7a6dadf9dd86090bb3bcf6
  + v5→v6 diff + self-checks 12/12 + staging plan/capacity) —
  remote-verified ancestor of origin/main before execution.
- Results: this package's results commit (hash in the commit
  itself; verified ancestor of origin/main at push).
