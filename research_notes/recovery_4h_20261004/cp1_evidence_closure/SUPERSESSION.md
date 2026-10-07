# SUPERSESSION NOTICE — trade_intersection.json

**Date:** 2026-10-06 (corrected 2026-10-07 per ChatGPT review 6029985481)
**Scope:** CP1 follow-up evidence package, `research_notes/recovery_4h_20261004/cp1_followup/`
**Status:** SUPERSEDED — retained for historical reference only. Do not cite as evidence.

## Correction to prior version of this notice

A prior version of this document incorrectly stated that the stale standalone
`trade_intersection.json` was "never published to GitHub" and that rev1 exists
"only in git history." **That is wrong.** The stale standalone **was published
to GitHub** and remains remotely pinned at the immutable CP1 commit. This
section corrects the record with exact pinned identities. Original bytes are
not erased; they are named explicitly below as superseded.

## The three forms

| Form | SHA-256 | n_with_gap_refs | T192 gap_refs | Location |
|------|---------|-----------------|---------------|----------|
| **rev1 standalone — REMOTELY PINNED (SUPERSEDED)** | `22a61c81800d3f01d98490a0a9da5fba020ac8757dbbb3c1d815349b1ebf2d99` | 3 | `['SOL-GAP3(2026-05-11_2026-05-12)']` | GitHub, immutable commit `84942a6929258a0c316a6e849a7480c286013d95`, path `research_notes/recovery_4h_20261004/cp1_followup/trade_intersection.json`, Git blob SHA-1 `5e525f9bd3d7f898e93224f1259a56b5ffd79c54` |
| rev2 standalone (recovered local) | `a457e7a10845650eeb2b4be6c7a2b0ca02c91dff2667f5a4687b4e8b6b460684` | 2 | `[]` (withdrawn) | Local working tree `cp1_followup/trade_intersection.json`, Git blob SHA-1 `110b05a65775ec298679576484680d50d5a4aa36`, `revision: "rev2-corrected"` |
| **Canonical** shard reconstruction | `02608fd49331e5d795ac678440c7d9792f74d577eeb454d7bd68686b234fd872` | 2 | `[]` (withdrawn) | GitHub: 4 shards + INDEX under `cp1_followup/` |

## Remotely pinned rev1 — exact identity

The stale standalone is pinned at the immutable CP1 commit and is publicly
readable without authentication:

- **Commit:** `84942a6929258a0c316a6e849a7480c286013d95` (immutable; ancestor of
  `origin/main`, preserved in history)
- **Path in tree:** `research_notes/recovery_4h_20261004/cp1_followup/trade_intersection.json`
- **Git blob SHA-1:** `5e525f9bd3d7f898e93224f1259a56b5ffd79c54`
- **SHA-256 of pinned bytes:** `22a61c81800d3f01d98490a0a9da5fba020ac8757dbbb3c1d815349b1ebf2d99`
- **Distinguishing content:** `n_with_gap_refs: 3`, `revision` field ABSENT,
  T192 `gap_refs: ['SOL-GAP3(2026-05-11_2026-05-12)']`, 240 trades
- **Raw URL (pinned):**
  `https://raw.githubusercontent.com/mickaellall116-cmyk/quality-flow-scanner-v5/84942a6929258a0c316a6e849a7480c286013d95/research_notes/recovery_4h_20261004/cp1_followup/trade_intersection.json`

This pinned file is **SUPERSEDED**. It is not deleted or rewritten; it remains
in the immutable commit's history as evidence of what was originally published.

## rev2 (recovered local) vs remotely pinned rev1

The local rev2 file (`a457e7a1…`, blob `110b05a6…`) was recovered during the
REV2 correction pass (local commit `b18a010`, "CP1 follow-up REV2"). It is
**not** the file pinned at `84942a6`. The two must not be confused:

- **Remotely pinned rev1** (`22a61c81…` / blob `5e525f9b…`): T192 gap_refs
  present, `n_with_gap_refs=3`. This is what a reader fetching the immutable
  commit sees.
- **Recovered local rev2** (`a457e7a1…` / blob `110b05a6…`): T192 gap_refs
  withdrawn (`[]`), `n_with_gap_refs=2`, `revision: "rev2-corrected"`. This is
  the corrected working-tree file.

Both are retained. Neither is silently overwritten.

## Field-level differences (rev1 → rev2)

The rev1 → rev2 correction changed:

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
- It is the form published on GitHub at the current `origin/main`
  (4 shard files + INDEX, all remote-verified, 17/17 blobs byte-identical).
- `FULL_MANIFEST.json` advertises the shard-reconstructed SHA-256 (`02608fd4…`).

## Explicit statement

**The remotely pinned standalone `trade_intersection.json` at immutable commit
`84942a6` (SHA-256 `22a61c81…`, blob `5e525f9b…`) is SUPERSEDED.**
It remains in the immutable commit's history as published evidence and is not
erased. All citations must use the canonical shard-reconstructed form
(SHA-256 `02608fd4…`, reassembled per `trade_intersection.json.INDEX`).
Any analysis citing `n_with_gap_refs=3` or T192 SOL gap references is citing
rev1 content and is stale.
