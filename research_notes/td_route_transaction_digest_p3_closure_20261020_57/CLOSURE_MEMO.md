# -57 CLOSURE MEMO — corrected digest check + P3 closure

Task: QF-TD-ROUTE-TRANSACTION-DIGEST-P3-CLOSURE-20261020-57 r1
Spec: Issue #1 comment 6302105446 (adjudication of -56; basis
immutable result commit 686ac81, memo and driver v8).
Budget: ≤45 min, ONE offline attempt, first-failure stop.
Start convention: elapsed from spec fetch 2026-10-20T21:59:15Z.

## Terminal verdict (verbatim, driver-recorded)

TD_ROUTE_TRANSACTION_PROOF_HOLD__UNEXPECTED_ERROR

The corrected P2 digest check EXECUTED AND PASSED (positive +
negative) — the -56 stop point P2_PROOF_DIGEST is closed on
executed evidence. The run then stopped at the FIRST P3 step
(binding identity) on a proof-driver evidence-construction
defect (below). CLI refusal and F1 did NOT run (stop
discipline). Repair minutes: 0. No second attempt.

## Single-dispatch + lease
- Pre-check before ANY file operation (21:59Z): no *td57* stage
  dir, no td57 worktree, no 20261020-57 commit on origin/main,
  no owner lease. SOLE LANE confirmed (parent-verified,
  re-verified by this worker).
- Atomic owner lease (O_CREAT|O_EXCL) acquired OUTSIDE the
  stage BEFORE any staging: /home/hatch/workspace/
  qf_td57_owner_lease.json, acquired_utc 2026-10-20T22:00:15Z,
  owner_session 6a3c60bf-c72a-4a61-977b-b88ba57de559.
- In-driver evidence (proof_results.json owner_lease):
  result VERIFIED_SINGLE_OWNER; task/stage match. Released
  LAST, after the result commit was remote-verified.

## Driver
proof_driver_v9.py sha256
c96ef6dc9c81cb718431dbbfe4688ddb8467bc844b8535bc8d638240666aacbe,
derived from EXECUTED v8 (aad2e97c…, gated byte-identical
in-run) with ONLY the spec-sanctioned changes (identity/lease;
corrected digest check; P3-only main sequence). Diff:
driver_v8_v9.diff (11 hunks). Pre-execution self-checks
24/24 PASS (td57_self_checks.py / td57_self_check_results.json),
including digest-checker unit tests (positive + 4 negatives),
the comparator demonstration + mutation negative, and the
matrix schema fact. Pre-execution commit 9f86d26, verified
ancestor of origin/main BEFORE execution.

## Executed evidence (one attempt, unshare -n, 22:11:59Z→22:12:47Z)
Environment: probes NETWORK_DENIED (curl exit 7); CPython
3.12.3 / pandas 2.2.3 / PMC 4.5.1; FREEZE_EQUALS_LOCK.
- Hash gates: ALL PASS (PKG48 manifest 19/19; route pins;
  -49 candidates; frozen drivers v2/v4/v5/v6/v7/v8; manifest
  v3 9573118c…; TD lock 08b38cfa…; wheelhouse 210b8273…;
  candidate supplement FULL pin 55ad6f40… match).
- Staging §B: git-aware shadow built; collector blob proof
  exit 0, sha256 b683d277cc02a8d27… == PIN_COLLECTOR.
- P2 receipt demonstration (suite NOT rerun): inherited
  comparator on the committed -56 candidate matrix vs the
  accepted -04 run-2 matrix — IDENTICAL, 205/205 cells,
  first_divergence null; -56 negative-control receipt cited
  (negative_controls_identical: true).
- **P2 CORRECTED DIGEST CHECK — PASS (executed):**
  staged supplement sha256
  55ad6f40509ac77f0634b8ab4208bf39017219ae065e240af852ac581c1acca5
  == full pin. POSITIVE: field path `calendar_proofs.<sole
  key>` — sole key ==
  6b030c62fdaf3cd738001a438b6f6a562b381b93b29dd8b299753de6aebe4fa5;
  field path `entries.*.calendar_proof_digest` — REQ-SPT-07
  and REQ-SPT-08 both == the same digest; check ok=true.
  NEGATIVE: the original supplement digest 36bc3a89… substituted
  at both field paths → check ok=false, rejected=true.
  The retired raw-matrix substring check was NOT performed
  (schema-invalid: zero 64-hex strings in either matrix —
  self-check-verified).

## First failure (verbatim) — P3 binding evidence construction
first_failure.key: UNEXPECTED_ERROR
detail: AttributeError: 'NoneType' object has no attribute
'construct_4h'
traceback tail:
  File "proof_driver.py", line 1740, in main — p3(expected_f1)
  File "proof_driver.py", line 1658, in p3 —
    v7.construct_4h is cmod.construct_4h
    AttributeError: 'NoneType' object has no attribute
    'construct_4h'
cmod = sys.modules.get("construct_4h_v3_cliguard") was None.

LABELED POST-HOC CHARACTERIZATION (static, from the pinned
candidate bytes; adjudication's call): the v7 entrypoint
candidate binds the constructor by exact path via
importlib.util.spec_from_file_location("construct_4h_v3_
cliguard", path) + module_from_spec + exec_module, and never
registers the module in sys.modules (pilot_build_v7_clibound.py
lines 69–75). The inherited p3() evidence code (unchanged since
the v2 lineage; P3 never executed in -49..-56 because every
run stopped earlier) assumed a plain-import registration in
sys.modules, and its `construct_is_candidate_function`
expression dereferences cmod unguarded, so the mismatch raised
AttributeError (recorded UNEXPECTED_ERROR) instead of failing
closed as P3_BINDING. The traceback's left operand
(v7.construct_4h) evaluated without error — the entrypoint
imported and its constructor binding executed; the None is the
driver's lookup, not the candidate's binding. NO candidate
defect is indicated: this is a proof-driver evidence defect,
the same family as -49 (checker keying), -53 (extractor
schema) and -54/-55 (staging context). The correct evidence
source is the entrypoint module's own globals (its _c4h_mod:
__file__/sha + identity v7.construct_4h is _c4h_mod.construct_4h).
NOT repaired here — one attempt, no in-run repair.

## Not run (stop discipline)
P3 CLI refusal (full-arg + bare) and P3 F1 end-to-end — both
sit downstream of binding inside p3(). Manifest v3's
EXECUTION_PROOF_PENDING status for the CLI refusal remains
accurate.

## Unchanged state + cleanup
- Pilot ledger: 7e5ccef0… before == after (run_proof post-run
  rehash). Pinned originals rehashed unchanged (construct_4h
  d47e8df1…, validate_input 1b83cdcd…, pilot_build 257d5bb9…,
  verify_sources a0bd2e4c…).
- Driver cleanup: shadow removed (remove_rc 0), main working
  tree status unchanged, anchor repo head still 9f86d26.
- Post-run (this worker, after result verification): stage
  root qf_td57_stage and anchor worktree td57_wt removed +
  pruned (both created by this run); owner lease released
  last. The -55 dirs and all other lanes untouched.

## Elapsed
Spec fetch 21:59:15Z → run end 22:12:47Z → result commit
remote-verified 22:16:56Z. Total 17 min 41 s of the ≤45 cap.
Repair minutes: 0. CORRECTION (labeled): the memo as first
committed estimated ≈26 min before verification completed;
the measured figure is 17m41s, corrected here and in the
manifest by the follow-up correction commit.

## Prohibitions — all honored
No closed family rerun (gate/clock/Gate-7/P2-suite/NLQUAL/
E1/A/D/B — receipts and artifact comparisons only); no
candidate/matrix/comparator/canonicalization/expectation
change beyond the one authorized digest-check correction;
nothing adopted or re-pinned; LIVE chain never executed
(candidates only inside the isolated shadow); REQ-S2
UNIMPLEMENTED__HARD_HOLD (recorded); no vendor/API/model
calls during execution (pre-run read-only spec fetch only);
0 credits/spend; fixtures only; no SPT-08; no backtests/
performance; no holdout; no state/ledger/production changes
(V5.4 untouched; main tree's pre-existing UU
forward_test/kama_shadow.json undisturbed); no Issue #9;
no Yahoo; no second attempt; no in-run repair.

## For adjudication
Everything in the transaction proof is now EXECUTED AND
PASSING except P3's three steps. The successor shape is a
driver-only evidence correction in p3's binding step (source
the constructor module from the entrypoint's globals instead
of sys.modules), then CLI refusal + F1 in one bounded
attempt. The candidates themselves have never failed a check
that actually executed against them.
