# Source Byte Recovery — Results

**Date:** 2026-10-06
**Manifest:** `research_notes/recovery_4h_20261004/cp1_followup/FULL_MANIFEST.json`, `sources` section

## Result: all source bytes recovered (present locally, hashes match)

No git-history archaeology was required. All three files exist in the local
working tree on branch `recovery-4h-20261004` with byte content matching the
manifest's expected SHA-256 exactly (verified 2026-10-06 via `sha256sum`):

| File | Expected SHA-256 (manifest) | Local SHA-256 | Verdict |
|------|----------------------------|---------------|---------|
| `pine_backtest.py` | `447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d1` | identical | ✅ RECOVERED |
| `pine_stack/pine_stack.py` | `839e4800624de253514095b5c007e8088afc0ab6c6ef45c86fb2` | identical | ✅ RECOVERED |
| `pine_execution/c1_corrected_baseline_20261003.py` | `4568823cb8fe645a820c64bb4fac112f` (prefix; full in manifest) | identical | ✅ RECOVERED |

## Boundary

- "Recovered" here means the exact bytes pinned by the manifest are present
  and verified in the working tree. No substitution or fabrication was
  performed.
- These files were not re-examined for correctness in this closure; only
  byte identity against the manifest was verified.
- No claims are marked UNVERIFIABLE on source-byte grounds. (Claims that
  depend on the *omitted resampler/XNYS review* are addressed separately
  in RESAMPLER_XNYS_EVIDENCE.md.)
