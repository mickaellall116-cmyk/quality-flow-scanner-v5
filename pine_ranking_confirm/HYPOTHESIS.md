# ADX ranking — confirmatory study (HYPOTHESIS, frozen 2026-09-25 BEFORE running)

## Hypothesis
When portfolio slots are scarce (crowded signal bars), ranking contenders by
ADX(14) — the signal with the strongest established trend — selects better
trades than the adopted rs_top2 rule, consistently across years.

## Mechanism
A breakout is a bet that demand overwhelms supply. When slots are limited,
prefer the setup whose trend is already most established (highest ADX):
stronger trends at entry continue more often than the highest 20-bar-return
names, which on this concentrated momentum watchlist tend to be late/extended.

## Baseline / variants (frozen)
Same signal population as P2: 14-stock watchlist, 4H, 2023-10-25 → 2026-09-23,
canonical `pb.gen_pine_trades` (frozen Mode B), $10k / 1% risk / max 5
concurrent / 5% heat, next-bar-open, 25bps primary. Ranking engages ONLY at
contested timestamps (candidates > free slots): rank by score, take top
min(2, free). All features point-in-time at the signal bar. `pine_backtest`
imported unmodified.

1. `takeall` — no ranking (arrival order), cap 2 at contested bars. The
   relevant counterfactual: ranking must beat doing nothing.
2. `rs_spy` (CONTROL, adopted rule) — 20-bar return minus SPY, top 2.
3. `adx` — ADX(14) at signal bar, top 2. Identical definition to P2.
4. `C_rs_adx` — PREDECLARED combination, ONE formulation, no tuning: mean
   cross-sectional percentile rank of (rs_spy, adx) among contenders, top 2.
   Run regardless (pre-declared, not winner-picked), but EVALUATED/PROMOTED
   ONLY if BOTH adx and rs_spy independently beat take-all on expectancy in
   this test. Per mandate: do not combine weak discoveries.

## Robustness (secondary, frozen)
- `adx10`, `adx20` — same ranking with ADX(10)/ADX(20). Directional check:
  does the edge survive nearby ADX periods, or is 14 an accident?

## Analyses (frozen)
- Main table @25bps: expectancy R, win%, PF, max DD, total return; cost
  stress @50/100bps for finalists.
- Opportunity cost: expectancy of ranked-out trades (taken by takeall but not
  by variant) and swapped-in trades.
- Symbol concentration: selected vs rejected trades per symbol per variant.
- Year-by-year breakdown per variant.
- Crowded-bars-only: timestamps with >=3 candidates (ranking cap binds at 2).
  Per-variant expectancy of trades taken at those bars; differential picks
  (ADX took but RS didn't, and vice versa).
- Walk-forward (period consistency; no parameters are fit): train =
  signal_time <= 2024-12-31, test = signal_time >= 2025-01-01. Full sim per
  variant per period; expectancy is the primary read.

## Win gate (frozen)
ADX earns MAYBE-or-better only if ALL hold:
(a) beats takeall on expectancy by a material margin (>= +0.03R);
(b) beats or matches takeall out-of-sample (2025+);
(c) not a single-year artifact (positive delta vs control in >= 2 of 3 years);
(d) not concentrated in 2-3 symbols;
(e) survives nearby ADX periods directionally;
(f) does not worsen max DD materially vs takeall.
FAIL if the edge is a 2025 artifact (negative/flat delta in 2024 and 2026).

## Main question
When portfolio slots are limited, does ADX select better trades consistently?
Verdict: PASS / MAYBE / FAIL.
