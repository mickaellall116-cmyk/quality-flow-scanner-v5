# V6 Short Research — Backtest Analysis

**Run date:** 2026-09-17. **Window:** 2024-09-16 → 2026-09-14 (2y 4H bars).
**Universe:** 18 liquid large caps (NVDA AAPL MSFT META AMD AVGO TSLA PLTR NFLX CRM
ORCL JPM XOM LLY COST GOOGL AMZN WMT). None dropped. **QQQ buy-hold same window: +52.9%.**

Methodology mirrors the long walk-forward backtest: point-in-time signals on closed
4H bars, next-bar-open entry, stop-first same-bar ties, 4 bps + 1% annualized borrow,
1 position/symbol, 30-bar max hold. No market-gate entry filter by design (regime is
measured, not filtered). 657 signals → 230 trades (1-position rule binds hard:
signals cluster inside selloffs).

## Headline results

| Metric | Short backtest | Long backtest (structural, for reference) |
|---|---|---|
| Trades | 230 | 76 |
| Win rate | 35.2% | 36.8% |
| Expectancy | **−0.576% / −0.08R** per trade | +0.69% / +0.165R |
| Profit factor | **0.79** | 1.41 |
| Max drawdown (1% risk/trade) | **40.5%** | 11.5% |
| $10k at 1% risk | **$7,746 (−22.5%)** | $11,130 (+11.3%) |
| Exit mix | 56% stop / 26% time / 18% target | — |
| Avg hold | 14.1 bars | — |
| Avg borrow drag | 0.03% per trade (negligible — assumption held) | n/a |

## The key question: do shorts only work when the market is falling?

**No — in this window they worked worst exactly when the market was falling.**

| Regime at entry | Trades | Win rate | Expectancy |
|---|---|---|---|
| RISK-ON | 82 | 40.2% | +0.161% / −0.034R (flat) |
| CAUTIOUS | 67 | 37.3% | −0.184% / +0.127R (flat) |
| **RISK-OFF** | 81 | 28.4% | **−1.647% / −0.297R** |

Why: RISK-OFF periods in this window were sharp selloffs (Aug-24 carry unwind,
Apr-25 tariff crash, Sep-26 AI rout) followed by **violent V-shaped recoveries**.
Breakdown signals fired at the point of maximum fear — the S2 stop-out ledger is
dominated by 2025-04-08/14 (NVDA @98.75, MSFT @358, META @514: generational
bottoms). The ADX>=20 momentum filter, which helps longs ride trends, makes shorts
enter at maximum exhaustion velocity. Bear-market rallies are the sharpest moves
in equities, and the 0.5×ATR stop cannot survive them.

Market-gate split confirms no filter rescues it: BLOCK −0.042R (119 trades),
CAUTION −0.124R (74), CONFIRM −0.112R (37).

## By setup

| Setup | Trades | Win rate | Expectancy | Read |
|---|---|---|---|---|
| S1 BREAKDOWN | 127 | 37.8% | −0.504% / +0.029R | ~breakeven, slightly negative |
| S2 PULLBACK SHORT | 34 | **8.8%** | **−2.391% / −0.737R** | catastrophic |
| S3 BULL TRAP | 69 | 43.5% | +0.186% / +0.044R | ~breakeven, slightly positive |

- **S2's 8.8% win rate was verified trade-by-trade — not a bug.** In a +53% market,
  "broken support" zones are bear traps: 29 of 34 stopped at −1R. Shorting retests
  in a structural bull market is picking up pennies in front of a steamroller.
- **S3 (bull trap) is the only setup near breakeven-positive**, but +0.044R over
  69 trades is noise around zero, not an edge.

## Verdict (against criteria written before seeing results)

Criteria for "edge exists": expectancy > +0.1R, PF > 1.2, ≥30 trades, works in at
least CAUTIOUS/RISK-OFF. **Result: FAIL on every count** (−0.08R, PF 0.79, worst in
RISK-OFF).

**Honest verdict: short edge does not exist in this framework over this window.
The long-term upward drift plus the V-shaped-recovery structure of selloffs kills
it.** The framework's long edge (+0.165R) and short anti-edge (−0.08R) are two
sides of the same coin: this structural/momentum approach is a bull-market
instrument. Inverting the sign does not invert the edge because markets are not
symmetric — down-moves are faster, shorter, and reverse more violently than
up-moves persist.

## Caveats (material)

1. **Single 2-year window, QQQ +52.9%.** Shorts are regime-dependent by nature;
   this test proves the framework's shorts fail in a strong bull market — it does
   NOT prove they fail in a 2022-style sustained bear market. That is a different
   backtest (different window), not a dismissal.
2. **No trend-flip early-cover rule** (documented v1 limitation). A faster exit
   when the breakdown fails (e.g. close back above VWAP/EMA55) might cut the
   −1R stop-outs that dominate the loss column. This is the single most promising
   v2 improvement — but per research discipline, it must be specified BEFORE
   testing, not fitted to these results.
3. **S3 is the only setup worth a second look**, and only with fresh eyes, not
   because it was "close."
4. Borrow assumption (1% flat) was immaterial to results (0.03%/trade).

## What this means for the V6 decision

- Do **not** build a live short-signal path on this framework as-is. The research
  gate ("does short edge exist?") returned **no**.
- If short research continues: (a) test a 2022-window bear-market sample before
  concluding anything universal; (b) pre-specify a fast-failure exit (cover on
  reclaim of breakdown level / VWAP) as the v2 hypothesis; (c) treat S3 as the
  only candidate setup, everything else shelved.
- The bullish-framework conclusion stands: Mike's scanner + indicator stack is a
  long-side system. Short exposure, if ever wanted, should more likely come from
  a different instrument (inverse ETFs, defined-risk puts) than from inverting
  this signal logic.
