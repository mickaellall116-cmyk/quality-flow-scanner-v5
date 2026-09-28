# Claude Independent Audit Request — Canonical Reconstruction Plan
**Date:** 2026-09-28
**Status:** PRE-BUILD AUDIT ONLY — no reconstruction authorized
**Owner:** Mike
**Purpose:** Independently determine whether the surviving canonical documents specify the old canonical environment tightly enough to rebuild it without silently inventing mechanics.

## Source documents
Audit these six files only as the canonical specification set:
- `canonical_baseline/ENGINE.md`
- `canonical_baseline/LONEWOLF_RERUN.md`
- `canonical_baseline/PIT_FEATURES.md`
- `canonical_baseline/PORTFOLIO.md`
- `canonical_baseline/REBASELINE.md`
- `canonical_baseline/UNIVERSE.md`

The original executable/cache artifacts were never committed anywhere in Git. Muse checked branches, tags, history, and stashes. Do not assume any missing implementation detail.

## Important historical context
- The published canonical V5 @50bps headline was approximately:
  - expectancy -0.0013R/trade
  - 374 trades
  - win 39.8%
  - PF 1.00
  - max DD ~39.8%
  - total return ~-0.9%
- Those numbers are an **expected-results oracle**, not proof that a rebuilt implementation is correct.
- The earlier 143-trade C1 result is selected-sample engineering evidence only, not canonical proof.
- Pine's 0-5 trendScore was correct; a numpy boolean-addition bug existed in an old Python mirror. Do not propagate that bug into any reconstruction.
- Live/frozen V5.4 remains untouched.
- A separate validation prereg already exists at:
  `research_notes/CANONICAL_QF_VALIDATION_PREREG_20260928.md`
  It must not be silently altered by this reconstruction exercise.

## Questions to answer

### 1) Rebuild dependency order
Propose the safest reconstruction order among:
- point-in-time universe and `universe.json`
- daily / 4H PIT cache
- shared simulation library (`simlib.py`)
- portfolio runner (`run_portfolio.py`)
- output artifacts (`portfolio_results.json`, `canonical_trades.json`)

For each stage, identify what inputs it depends on and what must be validated before moving to the next stage.

### 2) Spec completeness map
For every material rule, classify it as:
- **EXPLICITLY PINNED** by the six docs;
- **DERIVABLE** from an explicit rule with no meaningful discretion;
- **AMBIGUOUS / JUDGMENT REQUIRED**;
- **MISSING / NOT RECONSTRUCTABLE** from the docs alone.

At minimum inspect:
- universe candidate pool, ranking window, exclusions, listing gates, delisting handling;
- 4H session anchoring, early closes, missing bars, timezone;
- PIT daily-bar availability and RS endpoints;
- signal timing and next-bar-open entry timing;
- entry invalidation conditions;
- ranking / rs_top2 tie behavior;
- busy-symbol logic;
- slot limit;
- heat calculation;
- risk sizing;
- cost model and leg allocation;
- Mode B stop/TP1/PP/runner/timeout precedence;
- same-bar conflicts;
- gap handling;
- equity marking / max-DD construction;
- open positions at sample end;
- missing RS / missing data handling;
- ordering/determinism when several candidates compete on one bar.

### 3) Oracle design
The two JSONs are outputs, not source inputs.

State whether the correct procedure is:
A. rebuild inputs + engine, run once, then compare generated outputs to the published canonical expected-results record; or
B. attempt to recreate those JSONs directly.

Explain why.

Define a minimum reproduction gate before the rebuilt engine can be called a valid historical replica. Do not use only headline expectancy. Recommend a decision-packet / invariant comparison set that would make accidental headline matching unlikely.

### 4) Ambiguity risk
Answer this directly:

**Could two competent engineers read these six docs and independently build materially different backtests while each believing they followed the spec?**

If yes, enumerate every ambiguity that can materially affect accepted trades, fills, trade R, portfolio ordering, or drawdown. Rank those ambiguities by likely impact.

### 5) Original-machine recovery
Assess whether it is worth checking the original machine/session filesystem before reconstructing.

List the exact paths, filenames, caches, notebooks, shell histories, temp directories, workflow artifact downloads, or editor/worktree locations worth searching for. Do not assume Git was the only storage location.

### 6) Validation-prereg impact
Review `research_notes/CANONICAL_QF_VALIDATION_PREREG_20260928.md` conceptually against this situation.

Answer:
- Does the fact that the original executable/cache was never committed require changing the prereg?
- Or should reconstruction be treated as Phase 0 infrastructure recovery while the prereg remains frozen?
- If any amendment is necessary, specify the smallest possible amendment and explain why it is procedural rather than performance-driven.

### 7) Do-not-proceed conditions
Produce a short blocking checklist of conditions under which Muse should NOT start coding the reconstruction yet.

Examples:
- unresolved tie-break semantics;
- irrecoverable PIT universe boundary;
- unknown session labeling;
- undefined cost allocation;
- ambiguous heat/notional reservation;
- unavailable historical data that changes the eligible universe.

## Audit standard
- Do not optimize anything.
- Do not propose new trading rules.
- Do not use the published headline to reverse-engineer choices.
- Matching -0.0013R is insufficient if mechanics differ.
- Prefer saying "not reconstructable" over filling a gap with a plausible guess.
- Preserve disagreements explicitly.
- Final output should be a reconstruction audit, not code.

## Requested verdict format
End with exactly one of:
- **READY TO RECONSTRUCT**
- **READY WITH EXPLICIT AMBIGUITIES FROZEN FIRST**
- **NOT READY TO RECONSTRUCT**

Then list the minimum actions required before Muse may write code.
