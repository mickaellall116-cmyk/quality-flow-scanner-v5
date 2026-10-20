# -55 BRANCH MAP — branch-isolated clock proof and final remainder

Task: QF-TD-ROUTE-TRANSACTION-BRANCH-ISOLATED-FINAL-CLOSURE-20261020-55 r1
Spec: Issue #1 comment 6297990771 (ChatGPT dispatch, 2026-10-20T18:19:49Z).
Start convention for the ≤45 min cap: first command of this run
2026-10-20T18:28Z (spec fetch via the public API). One offline
attempt; first material failure stops.

## Driver v7 (the only derived artifact)

- proof_driver_v7.py sha256:
  bb375b76ddd49af88ebc085ec2c09cef806e67c83a3e21f0596d793d4b26d656
- Derived ONLY from frozen driver v6 (sha256
  3d02de026938c2a8f05a8ad7fee35f96b6d2bfd5eb7a6dadf9dd86090bb3bcf6,
  -54 package commit 87dfd68). Exact diff: driver_v6_v7.diff
  (483 lines, sha256
  8fe9d8254058309cfa38776066205fb52fbd7ebb6b7052c7ad922ed3fce240e7).
- Delta, nothing else: (a) identity/staging strings (task id, stage
  qf_td55_stage, run-repo worktree td55_wt, pilot stage
  td55_pilot_stage, adjudication basis 6297990771, continuation-of
  -54 87dfd68+c026fe7); (b) hash gate pinning driver v6; (c) the
  branch-isolated clock stage (below). No candidate, accepted
  runner, matrix, comparator, canonicalization, extractor, or
  expectation changes — proven by td55_self_checks.py 28/28 PASS
  (td55_self_check_results.json): every v6 function outside the
  authorized set is byte-identical (p3 and build_shadow_gitaware
  differ only by the pilot-stage dir rename), and the scoped
  comparator passes synthetic partition/scoping tests against the
  real accepted run-2 matrix.

## Branch map (membership fixed before execution)

Run repo: /home/hatch/workspace/td55_wt (detached worktree at
94648c8298cef0bc1ecada842054511622754b5e = origin/main at staging).
Both branches are detached git worktrees of the run repo at that
same HEAD, created by the driver, disposed of by the driver:

- ORIGINAL branch: $STAGE/shadow_original — untouched committed
  artifacts at their accepted paths; NO candidate substitution, NO
  stage transition. Used only to execute the accepted runner's
  repro_old historical branch.
- CANDIDATE branch: $STAGE/shadow_candidate — the -54 staging
  byte-for-byte (candidate substitution + §B preflight + the v6
  stage_transition_clock, unchanged). Used for the other 19 trials
  and the remaining transaction proof (Gate-7 spot check, P2, P3 —
  the v6 code unchanged).

## Fail-closed provenance pins (spec §4, verified in-driver pre-use)

- ORIGINAL: gate b5399645… (full PIN_R4_GATE_LEGACY), driver
  5fed4524…, supplement 3cbdbf63…, mechanism 1b83cdcd…, proof
  36bc3a89… (full values computed from the accepted files at
  derivation time and pinned as constants in v7; prefixes asserted
  against the spec; full values recorded in proof_results.json).
- CANDIDATE: gate 94ef967c…, driver d11c6b58…, supplement
  55ad6f40…, mechanism ca3bafd8…, proof 6b030c62…, adapter
  6980b5b3…, executor bbc23616….
- Both accepted runner copies byte-identical (and == the accepted
  PKG19 runner); resolved paths recorded; no path overlap; no
  symlinks at roots or original pin files; branch heads == run-repo
  HEAD before execution.

## Adjudication (spec §5, no matrix fabricated or altered)

- ORIGINAL: only repro_old compared cell-for-cell to accepted
  run-2, plus its rollup contribution (checks true/total + ok).
- CANDIDATE: the other 19 trials compared cell-for-cell to
  accepted run-2; repro_old explicitly excluded from the
  candidate-side verdict.
- Exact trial-name partition required: {repro_old} + 19 = all 20,
  no omission/overlap, in both branch outputs.
- Real pilot ledger unchanged in both branches (sha256 vs run repo).
- Upstream receipts reused; the 46-trial gate suite, extractor
  tests, E1, A/D/B/NLQUAL are NOT rerun (spec §6).

## Execution

`unshare -n bash run_proof.sh` — network probes must fail; venv
`--no-index --require-hashes` from the pinned wheelhouse; freeze
must equal the TD lock (08b38cfa…). Stage inputs (proof_driver.py =
v7, network_probe.py, requirements_hashes.txt,
integration_requirements.lock) are pinned copies from the -46
package, lock hash-gated inside the driver.

## Capacity pre-check (2026-10-20T18:32Z, PASS)

Workspace disk free 86,055,059,456 B vs ≈3.5 GB requirement (two
worktree checkouts ≈0.51 GB each + venv ≈0.17 GB + stage/output,
with margin). Stage target /home/hatch/workspace/qf_td55_stage
absent pre-run. Paths distinct.

## Controls

Research-only; REQ-S2 hard HOLD; no adoption/live repin/production
change; V5.4 entries PAUSED (sentinel untouched); no vendor/API/
model calls or spend; no real data, SPT-08, holdout, backtest,
trading, or Yahoo work. Terminal PASS only designates the route
research-adoption-ready with S2 still held; it adopts nothing.
