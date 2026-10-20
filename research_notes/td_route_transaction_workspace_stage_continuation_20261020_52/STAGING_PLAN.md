# -52 r1 — pre-execution staging plan (spec: Issue #1 comment 6292815205)

Task: `QF-TD-ROUTE-TRANSACTION-WORKSPACE-STAGE-CONTINUATION-20261020-52` r1.
Research-only, offline, ONE placement-only correction + ONE continuation
attempt, first material failure stops, zero candidate/checker changes,
zero repair/rerun.

## Why
-50 proved checker/driver v2 + P0, but P1 ran in a non-git shadow and
scored 22/46. The -51 characterization (commit e0b2b33) proved all 382
divergent cells trace to ONE staging mechanism (the staged gate's Gate-6
git-blob read cannot resolve in a non-git shadow): BEHAVIOR 0, IDENTITY 0,
with the falsifiable prediction P1 = 46/46 in a git-aware stage.
The -51 continuation (789726b) passed hash gates + P0 receipt and then
stopped at its first staging step: `git worktree add --detach
/tmp/td51_stage/shadow` failed on the 512 MB /tmp tmpfs (506 MB checkout +
174 MB venv cannot coexist there). HOLD__STAGING_WORKTREE_ADD, accepted
by adjudication (comment 6292815205).

## The one permitted correction (spec section B): stage placement only
Driver v4 (sha256 d2605bb411e8cc0f474a035e14e8f0b477113f25bde6aac6df88f528f9f309b8)
is derived from FROZEN driver v3 (65138541...) with NO semantic change:
the exact stage root moves from /tmp/td51_stage to
/home/hatch/workspace/qf_td52_stage (workspace-backed filesystem, outside
any repository checkout); run-repo worktree path td51_wt -> td52_wt;
task identity/provenance strings updated to the -52 spec; pilot-stage
directory renamed td51 -> td52 inside the shadow. Exact diff:
driver_v3_v4.diff (5 hunks, 25 +/- lines). Checker v2 (68998a90...),
candidates, manifests, matrices, comparator/canonicalization, fixtures,
expected outcomes, and the P1/P2/P3 logic are byte-identical inheritances.
Capacity/inode preflight: CAPACITY_RECEIPT.txt — ALL GATES PASS
(82G free vs a ~0.74 GB requirement + 2 GiB margin; btrfs dynamic inodes).
Driver v4 + diff + this plan + the capacity receipt are committed BEFORE
execution (this package's pre-execution commit).

## Sequence (one attempt, `unshare -n`, pinned wheelhouse venv)
1. Hash gates (inherited section A freeze: -48 package 19/19; route pins;
   -49 candidates; frozen full-length pins incl. checker v2 68998a90...,
   driver v3 65138541..., manifest v3 9573118c..., validator ca3bafd8...;
   TD lock 08b38cfa...; wheelhouse 210b8273...; -46 F1 object bd550433...).
2. Shadow construction at the preflighted workspace path (detached git
   worktree of td52_wt) + inherited section B checks: inside-work-tree
   =true; derived REPO == shadow root; STANDALONE collector-blob proof
   `git -C <shadow REPO> show ab254c3458697dd450356146abcf4ad4f75ecef4:research_notes/td_lifecycle_repair_candidate/td_min_collector.py`
   exits 0 and hashes to b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c
   == PIN_COLLECTOR; parent + contention children import the same staged
   candidate gate. Construction or proof failure = first failure, STOP.
3. P0 receipt verification only (accepted -50 record; v3 status
   IMPLEMENTED_BY_CANDIDATE__EXECUTION_PROOF_PENDING). P0 semantics NOT
   repeated.
4. P1: gate suite 46 trials vs the accepted -11 run-2 matrix (checker v2
   comparator + -50 canonicalization unchanged; real C01 child-process
   assertions) + clock/adapter/executor (-19) regression + Gate-7 spot
   check. Prediction on record: 46/46.
5. P2: driver integration suite vs the accepted -04 run-2 matrix
   (positive + unchanged negatives); candidate calendar-proof digest
   6b030c62... present in the candidate matrix.
6. P3: route-leg binding (v7 entrypoint loads the CLI candidate by exact
   path; plain construct_4h NOT loaded); direct CLI refusal AS EXECUTED
   (exit 3 + exact REFUSED on stderr + no output file + watch tree
   unchanged); entrypoint end-to-end on the F1 fixture, serialization
   byte-identical to the -46 expected F1 string (bd550433...).
7. Post-run rehash of frozen inputs; remove ONLY the task stage +
   shadow worktree registration; prove no lingering registration and
   unchanged repository status/head.

Positives pass; negatives fail CLOSED (a negative that succeeds is a
failure). First material failure stops; later stages do not run.

## Terminal labels (spec section D)
TD_ROUTE_TRANSACTION_PROOF_PASS__RESEARCH_ADOPTION_DESIGNATION_READY__S2_HOLD
TD_ROUTE_TRANSACTION_PROOF_HOLD__<first-failure-key>
A PASS adopts/re-pins nothing and authorizes no data acquisition or
performance work. REQ-S2 remains the next hard blocker (unimplemented).

Clock: execution start 2026-10-20T14:19:44Z (first command of this run);
cap 45 minutes from execution start.
