# TimesFM spike — evidence package manifest

Packaged 2026-10-13 per ChatGPT adjudication (Issue #1 comment 6138432952).
Packaging only: byte-identical copies of the original run artifacts; nothing
rerun, refetched, regenerated, or retuned. Verdict: **CLOSED — FAIL**;
independent reproduction PENDING (this package is what makes it possible).

## Files (copied verbatim from ~/workspace/timesfm_spike/)

| file | bytes | sha256 |
|---|---|---|
| run_timesfm_spike.py | 11,240 | d16e660b01a782237d149d89687c2cbcf415f5c354f9a752279c66a23d120030 |
| timesfm_spike_raw_results.json | 518,236 | aaff3be687212feb557c6b29ed98b5253410ab98a8e8e1e656061d19c71483ed |
| bars_cache.json (Yahoo bars as fetched) | 245,108 | ec5d89c53c5703693dbea905de0559a6af01aab004f03b196bcea0476cd33e35 |
| run_log.txt | 1,678 | 09b0278408472f69f74beb2f6a7890047d72e4e8fcb0a11c0425d31db027b69d |

## Run facts

- Command: the run script executed from ~/workspace/timesfm_spike/ (see
  run_timesfm_spike.py; run_log.txt is its captured output).
- Timing: model load ~14 s; batched forecasting 279 s; total run 311 s.
  (Setup — multi-GB torch/checkpoint downloads through the proxy — took far
  longer and is not part of the scored run.)
- Checkpoint: google/timesfm-2.0-500m-pytorch, HF revision
  dc2443792ce5516872b89b37cf1bc058c3bf0c10; torch_model.ckpt 1,995,545,448
  bytes (not packaged — 2 GB; sha-256 recorded in the results document).
- Loader: official google-research/timesfm repo tag v1.2.6, commit
  e77303c5513c84aa8b32639851c3f7f92f59645e, TimesFmTorch (pip timesfm no
  longer ships a 2.0 loader — deviation disclosed in the results document).
- Environment: Python 3.12.3, torch 2.14.1 CPU, 2-CPU VM.
- Scope: 1,577 origins, 13 of 14 tickers (DRAM excluded — 133 bars, never
  reaches the frozen 256-close context; SPCX short-context flagged).

Full scored results: research_notes/timesfm_spike_results_20261012.md.
Preregistration: research_notes/timesfm_spike_prereg_20261012.md (4708118).
