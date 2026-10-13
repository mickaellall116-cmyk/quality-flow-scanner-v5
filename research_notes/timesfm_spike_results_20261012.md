# TimesFM spike — RESULTS (run 2026-10-12/13)

Pre-registration: `timesfm_spike_prereg_20261012.md` (gate frozen before the
run; not moved, nothing retuned). Authorized by Mike, main chat,
2026-10-12 22:37 EDT.

## Verdict: FAIL

The frozen PASS gate required all three legs. Two of three failed.

| Gate leg | Requirement | Result | Verdict |
|---|---|---|---|
| 1. Pooled RMSE vs no-change | ≥ 5% lower | TimesFM 8.0036 vs no-change 7.6095 → **5.2% WORSE** | **FAIL** |
| 2. Directional accuracy (pooled) | ≥ 53% | **50.3%** (785/1,562) | **FAIL** |
| 3. Tradable check (pooled) | mean/trade > 0 after 25 bps | **+0.207%** over 670 trades | PASS |

Per the pre-registration, a FAIL closes the idea: no retuning of horizon,
context, threshold, or universe against this data.

## Headline numbers (pooled, 1,577 scored origins)

| Model | RMSE | MAE | Directional acc. |
|---|---|---|---|
| TimesFM 2.0 500M | 8.0036 | 3.9271 | 50.3% |
| No-change | **7.6095** | **3.7096** | — (no direction) |
| 20-day drift | 7.8178 | 3.8565 | 48.7% |

TimesFM lost to "tomorrow = today" on both error metrics. Its directional
accuracy is a coin flip. The dumbest baseline won.

Tradable check detail (descriptive): 670 trades triggered (forecast return
> +0.2%), mean +0.207% per trade after 25 bps round-trip, win rate 46.6%.
The positive mean is carried by a few names (ASTX +2.93% on only 9 trades,
HOOD +0.80%, RKLB +0.80%) while ANET (−0.37%), NIO (−0.97%), and PLTR
(−0.20%) legs lost money. Leg 3 passing does not rescue the gate — the gate
was all three, set in advance.

## Per-ticker table

| Ticker | n | TimesFM RMSE | No-change RMSE | Drift RMSE | TimesFM MAE | No-change MAE | RMSE impr. | Dir. acc. |
|---|---|---|---|---|---|---|---|---|
| QQQ | 133 | 10.007 | 9.428 | 9.621 | 7.839 | 7.195 | −6.1% | 44.4% |
| SMCI | 133 | 2.180 | 2.116 | 2.185 | 1.543 | 1.477 | −3.0% | 48.5% |
| PLTR | 133 | 6.137 | 5.828 | 6.007 | 4.176 | 3.854 | −5.3% | 43.6% |
| ANET | 133 | 6.411 | 5.938 | 6.209 | 5.116 | 4.589 | −8.0% | 41.4% |
| SOFI | 133 | 0.591 | 0.585 | 0.610 | 0.447 | 0.440 | −1.1% | 55.6% |
| RKLB | 133 | 5.545 | 5.458 | 5.722 | 3.970 | 3.833 | −1.6% | 53.4% |
| ONDS | 133 | 0.530 | 0.535 | 0.562 | 0.375 | 0.357 | **+1.0%** | 53.5% |
| SPCX | 54 | 6.771 | 5.976 | 6.242 | 4.995 | 4.491 | −13.3% | 50.0% |
| ASTX | 60 | 1.281 | 1.110 | 1.187 | 1.025 | 0.885 | −15.4% | 59.3% |
| BBAI | 133 | 0.168 | 0.147 | 0.151 | 0.120 | 0.108 | −14.2% | 56.2% |
| NIO | 133 | 0.162 | 0.154 | 0.157 | 0.120 | 0.112 | −5.3% | 48.8% |
| HOOD | 133 | 4.382 | 4.275 | 4.464 | 3.369 | 3.234 | −2.5% | 51.9% |
| AMD | 133 | 22.492 | 21.452 | 21.974 | 16.999 | 16.564 | −4.9% | 51.9% |
| DRAM | 0 | — | — | — | — | — | — | — |

TimesFM beat no-change on RMSE on **1 of 13** scored tickers (ONDS, +1.0%).

## Design as run

- Universe: 14 watchlist tickers, daily closes from Yahoo via yfinance
  (unadjusted Close). **No Tiingo data** (compliance hold respected).
- Task: 1-trading-day-ahead close; context = prior 256 closes; origins =
  every trading day 2026-04-01 → 2026-10-09 with a next trading day to
  score against. 1,577 origins scored.
- Model: TimesFM 2.0 500M, checkpoint `google/timesfm-2.0-500m-pytorch`,
  CPU inference, point forecast = median output (hparams default).
- Scoring conventions: 15 origins where the actual close exactly equaled
  the prior close were excluded from the directional-accuracy denominator
  (1,577 → 1,562); a forecast of exactly no-change counted as a miss there.
  Tradable check pooled across all tickers/origins as registered.

## Deviations from the pre-registration (all disclosed, gate unchanged)

1. **Loader source.** The pip `timesfm` packages installable in this
  environment (2.0.2, 3.0.2) no longer ship a loader for the TimesFM 2.0
  checkpoint, and the PyTorch CPU wheel index is unreachable from this
  machine. The run therefore used the official `google-research/timesfm`
  repository source at tag **v1.2.6** (commit
  `e77303c5513c84aa8b32639851c3f7f92f59645e`, `src/timesfm` `TimesFmTorch`) —
  the loader that serves this checkpoint — with the exact frozen
  checkpoint file: `torch_model.ckpt`, 1,995,545,448 bytes, SHA-256
  `a3a1362cdc26f0dde45c9790c438951ff02af96b2d1d6445fdb58f28c77e18de`,
  HF repo revision `dc2443792ce5516872b89b37cf1bc058c3bf0c10`.
  Model, checkpoint, task, and gate are exactly as registered.
2. **SPCX short context** (anticipated in the tasking): SPCX (IPO
  2026-06-12) can never have 256 prior closes inside the window. It was
  included with the context it had (30–83 closes; first origin
  2026-07-27; 54 origins), and every SPCX record is flagged
  `context_short` in the raw results.
3. **DRAM excluded — stated, not silent.** Yahoo carries only 133 DRAM
  bars (from 2026-04-02); it never reaches 256 prior closes in the
  window, so under the frozen 256-context design it contributes 0
  origins. The scored universe is 13 of the 14 registered tickers.
4. **ASTX partial window.** ASTX history starts 2025-07-11; its first
  origin with a full 256-close context is 2026-07-17 (60 origins).
  Direct consequence of the frozen context rule.
5. **No origin subsampling.** The pre-authorized fallback (every 2nd
  trading day if CPU inference was too slow) was not needed.

## Contamination caveat (from the pre-registration, stands)

The scoring window was chosen after TimesFM 2.x's public release to reduce
— not eliminate — pretraining contamination; the exact training cutoff is
not public. Here the verdict is FAIL, so contamination cannot be propping
up a pass; if anything, any residual contamination would have flattered
the model, which makes the negative result stronger, not weaker.

## Environment and runtimes

- Python 3.12.3; torch 2.14.1 (CPU execution; CUDA libraries present but
  unused); numpy 2.5.4; pandas 3.0.6; yfinance 1.7.0; einshape 1.0;
  utilsforecast 0.2.17; scikit-learn 1.9.1; jax 0.11.2 (import-only
  dependency of the loader's covariate module; not used for inference).
- Machine: 2 CPUs, 7 GB RAM.
- Compute runtime: model load ~14 s; batched forecasting 279 s; total run
  311 s (~5 min). (Environment setup — multi-GB package and checkpoint
  downloads over a slow proxy — took considerably longer and is not part
  of the run.)
- Artifacts: run script `~/workspace/timesfm_spike/run_timesfm_spike.py`;
  raw per-origin results `~/workspace/timesfm_spike/timesfm_spike_raw_results.json`
  (1,577 records with all three forecasts per origin); bars cache and run
  log alongside them.

## Bottom line

Zero-shot TimesFM does not forecast our tickers' next-day closes better
than assuming tomorrow equals today — on error, on direction, and on 12 of
13 names individually. The one gate leg that passed (tradable mean) rests
on a minority of names and was never sufficient alone. FAIL is the
recorded verdict; the idea is closed per the pre-registration.

— Muse, 2026-10-13
