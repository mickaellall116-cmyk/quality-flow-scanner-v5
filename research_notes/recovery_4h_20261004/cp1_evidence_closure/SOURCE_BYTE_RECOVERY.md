# Source Byte Recovery — Results (CORRECTED 2026-10-07)

**Date:** 2026-10-06 (corrected 2026-10-07 per ChatGPT amendment 6028744990)
**Manifest:** `research_notes/recovery_4h_20261004/cp1_followup/FULL_MANIFEST.json`, `sources` section

## Result: all source bytes recovered (present locally, hashes match)

No git-history archaeology was required. All three files exist in the local
working tree on branch `recovery-4h-20261004` with byte content matching the
manifest's expected SHA-256 exactly (verified 2026-10-06 and 2026-10-07 via
`sha256sum`).

| File | Expected SHA-256 (manifest, full) | Local SHA-256 | Verdict |
|------|-----------------------------------|---------------|---------|
| `pine_backtest.py` | `447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5` | identical | ✅ RECOVERED |
| `pine_stack/pine_stack.py` | `839e4800624de253514095b5c007e8088afc0ab6c6ef45c86fb29a5956dfcefa` | identical | ✅ RECOVERED |
| `pine_execution/c1_corrected_baseline_20261003.py` | `4568823cb8fe645a820c64bb4fac112fa7c90ac860bf626611467f7d94ea8f2b` | identical | ✅ RECOVERED |

Byte lengths: `pine_backtest.py` 16,996; `pine_stack/pine_stack.py` 19,161;
`pine_execution/c1_corrected_baseline_20261003.py` 16,548.

## Correction (2026-10-07)

The 2026-10-06 version of this document printed **truncated** hashes for
`pine_stack/pine_stack.py` and `c1_corrected_baseline_20261003.py`. The full
64-hex-character SHA-256 values are given in the table above, copied verbatim
from `FULL_MANIFEST.json`.

**Hash-algorithm precision:** `git hash-object` returns a **SHA-1** hash of the
Git blob object — it does not return SHA-256. Any earlier wording implying
that a `git hash-object` value equals a manifest SHA-256 was incorrect. The
two hash families are independent:
- Manifest pinning uses **SHA-256** (`sha256sum`).
- Git blob identity uses **SHA-1** (`git hash-object`).

The corresponding ambiguous line in `SCANNER_RULES_IDENTITY.md` ("`git
hash-object` HEAD version = `7db282dd…`") is corrected there: the working-tree
`sha256sum` equals the manifest SHA-256 `7db282dd…`, while `git hash-object`
of the same file returns the blob SHA-1 `087dd3a5da82e925b0fa31516763be08c2ceed8d`.

## Boundary

- "Recovered" here means the exact bytes pinned by the manifest are present
  and verified in the working tree. No substitution or fabrication was
  performed.
- Remote-readable copies are published in `archival_sources_v1/` with
  `ARCHIVAL_INDEX.md` (full SHA-256, Git blob SHA-1, byte lengths).
- These files were not re-examined for correctness in this closure; only
  byte identity against the manifest was verified.
- No claims are marked UNVERIFIABLE on source-byte grounds. (Claims that
  depend on the *omitted resampler/XNYS review* are addressed separately
  in RESAMPLER_XNYS_EVIDENCE.md and RESAMPLER_MECHANISM_FIXTURE.md.)
