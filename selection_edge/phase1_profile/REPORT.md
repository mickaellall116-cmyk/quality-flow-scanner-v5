# Phase 1: Per-Stock Profiling — Report

_2026-09-24. Selection-Edge Worker A. Descriptive measurement only — no factors built, no thresholds, no PASS/FAIL._

## Blinding

The 14 names (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX, ASTX, BBAI, NIO, HOOD, AMD) were excluded from everything below. Only 8 of them sit inside the 131-name PIT universe (AMD, ANET, DRAM, NIO, PLTR, QQQ, SMCI, SPCX); the other 6 were never in the universe, so masking them was automatic. **Working set = 123 stocks.** Per-stock R = `net_r_50bps` from `canonical_trades.json` (headline cost level).

## 1. Coverage

- 21 of 123 working-set stocks have ≥5 trades (rankable).
- 93 have 1–4 trades (thin; 237 trades, −10.15R combined).
- 9 have zero trades.
- The 21 rankable stocks account for 116 trades; the working set total is 353 trades / −10.13R.

## 2. The central fact

**The rankable stocks' expectancies are symmetric noise around zero.** The positive-expectancy group (11 stocks, 62 trades, +0.394R/trade, win rate 58%, PF 1.78) is almost exactly cancelled by the negative-expectancy group (10 stocks, 54 trades, −0.452R/trade, win rate 28%, PF 0.46): **+24.43R vs −24.41R, net +0.02R.** Everything below zero in the working set's P&L comes from the thin group (−10.15R from 237 sub-5-trade stocks).

Distribution of expectancy across the 21 rankable stocks (0.5R buckets):

| Bucket | Stocks |
|---|---|
| +0.50…+1.00R | 3 |
| +0.00…+0.50R | 8 |
| −0.50…+0.00R | 6 |
| −1.00…−0.50R | 4 |

The positive tail is **not a handful of names** — it is 11 stocks spread across the buckets. But: every per-stock expectancy rests on 5–7 trades. Nothing here is statistically stable; the top-vs-bottom ranking is a lottery ticket table, reported as observed only.

## 3. Ranked per-stock summary (n ≥ 5, working set only)

**Top 5 by expectancy:**

| Symbol | n | Expectancy | Sum R | PF | Win rate |
|---|---|---|---|---|---|
| GOOGL | 7 | +0.842R | +5.9 | 5.68 | 86% |
| OXY | 5 | +0.741R | +3.7 | 1.95 | 40% |
| JPM | 5 | +0.700R | +3.5 | 2.32 | 60% |
| LRCX | 5 | +0.490R | +2.4 | 3.26 | 80% |
| BRK-B | 5 | +0.391R | +2.0 | 1.87 | 60% |

**Bottom 5 by expectancy:**

| Symbol | n | Expectancy | Sum R | PF | Win rate |
|---|---|---|---|---|---|
| RTX | 7 | −0.413R | −2.9 | 0.54 | 29% |
| MPC | 6 | −0.540R | −3.2 | 0.45 | 17% |
| UBER | 5 | −0.631R | −3.2 | 0.21 | 20% |
| PANW | 5 | −0.839R | −4.2 | 0.14 | 20% |
| XLE | 6 | −0.964R | −5.8 | 0.12 | 17% |

Full per-stock table (n, expectancy, PF, win rate, median, avg winner, avg loser, own-series max DD in R, sum R, share of total absolute P&L) is in `PROFILE.json`. Thin stocks (n<5) are reported separately there; never ranked.

## 4. Pre-trade characteristics: positive vs negative group

All characteristics were computed from data available **at or before 2023-09-30** (universe formation date; last usable daily bar 2023-09-29). No future performance enters. "52-week-high distance" is approximated by max-high distance on the ~4 months of daily history available pre-formation — flagged as a limitation, not a true 52-week value.

| Characteristic (as of 2023-09-30) | Positive group (n=11) | Negative group (n=10) | Difference | Read |
|---|---|---|---|---|
| Trailing 63d RS vs SPY | +7.6% mean / +5.8% median | +1.7% mean / −2.7% median | **+5.9pp mean / +8.4pp median** | DIFFER — biggest separation |
| ADDV rank (1 = highest $ volume) | 54.4 mean / 59 median | 64.0 mean / 67.5 median | −9.6 mean / −8.5 median | DIFFER — positive group higher dollar volume |
| 52wk-high distance | −10.4% / −9.0% | −11.2% / −8.3% | +0.8pp / −0.8pp | NO DIFFERENCE (means & medians disagree) |
| Trailing 63d ATR/price | 2.26% / 2.16% | 2.35% / 2.21% | −0.09pp | NO DIFFERENCE |
| Dollar-volume trend (last21d ADDV / first21d ADDV of window) | 1.02 mean / 0.83 median | 0.97 mean / 1.02 median | mean +0.05, median −0.19 | NO DIFFERENCE (sign flips mean vs median = noise) |
| Sector mix | Tech 3, FinSvcs 3, Energy 2, HC 2, Comm 1 | Tech 2, Energy 2, ETF 2, HC 1, Comm 1, ConsDef 1, Ind 1 | FinSvcs 27% vs 0%; ETFs 0% vs 20% | POSSIBLY DIFFER — n=21, anecdotal |

Every difference below is **hypothesis generation, explicitly untested**: the groups were formed from noisy 5–7-trade samples, n=21 stocks, no significance computed, and nothing was validated out-of-sample.

## 5. Candidate characteristics for Phase 2 (untested)

1. **Trailing relative strength vs SPY at universe entry (candidate)** — the positive group was running ahead of SPY (+5.8% median) while the negative group was trailing (−2.7% median). Maps to F1 in the factor menu. Status: UNTESTED.
2. **Dollar-volume level / ADDV rank at universe entry (candidate)** — the positive group ranked ~10 slots higher by 2023-09-30 ADDV. Maps to a level (not expansion) version of the volume question. Status: UNTESTED.
3. **Sector membership (weak candidate)** — Financial Services appears only on the positive side, ETFs (XLE, IWM-style index trackers) only on the negative side. Sector is a coarse, 21-stock anecdote here; Phase 2's sector-leadership (F5) is a different, cleaner construction. Status: UNTESTED.
4. **Not supported as candidates by this pass:** proximity to 52wk high, ATR/price volatility level, dollar-volume trend (first vs second half of formation window). They do not separate the groups; de-prioritize unless Phase 2 construction differs.

## 6. Caveats that matter

- Per-stock expectancies on 5–7 trades have standard errors on the order of ±0.5R — the top-5/bottom-5 ordering is mostly noise.
- Group characteristics were computed with stocks ranked on the same in-sample trades they later "explain" — Phase 2 must test forward of formation, not re-describe these groups.
- dist_high is not a true 52-week distance (only ~4 months of daily history predates formation).
- The working set's negative total (−10.13R) is dominated by the thin group; any selector that merely skips thin names would "help" here, but that is a sample-depth artifact, not an edge.

## Files

- `PROFILE.json` — per-stock table, group comparisons, characteristic differences, sector table, histogram, thin-stock table
- `run_phase1.py` — the script that built it (imports data, never rebuilt it)
