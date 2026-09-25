# Pre-registration: Laggard-Veto Risk-Control Test

Date: 2026-09-24
Authorized by: Mike — Lane 2 narrowed to this single test (2026-09-24 directive).
Status: FROZEN before execution. No changes after results are seen.

## Hypothesis

Stocks in the bottom quartile of trailing relative strength are toxic for V5.4-style
breakout entries (selection study: bottom-quartile RS buckets ran −0.23R to −0.76R
nearly everywhere, while top buckets hovered near zero). Excluding signals on those
names should reduce portfolio drawdown and left-tail risk.

This is a **risk-control** test, not an expectancy-improvement claim. A PASS does not
change V5.4 production — it only qualifies the veto as a candidate for a separate
forward paper overlay, subject to Mike's explicit approval.

## Frozen rule

Veto (exclude) any signal where, at signal time, the stock ranks in the **bottom
quartile** of **RS3 or RS6**, where:

- RS3 = 63-day total return minus SPY total return, strict point-in-time
- RS6 = 126-day total return minus SPY total return, strict point-in-time
- Quartiles are cross-sectional across the test universe, ranked with only data
  available at the signal bar

Veto if bottom-quartile on EITHER factor (union). No tuning of lookbacks, no
threshold search, no exceptions.

## Test universe and population

- Same 131-symbol point-in-time universe as the canonical baseline; the 8
  in-universe old-14 names stay hard-masked (123-symbol working set), exactly as in
  the selection study the observation came from.
- Same trade population and machinery as the canonical baseline: exact Mode B exits,
  strict PIT features, realistic gap-through-stop handling in research, 50 bps
  round-trip costs as the primary cost assumption.
- Same portfolio replay: $75,000, 1% risk per trade, max 6 open positions, ~5% total
  heat, slot competition and capital tied up.
- Internal comparison only: baseline (no veto) vs veto on the identical population.

## Honesty caveat (recorded before running)

The hypothesis was formed on this same dataset (selection_edge/SELECTION.md), so this
test is confirmatory-with-caveats, not independent validation. The real arbiter of
the veto is forward data. Report this caveat alongside any PASS.

## Outcomes

Primary: maximum drawdown (relative reduction, veto vs baseline).
Secondary: pooled expectancy, total portfolio return, trade count, year splits,
dev (Oct 2023–Dec 2024) vs val (Jan 2025–Sep 2026), costs at 25/50/75/100 bps,
concentration (top-1/3/5 trades' share of total R), bootstrap, rolling walk-forward,
left-tail metrics (worst 5% of trades, max losing streak).

## Pre-registered decision rule

PASS as a risk-control candidate iff ALL of:
1. Max drawdown reduced by ≥25% relative to the no-veto baseline;
2. Pooled expectancy not worse than baseline by more than 0.05R;
3. Drawdown improvement also present in the validation window (Jan 2025–Sep 2026)
   alone, not just pooled.

Otherwise: FAIL. A FAIL hardens the conclusion that V5.4's risk profile is what it
is and improvement must come from exits, entries, or a different system.

A PASS qualifies the veto for a separate forward paper overlay decision by Mike. It
does NOT authorize any change to frozen V5.4 production, its entries, exits,
grades, ranking, or alerts.
