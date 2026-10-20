# -55 CLOSURE MEMO — branch-isolated clock proof and final remainder

Task: QF-TD-ROUTE-TRANSACTION-BRANCH-ISOLATED-FINAL-CLOSURE-20261020-55 r1
Spec: Issue #1 comment 6297990771. Pre-execution commit d7e0234
(driver v7 + diff + branch map + self-checks 28/28), ACK e691652.
One offline attempt (unshare -n), run 2026-10-20T18:33:25Z →
18:36:27Z (driver exit 0; the driver records its own verdict).
Elapsed, spec-fetch convention (first command 18:28Z → this memo):
~19 min of ≤45. Repair minutes: 0.

## Terminal (verbatim)

TD_ROUTE_TRANSACTION_PROOF_HOLD__P2_DRIVER_SUITE_RUN

## The headline: the branch-isolated clock proof PASSED

The -54 divergence is confirmed as the cross-contamination
artifact ChatGPT adjudicated. With ORIGINAL and CANDIDATE in two
separate git worktrees (same HEAD 94648c8, membership fixed and
recorded pre-execution), fail-closed provenance verified in-driver
before any suite ran:

- ORIGINAL pins all match: gate b5399645…, driver
  5fed45242eb5ec46…, supplement 3cbdbf63…, mechanism 1b83cdcd…,
  proof 36bc3a89… (full values in proof_results.json).
- CANDIDATE pins all match: gate 94ef967c…, driver d11c6b58…,
  supplement 55ad6f40…, mechanism ca3bafd8…, proof 6b030c62…,
  adapter 6980b5b3…, executor bbc23616….
- Both accepted runner copies byte-identical (== accepted PKG19
  runner); resolved paths recorded; no overlap; no symlinks.
- Trial-name partition exact: {repro_old} + 19 = all 20, both
  branch outputs complete, no omission/overlap.
- ORIGINAL scoped verdict: repro_old cell-for-cell EXACT vs
  accepted run-2, and its rollup contribution (checks true/total +
  ok) matches accepted exactly.
- CANDIDATE scoped verdict: the other 19 trials cell-for-cell
  EXACT (19/19); repro_old explicitly excluded on this side, as
  specified.
- Real pilot ledger sha256 unchanged in BOTH branches
  (7e5ccef0… == run-repo ledger).
- Reused, not rerun (spec §6): pinned -52 gate receipt canonical
  comparison identical (751/751 cells); Gate-5/6/7 evidence
  satisfied by the corrected extractor. The 46-trial gate suite,
  extractor tests, E1, A/D/B/NLQUAL were not rerun.

## What stopped the run: P2 (candidate branch)

After the clock proof passed, P1's remainder and P2 ran in the
candidate branch per spec §7:

- Gate-7 original-vs-candidate mechanism spot check: EXECUTED,
  recorded `error: FileNotFoundError: 'research_notes/
  pilot_harness/validate_input.py'` — the gate's mechanism path is
  repo-relative and the driver cwd is the stage root. This is the
  v6/v7 inherited call convention: the exception is recorded and
  the matrix governs (it does not raise). Recorded here plainly:
  the spot check produced NO comparative facts in this run.
- P2 driver integration suite: EXECUTED, exit 1 — 14/18 PASS.
  Failures, in trial order:
  - I01 FAIL — check `pin_validate_input` (the candidate driver's
    other two pin facts, pin_pilot_acquire / pin_rate_limiter,
    were recorded; the validate_input pin check failed). This
    failure precedes the interference below and stands as
    observed; characterization is for adjudication.
  - I03 ERROR — FileNotFoundError on a rename inside its own
    trial dir (pilot_state.json.tmp → pilot_state.json): the tmp
    file vanished mid-trial.
  - I14 / I15 ERROR — FileNotFoundError:
    '/home/hatch/workspace/qf_td55_stage/venv/bin/python' — the
    venv interpreter the suite spawns workers with vanished
    mid-run.
  First-failure stop: driver verdict
  TD_ROUTE_TRANSACTION_PROOF_HOLD__P2_DRIVER_SUITE_RUN.

## Evidence-integrity disclosure (plain)

An external actor or environment process removed files from the
stage DURING and AFTER this run: the venv, stage inputs, freeze.txt,
driver_stdout.txt/driver_stderr.txt, and the three clock-matrix
JSONs are gone; env_receipt.txt survives only from the driver-exit
line onward; I03's vanishing tmp file is in-run evidence of the
same removal. (The prior task's stage, qf_td54_stage, is likewise
absent from this host.) What survives, preserved in run_artifacts/:
proof_results.json (the driver's complete in-run record — all
comparisons, provenance, provenance pins, cleanup — computed and
written by the driver itself), driver_matrix.json, the
driver_trials/ listing, env_receipt.txt (surviving tail, incl. the
post-run sha256sum of the five pinned originals: construct_4h
d47e8df1…, validate_input 1b83cdcd…, pilot_build 257d5bb9…,
verify_sources a0bd2e4c…, credit_ledger 7e5ccef0… — all matching
their pins), run_status.txt (DRIVER_RAN). The lost clock matrices
are attested only by proof_results.json's canonical comparison
record; they cannot be re-inspected. No rerun was attempted (one
attempt; a rerun would also not cure an external removal).

## Unexecuted

- P3 (exact binding / direct CLI exit 3 + REFUSED + no writes /
  F1 byte identity): never reached — first-failure stop at P2.
  The CLI refusal remains implemented-but-unexecuted.
- The driver's own post-run rehash block: not executed (Fail
  path); run_proof.sh's post-run sha256sum above substitutes as
  the unchanged-state record for the pinned originals.

## Cleanup / unchanged state (driver-recorded)

Both branch worktrees removed (original_shadow_removed: true,
shadow_removed: true); run-repo HEAD unchanged
(94648c8298cef0bc1ecada842054511622754b5e); main working tree
status hash unchanged across the run (other workers' pre-existing
dirt untouched; nothing staged/stashed/committed there by this
task). V5.4 entries remain PAUSED; the sentinel and
v54_forward_harness.py were not touched.

## State after -55

Clock-fixture family: CLOSED by branch isolation (original
repro exact; candidate 19/19 exact). Remaining transaction proof:
Gate-7 spot check (needs a cwd-correct invocation), P2 (I01
pin_validate_input characterization + a stage the environment
does not wipe mid-run), P3 (never executed). REQ-S2 remains a
hard HOLD; nothing adopted; the PASS terminal was not reached,
so no research-adoption designation arises from this run.
