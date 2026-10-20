# CONSISTENCY CHECK — static candidate-package linter output (task -48 r1)

Linter: candidate_linter.py (text/hash analysis only; imports no chain module;
executes no chain code). One run, after the single candidate build.

```
PASS C1.route_manifest_status
PASS C1.route_hashes_match_files
PASS C1.route_triple_files
PASS C1.governance_recorded
PASS C2.canonical_bytes
PASS C2.status
PASS C2.supplement_id
PASS C2.base_binding
PASS C2.calendar_version
PASS C2.mechanism_pin
PASS C2.mechanism_path_resolves
PASS C2.lock_pin
PASS C2.single_proof
PASS C2.proof_self_digest
PASS C2.proof_mechanism
PASS C2.entries_point_at_proof
PASS C2.entries_carried_by_value
PASS C2.pins_carried_by_value
PASS C2.provenance_points_at_current
PASS C3.driver_supp_pin
PASS C3.driver_manifest_pin
PASS C3.driver_mech_pin
PASS C3.gate_pins
PASS C3.gate_path_P_DRIVER :: research_notes/td_route_adoption_transaction_prep_20261020_48/live_driver_r5_candidate.py
PASS C3.gate_path_P_SUPPLEMENT :: research_notes/td_route_adoption_transaction_prep_20261020_48/fresh_supplement_v2_candidate.json
PASS C3.gate_path_P_MECHANISM :: research_notes/td_validator_dst_repair_requalification_20261019_44/validate_input_v3_dstfix.py
PASS C3.gate_path_P_MANIFEST :: research_notes/td_fresh_full_manifest_preflight_evidence_20261016/fresh_manifest.json
PASS C3.gate_path_P_LOCK :: research_notes/td_nl_env_rebuild_evidence_20261016/lock_copy.txt
PASS C4.adapter_gate_pin
PASS C4.adapter_gate_path
PASS C5.executor_gate_pin
PASS C5.executor_supp_prefix
PASS C5.executor_manifest_prefix
PASS C5.executor_adapter_pin
PASS C5.executor_adapter_path
PASS C6.no_stale_authoritative_pins
PASS C6.full_old_hash_occurrences_classified :: supplement:1:OLD_SUPP
PASS C7.cycles_anchored_by_unchanged_node :: SCCs>1: collector,supplement
PASS C7.changed_subgraph_acyclic
PASS C7.rollback_complete
PASS C7.no_orphan_candidates
PASS C8.originals_unchanged
PASS C9.candidate_banners

LINTER SUMMARY: 43/43 PASS, 0 FAIL
```

Note on C7: the first linter draft required a fully acyclic pin graph and
flagged the accepted chain's one intentional mutual binding
(supplement <-> collector). The rule was corrected to the SCC form above
BEFORE any commit; no candidate byte changed. See PIN_DAG.md "Graph cycles".
