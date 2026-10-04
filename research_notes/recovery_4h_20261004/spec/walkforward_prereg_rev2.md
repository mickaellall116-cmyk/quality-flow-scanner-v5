# WALK-FORWARD / SEQUENTIAL OOS STRESS TEST — PREREGISTRATION REV 2
**Recovery pre-run package — Phase C**
**Date:** 2026-10-04 | **Branch:** `recovery-4h-20261004`
**Status:** PREREGISTRATION ONLY — folds defined, performance NOT opened.
ChatGPT review required before any data pull or performance run.
**Changes from rev 1:** Closes ChatGPT review 5985221338 gaps 4, 5, 6, 7.

---

## 1. Purpose

Fixed-system validation of the corrected canonical C1: does the edge survive
sequential out-of-sample blocks with no parameter selection on OOS data?

## 2. Data source — FROZEN CLAIM (Gap 4)

### What Yahoo 1H history can and cannot guarantee

| Property | Status |
|----------|--------|
| Split-adjusted retroactively | YES — Yahoo rewrites history on splits |
| Dividend-adjusted on intraday | NO — dividends not adjusted on 1H bars |
| Bar revisions | POSSIBLE — Yahoo occasionally rewrites recent bars |
| Survivorship | NOT GUARANTEED — delisted symbols absent from current universe |
| Corporate-action timestamps | NOT point-in-time — adjustment applied retroactively without as-traded record |

### Evidence tier: LIMITED (not PIT-clean)

The walk-forward is classified **LIMITED** on data provenance. It is NOT
claimed PIT-clean. Specifically:

1. **Split handling:** our frozen split protocol (exclusion windows around
   split events) mitigates retroactive split adjustment, but cannot recover
   as-traded prices.
2. **Survivorship:** the universe is the CURRENT tradable list. Symbols that
   died before the history window are missing. This biases results upward
   (dead losers excluded).
3. **Revisions:** bars older than ~30 days are stable in practice; recent-bar
   rewrites are handled by the constructor's `now` cutoff (Gap 5), but
   historical rewrites between download dates are undetectable.

### Why proceed at LIMITED tier

No qualified PIT-clean 1H source is available at zero cost (no budget
approved for licensed as-traded archives). The walk-forward still has value
as a **regime-robustness and parameter-stability** test on consistently-
constructed bars, even though it cannot claim full PIT cleanliness. All
reported results carry the LIMITED data-tier label. Any future claim of
PIT-clean validation requires a qualified source.

**Frozen data spec:**
- Source: Yahoo Finance 1H, `auto_adjust=False`, `prepost=False`
- Target start: 2023-01-01 (or earliest available per symbol)
- Corporate actions: frozen split-exclusion protocol
- Universe: frozen C1 universe (51 symbols, `pine_backtest.UNIVERSE_X`)
- Coverage: any symbol with <80% of target history marked COVERAGE-LIMITED

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

## 4. Fold-boundary portfolio state — CONTINUOUS OOS (Gap 5)

The walk-forward is a **single continuous sequential simulation**, not
independent per-fold backtests.

### State carry rules

| State element | Fold boundary behavior |
|---------------|----------------------|
| Open positions | CARRY — positions open at fold end remain open into next fold |
| Marked equity | CARRY — continuous equity curve, no reset |
| Drawdown peak (S4) | CARRY — peak is global max over all prior folds |
| Indicator state (EMA/ATR/ADX) | CARRY — computed on continuous bar series |
| S4 gate state (halted/active) | CARRY — gate state persists across boundary |

### Trade attribution

- Every trade is attributed to the fold containing its **entry timestamp**.
- A trade entered in F1's last week and exited in F2 counts in F1's metrics.
- Fold-level metrics use entry-attributed trades only.
- Pooled OOS metrics use all trades across all folds (entry-attributed).

### What is NOT allowed

- No portfolio reset at fold boundaries (that would be a separate sensitivity
  test, not the primary walk-forward).
- No warmup re-initialization at fold starts (indicators continue from prior state).
- No look-ahead: fold F_n's bar construction uses `now` = F_n OOS end date.
  Bars from F_{n+1} are never visible during F_n's simulation.

### Implementation audit point

The continuous simulation MUST be verified by asserting:
1. Equity at F_n end == equity at F_{n+1} start (to the cent).
2. Open position count at F_n end == open position count at F_{n+1} start.
3. No trade has entry timestamp > its attributed fold's OOS end.

## 5. Report spec (per fold + pooled)

Per fold: expectancy (R), profit factor, win rate, max DD, trade count,
start/end equity.
Pooled OOS: expectancy (R), PF, win rate, max DD, total trade count,
worst fold (by expectancy), % positive folds, max consecutive losing folds,
profit concentration (top fold's share of total OOS profit),
OOS/IS degradation ratio (pooled OOS expectancy ÷ IS expectancy).

**Every reported number carries the LIMITED data-tier label.**

## 6. Cost legs

Every metric reported at three cost levels:
- **4bps** (reference cost leg)
- **25bps — PRIMARY ADJUDICATION COST** (all PASS/FAIL criteria evaluated here
  unless explicitly stated otherwise)
- **Stress:** 30bps and 35bps total (i.e. +5bps and +10bps additional)

## 7. Statistical robustness

- **Block bootstrap:** 10,000 reps on weekly OOS return blocks (preserves
  within-week dependence).
- **Outputs:** 95% CI on pooled OOS expectancy; empirical distributions of
  max DD and longest losing streak.

### Regime slices — PIT-COMPUTABLE ONLY (Gap 6)

**Bull/bear label:** SPY close > SPY 200-day SMA (both computed causally from
data available at each bar's timestamp) = bull; else bear. The 200-day SMA
at bar t uses only closes ≤ t. No future data.

**High/low-vol label:** SPY 20-day realized volatility vs its own trailing
252-day median (both causal). Above median = high-vol; below = low-vol.
The median at bar t uses only vol readings ≤ t. **No full-sample quartiles.**

Each bar gets its regime label from information available at that bar's close.
Labels are computed once on the full bar series using causal rolling windows —
this is valid because each label only uses past data.

Any slice with <30 trades marked INSUFFICIENT — reported descriptively,
excluded from adjudication.

## 8. Pre-registered adjudication (Gap 7 — tightened)

All criteria evaluated at **25bps primary adjudication cost** on pooled OOS.

| Outcome | Criteria (ALL must hold for the outcome) |
|---------|------------------------------------------|
| **PASS** | (a) Pooled OOS expectancy > +0.05R, AND (b) block-bootstrap 95% CI lower bound > 0, AND (c) no single fold contributes >50% of total OOS profit, AND (d) PARAMETER CLIFF check passes (see below), AND (e) ≥5 adequate folds. |
| **MAYBE / INSUFFICIENT** | CI spans zero, OR <5 adequate folds, OR all regime slices INSUFFICIENT, OR data-tier limitation prevents a clean read. MAYBE is not a soft PASS — it means the test cannot answer the question. |
| **FAIL** | Pooled OOS expectancy ≤ 0, OR bootstrap CI lower bound ≤ −0.10R (decisive negative), OR profit concentration >75% in a single fold. |
| **STOP** | Any evidence of lookahead/leakage, data contamination beyond the disclosed LIMITED tier, candle-parity failure between folds, post-hoc rescue tuning, or fold-boundary state discontinuity (Gap 5 audit assertions fail). STOP is terminal — report the finding, do not repair-and-continue. |

### PARAMETER CLIFF — computed criterion (not "obvious")

For each Phase D one-at-a-time variant v with canonical setting c:
- `cliff(v)` = TRUE if sign(expectancy_v) ≠ sign(expectancy_c) AND |expectancy_v − expectancy_c| > 0.10R
- The PASS criterion (d) requires: zero variants with `cliff(v)` = TRUE among
  all one-at-a-time variants tested.
- FRAGILE (informational, not a cliff): |Δ| > 0.05R without sign flip.

### Warmup-length variation — separate from fragility

Warmup length (215 bars) is NOT a strategy parameter. Indicator convergence
is proven separately: for each symbol, compare indicator values (EMA200,
ATR, ADX) at bar 215 vs bar 230 on identical inputs. If max absolute
difference across all symbols < 1% of ATR, warmup is declared CONVERGED and
excluded from Phase D. If not converged, the walk-forward is marked
INSUFFICIENT on warmup grounds before any performance is read.

## 9. Contamination controls (pre-registered)

- Fold boundaries are calendar dates; trades attributed by entry date (Gap 5).
- Indicator warmup (215 bars) is INSIDE each fold's training history, never
  borrowed from future data.
- The session-anchored constructor's `now` parameter is set to each fold's OOS
  end date during that fold's bar construction (fail-closed causal cutoff).
- Universe is frozen at study start; no additions/removals based on OOS results.
- Data tier is LIMITED (Gap 4) — disclosed on every output, not hidden.
