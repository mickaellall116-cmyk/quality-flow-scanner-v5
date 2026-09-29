# SLICE 2 — Ranking + sector cap + slot accounting

**Status:** built 2026-09-18. All 18 tests pass (13 slice-1 + 5 slice-2).
**Scope (Mike's commission):** layer rs_top2 ranking, the E1 sector cap, and
position-slot accounting on top of the proven slice-1 live path.
Paper-only. Zero trading/alerting side effects.

## What was built (`pine_live/`)

| File | Purpose |
|---|---|
| `ranking.py` | `rs_score(df, signal_idx, spy_daily)`: per-signal 20-bar return minus SPY, mirroring `pine_ranking.compute_features` R1 (`RS_LOOKBACK`=20 imported; `bench_ret` imported). Unavailable SPY return → `-inf` **with a logged reason, never silent** (parity spec A8). `order_contenders` / `rank_take_limit` encode the contested-bar rule. Pinned bit-identical to the reference on every research-window candidate (test). |
| `sector.py` | Imports the frozen `SECTOR` dict from `pine_exposure` **by import** (single source of truth). Its sha256 is pinned at import time (`FROZEN_SECTOR_SHA256`); any change refuses import. `sector_of` raises `UnknownSectorSymbol` on unlabeled symbols — fail-closed, no default sector. |
| `portfolio.py` | `PortfolioState`: explicit, serializable, event-sourced state machine. `advance_clock` (open/total time) → `process_exits` (exits before entries at the same timestamp) → `decide_entries` → `settle` (peak/DD). Decision branch order mirrors `pine_stack.simulate_stack` exactly: RANKED_OUT → NO_SLOT → SECTOR_CAP → RISK_CAP → TAKEN. `reference_mark` mirrors the reference mark-to-market closure. Exit events are consumed; per-bar V3.6 exit evaluation for live positions is future work (the machine never invents exits). |
| `packets.py` (extended) | Slice2-v2 portfolio-decision packets: contenders (signal_id, symbol, sector, rs_score, rank inputs), contested flag, per-contender decision + reason code + reason_detail, sector counts and open counts before/after, state event-log range, data vintage, extended engine version (code hashes + sector-map hash). Slice-1 packets unchanged. |
| `replay.py` (extended) | `replay_portfolio_decision(packet, state_before, mark_fn)`: restores the prior state, re-runs `decide_entries`, diffs every decision bit-for-bit (code, rank, reason, rs_score, marked equity) plus before/after state. |
| `tests/test_slice2.py` | 5 tests (below). |

No existing repo file outside `pine_live/` was modified. Slice-1 files were
extended (packets, replay) but their proven behavior is untouched — all 13
slice-1 tests still pass.

## Acceptance proof (Mike's two-prong contract)

**Prong 1 — per-decision replay.** Crafted contested bar: 3 open positions
(2×SEMIS + 1×CRYPTO), 2 free slots, 4 simultaneous signals
(INTC/MU SEMIS, MSFT/CRM AI_SOFTWARE, rs 0.05/0.03/0.02/0.01).
Result: INTC→SECTOR_CAP, MU→SECTOR_CAP, MSFT→TAKEN, CRM→RANKED_OUT —
replayed from packet + prior state alone: **exact, zero diffs**. Replay
against a tampered prior state correctly refuses (not "close enough").

**Prong 2 — full-window aggregate parity.** The slice-2 event loop driven
over the entire research window reproduces the locked C1 stack **exactly**:

| Check | Slice-2 | Locked C1 |
|---|---|---|
| trades | 143 | 143 |
| expectancy | +0.337R | +0.337R |
| total return | 52.25% | 52.25% |
| max drawdown | 31.63% | 31.63% |
| Calmar | 1.65 | 1.65 |
| TAKEN | 143 | 143 |
| RANKED_OUT | 94 | 94 |
| SECTOR_CAP | 16 | 16 |
| NO_SLOT | 0 | 0 |
| RISK_CAP | 10 | 10 |

Bit-identical to a fresh `pine_stack.simulate_stack` run (final equity to
1e-6, max DD to 1e-9, identical taken trade index list, identical skip
counters) AND matching the frozen `stack_results.json` C1 numbers. The
first genuinely contested bar of the window also replays exactly from its
packet + prior state.

## Reference-behavior surprises (pinned, not "fixed")

1. **NO_SLOT is unreachable in the ranked configuration.** When free slots
   hit 0 with candidates present, the bar is by definition contested, and
   the ranking cutoff (`taken_at_t >= min(2, free)`) fires before the
   `free <= 0` branch. All slot-driven skips are therefore recorded as
   RANKED_OUT (94), never NO_SLOT (0). The dead branch is kept because the
   unranked reference has it; the test asserts the 0 explicitly.
2. **marked_equity is recomputed per candidate** inside the timestamp loop
   (positions taken earlier at the same t change it) — mirrored, not
   hoisted.
3. **The 5% portfolio-risk gate fired 10 times in C1** (RISK_CAP) — a live
   behavior the research summary had not headlined; it is part of the
   locked stack and reproduced exactly.

## Explicitly NOT built yet (slice 3)

- Duplicate-signal suppression (`signal_id` dedup on rerun/retry)
- Alert delivery (no alerting code exists; the module cannot send anything)
- Per-bar V3.6 exit evaluation for live open positions (state machine
  consumes exit events; nothing generates them live yet)
- The multi-symbol live evaluation cycle (per-bar fan-out across UX51)
- The Part-B reconciliation job (daily live-vs-reference diff)
- Any trading, order, or broker integration

## Test summary (18/18 green)

- Slice-1 (13): unchanged, all pass — no regressions.
- `test_sector_map_pinned_and_fail_closed` — map hash pinned; unknown
  symbol raises.
- `test_rs_score_matches_reference_on_all_candidates` — bit-identical rs
  on every research-window candidate; unavailable SPY never silent.
- `test_slice2_modules_import_cleanly`.
- `test_full_window_reproduces_locked_c1_exactly` — bit-identical vs the
  reference simulator; locked numbers; exact reason breakdowns; first
  contested bar packet replays exactly.
- `test_crafted_contested_bar_replay` — exact take/skip/reason codes from
  packet + state; tampered state refuses.
- Static no-side-effect scan (slice-1 test) covers the new modules:
  no alert/trade/network surface; only reference-module data download.
