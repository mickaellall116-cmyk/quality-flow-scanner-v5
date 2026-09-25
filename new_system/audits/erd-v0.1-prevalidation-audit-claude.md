# ERD v0.1 — Pre-Validation Audit (Specification-Only)

**Auditor:** Claude (independent verifier role)
**Date:** September 2026
**Status:** Blind audit — performed without access to any ERD backtest results
**Scope:** Frozen ERD v0.1 preregistration only. No parameter optimization, no backtest execution, no performance data consulted.

> **Integrity note:** This audit was conducted before any ERD performance results existed. Per the blind-verification protocol, this document must not be edited after seeing backtest results. Any later revision must be filed as a separate, dated amendment (e.g. `erd-v0.1-prevalidation-audit-amendment-1.md`), never as an edit to this file.

---

## Summary

| Metric | Count |
|---|---|
| CRITICAL findings | 9 |
| MATERIAL findings | 10 |
| MINOR findings | 1 |

**Overall verdict: NOT READY**

ERD v0.1's core mechanism is not implausible, but several open items — delisting handling, dividend/total-return adjustment, fill realism at halts/gaps, magnitude-ranking replacement effects, and quantitative kill-criteria — are the same mechanisms that already produced false edges elsewhere in this program (V5.4 historical inflation; lone-wolf and laggard-veto failures). These must be written into the frozen preregistration as explicit, immutable rules *before* data provisioning begins — not decided after seeing partial results, which would turn them into unlogged hypothesis tests.

---

## A. Specification Issues Found

### 1. Event-clock logic
- **CRITICAL** — BMO/AMC classification source is unverified: is it the actual release timestamp, or a vendor-imputed flag? An imputed flag that's wrong flips which session is treated as "S" — direct leakage, not noise.
- **CRITICAL** — No defined cutoff for after-midnight/ambiguous timestamps. Needs an explicit rule (e.g., "before 4:00am ET counts as prior-day AMC") rather than vendor discretion.
- **MATERIAL** — Weekend/holiday BMO dates and "next trading day" for AMC must use an actual NYSE trading calendar, not calendar-day arithmetic.
- **MATERIAL** — Duplicate/preliminary-vs-final announcements for the same ticker/quarter need an explicit tie-breaking rule.

### 2. Reaction calculation
- **CRITICAL** — Dividend/split adjustment is not specified as total-return. An ex-dividend date landing on S or E can bias the reaction and the resulting R-outcome in a systematic direction. Must confirm a total-return series, not merely split-adjusted.
- **CRITICAL** — "Prior close" needs an explicit, code-verifiable definition for the AMC case (must equal the close on the announcement day itself, not a separately-computed S−1 — an off-by-one here mirrors the V5.4 execution mismatch).
- **MATERIAL** — Halted/no-print sessions at S need an explicit exclusion rule rather than an undefined S-close.

### 3. Entry timing
- **CRITICAL** — Unconditional open fills are implied. The biggest-reaction events are also the most likely to gap, halt, or hit limit-up/down — exactly the trades driving the reaction-magnitude ranking. Unconditional fills will systematically overstate executability on the most profitable-looking events, echoing the profit-concentration problem already found in V5.4.
- **MATERIAL** — Need an explicit skip/log rule for halted-at-open names; silent drops would bias the sample non-randomly.

### 4. ATR stop
- **MATERIAL** — Confirm whether ATR(14) includes session S itself (typically an outsized-range day). If so, the stop auto-widens with the volatility the strategy is trying to capture — must be a stated design decision, not an artifact of a rolling-window index.
- **MATERIAL** — Confirm the ATR window ends strictly at S close, not E, ruling out an off-by-one leak.

### 5. Ten-session hold
- **CRITICAL** — Delisting/acquisition handling is unspecified. Silently dropping delisted names (especially bankruptcies, which concentrate in losers) inflates historical expectancy — the single most common source of false edge in small-universe swing systems.
- **MATERIAL** — Exit-priority determinism needed for the session where both the ATR stop and E+9 timed exit could trigger (stop checked intraday, before timed exit).

### 6. Universe construction
- **CRITICAL** — ADR/REIT/preferred-stock leakage: "earnings reaction" doesn't mean the same thing for these instrument types (FFO-driven REITs, foreign-timezone ADR reporting). Needs explicit exclusion and PIT-accurate classification, not current-day classification applied retroactively.
- **MATERIAL** — IPO inclusion before 20 sessions of volume history, and ticker-change/spinoff remapping, both need explicit rules.

### 7. Earnings-calendar integrity (Intrinio/Zacks)
- **CRITICAL-to-MATERIAL (class)** — Calendar integrity is the most common source of false edges in earnings-drift research industry-wide. See Section D for the full 50-event checklist.

### 8. Portfolio replay
- **CRITICAL** — Ranking by reaction magnitude is structurally the same kind of selection mechanism that killed lone-wolf and laggard veto via replacement effects. It requires the same full-portfolio-replay stress test, including alternate ranking rules (random, first-eligible, inverse-magnitude) as comparators — not assumed safe because it's simpler than a veto.
- **MATERIAL** — Heat calculation must be dynamic (reflect already-open positions' evolving risk), not static at entry time.

### 9. Placebos
- **MATERIAL** — Random-date placebo risks being an "easy win" by construction unless matched to earnings-day volatility/gap characteristics. As specified, it may not be a fair adversarial test.
- **MINOR** — Confirm negative-reaction and shuffled-label placebos draw comparable sample sizes for statistical power.

### 10. Kill-criteria loopholes
- **CRITICAL** — Real ways ERD could "pass" while being weak:
  - A handful of outlier trades carry the whole edge (needs an explicit concentration cap, e.g., top-5-trade profit share)
  - Pass in aggregate but fail in most individual years/seasons (needs a per-period pass requirement)
  - Statistically significant but economically trivial net-of-cost R (needs a minimum expectancy floor — the same lesson as V5.4's PF≈1.00 finding)
  - "Pass" language could conflate development-split performance with validation-split performance — must specify PASS applies only to validation/later data

### 11. Multiple testing
- **MATERIAL** — Declared parameter perturbations only count as robustness checks if run on the same mechanism/universe/period and reported as a full sensitivity surface, not the best cell. Anything that changes the mechanism is a new hypothesis and consumes budget. Recommend a running test ledger logging every perturbation, promoted or not.

---

## B. Severity Key
- **CRITICAL** — Could independently create or mask a false edge; must be resolved before testing.
- **MATERIAL** — Could bias magnitude/robustness of results; should be resolved before testing.
- **MINOR** — Worth tightening but unlikely to independently drive a false result.

---

## C. Changes Required Before the Preregistration Can Fairly Be Tested

1. Written, explicit rules for BMO/AMC classification source, ambiguous-timestamp cutoff, and prior-close definition (§1–2)
2. Total-return (dividend-adjusted) reaction and R calculations, confirmed in code (§2)
3. Explicit halt/limit/gap-fill assumption at entry, with skip/log rule (§3)
4. Explicit delisting handling with real proceeds, not silent exclusion (§5)
5. PIT-accurate security-type classification excluding ADR/REIT/preferred (§6)
6. Pre-committed, quantitative kill-criteria amendments: concentration cap, per-period pass requirement, minimum net expectancy floor, validation-split-only PASS definition (§10)
7. Random-date placebo re-specified to match earnings-day volatility/gap profile (§9)

---

## D. Data-Integrity Checklist — Intrinio/Zacks 50-Event Sample

Verify per event:
- Original vs. restated announcement date
- BMO/AMC source and confidence
- Timezone stamp + DST handling
- Preliminary/estimated vs. confirmed status
- Duplicate events across feeds
- Restatement frequency (track as a data-quality metric)
- Fiscal-period-end vs. report-date confusion

---

## E. Independent-Replication Decision-Packet Schema

Base fields (as proposed):
`ticker`, `earnings_timestamp`, `bmo_amc_classification`, `s_date`, `prior_close`, `s_close`, `spy_prior_close`, `spy_s_close`, `raw_reaction`, `market_adjusted_reaction`, `eligibility_decision`, `entry_date`, `entry_open`, `atr`, `stop`, `shares`, `portfolio_heat_before_entry`, `slot_rank_decision`, `exit_date`, `exit_reason`, `exit_price`, `costs`, `realized_r`

Additional fields required:
`bmo_amc_source_confidence`, `calendar_vintage_id`, `security_type_asof`, `universe_reconstitution_date`, `corporate_action_flags`, `halt_flag`, `delisting_flag_and_proceeds`, `atr_window_start`, `atr_window_end`, `fill_assumption`, `rank_at_entry_over_total_eligible`, `heat_at_entry`

One row per event; 32 fields total — sufficient to reconstruct every eligibility, sizing, ranking, and exit decision independently of Muse's code.

---

## F. Verdict

**NOT READY**

Recommendation: amend the preregistration with items C1–C7, re-freeze it, then status becomes **READY FOR DATA**.

---

*This audit was performed under the blind-verification protocol: no ERD backtest performance was reviewed prior to or during this analysis. This document is immutable once filed. Any subsequent finding must be recorded as a dated amendment, never as an edit to this file.*