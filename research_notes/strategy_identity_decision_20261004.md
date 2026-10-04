# Quality Flow Strategy Identity — Decision Brief
**Status:** DECISION REQUIRED (2026-10-04). No experiment chosen. No performance run.
**Reproduction reference preserved:** `pine_backtest.py` (`447a9a13bb2ec7ab…`) — untouched.

## The situation

Three lineages exist. They are materially different systems. The TOP-vs-BROAD experiment answers a different question under each.

### Lineage A — `pine_backtest.py` (as-studied)
- Produced the corrected C1: 240 trades, +0.178R @4bps.
- Exits: **close-evaluated** stops → next-bar open; TP1 50% intrabar; trail-after-TP1; ema55-break/bear → next-bar open.
- No 30-bar hold. No Profit Protect. No scanner EXIT. No ranking (chronological). Sizing: risk_pct × equity.
- **Experiment it supports:** "Does TOP-50 beat BROAD-225 under the as-studied research system?" — directly comparable to the corrected C1 baseline.
- **Limitation:** this is NOT what the forward test trades.

### Lineage B — `v54_exit_tracker.ModeBTracker` (as-traded)
- What the paper forward test actually runs.
- Exits: **intrabar** stops (stop wins ties); TP1 50%; **Profit Protect** (+1R arming gates scanner EXIT); **30-bar max hold**.
- **Experiment it supports:** "Does TOP-50 beat BROAD-225 under the as-traded system?" — comparable to paper forward-test behavior.
- **Limitation:** no backtest baseline exists for B; the corrected C1 numbers do not apply.

### Lineage C — REV6 spec A3/A4 (as-specified, unimplemented)
- The canonical reconstruction spec: rs_top2 ranking, $750 planned risk, busy/pending, 5 slots, 5% heat.
- **Status:** specified, never implemented in any backtest. Would require new code + its own fixtures before any experiment.
- **Experiment it supports:** "Does TOP-50 beat BROAD-225 under the specified REV6 stack?"
- **Limitation:** no baseline at all; new implementation risk.

## What each choice changes

| | A (as-studied) | B (as-traded) | C (as-specified) |
|---|---|---|---|
| Baseline exists | Yes (corrected C1) | No | No |
| Matches forward test | No | Yes | No |
| New code needed | No | Harness only | Yes (A3/A4) |
| Experiment question | Universe effect, studied system | Universe effect, traded system | Universe effect, spec system |

## Builder's notes (not a recommendation)

- The v3 proposal's §3.2 ("corrected REV6 portfolio stack") conflated A and C. That language is withdrawn.
- The 16 synthetic fixtures test Lineage A's routines. They are **builder-tested** pending independent inspection/execution.
- Whichever lineage is chosen, the TOP-vs-BROAD comparison itself is unchanged (same universe split, same gates, same bootstrap). Only the strategy being compared changes.
- Lineage A is preserved as the reproduction reference regardless of the experiment choice.

## Decision needed

Mike (with ChatGPT's review) chooses: **A, B, or C** — or parks the experiment. The data inventory continues independently; data readiness and strategy choice are separate gates, and both must pass before any performance-run approval.
