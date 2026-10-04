# Quality Flow "Top Stocks" Universe — Research Proposal v2
**Status:** REVISED per Mike/ChatGPT protocol challenge 2026-10-04 (was v1 2026-10-04)
**Process:** Muse builds → Mike challenges → (if approved) run on studied data → Claude reviews evidence
**Constraints:** entries paused; 4H holdout sealed; no signal changes; no run authorized by this document
**Full text:** `research_notes/top_stocks_universe_proposal_v2_20261004.md` (this file)

---

## 1. Research question (unchanged)

Does restricting the frozen Quality Flow (V5.4) system to a point-in-time-defined "top stocks" universe improve risk-adjusted performance versus the broader studied universe — on already-studied data, by enough to justify a separately-reviewed, powered holdout test?

Universe hypothesis only. The system is frozen. Only the eligible pool changes.

## 2. Common PIT parent universe & survivorship (CHALLENGE §1 — revised)

### 2.1 Pool definition
BROAD is the 250-symbol studied universe (51 UX51 + 199 FROZEN X2), with definition dates pinned from artifacts at build time. **Eligibility is point-in-time:** on any date D, a symbol is eligible iff it is in the 250 AND has 1H price data covering D (coverage matrix built at run time).

TOP(D) is always selected from BROAD(D) — the same date-eligible pool. Never from a fixed list.

### 2.2 Provenance & coverage audit (frozen procedure)
At build time, before any signal computation:
1. Download 1H data for all 250 over the study window (§4).
2. Build a symbol × date coverage matrix.
3. Report: symbols with full coverage; late starters (first data date); truncated enders (last data date); missing-history spans.
4. IPO eligibility: a symbol enters BROAD(D) on its first data date; it enters TOP ranking only once it has 126 trading days of history (§3.2).

### 2.3 Survivorship caveat (stated plainly)
The 250 were defined in September 2026. Names that died between the window start (2024-09-16) and the definition date are absent from the pool. **Consequences:**
- Absolute performance levels (both legs) are likely overstated for the early window — dead names, which skew losers, are missing.
- The TOP-vs-BROAD *comparison* uses the same pool, so the bias partly cancels — but TOP's RS filter may amplify it (selecting the strongest survivors). The absolute gates (§9, G0/G2) must be read with this caveat.
- **All conclusions from the studied-data run are labeled conditional on this pool.**
- The holdout (forward-collected from Sep 2026) does not share this bias — which is part of why it is the validation, not the development run.

## 3. TOP composite — exact frozen formula (CHALLENGE §2 — revised)

Computed at each quarterly rebalance date T (last trading day of Dec/Mar/Jun/Sep), from **fully completed** daily observations ending at T's close.

### 3.1 Inputs (daily, split- and dividend-adjusted)
- `dollar_vol_s` = mean over the 60 trading days ending at T (inclusive) of `adj_close × volume`.
- `ret_s` = `adj_close[T] / adj_close[T−126] − 1` (126 trading days).
- `ret_spy` = same for SPY.
- `rs_s` = `ret_s − ret_spy`.

### 3.2 Normalization & weights
- Percentile rank within eligible BROAD(T): `prank(x) = (rank_desc(x) − 1) / (N − 1)`, rank 1 = highest. Computed separately for `dollar_vol` and `rs`.
- **Composite = 0.5 × prank(dollar_vol) + 0.5 × prank(rs).** Equal weights, frozen.
- **Ties:** average ranks for tied inputs; if the composite ties at the 50th position, **all** names tied at the cutoff are included (TOP may exceed 50; deterministic).
- **Missing inputs:** a name missing either input is excluded from ranking that quarter (no imputation).

### 3.3 Effectiveness & held positions
- New TOP list takes effect at the **next session's open** after T.
- A held position in a name that leaves TOP **finishes under frozen exits** (no forced exit). New admissions come only from the current TOP list.

## 4. Data, candles, window (CHALLENGE §3 — revised)

- **Study window:** 2024-09-16 through 2026-09-14 (the corrected-C1 window; ~2 years, ~24 calendar months).
- **Candles:** `resample_closed_4h_session_anchored` (repo commit `b3a7251`), including the independently verified causal cutoff and XNYS early-close handling. Session-anchored 09:30/13:30 ET grid.
- **Canonical implementation identity** (hashes pinned at build, before any run):
  - Signal engine: V5.4, `rule_version 2026-09-15-v54` (file + SHA-256 recorded).
  - Candle constructor: `scanner_rules.resample_closed_4h_session_anchored` (SHA-256 recorded).
  - Portfolio: corrected C1 stack per `CANONICAL_RECONSTRUCTION_FROZEN_RULES_20260928_REV6.md` (5 slots, rs_top2 ranking, 5% heat, busy rules).
  - Fills: next-bar-open; costs 4bps/25bps legs.
- **Baseline warning:** the legacy corrected-C1 headline (+0.178R etc.) was produced on a different grid and different portfolio assumptions. **Do not assume it equals this run's BROAD baseline.** BROAD is recomputed from scratch under this spec.

## 5. Signal spec — frozen, unchanged (unchanged)

V5.4 engine exactly as corrected. No signal logic changes. Any signal change is a different proposal.

## 6. Portfolio spec — corrected C1 stack, identical for both legs (unchanged)

Per §4: 5 slots, rs_top2 (desc, timestamp, symbol asc), 5% heat first-fit, busy/pending rules, $750 planned risk. **The only difference between legs is the eligible universe.** Paired comparison by construction (same engine, same period, same costs) — but see §10 on why trades are not statistically paired.

## 7. Cost legs (unchanged)

4bps and 25bps, matching. **Primary: 25bps.**

## 8. Metrics (pre-registered)

1. Expectancy per trade at 25bps (primary).
2. Annualized Calmar — **exact definition** (CHALLENGE §4): from the leg's simulated equity curve at 25bps starting $100k:
   - `total_ret = final_equity / 100000 − 1`
   - `ntd` = trading days from first entry date to last exit date
   - `CAGR = (1 + total_ret)^(252/ntd) − 1`
   - `maxDD` = max peak-to-trough decline (production `max_drawdown` helper)
   - `Calmar = CAGR / maxDD` (0 if maxDD = 0)
   - Implemented by the extracted production helpers (`annualized_return`, `calmar_ratio`, `max_drawdown`) — the same code the BOSWaves v5 gate tests exercise.
3. Reported alongside (not gated): portfolio total return, max drawdown in dollars, win rate, profit factor, trade count, yearly splits.

## 9. Gates for holdout eligibility — ALL must pass (CHALLENGE §4 — revised)

| Gate | Rule | Status |
|------|------|--------|
| G0 — Absolute bar (NEW) | TOP expectancy at 25bps **> +0.15R** (promotion-grade absolute bar) | New research gate |
| G1 — Improvement | TOP expectancy exceeds BROAD by **> +0.10R** at 25bps | New research threshold (not a promotion gate) |
| G2 — Risk-adjusted | TOP Calmar **> 1.0** (per §8 definition) AND TOP Calmar > BROAD Calmar | Existing promotion bar |
| G3 — Consistency | Named periods Y1 (2024-09-16→2025-09-15) and Y2 (2025-09-16→2026-09-14): TOP beats BROAD on expectancy in **both**, with **≥25 closed trades per leg per period** (minimum information, not mere signs) | Revised per challenge |
| G4 — Sample | **≥100 closed trades** in EACH leg over the full window (else insufficient evidence → automatic no-spend) | Unchanged |
| G5 — Signal vs noise | 95% bootstrap CI on the expectancy difference **excludes zero** (method: §10) | Unchanged |

**Why G0 exists:** beating BROAD by +0.10R is meaningless if both legs lose money. TOP must independently clear the absolute bar.

**Threshold provenance:** G2's Calmar > 1.0 and the +0.15R absolute bar are existing promotion-grade thresholds (unchanged). G1's +0.10R is a **new research threshold**, labeled as such before results — it is not a promotion gate and must not migrate into one.

## 10. Inference — dependence-aware comparison (CHALLENGE §5 — revised)

Portfolio paths differ across legs, so individual trades are **not** naturally paired. The estimand is the **difference in expectancy per trade (TOP − BROAD)** at 25bps.

**Frozen method:** common-calendar block bootstrap.
- Partition the study window into **calendar months** (~24 blocks).
- Resample months with replacement, **jointly** (the same resampled months applied to both legs — preserves cross-leg dependence from shared market regimes).
- For each of 10,000 resamples, recompute (TOP expectancy − BROAD expectancy) from the trades falling in resampled months.
- Report the 95% percentile CI; G5 passes iff it excludes zero. Alpha = 0.05.
- Report portfolio-level total return and max drawdown per leg alongside R/trade (a per-trade win that comes with catastrophic drawdown is not a win).

## 11. Holdout decision procedure (CHALLENGE §5 — proposed, separately reviewed)

A development PASS does **not** automatically unlock the holdout. It makes the proposal **eligible** for a separately reviewed holdout test. The holdout test design is proposed here, but running it requires its own approval.

### 11.1 Power check (before any holdout spend)
- Extrapolate TOP's trade rate from the development run (e.g., 120 trades / 24 months → ~55 expected in 11 months).
- Compute the minimum detectable expectancy difference at 80% power given the expected trade count and observed trade-R variance.
- **If the holdout cannot plausibly detect the G1-sized effect (+0.10R), the holdout test is not run** — an underpowered test spends irreplaceable data for no information.

### 11.2 Holdout test spec (pre-registered, adapted for 11 months)
The 11-month holdout **cannot** repeat G3's yearly splits. Its gates:
- **H1:** TOP expectancy at 25bps > +0.15R (same absolute bar as G0).
- **H2:** TOP beats BROAD on expectancy (directional; magnitude assessed against the power check).
- **H3:** TOP Calmar > 1.0 (same definition as §8).
- **H4:** ≥40 closed trades per leg (scaled minimum information for 11 months).
- Method: same block bootstrap (§10) on the holdout window; report 95% CI on the difference.
- The holdout run uses the **frozen** TOP definition, signal engine, portfolio stack, and costs — no re-tuning on development results.

### 11.3 Decision
- Development ALL-pass + power check passes + separate holdout approval → run holdout test.
- Holdout ALL-pass (H1–H4) → consider paper testing (separate decision, separate gates).
- Any failure at any stage → stop. The hypothesis is rejected; the holdout stays sealed for a worthier question.

## 12. What this proposal does NOT do (unchanged)

- Does not touch the holdout (gated behind §9 AND §11 AND separate approval).
- Does not change the system (frozen per §5).
- Does not authorize paper trading or real money.
- Does not re-litigate the failed V5.4 verdict.

## 13. Null hypothesis (unchanged)

Concentration may do nothing or harm: fewer signals (variance up), the edge may live in breadth, the RS filter may just select high-beta names the exits already handle. If the data says this, the proposal reports it and stops. A failure rejects **this exact preregistered variant**, not every possible stock-selection hypothesis. No size/rebalance sweep or rescue after seeing results.

## 14. Open questions for Mike's challenge (revised)

1. **Survivorship (§2.3):** is "conditional on this pool" labeling sufficient, or should the proposal require a harder fix (e.g., restricting the window to post-definition data)?
2. **G0's +0.15R absolute bar:** right level, given the base system failed it?
3. **G1's +0.10R improvement bar:** right hurdle for spending irreplaceable holdout data?
4. **Holdout power check (§11.1):** is the 80%-power / minimum-detectable-effect framing the right pre-commitment, or should an underpowered holdout still run for directional evidence?
5. Anything in the composite (§3) that still smuggles lookahead or discretion?
