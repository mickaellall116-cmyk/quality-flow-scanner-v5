# CLOSURE MEMO — QF-TD-ROUTE-TRANSACTION-COLLISION-SAFE-REMAINDER-20261020-56 r1

**Terminal verdict (verbatim): `TD_ROUTE_TRANSACTION_PROOF_HOLD__P2_PROOF_DIGEST`**

One offline attempt, first-failure stop, no in-run repair, no second
attempt. Elapsed: spec fetch 2026-10-20T20:37Z → execution complete
21:02:28Z → this package committed immediately after (≈35 min of
the ≤45 cap; repair minutes: 0). The run executed FURTHER than any
prior attempt: the lease, hash gates, P0 receipt, P1 receipt reuse,
gate567, the Gate-7 spot check, and the full P2 suite all produced
PASSING evidence. The stop is the driver's own P2 proof-digest
presence check — a driver-side evidence check against a structure
the matrix format never contained (labeled characterization below;
the HOLD stands exactly as recorded).

## Single-dispatch (spec §1)
- Pre-check BEFORE any file operation: no *td56* stage dir, no
  td56 worktree, no 20261020-56 entry in origin/main log — PASS,
  sole lane (parent-verified, re-verified by this worker).
- Atomic owner lease (O_CREAT|O_EXCL) acquired BEFORE any stage
  mutation: /home/hatch/workspace/qf_td56_owner_lease.json,
  2026-10-20T20:52:06Z (LEASE_EVIDENCE.json in this package). The
  driver verified it in-run: `VERIFIED_SINGLE_OWNER`.
- Stage root task-unique (/home/hatch/workspace/qf_td56_stage);
  no -55 path touched or cleaned (qf-td55 worktree left as found).

## Build (committed BEFORE execution — pre-execution commit 16073bd)
- Driver v8 sha256 aad2e97c39b5ef9d59d249a0d5ca6431d27c7c257a3e5542604ce3c4f84d67ad,
  derived from the EXECUTED v7 (bb375b76…, restored by bb6fd8f;
  the never-executed 279db80 variant was not used). Changes ONLY:
  identity/lease enforcement; gate7_spot() with absolute mechanism
  paths; P2 adapter staging; p1() remainder (clock functions
  retained byte-identical, never invoked); main() lease-first, no
  original worktree. Diff: driver_v7_v8.diff.
- P2 adapter sha256 e08e33c2335df756488c7c566149638792018fd3c064a48b51eec4c8bcdc0c8c
  = frozen -04 runner + EXACTLY ONE line (I01 validate_input source
  path → candidate validator path). Diff: adapter_frozen_diff.diff.
- Self-checks (td56_self_checks.py): 21/21 PASS — unsanctioned and
  critical functions byte-identical to v7; p1 receipt head
  identical; adapter one-line diff; all pins resolve.
- Capacity pre-check PASS (86.2 GB free vs ~3.3 GB requirement;
  btrfs dynamic inodes). Anchor: td56_wt detached at the
  pre-execution commit.

## Execution (one attempt, `unshare -n`, 20:58:48Z → 21:02:28Z)
Environment: NETWORK_DENIED (probe NETWORK_DENIED; curl exit 7);
venv from the pinned wheelhouse; CPython 3.12.3 / pandas 2.2.3 /
PMC 4.5.1; FREEZE_EQUALS_LOCK (08b38cfa…). Driver exit 0.

- **Lease:** VERIFIED_SINGLE_OWNER.
- **Hash gates: ALL PASS** (33 recorded: -48 manifest 19/19;
  frozen v2/v4/v5/v6/v7 byte-identical; adapter == pin; -52
  receipt files == pins; TD lock; wheelhouse manifest; F1 object).
- **P0 receipt:** PASS (reuse; no rerun).
- **Staging §B preflight:** PASS; standalone blob proof from the
  shadow: b683d277cc02a8d27… == PIN_COLLECTOR.
- **P1 gate receipt (suite NOT rerun):** canonical comparison vs
  the accepted -11 run-2 matrix IDENTICAL — 751/751 cells,
  first_divergence null. **Gate567 (corrected extractor on the
  pinned receipt): SATISFIED** (gate5/6/7 PASS).
- **Gate-7 spot check — EXECUTED WITH FACTS (the -55 gap closed):**
  invoked from cwd /home/hatch/workspace/td56_wt with ABSOLUTE
  mechanism paths (original: pilot_harness/validate_input.py,
  sha 1b83cdcd…; candidate:
  td_validator_dst_repair_requalification_20261019_44/
  validate_input_v3_dstfix.py, sha ca3bafd8…). **Original and
  candidate derive_calendar facts IDENTICAL (4 facts each);
  candidate 2026-07-03 early-close fact = True.** PASS.
- **P2 driver suite (candidate-aware adapter): exit 0 —
  TRIALS 18 PASS 18 FAIL 0.** I01 PASS with facts
  `pin_validate_input = "ca3bafd87e7c"` (the candidate validator
  hash prefix, as spec §4 requires); I02–I18 all PASS.
  **Canonical comparison vs the accepted -04 run-2 matrix
  (integration_matrix_run2.json): IDENTICAL — 205/205 cells,
  first_divergence null.**
- **FIRST FAILURE — P2_PROOF_DIGEST:** after the identical
  comparison, the driver's inherited presence check searched the
  candidate matrix's raw text for the full candidate proof digest
  `6b030c62fdaf3cd738001a438b6f6a562b381b93b29dd8b299753de6aebe4fa5`
  and found it absent:
  `{"candidate_proof_digest_present_in_candidate_matrix": false,
  "negative_controls_identical": true}`.
  LABELED POST-HOC CHARACTERIZATION (adjudication's call): the
  check is unsatisfiable against the matrix's actual schema. The
  matrix (a list of 18 trial objects) records only 12-char hash
  prefixes in facts and contains ZERO 64-hex strings; the ACCEPTED
  run-2 matrix likewise never contains the original proof digest
  (36bc3a89…) in any form (grep-verified on both files in this
  run's record). The proof digest is the calendar_proofs KEY
  inside the supplement JSONs — consumed by the runner internally
  (the staging substitution target) — and is never serialized
  into the matrix output. This is the same defect class as -52's
  gate567 extractor: a driver-side evidence check searching for a
  structure the format never contained. The digest's presence in
  the candidate CHAIN is independently hash-gated (candidate
  supplement 55ad6f40… whose calendar_proofs key is 6b030c62…,
  read directly by the unchanged token_map during the identical
  canonical comparison). No candidate defect is indicated.
- **P3: NOT RUN** (stop discipline). Binding identity, CLI refusal
  and F1 byte identity remain unexecuted; manifest v3's
  EXECUTION_PROOF_PENDING status remains accurate.
- **Post-run rehash (shell level):** construct_4h.py d47e8df1…,
  validate_input.py 1b83cdcd…, verify_sources.py a0bd2e4c…,
  pilot ledger 7e5ccef0… — all == pre-run pins; the pilot ledger
  is UNCHANGED. Cleanup record: shadow removed by the driver
  (remove_rc 0), main-tree status unchanged, anchor head still
  the pre-execution commit.

## Cleanup (this package)
Shadow worktree removed by the driver; stage root
/home/hatch/workspace/qf_td56_stage removed by the worker after
artifacts were preserved into run_artifacts/; anchor worktree
td56_wt removed and pruned after this result commit; the owner
lease is released LAST, after this commit is verified on
origin/main (spec §8) — its evidence copy is LEASE_EVIDENCE.json.
Main tree untouched (pre-existing UU forward_test/kama_shadow.json
and harness state undisturbed).

## Prohibitions — all honored
No closed family rerun (gate suite, clock suites in either branch
form, NLQUAL, E1, A/D/B — receipts reused and re-verified only);
no candidate/matrix/comparator/canonicalization/extractor/
expectation change (the adapter and the Gate-7 invocation are the
spec's own §3 constructions, committed and hash-gated before
execution); -17 pin untouched; LIVE chain never executed
(candidates only inside the isolated shadow); REQ-S2
UNIMPLEMENTED__HARD_HOLD (recorded, not implemented); no
vendor/API/model calls during execution (pre-run read-only spec
fetch only); 0 credits/spend; fixtures only; no SPT-08, backtest,
performance computation, or holdout; no state/ledger/production
changes (V5.4 harness untouched); no Issue #9; no Yahoo work; no
second attempt; no in-run repair.

## For adjudication
Everything on the -56 remainder list is now EXECUTED AND PASSING
except the P2 proof-digest presence check itself and the
never-reached P3. If the characterization above is accepted, the
successor is minimal: correct the digest check to the matrix's
actual schema (e.g., verify the digest via the supplement's
calendar_proofs key, as the canonical comparison already does) in
a driver v9 under the same lease discipline, then run ONLY the
corrected P2 digest step + P3. The route proof otherwise stands
complete on executed evidence.
