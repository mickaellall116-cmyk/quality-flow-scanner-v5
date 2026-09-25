# Canonical Portfolio Baseline — V5 (PIT 131-name universe)

_Generated 2026-09-24. Universe: PIT 131-name (strict point-in-time contract, `PIT_FEATURES.md`)._

## Headline (V5 @ 50bps round trip, $75k book)

- **Expectancy:** -0.0013R/trade
- **Win rate:** 39.8%
- **Profit factor:** 1.0
- **Max drawdown:** -39.8% ($-30,504, -40.7R)
- **Trades:** 374
- **Effective n (overlap episodes):** 7 (avg 53.4 trades/episode, largest 155 trades, max 6 concurrent). _Note: with a near-continuously occupied book, episodes chain into a handful of long clusters._
- **Annualized return:** -0.4% (total -0.9%, $74,487 -> $74,344)
- Positions still open at sample end (marked, not force-closed): 6

## Method

- **Signals:** frozen V5.4 logic (`v54_engine.v54_classify`), all grades A/B/C, strict PIT (structural contract, ADX>=20, no scores). Entry at next 4H bar open; signal bar = last bar before entry.
- **Exits:** frozen Mode B (structural stop always on, 50% at TP1, +1R arms Profit Protect, armed scanner-EXIT fills next-bar open, runner keeps structural stop, 30-bar max hold, stop wins ties). Live-faithful convention: stop filled AT the stop on gap-through bars (optimistic); realistic-gap variant also run.
- **Sizing:** $75k book, $750 fixed risk/trade (shares = floor(750/(entry-stop))), max 6 open, ~5% heat cap (sum of current position risks / marked equity).
- **Slot competition:** when qualified signals exceed free slots, rank by `rs_top2` (20-bar 4H return minus SPY, strict PIT; unrankable signals sort last), tie-break by signal timestamp then symbol. One position per symbol (live `_busy` rule); a signal on a symbol with an open/pending position is skipped.
- **Costs:** round-trip, leg-based: cost_$ = (bps/2) x sum of leg notionals. Entry = full-size leg; exits: TP1 = half-size leg, runner = half-size leg (or full-size leg if no TP1). A standard round trip = 2 leg-equivalents, so cost = bps x notional. Headline = 50bps.
- **Equity:** marked at 4H closes; costs deducted at event legs; open positions at sample end are marked, not force-closed.

## Ablation ladder (expectancy, R/trade)

| Variant | n | E[R] | Win% | PF |
|---|---|---|---|---|
| V0: old system, 14-name (sanity) | 236 | 0.2704 | 50.8 | 1.43 |
| V1: old system, 131-name (UNIVERSE) | 2487 | -0.0808 | 44.0 | 0.89 |
| V2: V3.6 entries + Mode B (MODE B) | 2995 | -0.0267 | 41.7 | 0.96 |
| V3: v54 entries + Mode B (PIT/entries) | 1645 | 0.0138 | 36.1 | 1.02 |
| V4 @ 25bps (leg-based costs) | 1645 | 0.0136 | 36.1 | 1.02 |
| V4 @ 50bps (leg-based costs) | 1645 | -0.1174 | 35.3 | 0.85 |
| V4 @ 75bps (leg-based costs) | 1645 | -0.2483 | 33.9 | 0.72 |
| V4 @ 100bps (leg-based costs) | 1645 | -0.3793 | 31.9 | 0.61 |
| V5 @ 25bps (portfolio) | 374 | 0.1029 | 39.8 | 1.16 |
| V5 @ 50bps (portfolio) | 374 | -0.0013 | 39.8 | 1.0 |
| V5 @ 75bps (portfolio) | 374 | -0.1056 | 38.0 | 0.86 |
| V5 @ 100bps (portfolio) | 374 | -0.2099 | 36.4 | 0.75 |

### Deltas (isolated step effects)

- **V0 -> V1 (universe only):** 0.2704 -> -0.0808 = **-0.3512R**. The old system's edge does not survive the neutral PIT universe (n: 236 -> 2487).
- **V1 -> V2 (Mode B exits):** -0.0808 -> -0.0267 = **0.0541R** (same V3.6 entries; exit change only).
- **V2 -> V3 (v54 entries, strict PIT):** -0.0267 -> 0.0138 = **0.0405R** (structural-contract entries, ADX>=20, no scores; n: 2995 -> 1645).
- **Gap realism (V2 live-faithful vs realistic):** -0.0267 -> -0.0642 = **-0.0375R**. Live-faithful stop fills at the stop on gap-through bars are optimistic by ~0.04R.
- **V3 -> V4 @50bps (costs):** 0.0138 -> -0.1174 = **-0.1312R** (25bps-once convention -> 50bps leg-based round trip).
- **V4 -> V5 @50bps (portfolio):** -0.1174 -> -0.0013 = **0.1161R** (slots/heat/ranking filter 1645 -> 374 trades).

_Bridge note:_ V0 mixes legacy V3.6 entries/exits with the 14-name watchlist; V1..V5 use the PIT 131-universe. The V0->V1 step is a universe-only comparison (same engine/exits/costs); the V2->V3 step changes the entry definition (V3.6 Hybrid -> v54 structural contract), so it is not a pure PIT effect — it bundles the entry-definition change with strict-PIT enforcement.

### V5 signal funnel

- Candidate v54 signals: 4127
- Skipped (symbol busy — live `_busy` rule): 622
- Skipped (no free slot, lost rs_top2 rank): 744
- Skipped (5% heat cap): 2387
- **Accepted: 374**

## Splits

### By exit year (@50bps)

| Year | n | E[R] | Win% | Total R |
|---|---|---|---|---|
| 2024 | 117 | -0.2538 | 35.0 | -29.69 |
| 2025 | 128 | 0.061 | 41.4 | 7.81 |
| 2026 | 129 | 0.1658 | 42.6 | 21.39 |

### By market regime at signal (@50bps)

_Regime: bull = SPY close > EMA200 and EMA200 rising vs 20 daily bars ago; bear = below and falling; else sideways. Joined on the last completed daily bar at signal time._

| Regime | n | E[R] | Win% | Total R |
|---|---|---|---|---|
| bear | 8 | -0.0135 | 37.5 | -0.11 |
| bull | 356 | 0.0107 | 40.2 | 3.8 |
| sideways | 10 | -0.42 | 30.0 | -4.2 |

## Concentration

- **Top 10 trades:** 58.48R total (-11622.9% of total). Ex-top-10 expectancy: -0.162R (n=364).
  - SNDK 2025-12-31: 9.3R (TIMEOUT)
  - AVGO 2024-12-10: 7.44R (TIMEOUT)
  - PLTR 2025-01-27: 6.61R (TIMEOUT)
  - MU 2025-05-23: 6.06R (TIMEOUT)
  - SNDK 2025-10-10: 5.64R (TIMEOUT)
  - ARM 2026-05-07: 5.45R (TIMEOUT)
  - ARM 2026-04-10: 5.04R (TIMEOUT)
  - CAT 2025-09-05: 4.5R (TIMEOUT)
  - HD 2025-08-01: 4.29R (TIMEOUT)
  - MS 2024-10-25: 4.16R (TIMEOUT)
- **Top symbols by total R:** SNDK (14.24R, n=4), ARM (11.27R, n=3), PLTR (9.38R, n=4), CRWD (7.68R, n=4), MELI (6.57R, n=3), GOOGL (5.89R, n=7), AVGO (5.19R, n=3), CAT (4.16R, n=4)
- **Best year:** 2026. Ex-best-year expectancy: -0.0893R (n=245).
- **Top sectors by total R:** Technology (32.16R), Communication Services (2.71R), Utilities (0.97R), Consumer Cyclical (0.81R), Industrials (-1.68R), Energy (-2.35R), Healthcare (-4.06R), Consumer Defensive (-4.24R)
- **Hypothetical max-2-per-sector rule:** would have bound on 3 signal batches (3 excess trades). No such rule exists in live V5.4 — hypothetical only.

## 14-name watchlist overlay (separate — NOT canonical)

_Same V5 machinery, restricted to the 14-name watchlist. Reported for comparison only._

| Cost | n | E[R] | Win% | PF |
|---|---|---|---|---|
| 25bps | 151 | 0.5161 | 45.7 | 1.94 |
| 50bps | 151 | 0.4489 | 45.7 | 1.77 |
| 75bps | 151 | 0.3817 | 45.7 | 1.61 |
| 100bps | 151 | 0.3146 | 45.7 | 1.48 |

## Caveats

- Live-faithful Mode B fills stops AT the stop on gap-through bars (optimistic by ~0.04R vs realistic gap fills).
- No capital-availability constraint beyond slots/heat; notional tied up is tracked but not enforced.
- Regime join uses the last completed daily SPY bar at signal time.
- Effective n uses overlap-episode clustering (connected components of overlapping holding intervals).
- 4H bars for US names cover 09:30-16:00 ET only; crypto is 24/7.

## Files

- `canonical_baseline/portfolio_results.json`
- `canonical_baseline/canonical_trades.json`
- `canonical_baseline/v0_trades.json`
- `canonical_baseline/v1_trades.json`
- `canonical_baseline/v2_trades.json`
- `canonical_baseline/v3_trades.json`
- `canonical_baseline/v4_cost_ladder.json`
- `canonical_baseline/v5_summary.json`
- `canonical_baseline/v5_overlay14.json`
- `canonical_baseline/ablation_V0_V3.json`
- `canonical_baseline/simlib.py`
- `canonical_baseline/run_ablation.py`
- `canonical_baseline/run_portfolio.py`
- `canonical_baseline/analyze.py`
