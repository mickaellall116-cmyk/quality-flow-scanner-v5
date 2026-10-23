# QF-EQUITY43-DEV-ORDER-CENSOR-20261023-13 — RESULT

**Verdict: SUCCESSOR PREFLIGHT PASS — the single preregistered 43-name W_DEV exploratory run was executed exactly once under the pinned successor configuration, with a byte-identical deterministic replay.** All headline figures are labeled, verbatim: **EQUITIES-ONLY DEV EXPLORATORY / G4 UNADOPTED / NOT VALIDATED EDGE** — they are a development-window exploratory on candidate-grade inputs, not a validated edge, and they do not touch the frozen C1 FAIL, the sealed W_HO, or original UX51.

Authority: ChatGPT independent adjudication, Issue #1 comment 6375433659 (Slack TS 1792792161.768269), successor to -12 STOP_PREFLIGHT (package `861f5e2`). **The -12 record is immutable**: it was not re-run, edited, or silently superseded — this is a new, versioned experiment (`QF-EQUITY43-DEV-ORDER-CENSOR-20261023-13`, config sha256 `87b8285a522ba0e3…`, frozen in the driver before any run). Single-dispatch check was CLEAR. OFFLINE throughout (driver under `unshare -n`); 0 new vendor calls / 0 credits (program TD total stays 115 desk); W_HO sealed (HO files touched only as SHA256SUMS hashes and receipt-chain metadata); SMCI pre-declared EXCLUDED, never fabricated or imputed.

## The two adjudicated repairs (and nothing else)

1. **Canonical-order pin (Ruling A).** Candidate processing order is frozen as `(symbol, signal_idx)` ascending, applied to the candidate list before BOTH simulator paths. Strategy rules, caps, exits, and every frozen parameter are byte-unchanged (all strategy source files at their -12 pins); the successor engine deltas are confined to accounting inside `simulate_portfolio` / `simulate_stack` (successor pins: pine_backtest `874d2a9b…`, pine_stack `8d4a964f…`).
2. **Right-censored terminal-candidate treatment (Ruling B).** A position still open at the last bar is emitted as a candidate with `censored=true`, `exit`/`exit_time` null, carrying only terms known at signal time. It enters the identical time-local rank/cap/sector/risk selection; if taken it is held to the W_DEV cutoff (2026-10-16 17:30 ET) and valued in equity at the last-completed-bar as-of mark; if skipped it is ledgered with its exact gate reason. **No exit, cash flow, forced liquidation, or trade R is fabricated for it, and selection never uses knowledge of its future exit.**

## Gate matrix

| Gate | Verdict | Evidence |
|---|---|---|
| P0 pins & integrity | **PASS** | Successor engine at its new pins; pristine -09 fork byte-identical to -12 (pine_backtest `becea082…`, pine_stack `30594231…`, asof `f0f4582c…`); frozen originals at pins; session table `00c5555c…`; fresh clone of qf-data-archive@`bb644db` (clone head == remote head): SHA256SUMS 158/158 + 22/22, 0 mismatches. PAUSED pins identical before AND after (harness `ce7c902c…`, PAUSE present, RESUME absent). Experiment config pin recorded. |
| P1 receipt chains | **PASS** | Child root recomputed = `c5628652…` MATCH; parent = `ca498920…` MATCH; full child chain re-walked from GENESIS: **54/54 receipts**; 23 receipt-less legs = exactly the quarantined HO legs; pilot DEV receipts field-verified (root `79ccdd12…`). |
| P2 G1–G6 (DEV legs) | **PASS — 43/43** | Identical to -12 on identical bytes: admitted == pinned expected exactly (3,653/leg); 61 excluded rows, all in the generic early-close post-close class; zero zero-volume admitted bars. **PFE ruling carried**: the 2024-12-24 14:30 row excluded under the same generic pinned-session rule (stamp-value-agnostic, no whitelist); PFE/DEV admitted at 3,653. **G4/VBASIS carried disclosed, NOT waived** (CONVENTION_BREAK_SUSPECT, UNADOPTED; inputs candidate-grade, NOT QUALIFIED). |
| P3 fixture replay | **PASS** | -09 suite replayed on three trees: original exit 1, **0/5 hold** (defects reproduce); pristine fork exit 0, **5/5 hold**; successor engine exit 0, **5/5 hold** (treatment deltas regress nothing). -13 censoring fixture: frozen construction **4/8, exit 1** (terminal candidate silently dropped — no disposition, no inventory, mark never reaches equity); successor **10/10, exit 0** (taken-and-marked, rejected-with-reason, cross-path agreement, permutation invariance — all on invented prices). |
| P4 grid & aggregation parity | **PASS — 43/43** | 1,043 4H bars/symbol == pinned table; independent re-aggregation incl. SessionVWAP: **0 bad bars on 44,849**. |
| P4 candidate parity & generation | **PASS** | Successor closed generation field-identical to frozen `gen_candidates`: **586 closed candidates, 0 parity failures** vs frozen formulas; skipped_gap_below_stop = 1. The censored generator reproduces the -12 census **field-by-field** (symbol, signal_idx, entry, stop, TP1, tp1_hit, entry_time, last close): exactly **CRM 1041, SHOP 1029, MRNA 965, PFE 1035**. As-of liveness: rs differs midnight-vs-as-of on 586/586 closed candidates. |
| P4 C0 fidelity, trade-by-trade | **PASS** | On the canonical 590-candidate list under the pin, successor control vs successor stack agree **exactly** (tolerance 1e-9): identical taken sequence (193), identical per-trade risk dollars, **190 exit cash flows compared, 0 differences**, cap skips 323 = 323, risk skips 74 = 74, per-candidate dispositions identical, terminal inventory identical, final equity **12,321.3876 = 12,321.3876**. Equity decomposition identity holds to 0.0 in both paths: final = realized + Σ terminal marks. |
| P4 permutation invariance | **PASS** | Seeded shuffle (seed 20261023) → canonical pipeline → both paths reproduce the base result with 0 diffs; the stack fed the raw shuffled list also reproduces it exactly. |
| P4 terminal-open guard (C0) | **PASS** | See table below — both paths return the identical disposition for each of the four, and every taken one is in terminal inventory with its mark reconciled into equity. |
| P5 the one run + replay | **EXECUTED** | Below. In-driver second execution byte-identical; two full independent driver executions produced byte-identical `results.json` and `trade_ledger.json`. |

## Terminal-open guard — the four candidates (preflight, C0 configuration)

| Candidate | Disposition (both paths, identical) | Mark at cutoff | Unrealized $ in equity |
|---|---|---|---|
| CRM (idx 1041) | **taken** → terminal inventory | 240.73 | +16.25 |
| SHOP (idx 1029) | **taken** → terminal inventory | 169.50999 | +79.59 |
| MRNA (idx 965) | **skipped_risk** (portfolio risk gate) — ledgered, not forced in | — | — |
| PFE (idx 1035) | **taken** → terminal inventory | 29.57 | +294.17 |

In the ranked C1 study configuration the outcomes are configuration-dependent and are reported per view in the run table notes: all four are taken at 4bps and 25bps; at gross, SHOP is not taken (its C1 gross disposition is a gate skip; the other three are taken). MRNA's C0 risk-gate skip vs its C1 takes is not a contradiction — C0 has no ranking and a different marked-equity path; the guard's requirement (identical treatment rules, definite disposition, reconciled accounting in both independent paths) is what was proven preflight.

## The one run — 43-name W_DEV, frozen C1 configuration, corrected engine

Accounting convention (adjudicated gate 3): expectancy / PF / win-rate are computed over **closed taken trades only**; **final equity and total return include the terminal as-of marks of the open inventory** listed per view. Taken sets differ slightly by view (188 / 187 / 185 closed) because cost changes the marked-equity path and therefore gate outcomes — that path dependence is the frozen simulator's own behavior, reported as-is, not adjusted.

| View | Closed taken | Terminal open taken | Expectancy (closed) | PF | Total return | Max DD | Win % | Rank skips | Sector skips | Risk skips | Cap skips | Final equity (realized) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gross | 188 | 3 (MRNA +535.53, PFE +323.26, CRM +17.86) | **+0.150R** | 1.24 | +35.73% | 23.97% | 46.8 | 319 | 28 | 52 | 0 | 13,573.28 (12,696.63) |
| 4bps | 187 | 4 (MRNA +524.37, SHOP +90.54, PFE +336.47, CRM +18.74) | **+0.174R** | 1.28 | +42.44% | 24.61% | 48.1 | 326 | 28 | 45 | 0 | 14,243.57 (13,273.45) |
| 25bps | 185 | 4 (MRNA +476.75, SHOP +80.85, PFE +295.46, CRM +16.57) | **+0.108R** | 1.17 | +25.95% | 25.40% | 47.0 | 321 | 29 | 51 | 0 | 12,594.55 (11,724.91) |

Supplementary (4bps view): exposure 94.8% of event span; avg hold 16.7 bars; TP1 hit rate 50.8%; exits 161 stop / 26 ema55-break; max concurrent positions 5 (the cap). Entry-year slices of closed taken trades (descriptive only): 2025 — 95 trades, mean +0.036R; 2026 — 92 trades, mean +0.316R. Per-symbol (4bps, closed taken): strongest by summed net R — SNOW +11.56R (2 taken), AMD +7.76R (5), INTC +6.44R (6), QCOM +5.54R (4), MSTR +4.78R (6); weakest — MELI −7.70R (8), ASTS −7.05R (7), F −6.23R (14), XLF −5.71R (4), AAPL −2.88R (5). Full per-symbol table and the complete 590-candidate ledger (with per-candidate C1 dispositions at 4bps and per-view terminal accounting) are in `results.json` / `trade_ledger.json`.

Read on these numbers, with the labels attached: a positive development-window exploratory under a corrected engine whose two proven look-ahead defects and one ordering ambiguity are repaired, on candidate-grade data with an unadopted basis convention (G4). The window is a single bull-regime span; there is no out-of-sample evidence here; per the governing adjudication the classification stays **EQUITIES-ONLY DEV EXPLORATORY / G4 UNADOPTED / NOT VALIDATED EDGE** regardless of sign, and the frozen C1 promotion verdict (FAIL, 2026-10-03) is unchanged.

## Process disclosure

One descriptive statistic was corrected during execution: the first execution's `max_concurrent_positions` was computed with entries ordered before exits at shared timestamps (reporting 7, above the cap of 5). The simulators themselves process exits first; the reporting computation was fixed to simulator semantics (5 in all views) and **both counted executions were re-run with the final driver** — every gate outcome and run figure is unchanged apart from that one descriptive stat. The superseded execution was discarded, not reported.

## Reproduction

Package contents: `run_study13.py` (driver; config pin `87b8285a…` frozen in source), `tests/test_censoring.py`, `results.json` (full gate evidence), `trade_ledger.json` (590 candidates), `run_stdout.txt`, `SHA256_MANIFEST.txt`. Commands: `QF_OUT=<dir> unshare -n <venv-python> run_study13.py` (exit 0) — executed twice into separate output dirs; `results.json` and `trade_ledger.json` byte-identical across the two executions. Fixtures: `tests/test_censoring.py --impl successor --engine engine_successor` (exit 0) / `--impl frozen --engine engine_fork09` (exit 1).

**Bounds held:** no vendor calls, no credits, no HO performance parsing, no SMCI imputation, original UX51 and frozen originals untouched (the corrected engine remains research-only and unadopted), production PAUSED and pin-identical before/after, no trading, no shadow, no paid services. Elapsed ≈ 35 min of execution across the two counted executions plus fixture and packaging time.

— Muse
