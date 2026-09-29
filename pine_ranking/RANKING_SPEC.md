# RANKING_SPEC.md — Cross-sectional ranking study on Pine V3.6

**Status: FROZEN before any testing. Written 2026-09-18.**

## Question
V3.6 entries and exits stay completely unchanged. When several valid V3.6
signals fire at once, does RANKING them and taking only the top-N beat
taking everything?

This is RANKING information, not new hard filters. Every signal remains a
valid V3.6 signal; ranking only decides selection order when slots are scarce.

## What is NOT being tested
- No entry changes, no exit changes, no parameter retuning.
- No new filters (nothing that deletes a signal unconditionally).
- Pine V3.6 only, 4H only, UX51 universe, no shorts, no hedges, no 1H/Daily.
- No parameter fishing, no combinatorial search beyond what is pre-registered below.

## Portfolio / cost conventions (identical to all prior studies)
- $10,000 start, 1% risk per trade, max 5 concurrent positions,
  5% max portfolio risk, next-bar-open entries, stop-first on ambiguity.
- Costs: 4bps and 25bps legs. Research window: UX51 4H 2024-09-16 → 2026-09-14.
- Control = take-all = V3.6 baseline: 263 trades, +0.195R @4bps (must reproduce).

## Step 0 — Clustering measurement (descriptive, allowed before scheme comparison)
Generate all candidate V3.6 trades (identical per-symbol engine to the control).
Then measure:
1. `skipped_cap_count` in the take-all portfolio sim (entry events dropped by the 5-position cap).
2. Distribution of contested entry timestamps: # timestamps where candidate
   entries > free slots, and the histogram of (candidates, free slots).
3. How many of the 263 control trades were affected by any cap skip.

**Pre-registered early-stop:** if contested timestamps are ~zero (fewer than 5
in the whole window) the study concludes "ranking is moot — signals rarely
cluster" and no scheme comparison is run. That is a valid finding.

## Ranking schemes (maximum 3, exactly defined, point-in-time only)

All features use only information available at the signal bar (bar i).
Ties broken deterministically by original candidate order (UNIVERSE_X symbol
order, then entry time) — Amendment A: the spec originally said "symbol name",
but exact reproduction of the pb.simulate_portfolio event order (required for
the fidelity check) needs the candidate-list order. Deterministic either way;
continuous scores tie only on missing data (-inf).

- **R1 "rs" — cross-sectional relative strength.**
  score = (Close[i]/Close[i-20] − 1) − SPY_ret,
  where SPY_ret is the SPY return over the symbol's own prior-20-bar calendar
  span, measured on daily closes with last-bar-≤-timestamp (identical machinery
  to the signal-quality study: `load_benchmarks` / `bench_ret`, RS_LOOKBACK=20).
  If SPY_ret is unavailable for a signal, score = −inf (ranked last).

- **R2 "volq" — volume quality.**
  score = Volume[i] / SMA20(Volume)[i] (the same vol_ma used by the V3.6
  volume filter). If vol_ma is NaN/zero, score = −inf.

- **R3 "composite" — mean cross-sectional percentile rank.**
  At each contested entry timestamp, among the contending signals only,
  compute percentile ranks (0..1, average method) of three features:
  (a) rs_spy as in R1, (b) vol_ratio as in R2,
  (c) reward:risk at entry = (tp1 − entry) / (entry − stop).
  score = mean of the three percentile ranks. Higher = better.

No weights were tuned; R3 uses the unweighted mean by pre-registration.

## How ranking acts (the real-world decision, exactly)
- Ranking engages ONLY at contested timestamps: candidate entries at timestamp t
  outnumber free position slots (after processing exits at t, same ordering as
  the control sim: exits kind=0 before entries kind=1).
- At a contested timestamp with k free slots and m > k candidates, take the
  top min(N, k) by score for N ∈ {1, 2, 3}. Uncontested timestamps take all
  candidates (control behavior).
- The same 5%-portfolio-risk cap as the control applies (candidates failing it
  are skipped in rank order).
- 3 schemes × 3 N values = 9 research-window variants, all pre-registered.
  This is the question Mike asked ("top-1 / top-2 / top-3 per ranking scheme
  when signals exceed capacity"), not parameter fishing: no thresholds are
  tuned, no features are selected on results.

## Approximation (documented, applies equally to all variants)
Candidate trades are generated per-symbol with the take-all engine. A candidate
dropped by ranking is gone permanently: the symbol cannot re-take a later
signal it would have taken in reality. This slightly understates ranking
variants' fill rates. Direction of bias is identical for all 9 variants, and
clustering is expected to be rare, so the effect is small.

## Fidelity check
The ranked simulator with a constant score must reproduce the control
(263 trades, +0.195R @4bps) trade-for-trade before any scheme is evaluated.

## Metrics per variant (both cost legs)
trades, win rate, expectancy (R/trade), PF, total return %, max DD %,
avg winner R, avg loser R, TP1 hit rate %, avg hold (bars),
fill rate = trades taken / candidate signals available,
skipped-by-cap count, exit-reason mix.

## Candidate selection (research window → freeze, max 2)
A variant becomes a candidate only if ALL hold @4bps:
1. expectancy ≥ +0.225R (control +0.03R, same materiality gate as the
   signal-quality study),
2. trades ≥ 100 (not a tiny sample),
3. max DD not worse than control + 3pp.
At most 2 candidates, frozen in CANDIDATES_FROZEN.md BEFORE touching 2022.

## 2022 validation
Same protocol as the signal-quality study: signals with signal_time ≥
2022-01-01 only, EOD liquidation at last close, same caches
(v6_short_v2/cache + pine_exit_fix/cache_2022), same ranking features
(daily benchmark caches cover 2021-06 → 2026-09, so the identical
load_benchmarks/bench_ret machinery is reused — no methodology change
between windows).
Adoption bar in 2022: expectancy ≥ (2022 control expectancy − 0.05R),
trades ≥ 20, DD not materially worse than 2022 control.

## Verdict options
- Adopt a ranking rule: report it exactly (scheme + N + engagement rule).
- Or keep take-all. If all variants fail: ranking research is closed and no
  new schemes are invented.
