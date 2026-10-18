# QF-VALIDATION-MISSING-BYTES-RECOVERY-20261018-22 r1 — WORK RESULT

**Verdict: 3 of 4 items EXACT_RECOVERED (pin-verified); item 4 split — fetch_4h.py EXACT_RECOVERED, operative split-exclusion definition LOST.**
Elapsed ~4 min of the ≤20 cap (spec fetched 2026-10-18T17:57:41Z; package complete 18:01:30Z). Repairs: 0. Reruns: 0.
All recovered bytes are preserved ONLY in the isolated quarantine directory of this package, marked UNREVIEWED / NOT ADOPTED. Nothing was integrated, imported, executed, or copied to any live path.

## Why the -21 matrix said MISSING, and why that was incomplete

The -21 search covered the committed tree of `main`. The module sources were in fact committed on the `recovery-4h-20261004` lineage (reachable via merge commit `507d29f`, 2026-09-29; branches `recovery-4h-20261004`, `qf-r2-preflight-20261004`, `hardening-20261004`) and later left the working tree — the package directories in the current checkout contain only `__pycache__`. The git objects were never pruned, so exact bytes survive as blobs. Two independent committed records pin their SHA-256s, and all three match byte-for-byte.

## Item 1 — `pine_signal_quality.py` / `load_benchmarks` (field 1.3): EXACT_RECOVERED

- Origin: git blob `dd0422f8f04cc722d6089a7e862da53454bc1a3b`, path `pine_signal_quality/pine_signal_quality.py`, reachable from commit `507d29f` / branch `recovery-4h-20261004`.
- Bytes SHA-256: `b1b39ee8d0bd4bbb1387b3ce54c7345c1f8dd622f94a5ed390c989fed1d39e69` — equals the independent pin in `cp1_bundle/02_c1_ledger/c1_240_trade_ledger.json` line 43. EXACT match.
- Signature evidence (static text): `def load_benchmarks():` at line 30 of the recovered bytes — the exact symbol the pinned consumers import.
- Corroboration: surviving `__pycache__/pine_signal_quality.cpython-312.pyc` (sha256 `75e716d2…`) embeds source size 9945 = recovered source size, source mtime 1791343050.
- Quarantine copy: `QUARANTINE_UNREVIEWED_NOT_ADOPTED/pine_signal_quality.py`.
- Minimal next action: reviewer verifies the quarantined hash against the ledger pin and, if adopting, commits the bytes to the canonical path in a separate adoption task (not this one).

## Item 2 — `pine_ranking.py` / `compute_features` (field 2.4): EXACT_RECOVERED

- Origin: git blob `48b3408f43242b5cf3dd8a561361835920363c2b`, path `pine_ranking/pine_ranking.py`, same provenance as item 1.
- Bytes SHA-256: `77afae0df120e3a2ad77a6d2d43247c8aea0ad296f08c273bff7d1cc833aaae6` — equals the C1 ledger pin (line 41). EXACT match.
- Signature evidence (static text): `def compute_features(all_trades, data, bench):` at line 95 — replaces the docstring-prose-only formula status; the computation bytes now exist.
- Corroboration: surviving pyc sha256 `ba52887a…` embeds source size 15745 = recovered source size.
- Quarantine copy: `QUARANTINE_UNREVIEWED_NOT_ADOPTED/pine_ranking.py`.
- Minimal next action: same separate-adoption route as item 1.

## Item 3 — `pine_exposure.py` / 51-symbol `SECTOR` (field 1.4): EXACT_RECOVERED — canonical digest MATCH

- Origin: git blob `3757881fe50d7fd3f326991b587a779d55861c30`, path `pine_exposure/pine_exposure.py`, same provenance.
- File bytes SHA-256: `9f646161c27f6b28febe0980d03665bc9c1502fb844d37be6fd1d72ee45102be` — equals BOTH independent pins: C1 ledger line 42 AND `complete_manifest_rev2.json` `files["pine_exposure/pine_exposure.py"]`.
- Canonical serialization check (the manifest's sector-map test): the `SECTOR` literal statically extracted from the recovered source (AST literal evaluation of the assignment only; module never imported/executed) contains exactly **51 entries**, and `sha256(json.dumps(SECTOR, sort_keys=True))` = `9bab23b72dcb18d04935071f2bec94955cb8fa9df96f50dc11b72990dcd7fbb9` — **EXACT MATCH** to the manifest pin `sector_map.sha256`. (Alternative serializations tested and rejected: compact separators, insertion-order, indent=2, repr of sorted items.)
- Corroboration: surviving pyc sha256 `c6c3fcc7…` embeds source size 16483 = recovered source size.
- Quarantine copy: `QUARANTINE_UNREVIEWED_NOT_ADOPTED/pine_exposure.py`.
- Minimal next action: same separate-adoption route; on adoption, field 1.4's pin test is already proven reproducible.

## Item 4 — split-exclusion definition + `canonical_baseline/scripts/fetch_4h.py` (field 3.6): SPLIT

### 4a. `fetch_4h.py`: EXACT_RECOVERED
- Origin: git blob `aa8e85371da0fd55a3c1b0fbc34931c9c44af37a`, path `canonical_baseline/scripts/fetch_4h.py`, same provenance.
- Bytes SHA-256: `2a4994a26dbb98e244a14173a06697476835206c3d8d268ad21900dd43e0cbeb` — equals the `complete_manifest_rev2.json` pin for that exact path. EXACT match. Size 4356 bytes.
- Divergent candidates recorded, NOT the pinned bytes: (i) the surviving `canonical_baseline/scripts/__pycache__/fetch_4h.cpython-312.pyc` (sha256 `8d1dd9ab…`) embeds source size **4153 ≠ 4356** — a compiled artifact of a different, unpinned source revision: CANDIDATE_UNPROVEN, left in place, not preserved as evidence of the frozen fetch; (ii) `~/workspace/canonical-stage-a/canonical_stage_c/fetch_4h.py` (7753 bytes, sha256 `98325752…`) is a later Stage-C variant: CANDIDATE_UNPROVEN for this field.
- Quarantine copy: `QUARANTINE_UNREVIEWED_NOT_ADOPTED/fetch_4h.py`.
- Minimal next action: same separate-adoption route; separately, the 4153-byte pyc divergence should be explained or discarded in review — it is not the frozen fetch.

### 4b. Operative split-exclusion definition: LOST
- The recovered `fetch_4h.py` contains **no** split-exclusion logic (only comments disclosing that Yahoo retro-applies splits to intraday bars). Every committed reference found — prereg rev2 §2, `data_tier_metadata.md` lines 15/22 — names a "frozen split-exclusion protocol" in prose without operative content: no exclusion windows, thresholds, symbol/date lists, or executable definition exist in any searched location.
- Failure-memory key: `SPLIT_EXCLUSION_PROTOCOL_DEFINITION_MISSING`.
- Minimal next action: either locate the protocol in an unsearched external archive, or re-specify it in a new frozen amendment before any baseline data pull (the -21 action for field 3.6). Do NOT reconstruct it from prose under this task — none was attempted.

## Holdout-window note (parent brief item 4 — superseded by the spec's item 4)

The fetched spec's item 4 is the split-exclusion/fetch item above, not the holdout window (field 4.4). No holdout search was run under this task and **no sealed holdout data was opened, hashed, enumerated, or accessed in any way**. Field 4.4 remains MISSING per -21, untouched here.

## Locations and methods searched

- Git object store of `quality-flow-scanner-v5`: `git rev-list --objects --all` path search across all refs (15044 objects enumerated), `git log --all` per target path, stash list (2 stashes, harness files only), blob extraction + SHA-256 against two independent committed pin records (C1 ledger; manifest rev2).
- Working tree outside git: full `find` over `~/workspace` and `~` for the four filenames — package dirs contain only `__pycache__` (sources deleted from the tree Oct 7 era); byte-identical duplicate pyc set found in `~/workspace/goals/quality-flow-research-bridge/hidden_files/pyc_preservation_20261018/` (preserved 2026-10-18 15:46; hashes identical to worktree pycs for all five artifacts).
- Sibling repo `~/workspace/canonical-stage-a` (fetch_4h variant; hash/size mismatch, recorded above).
- Recovery bundles: `research_notes/recovery_4h_20261004/` (cp1_bundle manifests/ledger = the pin records; archival_sources_v1 consumers).
- Archives on disk (zip/tar inventory): `claude_handoff_bundle_20261003.zip`, `CLAUDE_QF_CANONICAL_AUDIT_REV5_SOURCE_BUNDLE.zip` — not opened: the git-blob recovery already produced pin-exact bytes for every module target, and the bundles predate/are redundant to that proof; the split-exclusion definition's absence was established across all text records searched (grep over research_notes/ and new_system/).
- /tmp: no candidate files.

## Scope confirmation

Zero vendor/helper/API/model calls (the only network use was fetching the spec comment and this delivery push); zero credits; zero market data; zero performance/backtest computation; zero data capture; zero live-path/ledger writes; zero production/trading changes; zero Issue #9 work; sealed holdout contents untouched. No module was imported or executed — verification used hashes, git objects, and static text/AST-literal inspection only. No decompilation was performed or needed. No frozen/pinned file was modified; the only writes are this package's new files. Recovered bytes are quarantined pending independent review; adoption is a separate decision.
