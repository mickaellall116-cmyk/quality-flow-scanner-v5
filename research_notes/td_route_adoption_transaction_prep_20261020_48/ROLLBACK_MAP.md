# ROLLBACK MAP — TD route adoption transaction (task -48 r1)

No candidate in this package overwrites any accepted/live file; all originals remain byte-identical in place. Adoption (a future, separately authorized transaction) designates the candidate executor as chain head. Rollback = withdraw that designation; the pre-transaction chain (executor r4 head) is intact by construction. The same table is the restore set if a future transaction instead substitutes bytes in place.

## Per-node restore set

| node | candidate sha256 | restore to (path) | restore sha256 |
|---|---|---|---|
| manifest | — (unchanged) | research_notes/td_fresh_full_manifest_preflight_evidence_20261016/fresh_manifest.json | `71aade8bfbb1f94b…` |
| supplement | `55ad6f40509ac77f…` | research_notes/td_fresh_full_manifest_preflight_evidence_20261016/fresh_supplement.json | `3cbdbf63fd49b021…` |
| proof | `6b030c62fdaf3cd7…` | fresh_supplement.json:calendar_proofs | `36bc3a89bd266b9d…` |
| validator | `ca3bafd87e7cb439…` | research_notes/pilot_harness/validate_input.py | `1b83cdcd4f6e2aaa…` |
| driver | `d11c6b587c028c26…` | research_notes/td_fresh_live_driver_integration_evidence_20261016/live_driver.py | `5fed45242eb5ec46…` |
| gate | `94ef967ca832faea…` | research_notes/td_policy_a_live_readiness_packet_20261017_11/dispatch_gate_r4.py | `b53996454650dafc…` |
| adapter | `6980b5b3c887ea7e…` | research_notes/td_live_dryrun_clock_adapter_binding_20261017_19/live_dry_run_adapter.py | `e8605669db902c3e…` |
| executor | `bbc23616b0b8c62f…` | research_notes/td_live_dryrun_clock_adapter_binding_20261017_19/live_readiness_executor_r4.py | `e792b8b2b776adc7…` |
| entrypoint | `442e56cc16bbbb7b…` | research_notes/pilot_harness/pilot_build.py | `257d5bb99bcbae50…` |
| constructor | — (unchanged) | research_notes/pilot_harness/construct_4h.py | `d47e8df14ec5f6f6…` |
| resampler | — (unchanged) | canonical_baseline/scripts/fetch_4h.py | `2a4994a2 (prefix…` |
| collector | — (unchanged) | research_notes/td_lifecycle_repair_candidate/td_min_collector.py (git blob @ab254c3) | `b683d277cc02a8d2…` |
| lock | — (unchanged) | research_notes/td_nl_env_rebuild_evidence_20261016/lock_copy.txt | `08b38cfa1880d328…` |
| wheelhouse | — (unchanged) | /home/hatch/workspace/td_nl_wheelhouse_20261016/SHA256_MANIFEST.txt | `210b8273a15cc731…` |

## Post-rollback verification

- Recompute sha256 of every current_path in this map == restore_to_sha256 (the -41 binding matrix values).
- Gate PIN set == r4 set (PIN_SUPPLEMENT 3cbdbf63..., PIN_MECHANISM 1b83cdcd..., PIN_CALENDAR_PROOF 36bc3a89..., PIN_DRIVER 5fed4524...).
- Driver EXPECTED_SUPPLEMENT_SHA256 == 3cbdbf63...; executor PIN_R4_GATE == b5399645...; adapter PIN_R4_GATE == b5399645....
- All standing HOLDs unchanged; no ledger/state writes occur in prep, adoption-designation, or rollback.

Full hashes: rollback.json (machine-readable).
