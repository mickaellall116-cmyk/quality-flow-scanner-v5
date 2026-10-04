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
| Portfolio | `v54_forward_harness.py` | Per-position tracking; admission controls **not yet mapped** — requires source verification before any claim |

**Open item:** the forward harness's slot/ranking/heat admission logic has not been source-verified for this map. No claim is made about it here.

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

Mike's objective: *test whether a defined stock-selection rule improves the intended Quality Flow system.*

- If the intended system is **System 1**, the experiment is fully specified: same `gen_candidates` + `compute_features` + `simulate_stack` code, only the universe split changes (TOP-50 vs BROAD-225). The corrected C1 is the baseline.
- If the intended system is **System 2**, the forward harness's admission logic must be source-mapped first, and a System-2 backtest baseline must be built (none exists).
- System 3 requires implementation before it can be tested.

**No lineage chosen here.** The data inventory continues. Performance runs remain paused.
