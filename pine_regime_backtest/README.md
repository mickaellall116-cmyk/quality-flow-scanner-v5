# Priority 4: Market-regime conditioning — results

**Question (descriptive only, no filter built):** WHEN is the baseline 4H Hybrid
edge strongest/weakest? Is any difference large and persistent enough to justify
a future regime filter?

**Setup:** 14-stock watchlist, 4H, Oct 2023–Sep 2026. Canonical `pine_buy_signal`
+ `gen_pine_trades` (pine_backtest imported unmodified), frozen Mode B exits,
25bps costs. Baseline rerun in-study: 237 trades, +0.239R, 50.6% win, PF 1.38.
Regime labels from daily SPY/QQQ/VIX at the signal date (pre-declared buckets,
no tuning).

## Headline: NO — not justified as a future filter

The apparent "stress-regime edge" is **two individual trades**, not a regime
effect:

| Trade | Date | Net R | Context |
|---|---|---|---|
| HOOD | 2025-04-29 | +8.67R | tariff-crash V-recovery |
| AMD | 2026-04-02 | +5.88R | V-recovery |

Together: +14.55R = **26% of the entire study's expectancy** (56.6R total).
Remove them and every "stress beats calm" gap collapses:

- SPY below 200 EMA: +1.53R (n=8) → the two giants are both in this bucket.
- SPY 50-day momentum negative: +0.88R (n=13, "persistent" 2025 +0.875 / 2026 +0.890) → ex-giants: **−0.28R** over the remaining 11.
- VIX 20–30: +0.79R (n=26, positive in all three years) → ex-giants: +0.25R, i.e. ordinary baseline noise.

## Regime table (25bps, n prominent)

| Bucket | n | Exp R | Win% | PF | Share of total R |
|---|---|---|---|---|---|
| SPY above 200 EMA | 229 | +0.19 | 50.7 | 1.31 | 78% |
| SPY below 200 EMA | 8 | +1.53 | 50.0 | 4.12 | 22% ← 2 giants |
| QQQ above/below 200 EMA | 230 / 7 | +0.19 / +1.93 | — | — | same story |
| VIX low <20 | 210 | +0.17 | 50.5 | 1.26 | 62% |
| VIX mid 20–30 | 26 | +0.79 | 50.0 | 2.67 | 36% ← 2 giants |
| VIX high >30 | 1 | +1.29 | 100 | — | thin, ignore |
| SPY mom50 pos / neg | 224 / 13 | +0.20 / +0.88 | — | — | neg bucket = giants |
| RV20 low / high | 149 / 88 | +0.29 / +0.15 | — | — | flips in 2026 |
| Bull / bear / sideways | 225 / 5 / 7 | +0.20 / +1.45 / +0.65 | — | — | bear = 5 trades |

## Why NO — four reasons

1. **The sample barely visits stress regimes.** 225 of 237 trades fired in bull
   markets; 229 with SPY above its 200 EMA. A "bear filter" would be built on
   n=5–9 trades. Thin buckets don't count.
2. **The stress outperformance is two trades, not a regime.** Both are
   V-recovery explosions after market stress. Fascinating mechanism (the system
   catches violent snapbacks), but n=2 is not a filter — it's an anecdote.
3. **The year effect dominates any regime effect.** 2026 YTD is underwater in
   EVERY bucket (bull −0.33R, VIX low −0.35R, RV20 low −0.45R). If regime
   conditioning were real, the "good" regimes would still work in 2026. They
   don't.
4. **Extreme tail concentration.** Top 2 trades = 27% of total R; top 5 = 60%;
   top 10 = 99.8%. In a fat-tail system like this, regime attribution is mostly
   luck-of-where-the-tails-landed. Any bucket the giants fall into looks like a
   "good regime."

## Genuine descriptive findings (not filter material)

- The system's edge is **fat-tailed**: it lives in a handful of explosive
  winners (RKLB +6.69R, ONDS +6.68R, SOFI +5.85R, ...), many of them
  V-recoveries after market stress. Losers are capped (~−1R typical, worst
  −5.05R on one ANET trade). This is the payoff-asymmetry design working as
  intended — but it means no regime bucket with n<20 can be trusted.
- **2026 YTD is uniformly negative** (−0.24 to −0.45R across all buckets).
  The edge is not firing this year in any regime. Worth monitoring via the
  forward test, not worth a regime filter.
- RV20 low-beats-high held in 2024 (+0.41 vs +0.20) and 2025 (+0.62 vs +0.18)
  but flipped in 2026 (−0.45 vs +0.06). Not persistent — parked.

## Verdict

**NO.** No regime difference is large, persistent, and well-sampled enough to
justify a future filter. The stress-regime outperformance is two outsized
V-recovery trades; the sample is 95% bull-market; 2026 fails in all regimes.
Regime conditioning joins the tested-and-parked list. Revisit only if the
forward test accumulates real bear-market samples (n≥30 in stress buckets).

## Files

- `run_regime.py` — study script (pine_backtest imported unmodified)
- `regime_results.json` — buckets, year cross-tabs, expectancy shares
- `cache/d_SPY.pkl`, `d_QQQ.pkl`, `d_VIX.pkl` — daily market data (yfinance)
- `README.md` — this file
