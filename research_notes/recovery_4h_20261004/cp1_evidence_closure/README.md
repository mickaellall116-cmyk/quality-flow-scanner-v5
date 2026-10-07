# CP1 Evidence Closure

**Date:** 2026-10-06
**Amendment:** 2026-10-07 per ChatGPT bounded amendment (Issue #1 comment 6028744990)
**Assignment:** ChatGPT bounded evidence closure (Issue #1 comment 6028234879)
**Immutable evidence pin:** `84942a6929258a0c316a6e849a7480c286013d95` (not modified)
**Status:** Evidence closure only. No performance computed. No production changes.

## Contents

| File | Purpose |
|------|---------|
| `SUPERSESSION.md` | Stale `trade_intersection.json` supersession: three forms documented (rev1 standalone, rev2 standalone, canonical shards), field-level diffs, explicit SUPERSEDED statement |
| `SCANNER_RULES_IDENTITY.md` | `scanner_rules.py` hash investigation: branch divergence explained (forensic-line Version A `7db282dd…` vs hardening-line Version B `62aa743a…`); manifest is internally consistent. **2026-10-07:** hash-algorithm wording corrected (SHA-256 vs Git blob SHA-1) |
| `SOURCE_BYTE_RECOVERY.md` | Byte recovery results: all three source files match manifest hashes locally; no recovery needed. **2026-10-07:** full (untruncated) hashes; hash-algorithm precision note |
| `RESAMPLER_XNYS_EVIDENCE.md` | Resampler/XNYS evidence: timezone origin, 08:30/12:30 vs 06:30/10:30/14:30 label distinction, early-close behavior, completed-bar causality, cache preservation, omitted-review boundary. **2026-10-07:** §2 mechanism corrected (see below) |
| `RESAMPLER_MECHANISM_FIXTURE.md` | **NEW 2026-10-07:** the real DST-regime anchor mechanism derived with a passing synthetic fixture — supersedes the §2 mechanism in RESAMPLER_XNYS_EVIDENCE.md |
| `resampler_grid_fixture.py` | **NEW 2026-10-07:** runnable synthetic fixture proving the mechanism (all assertions pass; no market-data download) |
| `INTERVAL_OVERLAP_CHECK.md` | Interval-overlap check. **2026-10-07:** two definitions (F/I) reported separately; T161 entry corrected; checker code + full CSV published |
| `interval_overlap_checker.py` | **NEW 2026-10-07:** the actual checker code (runnable) |
| `interval_overlap_full_output.csv` | **NEW 2026-10-07:** full per-trade output (240 rows, both definitions) |
| `CP2_PREFLIGHT_PROPOSAL.md` | CP2 preflight proposal — proposal only, no execution. **2026-10-07:** R1/R2 split (defective-grid reproduction vs corrected-grid reconstruction); R2 marked UNREPRODUCIBLE without 1H inputs; T7 quarantine rule (preserve-without-inspecting, never delete) |
| `archival_sources_v1/` | **NEW 2026-10-07:** remote-readable archival copies of the four manifest-pinned source files + `ARCHIVAL_INDEX.md` (full SHA-256, Git blob SHA-1, byte lengths) |
| `README.md` | This file |
| `SHA256_MANIFEST.txt` | SHA-256 of all files in this directory |

## Reproduction / verification commands

Run from the repo root (`~/workspace/quality-flow-scanner-v5`):

```bash
# 1. Verify supersession claims (Item 1)
cd research_notes/recovery_4h_20261004/cp1_followup
sha256sum trade_intersection.json
# expect: a457e7a10845650eeb2b4be6c7a2b0ca02c91dff2667f5a4687b4e8b6b460684
cat trade_intersection.json.shard00 trade_intersection.json.shard01 \
    trade_intersection.json.shard02 trade_intersection.json.shard03 | sha256sum
# expect: 02608fd49331e5d795ac678440c7d9792f74d577eeb454d7bd68686b234fd872

# 2. Verify scanner_rules.py identity (Item 2)
sha256sum scanner_rules.py
# expect: 7db282ddfc150c9e9aec7d8f1f10f439ce7e296da2d69da38f97ed8cbec70cac  (SHA-256)
git hash-object scanner_rules.py
# expect: 087dd3a5da82e925b0fa31516763be08c2ceed8d  (Git blob SHA-1, NOT SHA-256)

# 3. Verify source bytes (Item 3)
sha256sum pine_backtest.py pine_stack/pine_stack.py \
  pine_execution/c1_corrected_baseline_20261003.py
# compare against FULL_MANIFEST.json sources section (full 64-hex hashes)

# 4. Run the resampler mechanism fixture (Item 4, NEW 2026-10-07)
cd research_notes/recovery_4h_20261004/cp1_evidence_closure
python3 resampler_grid_fixture.py
# expect: all PASS, incl. SET A 08:30/12:30 EST and SET B 06:30/10:30/14:30 EDT

# 5. Re-run interval-overlap check (Item 5, NEW 2026-10-07)
python3 interval_overlap_checker.py
# expect: 240 trades, defF=88, defI=87, 1 definitional difference (T161), 0 spanned

# 6. Verify archival sources (Item 1, NEW 2026-10-07)
cd archival_sources_v1
sha256sum -c <(grep -v '^#' ARCHIVAL_INDEX.md | awk '/7db282dd|447a9a13|839e4800|4568823c/ {print $0}' | head -0)
# simpler: compare each file's sha256sum against the ARCHIVAL_INDEX.md table manually

# 7. Verify this package manifest
cd research_notes/recovery_4h_20261004/cp1_evidence_closure
sha256sum -c SHA256_MANIFEST.txt
```

## Constraints honored

- Immutable commit `84942a69…` not modified.
- No fresh-data retrieval, no backfill, no holdout access.
- No corrected performance, no #18 performance, no CP2 execution.
- No V5.4 semantic/production changes.
- Original 52 caches in `backtest_cache/v3/` preserved (not touched).
- No historical files silently overwritten (SUPERSESSION.md documents rather
  than replaces).
- 2026-10-07 amendment: no live code changed; all new files are
  documentation, fixtures, or archival copies.
