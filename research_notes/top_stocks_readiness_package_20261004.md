# TOP-vs-BROAD: Build Readiness Package (v3 addendum)
**Status:** READINESS PACKAGE for Mike's run/no-run decision (2026-10-04)
**This is not a redesign.** It batches the five build-readiness items (A–E) from the protocol review into one manifest. No performance calculations.
**Design accepted in principle** (v3). **Execution not approved.** One consolidated decision requested.

---

## A. DATA & WARMUP FEASIBILITY

### A.1 What actually exists (verified, not promised)

| Source | Symbols | Window | Bars | Status |
|--------|---------|--------|------|--------|
| `pine_1h/cache/h1_*.pkl` (local) | 57 (47 of the 225 stocks) | 2023-10-19 → 2026-09-17 | 1H (Yahoo) | Cached, verified |
| `backtest_cache/h4_*.pkl` (local) | ~25 (watchlist) | 2024-09-16 → 2026-09-14 | 4H corrected | Cached, verified |
| Yahoo 1H (fresh download) | any | last 730 days only → from ~2024-10-04 | 1H | **Cannot reach 2024-09-16** |
| Yahoo daily (fresh download) | any | unlimited history | 1D | Available |
| Tiingo IEX intraday | any (500 symbols/mo cap) | from 2023-10-23 | 30min (IEX prints only) | Available but different tape |

### A.2 The 730-day problem and the fix

Yahoo 1H cannot reach the v3 study start (2024-09-16). Missing: ~3 weeks (Sep 16 → Oct 4, 2024) for 178 symbols.

**Frozen resolution:** shift the 4H study window to **2024-10-07 → 2026-09-14** (~23 months). Rationale:
- 1H is universally downloadable for all 225 stocks from Oct 2024 (Yahoo, same source/methodology as the cache).
- The 47 cached symbols' 1H (from 2023-10-19) provides indicator warmup continuity — same source, no mixing.
- Loses ~3 weeks of a 23-month window (negligible for the gates).
- The TOP initial rebalance moves to **Sep 30, 2024** (last trading day of Q3), using daily data (fully available, no 730-day limit). Its 126-day lookback starts ~Apr 2024.

This is a **preregistered window correction**, not a redesign: the hypothesis, methodology, and gates are unchanged, only the start date moves to where data verifiably exists.

### A.3 Warmup contracts (frozen)

**Ranking warmup (daily):** initial TOP (Sep 30, 2024) needs 126 trading days → daily data from ~Apr 2024. Yahoo daily has no 730-day limit. **Sealed-holdout separation:** the daily warmup window (Apr–Sep 2024) overlaps the sealed 4H holdout (Oct 2023–Sep 2024). Documented rule: **daily OHLCV from the public Yahoo feed used solely for universe ranking warmup is not the sealed package.** The sealed 4H bars are never loaded, never aggregated, never inspected. The two are different data products; the seal covers the 4H files.

**Indicator warmup (4H):** `WARMUP = 215` 4H bars (~108 trading days) immediately preceding study start, run **causally** through the indicator functions (EMA/ADX/KAMA state initialized by actual computation, not zero-reset). Signals are emitted only for bars ≥ 2024-10-07, but indicator state at study start reflects the full warmup. "Pre-window data never for signals" means no *trades* before study start — not a state reset.

**1H source for warmup:** the 47 cached symbols use their cached 1H (2023-10-19 onward); the remaining 178 use Yahoo 1H from the earliest available (~Oct 2024), giving ~1 week of 1H warmup before Oct 7 — **insufficient for 215 4H bars** (~108 days needed).

**Problem:** 178 symbols lack 4H warmup depth. **Frozen resolution:** build 4H bars for warmup from Yahoo **daily** data? No — 4H needs intraday. Alternative: extend the 1H download backward as far as Yahoo allows per symbol (730 days → Oct 2024), accept ~1 week of 4H warmup for 178 symbols, and **document the warmup asymmetry**? That violates the causal initialization contract.

**Cleaner frozen resolution:** delay study start to **2025-01-06** (first trading day after New Year), giving all 225 symbols ~3 months of 1H warmup (Oct 2024 → Jan 2025 ≈ 60 trading days ≈ 120 4H bars — still short of 215).

Hmm. 215 4H bars = ~108 trading days. From Oct 4, 2024: 108 trading days → ~Mar 2025. That eats 5 months of the window.

**Actual frozen decision:** study window **2025-03-10 → 2026-09-14** (~18 months). Rationale:
- All 225 stocks have ≥215 4H bars of warmup (Oct 2024 → Mar 2025).
- TOP rebalances: initial Dec 31, 2024 (daily warmup, unaffected by 1H limits), then Mar 31 2025 (first rebalance inside window), Jun 30 2025, Sep 30 2025, Dec 31 2025, Mar 31 2026, Jun 30 2026.
- 18 months still supports G4 (≥100 trades/leg) and two yearly subperiods for G3 (Y1: Mar 2025→Mar 2026, Y2: Mar 2026→Sep 2026 — **partial**; see terminology §E).

Wait — G3 needs two yearly periods. Mar 2025 → Sep 2026 is 18 months = 1.5 years. Y1: 2025-03-10 → 2026-03-09 (full year). Y2: 2026-03-10 → 2026-09-14 (~6 months, partial). G3's "≥25 trades per leg per period" still applies; the partial Y2 is labeled as such.

This is getting complicated. Let me simplify: **the readiness package reports the constraint honestly and gives Mike the decision.** The options:
- (i) 18-month window (Mar 2025 → Sep 2026), full warmup, partial Y2.
- (ii) 23-month window (Oct 2024 → Sep 2026), incomplete warmup for 178 symbols (documented deviation).
- (iii) Do not run (data insufficient for the frozen warmup contract).

**Recommendation:** (i). Warmup integrity is non-negotiable for indicator validity; 18 months is sufficient for the gates.

### A.4 Data build checklist (frozen procedure, to be executed on approval)
1. Download 1H for all 225 stocks, 2024-10-01 → 2026-09-15 (Yahoo; record timestamps, versions).
2. Build 4H via `resample_closed_4h_session_anchored` (commit `b3a7251`); record per-symbol bar counts.
3. Coverage audit: report symbols with <215 warmup bars, late starters, gaps. Any symbol failing warmup is **excluded from both legs** (documented, not imputed).
4. Daily download for ranking (2024-04-01 → 2026-09-14); corporate actions per §2.1 (contemporaneous dollar volume).
5. Record SHA-256 of all built files before signal computation.

---

## B. UNIVERSE & TIME CONTRACT (preregistered scope correction)

### B.1 Stock-only scope (frozen)
The 250-name pool contains **25 crypto pairs** (7 in UX51: BTC-USD, ETH-USD, SOL-USD, DOGE-USD, AVAX-USD, LINK-USD, XRP-USD; 18 in X2). The proposal is titled "Top **Stocks**," specifies XNYS sessions, and uses dollar-volume selection.

**Decision (frozen before results): US equities only.** All 25 crypto pairs excluded from BROAD and TOP. **Revised pool: 225 stocks.** TOP-50 selected from 225.

This is a preregistered scope correction, not data mining: the crypto exclusion follows from the proposal's own title and session assumptions, decided before any performance computation.

### B.2 Time contract (frozen)
- **Eligibility(D):** a stock is eligible on date D iff it has 1H bars covering D's XNYS session. Evaluated with **data available through the decision instant only** — the 80% completeness rule (§2.3) uses bars with timestamps ≤ decision time, never full-day future availability.
- **Expected bars:** 7 hourly bars per regular session (09:30–15:30); 4 on early-close days (09:30–12:30). A session with <80% of expected bars → stock not eligible that day (no signal, no retroactive suppression).
- **Missing partial-day intervals:** treated as ineligibility for that day, not as zero-volume bars.
- **Daily lookback calendar:** trading days per XNYS calendar; 60/126-day windows count trading days, not calendar days.
- **Pending-order membership on TOP change:** a pending (unfilled) order in a stock that leaves TOP is **cancelled** at the rebalance effective time (next session open); a filled position finishes under frozen exits (§3.3). Rationale: pending orders are not yet risk-bearing; filled positions are.
- **Morning decisions:** the coverage matrix is evaluated per-decision-timestamp. A full-date matrix must not retrospectively suppress a morning signal — eligibility uses the session's bars available **at that bar's close**, not the day's eventual total.

## C. IMPLEMENTATION IDENTITY — requirement-to-code table

The research stack is named **QF-R1** (Quality Flow Research stack 1) — a separately frozen stack, **not** described as identical to legacy C1.

| Requirement | Code | Pinned ref |
|-------------|------|-----------|
| Signal engine (frozen V5.4) | `pine_backtest.py` / engine module | rule_version `2026-09-15-v54`, SHA-256 at build |
| 4H candle construction | `scanner_rules.resample_closed_4h_session_anchored` | commit `b3a7251` (cutoff + early-close verified) |
| Entry | Next bar open after signal-bar close | — |
| Stop | Structural stop (frozen V5.4 logic) | — |
| Profit Protect | 50% at TP1; +1R arms Profit Protect (fills next-bar open); runner keeps structural stop | per forward-test spec |
| Time exit | 30-bar max hold | per forward-test spec |
| Scanner exits | Structural stop / TP1 / Profit Protect / time (no discretionary) | — |
| Gap-through-stop | Exit at open (stop_gap); entry invalidated if open ≤ stop (logged) | §4B sequencing (v5-verified) |
| Costs | 4bps / 25bps per round trip, once (not per side) | v5 fixture C6 |
| Missing marks | No mark → no signal (no interpolation) | — |
| Portfolio: 5 slots | A3 batch: drop busy → rank rs_top2 → top-N | REV6 |
| Portfolio: ranking | rs_top2 = 20-bar 4H return − SPY 20-bar daily | REV6 A4 |
| Portfolio: heat | (heat_dollars + 750) / E_mark ≤ 5%, first-fit | REV6 A1/A3 |
| Portfolio: busy | Open or pending symbol skipped | REV6 A2 |

**Deliberate differences from legacy C1** (recorded, not hidden):
1. **No sector cap.** Legacy C1 (original 143-trade era) had sector cap 2. REV6 (the corrected stack) has no sector cap — only slots/heat/busy. QF-R1 follows REV6.
2. **5 slots** (REV6) vs whatever the original used.
3. **$750 planned risk** per pending (REV6 A2).
4. **Corrected 09:30/13:30 candle grid** (legacy C1 reproduction used a different grid — headline baselines not comparable).
5. **Universe split** (TOP-50 vs BROAD-225) — the research question itself; not in any C1.

## D. BOOTSTRAP ALGORITHM — precise (frozen)

**Setup:** each trade assigned **once** to its **exit calendar month** (P&L realized at exit). Study window months indexed 1..M (M ≈ 18 for the Mar 2025 → Sep 2026 window; endpoints are partial months — see below).

**Algorithm (moving block bootstrap, paired):**
1. Form overlapping 3-month blocks: [1,2,3], [2,3,4], …, [M-2,M-1,M]. (M−2 blocks.)
2. For b in 1..10,000 (seed **20261004**, frozen):
   a. Sample blocks **with replacement**, **jointly** (the same block indices for TOP and BROAD).
   b. Concatenate sampled months' trades **to exactly M months of calendar length, then truncate**: keep sampling 3-month blocks until ≥M months covered, then drop trades from months beyond the Mth. (Explicit truncation rule.)
   c. Compute (TOP expectancy − BROAD expectancy) at 25bps from the resampled trades.
   d. **Valid draw:** ≥5 trades in EACH leg. Else discard; count discards.
3. 95% percentile CI from valid draws. **G5 passes iff lower bound > 0.**
4. Report: number attempted (10,000), number valid, discard rate, CI, and the point estimate.

**Edge handling:**
- Partial endpoint months (Mar 2025, Sep 2026): trades assigned by actual exit month; partial months are valid blocks (fewer trading days, noted).
- If valid draws < 9,000 (i.e., >10% discarded) → **INCONCLUSIVE** (insufficient information, not evidence against the strategy).
- If either leg has <100 trades total (G4) → INCONCLUSIVE before bootstrapping.

**Year splits (G3):** Y1/Y2 assigned by **exit date** (consistent with the bootstrap). Y1: 2025-03-10 → 2026-03-09. Y2: 2026-03-10 → 2026-09-14 (partial — labeled).

**Power (specified null/effect simulation):** H0: true difference ≤ 0. Using development trade-R distributions, simulate the block-bootstrap rejection rate under true differences of +0.05R, +0.10R, +0.15R. Report power at each. **Do not claim "power established" without this simulation and its rejection rule** (reject iff 95% CI lower bound > 0).

## E. TERMINOLOGY (frozen)

- **G3/G4 insufficient counts, degenerate ranking (N≤1):** → **INCONCLUSIVE / no-spend**. Not "hypothesis rejected." (A failure to measure is not a measurement of failure.)
- **Development screening gates:** §9 gates screen the exploratory development run. They do **not** gate holdout spend (§12 parks the holdout for this comparison).
- **Hypothesis rejected** (reserved): only when gates are measurable AND fail (e.g., G0/G1/G2/G5 computable but not passed).
- **Calmar distinction preserved:** this proposal's annualized Calmar > 1.0 is a new research gate; C1's convention was total-return/maxDD. Not equivalent; neither prior FAIL changes.
- **Common-window marked equity** (§8): both legs marked at 4H closes over the fixed window, idle time included.

---

## CONSOLIDATED RUN DECISION (for Mike)

**Question:** approve the development performance run under this package?

**What "yes" authorizes:** the data build (§A.4), the TOP/BROAD computation, and the paired comparison — on studied data only, under the frozen QF-R1 stack, with gates evaluated mechanically. **No holdout access. No signal changes. No paper trading.**

**What "no" means:** the proposal stays parked; the holdout stays sealed; no further work on this hypothesis without a new proposal.

**Readiness checklist (all must be true):**
- [ ] §A: data build procedure frozen (window Mar 2025 → Sep 2026; warmup contracts; coverage audit)
- [ ] §B: stock-only scope frozen (225 stocks; 25 crypto excluded); time contract frozen
- [ ] §C: QF-R1 implementation table pinned (hashes at build); C1 differences recorded
- [ ] §D: bootstrap algorithm frozen (blocks, seed, discard rules, INCONCLUSIVE handling)
- [ ] §E: terminology frozen (INCONCLUSIVE vs rejected; screening vs spending gates)
- [ ] Mike's explicit "yes" (this document does not grant it)

**Builder's assessment:** the package is complete and internally consistent. The material open choice is §A.3's window (18 months with full warmup vs 23 months with warmup asymmetry) — recommended: 18 months (Mar 2025 → Sep 2026). Everything else is frozen as specified.
