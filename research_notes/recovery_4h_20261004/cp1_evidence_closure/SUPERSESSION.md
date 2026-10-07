# SUPERSESSION NOTICE — trade_intersection.json

**Date:** 2026-10-06
**Scope:** CP1 follow-up evidence package, `research_notes/recovery_4h_20261004/cp1_followup/`
**Status:** SUPERSEDED — retained for historical reference only. Do not cite as evidence.

## The three forms

| Form | SHA-256 | n_with_gap_refs | T192 gap_refs | Location |
|------|---------|-----------------|---------------|----------|
| rev1 standalone (commit `462b8dc`) | `22a61c81800d3f01…` | 3 | `['SOL-GAP3(2026-05-11_2026-05-12)']` | git history only |
| rev2 standalone (current local file) | `a457e7a10845650eeb2b4be6c7a2b0ca02c91dff2667f5a4687b4e8b6b460684` | 2 | `[]` (withdrawn) | `cp1_followup/trade_intersection.json` |
| **Canonical** shard reconstruction | `02608fd49331e5d795ac678440c7d9792f74d577eeb454d7bd68686b234fd872` | 2 | `[]` (withdrawn) | GitHub: 4 shards + INDEX |

## Field-level differences (rev1 → rev2)

The rev1 → rev2 correction (commit `b18a010`, "CP1 follow-up REV2") changed:

1. **`n_with_gap_refs`**: 3 → 2. The T192 SOL exact-gap intersection was withdrawn after
   re-examination showed zero SOL trades intersect the exact 44 absent-slot gaps.
2. **T192 `gap_refs`**: `['SOL-GAP3(2026-05-11_2026-05-12)']` → `[]`. The SOL-GAP3 reference
   was a calendar-period coincidence, not an exact-gap intersection.
3. **`revision` field**: absent → `"rev2-corrected"`.
4. **`correction_note` field**: added, documenting the superseded 82-count split
   (51 equity shifted-regime + 31 crypto calendar entries).

## rev2 standalone vs canonical shard form

The rev2 standalone file (`a457e7a1…`) and the shard-reconstructed form (`02608fd4…`)
are **content-identical**: same keys, same 240 trades, same values, verified by
JSON parse comparison on 2026-10-06. They differ only in serialization whitespace
(pretty-printed with indentation vs minified).

The shard form is **canonical** because:
- It is the form actually published on GitHub (4 shard files + INDEX, all remote-verified).
- `FULL_MANIFEST.json` advertises the shard-reconstructed SHA-256 (`02608fd4…`).
- The standalone file was never published to GitHub; only the shards were.

## Explicit statement

**The standalone `trade_intersection.json` (SHA-256 `a457e7a1…`) is SUPERSEDED.**
It is retained in the local working tree for historical reference and was not
silently overwritten. All citations must use the canonical shard-reconstructed
form (SHA-256 `02608fd4…`, reassembled per `trade_intersection.json.INDEX`).
Any analysis citing `n_with_gap_refs=3` or T192 SOL gap references is citing
rev1 content and is stale.
