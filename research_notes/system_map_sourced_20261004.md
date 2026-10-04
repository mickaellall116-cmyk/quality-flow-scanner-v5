# Quality Flow: Source-Backed Map of Complete Systems
**Status:** CORRECTION (2026-10-04). Supersedes the incomplete QF-R1 pin in addendum v2.
**Correction:** the earlier analysis mapped only `pine_backtest.simulate_portfolio` (a fidelity control). The complete corrected-C1 backtest uses `pine_stack.simulate_stack`, which **does** include ranking, sector caps, and risk controls.

---

## System 1: Corrected C1 — the complete as-studied backtest

**What produced it:** 240 trades, +0.178R @4bps (bridge_thread.md:60; team_reset_record_20261003.md:12).

| Layer | Source | Verified behavior |
|-------|--------|-------------------|
| Signals | `pine_backtest.py:109` `pine_buy_signal` | confirmed / breakout_buy / ready_buy (corrected 0–5 trendScore) |
| Trade engine | `pine_ranking/pine_ranking.py:25` `gen_candidates` | Byte-identical logic to `pb.gen_pine_trades`: next-bar-open entry; gap-below-stop invalidation; TP1 50% intrabar; trail-after-TP1 at bar close; close-evaluated stops/exits → next-bar open. Plus `signal_idx` for ranking features. |
| Ranking features | `pine_ranking/pine_ranking.py:95` `compute_features` | **rs** = 20-bar symbol return − SPY return over same span (PIT); vol = volume/vol_ma; rr = reward:risk |
| Portfolio | `pine_stack/pine_stack.py:40` `simulate_stack` | Event-driven; see controls below |
| Portfolio: ranking | `pine_stack.py:89-94` | When candidates contest free slots: **rank by rs descending, take top 2** (`taken_at_t >= min(2, free)`) |
| Portfolio: slots | `pb.MAX_CONCURRENT = 5` | 5 concurrent positions |
| Portfolio: sector cap | `pine_stack.py:104-109`, `sector_cap=True` | **Max 2 per sector** (`n_sec >= 2` → skip) |
| Portfolio: heat | `pine_stack.py:123-126` | (open risk $ + new risk $) / equity ≤ 5% |
| Portfolio: DD gate (S4) | `pine_stack.py:116-122` | Equity ≤ 90% of peak → risk halves; ≥ 95% → restores |
| Sizing | `pb.RISK_PCT = 0.01` (`pine_backtest.py:56`) | 1% of marked equity per trade (halved under DD gate) |
| Costs | `pb.COSTS` | 4bps / 25bps per round trip |
| R accounting | `pb._outcome` (`pine_backtest.py:214`) | Blended 0.5×TP1 + 0.5×runner, net of costs |

**Fidelity check:** `pine_stack.py:318` verifies `simulate_stack(..., False, False, False)` == `pb.simulate_portfolio` (C0 control). The ranking/sector/DD controls engage only in the C1+ cases.

**What this corrects:** addendum v2's §2 table ("NO rs_top2", "no $750", "chronological") described the C0 fidelity control, not the C1 system. The 16 synthetic fixtures tested the trade engine correctly, but the portfolio layer they tested (`pb.simulate_portfolio`) is the control, not the C1 stack.

## System 2: Forward-test Mode B — the as-traded system

| Layer | Source | Verified behavior |
|-------|--------|-------------------|
| Signals | `v54_engine.py`, harness scan | Frozen V5.4 (per-harness) |
| Exits | `v54_exit_tracker.py` `ModeBTracker` | **Intrabar** stops (stop wins ties); TP1 50%; **Profit Protect** (+1R arming gates scanner EXIT → next-bar open); **30-bar max hold** |
| Portfolio admission | **Claude source-reviewed** (Issue #1 comment `5975208144`, 2026-10-04) | **Per-symbol busy control ONLY** — `_busy()` prevents another open/pending position in the same symbol. **No** cross-symbol ranking, **no** sector cap, **no** portfolio-risk/heat gate. `v54_qualified_signals` is eligibility-only (no sorting/truncation/top-N). |

**Claude's conclusion (linked, not re-verified here):** "The inspected live pipeline did not implement the intended C1 top-two ranking, sector cap or portfolio-risk gate. It therefore cannot validate the C1 portfolio stack." Evidence tier: source-inspected call-chain (Claude); pin/hash identity unverified; no independent rerun.

## System 3: REV6 spec — as-specified (no implementation)

- `research_notes/CANONICAL_RECONSTRUCTION_FROZEN_RULES_20260928_REV6.md` specifies A3 (admission sequence) + A4 (rs_top2 ranking), $750 planned risk, busy/pending.
- **No backtest implements it.** It remains a spec, not a system.

## Reconciliation

| | System 1 (C1 studied) | System 2 (Mode B traded) | System 3 (REV6 spec) |
|---|---|---|---|
| Ranking | Yes — rs top-2 when contested | Unknown (unmapped) | Specified, unimplemented |
| Sector cap | Yes — 2 | Unknown (unmapped) | Not specified |
| Stops | Close-evaluated → next-bar open | Intrabar (stop wins ties) | — |
| Time exit | No | Yes — 30 bars | — |
| Profit Protect | No (trail-after-TP1) | Yes (+1R arming) | — |
| Sizing | 1% equity (halved in DD) | Harness-dependent | $750 fixed (spec) |
| Baseline | Yes — 240 trades | Paper only | None |

## What this means for the experiment

**Mike's decision (2026-10-04): System 1 is the experiment stack.** Test the complete studied C1 with TOP-vs-BROAD as the only difference.

**Qualification 1 — reproduction reference vs experiment baseline:** the 240-trade/+0.178R result is a **reproduction reference** (it validates that the code reproduces the studied numbers). It is **not** the experiment's baseline, because the experiment uses **corrected session-anchored candles** (commit `b3a7251`) while the 240-trade result used the old candle grid. The BROAD leg must be **newly computed** on corrected candles; the old headline cannot serve as the comparison point.

**Qualification 2 — portfolio verification:** the 16 synthetic fixtures tested the trade engine and the C0 control portfolio. The actual `simulate_stack` selection (rs top-2), sizing (1% equity), and caps (sector 2, 5 slots, 5% heat, S4 DD gate) now have **9 targeted fixtures** (`tests/test_simulate_stack_20261004.py`), all passing. Builder-tested; independent inspection pending.

- If the intended system is **System 1**, the experiment is fully specified: same `gen_candidates` + `compute_features` + `simulate_stack` code, only the universe split changes (TOP-50 vs BROAD-225). The BROAD leg is computed fresh on corrected candles.
- If the intended system is **System 2**, a System-2 backtest baseline must be built (none exists). Not the current experiment.
- System 3 requires implementation before it can be tested. Not the current experiment.

**No lineage ambiguity remains for this experiment: System 1.** The data inventory continues. Performance runs remain paused.
