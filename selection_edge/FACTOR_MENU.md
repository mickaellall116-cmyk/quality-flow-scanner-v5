# Selection-Edge Factor Menu — PRE-REGISTERED 2026-09-24 (before any testing)

> SUPERSEDED IN PART by Mike's exact specification (2026-09-24, ~22:35). The
> spec below remains the pre-registration record. Where they differ, Mike's
> spec governs: Phase 1 per-stock profiling first; Phase 2 tests the 8
> families below ONE AT A TIME with BROAD quartile buckets and MONOTONICITY
> as the primary question (not binary thresholds); Phase 4+ (combos, true
> OOS, placebo ≥5,000, selector validity A/B/C, anti-hindsight, portfolio
> replay) run only after independent factors survive. FIRST THING TO RUN:
> 3-mo RS vs SPY, 6-mo RS vs SPY, sector RS, distance from 52-week high —
> separately, PIT price data only, no combining.

Lane 2 priority research. Question: "Can we systematically identify the subset of stocks where Quality Flow actually works?" — with only point-in-time information, never touching the 14 names during construction.

## Blinding rule (hard, applies to every factor below)

The 14 names (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX, ASTX, BBAI, NIO, HOOD, AMD) are MASKED OUT of the PIT universe for all factor construction, threshold-setting, and evaluation. They appear only as a final reporting overlay after each factor is frozen. Any result built with knowledge of the 14 is invalid.

## Test design (same for every factor)

- Universe: canonical PIT 131-name universe, 14 masked → 117-name working set.
- Signals: canonical V5.4 4H long-signal population (canonical_baseline/canonical_trades.json + candidate pool), factor computed strict-PIT at each signal timestamp.
- Split: selected vs unselected on the same signal population. Primary test is RELATIVE (selected expectancy vs unselected expectancy) AND absolute (does selected clear zero?).
- Protocol: dev Oct 2023–Dec 2024 / val Jan 2025–Sep 2026; walk-forward 12mo/6mo; year splits; 25/50/75/100bps round-trip; perturbation not optimization; concentration; bootstrap ≥5,000; leave-one-symbol-out; economic effect.
- Economic check: portfolio replay restricted to selected names vs full working set (same $75k/1%/6-slot/5%-heat/rs_top2 machinery, imported from canonical_baseline/).
- Gates: PASS = selected beats unselected on validation + costs + perturbation + survives LOSO/concentration, and selected clears zero. MAYBE = directionally consistent but thin/fragile. FAIL = otherwise. "No factor survives" is an acceptable result.

## The factors

### F1 — Trailing relative strength vs SPY (20 trading days)
- **Construction:** 20-trading-day total return of stock minus 20-trading-day total return of SPY, endpoint = last completed daily bar as of signal time (the strict-PIT convention). Select: RS > 0 (pre-registered; perturb 15/25 days, and median-split variant as robustness only).
- **Mechanism:** A 4H breakout system buys continuation. Continuation works when there is already institutional sponsorship behind the name; RS vs SPY > 0 is the simplest PIT proxy for "this stock is being accumulated relative to the market." Breakouts in stocks the market is already rewarding should follow through more often than breakouts in laggards fighting for attention.

### F2 — Own-price momentum acceleration (10d vs 60d)
- **Construction:** (10-trading-day return) minus (preceding 50-trading-day return), i.e. recent return minus baseline drift, strict PIT on daily closes. Select: acceleration > 0 (pre-registered; perturb 10/20 vs 40/60).
- **Mechanism:** Quality Flow fires on fresh breakouts. A breakout that arrives with accelerating momentum (the move is speeding up, not just drifting) signals urgency — new information or forced positioning — which is what produces follow-through. A breakout with decelerating momentum into the signal is more likely an exhausted push.

### F3 — Dollar-volume expansion (20d ADDV vs 60d ADDV)
- **Construction:** ratio of 20-trading-day average daily dollar volume to 60-trading-day average, strict PIT. Select: ratio > 1.25 (pre-registered; perturb 1.15/1.50 and 20/40 windows).
- **Mechanism:** Breakouts need participation. Rising dollar volume means new money arriving — the fuel a breakout needs to sustain. A breakout on flat or declining dollar volume is a price move nobody is paying for; it should fail more often. This is the "is anyone actually buying this" filter.

### F4 — Volatility expansion (ATR regime)
- **Construction:** 14-day ATR divided by 60-day median ATR, strict PIT on daily bars. Select: ratio > 1.2 (pre-registered; perturb 1.1/1.4).
- **Mechanism:** Breakout systems harvest volatility expansion — the trade IS a bet that realized volatility is increasing. Entering when ATR is already expanding means the market has confirmed the regime the system needs; entering when ATR is compressed means betting on expansion that hasn't started. (Distinct from F3: volume is participation, ATR is price movement — a stock can expand volume without expanding range and vice versa.)

### F5 — Sector leadership (sector ETF momentum rank)
- **Construction:** rank the 11 sector ETFs by 20-trading-day return vs SPY (strict PIT, last completed daily bar); select signals whose sector is in the top 3 (pre-registered; perturb top 2/4). Sector mapping: current-pull GICS as in the canonical baseline (no mid-window structural change found).
- **Mechanism:** Stocks don't break out alone — sector rotation provides the bid underneath. A breakout in a leading sector rides institutional sector allocation flows; a breakout in a lagging sector fights its own sector's gravity. This is the participation question asked at the sector level, complementary to lone-wolf (which asked about sector *weakness* as a veto; this asks about sector *strength* as selection).

### F6 — Proximity to 60-day high (price position)
- **Construction:** (current price − 60-trading-day low) / (60-trading-day high − 60-trading-day low), strict PIT on daily closes. Select: position > 0.8, i.e. in the top quintile of its 60-day range (pre-registered; perturb 0.7/0.9 and 40/90-day windows).
- **Mechanism:** The system buys breakouts; the best breakouts come from stocks already near highs (no overhead supply, everyone holding is in profit, no trapped sellers to sell into strength). A "breakout" signal firing while the stock sits mid-range is structurally different — it's a range trade masquerading as a breakout.

### F7 — Earnings/revisions momentum (data-permitting)
- **Construction:** if and only if a PIT-computable earnings series exists in the available data (yfinance earnings dates + estimate revisions). Candidate: positive EPS revision in the last 63 trading days, or price reaction to the most recent earnings (5-day post-earnings drift direction). Pre-register exact construction AFTER data audit, before testing — if no clean PIT source exists, report UNTESTABLE, do not proxy it with price.
- **Mechanism:** Earnings revisions are the fundamental engine under sustained institutional momentum — analysts revising up means the numbers are improving, which is what keeps sponsorship alive after the technical breakout. This is the "is the business actually accelerating" check.

### F8 — Institutional-footprint proxy (up-volume persistence)
- **Construction:** over the trailing 20 trading days, fraction of up-days on above-median volume minus fraction of down-days on above-median volume ("smart-money day balance"), strict PIT. Select: balance > 0.15 (pre-registered; perturb 0.10/0.20 and 20/40-day windows).
- **Mechanism:** Institutions accumulate over days, not minutes — persistent up-days on expanding volume with muted down-days is the footprint of program buying. A breakout preceded by this footprint has a real buyer underneath; a breakout with no such footprint is retail noise or a single headline spike.

## Explicitly NOT in the menu (do-not-retest list stands)

Volume filters (P8 failed), chase filters (P6 failed), gap filters (P9 failed), generic mean reversion, calendar effects, scanner/Pine agreement. F1–F8 are selection factors on the *universe*, not entry filters on the *signal* — different question from the failed entry-filter studies.

## What happens after

Each factor gets PASS/MAYBE/FAIL. Only factors that survive independently may later be considered for combination (with ablation). After all frozen: one 14-overlap number per factor as sanity check only.

*Pre-registered 2026-09-24 by the coordinator, before any factor was computed. No thresholds were set from data.*
