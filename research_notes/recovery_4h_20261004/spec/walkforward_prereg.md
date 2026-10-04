# WALK-FORWARD / SEQUENTIAL OOS STRESS TEST — PREREGISTRATION
**Recovery pre-run package — Phase C**
**Date:** 2026-10-04 | **Branch:** `recovery-4h-20261004`
**Status:** PREREGISTRATION ONLY — folds defined, performance NOT opened.
ChatGPT review required before any data pull or performance run.

---

## 1. Purpose

Fixed-system validation of the corrected canonical C1: does the edge survive
sequential out-of-sample blocks with no parameter selection on OOS data?

## 2. Data requirement (to be pulled AFTER review)

- **History:** longest point-in-time-clean 1H Yahoo history available per symbol,
  target start **2023-01-01** (or earliest available if later).
- **Why:** ≥5 six-month OOS folds require ~30 months OOS + 215-bar warmup
  (~7 months). Existing `backtest_cache/v3/h4_*` (Sept 2024 → Sept 2026) is
  INSUFFICIENT alone (~2-3 folds max).
- **PIT-clean:** raw 1H downloads with split/dividend adjustment disabled;
  corporate-action handling per frozen split protocol. No survivorship repair
  beyond the frozen universe definition.
- **Universe:** frozen C1 universe (same symbols as the corrected baseline).
  Document any symbol with <80% of the target history as COVERAGE-LIMITED.

## 3. Fold design (expanding window, frozen at data-pull)

- **Warmup:** first 215 4H bars of each symbol's history are indicator warmup only
  (no signals evaluated).
- **OOS blocks:** 6 calendar months each, non-overlapping, sequential.
- **Training:** all history BEFORE each OOS block is training/warmup/state ONLY.
  No parameter is chosen, tuned, or selected on any OOS block or on pooled OOS.
- **Minimum:** ≥5 distinct OOS folds. If history permits fewer, mark the study
  INSUFFICIENT — do not shrink blocks to manufacture folds.

### Proposed fold calendar (template — freeze exact dates at data-pull)

Assuming tradeable start ≈ 2023-08-01 (215-bar warmup on Jan-2023 history):

| Fold | OOS window | Training history ends |
|------|-----------|----------------------|
| F1 | 2023-08-01 → 2024-01-31 | 2023-07-31 |
| F2 | 2024-02-01 → 2024-07-31 | 2024-01-31 |
| F3 | 2024-08-01 → 2025-01-31 | 2024-07-31 |
| F4 | 2025-02-01 → 2025-07-31 | 2025-01-31 |
| F5 | 2025-08-01 → 2026-01-31 | 2025-07-31 |
| F6 | 2026-02-01 → 2026-07-31 | 2026-01-31 |

Partial F7 (2026-08-01 → data end) reported descriptively only, not in pooled stats.

**Freeze rule:** exact fold boundaries are set from the ACTUAL earliest
tradeable date per the pulled data, then committed BEFORE any OOS performance
is computed. No boundary moves after seeing results.

## 4. Report spec (per fold + pooled)

Per fold: expectancy (R), profit factor, win rate, max DD, trade count,
start/end equity.
Pooled OOS: expectancy (R), PF, win rate, max DD, total trade count,
worst fold (by expectancy), % positive folds, max consecutive losing folds,
profit concentration (top fold's share of total OOS profit),
OOS/IS degradation ratio (pooled OOS expectancy ÷ IS expectancy).

## 5. Cost legs

Every metric reported at three cost levels:
- **Canonical:** 4bps (primary for cost reporting)
- **Primary adjudication:** 25bps
- **Stress:** +5bps and +10bps additional (i.e. 30bps and 35bps total)

## 6. Statistical robustness

- **Block bootstrap:** 10,000 reps on weekly OOS return blocks (preserves
  within-week dependence).
- **Outputs:** 95% CI on pooled OOS expectancy; empirical distributions of
  max DD and longest losing streak.
- **Regime slices:** bull/bear and high/low-volatility, defined by SPY
  200-day trend and realized-vol quartiles. Any slice with <30 trades marked
  INSUFFICIENT — reported descriptively, excluded from adjudication.

## 7. Pre-registered adjudication

| Outcome | Criteria |
|---------|----------|
| **PASS** | Pooled OOS expectancy > 0 at 25bps canonical costs AND block-bootstrap CI lower bound > 0 AND no single fold contributes >50% of total OOS profit AND no parameter cliff (Phase D neighborhood shows no discontinuous collapse at canonical settings). |
| **MAYBE / INSUFFICIENT** | CI spans zero, OR <5 adequate folds, OR regime slices all INSUFFICIENT. |
| **FAIL** | Pooled OOS expectancy ≤ 0 at 25bps. |
| **STOP** | Any evidence of lookahead/leakage, data contamination, candle-parity failure between folds, or post-hoc rescue tuning. STOP is terminal for the study — report the finding, do not repair-and-continue. |

## 8. Contamination controls (pre-registered)

- Fold boundaries are calendar dates; no trade may have entry in one fold and
  exit counted in another (assign by entry date).
- Indicator warmup (215 bars) is INSIDE each fold's training history, never
  borrowed from future data.
- The session-anchored constructor's `now` parameter is set to each fold's OOS
  end date during that fold's bar construction (fail-closed causal cutoff).
- Universe is frozen at study start; no additions/removals based on OOS results.
