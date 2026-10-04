# TOP-vs-BROAD: Consolidated Readiness Package (final)
**Status:** READINESS COMPLETE — awaiting Mike's performance-run decision (2026-10-04).
**No performance run. No holdout access. No launch.**

This consolidates: v3 proposal (design accepted), readiness package v1, addendum v2 (blockers 1,3,4,5), system map (strategy identity), data inventory (blocker 2), and Mike's qualifications.

---

## 1. The experiment (frozen)

**Question:** does the TOP-50 stock-selection rule improve the complete studied C1 system versus BROAD?

**System (Mike's choice — System 1):** `gen_candidates` (`pine_ranking.py:25`) → `compute_features` (`pine_ranking.py:95`, rs/vol/rr) → `simulate_stack` (`pine_stack.py:40`, rs top-2 ranking when contested, sector cap 2, 5 slots, 5% heat, S4 DD gate, 1% sizing). Source-backed map: `research_notes/system_map_sourced_20261004.md`.

**Only difference between legs:** universe membership (TOP-50 vs BROAD-218). Same signals, same exits, same portfolio, same costs (4bps + 25bps), same window.

**Baseline note (Mike's qualification):** the 240-trade/+0.178R result is a **reproduction reference**, not the experiment baseline. BROAD is newly computed on corrected session-anchored candles (commit `b3a7251`); the old headline (old candle grid) is not the comparison point.

## 2. Universe (frozen)

- **BROAD: 218 US stocks.** 225-stock pool (250 minus 25 crypto, preregistered scope correction) minus 7 warmup exclusions (below).
- **TOP: 50 stocks**, quarterly rebalance, composite = 50% liquidity percentile + 50% RS-vs-SPY percentile (v3 §2, smallest scores win).
- **Exclusions (warmup contract, not returns):** BMNR, CRWV, GLXY (listed after study start); NBIS, XYZ (listed too late for 215 bars); CLSK (1 vendor-gap day, 214 bars); SBET (partial sessions, 212 bars + reverse split). Documented in `research_notes/data_inventory_20261004.md`.

## 3. Window (frozen, revised per inventory)

**Study window: 2025-03-17 → 2026-09-14** (~18 months, 19 calendar month-buckets).

**Why not Mar 10:** the inventory proved 0/225 symbols reach 215 warmup bars before Mar 10 (Yahoo's 730-day boundary supplies only ~210–211). Mar 17 supplies 216. This is a **data-forced revision**, documented before any performance computation — not tuning.

- TOP rebalances: initial Dec 31, 2024 (daily lookback to ~Jul 2024), then Mar 31 2025, Jun 30 2025, Sep 30 2025, Dec 31 2025, Mar 31 2026, Jun 30 2026.
- G3: Y1 = 2025-03-17 → 2026-03-16 (full year); Y2 = 2026-03-17 → 2026-09-14 (~6 months, partial, labeled). ≥25 trades/leg/period retained.

## 4. Data readiness (verified)

**Inventory:** `research_notes/data_inventory_20261004.md` — 225/225 1H downloads (Yahoo, 2024-10-07 → 2026-09-15, raw OHLCV); 4H built with corrected resampler (bar-count only); per-symbol warmup audit at both cutoffs.

- **218/225 pass** the 215-bar warmup before Mar 17. 7 exclusions above.
- **15 symbols have splits in-window** (9 likely real, 6 flagged VERIFY as probable Yahoo artifacts). **Pre-run requirement:** split-aware raw series for the dollar-volume ranking input. Reported, not adjusted — implementation must handle before the run.
- **Sealed holdout untouched.** No sealed-4H reads. Daily ranking overlap logged as ranking-only.

## 5. Implementation verification (builder-tested)

- **Trade engine:** 16/16 synthetic fixtures pass (`tests/test_qf_r1_synthetic_20261004.py`) — entry, gap-below-stop, TP1/runner, close-evaluated stops, R-blending, coverage denominator (13:30/16:00/early-close), stale marks.
- **Portfolio stack:** 9/9 targeted fixtures pass (`tests/test_simulate_stack_20261004.py`) — rs top-2 ranking (with the aggressive in-loop contest behavior documented), sector cap 2, 5-slot cap, 5% heat, S4 DD gate, 1% sizing.
- **Coverage rule (fixed):** expected *completed* intervals through decision time (4/4 at 13:30, 7 at 16:00, 3/3 early-close); 4H candles missing any hourly constituent are not emitted (fail-closed).
- **Missing marks:** stale valuation, exposure retained, flagged.
- **Status:** builder-tested; Mike's independent inspection/execution pending.

## 6. Gates (frozen, from v3, with terminology corrections)

- G0: TOP expectancy @25bps > +0.15R. G1: TOP−BROAD > +0.10R. G2: TOP annualized Calmar >1.0 and > BROAD. G3: TOP beats BROAD in Y1 and Y2 (≥25 trades/leg/period). G4: ≥100 trades/leg. G5: 95% bootstrap CI (moving 3-month paired blocks, seed 20261004) lower bound > 0.
- **INCONCLUSIVE** (not rejection): insufficient counts, degenerate ranking, or >10% bootstrap discard rate.
- **Development screening gates** — they do not spend the holdout (parked per §12).

## 7. What "yes" authorizes / what remains

**A "yes" authorizes:** the BROAD + TOP computation on the inventoried data, under the frozen System 1, with gates evaluated mechanically. **No holdout access. No signal changes. No paper trading.**

**Pre-run implementation items (must complete before the run, no performance impact):**
1. Split-aware raw price series for the 15 flagged symbols (dollar-volume ranking input).
2. TOP/BROAD membership code + quarterly rebalance on the frozen composite.
3. Bootstrap implementation per the frozen algorithm.

**Open:** Mike's independent fixture inspection. ChatGPT's review of this package.

---

**Builder's assessment:** all five review blockers are resolved or verified. The material facts are: 218-symbol BROAD with full warmup, System 1 pinned and fixture-tested, window data-forced to Mar 17, splits flagged for pre-run handling. The decision is Mike's.
