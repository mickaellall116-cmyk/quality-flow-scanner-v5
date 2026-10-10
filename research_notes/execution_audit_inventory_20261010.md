# Entry/Exit Execution Audit — Completed-Work Inventory

**Date:** 2026-10-10
**Assignment:** Bridge #1 comment 5964633446 (2026-10-03) — inventory ALL completed entry ablations, MFE/MAE diagnostics, exit tests, 2022 stress results, and execution audits before inventing anything new.
**Method:** read-only. No reruns, no vendor calls, no code changes. All commit hashes verified via `git cat-file -t`.

## Completed experiments

| # | Name | Date | Commit | Key paths | Disposition | One-line verdict |
|---|---|---|---|---|---|---|
| 1 | V5.4 research verdict | 2026-10-03 | — (Mike's call, memory record) | `~/MEMORY.md` "V5.4 research verdict" | **FAIL** (closed) | Corrected C1: 240 trades, +0.178R @4bps — FAILS preregistered 25bps bar (bull +0.079R < 0.15R, Calmar 0.29 < 1.0; 2022 leg passes). Entries paused. |
| 2 | Canonical re-baseline (honest V5.4) | 2026-09-24 | — (memory `2026-09-24.md`) | `workspace/your_files/trading-handover-2026-09-24-rebaseline.md` | **FAIL** (adverse) | Honest V5.4 = −0.0013R/trade @50bps RT (374 trades, PF 1.00). Old +0.239R → delta −0.240R. Decomposition: universe −0.351R / costs −0.131R / gap realism −0.038R / portfolio +0.116R / Mode B +0.054R / entries+PIT +0.041R. |
| 3 | numpy-boolean trendScore bug (C1 ledger forensics) | 2026-09-28 | `497c603`, `1419d61`, `10f0fb3` | `pine_execution/C1_LEDGER_FINDINGS_2026-09-28.md` | **DISQUALIFIED** | 143-trade/+0.337R baseline was a bug artifact (`np.bool_+np.bool_` collapsed the 0–5 trendScore; `confirmed`/`ready_buy` were dead code). Corrected: 240 trades, +0.178R. No per-trade ledger exists for either version. |
| 4 | Corrected-grid replay | 2026-10-03 | — (bridge record) | `research_notes/bridge_thread.md` (E2 figures, Claude-verified) | **ADVERSE** | −15.23R (zero-cost). Methodology documented, not independently rerun. Preserved as adverse evidence — never tuned away. |
| 5 | Candle failure forensics + parity fix | 2026-10-03/04 | — (bridge record) | `research_notes/candle_gap_report_20261004.md` | **FAIL→FIXED** | Live ran 06:30/10:30/14:30 ET candles vs backtest 09:30/13:30 (`origin='start_day'` anchored to UTC midnight). Session-anchored fix verified 42/42 across DST + window lengths. Parity gate now mandatory pre-launch. |
| 6 | TOP-vs-BROAD (TOP-50/quarterly/composite) | 2026-10-04 | `68a7a0b` (KILL), repro `3b60557`, results `df79558` | `research_notes/killed_top50_branch_20261004.md`, `research_notes/top_broad_repro_comparison_20261004.md` | **KILLED** (Mike) | TOP +0.002R vs BROAD −0.091R @25bps — missed preregistered +0.10R differential; TOP ≈ zero expectancy. Bit-for-bit repro confirmed. No retuning (cutoff/interval/weights/S4). |
| 7 | Laggard-veto risk control | 2026-09-24/25 | `5b4dc56`, `fd0db61` | `selection_edge/laggard_veto_prereg.md`, `selection_edge/laggard_veto_report.md` | **FAIL** (closed) | Veto worsened DD −51.88% → −70.10% and expectancy −0.1186R → −0.2388R. Replacement-trade effect: dropped 167 baseline trades, admitted 84 replacements @ −0.31R. |
| 8 | Universe-selection study (12 factors) | 2026-09-24 | `fd0db61` | `selection_edge/SELECTION.md` | **FAIL** | 11/12 factors FAIL outright; RS6 (only monotonic, top bucket +0.044R) killed by placebo (56.8th pct, P=0.43). Mechanism: laggard toxicity, not strength selection. |
| 9 | Trend-Probe Tournament II (MA crossovers) | 2026-09-28 | branch `research/hema-20260927` | `research_notes/TREND_PROBE_TOURNAMENT_II_RESULT_20260928.md` (on branch), `research_notes/bridge_thread.md` | **FAIL** (all five) | DEMA/TEMA/ALMA/VIDYA/FRAMA: no crossover beats random (p 0.93–0.998); state/gap diagnostics flip sign across periods. KAMA benchmark "promising, unproven" (CI includes zero). |
| 10 | BOSWaves long-only daily (v3 rerun) | 2026-10-04 | `1946e74` (v5 correction pkg; v3 freeze in pkg) | `research_notes/boswaves_correction_v3/` | **FAIL / protocol-INCONCLUSIVE** | +0.199R @25bps (above 0.15R bar), clustered t=+3.45 — but Calmar 0.35 < 1.0 (drawdown-shape FAIL). Coverage-gate gap (388/831 symbols missing) → held for November full-831 rerun, not closed, not promotable. Severe tail dependence (top-5% removal flips negative). |
| 11 | SA-VWAP long-only daily | 2026-10-03/04 | — (bridge record) | `research_notes/bridge_thread.md` (2026-10-01 work result) | **SECONDARY** | +0.041R @50bps (t=1.4) — "not statistically distinguishable from zero." Less cost-resilient than BOSWaves. |
| 12 | ORB 15m random benchmark | 2026-10-07 | `838bb89`, `e360a94` | `research_notes/orb_15m_random_benchmark_20261007.md`, `research_notes/orb_15m_random_benchmark_20261007/` | **HOLD / WITHDRAWN** | Random null did not match ORB entries' realized risk distance — not apples-to-apples. Timing-edge claims withdrawn. No rerun until estimand + matched null frozen. |
| 13 | 3H hybrid forward baseline | 2026-09-26 | `668282c` | `research_notes/3h_hybrid_forward_baseline_2026-09-26.md` | **RESEARCH ONLY** | Zero forward-window signals — gate not evaluable. Full-window repro matched historical (+0.158R @25bps, 371 trades). Not approved, not deployed. |
| 14 | Capitulation-harami claims test | 2026-09-2x | `a9fcdc7` (bridge log) | `pine_claims_capitulation_harami/` | **FAIL** | 15 trades, −0.049R vs in-study baseline 237 trades +0.239R. Trigger fires ~13% of the time. |
| 15 | 60-bar correlation >0.7 admission filter | 2026-09-24 | — (memory `2026-09-24.md`) | memory only | **MAYBE** | +0.049R improvement (+0.321R vs +0.272R), held OOS (+0.041R) — but thin (28 trades blocked), no DD reduction. Paper-overlay validation recommended, never run. |
| 16 | Lone-wolf (no-portfolio) variant | 2026-09-24 | — (memory `2026-09-24.md`) | memory only | **REMOVED** | Corrected lone-wolf HURT: −0.0013R → −0.1746R, DD → −63.8%. Earlier PASS overturned. |
| 17 | QF-R2 breakout+volume prereg | 2026-10-04 | `b4ba924` | `research_notes/qf_r2/qf_r2_brk_vol_4h_prereg_20261004.md` | **HELD** (not executed) | Preregistered only. Performance held until pre-run checks pass. |
| 18 | FVG prereg rev 2 | 2026-09-2x | `83427fa`, `922d90d` | bridge record | **HELD** (not executed) | Frozen prereg; execution held, ChatGPT spec review requested. |
| 19 | VCP Phase 1A | 2026-10-07/08 | `48c064f`, `8c8b711`, `9bd6526`, `ebaba82`, `fb9fff9`, `7cfb649` | `research_notes/vcp_1a_*` | **HOLD** (until Nov) | Repair chain closed (interval fix scoped PASS). October partial invalid for inference. One full-universe November run planned; preflight gate queued `QF-VCP-1A-NOV-INTERVAL-PREFLIGHT-20261101-07`. |
| 20 | PR #7 stale-fill protection | 2026-10-0x | `76cf0a0` (merge), `b6303e7`, `246f778`, `62b95b2` | `forward_test/` | **MERGED** | Execution hardening (canonical `bar_close_at()`, timing-state void for stale single-bar fills). Not a strategy change. |
| 21 | EDGAR 10-event pilot (ERD feasibility) | 2026-09-30 | — (memory `2026-10-03.md`) | `workspace/goals/erd-50-event-timing-audit/hidden_files/edgar_pilot_package_20260930/` | **FAIL** | 0/9 announcement-time pairs retrieved. ERD stays HOLD. |
| 22 | Research-loop scaffold v1–v1.2 | 2026-10-07 | `39f5a8f`, `65e75ca`, `6f9595a`, `a878157` | `research_notes/research_loop/` | **PASS** (closed) | 28/28 fixtures; scoped PASS (6048657174). Single-process scaffolding, not a live scheduler. |

## 2022 stress legs (within studies, not standalone runs)

| Study | 2022 leg result |
|---|---|
| Corrected C1 (E2) | **2022 +0.140R** — the one leg that passes (Claude-verified) |
| BOSWaves long-only daily | 2022 −0.069R (flat, not blown up); green 15/18 years |
| SA-VWAP long-only daily | 2022 −0.320R; green 14/18 years |
| BOSWaves/SA-VWAP short-only | Structural losers: −0.261R / −0.163R, negative 14–16 of 18 years |

## MFE/MAE diagnostics (status)

- **Planned, not run:** the MFE/MAE diagnostic is parked for the ~50-signal forward-test checkpoint (late Oct 2026) on real forward data — per Mike's research sequence (2026-09-18). Hypotheses H2 (shakeout-clip), H3 (30-bar timeout), H4 (Profit Protect) in `research_notes/idea_backlog.md` are the queued diagnostic sketches — all UNTESTED.
- **Existing fragments:** laggard-veto report notes MAE on early forward stops (4 early stopped-out trades, worst MAE −1.865R); idea backlog H2 cites 91% intrabar stop-touch rate on bars closing above the stop (execution audit §2, conservative replay).

## Exit-variant tests (status)

- **No standalone exit experiment has ever been run.** Exit research is closed per Mike's sequence (2026-09-18) unless live evidence shows stops clipping winners or large uncaptured MFE.
- Mode B exit stack (50% TP1, +1R Profit Protect, structural stop, 30-bar max hold) is the frozen forward-test configuration — its components have never been ablated against each other.

## Do-not-repeat list (dead ideas with disqualifying evidence)

1. **TOP-50 / quarterly / liquidity+RS composite universe filter** — KILLED 2026-10-04 (Mike). Adjudicating run: TOP +0.002R ≈ zero expectancy; missed the +0.10R differential gate. Bit-for-bit repro confirmed (`68a7a0b`). Frozen prohibition: no retuning cutoff/interval/weights/S4; revival needs new held-out evidence or a materially different preregistered hypothesis.
2. **Laggard veto (bottom-quartile RS3/RS6 exclusion)** — FAIL 2026-09-25 (closed per Mike). Worsened max drawdown 35% relative (−51.88% → −70.10%) and expectancy −0.1201R. Lesson: candidate-stage filtering reshuffles slot/heat competition; replacement trades (−0.31R avg) swamp the benefit. Judge filters inside the portfolio stack, never on isolated expectancy.
3. **The 143-trade / +0.337R C1 baseline** — DISQUALIFIED 2026-09-28. numpy-boolean trendScore bug made `confirmed`/`ready_buy` dead code; only `breakout_buy` fired. Never cite as a baseline, gate, or comparator (`497c603`, `1419d61`, `10f0fb3`).
4. **MA-crossover trend probes (DEMA, TEMA, ALMA, VIDYA, FRAMA)** — FAIL 2026-09-28, closed on the dataset. No crossover beats random (p 0.93–0.998); state/gap diagnostics flip sign across periods. Second attempt needs genuinely new/held-out data, not retuned parameters.
5. **Short-side daily equity systems** — structural loser across three independent readings (BOSWaves short −0.261R, SA-VWAP short −0.163R, negative 14–16 of 18 years). Long-only is the only surviving direction on daily bars.
6. **Tuning the corrected-grid replay loss (−15.23R)** — adverse evidence, preserved per the 2026-10-03 standing rule. Fitting the loss period is overfitting with extra steps; improvements are built on separate learning data and proven on untouched testing data.
7. **Capitulation-harami entry trigger** — FAIL (15 trades, −0.049R vs +0.239R baseline). Thin sample; mechanism (13% trigger rate) explains it.
8. **ORB 15m "timing edge" claims** — WITHDRAWN 2026-10-07. Random null mismatched realized risk distance; claims ("real," "not luck," "robust") removed from the record. No rerun until the null design is fixed.

## Standing prohibitions carried forward

- No retuning of any killed/failed branch on its own results (TOP-vs-BROAD, laggard veto, MA probes).
- Revival of a FAIL/KILL record requires a NEW experiment ID with genuinely new held-out/forward evidence or a materially different preregistered hypothesis (failure-memory rule).
- Permission to run ≠ positive verdict. Verified losses are evidence, not embarrassment.
- Mike decides: relayed authorization is a proposal until his authority is directly established.
