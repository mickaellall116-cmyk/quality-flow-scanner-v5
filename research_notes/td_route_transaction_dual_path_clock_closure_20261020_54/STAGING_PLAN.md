# -54 STAGING PLAN — dual-path clock-fixture closure

Task: QF-TD-ROUTE-TRANSACTION-DUAL-PATH-CLOCK-CLOSURE-20261020-54 r1
Spec: Issue #1 comment 6296388979 (ChatGPT dispatch).
Start convention for the ≤45 min cap: the first command of this run
(2026-10-20T16:59Z, spec fetch via the public API).

## The one authorized change (spec §1)

Driver v6 = frozen driver v5 (sha256
33681f79b6c859ede5568f4f5399c5ea5b2771741c8f5a6faedda95aac0ec018)
+ ONLY:

1. Identity/staging strings (task id, stage root `qf_td54_stage`,
   run-repo worktree `td54_wt`, pilot-stage dir `td54_pilot_stage`,
   adjudication basis 6296388979, continuation-of -53
   d0db7b2+a4bc8ce+ff9e7c4).
2. Hash gate added: driver v5 byte-identity. The §4 gate on the
   corrected actual -52 proof-results hash
   `d31e41c3469c9d8546feb04513372193273817d0864c354fb061b85eade1df52`
   is inherited from v5 unchanged (PIN_PROOF_RESULTS_52, gated in
   hash_gates as receipt52_proof_results; the file at the pinned
   -52 result commit a2b334f hashes to exactly that value — verified
   again at plan time).
3. ONE logic change: `stage_transition_clock()` — a post-receipt
   stage transition inside p1(), after the pinned-receipt gate567
   extraction and before the -19 clock suite:
   - restore the ORIGINAL r4 gate bytes (PKG11
     dispatch_gate_r4.py, sha256 b5399645…d70fa81768fd370117 —
     hash-verified before copying) over the shadow's legacy PKG11
     path, which since staging held the candidate gate;
   - the candidate gate stays at its immutable -48 package path
     (never copied over, never moved; hash re-verified in the
     transition);
   - prove the §3 preflight simultaneously (recorded in
     results.stage_transition): legacy path == b5399645…; the -17
     adapter's static path/pin resolution (PKG11 =
     dirname(adapter)/../td_policy_a_live_readiness_packet_20261017_11)
     + an EXECUTED subprocess import of the -17 adapter (its
     module-level _load_runner() pin-checks gate b5399645… and
     runner 93b911e0… for real); candidate adapter GATE_PATH parts
     + PIN_R4_GATE resolve the candidate gate 94ef967c…; candidate
     executor ADAPTER_PATH + ADAPTER_SHA256 resolve the candidate
     adapter 6980b5b3…; the -19 runner branch map (load sites:
     reproduction → PKG17 r4_dry_run_adapter; new tests → staged
     HERE live_dry_run_adapter; binding → staged HERE
     live_readiness_executor_r4) present in the byte-identical
     staged runner.

No adapter, executor, gate, candidate, matrix, comparator,
canonicalization, extractor, fixture, or expectation change.
Driver v6 sha256:
3d02de026938c2a8f05a8ad7fee35f96b6d2bfd5eb7a6dadf9dd86090bb3bcf6
Diff: driver_v5_v6.diff (324 lines unified).
Self-checks: td54_self_checks.py — 12/12 PASS
(td54_self_check_results.json): the new parse helpers resolve all
three pins/paths against the immutable sources, the runner branch
patterns are present, and the inherited corrected extractor accepts
the pinned -52 matrix and rejects a gates_passed=11 mutation.

## Staging (the -52/-53 construction, which works)

- Stage root: /home/hatch/workspace/qf_td54_stage (workspace disk).
  Inputs: proof_driver.py (= v6), network_probe.py,
  requirements_hashes.txt, integration_requirements.lock (pinned
  copies from the -46 package; lock sha256 gated to the TD lock pin
  08b38cfa… inside the driver).
- Shadow: detached git worktree of this repo created by the driver
  at $STAGE/shadow; candidate substitution byte-for-byte the
  -50/-52/-53 plan; §B preflight incl. standalone collector-blob
  proof (git show ab254c3…:…/td_min_collector.py sha256 ==
  PIN_COLLECTOR b683d277cc02a8d27…) gates execution.
- Execution: `unshare -n bash run_proof.sh` — probes must fail; venv
  `--no-index --require-hashes` from the pinned wheelhouse; freeze
  must equal the TD lock.

## Capacity pre-check (recorded pre-execution; all PASS)

See CAPACITY_RECEIPT.txt (measured 2026-10-20T17:36:56Z): free
87,298,441,216 B vs ≈2.9 GB requirement incl. margin; inodes
dynamic, 21,707,608 free reported vs ~71,641 required; stage target
absent; paths distinct.

## Sequence (one attempt, first failure stops)

Hash gates (incl. driver v5 + the §4 -52 proof-results pin) → P0
receipt → git-aware staging + blob proof → P1 (pinned-receipt
canonical comparison + corrected extractor [gate567 SATISFIED] →
stage transition + §3 preflight → -19 clock/adapter/executor matrix
+ canonical comparison → Gate-7 original-vs-candidate spot check)
→ P2 (driver integration matrix + candidate proof digest) → P3
(binding identity + CLI refusal as executed + F1 byte identity) →
post-run rehash → shadow removal. Closed families NOT rerun: the
46-trial gate suite, NLQUAL, E1, A/D/B. REQ-S2:
UNIMPLEMENTED__HARD_HOLD (recorded, untouched).
