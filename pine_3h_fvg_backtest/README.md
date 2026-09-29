# 3H + FVG-as-entry backtest — the two winners combined

**Date:** 2026-09-24. **Status:** research, local-only. Modifies nothing frozen.

## Question
Mike asked to combine the two prior winners: 3H Hybrid (only timeframe to
clear the +0.15R gate) × FVG-as-entry (only entry toggle to add edge on 4H).

## Method
- 3H bars: `pine_2h3h_backtest/cache/h1_{SYM}.pkl` resampled WITHIN each
  trading day, bins anchored at 09:30 ET (09:30/12:30/15:30 + 15:30–16:00 stub)
  — identical convention to `run_2h3h_watchlist.py`.
- FVG port: `add_entry_timing_columns` / `sub_signals` / `make_combo_signal`
  imported unmodified from `pine_entry_timing_backtest/run_entry_timing.py`
  (1:1 port of the V3.7 Pine `fvgBuy` semantics: `trendBull and
  inBullFvgSupport and close > ema21 and volumeOK and safeToEnter`, OR'd into
  the Hybrid buySignal). Pullback and sweep toggles OFF.
- `pine_backtest.py` imported UNMODIFIED; only `pb.pine_buy_signal`
  monkey-patched per combo. Indicator lookbacks kept in BARS (unmodified
  transfer, no tuning).
- Universe: 14-stock watchlist. Portfolio: 4bps + 25bps costs, $10k,
  1%/trade, max 5 concurrent, 5% portfolio risk, next-bar-open entries,
  stop-first ties, gap-below-stop skips, Mode B exit stack.
- Combos: BASE (all-off, rerun in THIS study) and FVG-only.

## Fidelity check
In-study 3H BASE reproduced the prior study bar-for-bar: 371 trades,
+0.221R @4bps / +0.158R @25bps, win 50.7% @25bps. The comparison is valid.

## Headline — the FVG edge does NOT transfer to 3H

| Combo (3H) | Trades (+by FVG) | Win% @25 | Exp 4bps | Exp 25bps | PF @25 | MaxDD @25 |
|---|---|---|---|---|---|---|
| BASE (all-off) | 371 (+0) | 50.7 | +0.221 | **+0.158** | 1.24 | 39.3% |
| FVG-only | 434 (+116) | 47.9 | +0.172 | **+0.107** | 1.16 | 41.2% |

- FVG added 116 trades and *destroyed* ~1/3 of the edge: expectancy
  +0.158 → +0.107R at 25bps, win rate −2.8pp, PF 1.24 → 1.16.
- FVG-only MISSES the +0.15R deployment gate. The BASE 3H run still clears
  it (+0.158R) — unchanged from the prior study.
- Signal attribution: 1427 FVG sub-signal bars on 3H, 317 marginal (not also
  canonical) → 116 realized trades. On 4H the same marginal signals added
  edge; on 3H they dilute it.

## Per-ticker 25bps (BASE → FVG): dilution concentrated in the best names
- PLTR 0.601 → 0.294R; HOOD 0.604 → 0.457R; BBAI 0.429 → 0.275R;
  ONDS 0.214 → 0.116R; QQQ −0.264 → −0.354R; SMCI −0.201 → −0.237R.
- Small improvements: RKLB 0.452 → 0.524R; NIO −0.148 → 0.049R;
  AMD 0.500 → 0.515R. Not enough to matter.
- Thin names: DRAM 3–4 trades, ASTX 9–10, SPCX 0 (excluded, <200 bars).
  Per-ticker n is small — direction of the pooled result is what counts.

## Interpretation
On 4H, canonical signals are loose enough (50.4% win) that FVG extras add
quality setups. On 3H the canonical signal is already more selective
(50.7% win, +0.158R) — the extra FVG triggers are lower-quality fills that
regress the blend toward mediocrity. Edge components are NOT portable
across timeframes; each combo must be tested where it will run.

## Verdict
- The combo FAILS: 3H+FVG does not beat the +0.15R gate (+0.107R) and does
  not beat plain 3H Hybrid (+0.158R).
- FVG-as-entry stays a 4H-side paper-sidecar candidate only; it is NOT a
  3H candidate. No live change implied anywhere.

## Caveats
- Single backtest, in-sample, 14-ticker watchlist universe, thin per-ticker
  counts (12–51 trades).
- Unmodified-transfer lookbacks (4H bar terms on 3H bars) — no tuning done,
  same as the prior 3H study.
- ASTX is a 2x daily-reset leveraged ETF backtested as a stock.

## Files
- `run_3h_fvg.py` — driver (resample + combos + attribution)
- `pine_3h_fvg_results.json` — pooled + per-ticker stats, FVG marginal counts
