# TOP-vs-BROAD: Readiness Addendum v2 (blockers resolved)
**Status:** NON-PERFORMANCE work product (2026-10-04). Addresses the five review blockers. **No performance run. No holdout access.**
**Parent:** `research_notes/top_stocks_readiness_package_20261004.md` (commit `2e37099`).

---

## 1. Coverage denominator — FIXED (blocker 1)

**The bug:** v1 §B.2 said "7 hourly bars per regular session" with ≥80%. At a 13:30 decision, only 4 hourly bars are complete — 4/7 = 57% < 80% would block every 13:30 signal.

**Frozen rule (replaces v1 §B.2):** the denominator is the **expected COMPLETED source intervals through the decision instant**, clipped to the actual session end. The forming bar is never counted.

| Decision time | Expected completed | 80% threshold (ceil) |
|---------------|-------------------|---------------------|
| 13:30 (regular) | 4 (09:30, 10:30, 11:30, 12:30) | 4 of 4 |
| 16:00 (regular) | 7 (6×60min + 1×30min 15:30–16:00) | 6 of 7 |
| 13:00 (early close) | 3 (09:30, 10:30, 11:30) | 3 of 3 |

**Fail-closed on distorted 4H bars:** the 80% session rule governs *eligibility* (whether the stock is considered that day). Separately, **any emitted 4H candle must contain all its expected hourly constituents** — a 4H bar missing any hourly source interval is not emitted (fail-closed for that bar). The session-level 80% rule can never authorize a partial 4H bar.

**Synthetic fixtures:** `tests/test_qf_r1_synthetic_20261004.py` F6 — 13:30/16:00/early-close boundary cases, all passing.

## 2. QF-R1 implementation — PINNED (blocker 3)

**Pinned files (SHA-256):**
- `pine_backtest.py` — `447a9a13bb2ec7ab…` (full hash in test header)
- `scanner_rules.py` — `7db282ddfc150c9e…` (candle constructor, commit `b3a7251`)

**QF-R1 = the `pine_backtest.py` lineage** (the code that produced the corrected C1, 240 trades). This corrects v1 §C and v3 §3.2, which inaccurately described a "REV6" stack with rs_top2 ranking, busy/pending, and $750 fixed risk — **none of which are in the baseline code.**

### Actual QF-R1 semantics (verified by synthetic fixtures F1–F5, F7)

| Requirement | Actual implementation | Location |
|-------------|----------------------|----------|
| Signal | `pine_buy_signal(df, i)` — confirmed / breakout_buy / ready_buy | `pine_backtest.py:109` |
| Entry | Fill at **open of bar i+1**; invalid if entry ≤ stop (`skipped_gap++`, logged) | `gen_pine_trades`, L138 |
| Stop | **Close-evaluated** (NOT intrabar): close < runner → exit at **next bar open** | L170–186 |
| TP1 | Intrabar: high ≥ tp1 → **50% at TP1** (limit), runner continues | L172–173 |
| Trail | After TP1: runner = max(runner, close − atr×2.5) at **bar close** | L175 |
| Scanner exits | close < e55 ("ema55-break") or bear trend ("ema55-bear") → next bar open | L178–182 |
| 30-bar max hold | **ABSENT** — documents a difference from forward-test Mode B | (not in code) |
| Profit Protect arming | **ABSENT** — trail-after-TP1 instead; documents a difference from Mode B | (not in code) |
| R accounting | Blended: 0.5×TP1_R + 0.5×runner_R; costs 4bps/25bps per round trip | `_outcome`, L214 |
| Portfolio slots | 5 concurrent (`MAX_CONCURRENT = 5`) | `simulate_portfolio`, L221 |
| Portfolio heat | (open risk $ + new risk $) / equity ≤ 5% (`MAX_PORTFOLIO_RISK`) | L257 |
| Portfolio ranking | **Chronological** — NO rs_top2 (documents v3 §3.2 inaccuracy) | L224 (time-sorted events) |
| Sizing | risk_pct × marked equity (NOT fixed $750) | L259 |
| Equity | $10,000 start (`START_EQUITY`) | L55 |

### Deliberate differences from forward-test Mode B (recorded)
ModeBTracker (`v54_exit_tracker.py`) uses intrabar stops ("stop wins ties"), 30-bar max hold, Profit Protect arming, and scanner EXIT gating. QF-R1 (research baseline) uses close-evaluated exits and no time stop. **These are different systems; QF-R1 results do not transfer to Mode B expectations and vice versa.** The forward test's live behavior is governed by ModeBTracker, not by this research.

## 3. Missing-mark policy — SPECIFIED (blocker 4)

v1 §C's "no mark → no signal" covered entries but not held positions.

**Frozen rule:** a held position missing a fresh mark is **valued at the last available close (stale), flagged `stale_mark=True` in the ledger, and its full exposure retained** in equity and drawdown. It is never dropped, never marked to zero, and never excluded from max-drawdown computation. Admission of *new* positions in a symbol with no mark through the decision instant is blocked (no signal). Synthetic fixture F7 verifies the stale position remains counted.

## 4. Window — CONSOLIDATED (blocker 5)

**One definitive window: 2025-03-10 → 2026-09-14.** All superseded "frozen resolutions" (Sep 2024 start, Oct 2024 start) are withdrawn.

- **M (calendar month buckets):** Mar 2025 … Sep 2026 = **19 buckets** (18.2 elapsed months). Bootstrap blocks computed from these 19 indices.
- **G3 (revised, labeled):** Y1 = 2025-03-10 → 2026-03-09 (full year); Y2 = 2026-03-10 → 2026-09-14 (**~6 months, partial**). This is an explicit pre-result gate revision from the "two one-year periods" in v3 — the ≥25-trades-per-leg criterion is retained for both. The partial Y2 is labeled as such in all reporting.
- **Initial TOP (Dec 31, 2024):** 126-trading-day daily lookback → starts ~Jul 2024. (v1's "April" was conservative; July is sufficient. Daily data has no 730-day limit.)
- **Daily ranking overlap with sealed holdout:** the Dec 2024 ranking uses daily bars from Jul–Dec 2024, which overlaps the sealed 4H holdout window (ends Sep 2024). Logged as **ranking-only use of public daily data** — the sealed 4H bars are never loaded. This does not claim "all same-date evidence untouched."

## 5. Data inventory — IN PROGRESS (blocker 2)

The full 225-stock 1H download + 4H build + per-name warmup audit is running as a separate non-performance task. **No "all 225 verified" claim is made here.** The inventory report (`research_notes/data_inventory_20261004.md`) will carry per-symbol counts, IPO/gap/corporate-action findings, and the pass/fail list against the 215-bar warmup requirement. **The performance-run decision waits for that report.**

---

## Consolidated status

| Blocker | Status |
|---------|--------|
| 1. Coverage denominator | **RESOLVED** — completed-intervals rule + fail-closed + fixtures |
| 2. Warmup/data verification | **IN PROGRESS** — inventory task running; no claims until report |
| 3. QF-R1 pinned + tested | **RESOLVED** — hashes pinned; 16/16 synthetic fixtures pass; v3 §3.2 inaccuracy corrected |
| 4. Missing-mark policy | **RESOLVED** — stale valuation, exposure retained, flagged |
| 5. Window consolidation | **RESOLVED** — one window, 19 buckets, G3 labeled as full+partial |

**Remaining before the performance-run decision:** the data inventory report (blocker 2). Nothing else is outstanding. **No performance run is authorized by this document.**
