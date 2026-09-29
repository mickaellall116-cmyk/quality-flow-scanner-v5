# Priority 5 — Volatility normalization (measurement study)

**Question (pre-registered):** does baseline setup quality depend on volatility
at entry? Is there a broad volatility sweet spot?

**Setup:** 14-stock watchlist, 4H, Oct 2023–Sep 2026, canonical 4H Hybrid
entries, frozen Mode B exits, 25 bps. Baseline sanity rerun in-study:
237 trades, +0.239R, 50.6% win — matches prior studies exactly.
`pine_backtest.py` imported unmodified. Research only; nothing frozen touched.

## Bucket results (25 bps, n prominent)

### ATR / price at signal bar (quartiles) — strong gradient, but confounded
| bucket | range | n | exp | win% | PF |
|---|---|---|---|---|---|
| Q1 (calm) | < 0.0271 | 60 | −0.037R | 46.7 | 0.95 |
| Q2 | 0.0271–0.0371 | 59 | +0.189R | 45.8 | 1.26 |
| Q3 | 0.0371–0.0461 | 59 | +0.382R | 52.5 | 1.69 |
| Q4 (volatile) | > 0.0461 | 59 | +0.426R | 57.6 | 1.85 |

Monotonic in expectancy, win rate, and PF. **But it is mostly a symbol
proxy:** Q4 trades come from ONDS (16/16), BBAI (14/17), RKLB (13/25),
ASTX (5/5), SMCI (7/19); QQQ, ANET, SOFI have zero Q4 trades.
Within-symbol the picture is mixed (SMCI Q4 +0.224 vs rest −0.623;
RKLB Q4 +0.331 vs rest +1.303 — reversed). A filter on ATR/price would be
a backdoor ticker filter. **Redirect to P2 (ranking/universe), not a
volatility filter.**

Year × quartile: the gradient holds in all three years (2024: Q1 +0.00 →
Q4 +0.47; 2025: +0.21 → +0.60; 2026: −0.74 → +0.03 — Q4 the only
non-negative bucket in the underwater year). Persistent, but persistent
*as a symbol effect*.

### Realized-vol percentile vs trailing 500 bars (terciles) — persistent
| bucket | n | exp | win% | PF |
|---|---|---|---|---|
| low (<33) | 39 | −0.034R | 48.7 | 0.95 |
| mid (33–66) | 85 | +0.228R | 48.2 | 1.35 |
| high (>66) | 107 | +0.402R | 54.2 | 1.73 |

High-vol regime is the best bucket in **all three years**
(2024 +0.80; 2025 +0.38; 2026 +0.10 — the only positive bucket that year).
Symbol mix in the high bucket is broad (no name > 12.1%), though
within-bucket expectancy disperses (HOOD +1.30, ONDS +1.23 vs
QQQ −0.52, SOFI −0.89). Mechanism is plausible: breakouts need actual
movement; dead-market signals are false starts. **This is the one MAYBE
thread: a pre-registered follow-up testing "skip bottom-tercile
realized-vol regimes" is justified.**

### ATR percentile vs trailing 500 bars (terciles) — no pattern
| bucket | n | exp |
|---|---|---|
| low (<33) | 23 | +0.204R |
| mid (33–66) | 64 | +0.216R |
| high (>66) | 145 | +0.294R |

Directionally consistent but inconsistent by year (2024 high wins +0.80;
2025 mid wins +0.90; 2026 all negative). **No signal.**

### Breakout size / ATR (quartiles) — anti-chase shape, deferred to P6
| bucket | range | n | exp |
|---|---|---|---|
| Q1 (deepest below 10-bar high) | < −1.95 | 60 | +0.434R |
| Q2 | −1.95…−1.10 | 59 | +0.157R |
| Q3 | −1.10…−0.41 | 59 | +0.269R |
| Q4 (at/above high) | > −0.41 | 59 | +0.092R |

Entries furthest *below* the recent high do best. **Tension flagged:**
P6 (chase penalty) independently returned FAIL — its most-extended
quartile was the best (+0.297R). Different measures (distance-below-high
vs distance-from-EMA), but the chase question belongs to P6; no claim
made here.

### Stop distance / ATR — degenerate by construction (~1.5 always), flat. No signal.

## Verdict

**NO clean volatility sweet spot.** What exists:
1. A strong cross-sectional ATR/price gradient that is really a
   which-tickers effect → not a volatility filter (P2 territory).
2. A persistent time-series effect: low realized-vol regimes drag
   (−0.034R overall, −1.15R in 2026), high-vol regimes carry (+0.402R,
   best bucket every year) → **MAYBE, one follow-up justified:**
   pre-register and test skipping bottom-tercile realized-vol regimes.
3. ATR percentile: nothing. Stop/ATR: degenerate.

## Files
- `run_volatility.py` — study script (`pine_backtest` unmodified)
- `volatility_results.json` — baseline, buckets, year cross-tabs
- `README.md` — this file
