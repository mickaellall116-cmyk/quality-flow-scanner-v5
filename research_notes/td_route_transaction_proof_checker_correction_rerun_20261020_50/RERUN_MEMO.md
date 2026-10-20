# QF-TD-ROUTE-TRANSACTION-PROOF-CHECKER-CORRECTION-RERUN-20261020-50 r1 — RERUN MEMO

Spec: Issue #1 comment 6289252055. ONE corrected proof driver + ONE
network-isolated P0→P3 attempt; first material failure stopped the run;
zero candidate repairs; zero second attempts.

## Terminal verdict (verbatim)

`TD_ROUTE_TRANSACTION_PROOF_HOLD__P1_GATE_REGRESSION`

## What was corrected (pre-execution commit 48a7a3c)

- **Proof driver v2** (`proof_driver_v2.py`, sha256
  `68998a9060e5d3f5253023d94a00993e77f04588eb6aeed8da12278b176b832e`),
  derived from the -49 driver (`1478d746…`). Full diff:
  `driver_v1_v2.diff`. Changes: (1) the §B semantic correction — the P0
  top-level comparison keys callables by name→AST dump and every
  non-callable statement by a **multiset (Counter) of normalized AST
  dumps** (content-keyed, multiplicity-preserving, line-number-free),
  replacing the -49 `other:<type>:<lineno>` keying; (2) §B.3 checker
  self-checks; (3) §C/§D v3 manifest-status gate in P0; (4) §A explicit
  full-length frozen-pin hash gates; (5) task/stage identity strings
  and a 600 s suite-timeout bound. Stage order, fixtures, canonical
  replacements, failure keys, first-failure stop, and P1/P2/P3 logic
  are otherwise the -49 code.
- **ROUTE_MANIFEST_CANDIDATE_V3.json** (sha256
  `9573118c9b98cf920a008cec2176f0b2a52366d4f1cf57d08c289086c5059e14`,
  canonical bytes). v2→v3 diff (`manifest_v2_v3.diff`) contains ONLY:
  `adjudication_basis` → comment 6289252055, and
  `governance.direct_cli_refusal.status` →
  `IMPLEMENTED_BY_CANDIDATE__EXECUTION_PROOF_PENDING`. No route pin,
  readiness pin, governance rule, atomicity, rollback, or REQ-S2
  change. The -49 v2 manifest was not edited.

## The one attempt (2026-10-20, unshare -n)

- Env receipt (`env_receipt.txt`): network probes failed as required
  (`NETWORK_DENIED`, curl exit 7); venv built `--no-index
  --require-hashes` from the pinned wheelhouse; identity CPython
  3.12.3 / pandas 2.2.3 / PMC 4.5.1; `FREEZE_EQUALS_LOCK` (TD lock
  `08b38cfa…`). Driver execution 11:07:48Z → ~11:08:26Z.
- **Hash gates: PASS** — -48 package 19/19; route pins 3/3 vs the -48
  manifest; -49 candidates 2/2 vs manifest v2; §A frozen pins 3/3 at
  full length (validator candidate `ca3bafd87e7cb439…`, constructor
  candidate `3f432e7e30d3…`, entrypoint candidate `84ccd2c68aea…`);
  v3 manifest canonical; -46 F1 expected-output object re-verified
  (`bd550433…`); TD lock and wheelhouse manifest pins matched.
- **Checker self-checks: PASS 8/8** — same statement at different line
  numbers equal; replaced/added/removed expressions detected;
  duplicate count preserved (delta counts one); v6-vs-v6 delta empty;
  v6 line-shifted (banner inserted) delta empty.
- **P0: PASS** —
  - constructor surface: callables identical (3), docstring identical;
    the non-callable multiset delta is exactly one removed item
    (content sha `e4995c06e8cea82a`, the original `__main__` guard) and
    one added item (`a0803cd290672083`, the candidate guard) — nothing
    else;
  - entrypoint delta: all callables identical; delta = 1 removed item
    (`from construct_4h import construct_4h`) + 6 added items (importlib
    import, `_CONSTRUCTOR_PATH`/`_c4h_spec`/`_c4h_mod` assigns, the
    loader Expr, the `construct_4h` assign) — every item carries an
    authorized fragment; nothing else;
  - manifest v2 chain-carried checks and stale-route-pin scan passed
    (unchanged -49 checks);
  - **v3 status gate PASS**: only-allowed-changes vs v2 true;
    adjudication basis names comment 6289252055; new status is the
    pending value; the old overclaiming status
    (`SATISFIED_BY_CANDIDATE__OFFLINE_PROOF_IN_THIS_PACKAGE`) is
    rejected by the driver's status rule.
- **Staging: PASS** — shadow stage bound the candidate gate, driver,
  supplement, adapter, and executor byte-identically (driver-runner
  staged diff = the single proof-key literal line, as in -49).
- **P1: FIRST FAILURE — `P1_GATE_REGRESSION`.** The candidate gate
  trial suite itself ran to completion (exit 0) and produced
  `gate_matrix.json` (`gate_revision: r5-route48-candidate`,
  `total_checks: 184`, `old_spot8_state_unchanged: true`,
  `real_pilot_ledger_unchanged: true`), but only **22 of 46 trials
  passed**, against the accepted -11 run-2 matrix's 46/46. After the
  unchanged canonicalization, the first divergence is at `$.n_pass`
  (accepted `"46"` vs candidate `"22"`); candidate matrix has 659
  leaf cells vs the accepted 751. Failing trials recorded in the
  candidate matrix (24): G01_green_dry_run, G02_green_dispatch_and_replay,
  G03_default_factory_spy_wiring, F19_token_mismatch,
  F20_evidence_tamper_token, G04_lease_lifecycle,
  H01_helper_import_fail_seam, H02_helper_wrong_module,
  H03_helper_wrong_callable, H04_helper_wrong_binding,
  H05_helper_real_sanctioned_path, C01_contention_two_process,
  P01_helper_absent_path, P02_shadow_on_default_path,
  P03_wrong_origin_no_pin, P04_signature_mismatch, P05_post_gate_swap,
  P06_tampered_bytes, P08_handoff_shadow_installed,
  A01_policy_digest_drift, A03_go_record_absent,
  A04_go_record_malformed, A05_gate3_remaining_exactly_52,
  A06_gate3_remaining_51.
  Post-hoc observation only (not a finding, no rerun made): the
  failures span the green paths and the helper/path/policy families,
  i.e. they are not confined to the Gate-7 mechanism cell the r5
  revision changed; whether this is a genuine candidate-chain
  regression or a trial-harness/staging-convention mismatch is for
  adjudication to determine. The result stands as recorded.
- **P2: NOT RUN. P3: NOT RUN** (first-failure stop). The CLI refusal
  therefore remains implemented by the frozen candidate but is still
  NOT execution-proven by an executed P3; the v3 manifest's pending
  status remains the accurate status after this run.

## Post-run re-verification

The driver's own post-run block did not execute (the run stopped at
P1, before it). The orchestrating shell's post-run re-hash
(`env_receipt.txt`) shows the pinned originals unchanged
(construct_4h `d47e8df1…`, validate_input `1b83cdcd…`, pilot_build
`257d5bb9…`, verify_sources `a0bd2e4c…`), and the pilot ledger
post-run hash `7e5ccef0…` equals the driver's pre-run `ledger_before`.
The three frozen candidates were re-hashed after the run and are
byte-identical to their §A pins (`3f432e7e…`, `84ccd2c6…`,
`ca3bafd8…`).

## Elapsed / repairs

Dispatch (parent brief) → remote-verified results package: ≈17 min of
the ≤45 cap. The isolated attempt itself: ~38 s of driver execution
within a ~1 min orchestrated run. Repair minutes beyond the one
authorized checker build: **0**.

## Prohibitions — all honored

No candidate or existing source modified (candidates frozen and
hash-gated before/after); nothing adopted or re-pinned; no live chain
executed (candidates ran only inside the network-isolated shadow
stage); E1 and the full A/D/B/NLQUAL families NOT repeated; REQ-S2
untouched and recorded as a continuing hard HOLD (this run neither
implements nor waives it; no corrected-performance claim); no
vendor/API/model calls during execution (the only network use was the
pre-run read-only public fetch of spec comment 6289252055); no
credits/spend; no real market data (synthetic fixtures only); no
SPT-08; no backtests/performance; no holdout access; no
state/ledger/production changes (V5.4 harness untouched — the main
tree's pre-existing `UU forward_test/kama_shadow.json` merge state was
never touched; all work happened in a detached worktree); no Issue #9
work; no Yahoo work; no second attempt or in-run repair.
