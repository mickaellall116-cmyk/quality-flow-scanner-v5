# INSPECTED FILES — task -41 r1 (all hashes recomputed this pass)

## Pins verified byte-exact
| Artifact | Location | sha256 (prefix) |
|---|---|---|
| FRESH manifest (file == canonical digest) | td_fresh_full_manifest_preflight_evidence_20261016/fresh_manifest.json | 71aade8b |
| r2 package manifest ("ef82fb37" referent) | td_fresh_full_manifest_preflight_evidence_20261016_r2/SHA256_MANIFEST.txt | ef82fb37 |
| FRESH supplement | td_fresh_full_manifest_preflight_evidence_20261016/fresh_supplement.json | 3cbdbf63 |
| Live driver (-04) | td_fresh_live_driver_integration_evidence_20261016/live_driver.py | 5fed4524 |
| Dispatch gate r4 | td_policy_a_live_readiness_packet_20261017_11/dispatch_gate_r4.py | b5399645 |
| Credential resolver | td_credential_helper_path_binding_20261017_08/credential_resolver.py | c8271193 |
| Sanctioned helper (live file) | /opt/hatch/skills/skill-creator/bin/dynamic_credentials.py | 8b1f42e8 |
| Source ledger | pilot_harness/credit_ledger.json | 7e5ccef0 |
| Candidate ledger | td_ledger_compat_card_binding_20261017_07/candidate_credit_ledger.json | 79ff4844 |
| Policy A canonical digest (pin value in gate :90 / executor :122) | TD_GATE3_ATTESTATION_POLICY_20261017.md chain | 5d9d82ca |
| Executor r4 | td_live_dryrun_clock_adapter_binding_20261017_19/live_readiness_executor_r4.py | e792b8b2 |
| Live dry-run adapter | td_live_dryrun_clock_adapter_binding_20261017_19/live_dry_run_adapter.py | e8605669 |
| Collector @ab254c3 | td_lifecycle_repair_candidate/td_min_collector.py | b683d277 |
| Original supplement @ab254c3 | td_lifecycle_repair_candidate/p2_spot_supplement_v2.json | cccd5226 |
| NL451 candidate supplement (2 copies on main, identical) | td_p2_spot_v2_execution_preflight_evidence_20261015/ + td_closed_session_classifier_nlqual_evidence_20261015/ p2_spot_supplement_v2_nl20261015_candidate.json | 9c712330 |
| Validator (main AND @ab254c3, identical) | pilot_harness/validate_input.py | 1b83cdcd |
| TD lock (pin value; lock copy in td_nl_env_rebuild_evidence_20261016) | — | 08b38cfa |
| Wheelhouse manifest (explicit pin, per -40 minor note) | ~/workspace/td_nl_wheelhouse_20261016/SHA256_MANIFEST.txt | 210b8273 |

## Also inspected (read-only)
- live_driver.py header/gap notes :8-63, reconcile :332-360, constructor
  checks :431-447, classify_closed :529-560.
- dispatch_gate_r4.py pins/paths :50-100, derive_calendar :169-248,
  packet check :422, env/lock gates :540-551, Gates 6-7 :561-590.
- live_readiness_executor_r4.py pins :116-124; full-text search for
  supplement/validator/classifier/calendar references (0 hits).
- live_dry_run_adapter.py :34-52, :125-162.
- td_min_collector.py @ab254c3 :507, :527, :531, :549.
- validate_input.py :56-57 (both refs).
- construct_4h.py :49-50 (observation F3).
- -40 package: ADOPTION_CANDIDATE_RECORD.md :27 (SPOT8 scope caveat).
- -20A preflight memo (chain citation of fresh supplement + executor).
- Chain head commit 39329038879d (ancestor of origin/main — verified).

## Sweep scope
- Refs searched: origin/main (full research_notes tree), classifier
  branch commit ab254c3 tree, recovery-4h-20261004 (via main's committed
  recovery_4h_20261004/ evidence tree + branch ref presence).
- Patterns: `5.5.0`, `cccd5226`, `9c712330`, `fresh_supplement`,
  `pandas_market_calendars` imports / `get_calendar` in td_*/pilot_harness
  code, `ef82fb37`, `3cbdbf63`.
- Results: enumerated in BINDING_MATRIX.md (Residual Sweep §1-5).

## Prohibitions honored
No tests or components executed; no code/supplement/ledger/state edits;
no TD/vendor/API/helper calls; no credits/tokens; no environment created;
no market data; no holdout access; no production changes (V5.4 harness
untouched); no Issue #9 work; no repairs of anything found. The only
writes are the four new files of this package, committed from a temp
worktree off origin/main (the main tree's harness merge state untouched).
