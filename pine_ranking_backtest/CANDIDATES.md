# CANDIDATES.md — Ranking-factor study (P2)

**FROZEN 2026-09-24, BEFORE any factor is run.** Research only. Control = rs_top2
(20-bar return minus SPY, take top min(2, free slots) at contested bars) — the
adopted rule. Nothing in production is touched.

## Setup (fixed)
- Universe: 14-stock watchlist (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM,
  SPCX, ASTX, BBAI, NIO, HOOD, AMD), 4H, 2023-10-25 → 2026-09-23.
- Trades: canonical `pb.gen_pine_trades` (frozen Mode B exits). Signal bar index
  recovered via per-symbol sig_index; no engine modification.
- Portfolio: $10k start, 1% risk/trade, max 5 concurrent, 5% max heat,
  next-bar-open entries, stop-first on ambiguity. Primary cost: 25bps.
- Ranking engages ONLY at contested timestamps (candidates > free slots):
  rank contenders by factor score (higher = taken first), take top min(2, free).
  Ties: deterministic by original candidate order (UNIVERSE order, then time).
- All features point-in-time at the signal bar. Missing data → score = −inf
  (ranked last).

## Factors (higher score = preferred)

| id | definition |
|---|---|
| rs_spy (CONTROL) | (Close[i]/Close[i-20]−1) − SPY_ret over the same calendar span (daily closes, last-bar-≤-timestamp) |
| rs_sector | (Close[i]/Close[i-20]−1) − SECTOR_ETF_ret over same span. Frozen mapping: SMCI/PLTR/AMD/ANET/BBAI/DRAM→XLK, SOFI/HOOD→XLF, RKLB/SPCX/ASTX/ONDS→XLI, NIO→XLY, QQQ→SPY |
| mom20 | Close[i]/Close[i-20]−1 (raw absolute momentum) |
| mom50 | Close[i]/Close[i-50]−1 |
| adx | ADX(14)[i] |
| breakout_dist | (Close[i] − max(High[i-20:i])) / ATR[i] — how decisively price cleared the 20-bar high |
| vol_expansion | Volume[i] / SMA20(Volume)[i] |
| dollar_liq | mean(Close×Volume)[i-20:i] — average dollar volume; prefers liquid names |
| atr_mom | (Close[i]/Close[i-20]−1) / (ATR[i]/Close[i]) — momentum per unit of noise |
| dist_200ema | (Close[i] − EMA200[i]) / ATR[i] |
| dist_high | −(max(High[i-50:i]) − Close[i]) / ATR[i] — nearer the 50-bar high ranks higher |
| trend_score | (e21>e55) + (Close>e200) + (adx≥20) + (Close>e21) → integer 0–4 |
| rr | (tp1 − entry)/(entry − stop) at candidate generation |

Hypotheses (one line each): rs_spy — relative leadership persists; rs_sector —
sector leadership adds information beyond market leadership; mom20 — absolute
momentum persists; mom50 — longer trends are more durable; adx — stronger trends
at entry continue; breakout_dist — decisive breaks outperform marginal ones;
vol_expansion — conviction volume confirms the break; dollar_liq — liquid names
have sponsorship and less slippage; atr_mom — momentum scaled by noise is cleaner;
dist_200ema — established uptrends persist; dist_high — leadership near highs
outperforms; trend_score — stacked trend evidence beats any single measure;
rr — better payoff asymmetry improves expectancy.

## Pre-declared combinations (mean cross-sectional percentile rank among contenders)
- C_rs_adx: (rs_spy, adx)
- C_rs_vol: (rs_spy, vol_expansion)
- C_rs_rr: (rs_spy, rr)
Run regardless of single-factor outcomes (pre-declared, not winner-picked).

## Gates
A factor PASSES only if at 25bps it beats rs_top2 on expectancy by a material
margin (≥ +0.03R, pre-declared), OR cuts max DD by ≥ 3pp without expectancy loss,
AND the win is not concentrated in one year or 2–3 symbols. Otherwise FAIL/MAYBE
per mandate gates. Small deltas = noise.
