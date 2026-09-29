# Slice 4 — Multi-symbol live cycle (paper)

Status: built and tested 2026-09-18. 40/40 slice-1..4 tests green.

## What this is

`pine_live/multicycle.py` — the canonical multi-symbol live cycle. One
`run_cycle(symbols, bar_time)` ingests all eligible symbols, evaluates each
through the slice-1 path (assertions + canonical `pine_buy_signal` from the
reference), aggregates every valid contender, and runs the locked slice-2
per-timestamp engine exactly once: ranking → sector cap → 5% portfolio-risk
gate, in the frozen branch order. Paper state updates deterministically;
every accepted AND rejected decision gets a replayable packet
(`TAKEN` / `RANKED_OUT` / `SECTOR_CAP` / `RISK_CAP` / `NO_SLOT`). Slice-3
dedup + paper alerts stay causally downstream and cannot change logic.

`bar_time` is the DECISION time (the bar whose open triggers the cycle).
`signal_bar="previous"` (default) is the canonical live semantic: evaluate
the just-closed bar, enter at the known open. It is also the research-replay
semantic: the reference decides entries at `entry_time` from the signal bar
whose next open is `entry_time`. `signal_bar="at"` evaluates the bar at
`bar_time` itself (evaluate-latest-closed-bar); a signal whose next bar is
not in frame yet is logged as `pending_entry` — never entered prematurely
(the reference enters at next-bar open, which does not exist yet).

## The locked cycle contract (Mike's commission)

1. Every symbol passes slice-1's canonical 4H assertions before evaluation.
2. V3.6 qualification comes from the imported canonical `pine_buy_signal`;
   decomposition is packet explanation only.
3. Same-timestamp signals flow through the locked order: ranking → sector
   cap → 5% portfolio-risk gate.
4. Paper state updates deterministically; symbol input order cannot affect
   results (symbols are canonicalized and sorted; `universe_order` follows
   sorted symbols, never input order).
5. Per-symbol data/assertion failure is logged and skipped — never
   evaluated on bad data, never poisoning valid symbols.
6. Unknown sector refuses the whole timestamp and rolls back exactly (no
   partial entries; clock accounting still advances — documented
   fail-closed semantics).
7. Dedup + paper alerts remain causally downstream (proven by the slice-3
   structural test AND by enabled-vs-disabled byte-identical runs on the
   multi-symbol path).
8. Live exits are NOT generated here (slice 5). Reconciliation (slice 6),
   real alerts, trading, and live orders are excluded.

## Reference-behavior pin (discovered slice 4, proven)

**Within ONE timestamp, `RANKED_OUT` and `RISK_CAP` are mutually exclusive
under the locked branch order** `TAKEN → RANKED_OUT → NO_SLOT → SECTOR_CAP
→ RISK_CAP`:

- A risk veto occurs while `taken_at_t < min(2, free)`; after the veto no
  position is added, so free slots do not shrink and portfolio heat cannot
  improve — every later eligible candidate is risk-vetoed too.
- Once `taken_at_t >= min(2, free)`, the next candidate is rejected as
  `RANKED_OUT` before the risk gate is ever reached.
- A seeded sweep over position counts × heat levels found ZERO
  configurations producing both codes at one timestamp; the full-window
  replay through `run_cycle` confirms: no real-data timestamp carries both.

This is a property of the LOCKED logic, not a gap in the test. Forcing both
codes at one `bar_time` would require altering or bypassing locked strategy
logic — forbidden. The four-layer acceptance scenario therefore exercises
all four strategic layers across TWO crafted timestamps in one scenario run
through the same cycle path:

- **T_A = 2025-05-29 13:30 ET** (max-heat): 4 open, heat 4.04% > 4%.
  NET → `SECTOR_CAP` (AI_SOFTWARE already has 2 open), AVGO → `RISK_CAP`,
  NVDA → `RISK_CAP`. (This is the risk gate's whole point: it only engages
  at max-heat moments.)
- **T_B = 2025-06-16 13:30 ET** (contested): 3 open (2× SEMIS), 3 candidates.
  AMAT → `SECTOR_CAP` (SEMIS already has 2 open), PLTR → `TAKEN`,
  NVDA → `RANKED_OUT` (contested bar, 3 candidates, 1 free, top-1 cutoff).

Real signals both times (NVDA/AVGO/NET at T_A: RS ≈ 0.0361/0.0400/0.0772;
NVDA/PLTR/AMAT at T_B: RS ≈ 0.0417/0.0655/0.1091) through `evaluate_frame`.
Every decision replays exactly from packet + prior state
(`replay_portfolio_decision`, `exact: True`).

## Acceptance evidence (pine_live/tests/test_slice4.py, 11 tests)

- (a) All 29 slice-1..3 tests still green → 40/40 pass.
- (b) Determinism: byte-identical rerun from restored state; symbol-order
  independence (shuffled order + extra no-signal symbol + mixed case →
  identical decisions and state). `universe_order` follows sorted symbols.
- (c) The four-layer contested scenario above: all four layers visible in
  the packet log, every decision replayable exactly.
- (d) Full-window aggregate parity: the entire research window driven
  through `run_cycle` (delivery enabled) reproduces locked C1 EXACTLY —
  143 trades, +0.337R/trade, +52.25%, 31.63% DD, Calmar 1.65,
  TAKEN=143, RANKED_OUT=94, SECTOR_CAP=16, NO_SLOT=0, RISK_CAP=10 — with
  mutual exclusivity pinned on real data (no timestamp with both codes).
  The cycle's own evaluation agrees with the research candidate set on
  every bar (each contender's packet decision is `signal` with the
  research signal id; entry/stop/TP1 and RS match the reference trade).
  143 paper alerts, 263 dedup claims (one per finalized decision).
- (e) Failure drills: frame-provider exception → logged skip, rest proceed;
  assertion-refusing frame (duplicate bar timestamps) → logged skip, rest
  proceed; unknown-sector symbol with a real signal → whole timestamp
  refused, exact rollback (positions/counters/events identical; clock
  accounting advances — documented fail-closed semantics), refusal logged,
  delivery never engaged.
- (f) Static: `multicycle.py` has no trading surface and no
  remote-notification wiring (default sender is the paper one);
  `dedup.py`/`alerts.py` re-proven stdlib-only; fault injection through
  `run_cycle` (raising sender) leaves state and decisions byte-identical.

## What remains unbuilt (explicit)

- Slice 5: live exit generation. `run_cycle` accepts only externally
  supplied exit events; it never invents exits.
- Slice 6: the Part-B reconciliation job against the canonical reference.
- Real notification wiring (the outbox is local paper only by design).
- Trading / order integration. Real-money deployment is not authorized.

Agreed sequence after slice 4: live exit evaluation → reconciliation
against canonical reference → the eight-week paper-only phase. Mike decides
whether anything advances beyond paper.
