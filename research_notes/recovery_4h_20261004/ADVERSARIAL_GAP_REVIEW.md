# ADVERSARIAL GAP REVIEW
**Recovery pre-run package — required by standing protocol v1**
**Date:** 2026-10-04 | **Branch:** `recovery-4h-20261004`
**Role:** Honest adversarial review of THIS PLAN, not of the strategy.

---

## 1. What could go wrong

### A1. The "corrected" bars may not match what the scanner would have produced live
The session-anchored constructor is deterministic on 1H inputs, but the LIVE
scanner never used it — it used vendor 4H (Path 4) and the legacy constructor
(Path 1). The corrected replay answers "what if the system had always used
correct bars," NOT "what would live have done." Any claim that corrected
performance predicts live performance must clear the separate candle-parity
AND portfolio-decision parity gates. This package does not clear them.

### A2. Yahoo 1H history is not point-in-time clean
Yahoo retroactively adjusts for splits/dividends and occasionally rewrites
bars. "Longest PIT-clean history" is aspirational — true PIT requires
as-traded archives we don't have. The walk-forward mitigates but does not
eliminate survivorship/adjustment bias. Delisted symbols are missing entirely.

### A3. The per-day-origin path (Path 3) may differ from session-anchored in ways
### that flatter the corrected run
If Path 3 had a subtle defect that SUPPRESSED trades (e.g. dropped valid bars),
the corrected run could show MORE trades and look better for purely mechanical
reasons. The byte-identity fixtures (Phase A) must be read skeptically: deltas
in either direction need causal explanation, not just documentation.

### A4. Walk-forward with 6 folds on ~3.5 years is still a small sample
Six 6-month folds is the minimum for the word "robust." A single regime
(2023-2026 was mostly a bull market with one sharp drawdown) dominates.
The regime slices will likely be INSUFFICIENT — which the preregistration
handles by exclusion, but exclusion is not evidence.

### A5. Parameter inventory can become optimization with extra steps
The "no winner selection" rule is a behavioral commitment, not a technical
constraint. If the surface shows a clearly better setting, the temptation to
adopt it will be strong. The only defense is the written rule + ChatGPT
adjudication. Mike must hold this line.

## 2. Load-bearing assumptions

| # | Assumption | If false... |
|---|-----------|-------------|
| 1 | Session-anchored bars = "correct" bars | The entire recovery is built on a different-but-arbitrary grid. Correctness is defined as DST-invariance + session alignment, which is principled but not proven optimal. |
| 2 | 215-bar warmup is sufficient for indicator stability | EMA200 needs 200 bars minimum; 215 leaves only 15 bars of margin. Early-fold signals may be unstable. |
| 3 | XNYS calendar covers all session-close variations | Unscheduled closes (e.g. national mourning, exchange outages) are not in the calendar. Fallback is 16:00, which is wrong on those days. |
| 4 | The frozen C1 parameters are the right baseline | We're recovering the AS-STUDIED system, not the best system. If the studied parameters were overfit, the recovery faithfully reproduces overfit results on cleaner bars. |
| 5 | Block bootstrap on weekly blocks captures dependence | 4H-bar autocorrelation and multi-day trade overlap may exceed weekly blocks. CI could be too narrow. |

## 3. Where leakage could creep in

- **Fold boundary trades:** a trade entered in F1's last week and exited in F2
  must be assigned by entry date. The preregistration covers this, but the
  implementation must be audited.
- **Universe definition:** if the symbol list was formed with knowledge of
  post-2023 outcomes, the walk-forward is contaminated at the universe level.
  Document universe provenance explicitly.
- **Warmup borrowing:** 215 bars of "training history" before F1 must actually
  exist. If history starts too late, the first fold's warmup borrows from...
  nothing — it must be marked INSUFFICIENT, not padded.
- **`now` parameter:** the constructor's fail-closed cutoff must use each fold's
  OOS end, not the global data end. A single global `now` leaks future bars
  into early folds' last-bar exclusion logic.
- **Sector map:** frozen, but if sector assignments changed over 2023-2026
  (they do), using current assignments for historical folds is a subtle
  lookahead. Document which vintage the map represents.

## 4. What the plan doesn't cover

- **Live parity:** nothing here proves the corrected system would execute the
  same in production (order types, fills, corporate actions, data vendor).
- **Regime robustness:** acknowledged as likely INSUFFICIENT.
- **The 4 legacy positions:** explicitly out of scope (pinned path preserved).
- **Costs beyond 35bps:** institutional frictions (market impact at size) not modeled.
- **What "correct" means for volume:** Yahoo 1H volume vs vendor 4H volume
  aggregation differences are not addressed by bar-boundary fixes.

## 5. Strongest objection to this plan

> "You're spending significant effort to precisely measure a system whose
> corrected expectancy is unknown and whose prior corrected-grid replay was
> −15.23R. If the canonical bars don't rescue the edge, this is an expensive
> autopsy. The walk-forward should come FIRST on the existing (possibly
> flawed) bars to test whether there's anything worth recovering, before
> investing in bar-construction forensics."

**Response:** The ordering is deliberate. The bar-construction defect is a
known, proven contaminant (live traded wrong candles for 3 weeks). Any
measurement on contaminated bars — including a walk-forward — inherits the
contamination. Clean the instrument first, then measure. But the objection
sets a valid tripwire: if Phase A shows Path 2 ≡ Path 3 (no material delta),
the "recovery" narrative weakens and the walk-forward becomes the main event.
