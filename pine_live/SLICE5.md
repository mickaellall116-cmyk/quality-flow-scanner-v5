# Slice 5 — Live exit evaluation (paper-only)

**Status:** complete. 17/17 slice-5 tests pass; full Slice 1–5 suite green.
**Authorization:** Slice 5, paper-only. No real notifications, no trading
integration, no strategy changes. Reconciliation, notifications, and
trading integration remain out of scope.

## What it does

At each cycle timestamp, open positions are evaluated with the canonical
V3.6 exit logic **before** entries are decided. Exits free slots, sector
capacity, and risk budget for the same timestamp's entries. Exit
decisions, like entry decisions, produce fsync'd replayable packets.

## Canonical behavior (observed, not designed)

The reference is the position-management block of
`pine_backtest.gen_pine_trades` (mirrored by `pine_ranking.gen_candidates`,
the engine behind the locked C1 trades). Observed 2026-09-18:

- `High >= TP1` fills 50% at TP1.
- Once TP1 is hit, the runner updates at each close:
  `runner = max(runner, close - ATR * TRAIL_ATR)` (`TRAIL_ATR` imported
  from `pine_backtest`, never a literal).
- Final triggers are close-evaluated: `close < runner` → `stop`
  (stop wins same-bar ties); otherwise `close < EMA55` or bearish trend
  → `ema55-break` / `ema55-bear`.
- The final fill is the next bar's open (live edge: the trigger bar's
  close when there is no next bar).
- The reported exit price is the synthetic 50/50 blend once TP1 is hit.
- `lo` is unpacked but never read — by the reference or here.
- **There is no time-based exit in V3.6.** The 30-bar maximum hold belongs
  to V5.4 Mode B, a different system. Adding one here would be a strategy
  change and would break the bit-identical differential proof.

## Direct-reference design (acceptance criterion 1)

`pine_live/exits.py` does not reimplement the exit loop. The loop lives
inside `gen_pine_trades`' walk, so there is no standalone reference exit
function to import — and `pine_backtest.py` is frozen. The module is a
character-faithful extraction of the per-bar manage block, and its
fidelity is proven, not asserted:

- `test_exit_walk_matches_reference_on_all_trades` replays the walk over
  all 263 research-window reference trades and requires the first
  trigger to reproduce (exit_time, exit_px, reason, tp1_hit, hold_bars)
  **exactly**: 263 checked, 0 mismatches.
- Every constant comes from `pine_backtest` by import (`TRAIL_ATR`).
- Entry/stop/tp1 carried by live positions are asserted equal to the
  reference trade on every research candidate (slice-4 suite).
- The import graph is pinned: `exits.py` imports only stdlib, pandas,
  and `pine_backtest` — it cannot reach portfolio state, dedup, or
  alerts, so exits cannot retroactively alter entry decisions
  structurally, not just by convention.

## Exit packets

One packet per applied exit, fsync-appended to its own JSONL log
(`exit_packet_log`, separate from entry packets):

- `position`: exact pre-exit position fields.
- `evaluation` / `trigger` / `exit`: walk report, trigger bar/reason/
  fill, exit_px, R breakdown, hold_bars, net_r.
- `pre_exit_state`: the full `PortfolioState.to_dict()` immediately
  **before this exit** — sequential when several exits share a
  timestamp (derived from the pre-timestamp state plus the engine's own
  close events in application order).
- `post_exit_state`: the full `to_dict()` immediately **after this
  exit** — the replay target.
- `realized_after`, `net_r`: read from the applied close event (engine
  ground truth), never recomputed prospectively.
- `bars_snapshot_ref`: sha256-pinned snapshot of the walked bars
  **through the trigger bar plus the fill bar** (the fill is next-bar
  open, so replay needs that bar). The snapshot stores the frame's IANA
  tz (`America/New_York`), not a fixed offset — a fixed offset corrupts
  bar times when the snapshot spans a DST boundary.
- `data_vintage`, `engine_version` (pins `exits.py` by hash).

## Replay

`replay_exit_decision(packet)` needs only the packet + its snapshot:

1. Hash-verifies the snapshot (tampering is rejected, never papered
   over).
2. Re-runs the pure walk; trigger time/reason/tp1/exit_px/hold_bars must
   match.
3. Rebuilds the `PortfolioState` from `pre_exit_state`, applies exactly
   one exit through the real `process_exits`, and requires the resulting
   serialized state to equal `post_exit_state` **exactly**
   (bit-identical; JSON round-trips doubles exactly and the engine is
   deterministic).

## Ordering and atomicity

- Exits are evaluated **before** entries at each timestamp; the entry
  path is untouched. A dedicated test proves entry decisions are
  byte-identical whether exits come from live evaluation or external
  events.
- The timestamp is atomic: malformed generated events, engine
  exceptions, or exit-packet write failures restore the exact
  pre-timestamp state, roll back the append-only logs, log the failure,
  and leave no partially applied exit.
- A position whose walk cannot be evaluated is skipped (stays open, failure
  logged); the rest of the cycle proceeds.
- Exit evaluation order is canonical (sorted symbols); contender input
  order is inert — proven by a shuffled-input byte-identity test.
- Delivery (dedup/outbox) is causally inert: a raising sender cannot
  mutate state, and enabled vs physically-disabled runs are
  byte-identical.

## Full-window proof

`test_live_exits_full_window_c1_exact` drives the whole research window
through `run_cycle(live_exits=True)` with no external exit feed:

- the live walk fires exactly the reference exit set at every timestamp;
- the taken set is byte-identical to the reference 143;
- locked C1 reproduced exactly: 143 trades, +0.337 R/trade, +52.25%,
  31.63% DD, Calmar 1.65, TAKEN 143, RANKED_OUT 94, SECTOR_CAP 16,
  NO_SLOT 0, RISK_CAP 10;
- all 143 exit packets match their reference trades and replay exactly.

## Crafted capacity scenario

Seeded 5 positions (4 fillers + the real NFLX reference trade) at
2026-04-17 13:30:00-04:00 with a full book: the live walk exits NFLX
(reason `stop`, exit_px `99.90533209585874` — exact reference match)
before entries, freeing one slot; INTC (top-ranked) is TAKEN, XLF stays
RANKED_OUT. The no-exit control takes neither.

## Deliberate non-goals

- No 30-bar / time-based exit (V5.4 behavior, not V3.6).
- No reconciliation job (Mike's intended next step after Slice 5).
- No real notifications, trading integration, broker automation, or
  real-money deployment.
- No strategy changes of any kind: the walk is proven equal to the
  reference, not improved upon.
