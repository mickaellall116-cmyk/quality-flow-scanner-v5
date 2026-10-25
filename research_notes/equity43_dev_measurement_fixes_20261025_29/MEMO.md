# -29 — Measurement + recording fixes (P1 / P4 / P7 / P8), 25 bps reconciliation, and ledger parity

**Date:** 2026-10-25 (ET). **Lane:** Muse, single dispatch.
**Governing texts:** USER AUTHORIZED GO relayed by ChatGPT, Slack TS 1792932745.183489 (2026-10-25 08:52 ET); binding scope in Issue #1 comment 6397875042. Specifications: -27 memo §2.1 (P1), §2.4 (P4 erratum text), §2.7 (P7), §2.8 (P8); -25 §A6 telemetry keys T1–T6; Mike's full-state journal direction (bridge 9087bf0).
**ACK:** Slack TS 1792933280.017509; bridge commit 83194a6. Single-dispatch check: CLEAR (no stage dir, worktree, or implementation commit for this GO; the -27/-28 packages are review text only).

**Bounds held:** no BUY/EXIT/TP1/ranking/portfolio decision logic changed; no new performance tests or backtests (the pipeline re-executions below are accounting reproductions of the recorded -13 run asserting byte-identity of its artifacts — parity checks, not new results); holdout SEALED; no vendor calls; no spending; no trading; production PAUSED and untouched; the Oct 26–30 feed pilot untouched; no S1/S2/G4 change. Original C1 FAIL stands; no validated-edge claim.

---

## 1. P1 — All-bar marked equity / drawdown (measurement layer)

**Method** (per -27 §2.1 spec, implemented in `code/mtm_allbar.py` as a measurement fork of the successor `pine_stack.simulate_stack`): equity is marked at every admitted 4H bar completion on the union calendar of the run's symbols, in addition to the frozen event times. Valuation is byte-identical to the frozen `marked_equity` — only *when* marking happens changes, never *how* a position is valued. Decisions run at event times only, against identical `marked_equity(t)` values, so the taken set cannot move; the fork additionally refuses `dd_gate=True` fail-closed (under S4 the peak would feed sizing, and an all-bar peak could then alter decisions — the frozen DEV C1 run has the gate off, verified in `run_study13.run_views`). One boundary rule matters: at a bar completion that coincides with an exit event, the position is first valued at the just-completed bar's close (it was open at that close; its fill is the next bar's open), then the exit is realized — the mark the event grid can never see.

**Synthetic fixtures** (`tests/test_mtm_allbar.py`, all PASS): a position whose intra-event excursion (close 50 between two event marks of 100) is invisible to the event grid — fail-before event DD = 0.0 exactly; pass-after all-bar DD = 5.0% exactly (hand-computed). Upward-excursion fixture: all-bar DD = 500/10500 exactly. Empty book: 0/0. `dd_gate=True`: refused.

**DEV results** (fork applied to the recorded run; decisions/outputs asserted identical to the frozen simulator on every field — taken, dispositions, exit cash flows, final/realized equity, terminal inventory, skip counts, exposure):

| View | Event-sampled DD (historical, retained) | All-bar marked DD (new measurement) | Gap |
|---|---|---|---|
| gross | 23.97% | **25.5756%** | +1.61 pp |
| 4 bps | 24.61% | **26.1840%** | +1.57 pp |
| 25 bps | 25.40% | **26.7035%** | +1.30 pp |

The all-bar trough sits at the 2026-03-27 13:30 ET mark in all three views. The event-sampled figures stay as the historical record, unmodified, everywhere they appear; the all-bar figures are reported beside them (`artifacts/mtm_dev.json`; full marked series in `artifacts/equity_series_allbar.json`). Cross-verification: an independent interval reconstruction of the equity path (`equity_series_from_intervals`, sharing no loop code with the fork) reproduces the all-bar DD to <1e-9 and every bar-close mark with 0 mismatches, in all three views. The invariant all-bar DD ≥ event-sampled DD holds and is asserted in code. Per -27 §2.1(iv), until a results template adopts the all-bar figure it must carry the sentence: "Drawdown is event-sampled and is a lower bound on all-bar marked drawdown."

## 2. P4 — Stop docstring correction (documentation only)

Applied the -27 §2.4 erratum verbatim to the executed successor source of record, `research_notes/equity43_dev_forensic_20261023_14/code/engine_successor/pine_backtest.py`: line 16 now reads "TP1 = entry fill + ATR*2.0"; the line-18 exit clause ("exits: intrabar stop (stop-first on ties), TP1, close<EMA55 or trendBear") is replaced with the close-evaluated truth (TP1 is an intrabar LIMIT order; the stop/trail and EMA55/trend-bear exits are CLOSE-evaluated and fill at the NEXT bar open; there is no intrabar stop and no stop-first tie rule). Diff: 6 insertions / 3 deletions, **all inside the module docstring** (docstring spans lines 1–29).

**Zero-behavior proof** (`tests/p4_bytecode_check.py`, output in `artifacts/p4_bytecode_check.txt`, PASS): all 18 code objects compared recursively — `co_code`, names, varnames, flags, and constants (docstring excluded) identical; instruction streams identical with LOAD_CONST masked and line numbers ignored; no changed line outside the docstring. File sha256 changes 874d2a9b… → **262ec034…**; any future packet or pin referencing this file must re-pin to the new hash (the blind-review packet stays pinned at commit 555ebb1 with the pre-erratum bytes, as history). Scope note: other copies carrying the stale sentence (the repo-root production `pine_backtest.py` — a production file, not touched under this GO's prohibitions; the -22 bundle snapshot — a frozen review artifact) are NOT edited; the erratum text above is the correction of record for all copies.

## 3. P7 — All-fire unsuppressed BUY journal

**Method** (`code/allfire_journal.py`): a generation/recording layer that mirrors the successor `gen_candidates_censored` loop statement-for-statement and probes the frozen `pine_buy_signal` on **every** completed bar of the generator's evaluation domain (per symbol, bars i ∈ [WARMUP=215, n−2] of the pinned 4H series). Each fire is classified MATCHED_CANDIDATE / SUPPRESSED_OVERLAP (with the occupying candidate named) / GAP_INELIGIBLE_ENTRY / UNCLASSIFIED (fail-closed alarm). Anchors, all asserted in the DEV harness: the mirrored loop's candidates are field-identical to the frozen generator's on all 43 symbols; the matched set equals the committed ledger's 590 candidate keys exactly; UNCLASSIFIED = 0.

**DEV census** (`artifacts/allfire_journal.json`, summary in `artifacts/allfire_summary.json`):

| Class | Count |
|---|---|
| Total frozen BUY fires | **2,892** |
| MATCHED_CANDIDATE (the ledger's 590) | 590 |
| SUPPRESSED_OVERLAP (standalone trade open on the symbol) | 2,301 |
| GAP_INELIGIBLE_ENTRY (next-bar open ≤ stop threshold) | 1 |

The 590-candidate ledger is untouched and remains the decision record; the journal sits beside it as the all-fire record (U2 universe of -27 §2.7 is now populated for DEV). Every rate computed on the 590 keeps its standing qualifier: they are non-overlapping standalone candidates — about one fire in five became a candidate. The journal computes no outcomes for suppressed fires and feeds no decision.

## 4. P8 — As-of signal / EXIT-path research telemetry (code only, prospective)

`code/qf_telemetry.py` implements the adopted spec (Mike's full-state journal direction, bridge 9087bf0; -25 §A6 keys T1–T6) as an append-only, hash-chained JSONL journal with four record types — SIGNAL_FIRE (T1 full signal state incl. ADX/DI, trendScore, VWAP distance, rel-volume, EMA geometry, rs + benchmark as-of, market-gate state; T2 admission state; all price levels), BAR_PATH (T4 threshold events + MAE/MFE inputs; T5 geometry series in force), EXIT_DECISION (T3: the decision bar's full OHLC — including its close — plus the runner/EMA55 thresholds in force), EXECUTION (T6). Guards, all fail-closed and battery-tested (`tests/test_telemetry.py`, 14/14 PASS): nothing records from an unfinalized bar; decision_time must equal the bar's completion (earlier = lookahead, refused); retro-stamped records refused; per-symbol monotonic append (no backfill); strict schemas (unknown or missing fields refused); hash chain verified on load and on demand, with tamper localized to the exact line; EXECUTION records refused in signal-only mode (a feed cannot establish fills). No historical values are populated; the module is prospective research-capture code only — S1/shadow adoption remains under its own launch gates, unchanged by this item.

## 5. Reconciliation — the 25 bps 185-vs-187 discrepancy is RESOLVED

From the pinned artifacts only; no strategy re-run. The -13 driver's phase5 wrote one candidate ledger whose rows carry **per-view taken flags**, because each cost view ran its own portfolio path (costs feed the marked-equity path the risk gate reads, so the taken sets genuinely diverge in both directions: 12 candidates are taken at 25 bps but not at 4 bps, 14 vice versa, 177 in common). results.json's 25 bps row describes the 25 bps view's own taken set. The -27 §3 recomputation summed the `net_r_25bps` column over the **4 bps taken set** — the wrong subset — yielding 187 @ +0.10753R and the appearance of an irreproducible headline. Extracting by the `taken_25bps` flag (`code/reconcile_per_view.py`; artifacts `ledger_gross.json` / `ledger_4bps.json` / `ledger_25bps.json` / `per_view_summary.json`):

| View | Taken | Closed | Mean R (ledger) | results.json expectancy | PF | Win % |
|---|---|---|---|---|---|---|
| gross | 191 | 188 | +0.14990 | 0.150 | 1.239 (1.24) | 46.8 |
| 4 bps | 191 | 187 | +0.17373 | 0.174 | 1.283 (1.28) | 48.1 |
| 25 bps | 189 | **185** | **+0.10751** | 0.108 | 1.166 (1.17) | 47.0 |

All three views match their results.json rows exactly on counts and within the rows' rounding on every figure. The wrong-subset figure (187 @ +0.10753R) is reproduced in the summary as a labeled diagnostic. **Original cost convention, documented:** DEV costs are a single flat per-trade charge of the view's bps on entry notional, applied once per trade in `_outcome` (pine_backtest.py:214-218) — not per-fill, not on exit notional. Verified arithmetically on all 586 closed records × 2 nonzero views (net_r == gross_r − cost/risk_frac; 1,172 checks, 0 violations). No cost model was changed and no "edge" was recalculated; the per-view ledgers are extractions of recorded data. The -27 R19 gap is closed; a short erratum pointer to this memo should ride the v0.3 redline record (ChatGPT's lane).

## 6. Parity — byte-identical, with the fixed measurement code in place

1. **Baseline reproduction.** The pinned -13 pipeline (driver phases 2/4/build/fidelity/5, stage assets hash-verified against the driver's own EXPECTED_PINS) reproduces the committed `trade_ledger.json` **byte-identically** (sha256 267e794c…) and the results.json P5_run views exactly (parsed-equality on every field, all three views).
2. **Fork in place.** With `simulate_stack` swapped for the all-bar fork, phase5 re-executes and the produced ledger is again **byte-identical** (same sha256); the view rows differ from the committed rows in **only** `max_drawdown_pct` (gross 23.97→25.58, 4 bps 24.61→26.18, 25 bps 25.40→26.70, at the rows' 2-dp rounding) — precisely the intended measurement change, nothing else.
3. **Repo artifacts untouched.** The committed -13 ledger/results and all other record files are unmodified by this package (the only pre-existing file edited anywhere is the P4 docstring, §2). Field-scoped note: byte identity applies to the ledger and to every view field except the drawdown fields named above; there is no other divergence to scope.

## 7. Deliverables and verification

Package: `research_notes/equity43_dev_measurement_fixes_20261025_29/` — `code/` (mtm_allbar, allfire_journal, qf_telemetry, reconcile_per_view, verify_package, plus the two executed harnesses as workpapers), `tests/` (5 batteries), `artifacts/` (mtm_dev, equity_series_allbar, allfire_journal + summary, per-view ledgers + summary, p4_bytecode_check), `SHA256_MANIFEST.txt`. Independent check: `python3 code/verify_package.py` re-derives every artifact-level claim from the package + committed -13 artifacts and runs all batteries (exit 0). Environment note: the DEV harnesses read `pandas_market_calendars` from the existing `qf_td17_stage/pylibs` on PYTHONPATH (read-only; nothing installed).

— Muse
