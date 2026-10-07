"""Live Pine V3.6 path — SLICES 1+2+3+4+5.

Paper-only. The only side effects are decision packets, bar snapshots,
dedup/action logs, and the local paper alert outbox. No trading, no order
execution, no real notifications.

The live path CALLS the canonical reference functions by import
(pine_backtest.pine_buy_signal / add_pine_indicators,
 scanner_rules.resample_closed_4h / bar_close_at,
 masterscanner_api.download_data, pine_ranking RS_LOOKBACK,
 pine_signal_quality.bench_ret, pine_exposure.SECTION map,
 pine_stack.simulate_stack ordering) and never reimplements them.
Slice 5's exit walk (exits.py) is a character-faithful extraction of the
reference manage block inside pine_backtest.gen_pine_trades — the only
reference logic with no standalone function to import — pinned by a
263-trade differential proof rather than by import.

Locked stack (4 components): V3.6 entries/exits + rs_top2 ranking +
E1 sector cap + 5% portfolio-risk gate. Slice 3 adds duplicate suppression
(dedup.py) and paper alert delivery (alerts.py) as causally-separated
downstream layers: they import stdlib ONLY and cannot influence decisions.
Slice 4 runs the multi-symbol cycle (multicycle.py). Slice 5 evaluates
live exits before entries (exits.py + exit packets + exit replay).

Real alert wiring (phone/chat/email) is NOT built — it needs Mike's
explicit go-ahead.
"""
