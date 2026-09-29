# Confirmatory Study 2: FVG-as-entry — WHERE does the edge come from? (2026-09-24)

**Main question:** is FVG improving trade quality, or merely changing the sample?

**Answer up front: it is changing the sample — and the headline edge traces to
ONE trade. Without the single RKLB trade on 2024-09-09 (+12.98R), FVG pooled
expectancy is +0.237R — identical to baseline +0.239R. Verdict: MAYBE.**

## Method

Same canonical setup as the robustness study (14-stock watchlist, 4H,
Oct 2023–Sep 2026, frozen Mode B, 25bps, matched on (symbol, signal_time)).
`pine_backtest` imported unmodified; FVG definition fixed (no threshold search).
Reproduction verified exactly: 237 BASE / 266 FVG trades, 203 shared,
34 BASE-only, 63 FVG-only, shared ΔR = 0.0000.

## 1. Shared setups — entry-price/timing re-verified: 0.0000R

203/203 byte-identical fills; mean entry diff $0.00, mean stop-distance diff
0.00pp, 0 nonzero deltas. FVG is NOT a better entry mechanism. Definitive.

## 2. Avoided losers (BASE-only, n=34): +0.150R — below-average, not losers

FVG dodged mediocrity, not disasters. Median −0.48R, win 44.1%. Also
concentrated: top-5 = 406% of the bucket's +5.11R total (29 other trades net
−15.7R). Dropping them was worth +0.0127R of the headline.

## 3. Added winners (FVG-only, n=63): +0.387R — driven by 5 monsters

Top-5 trades = 147% of the bucket's +24.39R total; the other 58 trades net
**−11.5R**. Median FVG-only trade is −0.37R; win rate 46.0%. The TYPICAL added
trade LOSES. Top trades: RKLB 2024-09-09 +12.98R, SOFI 2025-05-27 +7.92R,
AMD 2025-10-03 +7.51R, BBAI 2025-01-30 +3.82R, ANET 2025-06-24 +3.62R.

## 4. Stop geometry — FVG entries run tighter stops

Mean stop: FVG-only 1.48× ATR vs shared 1.82× ATR vs BASE-only 1.64× ATR.
FVG entries sit closer to support (same $ risk per trade under 1% sizing, but
tighter stops flatter R-multiples for the same price move — and cost more
stop-outs: 46% win vs 50.4% overall). Part of the +0.387 vs +0.254 gap is
stop-geometry, not setup quality.

## 5. Concentration — themes and symbols

FVG-only gains: Space +16.85 (n=5, RKLB), Fintech +7.34, Semis/AMD +6.62,
China EV +3.00. Losses: Software/AI −4.74 (n=17), Index −1.98, Drones −1.82.
Not broad — 4 themes up, 4 down. RKLB alone (one trade) is 60% of the bucket.

## 6. Regime dependence — the one trade

2024 bear/sideways FVG bucket: n=1 — the RKLB trade, +12.98R. The other 3
2024 bear trades were SHARED (both variants held them, +5.11R combined). So
"4 outsized 2024 bear trades" = 3 shared + 1 FVG-only monster. Removing just
the one FVG-only trade: FVG pooled = +0.237R vs BASE +0.239R. **The entire
headline edge is one trade.**

## 7. Walk-forward on the buckets (train ≤2024 / test ≥2025)

| Bucket | Train mean | Test mean |
|---|---|---|
| FVG-only | +0.768 (n=17) | +0.246 (n=46) |
| BASE-only (omitted) | +0.223 (n=12) | +0.111 (n=22) |
| Shared | +0.371 (n=63) | +0.201 (n=140) |

Selection directionally persists in test (FVG-only > omitted), but it is
year-flippy: 2025 bull FVG-only +0.938 (n=23) vs **2026 bull FVG-only −0.577
(n=20)** — worse than shared (−0.230) in 2026. The OOS edge is a 2025
phenomenon so far.

## Verdict: MAYBE

- NOT PASS: pooled edge = one trade; median added trade loses; 2026 favors
  baseline; concentration gates fail; tighter-stop geometry flatters the
  R-multiples.
- NOT FAIL: test-period selection directionally positive (FVG-only +0.246 vs
  omitted +0.111), survives costs, and 2025 bull FVG-only was genuinely
  broad-ish (23 trades across SOFI/AMD/QQQ/NIO/ANET/BBAI at +0.938R).

This cannot be resolved by more backtesting — one-trade dependence is only
resolvable with NEW data. The live paper sidecar (since 2026-09-23) is the
uncontaminated arbiter. Revisit at the ~50-signal checkpoint (late Oct 2026):
compare sidecar closed-trade expectancy and, specifically, whether FVG-only
live trades run hot or regress to the −0.37R median.

## Files

- `run_fvg_attribution.py` — study script (imports `run_fvg_robustness`
  helpers and `pine_backtest` unmodified; per-trade capture added)
- `fvg_attribution_results.json` — shared verification, bucket breakdowns,
  stop geometry, themes, regime×bucket, walk-forward on buckets
- `README.md` — this file

Guardrails respected: research only. V5.4, Mode B, production alerts, grades,
market gate, AI Observer, and the live paper sidecar untouched.
