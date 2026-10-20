# -53 STAGING PLAN — receipt-extractor correction closure

Task: QF-TD-ROUTE-TRANSACTION-RECEIPT-EXTRACTOR-CORRECTION-CLOSURE-20261020-53 r1
Spec: Issue #1 comment 6295378552 (ChatGPT dispatch; Slack TS 1792512475.680019).
Start convention for the ≤45 min cap: the first command of this run
(2026-10-20T16:29Z, spec fetch).

## The one authorized correction

Driver v5 = frozen driver v4 (d2605bb411e8cc0f474a035e14e8f0b477113f25b
de6aac6df88f528f9f309b8) + ONLY:

1. Identity/path strings (task id, stage root `qf_td53_stage`, run-repo
   worktree `td53_wt`, pilot-stage dir `td53_pilot_stage`,
   adjudication basis 6295378552, continuation-of -52).
2. Hash gates added: driver v4 byte-identity; the pinned -52 receipt
   files byte-identity (gate matrix `b523b148042ee4012f5eae3fe96e0e5d0
   6d134c37c06adfa447e99eb37df12ac`; proof results — see the pin note
   in proof_driver_v5.py: the spec's stated full expansion matches no
   committed object; the bytes at the spec's cited immutable result
   commit `a2b334fbe0e0cc973cad9dd839b6ec10659e353a` hash to
   `d31e41c3469c9d8546feb04513372193273817d0864c354fb061b85eade1df52`
   and those bytes are what is gated).
3. P1 gate stage REPLACED by pinned-receipt reuse: the 46-trial gate
   suite is NOT rerun. The pinned -52 candidate matrix is
   canonical-compared against the accepted -11 run-2 matrix
   (comparator unchanged) and the Gate-5/6/7 evidence is read by the
   corrected extractor `extract_gate567` from the matrix's actual
   schema (below). P1 remainder (clock/adapter suite, Gate-7 spot
   check), P2, P3 are the v4 code unchanged.

Driver v5 sha256: 33681f79b6c859ede5568f4f5399c5ea5b2771741c8f5a6faedda95aac0ec018
Diff: driver_v4_v5.diff (8 hunks, unified).

## The true matrix schema (what the corrected extractor reads)

Verified against the pinned -52 gate_matrix.json:

- Top level: `{gate_revision, n_trials=46, n_pass=46, total_checks=332,
  old_spot8_state_unchanged=true, real_pilot_ledger_unchanged=true,
  trials[46]}`.
- Each trial: `{trial, status, checks[], n_checks, facts{decision,
  gates_passed, failed_gates, gate_codes, ...}}`.
- Named green trials: G01_green_dry_run and
  H05_helper_real_sanctioned_path — status PASS, check `all_12_pass`
  present, facts gates_passed=12, failed_gates=[], gate_codes=[],
  decision PASS_DRY_RUN.

The v4 extractor instead walked the JSON for a dict holding a nested
12-element `gates` list — the receipt's per-gate list lives only inside
the gate's dispatch receipt during the run; the matrix records its
AGGREGATION (the runner's `gate_summary`), never the list itself.

Static binding (self-tested): runner
`run_dispatch_gate_trials_r4.py` gate_summary: `gates =
res["receipt"]["gates"]`; `gates_passed = sum(1 for x in gates if
x["result"] == "PASS")`; `failed_gates`/`gate_codes` collect exactly
the non-PASS remainder. Candidate gate module
`dispatch_gate_r5_candidate.py::evaluate_gates` emits unique gate ids
1..12 (61 branch calls, one append per gate per evaluation). Hence
gates_passed==12 with empty failed_gates/gate_codes entails gates
5, 6, 7 each PASS.

## Extractor self-tests (pre-execution, in the clear)

extractor_self_tests.py against the hash-verified pinned matrix:
POSITIVE accepted (gates 5/6/7 PASS, all_12_pass true); negatives all
rejected fail-closed: gates_passed=11; nonempty failed_gates/gate_codes;
missing all-12 check; wrong status; wrong decision; missing facts;
top-level n_pass=45. Static-binding tests pass. 10/10 PASS
(extractor_self_test_results.json).

## Staging (the -52 construction, which works)

- Stage root: /home/hatch/workspace/qf_td53_stage (workspace disk).
  Inputs: proof_driver.py (= v5), network_probe.py,
  requirements_hashes.txt, integration_requirements.lock (pinned
  copies from the -46 package; lock sha256 gated to the TD lock pin
  inside the driver).
- Shadow: detached git worktree of this repo created by the driver at
  $STAGE/shadow; candidate substitution byte-for-byte the -50/-52
  plan; §B preflight incl. standalone collector-blob proof
  (git show ab254c3…:…/td_min_collector.py sha256 == PIN_COLLECTOR
  b683d277cc02a8d27…) gates execution.
- Execution: `unshare -n bash run_proof.sh` — probes must fail; venv
  `--no-index --require-hashes` from the pinned wheelhouse; freeze
  must equal the TD lock.

## Capacity pre-check (recorded pre-execution; all PASS)

- Filesystem /dev/mapper/rv (btrfs, /home/hatch): free
  87,300,009,984 B (df -B1, 2026-10-20T16:40Z).
- Requirement (measured, -52 basis): checkout 485,741,263 B
  (td53_wt du -sb) + venv allowance 174 MiB + outputs 64 MiB
  ≈ 735 MB; + 2 GiB margin → ≈ 2.9 GB ≪ 87.3 GB free. PASS.
- Inodes: btrfs dynamic (stat -f: 21,708,151 total / 21,313,479 free
  reported; no fixed pool) vs ~71,607 required (11,607 checkout files
  + 50k margin). PASS.
- Stage target absent at plan time; stage / run-repo / main-repo
  paths distinct.

## Sequence (one attempt, first failure stops)

Hash gates → P0 receipt → git-aware staging + blob proof → P1
(receipt canonical comparison + corrected extractor + clock/adapter
suite + Gate-7 spot check) → P2 → P3 → post-run rehash → shadow
removal. REQ-S2: UNIMPLEMENTED__HARD_HOLD (recorded, untouched).
