# -52 r1 — continuation memo (spec: Issue #1 comment 6292815205)

Task: `QF-TD-ROUTE-TRANSACTION-WORKSPACE-STAGE-CONTINUATION-20261020-52` r1.
Terminal verdict: **TD_ROUTE_TRANSACTION_PROOF_HOLD__P1_GATE567_NOT_EVIDENCED**
One placement-only correction + ONE offline continuation attempt; first
material failure stopped the run; repair minutes: **0**.

Commits: pre-execution `ebf8a4c35ce0933c8cac47283da2a5b888f70789`
(driver v4 + exact v3→v4 diff + capacity receipt + staging plan, committed
BEFORE execution per spec §B.3); results commit = the commit carrying this
memo (see SHA256_MANIFEST.txt / git log).

## The correction (spec §B — placement only)
Driver v4, sha256 `d2605bb411e8cc0f474a035e14e8f0b477113f25bde6aac6df88f528f9f309b8`,
derived from FROZEN driver v3 (`651385415a46dbc72c080b6c8921ced0de8170d30b5932642fb2daa90877988d`).
Exact diff in `driver_v3_v4.diff` (5 hunks, 25 +/- lines): stage root
`/tmp/td51_stage` → `/home/hatch/workspace/qf_td52_stage`; run-repo
worktree `td51_wt` → `td52_wt`; task identity/provenance strings updated
to this spec (6292815205) and its -51 continuation basis; pilot-stage
directory renamed inside the shadow. NO logic, gate, comparator,
canonicalization, fixture, or expectation change. Checker v2
(`68998a90…`) and every candidate inherited byte-identical.
Capacity/inode preflight (CAPACITY_RECEIPT.txt, committed pre-execution):
ALL GATES PASS — workspace btrfs free 88,838,227,968 B vs measured
requirement 735,055,997 B + 2 GiB margin; btrfs dynamic inodes (no fixed
pool; df -i 0/0 verbatim) vs 71,607 required; target absent + non-symlink
verified; target/repo/main-repo paths distinct; pre-execution commit
added NEW files only.

## The one attempt (unshare -n; 14:26:38Z → 14:28:11Z)
Environment: probes NETWORK_DENIED (connect/DNS failed as required; curl
exit 7); venv built offline `--no-index --require-hashes` from the pinned
wheelhouse; CPython 3.12.3 / pandas 2.2.3 / PMC 4.5.1;
FREEZE_EQUALS_LOCK (lock `08b38cfa…` == freeze). See env_receipt.txt.

- **Hash gates: PASS** (all 26 recorded gates: -48 package 19/19 members;
  route pins; -49 candidates CLI `3f432e7e…` / entrypoint v7 `84ccd2c6…`;
  validator candidate `ca3bafd87e7cb4…`; checker v2 `68998a90…`; driver v3
  `65138541…`; manifest v3 `9573118c…` canonical; TD lock `08b38cfa…`;
  wheelhouse manifest `210b8273…`; -46 F1 object `bd550433…`).
- **Shadow construction + inherited §B checks: PASS.** Detached git
  worktree created at the preflighted workspace path (the -51 failure
  step now succeeds on the workspace filesystem). b1 inside-work-tree
  = true; b2 derived REPO == shadow root
  (`/home/hatch/workspace/qf_td52_stage/shadow`); b4 parent + contention
  children import the same staged candidate gate.
  **Standalone collector-blob proof: PASS** —
  `git -C <shadow> show ab254c3458697dd450356146abcf4ad4f75ecef4:research_notes/td_lifecycle_repair_candidate/td_min_collector.py`
  exit 0, sha256 `b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c`
  == PIN_COLLECTOR: YES.
- **P0 receipt verification: PASS** (accepted -50 record; driver v2
  receipt hash matched; v3 status read live as
  `IMPLEMENTED_BY_CANDIDATE__EXECUTION_PROOF_PENDING`). P0 semantics NOT
  repeated.
- **P1 gate suite: RAN — 46/46 trials PASS** (332 total checks, suite
  exit 0; `gate_revision: r5-route48-candidate`;
  old_spot8_state_unchanged: true; real_pilot_ledger_unchanged: true).
  **Canonical comparison vs the accepted -11 run-2 matrix: IDENTICAL —
  751/751 leaf cells compared, first_divergence: null,
  identical_after_canonicalization: true.** The -51 falsifiable
  prediction (git-aware stage → P1 46/46 identical under the existing
  canonicalization) **HELD**.
- **P1 Gate-5/6/7 evidence step: FAIL — FIRST FAILURE
  `P1_GATE567_NOT_EVIDENCED`, recorded detail verbatim:
  `{"found_12_gate_cells": 0}`.** After the passing comparison, the
  driver's inherited evidence extractor walks the candidate matrix for
  any dict holding a `gates` list of length 12 whose statuses are all
  PASS (to evidence Gates 5/6/7 individually); it found ZERO dicts with
  a 12-element `gates` list, so the evidence object is absent and the
  driver fails closed. Per stop discipline the run ended here.
  *Labeled post-hoc observation (characterization is adjudication's
  call, not this run's): the candidate matrix is byte-identical-after-
  canonicalization to the ACCEPTED run-2 matrix, so the accepted matrix
  likewise contains no 12-element `gates` list — the extractor searches
  for a structure the matrix format does not carry. This code path was
  unreachable in -49/-50 because P1 always failed earlier (at the delta
  checker, then at the matrix comparison); -52 is the first run to pass
  the comparison and reach it. The extractor is inherited driver code,
  unchanged since v2; no candidate, gate, or matrix defect is indicated
  by this failure.*
- **P1 clock/adapter/executor regression + Gate-7 spot check: NOT RUN**
  (they follow the gate567 step inside p1(); stop discipline).
- **P2: NOT RUN. P3: NOT RUN.** The direct-CLI refusal was therefore NOT
  executed this run (no exit-code/message evidence claimed); it remains
  implemented in the frozen candidate, and the manifest v3 status
  `IMPLEMENTED_BY_CANDIDATE__EXECUTION_PROOF_PENDING` remains ACCURATE.
- **Post-run rehash: PASS** — pinned originals unchanged
  (construct_4h `d47e8df1…`, validate_input `1b83cdcd…`, pilot_build
  `257d5bb9…`, verify_sources `a0bd2e4c…`); pilot ledger `7e5ccef0…`
  == pre-run value.

## Cleanup (spec §C.6 + §D)
Driver-side (recorded in proof_results.json `staging_cleanup`): shadow
worktree removed (remove_rc 0, shadow_removed: true); td52_wt status
post-run 0 lines; main-repo status unchanged (53 lines, identical);
repo head still `ebf8a4c…` (the pre-execution commit). Shell-side after
packaging: the task stage root `/home/hatch/workspace/qf_td52_stage`
and the td52_wt package worktree were removed and `git worktree list`
verified to hold no -52 registration (see the results-commit message /
final receipt in this package's SHA256_MANIFEST notes). The main tree's
pre-existing `UU forward_test/kama_shadow.json` merge state was never
touched.

## Timing / prohibitions
Execution start 2026-10-20T14:19:44Z (first command; spec fetched
14:19Z). Attempt window 14:26:38Z→14:28:11Z. Dispatch→remote-verified
elapsed is recorded with the results commit (inside the ≤45 min cap).
Repair minutes beyond driver v4 (the one authorized derivation): 0.
REQ-S2: `UNIMPLEMENTED__HARD_HOLD` — untouched, recorded in the run's
results; it remains the next hard blocker.
ALL PROHIBITIONS HONORED: offline only (sole network use = the pre-run
read-only public fetch of spec comment 6292815205); no vendor/API/model
calls during execution; 0 credits/spend; fixtures only, no real market
data; no SPT-08; E1 and full A/D/B/NLQUAL NOT repeated; nothing adopted
or re-pinned; LIVE chain never executed (candidates only inside the
isolated shadow stage); no state/ledger/production change (V5.4 harness
untouched); no backtest/performance; no holdout; no Issue #9; no Yahoo
work; no second attempt; no in-run repair.
