# Stale-FVG invalidation backtest — README

**Date:** 2026-09-25. **Idea source:** pre-registered research note
`research_notes/next_idea_2026-09-25.md`.

## Question

The 4H FVG-as-entry toggle fires whenever price sits in a bull fair-value gap,
no matter how old the gap is (the Pine port keeps `lastBullFvgLow/High`
persisting until the *next* bull FVG forms). Does the FVG edge live only in
*fresh* gaps? If stale gaps are noise, an age filter (gap formed ≤ 10 bars ago)
should raise the sidecar's expectancy.

## Method

- Universe: 14-stock watchlist (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM,
  SPCX, ASTX, BBAI, NIO, HOOD, AMD), 4H session bars, Oct 25 2023 → Sep 23 2026,
  same 1H-derived cache as the entry-timing study.
- `pine_backtest.py` imported UNMODIFIED; only `pb.pine_buy_signal`
  monkey-patched per variant. FVG port copied from
  `pine_entry_timing_backtest/run_entry_timing.py` + one field: `fvg_age`
  (bars since the currently-active lastBullFvg formed; NaN when none active).
  Same activation semantics as the entry-timing port.
- Variants (identical Mode B exits via `gen_pine_trades`, next-bar-open fills,
  4bps + 25bps costs, $10k / 1%-per-trade / max-5 / 5%-risk portfolio sim):
  - **BASE** — all-off canonical Hybrid, rerun in-study.
  - **FVG-ALL** — canonical OR fvg sub-signal (current sidecar behavior, rerun).
  - **FVG-FRESH** — canonical OR (fvg AND fvg_age ≤ 10). Pre-registered K=10.
  - FVG-FRESH5 / FVG-FRESH20 — secondary context only, not decision criteria.
- Attribution: FVG-ALL trades split by sub-signal state at their signal bar —
  fresh (≤10) vs stale (>10) buckets; age buckets 0–10 / 11–20 / 21–40 / 41+.
- Success gate: FVG-FRESH beats FVG-ALL by >0.02R at 25bps AND clears +0.15R.

## Results (25bps)

| Variant      | Trades | Win rate | Expectancy | PF   | Max DD  |
|--------------|-------:|---------:|-----------:|-----:|--------:|
| BASE         | 237    | 50.6%    | **+0.239R**| 1.38 | 21.63%  |
| FVG-ALL      | 266    | 50.4%    | **+0.285R**| 1.48 | 28.08%  |
| FVG-FRESH    | 266    | 50.0%    | **+0.279R**| 1.46 | 29.17%  |
| FVG-FRESH5   | 265    | 49.8%    | +0.274R    | 1.45 | 29.17%  |
| FVG-FRESH20  | 266    | 50.4%    | +0.285R    | 1.48 | 28.08%  |

Both reruns match expectations (BASE ≈ +0.239R, FVG-ALL ≈ +0.285R).
FVG-FRESH trails FVG-ALL by 0.006R — gate failed.

## Attribution (25bps), FVG-ALL trades

- FVG-entry trades (sub-signal fired at signal bar): n=191, win 49.2%,
  exp **+0.271R**.
- Marginal trades (fvg fired, canonical did not): n=60, win 46.7%,
  exp **+0.433R** — the marginals carry the FVG edge. 96.7% of them are fresh.
- Fresh (age ≤10): n=182, exp +0.273R. Stale (age >10): n=9, exp +0.232R.
- Age buckets: 0–10 → n=182, +0.273R · 11–20 → n=9, +0.232R ·
  21–40 → n=0 · 41+ → n=0.
- Signal-level diagnostic: 915 fresh vs 41 stale FVG sub-signal bars across
  3 years × 14 names (stale share 4.3%); only **10 bars** were stale-fvg-only
  signals the filter would actually drop.

Note: the brief estimated "29 marginal trades"; both this study and the
earlier entry-timing study count 60 trades whose signal bar fired fvg without
canonical. The 29 figure appears to have been a miscount — the mechanism
conclusion is unaffected either way.

## Why the filter does nothing (mechanism)

The Pine FVG sub-signal already requires |close − fvgHigh| ≤ 3·ATR — price
must be *near* the gap. Old gaps drift away from price and almost never fire:
zero trades above age 20, nine between 11–20, and only ten signal bars in the
entire sample that the age filter would have dropped. The price-proximity
condition self-filters stale gaps in price space, so an age filter in time
space is redundant. FVG-FRESH20 is bit-identical to FVG-ALL for the same
reason. The −0.006R tilt is portfolio-sim noise on a near-identical trade set,
not an effect.

## Verdict

**Clean kill — no age filter.** The stale-FVG hypothesis is falsified by
redundancy, not by bad stale-gap performance: stale gaps essentially never
reach the entry gate, so there is nothing to cut. The sidecar needs no change;
the FVG-ALL behavior stands as-is. This joins the tested-and-parked list.
A genuinely different refinement would need a different mechanism (e.g. gap
*size* or revisit-count filters), not age.

## Files

- `run_stalefvg.py` — study script (imports `pine_backtest` unmodified)
- `stalefvg_results.json` — pooled + per-ticker results, attribution, age buckets
- `README.md` — this file
