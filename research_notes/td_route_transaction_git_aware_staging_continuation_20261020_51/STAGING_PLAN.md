# -51 r1 — pre-execution staging plan (spec: Issue #1 comment 6290393927)

Task: `QF-TD-ROUTE-TRANSACTION-GIT-AWARE-STAGING-CONTINUATION-20261020-51` r1.
Research-only, offline, ONE continuation attempt, first material failure stops,
zero candidate/checker changes, zero repair/rerun.

## Why
-50's corrected checker passed P0 in full, but P1 ran in a non-git shadow:
the staged gate's Gate-6 git-object read
(`git -C <REPO> show ab254c3…:research_notes/td_lifecycle_repair_candidate/td_min_collector.py`)
returned None because REPO resolved to the plain shadow root →
`PIN_MISMATCH:collector` on every full-gate evaluation → 22/46.
-51 (characterization, commit e0b2b33) proved statically that all 382
divergent cells trace to that single mechanism (BEHAVIOR 0, untokenized
IDENTITY 0) and recorded the falsifiable prediction: with a git-aware
stage, P1 = 46/46 under the existing canonicalization.

## The one authorized change (spec §B)
The shadow stage is a **detached git worktree** of this repository
(`git -C <repo> worktree add --detach <shadow>`), so the staged gate's
derived REPO (= two parents above the staged gate file) IS a real git
checkout whose object store contains commit
`ab254c3458697dd450356146abcf4ad4f75ecef4`. Candidate substitution is
byte-for-byte the -50 staging plan applied over the worktree's committed
files (substituted package dirs rebuilt with exactly the -50 file set;
non-substituted dirs are the worktree's real committed files). No gate,
candidate, trial, expected-outcome, canonicalization, or business-logic
change.

Orchestrator: proof driver v3, sha256
`651385415a46dbc72c080b6c8921ced0de8170d30b5932642fb2daa90877988d`,
derived from frozen driver v2 (`68998a90…`); exact diff in
`driver_v2_v3.diff` (13 hunks: header/constants, §A pin gates,
P0-receipt stage, staging topology + §B preflight + cleanup, main()
order, pilot-stage dir name). P1/P2/P3 logic and the comparator are the
v2 code unchanged. Committed BEFORE execution (this package's
pre-execution commit).

## Sequence (one attempt, `unshare -n`, pinned wheelhouse venv)
1. Hash gates (§A freeze: -48 package 19/19; route pins; -49 candidates;
   frozen full-length pins incl. driver v2 `68998a90…` and v3 manifest
   `9573118c…`; -48 candidate pins; TD lock `08b38cfa…`; wheelhouse
   `210b8273…`; -46 F1 object `bd550433…`).
2. P0 receipt verification only (spec §C): the accepted -50 P0 record +
   v3 status `IMPLEMENTED_BY_CANDIDATE__EXECUTION_PROOF_PENDING`. The
   semantic-delta proof is NOT repeated.
3. Git-aware staging + §B preflight, incl. the standalone blob proof:
   `git -C <shadow> show ab254c3…:…/td_min_collector.py` must exit 0 and
   hash to `b683d277cc02a8d27…` (= PIN_COLLECTOR). Blob-proof failure =
   first failure; no suite runs.
4. P1: full gate matrix vs the accepted -11 run-2 matrix (checker v2
   comparator + canonicalization unchanged), Gate-5/6/7 evidence,
   adapter/executor (-19) regression, Gate-7 spot check.
5. P2: candidate driver integration matrix vs the accepted -04 run-2
   matrix (positive + unchanged negatives); candidate calendar-proof
   digest `6b030c62…` must appear.
6. P3: route-leg binding (v7 loads the CLI candidate by exact path),
   direct CLI refusal executed (exit 3 + REFUSED + no writes), F1
   fixture via the entrypoint byte-identical to `bd550433…`.
7. Post-run rehash; shadow worktree removed; pre/post repository status
   recorded (main working tree untouched, incl. its pre-existing
   `UU forward_test/kama_shadow.json` merge state).

Terminal labels (spec §D):
`TD_ROUTE_TRANSACTION_PROOF_PASS__RESEARCH_ADOPTION_DESIGNATION_READY__S2_HOLD`
or `TD_ROUTE_TRANSACTION_PROOF_HOLD__<first-failure-key>`.
A PASS adopts/re-pins nothing. **REQ-S2 remains the next hard blocker,
unimplemented and untouched.**
