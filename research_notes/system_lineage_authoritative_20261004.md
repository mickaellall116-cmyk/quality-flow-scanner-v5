# Authoritative System Lineage — C1 / Mode B / Rev6
**Status:** BLOCKING TASK COMPLETE (2026-10-04). Single factual lineage table per Bridge #1 comment 5976364417.
**No performance run. No holdout access.**

---

## Lineage table

| Stage | A1: Raw pine_backtest (control) | A2: Corrected C1 (studied system) | B: Forward-test Mode B (as-traded) | C: REV6 (spec) |
|-------|-------------------------------|----------------------------------|-----------------------------------|----------------|
| **Entry point** | `pine_backtest.py:347` `main()` | `pine_stack/pine_stack.py:295` `main()` | `v54_forward_harness.py` hourly cycle | — (no implementation) |
| **Signal generator** | `pine_backtest.py:109` `pine_buy_signal` (commit `507d29f`) | `pine_backtest.py:109` `pine_buy_signal` via `gen_candidates` (same commit) | `v54_engine.py` scan → `v54_qualified_signals` (commit `246f778`) | REV6 §2 (transcription) |
| **Trade/exit simulator** | `pine_backtest.py:138` `gen_pine_trades` (commit `507d29f`) | `pine_ranking/pine_ranking.py:25` `gen_candidates` — **byte-identical trade logic** to `gen_pine_trades`, plus `signal_idx` (commit `507d29f`) | `v54_exit_tracker.py` `ModeBTracker` (commit `507d29f`) | REV6 §3–§4 (spec) |
| **Ranking features** | — (none) | `pine_ranking/pine_ranking.py:95` `compute_features`: rs (20-bar 4H return − SPY 20-bar daily), vol, rr | — (none; Claude-verified, comment `5975208144`) | REV6 A4: rs_top2 (spec) |
| **Portfolio wrapper** | `pine_backtest.py:221` `simulate_portfolio` (commit `507d29f`) | `pine_stack/pine_stack.py:40` `simulate_stack`, `use_ranking=True, sector_cap=True, dd_gate` (commit `507d29f`) | Harness `_busy()` per-symbol only (Claude-verified, comment `5975208144`) | REV6 A3: admission sequence (spec) |
| **Output ledger** | In-memory dict (no file) | `pine_stack/stack_results.json`, `stack_results_2022.json`, `stack_results_2022_C1_CORRECTED_SCORE_BASELINE.json` | `v54_forward/forward_test.jsonl` (append-only) | — |
| **Fill semantics** | Entry: next-bar open. Exits: next-bar open (close-evaluated). TP1: intrabar limit. | Same as A1 (identical engine). | Entry: next-bar open. Stop: **intrabar** (stop price). TP1: intrabar limit. Scanner EXIT: next-bar open (after +1R arm). Time: bar close. | Per REV6 §4 (spec) |
| **RS timeframe** | — | 20 completed 4H bars (symbol) minus SPY 20 completed daily bars | — | Same as A2 (spec) |
| **Risk sizing** | 1% of marked equity (`RISK_PCT`) | 1% of marked equity, **halved** when equity ≤90% of peak (S4 DD gate) | Harness/paper (not backtest-sized) | $750 fixed planned risk (spec, unimplemented) |
| **Result** | C0 fidelity control | **240 trades, +0.178R @4bps** (reproduction reference) | Paper positions (paused) | — |

---

## A1 vs A2 — the distinction (per 5976364417)

- **A1** (`simulate_portfolio`) is the **fidelity control**: chronological, no ranking, no sector cap, no DD gate. Its purpose is to verify A2's engine matches the base simulation (`pine_stack.py:318` asserts equality when all controls are off).
- **A2** (`simulate_stack`) is the **studied system**: same trade engine, plus rs top-2 ranking when contested, sector cap 2, 5 slots, 5% heat, S4 DD gate. This produced the 240-trade corrected C1.
- Discussing "pine_backtest.py" without specifying A1 vs A2 caused the earlier confusion. They share the signal generator and trade engine; they differ only in the portfolio wrapper.

## B — actual call path (per 5976364417)

`v54_forward_harness.py` → `v54_scan_symbols()` → `v54_qualified_signals()` (eligibility-only filter, no ranking) → `ModeBTracker` per position → `v54_forward/forward_test.jsonl`.

Claude source-verified (comment `5975208144`): no cross-symbol ranking, no sector bookkeeping, no portfolio-risk gate in the live path. `_busy()` is per-symbol only. **The live pipeline cannot validate the C1 portfolio stack.**

## C — REV6: implemented vs unimplemented (per 5976364417)

| REV6 requirement | Status |
|-----------------|--------|
| A4 rs_top2 ranking formula | **Implemented** in A2 (`compute_features` + `simulate_stack` L89–94) |
| 5 slots, 5% heat, first-fit | **Implemented** in A2 |
| $750 fixed planned risk | **Unimplemented** — A2 uses 1% of equity |
| Busy/pending handling | **Partially implemented** — A2 has no pending concept; B has per-symbol busy |
| A3 admission sequence (spec) | **Specified only** — no backtest implements the full A3 sequence as written |
| D6 differential oracle | **Specified only** — not built |

**Without declaring all C1 controls nonexistent:** A2 demonstrably implements ranking (rs top-2), sector cap 2, and the S4 risk gate — verified by source inspection and 9 passing synthetic fixtures. What A2 does *not* have is the $750 fixed risk and the full A3 pending/busy sequence as REV6 specifies them.

---

## For the TOP-vs-BROAD experiment

**Frozen stack: A2** (Mike's System 1 choice). Entry point `pine_stack.main`, signal `pine_buy_signal`, trade engine `gen_candidates`, ranking `compute_features`, portfolio `simulate_stack` with all C1 controls. The only difference between TOP and BROAD arms is universe membership. BROAD is computed fresh on corrected session candles (commit `b3a7251`); the 240-trade ledger is the reproduction reference, not the baseline.
