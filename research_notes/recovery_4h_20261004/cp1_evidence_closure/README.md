# CP1 Evidence Closure

**Date:** 2026-10-06
**Assignment:** ChatGPT bounded evidence closure (Issue #1 comment 6028234879)
**Immutable evidence pin:** `84942a6929258a0c316a6e849a7480c286013d95` (not modified)
**Status:** Evidence closure only. No performance computed. No production changes.

## Contents

| File | Purpose |
|------|---------|
| `SUPERSESSION.md` | Stale `trade_intersection.json` supersession: three forms documented (rev1 standalone, rev2 standalone, canonical shards), field-level diffs, explicit SUPERSEDED statement |
| `SCANNER_RULES_IDENTITY.md` | `scanner_rules.py` hash investigation: branch divergence explained (forensic-line Version A `7db282dd…` vs hardening-line Version B `62aa743a…`); manifest is internally consistent |
| `SOURCE_BYTE_RECOVERY.md` | Byte recovery results: all three source files match manifest hashes locally; no recovery needed |
| `RESAMPLER_XNYS_EVIDENCE.md` | Resampler/XNYS evidence: timezone origin, 08:30/12:30 vs 06:30/10:30/14:30 label distinction, early-close behavior, completed-bar causality, cache preservation, omitted-review boundary |
| `INTERVAL_OVERLAP_CHECK.md` | Interval-overlap check: 0/240 trades span EST periods with endpoints outside; no code change proposed |
| `CP2_PREFLIGHT_PROPOSAL.md` | CP2 preflight proposal: input identities, lineage limits, 7 fixed tests with gates, exclusions, authorization checklist — proposal only, no execution |
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
git show 462b8dc:research_notes/recovery_4h_20261004/cp1_followup/trade_intersection.json \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['n_with_gap_refs'])"
# expect: 3 (rev1)

# 2. Verify scanner_rules.py identity (Item 2)
sha256sum scanner_rules.py
# expect: 7db282ddfc150c9e9aec7d8f1f10f439ce7e296da2d69da38f97ed8cbec70cac
git show 0faaa6c:scanner_rules.py | sha256sum
# expect: 62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c

# 3. Verify source bytes (Item 3)
sha256sum pine_backtest.py pine_stack/pine_stack.py \
  pine_execution/c1_corrected_baseline_20261003.py
# compare against FULL_MANIFEST.json sources section

# 4. Verify resampler citations (Item 4)
sed -n '87,108p' scanner_rules.py          # resample_closed_4h docstring + defect note
sed -n '75,95p' research_notes/recovery_4h_20261004/fixtures/byte_identity_report.md
sed -n '1,20p' research_notes/recovery_4h_20261004/spec/call_site_map.md

# 5. Re-run interval-overlap check (Item 5)
cd research_notes/recovery_4h_20261004/cp1_followup
python3 -c "
import json
parts = [open(f'trade_intersection.json.shard{i:02d}').read() for i in range(4)]
d = json.loads(''.join(parts))
print('trades:', len(d['trades']))
print('n_with_gap_refs:', d['n_with_gap_refs'])
"

# 6. Verify this package manifest
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
