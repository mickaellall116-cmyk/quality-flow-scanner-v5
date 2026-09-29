"""Pine V3.6 paper-trading phase — production dress rehearsal.

Paper ONLY: no orders, no broker integration, no real money. This package
drives the frozen V3.6 stack (pine_live.multicycle.run_cycle with
signal_bar="previous", live_exits=True) on a live data feed, logs every
decision/fill/rejection to an append-only ledger, replays every packet
against the canonical reference (halt on any category 2-7 mismatch), and
answers the three paper-phase questions:

  1. Does the system behave exactly as specified?
  2. Does execution remain within the tested cost envelope?
  3. Is realized behavior statistically plausible vs the validated backtest?

Nothing here is strategy research: no parameters change, no new filters,
no optimizations. New code only — no existing pine_live/ module is
modified by this package.
"""
