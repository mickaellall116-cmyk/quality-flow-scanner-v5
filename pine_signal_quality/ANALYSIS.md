# ANALYSIS.md — Final signal-quality study on Pine V3.6 (2026-09-18)

## 1. Exact definitions of the 3 hypotheses

All three were tested as additional AND-filters on top of the **unchanged** V3.6
signal (`pine_backtest.pine_buy_signal`, Hybrid). Exits byte-identical. 4H only,
UX51, 2024-09-16→2026-09-14, $10k / 1% risk / max 5 positions, 4bps + 25bps,
next-bar-open, stop-first, gap-below-stop skip. Control reproduced exactly:
263 trades, +0.195R @4bps. Full pre-registered definitions in
[SIGNAL_QUALITY_SPEC.md](sandbox://workspace/quality-flow-scanner-v5/pine_signal_quality/SIGNAL_QUALITY_SPEC.md)
(frozen before testing; one documented amendment: daily — not 1h — benchmark
bars, because Yahoo restricts intraday data to the last 730 days).

- **H1 — Relative strength.** Signal kept only if the symbol's return over its
  prior 20 4H bars (calendar span [t0, t1]) strictly beats SPY **and** QQQ
  **and** its sector ETF over the same span (sector via frozen yfinance GICS
  map; 39/51 symbols mapped, 12 — 7 crypto + 5 ETFs — use SPY+QQQ only).
  Benchmark returns from daily closes, last-bar-≤-timestamp, no lookahead.
  No lookback optimization (20 bars pre-registered).
- **H2 — Volatility contraction.** Signal kept only if
  ATR14 / SMA(ATR14,50) < 1.0 at the signal bar (the exact `atr_ratio` series
  V3.6 computes). Threshold 1.0 pre-registered, no tuning. Measures the
  compression *state* — V3.6 only measures volatility *level* floors.
- **H3 — Breakout base quality (tight base).** Signal kept only if the range of
  the 10 bars before the breakout bar (the same window the breakout condition
  uses) is < 2.0 × ATR14. Multiplier 2.0 pre-registered, no tuning.

## 2. Research-window comparison table (@4bps; 25bps in JSON)

| Variant | Trades | Win% | Exp R | PF | Ret% | DD% | AvgWin R | AvgLos R | Stop% | TP1% | Hold | ΔTrades |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V0 control | 263 | 44.9 | **+0.195** | 1.27 | +35.30 | 35.17 | +2.02 | −1.29 | 93.9 | 47.5 | 18.1 | — |
| H1_rs | 216 | 47.2 | **+0.294** | 1.43 | +41.54 | 33.15 | +2.08 | −1.30 | 95.8 | 49.5 | 18.6 | −17.9% |
| H2_contraction | 117 | 47.9 | **+0.213** | 1.28 | +20.18 | 30.83 | +2.04 | −1.47 | 94.0 | 48.7 | 19.3 | −55.5% |
| H3_tightbase | 27 | 51.9 | **+1.517** | 3.83 | +46.98 | 9.63 | +3.96 | −1.11 | 88.9 | 55.6 | 24.8 | −89.7% |

## 3. Which features added real value

- **H1 (relative strength): real, material, and genuinely new.** +0.294R vs
  +0.195R (+0.099R), PF 1.27→1.43, drawdown *improved* 35.2%→33.2%, on 216
  trades (−17.9% — a modest selectivity price). No V3.6 component measures
  relative strength, so it is new information, not a duplicate. The only
  hypothesis that cleared all four research-window gates.
- **H2 (contraction): directionally positive, below the bar.** +0.213R missed
  the pre-registered +0.225R materiality gate. Fewer trades (−55.5%) for no
  meaningful expectancy gain. Not adopted — no judgment override.
- **H3 (tight base): small-sample artifact.** +1.517R on 27 trades with a 9.6%
  drawdown is the classic signature of a handful of big winners, not a robust
  filter. Failed the ≥60-trade stability floor by design. Adopting it would be
  exactly the overfitting this study was built to prevent.

## 4. Frozen candidates

One: **C1 = H1_rs** (exact definition in
[CANDIDATES_FROZEN.md](sandbox://workspace/quality-flow-scanner-v5/pine_signal_quality/CANDIDATES_FROZEN.md),
frozen before touching 2022). H2 and H3 were mechanically excluded per the
pre-registered gates.

## 5. 2022 validation results (32 symbols, same framework as all prior studies)

| Variant | Trades | Win% | Exp R | PF | Ret% | DD% | AvgWin R | AvgLos R | Hold |
|---|---|---|---|---|---|---|---|---|---|
| V0 control | 39 | 43.6 | **+0.287** | 1.35 | +11.21 | 20.42 | +2.55 | −1.47 | 20.1 |
| C1_H1_rs | 38 | 42.1 | **+0.138** | 1.16 | +5.09 | 21.94 | +2.34 | −1.47 | 18.7 |

(Control reproduces the entry-ablation 2022 baseline trade-for-trade: 39 /
+0.287R / PF 1.35 / DD 20.42% — pipeline sanity confirmed.)

Adoption bar (all required): (i) research gates ✓ | (ii) 2022 exp > 0 ✓
(+0.138R) | (iii) 2022 exp ≥ control−0.05R = +0.237R ✗ (+0.138R — **fails**) |
(iv) DD within bounds ✓. **C1 is NOT adopted.**

Why it failed — the mechanism, not just the number: in 2022 the RS filter
removed +17.13R of winners (AAPL 2022-07-28 +2.21R; BTC-USD 2023-01-06
+14.36R; SPY 2022-08-03 +0.55R) while knock-on re-entries added only +11.19R
(AAPL 2022-08-10 +0.64R; BTC-USD 2023-01-11 +10.55R) — net −5.94R across
~39 trades, ≈ −0.15R/trade, fully explaining the drop. Relative strength is
**pro-cyclical**: in bull markets it keeps you in leaders (helps); in bear
markets the only breakouts that work are counter-trend bounces in beaten-down
names *without* relative strength — exactly what the filter deletes. This is a
coherent regime story, and it is the reason a bull-window improvement does not
transfer.

## 6. Does any feature deserve a V3.7 signal upgrade?

No. H1 was the strongest genuine signal-quality idea in the entire research
program — new information, material bull-window gain, *better* drawdown —
and it still failed the bear-market robustness bar. H2 never cleared
materiality; H3 was never statistically real.

## 7. Verdict

**V3.6 remains permanently unchanged. V3.6 signal research is exhausted.**
No fourth hypothesis, per the brief. The complete arc of every study run on
this indicator now points the same way: added complexity and added
selectivity both shine in the 2024–2026 bull window and break in 2022.
The simple engine (+0.195R bull / +0.287R bear) is the only specification
that has survived every window it was tested on.

## Files
- `SIGNAL_QUALITY_SPEC.md` — frozen pre-test spec (+ Amendment A)
- `CANDIDATES_FROZEN.md` — freeze record
- `signal_quality_results.json` — research-window results
- `signal_quality_validate.json` — 2022 validation results
- `pine_signal_quality.py` / `pine_signal_quality_validate.py` / `fetch_benchmarks.py`
- `sector_map.json` (frozen GICS mapping), `benchmark_manifest.json`
- `cache/bench_1d_{SPY,QQQ,XLC,XLF,XLI,XLK,XLV,XLY}.pkl` — daily benchmark bars
