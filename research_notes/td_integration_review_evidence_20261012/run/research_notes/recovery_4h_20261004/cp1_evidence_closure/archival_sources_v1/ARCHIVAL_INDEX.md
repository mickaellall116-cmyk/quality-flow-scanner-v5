# Archival Sources v1 — Index

**Date:** 2026-10-06/07
**Purpose:** Remote-readable archival copies of the exact source bytes pinned by
`cp1_followup/FULL_MANIFEST.json` (`sources` section). These files previously
returned GitHub 404 (local-only); this directory supplies the remote evidence.
**No code was changed.** These are byte-identical copies of working-tree files
on branch `recovery-4h-20261004`.

**Hash-algorithm note (read carefully):**
- `SHA-256` values below are computed with `sha256sum` and match the manifest's
  expected hashes exactly.
- `Git blob SHA-1` values are computed with `git hash-object` (which returns a
  **SHA-1** hash of the blob object, not SHA-256). They are provided so the
  remote GitHub blob can be cross-checked after publication.

| # | Original repo path | Archival path | Bytes | SHA-256 | Git blob SHA-1 |
|---|-------------------|---------------|-------|---------|----------------|
| 1 | `scanner_rules.py` (Version A, forensic line) | `archival_sources_v1/scanner_rules.py` | 22,892 | `7db282ddfc150c9e9aec7d8f1f10f439ce7e296da2d69da38f97ed8cbec70cac` | `087dd3a5da82e925b0fa31516763be08c2ceed8d` |
| 2 | `pine_backtest.py` | `archival_sources_v1/pine_backtest.py` | 16,996 | `447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5` | `9f195dbf33aed9a2c14d0e23719126143431d946` |
| 3 | `pine_stack/pine_stack.py` | `archival_sources_v1/pine_stack/pine_stack.py` | 19,161 | `839e4800624de253514095b5c007e8088afc0ab6c6ef45c86fb29a5956dfcefa` | `db8da1d772b37805071b33738db4490e13f2af41` |
| 4 | `pine_execution/c1_corrected_baseline_20261003.py` | `archival_sources_v1/pine_execution/c1_corrected_baseline_20261003.py` | 16,548 | `4568823cb8fe645a820c64bb4fac112fa7c90ac860bf626611467f7d94ea8f2b` | `7faf7a7b709cf1524e417e301acabdace00f767e` |

## Version notes

- **File 1 (`scanner_rules.py`)** is **Version A (forensic line)** — the exact
  bytes the CP1 forensic analysis was performed against (branch
  `recovery-4h-20261004`, commit `b3a7251` "Candle fixes"). It is NOT the
  hardening-line Version B (`62aa743a…`, remote `main`), which was never part
  of CP1 evidence collection. See `SCANNER_RULES_IDENTITY.md`.
- **Files 2–4** are the engine/constructor sources whose manifest hashes were
  verified byte-identical in the working tree on 2026-10-06. See the corrected
  `SOURCE_BYTE_RECOVERY.md`.

## Verification

- Local: `sha256sum <file>` matches the manifest's expected SHA-256 for all
  four files (verified 2026-10-06 and again 2026-10-07).
- After publication: compare each remote GitHub blob's SHA-1 against the
  `Git blob SHA-1` column above. (GitHub blob pages and the
  `get_file_contents` API return the blob SHA-1.)
- Immutable paths: once published, these archival copies must not be edited.
  Any future correction requires a new versioned subdirectory
  (`archival_sources_v2/`), never an in-place overwrite.
