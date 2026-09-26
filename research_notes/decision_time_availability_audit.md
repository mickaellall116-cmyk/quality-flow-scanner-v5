# Decision-Time Availability Audit — preregistration

Status: GOVERNANCE / FAILURE-MODE TEST ONLY. No production change.
Date: 2026-09-25
Scope: future candidate architectures and portfolio replays. V5.4 remains frozen. ERD v0.1 remains frozen/lab-only.

## Hypothesis
A backtest can show false cross-sectional selection skill if a feature used to rank or gate symbols is computed from information whose `available_at` timestamp is later than the portfolio decision timestamp, even when the feature is historically dated correctly.

## Frozen rule
Every candidate feature consumed at a decision must carry:
- `event_at`: when the underlying economic/market event occurred;
- `available_at`: earliest timestamp the exact value was observable to the strategy;
- `decision_at`: timestamp of the portfolio decision;
- provenance/source/version.

Eligibility is mechanical: `available_at <= decision_at`. Otherwise the feature is LATE and must be rejected for that decision. No backfill, nearest-value substitution, same-day assumption, or use of revised values.

For cross-sectional ranks, the rank universe at `decision_at` contains only symbols whose required feature values individually satisfy the rule. Missing/LATE values remain unavailable; they are not imputed from future observations. Universe membership itself must also be point-in-time eligible.

## Audit
For each serious candidate before performance interpretation:
1. Produce an availability ledger for every feature/symbol/decision consumed.
2. Assert zero accepted rows with `available_at > decision_at`.
3. Re-run with each non-price feature shifted one publication interval later. A candidate that improves or is unchanged suspiciously under a shift receives REVIEW, not PASS, until explained.
4. Remove all rows whose availability timestamp is inferred rather than vendor-recorded and report sensitivity.
5. Portfolio replay is mandatory under identical ranking, sector-cap, slot, risk, cost, and execution rules; record displaced trades.
6. Report coverage loss caused by availability enforcement and by PIT universe enforcement.
7. Keep the test in the candidate's existing `family_id`; this audit does not create a fresh family or reset multiple-testing history.

## Decision rule
FAIL the implementation if any accepted decision uses a LATE feature, a revised value unavailable at decision time, or non-PIT universe membership.

REVIEW/MAYBE if timing is valid but inferred timestamps or coverage loss are large enough that the economic result depends materially on them.

PASS the availability audit only if timing assertions are clean and the candidate's claimed portfolio result survives the availability-enforced replay. Passing this audit is necessary, not sufficient, for candidate PASS.

## Placebo / anti-leakage control
The shifted-availability replay is a leakage diagnostic, not an alternate model and cannot be selected because it performs better. Any performance from deliberately late features is evidence for investigation, never evidence for the candidate.

## Explicit exclusions
This does not modify V5.4, ERD v0.1, their frozen logic, or any killed branch. It does not authorize stale-FVG, laggard-veto, lone-wolf RS, universe-factor mining, N-wave targets, or any other closed family.
