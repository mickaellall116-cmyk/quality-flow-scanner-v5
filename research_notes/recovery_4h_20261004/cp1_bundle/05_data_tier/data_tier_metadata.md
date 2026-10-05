# CP1 Bundle — Data Tier Metadata (raw facts)

## Cache files under audit
- Directory: `backtest_cache/v3/h4_*.pkl`
- File count: 52
- Total bars: 75,311
- Earliest bar timestamp observed: 2024-09-15 12:00:00+00:00
- Latest bar timestamp observed: 2026-09-15 08:00:00+00:00
- Index timezone values observed across files: `America/New_York`, `UTC` (mixed; per-file value in `01_cache_grid/bar_timestamps_raw.json`)
- Per-file SHA-256: `01_cache_grid/h4_cache_hashes.json`

## Intended walk-forward data spec (from preregistration rev 2, §2)
- Source: Yahoo Finance 1H, `auto_adjust=False`, `prepost=False`
- Target start: 2023-01-01 (or earliest available per symbol)
- Corporate actions: frozen split-exclusion protocol
- Universe: 51 symbols (`pine_backtest.UNIVERSE_X`); definition SHA-256 in manifest
- Coverage rule: symbol with <80% of target history marked COVERAGE-LIMITED

## Evidence tier classification (from preregistration rev 2, §2)
- Classification: LIMITED (not PIT-clean)
- Stated reasons:
  1. Split handling: frozen split protocol mitigates retroactive split adjustment; cannot recover as-traded prices.
  2. Survivorship: universe is the current tradable list; symbols that died before the history window are absent.
  3. Revisions: bars older than ~30 days stable in practice; historical rewrites between download dates undetectable.
- Stated: no qualified PIT-clean 1H source available at zero cost.

## Raw 1H inputs
- Per the rev 2 manifest: raw 1H inputs were transient Yahoo downloads, not preserved.
- This is documented in `03_manifests/complete_manifest_rev2.json` under `raw_1h_inputs`.
