# Freeze Manifest — Preregistration v1.0 (G5 freeze candidate)

The frozen set for gate **G5** (Mike's signed freeze, §15) is exactly the
files below, identified by SHA-256. Every hash in this manifest was
recomputed on 2026-10-26 from the committed git blobs at the cited
commits (`git show <commit>:<path>`), and each package's own committed
`SHA256_MANIFEST.txt` was re-verified end-to-end against those blobs
(v1.0: 17/17, v1.0.1: 17/17, v1.0.2: 18/18, closure: 1/1 — all OK, no
mismatches). The accompanying script `VERIFY_MANIFEST.py` reproduces
every value in this manifest from the repository alone.

## Package commits (frozen set identity)

| Package | Commit |
|---|---|
| Preregistration v1.0 | `4ffb8fb0aceca750283eebfcba85ac84763ac59f` |
| v1.0.1 amendment (C1 HOLD response) | `247a1c742c8d10c7a9ef9bb82abbfee5d5747e8a` |
| v1.0.2 wording amendment (evidence-label repair) | `4b45a3e48b82064880db28ce8c82079d0655d3e3` |
| Closure addendum (B1 + O9 closed) | `c31c61391c62b09dbfd008bc2cf91e7c511bc1f0` |
| §9 contamination audit package (referenced pin) | `f7b37ccd676f6b99a48e4d814231278af54fa1ff` |

## Headline pins

| Artifact | SHA-256 |
|---|---|
| `PREREG_V10.md` (the frozen protocol text) | `29a0477a13e52ff4467193f69df7ef107048a8801f64c61f43de28d40d2850c6` |
| v1.0 bootstrap seed (contract `fc17041`: first 8 bytes, big-endian, of the `PREREG_V10.md` SHA-256) | `2999475941474119668` (decimal value) |
| `P11_PINS_V10.json` (immutable version pins) | `e7d0b6505ecf81a526d43aafe89a177e2aebfe12c85522dbbdb171c5cec3f3bd` |
| Tier 3 list, v1.2.1 output (container) | `08b670c43b68e38d0fb720dddb6b90710e8acefe7d37f34ad485613a560d2bbd` |
| Tier 3 list, `tier3_list` array canonical hash (`json.dumps(array, indent=2)`) — identical in the v1.0.1 and v1.0.2 outputs | `6468dc73712206111bba732c1b8da61d300373e073cf421391b93510491a5200` |
| Tier 3 list, v1.2 output (v1.0.1 container, superseded wording) | `fbb734465ef7a0b05398d519dd847795b4cdcc3a63dd59e2f0ee8773ed190f48` |
| Closure addendum | `f135e15a8e54ecf2ba2cef2f54be14ec249f023bba7c7e4e1b4a1c75a61e1116` |
| §9 contamination audit doc (pin carried in `P11_PINS_V10.json`) | `ebaca6a0441c0983d6e16deaea92167a9cfeb855586e7f5612cc6dd5223dfd24` |

## Full file manifest — v1.0 (`4ffb8fb`)

| SHA-256 | Path |
|---|---|
| `90a25e37c6c7d3416a16fc2ccacbc15a3cd60d7d1c1850520a0c9660ae3e766a` | `research_notes/prereg_v10_20261026/CHANGELOG_V10.md` |
| `145f9a4124b41e2859a01ac85c8747fe80f891d7717c76ca0cb9815033afbd6a` | `research_notes/prereg_v10_20261026/FREEZE_CHECKLIST_V10.md` |
| `045281e247455e89a6d10a9ad200d9c2a3017293d84b4f93793d22c299752ce0` | `research_notes/prereg_v10_20261026/P10_AUDIT.md` |
| `e7d0b6505ecf81a526d43aafe89a177e2aebfe12c85522dbbdb171c5cec3f3bd` | `research_notes/prereg_v10_20261026/P11_PINS_V10.json` |
| `806520a440e349141c300382c4c30628ae1f9dc6a38de5a65e5ab46e896fffa1` | `research_notes/prereg_v10_20261026/PACKAGE_README.md` |
| `af8aef6421c0bab0677454e5d035da31aa7cd55ceb7ad7d1f8c688a993c2e6d8` | `research_notes/prereg_v10_20261026/POWER_REPORT.md` |
| `29a0477a13e52ff4467193f69df7ef107048a8801f64c61f43de28d40d2850c6` | `research_notes/prereg_v10_20261026/PREREG_V10.md` |
| `b9bef2fef499f5b01a5cb7ee34bbb631db811e50256b9c42ea4d1d023340db9c` | `research_notes/prereg_v10_20261026/REPRODUCIBILITY_RECORD.md` |
| `ebaca6a0441c0983d6e16deaea92167a9cfeb855586e7f5612cc6dd5223dfd24` | `research_notes/prereg_v10_20261026/S9_CONTAMINATION_AUDIT.md` |
| `da199df473bc6f7928e286f7b99dcad77878353dac57e582a571e0f414f674d8` | `research_notes/prereg_v10_20261026/SHA256_MANIFEST.txt` |
| `b4b993e8e23a221c050a6ceab0274ed59e5c25a4973704b4e545646863297ce3` | `research_notes/prereg_v10_20261026/TIER3_RULE_FROZEN.md` |
| `7526f51417df1e32c06c629b06446f787a31729705f971df35af57fcaa990ea6` | `research_notes/prereg_v10_20261026/VERIFICATION_LOG.md` |
| `b18d17149cbc8577b6c0d4e59e75144f16e2f01a4e760489c79c4abc345045b1` | `research_notes/prereg_v10_20261026/bridge_record_20261026.md` |
| `0b39e1d4d447ef6a04fec18d064c439b65e5b7831c682ebb2f6427ce29a8921b` | `research_notes/prereg_v10_20261026/generate_tier3_list.py` |
| `c692694e45815ac7b0992b542a9393788872cb4e290dff84ada0b1f1661df351` | `research_notes/prereg_v10_20261026/stage_packages/preconditions_checklist.md` |
| `831fb73896d70acdd12c089b852f0350ec7cb68cb54687197ad1236ed1d65d49` | `research_notes/prereg_v10_20261026/stage_packages/stage_a_package.md` |
| `5acb62fab3be77bca8ae662c170d7151843997a7df62fb712929e4cffe806c04` | `research_notes/prereg_v10_20261026/stage_packages/stage_b_package.md` |
| `9e7ae05261b02cd6fde20909f86332a7b6cfda82bc330094136f56aba71f5d4e` | `research_notes/prereg_v10_20261026/tier3_list.json` |

## Full file manifest — v1.0.1 amendment (`247a1c7`)

| SHA-256 | Path |
|---|---|
| `1dc092e2841e1e0c653b4442c56524842888021b2eff88843fb1ddff9a158346` | `research_notes/prereg_v10_1_amendment_20261026/AMENDMENT_V10_1.md` |
| `6d5ade617b8ca24b2ee8b41123251ae7ff3fd9d1e98e85660e5e84586cc3dff3` | `research_notes/prereg_v10_1_amendment_20261026/CHANGELOG_V10_1.md` |
| `ec2f5fe2da435ed8d34a2150807c1219514710a1352cac13f413d8dd2f845a49` | `research_notes/prereg_v10_1_amendment_20261026/ERRATUM_PROVENANCE.md` |
| `76abf279819d6223da61e0b21d864a8a96fb710169499096089880f394e4608f` | `research_notes/prereg_v10_1_amendment_20261026/FREEZE_CHECKLIST_V10_1.md` |
| `4d9947db06fd275e00b66fe331e433ed3722552d06c146e3dda63610ca805d1c` | `research_notes/prereg_v10_1_amendment_20261026/README.md` |
| `392259f20851c67af321d117ae8e6a6fb391d5144767a59f0507746c96da48bf` | `research_notes/prereg_v10_1_amendment_20261026/SHA256_MANIFEST.txt` |
| `f6ad753e0eed22af3503c4de8a79da847c07085bb206c5d359c44606f809398e` | `research_notes/prereg_v10_1_amendment_20261026/bridge_record_20261026_v10_1.md` |
| `0e90166bb67698258e003c66f58b13de201c32bad234ce527f887b954311a295` | `research_notes/prereg_v10_1_amendment_20261026/tier3_inputs/INPUTS_AND_GAPS.md` |
| `3bccdbf27bbfd0c89810ee16169bdd149b7351a5370995bcd26d7d0d1ad1ed85` | `research_notes/prereg_v10_1_amendment_20261026/tier3_inputs/ISSUER_MAP.json` |
| `d345fbabeec144f50f117f4d2a6ae7b947e8acb0a4604af64fa869ed25bbd595` | `research_notes/prereg_v10_1_amendment_20261026/tier3_inputs/S4_FROZEN_AGGREGATES.csv` |
| `b9ae9b3644c39341d801212e4d3e80da53bfa2ae1907941003d00a55b673a4c5` | `research_notes/prereg_v10_1_amendment_20261026/tier3_inputs/build_issuer_map.py` |
| `e726d909cdb227c965b9c04636b832113115fe77db896bd1c50de26d7a9fb146` | `research_notes/prereg_v10_1_amendment_20261026/tier3_inputs/build_s4_table.py` |
| `c7112909009aa605a380b198d07b3ebd421fa44ce5a4751e830c8496ca535e04` | `research_notes/prereg_v10_1_amendment_20261026/tier3_inputs/exclusion_universes.json` |
| `d67ded42c023f9437e03e5fe3dc307bcaa3e6d7c2f8f1bfdf8c3dd594d90ff36` | `research_notes/prereg_v10_1_amendment_20261026/tier3_inputs/generate_tier3_list_v1_2.py` |
| `464e82847212024e3c2b871c487c4ac6a3af854763f82dbd124ed4987b39b912` | `research_notes/prereg_v10_1_amendment_20261026/tier3_inputs/sources/nasdaq_screener_raw.json` |
| `8e72f822228a2536b0e712e5ee91c14e30db07408cc8863a6d64cb1bac1c2c19` | `research_notes/prereg_v10_1_amendment_20261026/tier3_inputs/sources/nasdaqlisted.txt` |
| `67c1e321790341bf89172e2dc30119e1a39180d3dd4b2d7cb4e420ba02305ca6` | `research_notes/prereg_v10_1_amendment_20261026/tier3_inputs/sources/otherlisted.txt` |
| `fbb734465ef7a0b05398d519dd847795b4cdcc3a63dd59e2f0ee8773ed190f48` | `research_notes/prereg_v10_1_amendment_20261026/tier3_inputs/tier3_list_v1_2.json` |

## Full file manifest — v1.0.2 wording amendment (`4b45a3e`)

| SHA-256 | Path |
|---|---|
| `e6785ebea9d634e5cbf7f0ddb1fa82c56fec09b0376ffb278789eb2c1962c73d` | `research_notes/prereg_v10_2_wording_20261026/AMENDMENT_V10_2.md` |
| `6f53999a6a9880969820942d61101ee2a2bfd6cd43543c2b844fc061ad6b3af5` | `research_notes/prereg_v10_2_wording_20261026/CHANGELOG_V10_2.md` |
| `5af4007cd95c2112d90283d2ef830638c4d72fe26a80af8197fbf782f01430e1` | `research_notes/prereg_v10_2_wording_20261026/FREEZE_CHECKLIST_V10_2_ADDENDUM.md` |
| `06139a5fe2b7b79e1cfb951bd9ef5fd6229cc24fa34fae070aaed078a6228e7c` | `research_notes/prereg_v10_2_wording_20261026/README.md` |
| `4bcc13f0edc348b6ef5050c51a4574435254afc3bef85c3c160fa499e904df32` | `research_notes/prereg_v10_2_wording_20261026/SHA256_MANIFEST.txt` |
| `1aa3a157e4f388f163755e3969a28d8e09a901eefa50c207d6070fdaa0f49ee5` | `research_notes/prereg_v10_2_wording_20261026/VERIFICATION_V10_2.md` |
| `1bae168eb00a46c9b069391539e4e3b23e626159eba765ef4c143d2c5a763112` | `research_notes/prereg_v10_2_wording_20261026/bridge_record_20261026_v10_2.md` |
| `cea70c7e616d598cb3dfb9625fb6be97dc93204e51c9b77236897979fa78a14c` | `research_notes/prereg_v10_2_wording_20261026/tier3_inputs/INPUTS_AND_GAPS.md` |
| `3bccdbf27bbfd0c89810ee16169bdd149b7351a5370995bcd26d7d0d1ad1ed85` | `research_notes/prereg_v10_2_wording_20261026/tier3_inputs/ISSUER_MAP.json` |
| `d345fbabeec144f50f117f4d2a6ae7b947e8acb0a4604af64fa869ed25bbd595` | `research_notes/prereg_v10_2_wording_20261026/tier3_inputs/S4_FROZEN_AGGREGATES.csv` |
| `b9ae9b3644c39341d801212e4d3e80da53bfa2ae1907941003d00a55b673a4c5` | `research_notes/prereg_v10_2_wording_20261026/tier3_inputs/build_issuer_map.py` |
| `e726d909cdb227c965b9c04636b832113115fe77db896bd1c50de26d7a9fb146` | `research_notes/prereg_v10_2_wording_20261026/tier3_inputs/build_s4_table.py` |
| `c7112909009aa605a380b198d07b3ebd421fa44ce5a4751e830c8496ca535e04` | `research_notes/prereg_v10_2_wording_20261026/tier3_inputs/exclusion_universes.json` |
| `5a1e074539645f687c4b54842b63dedbdf51fdf12cad0a64221ace4bf7d01fa6` | `research_notes/prereg_v10_2_wording_20261026/tier3_inputs/generate_tier3_list_v1_2.py` |
| `464e82847212024e3c2b871c487c4ac6a3af854763f82dbd124ed4987b39b912` | `research_notes/prereg_v10_2_wording_20261026/tier3_inputs/sources/nasdaq_screener_raw.json` |
| `8e72f822228a2536b0e712e5ee91c14e30db07408cc8863a6d64cb1bac1c2c19` | `research_notes/prereg_v10_2_wording_20261026/tier3_inputs/sources/nasdaqlisted.txt` |
| `67c1e321790341bf89172e2dc30119e1a39180d3dd4b2d7cb4e420ba02305ca6` | `research_notes/prereg_v10_2_wording_20261026/tier3_inputs/sources/otherlisted.txt` |
| `f7c19f8736c8faaf9995eb4c1b7fa0c27ac6d303fe9402d0716e87367d62fb4e` | `research_notes/prereg_v10_2_wording_20261026/tier3_inputs/test_rank12_fixture.py` |
| `08b670c43b68e38d0fb720dddb6b90710e8acefe7d37f34ad485613a560d2bbd` | `research_notes/prereg_v10_2_wording_20261026/tier3_inputs/tier3_list_v1_2.json` |

## Full file manifest — closure addendum (`c31c613`)

| SHA-256 | Path |
|---|---|
| `f135e15a8e54ecf2ba2cef2f54be14ec249f023bba7c7e4e1b4a1c75a61e1116` | `research_notes/prereg_closure_20261026/CLOSURE_ADDENDUM_20261026.md` |
| `dab6da555376d24eac3be1b203b41320a1194dac076a3aa3b7c84ebe273097c6` | `research_notes/prereg_closure_20261026/SHA256_MANIFEST.txt` |

Any byte change to any file above is an amendment: it must be committed
as a new package, logged, and — for `PREREG_V10.md` — the bootstrap seed
recomputed and re-recorded. Nothing outside this manifest is part of
the frozen set.
