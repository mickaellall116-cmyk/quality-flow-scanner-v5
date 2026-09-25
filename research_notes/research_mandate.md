# Quality Flow Research Mandate — CONFIRMATORY PHASE (Mike, 2026-09-24)

## Operating directive (Mike, 2026-09-24, 23:00 ET) — SUPERSEDES prior Lane 2 scope

Three tracks, no more, no less:

1. **V5.4 = finish measuring.** Frozen production stays frozen. Paper forward test
   continues to the precommitted checkpoints (~50 signals late Oct 2026, ~100 late
   Nov 2026), judged against ~0R. No patching. No rescuing FVG. No adding selectors.
2. **Lane 2 = one risk-control test only.** The laggard veto (pre-registered at
   `selection_edge/laggard_veto_prereg.md`): exclude bottom-quartile RS3/RS6 signals,
   primary outcome = max drawdown reduction, NOT an expectancy claim. A PASS only
   qualifies it as a candidate for a separate forward paper overlay — never a V5.4
   production change without Mike's explicit approval.
3. **New system = separate design track.** A fresh indicator/system architecture —
   NOT "V5.4 plus more filters." Design only for now; no production changes. When a
   candidate is ready it runs through the exact audit gauntlet that exposed V5.4
   (PIT universe, realistic execution, costs, portfolio replay, placebo, walk-forward,
   concentration) before any forward-test consideration.

All other backlog ideas are PARKED until further notice. No new edge-hunting branches.

## Standing operating instruction — multi-agent research loop (Mike, 2026-09-25)

**Roles.** Muse = primary research executor and builder. ChatGPT = research architect and adversarial reviewer. Claude = independent replication/code auditor. Mike = final decision-maker.

**Communication.** The live research mailbox is **quality-flow-research@agentmail.to** — the active Muse ↔ ChatGPT loop runs through it. Muse emails ChatGPT when a meaningful study finishes, on hitting a blocker, finding a bug, needing review, or having a new candidate idea — and reads and responds to ChatGPT's replies directly. **Claude cannot join the mailbox** (organization/Microsoft permission restrictions) and serves as an independent external auditor at major gates only: pre-validation specification audits, independent replication of promising results, code/execution parity audits, final review before a candidate enters forward testing. Mike manually provides Claude with frozen specifications/results; Claude's audit comes back through Mike (via ChatGPT) to Muse. Do not wait for direct messages from Claude; never assume Claude can email, commit to GitHub, or respond inside the shared bridge. A Claude audit received via ChatGPT is treated as an independent verification artifact. **Disagreement protocol:** (1) preserve Claude's original finding unchanged; (2) never silently modify the study; (3) respond with evidence and implementation details; (4) ChatGPT defines the specific falsification test needed to resolve the disagreement; (5) any resulting protocol change is recorded as a new amendment before further testing. GitHub remains the permanent research record: preregistrations, code, reports, failed tests, final decisions. (Structure updated per Mike, 2026-09-25; first exercised by Claude's blind pre-validation audit of ERD v0.1 → Amendment 1.)

**Bridge protocol (per Mike, 2026-09-25; GitHub-primary since ~18:50 EDT).** Standing issue `mickaellall116-cmyk/quality-flow-scanner-v5#1` ("Quality Flow Research Bridge") is the primary channel — conversation and evidence live in the same place. Muse posts via commits to `research_notes/bridge_thread.md` (its GitHub token can create issues and read comments but cannot post issue comments — scope limit); ChatGPT replies as issue comments; Muse's `research-bridge-watcher` cron (every 10 min, script `research_notes/bridge_watcher.py`) polls both the issue comments and the Gmail fallback thread and surfaces new ChatGPT messages. Message types: PROPOSAL / REVIEW / PASS / MAYBE / FAIL / BLOCKER / KILL / TEST RESULT / DISAGREEMENT / ACTION REQUIRED. The AgentMail email thread (subject `QUALITY FLOW — AGENT RESEARCH BRIDGE`) is fallback/notification only. ChatGPT's AgentMail outbound was blocked 3x on 2026-09-25 by auto bounce-suppression (org-level send-block on the recipient) — fix is on ChatGPT's side via the Lists API (GET/DELETE `/v0/lists/send/block/mickaellall116@gmail.com`); until confirmed cleared, Mike's relay stays authoritative.

**Workflow.**
1. Brainstorm with ChatGPT before coding.
2. Narrow to one falsifiable idea.
3. Freeze the preregistration before looking at results.
4. Commit the preregistration to GitHub.
5. Run the study: PIT data, realistic execution, realistic costs, full portfolio replay.
6. Send complete results to ChatGPT for adversarial review.
7. If still promising, Mike provides the frozen spec/data/code to Claude for independent replication (Claude cannot join the research mailbox — org/Microsoft restrictions; relayed via Mike).
8. Resolve disagreement through a specific falsification test — never by silently modifying the study.
9. Only candidates surviving Muse validation + ChatGPT review + Claude verification may move to forward testing.
10. No production change without Mike's explicit approval.

**Current standing status (Mike, 2026-09-25).** V5.4 frozen, forward measurement only. FVG-as-entry closed. Lone-wolf sector RS closed. Laggard veto closed. Universe-selection factor mining closed. ADX not a proven standalone edge. ERD v0.1 is the current fresh-system candidate — frozen, lab-only, waiting on clean PIT data (Intrinio/Zacks EPS Surprises; Norgate first choice, Intrinio EOD fallback). No hand-picked watchlist optimization. Portfolio-level replay mandatory for every serious test.

**When no study is active:** use the email thread to brainstorm with ChatGPT about genuinely different fresh architectures, or to improve data-validation/reproducibility infrastructure.

**Goal (not negotiable):** do not optimize toward producing a good backtest. Find an edge that survives attempts by all three agents to break it.

## Standing lessons (earned, not assumed)

- **Portfolio-level replay is mandatory for every candidate, every time.** The laggard-veto test (FAIL, 2026-09-25) proved why: the veto correctly identified toxic trades, but slot/heat reshuffling admitted worse replacements — the damage is invisible without the full replay. No more veto/filter rescue attempts on V5.4; that branch is closed.
- **ERD v0.1 frozen as pre-registration 2026-09-25** (`new_system/DESIGN.md`): bare-event Earnings Reaction Drift, locked data sources (Intrinio/Zacks EPS Surprises; Norgate first choice, Intrinio EOD fallback), no-substitution rule on the earnings calendar, lab-only. Validation begins once the sources are available in the lab.
- **Candidate-family multiple-testing ledger (adopted 2026-09-25, Mike's decision — research governance, no production impact).** Closes the researcher-degrees-of-freedom risk: after enough architecture experiments, one can look exceptional by chance. Rules: every distinct economic hypothesis gets one frozen family_id at inception; parameter variants, feature substitutions, universe changes, and reformulations stay inside that family — they are not new hypotheses. Every portfolio replay is logged in the family, including failures and abandoned variants — nothing is dropped. Only the preregistered primary specification can establish the result; the best-performing variant cannot quietly become the new primary. Once results have been inspected, another attempt at the same family requires genuinely new forward/holdout data, never recycling the same history. Portfolio-level replay, displacement accounting, concentration checks, and placebo controls remain mandatory. Initial families: FAM-V54 (frozen, forward measurement only), FAM-ERD (frozen, lab-only, pre-data), FAM-LAGGARD-VETO (killed 2026-09-25), FAM-FVG-ENTRY (closed), FAM-LONEWOLF-RS (closed), FAM-ADX-STANDALONE (not proven), FAM-UNIVERSE-FACTOR-MINING (closed).

Standing mandate. Research only — do NOT modify the frozen V5.4 production system.

## Phase change (2026-09-24)
Broad exploration is COMPLETE. All 15 exploration priorities were measured on the night of Sep 24–25. The main job is now to determine which of the current candidate edges are real enough to survive forward validation.

**Final rule:** The goal is no longer "find more features." The goal is: prove or kill the strongest candidate edges, determine whether they are independent, and preserve V5.4 untouched until forward evidence justifies a future version.

## Current benchmark
- 4H Hybrid baseline: +0.239R/trade, 237 trades, 50.6% win rate, PF 1.38, 25 bps costs, Oct 2023–Sep 2026
- Watchlist: QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX, ASTX, BBAI, NIO, HOOD, AMD

## Canonical testing protocol (Mike, 2026-09-24) — applies to EVERY candidate edge, every time

The point: stop getting seduced by pretty backtests. Same sequence, no exceptions.

1. **Pre-register before running.** Write down: hypothesis, exact rule, baseline, date range, symbols, costs, and what counts as PASS/MAYBE/FAIL. No changing the rule after seeing results.
2. **Same trade population first.** Compare against the baseline signals generated on the same dates and names. Isolates the effect instead of accidentally comparing different universes.
3. **Split development from validation.** Development: Oct 2023–Dec 2024. Validation: Jan 2025–Sep 2026. Once the rule is defined on development data, do NOT retune it on validation.
4. **Rolling walk-forward.** Train/observe 12 months, test next 6 months, roll forward 6 months, repeat. Combine only the untouched test windows at the end.
5. **Year and regime splits.** Show the edge in 2023, 2024, 2025, 2026 separately — not just pooled. Also bull / sideways / high-volatility / weak-market conditions where observations suffice.
6. **Cost stress automatic.** Every test shows 25, 50, 75, 100 bps. If the edge disappears with modest friction, it's weak.
7. **Perturb the parameter — don't optimize it.** Rule uses 20-day RS → test 15/20/25. We don't care which is best; we care whether the general idea survives nearby settings.
8. **Concentration check.** Report how much of the improvement came from the best 1, 3, and 5 stocks, sectors, and years. If removing one ticker kills the edge, red flag.
9. **Bootstrap the trades.** Randomly resample trade returns thousands of times; show the distribution of expectancy and drawdown. Is positive expectancy typical, or is the observed result a lucky tail?
10. **Leave-one-symbol-out.** Rerun removing one ticker at a time. A robust edge shouldn't collapse because one name is removed.
11. **Economic effect, not just statistics.** For each test show: Δ expectancy, Δ PF, Δ drawdown, trades removed/added, opportunity cost, return per unit of risk.
12. **Paper it forward untouched.** Once a candidate gets MAYBE/PASS, freeze that exact version. No tweaking while live data comes in.

**Ablation after every winner.** If a combination works (e.g. FVG + lone-wolf), remove each component one at a time. If the combined result is good but neither component independently contributes, that's an interaction or an overfit — not two real edges.

**The standard:** an idea should survive different years, nearby parameters, higher costs, removal of individual symbols, and untouched forward data. If it only survives one exact backtest configuration, kill it.

## Project reframe (Mike, 2026-09-24) — the question changed

V5.4 as currently defined does not have a demonstrated historical edge (−0.0013R at 50bps RT). The old +0.239R was mostly the hand-picked universe + weaker execution assumptions.

- **V5.4 baseline = control system**, not ready for real-money deployment.
- **Forward test = continue to ~50 signals** — genuinely unseen evidence, judged against ~0R.
- **Lane 2 research priority = stock-selection / universe-selection edge**, using only point-in-time information. The question is now "can we systematically identify the subset of stocks where Quality Flow actually works?" — not "does Quality Flow have a big entry edge?"
- **Blinding rule (hard):** the 14 names must NEVER be used during rule construction, factor selection, or tuning. They may appear only as a final reporting overlay AFTER a rule is frozen — never as a gate, never as training data.
- Candidate selection-factor families: relative strength/momentum, earnings growth/revisions, liquidity/dollar-volume change, volatility expansion, sector leadership, price acceleration, institutional momentum proxies. Each pre-registered, each through the 12-step protocol, on the PIT universe.
- **Deferred production change (approved in principle, NOT done):** fix gap-through-stop to fill at the open beyond the stop. Separate change, never silently folded into V5.4. Awaiting Mike's go-ahead to implement.

## Two-lane operating mode (Mike, 2026-09-24)

Edge hunting is NOT the priority until the baseline is trustworthy — but it doesn't stop completely.

- **Lane 1 (highest priority):** fix the baseline. One canonical backtest of the exact frozen V5.4 Mode B system: point-in-time universe, faithful Mode B execution, strict PIT features, round-trip costs, portfolio realism. Until this is done, no new edge is measured against the old distorted baseline.
- **Lane 2 (background):** keep discovering and logging new edge hypotheses, but DO NOT declare any new PASS, do not recommend production changes, and do not trust results until hypotheses are retested on the corrected framework. Log: hypothesis / mechanism / reason noticed / test sketch. The queue waits for the clean baseline.

Instruction to Research: "Keep discovering and logging new edge hypotheses, but do not declare any new PASS or recommend production changes until the corrected point-in-time Mode B baseline is complete. Once the framework is fixed, retest the strongest new ideas against that clean baseline."

## Research stack — source of truth (Mike, 2026-09-24)

- **Python scanner/backtester** (`pine_backtest`, imported unmodified): ALL research. FVG tests, lone-wolf filter, ADX ranking, walk-forward, bootstrap, costs, drawdown. This is where thousands of historical bars are replayed, costs controlled, variants compared, expectancy measured consistently.
- **TradingView V3.7 indicator:** parity check ONLY — confirm the Pine signal matches the scanner on the same bar. Never the research benchmark. Strategy Tester results are not execution-realistic and do not count.
- **Forward test:** live paper validation, only after the Python research survives.

Instruction to Research: "Run these studies against the canonical Python V5.4 backtest/scanner logic. Do not use TradingView strategy tester results as the research benchmark. Use Pine only for parity verification."

## Candidate edges (priority order)

### 1. Lone-wolf sector-RS overlay — HIGHEST PRIORITY
Current: skip entries where stock RS > 0 but sector RS ≤ 0 → +0.108R pooled, +0.144R out-of-sample, improved all 3 years, flipped 2026 positive, DD 21.6% → 18.9%, broad across 12 symbols, survives 50/100bps. Weakness: 10d and 40d lookbacks failed while predeclared 20d worked.
- Research task: determine whether this is a real structural effect or a 20-day lookback accident.
- DO NOT optimize for the best lookback. Test only a small, PREDECLARED family of nearby formulations: 15d, 20d, 25d, simple slope/continuous versions if justified.
- Report: expectancy, PF, DD, yearly consistency, symbol concentration, cost sensitivity, walk-forward, whether the effect remains directionally present even when weaker.
- Main question: is "stock strength without sector participation" genuinely lower quality?
- Verdict only: PASS / MAYBE / FAIL.
- Live: paper overlay on forward test (`v54_lonewolf_overlay.py`, hourly cron `lonewolf-overlay-cycle`), verdict at ~50-signal checkpoint late Oct 2026.

### 2. FVG-as-entry — MAYBE
Current: +0.285R vs +0.239R baseline. Paper sidecar live since 2026-09-23.
- Research task: determine exactly where the improvement comes from. Break into: better entry price, avoided losers, changed trade selection, different stop geometry, sector/symbol concentration, regime dependence.
- Run matched-trade attribution and walk-forward analysis. Do NOT search for a better FVG threshold.
- Main question: is FVG improving trade quality, or merely changing the sample?

### 3. ADX-based ranking — MAYBE
Current: ADX ranking +0.314R vs +0.160R current ranking in test; existing rs_top2 LOST to take-all (+0.221R) on the 14-name watchlist.
- Research task: test whether ADX is genuinely a better crowded-signal ranking factor. Compare: take-all, current RS ranking, ADX ranking, simple RS+ADX combination ONLY if each factor independently holds up. Same signal population.
- Report: expectancy, opportunity cost, max DD, concentration, yearly breakdown, crowded bars only, out-of-sample.
- Main question: when portfolio slots are limited, does ADX select better trades consistently?

### 4. Interactions between the three candidates
ONLY after the individual tests are complete, test whether the strongest candidates are additive. Examples: lone-wolf + existing ranking, FVG + lone-wolf, FVG + ADX ranking. Do NOT test a large grid of combinations. Use only combinations where BOTH components independently survived.
- Main question: are these independent edges, or are they describing the same underlying market condition?

### 5. Exit diagnostics — frozen until ~50-signal checkpoint (late Oct 2026)
Do not change exits now. At the checkpoint, analyze: MFE after TP1, giveback on runners, time to TP1, time to stop, Profit Protect effectiveness, 30-bar timeout behavior, stop-vs-TP1 same-bar cases, whether runner exits are leaving meaningful R on the table. Only then propose ONE exit experiment at a time.

## Forward-test scoreboard
Maintain a simple live scoreboard for: V5.4 baseline, FVG sidecar, lone-wolf overlay, ADX ranking shadow result if feasible.
For each: signals, closed trades, expectancy, win rate, PF, max adverse excursion, max favorable excursion, missed winners, avoided losers, current sample-size warning.
Do NOT declare a winner from a tiny live sample.

## Research discovery going forward
Do NOT return to random indicator testing. New ideas come ONLY from: unexplained winner/loser differences, forward-test failures, regime-specific weakness, portfolio-selection inefficiency, execution slippage, recurring exit inefficiency, externally sourced claims with a clear mechanism.
For every new idea: (1) state the mechanism, (2) state the test before running it, (3) define the win gate, (4) use realistic costs, (5) check nearby parameters, (6) check multiple years/symbols, (7) report PASS / MAYBE / FAIL, (8) keep production frozen.

## Do NOT retest unless new evidence appears
1H, 2H, daily transfer, generic mean reversion, shorts, inverse ETFs, hedge overlays, volume filters, chase filters, gap filters, portfolio heat filters, generic time/calendar effects, scanner/Pine agreement filters, broad universe expansion. These already failed or lacked enough evidence.

## Anti-overfitting rules (unchanged)
Every idea must: have a plausible mechanism; be specified before looking at results; use few parameters; avoid exhaustive parameter searches; survive nearby parameter values; work across multiple symbols; work across multiple years/regimes; survive realistic costs; have enough trades to matter; improve expectancy, drawdown, or portfolio efficiency materially. Small improvements = noise unless replicated. Do not combine weak discoveries into a complex model because the combined backtest looks better.

## Research gates (unchanged)
- PASS: meaningful improvement, broad across periods/symbols, survives costs, survives perturbation, mechanism makes sense, no obvious concentration.
- MAYBE: promising result, insufficient sample or regime coverage, needs forward validation.
- FAIL: improvement disappears out-of-sample, depends on a few symbols/one year, requires precise parameters, worsens drawdown materially, fails cost stress.

## Reporting format (unchanged)
Hypothesis / Mechanism / Baseline / Variant / Trade count / Expectancy / Win rate / Profit factor / Max DD / Cost sensitivity / Year-regime breakdown / Symbol-sector concentration / Out-of-sample result / Why it worked or failed / PASS-MAYBE-FAIL / Recommended next experiment.

## Exploration archive (completed Sep 24–25, 2026)
P1 FVG validation → MAYBE. P2 ranking → ADX MAYBE; rs_top2 loses to take-all on watchlist. P3 correlation → CORR_07 MAYBE; max-2-per-theme never binds. P4 regimes → NO. P5 volatility → NO sweet spot; dead-markets follow-up MAYBE (weak). P6 chase → FAIL. P7 setup age → NO. P8 volume → NO. P9 gaps → NO. P10 sector-RS → MAYBE (strong) → lone-wolf filter. P11 breadth → NO. P12 heat → NO (regime proxy). P13 sequencing → NO edge decay, NO re-entry penalty; overlap MAYBE (weak). P14 time → NO. P15 exits → diagnostics only. Plus: pullback-entry timing no edge; stale-FVG clean kill; breakout-retest reel test → no edge (97% retest within 1 bar).
