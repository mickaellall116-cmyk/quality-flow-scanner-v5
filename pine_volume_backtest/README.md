# Priority 8 — Relative volume and liquidity

**Question:** does volume/liquidity at entry affect baseline 4H Hybrid expectancy?
Does volume confirm the setup, or is it noise?

**Setup:** 14-stock watchlist, 4H bars Oct 2023–Sep 2026, canonical
`pine_buy_signal` + `gen_pine_trades` (`pine_backtest` imported unmodified),
frozen Mode B exits, 25 bps costs. Baseline rerun in-study: 237 trades,
+0.239R, 50.6% win, PF 1.38.

**Volume metrics at the signal bar (pre-declared, no tuning):**
- RVOL = signal-bar volume / 20-bar mean → low(<0.8) / med(0.8–1.5) / high(>1.5)
- Dollar volume = volume × close → pooled terciles
- Avg dollar volume = 20-bar mean of volume×close → pooled terciles
- Expansion = signal-bar volume / 10-bar mean → pooled quartiles

## Results

### RVOL — flat, no confirmation effect
| bucket | n | exp | win | PF |
|---|---|---|---|---|
| high >1.5 | 83 | +0.248R | 51.8% | 1.40 |
| med 0.8–1.5 | 154 | +0.234R | 50.0% | 1.37 |

No low-RVOL bucket exists at all — the breakout signal essentially requires
volume, so there is no low-volume variation to exploit. Year cross-tab flips
sign (2024: med +0.532 vs high −0.001; 2025: high +0.789 vs med +0.252;
2026: both negative). Pure noise.

### Signal-bar expansion quartiles — no pattern
| bucket | n | exp | win | PF |
|---|---|---|---|---|
| Q1 (lowest) | 60 | +0.327R | 55.0% | 1.56 |
| Q2 | 59 | +0.361R | 55.9% | 1.66 |
| Q3 | 59 | +0.059R | 45.8% | 1.08 |
| Q4 (highest) | 59 | +0.207R | 45.8% | 1.32 |

Non-monotonic; year cross-tab flips (2024 best = Q1 +0.873; 2025 best = Q2
+0.794; 2026 all quartiles negative). Noise.

### Dollar volume terciles — strong headline, but a size proxy
| bucket | n | exp | win | PF | share of total R |
|---|---|---|---|---|---|
| T1 low | 79 | +0.505R | 58.2% | 2.05 | 70.5% |
| T2 mid | 79 | +0.073R | 45.6% | 1.10 | 10.1% |
| T3 high | 79 | +0.138R | 48.1% | 1.21 | 19.3% |

Persistent in 2024 (T1 +0.49) and 2025 (T1 +0.737); breaks in 2026
(T1 n=9, −0.034R).

**But the bucket composition shows it is a symbol/size proxy, not a volume
effect.** T1_low = BBAI(15), RKLB(12), NIO(11), SOFI(11), ONDS(10), ANET(9),
HOOD(5), ASTX(4), SMCI(2) — the small-cap / low-price names. T3_high =
QQQ(29), AMD(23), PLTR(15), HOOD(6), SMCI(4) — the large caps. A "low dollar
volume" filter would simply exclude QQQ, AMD and most of PLTR — a
portfolio-construction decision (drop the most liquid core names), not a
volume edge. Same rejection logic as P5's ATR/price gradient (backdoor ticker
filter, rejected).

Within-symbol check (low vs high dollar-volume half, symbols with ≥8 trades):
8 of 11 names favor the low half (e.g. HOOD +1.603R vs −0.392R, ONDS +1.278R
vs +0.042R, AMD +0.551R vs −0.128R; exceptions: BBAI, QQQ, SMCI). Suggestive
but halves are 4–15 trades each — too thin to promote — and within-symbol
dollar volume is confounded with entry price level (cheaper entries = earlier
in the sample), which overlaps the already-tested P6 extension question.

Avg-dollar-volume terciles tell the same size story (T1 +0.347R, T3 +0.043R).

## Verdict: NO

Volume does not confirm the setup:
1. The clean volume metrics (RVOL, signal-bar expansion) are flat with
   sign-flipping year cross-tabs — noise.
2. The dollar-volume "edge" is a backdoor size filter, rejected on the same
   grounds as P5. It is not a volume effect and must not be smuggled in as one.
3. The within-symbol low-dollar-volume hint (8/11 names) is too thin and too
   confounded to act on.

**Do not impose a volume filter.** Noted thread for the record: within-symbol
low dollar volume beat high in 8 of 11 names — worth one pre-registered
follow-up only if a larger sample ever exists, not a filter today.

## Files
- `run_volume.py` — study script (`pine_backtest` imported unmodified)
- `volume_results.json` — baseline, bucket cuts, per-bucket stats, year cross-tabs
- `README.md` — this file

Research only. No frozen files touched.
