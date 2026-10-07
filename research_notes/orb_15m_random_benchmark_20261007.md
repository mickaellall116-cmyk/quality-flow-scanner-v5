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

> **NULL-MISMATCH LIMITATION (ChatGPT review 2026-10-07):** ORB entries execute at the breakout candle's *close*, with the stop at the opposite range boundary — the realized risk distance is the full range width only when entry is exactly at the boundary; in practice entry is beyond it, so realized risk per trade can exceed the nominal range width. The random variants used the nominal opening-range width as their risk unit with entry at the bar close. **The risk distances are therefore not identical between ORB and random.** The estimand is ambiguous: the test measures the *entire ORB policy* (breakout timing + direction + realized risk profile) against a fixed-risk random baseline — it does NOT isolate timing/direction alone. A cleaner null would match realized per-trade risk distances; this design was not rerun. Treat the percentiles as descriptive of this specific simulation, not as a valid test of a timing-only null.
- **Costs:** reported at zero, 1bp/side, 3bp/side, 5bp/side. **These are scenarios, not substantiated by quotes or fills.** No bid/ask spread data, slippage model, or commission schedule was used. 3bp/side is labeled "closer to realistic retail all-in" as a judgment, not a measured figure.

## Data & PIT audit

- **Source:** Tiingo IEX intraday, 15m bars, via `custom.tiingo` credential. 2024-10-01 → 2026-10-07 (~2.0 years, 527 trading days, ~13,700 bars/symbol).
- **IEX-only prints**, not consolidated tape — opening-range high/low may differ by pennies from consolidated. Exact R values are approximate.
- **No lookahead:** range uses only the 09:30 bar (known at 09:45 ET); entries execute at subsequent bar closes.
- **Session handling:** regular hours only (09:30–16:00 ET), tz-aware conversion (DST-safe). Early-close days traded normally with EOD exit at the last bar; no exclusions needed (all 527 days had a valid 09:30 bar).
- **Splits/dividends:** Tiingo IEX prices are split-adjusted. QQQ/SPY paid regular quarterly dividends in-window; dividends were not modeled. Absolute R is slightly understated (no dividend capture modeled).
- **Survivorship:** none — QQQ/SPY are the traded instruments.
- **QQQ/SPY are correlated, not independent replications.** Both are large-cap US equity index ETFs with overlapping constituents; agreement between them is one data point from one market regime, not two independent confirmations.

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

2026 is negative on both symbols across most months (QQQ negative in 8 of 10 months, SPY negative in 7 of 10). Descriptive only — no causal claim is made here (crowding, volatility regime, or parameter misfit are hypotheses, not findings).

### Cost anatomy

Median first-15m range ≈ 45bps of price. A 2bp round-trip (1bp/side scenario) costs ≈ 0.044R per trade — small per trade, but over ~500 trades it erases **~80% of the gross edge** (QQQ: 28.6R → 6.0R; SPY: 47.5R → 10.8R). At the 3bp/side scenario, both are deeply negative. This mirrors the video's gold lesson: **beating random ≠ making money when friction exceeds edge** — with the caveat that the null mismatch above means "beating random" here is itself an approximate statement.

## Interpretation (amended per ChatGPT review 2026-10-07)

1. **Percentiles are descriptive, not proof.** 95th–99th percentile vs 1,000 random-entry variants under the stated simulation describes this run's outcome; it is not proof of a valid null or a stable effect — particularly given the null-mismatch limitation above.
2. **The edge is thin and fragile under cost scenarios.** Even the optimistic 1bp/side scenario consumes ~80% of gross R. The 3bp+ scenarios flip it deeply negative. Cost figures are scenarios, not measured fills.
3. **2026 is weaker, descriptively.** 2024–2025 positive, 2026 negative across most months on both symbols. No causal attribution is made.
4. **Risk is poor.** Max DD of 20–30R against +6–11R totals at the 1bp scenario = Calmar-style ratios far below any promotion bar.

## Verdict (amended)

**The 15m ORB ranks 95th+ percentile against this simulation's random baseline on QQQ/SPY, but the comparison has a known null mismatch (risk distances differ), costs are unmeasured scenarios, and 2026 is descriptively weaker. It is not tradeable on this evidence: the 1bp/side scenario erases ~80% of gross R, and the 3bp+ scenarios are deeply negative.**

## Notes for our research

- The random-entry null is worth adopting as a standing diagnostic (already added to backlog): it cleanly separates timing edge from market drift. **Any future random benchmark on forward-test data requires a frozen analysis plan first** (pre-commit the null design, then run) — the null-mismatch issue above is what happens without one.
- Script: `orb_15m_random_benchmark_20261007/artifacts/orb_test.py` (standalone). Reproducibility manifest: `orb_15m_random_benchmark_20261007/ARTIFACTS_MANIFEST.md`. No frozen code touched.
- ChatGPT evidence review: Issue #1 comment 6046384583 (2026-10-07) — verdict HOLD / exploratory diagnostic. Corrections applied in this revision.
