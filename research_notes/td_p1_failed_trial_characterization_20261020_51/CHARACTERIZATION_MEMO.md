# QF-TD-P1-FAILED-TRIAL-CHARACTERIZATION-20261020-51 r1 — CHARACTERIZATION MEMO

STATIC / READ-ONLY investigation of committed evidence. No suite, gate,
driver, collector, or candidate was executed; no code was changed.
Analysis scripts (`analysis_compare.py`, `analysis_classify.py`) operate
on the two committed JSON matrices and on file hashes only; they import
no chain code.

## Provenance

ChatGPT's formal -51 spec (this same investigation) failed to deliver
to Slack/GitHub (Mike, 2026-10-20 08:00 EDT). This run proceeds on
Muse's -50 WORK RESULT proposal for a static per-trial
characterization, as relayed and approved by Mike. Scope follows that
proposal faithfully.

## Terminal verdict

`P1_FAILURES_CHARACTERIZED__STAGING_GIT_BLOB_ONLY__NO_BEHAVIOR_CELLS`

All 24 failing trials, and every one of the 382 non-equal leaf cells
behind them, trace to ONE staging mechanism: in the -50 shadow stage
the candidate gate's file location made its repo root a non-git
directory, so the gate's one git-object read returned nothing and
Gate 6 recorded `PIN_MISMATCH:collector` on every full-gate evaluation.
Class (i) R4_IDENTITY cells: **0**. Class (iii) BEHAVIOR cells: **0**.

## Inputs (committed evidence)

- Candidate matrix: `research_notes/td_route_transaction_proof_checker_correction_rerun_20261020_50/gate_matrix.json`
  (gate_revision `r5-route48-candidate`, n_pass 22/46), produced by the
  -50 run (commits `48a7a3c` + `d1f2c8c`).
- Accepted matrix: `research_notes/td_policy_a_live_readiness_packet_20261017_11/dispatch_matrix_run2.json`,
  sha256 `aafd4e1b13b444600eb4d13481525aac54e840416b25d73ad84db514c16e2de3`
  (byte-identical to `dispatch_matrix_run1.json`; gate_revision
  `r4-policyA-11`, n_pass 46/46) — the -11 run-2 matrix the -50
  driver's `compare_matrix` used (proof_driver_v2.py, P1 section).
- The -50 comparison method, replicated exactly: the driver's
  `token_map()` / `canonicalize()` (7 pin-hash pairs + filename tokens
  + 12/8-char hash prefixes + REVISION strings + the -48 package-dir
  token). Replication is verified faithful: it reproduces the driver's
  own recorded leaf counts (accepted 751, candidate 659) and the memo's
  failing-trial list exactly.

## Classification rules (stated upfront, applied mechanically)

Every non-equal leaf cell (divergent value, or present on one side
only) is classified into exactly one class:

- (i) **R4_IDENTITY** — the cell's value encodes an r4-lineage identity
  the -48 adoption is designed to change (file paths/names, pin hashes,
  revision strings, version labels) and canonicalization did not
  already neutralize it.
- (ii) **STAGING_OR_CANONICALIZATION** — the difference is produced by
  the comparison/staging convention itself: the shadow-stage
  environment, canonicalizer coverage, runner emission mechanics, and
  count cells that merely aggregate root divergences (marked DERIVED
  and counted separately).
- (iii) **BEHAVIOR** — a genuine semantic difference in gate output
  under identical inputs, neither (i) nor (ii).

Root cells are classified; rollups (top-level `n_pass`/`total_checks`,
per-trial `n_checks`, and the emitted `checks` lists) are DERIVED and
counted separately. The runner's emission mechanics make them derived
by construction: `Trial.check()` appends a label and raises
AssertionError at the first failed assertion
(`run_dispatch_gate_trials_r4.py:194-197`), so a trial's emitted check
list is a mechanical function of where its first assertion failed.

## Headline counts

Non-equal leaf cells after canonicalization: **382** of 751 accepted
leaves.

| Class | Cells | Composition |
|---|---|---|
| (i) R4_IDENTITY | **0** | — |
| (ii) STAGING — root cells | **208** | GATE6_ROOT 117, GATE6_COUNT 39, STATUS_CONSEQUENCE 24, PASS_ARTIFACT_ABSENT 18, DECISION_FLIP 6, STATE_CONSEQUENCE 4 |
| (ii) DERIVED — counted separately | **174** | checks-emission cells 148 + per-trial `n_checks` 24 + top-level rollups 2 |
| (iii) BEHAVIOR | **0** | — |

An explicit scan of every non-equal cell value for untokenized
identity strings (40–64-char hex digests, gate/driver file names,
`.py` names, `r4-policyA` / `r5-route48` revision strings) returns
**zero hits**: canonicalization had already neutralized every identity
value, and the trial `facts` objects contain no hashes at all.

## The single root mechanism (statically proven)

1. Gate 6 (`source_hashes`) recomputes the collector pin from a **git
   object**, not a file: `_git_blob(REPO, *P_COLLECTOR_GIT)` runs
   `git -C <REPO> show ab254c3458697dd450356146abcf4ad4f75ecef4:research_notes/td_lifecycle_repair_candidate/td_min_collector.py`
   and returns None on any git failure
   (`dispatch_gate_r4.py:158-163`, used at `:574-578`).
2. `REPO` is derived from the gate file's own location
   (`dispatch_gate_r4.py:51`: two directories up). In the accepted -11
   run the gate file sat in the real repository checkout, and the blob
   resolves: reading that exact object from this repository during
   this investigation (`git cat-file blob`, the same object read)
   yields bytes with sha256
   `b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c`
   — exactly `PIN_COLLECTOR`. In the -50 run the gate file sat in the
   shadow stage (`/tmp/td50_stage/shadow/research_notes/...`, per
   proof_driver_v2.py `build_shadow()`), so `REPO` was
   `/tmp/td50_stage/shadow` — **not a git repository** — `git show`
   failed, the blob was None, and the collector sub-check was False on
   every evaluation. Every other Gate-6 sub-check reads files, and all
   file paths in the shadow resolved (symlinks/substituted dirs), which
   is why the bad set is exactly `collector` and nothing else
   (candidate G01 `gate_codes`: `["6:PIN_MISMATCH:collector"]`).
3. The r5 candidate diff cannot cause this: the -48 gate diff
   (`diffs/dispatch_gate_r5_candidate.diff`) changes only the banner,
   `REVISION`, `P_DRIVER`/`P_SUPPLEMENT`/`P_MECHANISM`, and
   `PIN_DRIVER`/`PIN_SUPPLEMENT`/`PIN_MECHANISM`/`PIN_CALENDAR_PROOF`.
   `P_COLLECTOR_GIT` and `PIN_COLLECTOR` are byte-identical in r4 and
   r5, and no gate logic changed. Under the accepted run's environment
   (a real checkout), the candidate chain produces the accepted
   Gate-6 result.

## Transformation verification (why zero BEHAVIOR cells is proven, not eyeballed)

For each of the 43 trials that record gate facts, the candidate facts
were checked against the exact transformation the single mechanism
predicts: `failed_gates` set = accepted set ∪ {6}; `gate_codes` set =
accepted set ∪ {`6:PIN_MISMATCH:collector`} (with the same-gate bad-set
merge for F10: `manifest` → `collector,manifest`); `gates_passed` −1
where gate 6 had passed; `decision` flips to HOLD exactly where the
accepted decision was PASS/PASS_DRY_RUN; every remaining divergent fact
key is either a PASS-artifact key (recorded only from a PASS
receipt/dispatch) or the zero-access state pair
(`ledger_unchanged`, `ns_created_by_call`). **Residuals: none.** The
remaining 3 trials (F21, F22, P07) record no gate facts in either
matrix and are byte-identical. Four trials carry the mechanism one step
removed and are dossiered here:

- **G02** (replay): `gate_summary()` is called per dispatch and the
  replay summary overwrites the first (runner `g02`, lines 289-321).
  Accepted facts are the replay's ([3,8], gates 3+8). In the candidate
  run the first dispatch HELD at gate 6, the trial aborted at its
  `decision_pass` check, and the recorded summary is the first
  dispatch's ([6], 11 passed). `lifecycle_outcome`/`replay_guard`
  never set. Same root.
- **P05 / P08**: each asserts `only_gate9_failed` with
  `failed_gates == [9]` exactly. Candidate records [6] with
  gates_passed unchanged at 11: the gate-9 post-gate reverify that
  produces `SWAPPED_POST_GATE` / `SHADOW_INSTALLED` sits downstream of
  a clean gate evaluation in the dispatch flow, so the gate-6 HOLD
  preempts its recording. Same root; no gate-9 logic differs (the r5
  diff touches no gate logic).
- **C01**: holder/contender are subprocesses running the gate from the
  same staged directory (runner `c01_contention`, line 758+); the
  holder's own gate evaluation HELD at gate 6 (same non-git REPO), so
  the holder never reached its blocking point and no holder/contender
  fact files were produced — candidate C01 facts are the empty object;
  all 10 accepted fact cells are PASS-artifacts of a dispatch that
  never occurred. Same root.
- **G03 / G04** `ledger_unchanged` (False→True) and
  `ns_created_by_call` (True→False): on a PASS dispatch the Runner
  creates the namespace and writes reservations by design; a HOLD
  performs zero access. Deterministic consequence of the decision
  flip, tagged STATE_CONSEQUENCE (4 cells).

## Per-trial verdicts — the 24 failing trials

Verdict vocabulary note: every trial below is **STAGING_ONLY** — in the
task's three-way vocabulary, none is IDENTITY_ONLY, none is
IDENTITY+STAGING (identity component is zero everywhere), and none
CONTAINS_BEHAVIOR. "Root cells" excludes DERIVED emission/rollup cells.

| Trial | Root cells | Shape |
|---|---|---|
| G01_green_dry_run | 6 | decision PASS_DRY_RUN→HOLD; gate 6 collector only |
| G02_green_dispatch_and_replay | 8 | first-dispatch summary recorded; replay artifacts absent (dossier) |
| G03_default_factory_spy_wiring | 9 | decision flip + zero-access state pair + spy artifacts absent |
| G04_lease_lifecycle | 8 | decision flip + state pair + lease artifact absent |
| F19_token_mismatch | 4 | gate 6 inserted; token layer never reached |
| F20_evidence_tamper_token | 4 | gate 6 inserted; token layer never reached |
| H01_helper_import_fail_seam | 6 | gate 6 inserted ahead of the expected gate-9 failure |
| H02_helper_wrong_module | 6 | same insertion pattern |
| H03_helper_wrong_callable | 6 | same insertion pattern |
| H04_helper_wrong_binding | 6 | same insertion pattern |
| H05_helper_real_sanctioned_path | 6 | decision flip (PASS_DRY_RUN→HOLD) + helper_route absent |
| C01_contention_two_process | 11 | subprocess holder held at gate 6; facts empty (dossier) |
| P01_helper_absent_path | 6 | gate 6 inserted ahead of expected gate-9 failure |
| P02_shadow_on_default_path | 6 | decision flip + shadow_imported absent |
| P03_wrong_origin_no_pin | 6 | gate 6 inserted ahead of expected gate-9 failure |
| P04_signature_mismatch | 6 | gate 6 inserted ahead of expected gate-9 failure |
| P05_post_gate_swap | 3 | recorded summary substitution [9]→[6] (dossier) |
| P06_tampered_bytes | 6 | gate 6 inserted ahead of expected gate-9 failure |
| P08_handoff_shadow_installed | 3 | recorded summary substitution [9]→[6] (dossier) |
| A01_policy_digest_drift | 4 | gate 6 appended to the expected failure |
| A03_go_record_absent | 4 | gate 6 appended |
| A04_go_record_malformed | 4 | gate 6 appended |
| A05_gate3_remaining_exactly_52 | 5 | decision flip (PASS_DRY_RUN→HOLD) |
| A06_gate3_remaining_51 | 4 | gate 6 appended |

## Per-family rollup

| Family | Trials | Candidate PASS | Of the PASS: identical | Of the PASS: staging-diverged facts | FAIL |
|---|---|---|---|---|---|
| Green (G) | 4 | 0 | 0 | 0 | 4 |
| Gate-refusal (F) | 22 | 20 | 2 (F21, F22) | 18 (F01–F18) | 2 (F19, F20) |
| Helper (H) | 5 | 0 | 0 | 0 | 5 |
| Contention (C) | 1 | 0 | 0 | 0 | 1 |
| Path/pin (P) | 8 | 1 | 1 (P07) | 0 | 7 |
| Policy (A) | 6 | 1 | 0 | 1 (A02) | 5 |
| **Total** | **46** | **22** | **3** | **19** | **24** |

## The passing set — consistency answer

Question: do any of the 22 passing trials pass only because their
outputs contain no identity cells? **No — and the premise does not
arise: identity cells are zero in every trial, passing or failing.**
The 22 split as:

- **19 pass WITH the staging divergence in their facts** (F01–F18,
  A02). Their assertions are insensitive to an extra failed gate: the
  refusal-trial shape (`refusal_trial` / `expect_hold_zero_access`,
  runner lines 341-361, 242-252) asserts decision == HOLD and
  zero-access properties, and the per-trial gate assertions are
  membership-style. The added `6:PIN_MISMATCH:collector` entry disturbs
  none of them.
- **3 pass byte-identical** (F21 clock-seam live mode, F22 direct-arm
  boundary, P07 driver handoff). Their flows refuse before, or never
  record, a gate summary, so no gate-6-dependent cell exists in either
  matrix.

The pass/fail split inside the 43 gate-recording trials is fully
explained by assertion shape: trials whose checks use exact-equality
on the failed-gate set (`only_gate9_failed`), require a PASS decision,
or reach post-gate layers (tokens, replay, contention) fail on the
extra gate-6 entry; trials asserting HOLD + membership pass. This is
exactly the pattern a single environment-caused extra failure
produces, and no trial requires a second mechanism.

## Recommendation to adjudication (not implemented)

The matrix becomes a valid adoption regression with an **environment
fix, not an expectation change**:

1. Run P1 with the staged gate file located inside a real git checkout
   whose object store contains commit
   `ab254c3458697dd450356146abcf4ad4f75ecef4` (e.g. make the shadow
   root a git worktree of the repository instead of a bare /tmp tree),
   so the gate's `REPO` resolves to a repository and
   `git -C REPO show` returns the pinned collector blob. No code, pin,
   or expectation changes.
2. Keep the accepted -11 run-2 matrix as the comparator and the -50
   canonicalization unchanged: once the environment is fixed, every
   remaining r4→r5 delta is already covered by the existing token
   pairs (this investigation found zero untokenized identity cells).
3. Do NOT canonicalize away the gate-6 collector cell to make a
   non-git stage pass — that would mask a real environmental
   dependency of the gate. The dependency itself (Gate 6 requires a
   git checkout at runtime) is worth recording in the adoption
   transaction's deployment terms, since any future staged/offline
   execution of this gate inherits it.

With that single environmental correction, the predicted P1 outcome —
stated as a falsifiable expectation, not a result — is 46/46 identical
after the existing canonicalization.

## Prohibitions — all honored

No suite/gate/driver/collector/constructor/candidate code executed
(the only commands run against repository content were file reads,
sha256 hashing, and one read-only `git cat-file blob` of the pinned
collector object — a static read of committed evidence);
no file outside this new -51 package edited; no vendor/API calls
(none needed; nothing fetched); no credits/spend; no market data; no
holdout access; no state/ledger/production changes (V5.4 harness
untouched; the main tree's pre-existing `UU forward_test/kama_shadow.json`
merge state was never disturbed — all work in a detached temp
worktree); no Issue #9 work; no Yahoo work.
