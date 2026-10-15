# Trial log — QF-TD-P2-SPOT-V2-DERIVATION-CANDIDATE-20261015-06 r1

All times EDT 2026-10-15. Budget: ≤50 min incl. one ≤10-min repair.
Repair allowance: USED (~9 min total: ~3 min driver-expectation fix,
~6 min candidate stub-compatibility fix). Elapsed total: see memo §6
(disclosed overrun; dominant cost is real-calendar receipt revalidation
across ~35 fresh state copies per suite run).

| # | Trial | Outcome |
|---|---|---|
| 1 | Environment check | Qualified `/tmp/tdqual/venv` present at start (CPython 3.12.3, pmc 4.5.1, freeze == f64d12f lock). No rebuild needed initially. |
| 2 | Candidate build | Branch `td-derivation-candidate-20261015-06` from `ab254c3` in a `/tmp` worktree; commits `78d925f` (derivation + read-only verify), `9e4f4f0` (derived-unbound fail-closed), `27866cd` (findings accumulation). Single-file diff vs base. |
| 3 | Suite trial 0 (first full execution, pre-repair plumbing) | 43/45 pass in ~20 min. 2 failures, both **driver-expectation defects** (calendar-drift case assumed an SPT08 dispatch the candidate correctly pre-empts by failing closed at the derived-evidence binding with zero dispatch; one outcome-substring check named the wrong token). Results preserved: `suite_results_trial0_driver_defective.json`. |
| 4 | Driver repair (~3 min, within allowance) | Calendar-drift case re-specified to the true invariant (drifted supplement → derived evidence unbound → HOLD, zero dispatch, no SPT08 STARTED); substring check corrected. No candidate bytes changed. |
| 5 | Regression: -17 classifier suite vs candidate | FAILED (errors=1): S3 stub replaces `_validate_bars` with a 2-arg lambda; candidate's new `observational` keyword broke the stub convention. A genuine candidate defect (internal call-signature drift), counted against the repair allowance. |
| 6 | Candidate repair (~6 min, within allowance) | Observational mode switched to an instance flag; base `_validate_bars(req, values)` call signature restored exactly. Commit `ce9c02a`. Classifier suite: 18 tests OK. Lifecycle suite: OK. |
| 7 | Regressions set 1 (post-repair) | classifier OK; lifecycle OK; pinned integration 16/16 success (`pinned_integration_results_run1.json`). |
| 8 | -05 reproduction | -05 driver vs unchanged base: 9 cases, `all_checks_pass: true`, `transition_supported: false` — the HOLD finding reproduces exactly. |
| 9 | Regressions set 2 | classifier OK; lifecycle OK; pinned integration 16/16 success; results.json byte-identical to set 1. |
| 10 | Suite run A (post-repair, /tmp worktree + /tmp venv) | **ABORTED BY ENVIRONMENT**: `/tmp` wiped mid-run; run outputs and worktrees destroyed. Candidate commits recovered byte-identical from the main repo object store (branch `td-derivation-candidate-20261015-06` @ `ce9c02a`, collector sha256 `51b61675…` re-verified from the commit object). No results from run A are claimed anywhere in this packet. |
| 11 | Environment rebuild (disclosed) | Venv rebuilt under `~/workspace/pf06_scratch/venv` per the qualified procedure: pip download of the exact lock, 11/11 wheel hashes byte-identical to qualified records, `--no-index` install, freeze == lock, CPython 3.12.3 / pmc 4.5.1. Worktrees recreated under `~/workspace/pf06_scratch`. Wheel hashes + freeze in package (`env_rebuild_*`). |
| 12 | Suite run 1 (final, post-repair, rebuilt env) | **45/45 PASS.** `suite_results_run1.json` sha256 `adb6bee968e1b32db39e15e939191eaa498426eb79602dcb3ed4458667c21aa9`. Crash mapping: before-append → restart DERIVED (final 1 event); after-evidence-file → restart DERIVED (final 1); after-event → state still HOLD, restart DERIVED_RECONCILED (final 1); after-state → restart REFUSED duplicate (final 1). |
| 13 | Suite run 2 (determinism) | **45/45 PASS**, output byte-identical to run 1 (sha256 in memo §3). |

Candidate failures in final trials: none.
