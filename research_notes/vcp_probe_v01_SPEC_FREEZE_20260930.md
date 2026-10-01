# VCP / Fundamental Momentum Probe v0.1 — FROZEN SPEC

Frozen: 2026-09-30. Hash-locked before the first performance run.
No post-result parameter changes. Any amendment requires a new versioned spec.

## Lane status

Quarantined research lane. Do not modify V5.4, Quality Flow, the forward test,
or any frozen ledger. Promotion into production requires a separate validation
process and Mike's explicit approval.

## Research question (narrow)

Does adding a mechanically defined VCP + fundamental-quality screen improve
forward returns versus ordinary trend/momentum selection?

Excluded from the hypothesis until independently reproduced: "85% win rate",
"2-3x S&P", and all other marketing claims from the source video.

## Phase 1 — selection study, NOT a strategy backtest

Do not invent exits, sizing, or rebalance rules from the video. Freeze the
observable screen and measure what happens afterward.

### Frozen sample window

Monthly observation dates, January 2010 through December 2025 (16 years;
includes the 2020 crash and the 2022 bear market). Frozen; do not extend or
truncate after seeing results.

### Phase 1A — cheap trend skeleton

- Historical U.S. common stocks, including delisted/acquired/bankrupt names.
  Dead tickers must not silently disappear from the sample.
- Point-in-time universe and point-in-time market cap: $2B-$100B **at each
  decision date**. Do not use today's stock universe or today's share counts
  to reconstruct history.
- Price > $10 at observation.
- Monthly observation dates.
- Two preregistered variants:
  1. Close > 150DMA and close > 200DMA.
  2. Variant 1 + the frozen 12-month trend condition.
- Measure forward 3-, 6-, and 12-month total returns (dividends included).
- Report: excess return, hit rate, downside excursion/drawdown after selection,
  breadth (count of qualifying stocks), and turnover.
- Freeze handling for splits/dividends, acquisitions, bankruptcies, and
  delistings before the first run.

### Controls

- Primary control: stocks that fail the trend condition but otherwise meet the
  same PIT universe restrictions on the same date.
- Secondary reference: SPY over the identical forward window.

### Phase 1B — price-only VCP probe

- Before looking at performance, preregister 2-3 mechanical VCP definitions.
  Freeze all parameters first: contraction count, contraction-depth rules,
  higher-low requirement, pivot definition, range/ATR compression, etc.
- Apply VCP only to Phase 1A qualifiers.
- First report trigger counts/base rates. A variant with fewer than 50 total
  triggers is reported as "insufficient base rate" — no inference run.
- Then compare VCP qualifiers with non-VCP Phase 1A qualifiers.
- No parameter tuning after results.

### Persistence / evidence rule (preregistered)

- Positive mean excess return versus the primary control in a majority of the
  frozen non-overlapping 2-year subperiods.
- Positive full-sample excess return.
- Full-sample inference clears a frozen 5% two-sided threshold using
  date-aware/block-bootstrap or equivalent clustered inference, because monthly
  selections and 3/6/12-month outcomes overlap.
- Report effect size and confidence intervals, not just p-values.
- Report all 3/6/12-month horizons; don't cherry-pick whichever works.

### Gate

Do the expensive PIT-fundamentals build only if Phase 1A or a preregistered
Phase 1B VCP variant shows persistent separation per the evidence rule above.
A failed 1A alone does not reject VCP. If both 1A and 1B are dead, park the lane.

## Later layers (only if the gate passes)

trend -> trend + PIT quality fundamentals -> trend + VCP ->
trend + PIT fundamentals + VCP -> optional refiners (insider ownership,
P/E behavior).

For fundamentals: use only data actually available before each decision
timestamp. Document filing/release availability, revisions/restatements, and
employee-count availability. No lookahead. P/E direction tested separately;
rising P/E may be price outrunning earnings, not independent information.

## Provenance

Spec authored from Mike's directives, 2026-09-30, with two review additions
(frozen 2010-2025 sample window; 50-trigger minimum base rate for 1B inference).
Source method: @stockweatherman TikTok ("how to find great stocks to buy,
early"), itself a repackaging of Minervini-style VCP + momentum/quality screening.
