# Universe Selection Edge — Final Verdict

**Date:** 2026-09-25
**Question:** Can we define a SIMPLE, POINT-IN-TIME stock-selection rule that identifies
stocks where Quality Flow has positive expectancy, without future knowledge or
reverse-engineering the old 14-name watchlist?
**Answer: NO. No legitimate selection edge found.**

Twelve factors tested independently under the frozen spec. Eleven FAIL outright.
The twelfth (RS6, a MAYBE) was killed by the pre-registered placebo: its top-quartile
"+0.044R" is exactly what random bucketing produces (P(random ≥ real) = 0.43).
Per Mike's spec, "no factor survives" is an acceptable result — and it is the result.

Nothing in production changes. V5.4 stays frozen. No V5.5. No new filters.

---

## Scoreboard

| # | Factor | Construction | Verdict | One-line reason |
|---|--------|--------------|---------|-----------------|
| F1a | RS3: 63d return − SPY | cross-sectional quartile, strict PIT | **FAIL** | Top bucket −0.06R; worst bucket in dev; ordering flips across windows |
| F1b | RS6: 126d return − SPY | same | **MAYBE → FAIL** | Monotonic everywhere, but top bucket +0.044R = placebo noise (see §2) |
| F5 | SECTOR_RS: 63d sector-ETF − SPY | same | **FAIL** | Wrong-signed: breakouts in *leading* sectors do *worse*, every cut |
| — | HI52: distance from 252d high | same | **FAIL** | No signal either direction; orderings flip |
| FAM2 | Trend persistence (% days > 50d EMA) | same | **FAIL** | Middle bucket best; dev/val point opposite ways |
| FAM3 | ATR-normalized 126d momentum | same | **FAIL** | Not monotonic; validation wrong-signed; year flips |
| FAM5 | 63d realized-vol percentile | same | **FAIL** | Headline points the *wrong* way; expensive to compute |
| FAM6 | 63d dollar-volume trend | same | **FAIL** | Monotonic headline but dev says opposite; entire top bucket = 2 stocks (SNDK, ARM); doesn't clear zero |
| F7-REV | Analyst rating revisions (up−down, 63d) | same | **FAIL** | *Inverted* monotonicity: most-upgraded bucket −0.135R, most-downgraded +0.480R |
| — | Revenue/EPS growth | — | **UNTESTABLE** | yfinance quarterly history ~42% coverage + restatement leakage; fails 70% gate |
| — | EPS estimate revisions | — | **UNTESTABLE** | No timestamped revision history available without paid API |

Full protocol per factor (except UNTESTABLE): per-bucket n/expectancy/PF/win-rate/maxDD,
cost ladder 25/50/75/100bps round-trip, dev Oct23–Dec24 / val Jan25–Sep26, year splits,
rolling 12mo/6mo walk-forward, window perturbations, concentration (drop top 1/3/5),
≥5,000 bootstrap, leave-one-symbol-out, absolute top-clears-zero check.
All factor definitions pre-registered before any computation.

## The RS6 MAYBE and why it died (placebo)

RS6 was the only factor with consistent top>middle>bottom ordering across full/dev/val,
all years, all cost levels, all 79 LOSO deltas. But the top bucket earned only +0.044R/trade
(95% CI −0.23 to +0.35, includes zero), died above 50bps costs, and was carried by 3 outsized
trades (drop top-3 → −0.15R).

Phase 6 placebo (exactly as specified): within each signal date, randomly permute the RS6
rank values across the 123-name working set, re-bucket into quartiles, recompute top-bucket
expectancy. 5,000 repetitions, exact replication of worker B's construction verified
byte-for-byte (n=145, mean +0.0441R matched).

- Real RS6 top bucket: **+0.0441R** (n=145)
- Random bucketing: mean **+0.0360R**, sd 0.051, 90% interval [−0.048, +0.121]
- Real sits at the **56.8th percentile** of random; **P(random ≥ real) = 0.43**

A coin flip. The monotonic ordering is a ranking artifact on noise, not selection skill.
**RS6: FAIL. No combinations triggered** (spec requires independently surviving factors;
none exist).

## Selector validity (A/B/C) — RS6, the best candidate

| Group | Definition | Expectancy @50bps | n |
|-------|-----------|-------------------|---|
| A — all working stocks | full 123-name universe | −0.033R | 352 |
| B — selector-approved | RS6 top quartile | +0.044R | 145 |
| C — selector-rejected | RS6 middle+bottom | −0.087R | 207 |

B > C holds, but B is placebo-indistinguishable from random and doesn't clear zero.
There is no approved subset worth trading.

## Anti-hindsight (Phase 8)

- The 14 names (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX, ASTX, BBAI, NIO,
  HOOD, AMD) were **masked from all factor construction, ranking, and evaluation**.
  21 canonical trades on masked names excluded; all workers verified zero masked symbols
  in any factor record.
- Correction discovered during the work: only **8 of the 14** were ever in the 131-name
  PIT universe (ASTX, BBAI, HOOD, ONDS, RKLB, SOFI never made it). Working set = 123.
- **14-overlap for RS6's top bucket: 0.0%** (0 of 145 top-bucket trades; base rate 5.6%).
  The selector does not rediscover the 14.
- "Excluding all 14" is satisfied by construction — every number in this file is computed
  on the masked universe.
- "Never-before-used names": all 123 working names were unseen by the selector at
  construction; no watchlist targeting occurred.

## Why Phases 4 and 9 did not run

- **Phase 4 (combinations):** spec allows 2-factor combos only after at least two factors
  independently survive. Zero survived. No combos were built.
- **Phase 9 (portfolio replay):** spec replays the best *surviving* selector. None survived;
  replaying a placebo-killed MAYBE would be theater, not evidence.

## Mechanism read

The honest interpretation of twelve nulls: V5.4's ~0R expectancy is not a universe
problem hiding a selection solution — it is the system's expectancy, full stop. The
cross-cutting pattern across factors is that **laggard buckets are toxic**
(bottom-quartile RS buckets run −0.23 to −0.76R nearly everywhere) while **top buckets
hover near zero** — strength ranking avoids losers slightly better than chance but
cannot isolate a profitable subset. That asymmetry is consistent with a breakout system
whose entries fire into moves that have already happened: the worst laggards keep
lagging, but "strong" breakouts have no follow-through edge left to harvest.

Two observations filed for the record, not adopted:
1. Analyst *downgrades* bucket ran +0.480R (n=61, concentrated in OXY/VLO/MU) — the
   inverse of F7-REV. Adopting it would be unregistered data mining.
2. FAM6's volume-trend monotonicity was entirely SNDK + ARM. Another reminder that
   353 trades cannot support stock-level stories.

## PASS/FAIL: FAIL

No factor meets the bar: positive 50bps expectancy that survives OOS, nearby-lookback
robustness, breadth, placebo, and the excluding-14 check. The clearest monotonic
improver (RS6) fails the placebo. **There is no legitimate selection edge.**

## Recommended next experiment

Stop hunting cross-sectional stock selectors on this trade population. The next
experiment worth running is the one the data keeps pointing at: the **laggard veto**
(bottom-quartile RS exclusion) as a *risk* control, not a profit engine — pre-register
"exclude bottom-quartile RS3/RS6 signals" and test whether it reduces maxDD and left-tail
R without claiming expectancy gains. If that fails too, the conclusion hardens:
V5.4's expectancy is what it is, and improvement must come from exits, entries, or
a different system — not from picking which stocks to take.

## Artifacts

- `selection_edge/phase1_profile/` — per-stock profiling (REPORT.md, PROFILE.json, run_phase1.py)
- `selection_edge/phase2_strength/` — RS3/RS6/SECTOR_RS/HI52 (REPORT.md, *.json, phase2_strength.py)
- `selection_edge/phase2_other/` — FAM2/3/5/6 (REPORT.md, *.json, compute/analyze scripts)
- `selection_edge/phase2_fundamentals/` — data audit + F7-REV (DATA_AUDIT.md, REPORT.md, FACTOR.json)
- `selection_edge/placebo_rs6.json` — 5,000-rep placebo + 14-overlap numbers
- `selection_edge/FACTOR_MENU.md` — pre-registration (superseded by Mike's exact spec where different)
- `/tmp/placebo_rs6v3.py` — placebo replication script (exact worker-B construction via simlib)
