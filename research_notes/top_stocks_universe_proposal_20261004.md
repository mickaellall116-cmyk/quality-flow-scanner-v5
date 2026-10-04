# Quality Flow "Top Stocks" Universe — Research Proposal
**Status:** DRAFT for Mike's design challenge (2026-10-04)
**Process:** Muse builds → Mike challenges design → (if approved) run on studied data → Claude reviews evidence
**Constraints during prep:** entries stay paused; 4H holdout stays sealed; no signal changes

---

## 1. Research question

Does restricting the frozen Quality Flow (V5.4) system to a point-in-time-defined "top stocks" universe improve risk-adjusted performance versus the broader studied universe — on already-studied data, by enough to justify spending the sealed 4H holdout?

This is a **universe hypothesis**, not a signal hypothesis. The system is frozen. Only the eligible pool changes.

## 2. Why this question

Mike's revealed preference is concentration over breadth ("4-5 compound moves, not all signals"). This proposal tests whether that preference is skill or just taste: do liquid, strong names actually produce better risk-adjusted returns under the system, or does concentration just concentrate variance?

The studied-data comparison is a **gate**, not a validation. The system was developed on studied data, so a win there is in-sample for the system (though the universe question itself is new). A win earns the right to spend holdout data. A loss kills the hypothesis without touching the holdout.

## 3. Universe definitions (frozen before any run)

### 3.1 BROAD — the control
The 250-symbol studied universe (51 UX51 + 199 FROZEN X2). No redefinition, no additions.

### 3.2 TOP — the treatment
Computed quarterly, strictly point-in-time, from data available at each rebalance date (quarter-end):

- **Liquidity:** 60-trading-day average daily dollar volume (close × volume), ranked descending across BROAD.
- **Relative strength:** 126-trading-day total return minus SPY total return over the same window, ranked descending across BROAD.
- **Composite:** mean of the two ranks. **Top 50** by composite form the TOP universe for the next quarter.

Rebalance: first trading day of Jan/Apr/Jul/Oct. Between rebalances the list is fixed.

Edge cases (frozen):
- Names with <126 trading days of history at a rebalance date are excluded until they qualify.
- Delisted/acquired names leave at the next rebalance; the existing delisting exit logic handles open positions.
- No discretionary additions or removals. Ever.

### 3.3 Why these two factors
- **Liquidity** = tradability. Mike's real-money constraint: size can't go into names that can't absorb it.
- **Relative strength** = alignment with a long-only trend system. Don't fight the tape.
- Both are standard, mechanical, PIT-clean, and specified **before** seeing any results. No factor mining.

## 4. Data & candle spec (identical for both legs)

- **Window:** the same historical window as the corrected C1 retrospective analysis (exact dates pinned at build from C1 artifacts).
- **Candles:** corrected session-anchored 4H grid (09:30/13:30 ET) via `resample_closed_4h_session_anchored`, including the independently verified cutoff and early-close handling. The buggy 06:30 grid is never used.
- **Point-in-time throughout:** universe construction, signal computation, and portfolio decisions use only data available at each decision timestamp.

## 5. Signal spec — frozen, unchanged

V5.4 engine, rule version 2026-09-15-v54, exactly as in the corrected analysis. **No signal logic changes.** Any signal change is a different proposal.

## 6. Portfolio spec — corrected C1 stack, identical for both legs

Per the frozen canonical reconstruction (REV6):
- 5 slots; pending entries reserve slot + $750 planned risk (busy symbols skipped).
- Same-timestamp batch: drop busy → rank by **rs_top2** (desc, signal timestamp, symbol asc) → keep top-N for free slots.
- Heat gate: accept iff `(heat_dollars + 750) / E_mark ≤ 5%`, first-fit in rank order.
- `rs_top2 = (symbol 20-bar 4H return) − (SPY 20-bar daily return)`, strict PIT.

**The only difference between the two legs is the eligible universe.** Same signals engine, same portfolio rules, same costs. This is a paired comparison.

## 7. Cost legs

4bps and 25bps, matching across legs. **Primary: 25bps** (cost-realistic).

## 8. Metrics (pre-registered, in priority order)

1. **Expectancy per trade at 25bps** (primary).
2. **Annualized Calmar** (CAGR / max DD).
3. Secondary (reported, not gated): max drawdown, win rate, profit factor, trade count, yearly splits.

## 9. Gates for holdout spend — ALL must pass

| Gate | Rule |
|------|------|
| G1 — Magnitude | TOP expectancy/trade exceeds BROAD by **> +0.10R** at 25bps |
| G2 — Risk-adjusted | TOP Calmar **> 1.0** AND TOP Calmar > BROAD Calmar |
| G3 — Consistency | TOP beats BROAD on expectancy in **≥3 of 4** yearly subperiods |
| G4 — Sample | **≥100 closed trades** in EACH leg (else insufficient evidence → automatic no-spend) |
| G5 — Signal vs noise | Bootstrap 95% CI on the paired expectancy difference **excludes zero** |

Rationale for the bars: G1's +0.10R demands an economically meaningful edge, not a rounding win. G2's Calmar > 1.0 is the same promotion-grade bar the system itself failed — concentration must clear what the base system couldn't. G3 blocks a single-regime fluke. G4/G5 block small-sample mirages.

## 10. Decision procedure — one clear recommendation

- **If ALL gates pass:** spend the sealed 4H holdout on the SAME paired comparison (TOP vs BROAD, same definitions, same rules). The holdout result is the validation. Then decide on paper testing separately.
- **If ANY gate fails:** do NOT spend holdout. The concentration hypothesis is rejected on studied data. The holdout stays sealed for a worthier question.

The recommendation is **binary and mechanical**. No judgment calls, no "close enough."

## 11. What this proposal does NOT do

- Does not touch the holdout (gated behind §9).
- Does not change the system (frozen per §5).
- Does not authorize paper trading or real money (separate decisions, separate gates).
- Does not re-litigate the failed V5.4 verdict (that stands).

## 12. Null hypothesis (stated plainly)

Concentration may do nothing or harm: fewer signals (variance up), the system's edge may live in breadth (catching moves across many names), and the TOP filter may just select high-beta names that the system's exits already handle. If the data says this, the proposal reports it and stops.

## 13. Questions for Mike's challenge

1. **Top 50** — right size? (Rationale: concentrated vs 250, but large enough for the 5-slot portfolio to have selection breadth and for G4's 100-trade minimum.)
2. **Quarterly rebalance** — right frequency? (Rationale: standard, low churn, PIT-clean.)
3. **Gate bars** — is +0.10R / Calmar 1.0 / 3-of-4 the right hurdle for spending irreplaceable holdout data?
4. Anything in the TOP definition that smuggles in lookahead or discretion?
