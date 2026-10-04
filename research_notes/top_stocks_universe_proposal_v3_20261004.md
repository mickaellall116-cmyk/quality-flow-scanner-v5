# Quality Flow "Top Stocks" Universe — Research Proposal v3
**Status:** REVISED per Mike/ChatGPT full protocol review 2026-10-04 (was v2)
**Process:** Muse builds → Mike challenges → (if approved) inventory + definitions frozen → development run → Claude reviews evidence
**Constraints:** entries paused; 4H holdout sealed; no signal changes; no run authorized by this document
**Full text:** `research_notes/top_stocks_universe_proposal_v3_20261004.md` (this file)

---

## 0. Correction to v2 (acknowledged error)

v2 §2.3 stated the holdout is "forward-collected from Sep 2026." **That is wrong.** The sealed 11-month 4H holdout is **2023-10-19 → 2024-09-15, 51 UX51 symbols** (per `forward_test/holdout_protocol_v2_20261003.md` and the 2026-10-03 inventory). v2's claim that the holdout "does not share this bias" is withdrawn. Unused historical data **does** inherit selection bias from a later-selected watchlist. This section reconciles the record; §2.3 is replaced in full below.

---

## 1. Research question (unchanged)

Does restricting the frozen Quality Flow (V5.4) system to a point-in-time-defined "top stocks" universe improve risk-adjusted performance versus the broader studied universe — on already-studied data, by enough to justify a separately-reviewed, powered holdout test?

Universe hypothesis only. The system is frozen. Only the eligible pool changes.

## 2. Data & holdout inventory — non-performance (CHALLENGE §1, §3)

No performance computed in this section. Dates, identities, provenance, prior use.

### 2.1 Development data (to be built at run time)
- **Universe:** 250 symbols = 51 UX51 + 199 X2.
  - UX51: `UNIVERSE_15` (15 names) + 36 extensions, hardcoded in `pine_backtest.py`. **No selection methodology documented anywhere.** First git appearance 2026-09-29 (code developed locally, committed late). Composition consistent with a 2026-vintage watchlist (2024–2026 runners, 7 crypto pairs).
  - X2: `v54_universe_x2.py` (`EXPECTED_X2_SIZE = 199`), added 2026-09-15 (forward-test day 1).
- **Window:** 2024-09-16 → 2026-09-14 (~24 months).
- **Candles:** 1H downloads → corrected session-anchored 4H (09:30/13:30 ET) via `resample_closed_4h_session_anchored` (repo commit `b3a7251`).
- **Local cache status:** `backtest_cache/` holds 4H/daily for ~25 symbols only (watchlist names). A full 1H download for all 250 over the window is required at build time. Source: Yahoo Finance 1H (same as the corrected-C1 build). Exact source version and download timestamps recorded at build.
- **Corporate actions:** splits/dividends via Yahoo adjusted closes for returns; **dollar volume uses contemporaneous raw close × raw volume** (adjusted close × raw volume understates historical dollar turnover after splits — corrected per challenge).

### 2.2 Holdout data (sealed, verified without performance)
- **Window:** 2023-10-19 → 2024-09-15 (~11 months). **Universe:** 51 UX51 symbols only. **Bars:** 4H.
- **Provenance:** same UX51 as §2.1 — 2026-vintage composition, no documented methodology. The holdout's *prices* are untouched; its *universe* was selected with hindsight. **Sealing dates does not remove selection bias.**
- **Coverage:** BROAD-250 comparison **cannot** run on this holdout (only 51 names present). Any holdout use must be re-scoped to these 51 names or not run at all.

### 2.3 Common PIT parent universe & eligibility
- On any date D, a symbol is eligible iff it is in the 250 **and** has 1H bars covering D's session (coverage matrix built at run time, before any signal computation).
- TOP(D) is always selected from eligible BROAD(D). Never from a fixed list.
- **Completeness contract:** a symbol with no bars on an exchange trading day is treated as not tradable that day (no retroactive exclusion). For ranking eligibility (§3), a symbol needs ≥80% of expected 1H bars in each lookback window (missing intraday rows must not cause hindsight admission decisions).
- **Coverage audit at build:** report full-coverage / late-starter / truncated-ender counts with dates, before signal computation.

### 2.4 Survivorship caveat (revised)
The 250 were defined in September 2026; names that died during 2024-09 → 2026-09 are absent. Consequences:
- Absolute performance (both legs) likely overstated early-window; dead names skew losers.
- The TOP-vs-BROAD comparison shares the pool, but TOP's RS filter may amplify the bias (strongest survivors).
- **All studied-data conclusions labeled conditional on this pool** (acceptable for exploratory development; not sufficient to certify unbiased validation).
- The holdout inherits the same UX51 selection bias (§2.2) — it is **not** an unbiased validator for universe-selection hypotheses.

## 3. TOP composite — exact frozen formula (CHALLENGE §2 — revised)

Computed at each quarterly rebalance date T (last trading day of Dec/Mar/Jun/Sep), from **fully completed** daily observations ending at T's close.

### 3.1 Inputs
- `dollar_vol_s` = mean over the 60 trading days ending at T (inclusive) of `raw_close × raw_volume` (contemporaneous — §2.1).
- `ret_s` = `adj_close[T] / adj_close[T−126] − 1`; requires **127 observations** (T−126 through T).
- `ret_spy` = same for SPY; `rs_s` = `ret_s − ret_spy`.

### 3.2 Normalization, weights, direction
- Percentile rank within eligible BROAD(T): `prank(x) = (rank_desc(x) − 1) / (N − 1)`, rank 1 = highest. **Best input → 0, worst → 1.**
- **Composite = 0.5 × prank(dollar_vol) + 0.5 × prank(rs).** Equal weights, frozen.
- **Select the 50 SMALLEST composite scores (ascending).** (v2's "top 50" was ambiguous — the formula's strong end is 0.)
- **Ties:** average ranks for tied inputs; if the composite ties at the 50th position, **all** names tied at the cutoff are included (TOP may exceed 50; deterministic).
- **Missing inputs / small N:** a name missing either input is excluded (no imputation). If fewer than 50 names are valid, TOP = all valid names (documented). If N ≤ 1, no ranking is performed (degenerate — reported, not run).

### 3.3 Warmup & effectiveness
- **Initial TOP:** computed from the last completed quarter-end **before** the study start (2024-09-16), requiring daily warmup data back to ~2024-03 (for the 126-day window). Pre-window daily data is for universe construction only, never for signals.
- New TOP list takes effect at the **next session's open** after T.
- A held position in a name that leaves TOP **finishes under frozen exits** (no forced exit). New admissions come only from the current TOP list.

## 4. Canonical implementation identity (CHALLENGE §3)

Hashes pinned at build, before any run (not "hash-at-build promises" — the pinning is itself a frozen build step whose output is recorded):
- Signal engine: V5.4, `rule_version 2026-09-15-v54` (file + SHA-256).
- Candle constructor: `scanner_rules.resample_closed_4h_session_anchored` (SHA-256; commit `b3a7251` includes cutoff + early-close).
- Portfolio: corrected C1 stack per `CANONICAL_RECONSTRUCTION_FROZEN_RULES_20260928_REV6.md` — 5 slots, rs_top2 ranking (desc, timestamp, symbol asc), 5% heat first-fit, busy/pending rules, $750 planned risk. **No sector cap exists in the frozen spec** (verified — the only caps are slots/heat/busy).
- Fills: next-bar open; gap-below-stop entries invalidated and logged; open trades at window end marked at last close and **excluded** from primary expectancy (reported supplementary only, per the frozen protocol).
- Outage/coverage policy: a symbol-day with missing 1H data produces no signal (no backfill); portfolio decisions use only completed bars.
- **Baseline warning (retained):** the legacy corrected-C1 headline was produced on a different grid and portfolio assumptions. Do not assume it equals this run's BROAD baseline. BROAD is recomputed from scratch under this spec.

## 5. Signal spec — frozen, unchanged

V5.4 engine exactly as corrected. No signal logic changes.

## 6. Portfolio spec — identical for both legs (unchanged)

Per §4. **The only difference between legs is the eligible universe.**

## 7. Cost legs (unchanged)

4bps and 25bps, matching. **Primary: 25bps.**

## 8. Metrics — Calmar fixed (CHALLENGE §4 — revised)

1. Expectancy per trade at 25bps (primary).
2. **Annualized Calmar — exact definition, common window:**
   - Both legs' equity curves run over the **same fixed calendar span**: 2024-09-16 → 2026-09-14, **including idle time** (equity flat when no positions are open).
   - Equity **marked at each 4H bar close** (the system's native grid); costs included (25bps leg); initial peak = starting equity ($100k).
   - `total_ret = final_equity / 100000 − 1`; `ntd` = trading days in the fixed span.
   - `CAGR = (1 + total_ret)^(252/ntd) − 1`; `maxDD` = max peak-to-trough on the marked curve (production `max_drawdown` helper).
   - `Calmar = CAGR / maxDD` (0 if maxDD = 0).
   - **Provenance label:** annualized Calmar > 1.0 is a **new Quality Flow research gate** for this proposal. The C1 convention was total-period-return/maxDD (not annualized); BOSWaves helper reuse does not make them equivalent. Neither prior FAIL changes.
3. Reported alongside (not gated): portfolio total return, dollar max drawdown, win rate, profit factor, trade count, named yearly splits.

## 9. Gates for holdout eligibility — ALL must pass (revised)

| Gate | Rule | Provenance |
|------|------|-----------|
| G0 — Absolute | TOP expectancy at 25bps **> +0.15R** | Existing promotion-grade bar |
| G1 — Improvement | TOP expectancy exceeds BROAD by **> +0.10R** at 25bps | **New research threshold** (labeled; not a promotion gate) |
| G2 — Risk-adjusted | TOP Calmar **> 1.0** (per §8) AND TOP Calmar > BROAD Calmar | New research gate (annualized convention) |
| G3 — Consistency | Named Y1 (2024-09-16→2025-09-15), Y2 (2025-09-16→2026-09-14): TOP beats BROAD on expectancy in **both**, with **≥25 closed trades per leg per period** | Revised per challenge |
| G4 — Sample | **≥100 closed trades** per leg over the full window (else automatic no-spend) | Unchanged |
| G5 — Signal vs noise | 95% CI on the expectancy difference has **positive lower bound** (method §10) | Strengthened per challenge |

## 10. Inference — dependence-aware (CHALLENGE §5 — revised)

Trades are not naturally paired across legs (different portfolio paths). Estimand: **difference in expectancy per trade (TOP − BROAD)** at 25bps.

**Frozen method:** moving block bootstrap (contiguous blocks).
- Partition the window into **overlapping 3-calendar-month blocks**, step 1 month.
- **Trade assignment:** each trade assigned to the block containing its **exit month** (P&L realized at exit).
- Resample blocks with replacement, **jointly** across legs (same resampled blocks for TOP and BROAD — preserves cross-leg dependence from shared regimes).
- 10,000 resamples, **seed 20261004** (frozen). Per resample, recompute the expectancy difference.
- **Degenerate draws:** a resample with <5 trades in either leg is discarded; the discard rate is reported.
- Report the 95% percentile CI; G5 passes iff **lower bound > 0**. Alpha = 0.05.
- **Sensitivity (diagnostics only, not gates):** repeat with 2-month and 6-month blocks; report CI stability.
- Report portfolio-level total return and dollar max drawdown per leg alongside R/trade.

## 11. Power — for the difference, with dependence (CHALLENGE §5 — revised)

- Power the **TOP−BROAD difference estimand**, modeling **cross-leg correlation and serial dependence** — TOP variance alone is inadequate.
- Method: using development data only, simulate the block-bootstrap distribution (§10) under hypothetical holdout sample lengths; compute the minimum detectable difference at 80% power.
- **~11 monthly observations carry strong limitations:** 40 trades do not by themselves establish effective information. The power check must show its work (effective sample after dependence adjustment), not just trade counts.

## 12. Holdout — reconciled position (CHALLENGE §1, §6 — revised)

### 12.1 What the holdout is (corrected)
2023-10-19 → 2024-09-15, **51 UX51 symbols**, 4H bars, sealed. 2026-vintage universe composition → selection bias attaches. It **cannot** run the 250-name TOP-50 vs BROAD-250 comparison.

### 12.2 Recommendation: do not spend it on this proposal
Per the PARK RULE (`forward_test/holdout_protocol_v2_20261003.md` §4, Mike-approved 2026-10-03): a frozen hypothesis does not oblige spending scarce validation data on a test the holdout cannot adjudicate. This proposal's comparison needs 250 names; the holdout has 51. **The holdout stays sealed.** A re-scoped 51-name hypothesis would be a separate proposal, carrying the UX51 bias limitation.

### 12.3 If a future proposal targets the holdout (frozen criteria)
- **H2 (improvement):** holdout expectancy difference 95% CI **lower bound > 0** — a positive point estimate alone is insufficient.
- **Insufficient counts/power → INCONCLUSIVE**, reported as indeterminate — not as strategy failure.
- **Distinguish:** development failure = hypothesis rejected, holdout still sealed. Completed holdout failure = holdout spent, hypothesis rejected on untouched data. These are different evidence states and are recorded as such.
- Criteria are never weakened to directional evidence to justify spending.

## 13. What this proposal does NOT do (unchanged)

- Does not touch the holdout (§12.2).
- Does not change the system (§5).
- Does not authorize paper trading or real money.
- Does not re-litigate the failed V5.4 verdict.

## 14. Null hypothesis (unchanged)

Concentration may do nothing or harm. A failure rejects **this exact preregistered variant** — top-50, quarterly, equal-weight composite, this window — not every stock-selection hypothesis. No sweep or rescue after results.

## 15. Decision procedure (revised)

1. **Inventory + definitions frozen** (this document, after Mike's challenge).
2. **Development run** on studied data (requires Mike's explicit run approval — not granted by this document).
3. **Gates §9 evaluated.** ALL pass → the proposal is *eligible* for a re-scoped holdout discussion (separate proposal, separate review — §12.2 recommends against spending on this comparison). ANY fail → hypothesis rejected, holdout sealed, stop.
4. **Claude reviews the evidence** after the run.

## 16. Open questions for Mike's challenge (revised)

1. **Holdout non-spend (§12.2):** agree the 51-name holdout stays sealed for this 250-name comparison, or re-scope the entire proposal to UX51 now?
2. **Survivorship (§2.4):** is "conditional on this pool" labeling sufficient for the exploratory development run, or restrict the window to post-definition dates (Sep 2026 → now, ~1 month — effectively no sample)?
3. **G0/G1 bars:** +0.15R absolute / +0.10R improvement — right hurdles?
4. **Block bootstrap (§10):** 3-month moving blocks, exit-month assignment, seed 20261004 — sound, or different block structure?
5. Anything remaining in the composite (§3) or Calmar (§8) that smuggles lookahead?
