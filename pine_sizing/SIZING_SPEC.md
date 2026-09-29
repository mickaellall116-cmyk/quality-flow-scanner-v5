# POSITION SIZING STUDY — pre-registered spec (frozen before any runs)

Status: SPEC FROZEN. No test has been run against this spec.

## Question

Does any position-sizing rule beat fixed 1% risk/trade on risk-adjusted terms
for Pine V3.6, without degrading the 2022 bear window?

RESEARCH ONLY. Nothing here is implemented anywhere. Mike has no sizing rules
live; whatever this study finds, no live sizing change is authorized. Output is
a recommendation, not an implementation.

## What is frozen

- V3.6 entries and exits byte-identical (reused from the MFE/MAE engine copy;
  fidelity check: 263 trades, expectancy +0.195R at 4bps, exactly the baseline).
- Universe: UX51, 4H, 2024-09-16 → 2026-09-14.
- Portfolio plumbing: $10k start, max 5 concurrent positions, max 5% portfolio
  risk gate, next-bar-open entries/exits, marked-to-market equity, 4bps primary
  leg (25bps confirmation leg for frozen candidates only).
- Trades themselves are IDENTICAL across schemes (same 263 trades, same entry/
  exit times). The ONLY thing that varies is $ risk per trade.

## Schemes (exactly 5, no more)

- **S0 (control): fixed 1.00%** risk per trade.
- **S1: fixed 0.50%** risk per trade.
- **S2: fixed 0.75%** risk per trade.
- **S3: fixed 1.25%** risk per trade.
- **S4 (adaptive, drawdown-gated):** base risk 1.00%. At each entry, if marked
  equity <= 90% of running peak marked equity, risk is halved to 0.50% for
  that trade. Full 1.00% risk is restored once marked equity >= 95% of the
  running peak (hysteresis, avoids gate flicker). The 5% portfolio-risk gate
  still applies, using the scheme's current per-trade risk_pct.

Why drawdown-gated and not volatility-adjusted: per-trade position size is
already risk_frac = (entry - stop)/entry, so symbol-level ATR differences are
already neutralized in $ terms. A market-volatility-regime rule would be regime
research, out of scope. No Kelly, no martingale, no scheme that increases risk
after losses.

## Metrics (per scheme)

R-space (size-invariant — reported to verify the invariance sanity check):
- n, expectancy R/trade, total R, win rate, PF (must be identical across
  schemes; any deviation is a bug).

Portfolio-space (event engine, exact, with concurrency caps + marked DD):
- terminal return %, max drawdown % (marked-to-market)
- max DD in units of 1%-risk R: DD_R = maxDD% / 0.01 (documented; for adaptive
  this is "R of base risk")
- Calmar = total_return% / maxDD%
- longest losing streak: in trades (consecutive net_r <= 0) and in % (worst
  peak-to-trough on the marked curve)
- trades skipped by the 5-position cap and by the 5% risk cap (cap behavior
  differs by size; reported)

Bootstrap (10,000 paths, seed 20260918, R-space resampling of the trade net_r
list, sequential compounding at each scheme's risk rule — for S4 the DD-gate
rule is applied along each resampled path):
- P(maxDD > 20%), P(ruin: equity ever <= 50% of start)
- median / p75 / p95 maxDD%
- Documented approximation: same sequential-compounding model as the Monte
  Carlo study; ignores the concurrency-cap drag. All scheme comparisons are
  made within this one accounting — never mixed with event-engine numbers.

Accounting note (from the Monte Carlo study): on identical trades, sequential
compounding gave +52.0% vs the event engine's +35.3% — that gap is the
concurrency-cap drag. Event-engine numbers and bootstrap numbers are reported
separately and labeled.

## 2022 validation

After the research window, freeze MAXIMUM 2 schemes in CANDIDATES_FROZEN.md
BEFORE touching 2022 data. 2022 framework: same caches and rules as the
MFE/MAE study (2022-01-01 cutoff, end-of-data liquidation; ~30 trades).
Frozen candidates are re-run on 2022 at both cost legs.

## Adoption bar (all must hold)

1. Better risk-adjusted than S0 in the bull window: lower maxDD% and/or higher
   Calmar at comparable-or-better terminal return.
2. Does not degrade 2022 vs control (no materially worse DD or return).
3. Improvement is not a small-sample artifact (bootstrap P(>20% DD) and ruin
   must agree with the point estimates' direction).

If no scheme passes: "fixed 1% remains the default" and sizing research closes.

## Sanity check (pre-registered)

Expectancy R/trade must be numerically identical across all five schemes
(sizing is pure $ scaling; R-space cannot change). Verified before any
conclusion is drawn.
