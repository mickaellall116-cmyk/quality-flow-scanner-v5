# QF-VALIDATION-SOURCE-ADOPTION-20261018-23 r1 — Adoption Memo

Spec: GitHub Issue #1 comment 6253626132 (verdict
`EXACT_BYTES_VERIFIED__STATIC_ADOPTION_READY__VALIDATION_CONTRACT_STILL_HOLD`).
Mode: offline/static only. Cap ≤20 min; 0 repair/rerun.

## Action

Copied the four byte-identical verified files out of the -22 quarantine
(`research_notes/validation_missing_bytes_recovery_20261018_22/QUARANTINE_UNREVIEWED_NOT_ADOPTED/`,
source commit `8e0a18750dc36b5fae5becfeb6bdd2a478370686`) to their historical
research paths. All four destinations were ABSENT before the copy — no
conflicts, no overwrites; the fail-closed rule was armed but never triggered.
Quarantine originals remain in place (adoption by copy, not move).

| Destination | SHA-256 | Outcome |
|---|---|---|
| `pine_signal_quality/pine_signal_quality.py` | `b1b39ee8d0bd4bbb1387b3ce54c7345c1f8dd622f94a5ed390c989fed1d39e69` | RESTORED |
| `pine_ranking/pine_ranking.py` | `77afae0df120e3a2ad77a6d2d43247c8aea0ad296f08c273bff7d1cc833aaae6` | RESTORED |
| `pine_exposure/pine_exposure.py` | `9f646161c27f6b28febe0980d03665bc9c1502fb844d37be6fd1d72ee45102be` | RESTORED |
| `canonical_baseline/scripts/fetch_4h.py` | `2a4994a26dbb98e244a14173a06697476835206c3d8d268ad21900dd43e0cbeb` | RESTORED |

Origin blobs and prior pin sources per file are recorded in
`validation_source_adoption_20261018_23/ADOPTION_MANIFEST.json`.

## Static checks (parse only — nothing imported or executed)

- AST parse OK for all four files.
- Required definitions present: `load_benchmarks` (pine_signal_quality),
  `compute_features` (pine_ranking), `SECTOR` (pine_exposure),
  `resample_4h` (fetch_4h).
- SECTOR statically extracted via `ast.literal_eval`: exactly 51 entries;
  `sha256(json.dumps(SECTOR, sort_keys=True))` =
  `9bab23b72dcb18d04935071f2bec94955cb8fa9df96f50dc11b72990dcd7fbb9` —
  exact match to manifest rev2 pin.
- Post-copy file hashes equal the -22 manifest hashes exactly.

## Not cured here (remain MISSING / HOLD)

- Operative split-exclusion protocol definition — LOST per -22; no
  reconstruction attempted.
- Exact sealed holdout window dates — absent; holdout contents were not
  accessed in any way.

## Prohibitions honored

No module imported or executed; no test run; no data capture; no
vendor/model/API calls (network used only for the spec fetch and the git
push); no installs; no credentials; no credits; no holdout access; no
performance/backtest computation; no strategy edits; no writes to
live/production/ledger paths; no Issue #9 work; no other frozen/pinned
file edited.
