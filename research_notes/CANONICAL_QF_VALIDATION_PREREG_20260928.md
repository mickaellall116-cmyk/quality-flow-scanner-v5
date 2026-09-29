# Canonical Quality Flow Validation — Preregistration (2026-09-28)

Research-only. Frozen/live Quality Flow remains unchanged until this protocol is completed.

## Why this supersedes indicator research
Recent 30-symbol work found:
- HEMA hard gating, retest logic, ranking and runner-exit modifications did not add robust incremental edge.
- Raw QF 4H entry timing showed only suggestive 10-bar excess versus symbol/month-matched random bars.
- The unconstrained surrogate portfolio was distorted by pathological position sizes from very tight stops.
- A 1% minimum stop removed the worst single-position leverage and sharply reduced drawdown, but the remaining edge was still concentrated in the best trades.
- Total gross portfolio exposure can still exceed equity even when each individual position is capped.

The next research priority is therefore to validate **Quality Flow itself** on the frozen 131-symbol point-in-time universe under executable portfolio constraints.

## Phase 0 — exact frozen reproduction
Before adding any risk constraint, regenerate the published canonical V5.4 baseline exactly:
- PIT 131-symbol universe and listing-admission rules;
- frozen V5.4 entry logic;
- next-4H-open entry;
- Mode B exits;
- max 6 open;
- 5% heat cap;
- rs_top2 slot ranking;
- 25/50/75/100 bps;
- both documented stop-fill conventions, including realistic gap-through fills.

Phase 0 reconciles against the frozen multi-invariant comparator in `CANONICAL_RECONSTRUCTION_FROZEN_RULES_20260928_REV6_1.md` (§5 pre-run, §6 post-run). Exact trade-by-trade reconciliation is required only if an original trade ledger becomes available. The rebuild result is labeled a reconstructed canonical replica from an unblinded replication, not a recovered original. This reconciliation is required before any amended test is interpreted.

## Phase 1 — executable-risk amendment
Primary risk-control scenario, fixed before seeing the rerun:
- **minimum actual fill-to-structural-stop distance: 1.00%**;
- **maximum single-position notional: 100% of current marked equity**;
- **maximum total gross portfolio notional: 100% of current marked equity**;
- do not widen the structural stop to make a trade qualify;
- position size = min(risk-budget shares, single-position cap shares, remaining-total-exposure shares);
- use actual resulting dollars-at-risk for heat;
- reserve both risk and notional for pending next-bar entries so same-timestamp candidates cannot collectively exceed limits.

Sensitivity only, not winner-selection:
- total gross exposure cap 150%;
- total gross exposure cap 200%;
- minimum stop 2.00% with 100% gross exposure cap.

No threshold may be selected solely because it backtests best.

## Ranking-data hygiene
- Missing rs_top2 must be represented explicitly as null/unrankable, not a numeric -999 score.
- Unrankable signals sort last.
- Every accepted trade must log rankability, raw rs_top2, candidates at that decision, free slots, remaining risk heat and remaining gross-notional capacity.

## Required trade record
Each trade must include:
- symbol and PIT eligibility metadata;
- signal timestamp and decision timestamp;
- entry timestamp/price;
- structural stop and TP1;
- stop-distance percent at actual fill;
- shares;
- entry notional;
- marked equity at entry;
- position notional/equity;
- total gross exposure/equity immediately before and after entry;
- planned dollars-at-risk and heat;
- ranking inputs;
- all partial/full exit legs;
- gross R, net R and net P&L;
- costs and gap/slippage fields.

## Required analysis
At 25/50/75/100 bps:
- n, total R, expectancy, PF, win rate;
- marked return and max drawdown;
- year splits;
- top-1/3/5/10 removal;
- best-year removal;
- symbol/sector concentration;
- overlap-episode effective sample;
- entry-timing event study against symbol/month-matched random bars on the full PIT universe;
- realistic-gap versus stop-price fills;
- rejected counts for min-stop, single-position cap, total-exposure cap, slot pressure and heat.

Primary focus is the 50-bps, realistic-gap, 100%-gross-exposure scenario.

## Interpretation standard
Quality Flow should not be described as having a robust tradable edge unless the canonical rerun:
- stays positive after realistic costs and gap handling;
- does not depend on a few extreme trades or a short partial period;
- has acceptable drawdown under executable exposure constraints;
- shows reasonably consistent performance across years;
- and shows entry timing that improves on matched controls on the broad PIT universe.

A failure is an acceptable research outcome and means the frozen system needs re-evaluation rather than more indicator layering.

## Missing inputs
The repository documents the canonical baseline, but the referenced executable artifacts and data are currently absent from main:
- canonical_baseline/portfolio_results.json
- canonical_baseline/canonical_trades.json
- canonical_baseline/simlib.py
- canonical_baseline/run_portfolio.py
- canonical_baseline/universe.json
- raw 131-symbol 4H/daily PIT cache and SPY data

These must be recovered or regenerated before Phase 0 can be executed.
