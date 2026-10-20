# -47 NLQUAL stage inventory (stage-assembly receipt)

Stage root at execution: `/tmp/td47_stage` (fresh assembly for this
task; nothing carried over from the -46 stage directory). Assembly =
byte copies from the source refs below + one patch application
(staged runner). Every member was SHA-256 gated before execution;
gates are recorded in `proof_results.json#hash_gates` and the
pre-run section of `env_receipt.txt`. The static import-closure
derivation is in `IMPORT_CLOSURE.json`.

| Stage path | Source ref | SHA-256 | Purpose |
|---|---|---|---|
| `run_nlqual_matrix.py` | repo `research_notes/td_closed_session_classifier_nlqual_evidence_20261015/run_nlqual_matrix.py` (`3e85efe4…`) + `nlqual_runner.diff` (this package; only the two mechanism-hash expectations → candidate) | `91cfa59b2677f2205ed471bb2d34f0e47814dc9ccd84bfa0fbdb0cf9c8a262e2` | NLQUAL 28-case matrix runner (staged bytes identical to -44/-45/-46 staging) |
| `nlqual_supplement.json` | -46 package staged record `nlqual_supplement_staged.json` (= NL candidate `9c712330…` with `mechanism_module_sha256` re-pinned to the validator candidate) | `7fe1fd2f7c2217515f364a603e5effa6134550027bd7e95a09b239e04a755bbb` | Supplement template supplied to the collector by the matrix |
| `candidate_validator.py` | -44 package `validate_input_v3_dstfix.py` | `ca3bafd87e7cb439d538ddf924aa08a029dd2c9bb32b485f61acbeea91429cc6` | Validator candidate (frozen); gate copy |
| `candidate_entrypoint.py` | -45 package `pilot_build_v6_dstfix.py` | `442e56cc16bbbb7ba8f3a62910d92bfcd07d85d0bb88ca2346d26b0bdcd2cba6` | Entrypoint candidate (frozen); gate copy for the pair record (Family C drives the collector, not the entrypoint) |
| `nlqual/td_lifecycle_repair_candidate/td_min_collector.py` | branch commit `ab254c3`:`research_notes/td_lifecycle_repair_candidate/td_min_collector.py` | `b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c` | Collector under regression |
| `nlqual/td_lifecycle_repair_candidate/p2_spot_supplement_v2.json` | branch commit `ab254c3`:`research_notes/td_lifecycle_repair_candidate/p2_spot_supplement_v2.json` | `cccd52260b2c80a7110559ed100111cf3634e7901daef2f883c6517b68255b31` | Shipped supplement read by the ELIG08 case |
| `nlqual/pilot_harness/validate_input.py` | validator candidate (same bytes as `candidate_validator.py`) | `ca3bafd87e7cb439d538ddf924aa08a029dd2c9bb32b485f61acbeea91429cc6` | Mechanism position: sibling module imported by collector + runner |
| `nlqual/pilot_harness/rate_limiter.py` | repo `research_notes/pilot_harness/rate_limiter.py` | `06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64` | Sibling closure member (collector line 34; runner limiter) |
| `nlqual/pilot_harness/verify_sources.py` | repo `research_notes/pilot_harness/verify_sources.py` | `a0bd2e4cdce44be5d9fcc1d7c21046391d36c9bd366a959df03bf5d19c9a79e0` | Sibling closure member (collector line 35) — **the -46 omission, now staged and verified** |
| `nlqual/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/pine_backtest.py` | repo `research_notes/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/pine_backtest.py` | `447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5` | Runtime data closure: `verify_directory(ARCHIVAL_DIR, PINNED)` target at the path resolved from the staged `verify_sources.py` |
| `nlqual/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/scanner_rules.py` | repo `research_notes/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/scanner_rules.py` | `7db282ddfc150c9e9aec7d8f1f10f439ce7e296da2d69da38f97ed8cbec70cac` | Runtime data closure (same as above) |
| `integration_requirements.lock` | -46 package staged record (TD lock) | `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068` | `--lock` argument; freeze-equality target |
| `requirements_hashes.txt` | -46 package staged record | `037af3d59261497b2f37dc5bb8cc8afa0af4229e4d805734394914680b263f6e` | Wheelhouse install pins (`--require-hashes`) |
| `network_probe.py` | -46 package record | `2b66f5e7ab655b4eaf331fa75f8c1be498f381b35f99afda1b3195ddd76328c7` | Isolation probe (must report NETWORK_DENIED) |
| `proof_driver.py` | written for this task (stage-assembly/receipt code only) | in `SHA256_MANIFEST.txt` | Hash gates → static closure derivation → two matrix invocations → verdict |
| `run_proof.sh` | written for this task | in `SHA256_MANIFEST.txt` | Single offline orchestration (`unshare -n`) |

Repo inputs consumed in place (not staged; hash-gated):
preserved body `REQ-SPT-07.rejected.bin` `3339c341…` and SPOT8
manifest `acquisition_manifest_v2_spot8.json` `ddff040f…` (paths in
`REGRESSION_MEMO.md` §3). Wheelhouse manifest
`~/workspace/td_nl_wheelhouse_20261016/SHA256_MANIFEST.txt`
`210b8273a15cc7317b4a8029198f8d6e1401c1e375acdbe7f8602167c13e815b`.

Stage-assembly diff vs -46: the -46 stage omitted
`nlqual/pilot_harness/verify_sources.py` and the entire
`nlqual/recovery_4h_20261004/…` archival subtree. -47 adds exactly
those members (byte copies of the repo pins above) and the static
closure/archival verification in the driver. No other difference in
members, bytes, arguments, or expectations.
