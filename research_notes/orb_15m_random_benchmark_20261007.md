# 15-Minute Opening Range Breakout — Random-Entry Benchmark Test

**Date:** 2026-10-07
**Type:** RESEARCH ONLY. Not a trade recommendation. No frozen-system changes.
**Question:** Does the 15m ORB (per Quant Lab video) show edge on QQQ/SPY beyond what random entries achieve, after costs?

## Method (replicating the video)

- **Range:** high/low of the first 15m bar of the regular session (09:30–09:45 ET).
- **Entry:** first 15m candle that *closes* outside the range (long above / short below), at that close.
- **Stop:** other side of the range. **Target:** 2× risk. One trade/day max.
- **Same-bar stop+target:** stop assumed first (conservative).
- **EOD rule (not in video, required):** exit at last regular-session bar close if neither stop nor target hit.
- **Random benchmark:** 1,000 variants. Same risk unit (that day's ORB range width), same 2R target, random entry bar (uniform over session bars after 09:45), random direction (50/50). Two comparisons: matched to ORB's trading days (primary — isolates timing/direction edge) and all valid days (secondary).
- **Costs:** reported at zero, 1bp/side, 3bp/side, 5bp/side.

## Data & PIT audit

- **Source:** Tiingo IEX intraday, 15m bars, via `custom.tiingo` credential. 2024-10-01 → 2026-10-07 (~2.0 years, 527 trading days, ~13,700 bars/symbol).
- **IEX-only prints**, not consolidated tape — opening-range high/low may differ by pennies from consolidated. Directional results are robust to this; exact R values are approximate.
- **No lookahead:** range uses only the 09:30 bar (known at 09:45 ET); entries execute at subsequent bar closes.
- **Session handling:** regular hours only (09:30–16:00 ET), tz-aware conversion (DST-safe). Early-close days traded normally with EOD exit at the last bar; no exclusions needed (all 527 days had a valid 09:30 bar).
- **Splits/dividends:** Tiingo IEX prices are split-adjusted. QQQ/SPY paid regular quarterly dividends in-window (small ex-div gaps); these affect ORB and random equally, so the comparison is fair. Absolute R is slightly understated (no dividend capture modeled).
- **Survivorship:** none — QQQ/SPY are the traded instruments.

## Results

### QQQ — 499 ORB trades over 527 days

| Cost | ORB total R | Win rate | Avg win | Avg loss | Max DD (R) | ORB pct vs 1,000 random |
|---|---|---|---|---|---|---|
| zero | **+28.6R** | 47.1% | +1.06R | −0.83R | 13.4R | **95.4%** |
| 1bp/side | **+6.0R** | 46.3% | +1.03R | −0.87R | 19.9R | 95.4% |
| 3bp/side | **−39.3R** | — | — | — | 52.0R | — |
| 5bp/side | **−84.5R** | — | — | — | 86.0R | — |

Random-matched (1bp): mean −25.0R, median −25.6R, σ 18.6R, p5 −54.3R, p95 +5.4R.

### SPY — 500 ORB trades over 527 days

| Cost | ORB total R | Win rate | Avg win | Avg loss | Max DD (R) | ORB pct vs 1,000 random |
|---|---|---|---|---|---|---|
| zero | **+47.5R** | 44.8% | +1.29R | −0.88R | 12.9R | **98.9%** |
| 1bp/side | **+10.8R** | 43.8% | +1.25R | −0.93R | 29.8R | 98.9% |
| 3bp/side | **−62.8R** | — | — | — | 78.5R | — |
| 5bp/side | **−136.3R** | — | — | — | 137.7R | — |

Random-matched (1bp): mean −39.5R, median −39.5R, σ 21.3R, p5 −76.0R, p95 −4.5R.

### Per-year breakdown (1bp/side)

| Year | QQQ R | SPY R |
|---|---|---|
| 2024 (64d) | +8.7R | +23.2R |
| 2025 (~246d) | +5.4R | +3.7R |
| 2026 (~190d) | **−8.1R** | **−16.2R** |

2026 decay is broad-based, not one bad month: QQQ negative in 8 of 10 months, SPY negative in 7 of 10.

### Cost anatomy

Median first-15m range ≈ 45bps of price. A 2bp round-trip (1bp/side) costs ≈ 0.044R per trade — small per trade, but over ~500 trades it erases **~80% of the gross edge** (QQQ: 28.6R → 6.0R; SPY: 47.5R → 10.8R). At 3bp/side (closer to realistic retail all-in), both are deeply negative. This is the video's gold lesson reproduced exactly: **beating random ≠ making money when friction exceeds edge.**

## Interpretation

1. **The timing edge is real.** 95th–99th percentile vs 1,000 random-entry variants with identical risk/target structure is not luck. ORB entry selection (breakout direction + timing) adds value beyond random.
2. **The edge is thin and fragile.** Even optimistic 1bp/side costs consume ~80%. Realistic retail costs (spread + fees ≈ 3bp+) flip it to −40R to −140R territory.
3. **The edge is decaying.** 2024–2025 positive, 2026 negative across most months on both symbols. Possible causes: vol-regime change, ORB crowding, or the 2R-target/1R-stop ratio misfit to current intraday ranges. Not diagnosed here.
4. **Risk is poor.** Max DD of 20–30R against +6–11R totals at 1bp costs = Calmar-style ratios far below any promotion bar.

## Verdict

**The 15m ORB shows genuine timing edge on QQQ/SPY (95th+ percentile vs random), but it is not tradeable: 1bp/side costs erase ~80% of it, realistic 3bp+ costs make it deeply negative, and 2026 shows broad-based decay.**

## Notes for our research

- The random-entry null is worth adopting as a standing diagnostic (already added to backlog): it cleanly separates timing edge from market drift.
- Script: `/tmp/orb_test.py` (standalone; raw data in `/tmp/qqq_15m*.json`, `/tmp/spy_15m*.json`). No frozen code touched.
