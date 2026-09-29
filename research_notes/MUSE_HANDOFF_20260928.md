# Muse Handoff — Quality Flow Research
**Date:** 2026-09-28  
**Owner:** Mike  
**Purpose:** Restore Muse as primary research executor after credit interruption.

## 0) Read this first
Latest user directive supersedes older lane restrictions where they conflict: **keep testing the other trend probes while KAMA forward-shadows.** Do not revive killed branches or modify live/frozen QF.

Roles:
- **Muse:** primary builder/executor; use parallel worktrees/jobs where helpful.
- **ChatGPT:** research architect + adversarial reviewer.
- **Claude:** independent replication/code auditor at major gates.
- **Mike:** final decision-maker.

Hard research rule: never call something tested unless an actual run completed and outputs exist. Preregister before looking. Preserve failed tests. No production change without Mike's explicit approval.

Repository: `mickaellall116-cmyk/quality-flow-scanner-v5`

## 1) Frozen/live state
- Frozen V5.4/live QF logic remains untouched.
- KAMA is **NOT** a live filter. It is now a passive forward-shadow observation only.
- Do not alter signal generation, ranking, sizing, stops, TP1, exits, or alerts because of KAMA.
- Any exploratory work belongs on a research branch/worktree.

## 1A) Pre-HEMA context — full research arc Muse must retain

Muse was unavailable for longer than the HEMA work. The following earlier state is part of the handoff and must be treated as standing context, not rediscovered from scratch.

### Frozen QF / V3.6-V3.7 lineage
- Primary timeframe: **4H**. A 1H transfer test failed badly and is closed.
- V3.6 entry/exit mechanics were the stable signal core. V3.7 was a **clean parity/observability release**, not a new edge: no entry-rule change vs V3.6.
- The trendScore issue was a Python mirror bug only; Pine's 0-5 score was already correct.
- Entry Mode is frozen to **Hybrid**. The three optional "Use X as Real Entry" toggles for pullback/FVG/sweep stay false unless explicitly studied; they can silently change signal semantics.
- TradingView Strategy Tester equity curves are not the canonical portfolio benchmark; Pine is used for parity/visual validation only.

### Earlier V3.6 research results
The original 4H UX51 V3.6 study (2024-09-16 through 2026-09-14) produced roughly:
- 263 trades
- 44.9% win rate
- +0.195R expectancy
- PF 1.33
- ~+35% return
- ~35% max DD

Important transfer/expansion failures:
- 1H transfer: ~+0.009R, ~-54% return, ~67% DD, 1,394 trades -> FAIL.
- Pine/scanner agreement filter: only 14/263 overlap, overlapping trades ~-0.24R -> FAIL as a gate.
- Blind larger-universe expansion: ~-0.01R -> FAIL.
- Daily transfer: ~-0.05R -> FAIL.
- Weekly transfer: small sample, ~31 trades and +0.55R -> only a MAYBE, never promoted.
- Legacy V1.1 looked excellent in a bull window (~+0.30R) but failed 2022 (~-0.08R).
- Relative-strength variants looked good in the bull window but also failed 2022. Do not revive them from the old selected sample.

### Portfolio-selection / risk work before canonical reframe
On crowded bars, ranking the top 2 by **20-bar stock return minus SPY** improved the selected-sample result:
- ~154 trades
- ~+0.32R/trade vs ~+0.20R without the ranking
- DD ~32.7% vs ~35.2%
- no obvious 2022 harm in that historical check.

Sector-cap and risk controls were then studied:
- max 2 positions/sector improved DD and expectancy in the selected-sample simulation;
- drawdown/risk gate helped on its own;
- the combined stack later showed redundancy.

The locked research stack known as **C1** became:
- V3.6 entries/exits unchanged;
- top-2 20-bar return-minus-SPY ranking;
- max 2 per sector;
- risk gate at 5% portfolio risk.

Engineering parity replay reproduced that stack exactly:
- 143 trades
- ~+0.337R/trade
- ~+52.25% return
- ~31.63% DD
- rejections: 94 ranked out, 16 sector-capped, 10 risk-gate
- alert/dedup/fault-isolation suite passed 29/29.

These numbers are historical **selected-sample engineering evidence**, not canonical proof. Later PIT/cost/execution work showed that the broad canonical system was near flat at realistic 50 bps. Do not use the C1 headline as evidence that QF itself is proven.

### Frozen V5.4 forward test
V5.4 was frozen for untouched forward measurement on ~250 symbols (UX51 + X2):
- signal/exit logic frozen;
- forward checkpoints planned around ~50 and ~100 signals;
- no rule patching while forward data accumulates.

Published forward status before the current KAMA shadow work had 26 signals logged by 2026-09-25. That forward stream continues independently of KAMA.

### Important methodological lessons already earned
- Portfolio replay is mandatory. Filters/vetoes can look good trade-by-trade but fail after slot/heat displacement.
- Concentration is a first-class failure mode: top trades/episodes carried a large share of historical P&L.
- Realistic costs matter; QF degrades sharply as round-trip friction rises.
- Tiny structural stops can create absurd notional leverage unless explicit capital/gross constraints are enforced.
- Effective sample size is closer to market episodes than raw trade count when signals cluster.
- No hand-picked watchlist result may be treated as broad-universe proof.
- Once a family has been explored on a dataset, a second attempt needs genuinely new/held-out data rather than retuning the same history.

### Other research underway before HEMA
- **ERD v0.1** is a separate fresh-system architecture, not a QF filter. It was frozen lab-only and blocked on clean point-in-time earnings data/timing validation. Do not mix ERD with the trend-probe work.
- Fundamental/F7 work reached infrastructure/feasibility review only; no performance claim should be inferred from those artifacts.
- Macro items Mike asked about (MOVE/rate velocity, CPI, Nasdaq, Russell 2000, 10Y, ARM weekly context) are research/context ideas, **not part of the frozen QF entry rule** unless separately preregistered and tested.

## 2) What happened while Muse was unavailable

### A. HEMA line of research is closed
HEMA was tested as:
- hard entry gate;
- crowded-bar ranking input;
- runner/exit control;
- loss-control/emergency exit;
- standalone crossover timing;
- pre-cross convergence predictor.

None earned a live role.

Key completed runs:
- HEMA entry timing: run `36375552823`, artifact `10950049609`
- HEMA pre-cross convergence: run `36375887910`, artifact `10951370404`
- raw QF entry timing: run `36376113805`, artifact `10951400361`
- HEMA loss control: run `36373492556`, artifact `10950051985`
- HEMA ranking: run `36372139137`, artifact `10949631519`

Important conclusion: waiting for HEMA confirmation after QF materially harmed entries; HEMA is late, not a useful confirmation layer.

### B. Trend-Probe Tournament I completed
Prereg:
`research_notes/TREND_PROBE_TOURNAMENT_PREREG_20260928.md`

Run:
- workflow run `36421422003`
- job `108924815610`
- artifact `10970047829`
- result note `research_notes/TREND_PROBE_TOURNAMENT_RESULT_20260928.md`
- result commit `43a42e764df06f63ae6add217f31cade82811000`

Candidates: EMA20/40, HEMA20/40, HMA20/40, KAMA20/40, ZLEMA20/40.

Standalone bullish crossovers all failed matched-random controls at the preregistered 10-bar horizon. HMA had one isolated 4-bar result but it did not hold in 2026 and is treated as chance-like.

At raw QF signals, only **KAMA bullish state** survived directionally:
- discovery 2024-25: bull n=159, +2.319% SPY-relative; bear n=42, -0.351%; diff +2.670pp
- 2026: bull n=61, +3.868%; bear n=17, -3.267%; diff +7.134pp

Caution:
- KAMA was selected from ~25 comparisons on this same 30-symbol surrogate.
- bearish 2026 observations cluster into only a few market episodes.
- feature tertiles were noisy/reversing; do not promote KAMA gap/slope/delta rules.
- exact EMA slope and EMA price-distance features are algebraically redundant by construction, not a bug.

Status after Tournament I: **KAMA promising, unproven.**

### C. Full realistic KAMA portfolio test completed, then audited
Original prereg:
`research_notes/KAMA_QF_FILTER_PREREG_20260928.md`

Frozen filter:
- KAMA20 > KAMA40
- ER length = line length
- fast=2, slow=30
- completed QF signal bar only
- no threshold/slope/crossover/gap condition

Realistic portfolio rules used for baseline and KAMA:
- next 4H open;
- realistic gap-through stops;
- minimum actual fill-to-stop distance 1%;
- 1% marked-equity risk budget/trade;
- max single-position notional 100% marked equity;
- max TOTAL gross notional 100% marked equity;
- max 6 open;
- max 5% planned-risk heat;
- rs_top2 ranking, missing RS unrankable/last;
- current TP1 / Profit Protect / runner / timeout unchanged;
- 25/50/75/100 bps costs.

The first run had a warmup defect: missing KAMA on early trades was implicitly treated as bearish, and late-2023 winners contaminated the comparison.

### D. Warmup defect corrected and rerun
Preregistered mechanical fix:
`research_notes/KAMA_WARMUP_CORRECTION_PREREG_20260928.md`
commit `b23c6608afdaa9c744a60ad1bbc53c2c6dbce539`

Code fix:
commit `84cdb34e61fa18204a1c0431d502e95fd507060b`

Corrected run:
- workflow run `36431733499`
- job `108959345907`
- artifact `10973692222`
- result note `research_notes/KAMA_WARMUP_CORRECTED_RESULT_20260928.md`
- result commit `55131eda37c224e9917ef9459b87e626c41d15b7`

Both variants now enforce the frozen **215-bar warmup** and begin on **2024-04-11**.

Primary 50 bps:
- baseline: 149 trades, +0.2815R expectancy, +41.94R total, +57.11% marked return, PF 1.399, DD 13.03%
- KAMA: 130 trades, +0.4047R expectancy, +52.62R total, +73.24% marked return, PF 1.596, DD 13.56%

Trade-set behavior at 50 bps:
- shared: 121
- baseline-only: 28 trades, -0.328R/trade
- KAMA-only from freed capacity: 9 trades, +0.154R/trade

User/independent audit of corrected run:
- 23 KAMA-bearish baseline trades averaged about -0.49R, total about -11.2R.
- month-block bootstrap for bull-vs-bear difference: +0.38R to +1.59R, excludes zero.
- random-removal p≈0.024; month-matched removal p≈0.031.
- KAMA improves every full year (2024/2025/2026).
- KAMA improves total R and return at 50/75/100 bps.
- drawdown is slightly worse at every cost, ~0.5-0.9pp.
- at 25 bps marked return does not improve.
- removed trades cluster; 12/23 are Jul-Oct 2025 and HOOD contributes 5.
- only 3 removed trades are in 2026, so independent holdout support remains thin.
- top-10 removal leaves both negative: ~-0.13R baseline vs ~-0.07R KAMA.

Verdict: **ROBUST ENOUGH FOR FORWARD TEST, SHADOW MODE ONLY.** No live filter.

## 3) KAMA forward shadow is live
Protocol:
`forward_test/KAMA_SHADOW_PROTOCOL.md`
commit `0bd9595f39a71e69f13560e88a6b325eef56debe`

Passive logger:
`forward_test/kama_shadow_watcher.py`
commit `a59cae78346f55502ee29589e4e5815429a18e36`

Workflow:
`.github/workflows/kama_shadow.yml`
commit `af0872d5b6a721dcbe3fbdf6cd503cb5223a3118`

First workflow run:
- run `36433649907`
- job `108965913107`
- success

Published state:
`forward_test/kama_shadow.json`

Frozen shadow rules:
- starts **2026-09-28T13:46:00Z**
- absolutely no historical backfill into primary cohort
- exact KAMA20/40 definition above
- logs every eligible new V5.4 signal
- KAMA cannot affect trades
- 50 signals = data-quality checkpoint only
- first 100 eligible signals = frozen primary cohort
- performance review only after all 100 resolve
- canonical 131 confirmation still required before any live change

Because of the known production 4H clock issue, every signal records:
1. `tested_session_state` = DST-safe 09:30-13:30 / 13:30-16:00 ET bars; PRIMARY research read.
2. `live_grid_state` = current production grid; diagnostic only.

Initial state was correctly 0 signals after start.

Do not tune KAMA while this runs.

## 4) Quality Flow itself remains the larger unresolved question
Do not confuse the corrected 30-name surrogate with canonical proof.

Published canonical V5 @50 bps, $75k:
- expectancy -0.0013R/trade
- win 39.8%
- PF 1.0
- 374 trades
- max DD ~39.8% / -40.7R
- annualized ~-0.4%
- total ~-0.9%
- top-10 concentration is severe
- cost ladder: 25bps +0.1029R; 50bps -0.0013R; 75bps -0.1056R; 100bps -0.2099R

Canonical rerun is still BLOCKED because the current repo/library lacks:
- `canonical_baseline/portfolio_results.json`
- `canonical_baseline/canonical_trades.json`
- `canonical_baseline/simlib.py`
- `canonical_baseline/run_portfolio.py`
- `canonical_baseline/universe.json`
- raw 4H/daily PIT cache

Docs still present:
- `canonical_baseline/ENGINE.md`
- `LONEWOLF_RERUN.md`
- `PIT_FEATURES.md`
- `PORTFOLIO.md`
- `REBASELINE.md`
- `UNIVERSE.md`

Canonical-validation prereg already exists on research branch:
`research_notes/CANONICAL_QF_VALIDATION_PREREG_20260928.md`
commit `94fa6553032143c1f7098835b45aad9696c89e99`

Primary corrected canonical execution in that prereg:
- min 1% actual fill-stop;
- max single position 100% marked equity;
- max TOTAL gross 100% marked equity;
- no stop widening;
- shares = min(risk-budget, single-pos cap, remaining gross);
- actual resulting risk used for heat;
- pending entries reserve risk and notional;
- missing RS = null/unrankable last;
- realistic gap handling;
- primary 50 bps.

Before reconstructing anything: **search Git history, branches and tags for the missing canonical executable/cache artifacts.** Exact reproduction comes before any reconstructed substitute.

## 5) Known DST / 4H bar-clock issue
Production `scanner_rules.resample_closed_4h` uses a pandas resample origin/offset arrangement that can shift winter bars to 08:30/12:30 ET across DST.

Research branch has an explicit per-session wall-clock implementation:
- 09:30-13:30
- 13:30-16:00

Do not silently patch production.
If working on this, use a separate research branch and regression fixtures for summer, winter, half-day, holiday, and bar-close availability. Prove parity/impact before proposing any live change.

## 6) Other important completed diagnostics
Raw QF entry timing:
- run `36376113805`
- 10-bar SPY-relative +1.971% vs matched random +1.142%, p≈0.0639
- suggestive but not conventionally significant
- concentration severe; removing top symbols/events erodes/reverses edge

Position sizing test:
- run `36374572362`
- exposed unrealistic leverage from tiny structural stops
- old raw sim could reach ~9.2x single-position notional and >2.5x total gross
- this is why corrected portfolio screens now enforce min 1% stop and 100% total gross.

## 7) Immediate ACTIVE research task: Trend-Probe Tournament II
Mike explicitly said: **keep going and testing the other ones.**

Prereg already frozen on research branch:
`research_notes/TREND_PROBE_TOURNAMENT_II_PREREG_20260928.md`
commit `411a26ff5f49c78d7af9963f98f407132d0c8b51`

This has NOT been run yet.

Candidates, exact 20/40 only:
- DEMA
- TEMA
- ALMA (offset=.85, sigma=6)
- VIDYA (alpha=2/(n+1)*abs(CMO_n), CMO length=line length)
- FRAMA (standard half-window fractal-dimension estimate; alpha=exp(-4.6*(D-1)), clip [0.01,1])

KAMA is benchmark only, not retuned.

Dataset:
- same DST-safe 30-symbol 4H surrogate
- 215-bar warmup
- discovery 2024-2025
- holdout 2026
- 2023 partial excluded

Study A:
- standalone bullish crossover
- next 4H open
- horizons 1/2/4/6/10/20
- 500 symbol/month matched random non-event draws
- family context = 30 tests; isolated p<.05 is not enough

Study B at raw QF signals:
- bullish fast>slow state
- normalized fast-slow gap
- primary outcome 10-bar SPY-relative return
- discovery/2026 separately
- month-block bootstrap state difference
- discovery tertiles frozen then applied unchanged to 2026

Promotion standard:
- same direction discovery and 2026
- 2026 not tiny-N
- materially distinct from KAMA/EMA
- screening only; nothing goes live from this tournament

### Muse's first action
Implement Tournament II exactly as preregistered on `research/hema-20260927` (or a fresh child worktree), add workflow, run it, save raw artifacts + result note, and post **TEST RESULT** to Bridge issue #1 with commit/run/artifact IDs.

Do not change the prereg after looking.

## 8) Parallel work Muse can do while Tournament II runs
Safe parallel lane:
1. Search all Git history/branches/tags for missing canonical baseline executable/cache artifacts.
2. Report findings only; do not reconstruct until exact recovery attempt is exhausted.
3. If exact artifacts are absent, propose a reconstruction plan against the six canonical docs. Do not execute reconstruction until the plan is reviewed.
4. Leave KAMA shadow untouched except monitoring for failures/data-quality issues.
5. Do not start another indicator family until Tournament II results are reviewed.

## 9) Claude usage
Claude is available again as independent auditor through Mike, not as primary executor.

Use Claude only after a candidate survives our first screen or for major code/parity gates. Preserve Claude's original finding unchanged; resolve disagreements through explicit falsification tests, never silent code changes.

## 10) Communication
Primary bridge: GitHub issue #1, **Quality Flow Research Bridge**.
Use message types:
`PROPOSAL / REVIEW / PASS / MAYBE / FAIL / BLOCKER / KILL / TEST RESULT / DISAGREEMENT / ACTION REQUIRED`

AgentMail thread remains fallback/notification.

## Bottom line
Current state is intentionally asymmetric:
- **KAMA:** frozen, passive forward shadow only.
- **QF core:** canonical edge still unproven; exact canonical rerun blocked by missing artifacts.
- **Active exploration:** Tournament II (DEMA/TEMA/ALMA/VIDYA/FRAMA) is preregistered and ready for Muse execution.
- **Live QF:** no changes.
- **Goal:** faster execution with more automation, without increasing researcher degrees of freedom.
