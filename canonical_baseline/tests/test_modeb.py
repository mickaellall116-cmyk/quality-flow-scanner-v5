"""Unit tests for the canonical Mode B execution engine.

Each test uses a synthetic bar sequence to prove one frozen Mode B rule.
Conventions used throughout: entry=100.0, stop=90.0 (risk=10.0), tp1=120.0
(risk_frac=0.1), so R(px) = (px-100)/10.
"""

import sys
import os

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modeb_engine import run_trade, MAX_HOLD_BARS  # noqa: E402

E, S, T = 100.0, 90.0, 120.0  # entry / stop / tp1


def bars(rows, start="b0"):
    """rows: list of (open, high, low, close). Index labels b0, b1, ..."""
    df = pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"],
                      index=[f"b{i}" for i in range(len(rows))])
    return df


def flat(n, px=100.0):
    return [(px, px, px, px)] * n


# ---------------------------------------------------------------------------
# Rule 1: structural stop always active from the entry bar
# ---------------------------------------------------------------------------

def test_stop_active_on_entry_bar():
    # Entry bar itself can stop the trade (live processes the entry bar first).
    df = bars([(100, 101, 89, 95)])
    r = run_trade(0, E, S, T, df)
    assert r.exit_reason == "STOP"
    assert r.live_reason == "stop"
    assert r.exit_bar == "b0"
    assert r.exit_px == S
    assert r.blended_r == -1.0
    assert r.bars_held == 1


def test_full_position_stop_before_tp1():
    df = bars([
        (100, 105, 98, 102),   # b0: entry bar, nothing
        (102, 108, 95, 100),   # b1: nothing
        (100, 104, 89, 92),    # b2: low 89 <= stop 90 -> stop
    ])
    r = run_trade(0, E, S, T, df)
    assert r.exit_reason == "STOP"
    assert r.exit_px == S
    assert r.blended_r == -1.0
    assert r.exit_bar == "b2"
    assert r.bars_held == 3
    assert r.tp1_taken is False
    assert r.partial_r is None and r.runner_r is None


# ---------------------------------------------------------------------------
# Rule 2: 50% at TP1 with correct R math
# ---------------------------------------------------------------------------

def test_tp1_takes_half_with_correct_r_math():
    df = bars([
        (100, 105, 98, 102),   # b0
        (102, 121, 101, 119),  # b1: high 121 >= tp1 120 -> TP1
        (119, 122, 89, 95),    # b2: runner stops
    ])
    r = run_trade(0, E, S, T, df)
    assert r.tp1_taken is True
    assert r.tp1_fill_px == T
    assert r.tp1_fill_bar == "b1"
    assert r.exit_reason == "TP1_THEN_STOP"
    assert r.live_reason == "runner-stop"
    assert r.exit_px == S
    # partial = 0.5 * R(120) = 0.5 * 2.0 = 1.0 ; runner = R(90) = -1.0
    assert r.partial_r == 1.0
    assert r.runner_r == -1.0
    # blended = 1.0 + 0.5 * (-1.0) = 0.5
    assert r.blended_r == 0.5
    assert r.bars_held == 3


def test_tp1_runner_rides_to_timeout_math():
    # TP1 at b1, then flat: runner survives to the 30-bar timeout.
    rows = [(100, 105, 98, 102), (102, 121, 101, 119)] + flat(28, 115)
    df = bars(rows)
    r = run_trade(0, E, S, T, df)
    assert r.tp1_taken is True
    assert r.exit_reason == "TIMEOUT"
    assert r.live_reason == "runner-time"
    assert r.exit_bar == "b29"          # 30th processed bar
    assert r.exit_px == 115.0
    # blended = 0.5*R(120) + 0.5*R(115) = 1.0 + 0.75 = 1.75
    assert r.partial_r == 1.0
    assert r.runner_r == 1.5
    assert r.blended_r == 1.75
    assert r.bars_held == 30


# ---------------------------------------------------------------------------
# Rule 3: +1R (unrealized, full position) arms Profit Protect — sticky
# ---------------------------------------------------------------------------

def test_plus_1r_arms_pp_and_is_sticky():
    df = bars([
        (100, 105, 98, 102),   # b0
        (102, 110, 101, 108),  # b1: high 110 -> R=1.0 -> arms
        (108, 109, 95, 96),    # b2: falls back, stays armed
    ])
    r = run_trade(0, E, S, T, df)
    assert r.pp_armed is True
    assert r.pp_arming_bar == "b1"
    assert r.reached_plus_1r is True
    assert [e for e in r.events if e["event"] == "profit_protect_armed"] \
        == [{"event": "profit_protect_armed", "bar": "b1"}]
    assert r.exit_reason == "OPEN"  # no stop/TP1/EXIT/timeout hit


def test_no_arm_below_1r():
    df = bars([(100, 109.9, 98, 105)] * 5)
    r = run_trade(0, E, S, T, df)
    assert r.pp_armed is False
    assert r.reached_plus_1r is False


def test_arm_on_tp1_bar_counts():
    # Arming is evaluated before the TP1 check on the same bar (live :189-197
    # runs before :153-162), so a bar that both reaches +1R and TP1 arms.
    df = bars([
        (100, 121, 98, 119),   # b0: high 121 -> +1R armed AND TP1 taken
        (119, 119, 118, 118),  # b1: flat runner
    ])
    r = run_trade(0, E, S, T, df)
    assert r.pp_armed is True
    assert r.pp_arming_bar == "b0"
    assert r.tp1_taken is True


# ---------------------------------------------------------------------------
# Rule 4: PP fills at the NEXT bar's open, not the arming/signalling bar
# ---------------------------------------------------------------------------

def test_pp_full_position_fills_next_bar_open():
    df = bars([
        (100, 105, 98, 102),    # b0
        (102, 111, 101, 109),   # b1: arms (+1R); EXIT signalled same bar
        (109, 112, 107, 108),   # b2: PP fills at b2's open
    ])
    states = [None, "EXIT", None]
    r = run_trade(0, E, S, T, df, scanner_states=states)
    assert r.exit_reason == "PP"
    assert r.live_reason == "scanner-exit"
    assert r.exit_bar == "b2"            # NOT the signalling bar b1
    assert r.exit_px == 109.0            # b2's open
    assert r.blended_r == 0.9            # full-position R(109)
    assert r.tp1_taken is False
    assert r.bars_held == 3


def test_pp_runner_fills_next_bar_open():
    df = bars([
        (100, 105, 98, 102),    # b0
        (102, 121, 101, 119),   # b1: TP1 taken; also arms (+1R via b1 high)
        (119, 122, 115, 120),   # b2: EXIT signalled (armed) -> pending
        (120, 121, 118, 119),   # b3: PP fills at b3's open
    ])
    states = [None, None, "EXIT", None]
    r = run_trade(0, E, S, T, df, scanner_states=states)
    assert r.exit_reason == "TP1_THEN_PP"
    assert r.live_reason == "runner-exit"
    assert r.exit_bar == "b3"
    assert r.exit_px == 120.0
    # blended = 0.5*R(120) + 0.5*R(120) = 1.0 + 1.0 = 2.0
    assert r.blended_r == 2.0
    assert r.bars_held == 4


def test_exit_ignored_before_arming():
    # EXIT scanner state with mfe < 1R must not set a pending exit.
    df = bars([
        (100, 105, 98, 102),
        (102, 106, 100, 104),   # EXIT but not armed
        (104, 107, 102, 105),
    ])
    states = [None, "EXIT", None]
    r = run_trade(0, E, S, T, df, scanner_states=states)
    assert r.exit_reason == "OPEN"
    assert r.pp_armed is False
    assert not any(e["event"] == "exit_signaled" for e in r.events)


def test_pending_pp_fill_takes_precedence_over_stop_on_fill_bar():
    # Once armed+signalled, the PP fill at next open wins even if the fill
    # bar gaps through the stop (live :141-147 fills and returns first).
    df = bars([
        (100, 105, 98, 102),    # b0
        (102, 111, 101, 109),   # b1: arms; EXIT signalled
        (80, 85, 75, 78),       # b2: gaps through stop — PP still fills at open
    ])
    states = [None, "EXIT", None]
    r = run_trade(0, E, S, T, df, scanner_states=states)
    assert r.exit_reason == "PP"
    assert r.exit_px == 80.0
    assert r.blended_r == -2.0  # R(80) = -2.0, NOT the -1.0 stop


# ---------------------------------------------------------------------------
# Rule 5: runner keeps the STRUCTURAL stop after TP1 (never breakeven)
# ---------------------------------------------------------------------------

def test_runner_keeps_structural_stop():
    df = bars([
        (100, 105, 98, 102),   # b0
        (102, 121, 101, 119),  # b1: TP1
        (119, 120, 95, 96),    # b2: dips below entry (breakeven would stop
                               #     here) but above stop -> runner survives
        (96, 98, 89, 90),      # b3: structural stop hit
    ])
    r = run_trade(0, E, S, T, df)
    assert r.exit_reason == "TP1_THEN_STOP"
    assert r.exit_bar == "b3"      # survived b2's dip below entry
    assert r.exit_px == S          # filled at the STRUCTURAL stop, not BE
    assert r.runner_r == -1.0
    assert r.blended_r == 0.5


def test_no_evaluation_on_tp1_bar_itself():
    # Even if the TP1 bar's low is below the stop, the stop is checked FIRST
    # (stop wins ties — tested below). Here the TP1 bar has no stop touch:
    # the runner must NOT be stopped on the TP1 bar by the dip to 95.
    df = bars([
        (100, 121, 95, 119),   # b0: TP1 taken; low 95 < entry but > stop
        (119, 120, 118, 119),
    ])
    r = run_trade(0, E, S, T, df)
    assert r.tp1_taken is True
    assert r.exit_reason == "OPEN"  # runner alive after the TP1 bar


# ---------------------------------------------------------------------------
# Rule 6: 30-bar timeout fires on the 30th processed bar (entry bar = #1)
# ---------------------------------------------------------------------------

def test_timeout_fires_on_30th_bar_at_close():
    df = bars(flat(30, 105.0))
    r = run_trade(0, E, S, T, df)
    assert r.exit_reason == "TIMEOUT"
    assert r.live_reason == "time"
    assert r.exit_bar == "b29"
    assert r.exit_px == 105.0
    assert r.blended_r == 0.5
    assert r.bars_held == 30


def test_no_timeout_before_30_bars():
    df = bars(flat(29, 105.0))
    r = run_trade(0, E, S, T, df)
    assert r.exit_reason == "OPEN"
    assert r.bars_held == 29


def test_timeout_binds_on_winners_too():
    # A runner that would otherwise ride forever is cut at bar 30.
    rows = [(100, 121, 101, 119)] + flat(29, 150.0)
    df = bars(rows)
    r = run_trade(0, E, S, T, df)
    assert r.exit_reason == "TIMEOUT"
    assert r.live_reason == "runner-time"
    assert r.exit_bar == "b29"
    assert r.bars_held == 30
    # blended = 0.5*R(120) + 0.5*R(150) = 1.0 + 2.5 = 3.5
    assert r.blended_r == 3.5


def test_stop_beats_timeout_on_bar_30():
    # Stop is evaluated before the timeout check on the same bar.
    rows = flat(29, 105.0) + [(105, 106, 89, 92)]
    df = bars(rows)
    r = run_trade(0, E, S, T, df)
    assert r.exit_reason == "STOP"
    assert r.exit_bar == "b29"
    assert r.bars_held == 30


# ---------------------------------------------------------------------------
# Rule 7: stop wins same-bar ties
# ---------------------------------------------------------------------------

def test_stop_wins_tie_full_position():
    df = bars([
        (100, 105, 98, 102),   # b0
        (102, 125, 89, 110),   # b1: high >= TP1 AND low <= stop -> STOP wins
    ])
    r = run_trade(0, E, S, T, df)
    assert r.exit_reason == "STOP"
    assert r.live_reason == "stop"
    assert r.tp1_taken is False
    assert r.blended_r == -1.0


def test_stop_wins_tie_on_entry_bar():
    df = bars([(100, 125, 89, 110)])
    r = run_trade(0, E, S, T, df)
    assert r.exit_reason == "STOP"
    assert r.tp1_taken is False


# ---------------------------------------------------------------------------
# Rule 8: gaps — live-faithful (primary) vs realistic variant
# ---------------------------------------------------------------------------

def test_gap_through_stop_live_fills_at_stop():
    # Live: v54_exit_tracker.py:151-152 — gap-through-stop fills AT THE STOP
    # PRICE (optimistic). Primary implementation must reproduce this.
    df = bars([
        (100, 105, 98, 102),   # b0
        (85, 88, 80, 82),      # b1: opens below the stop -> fills at stop
    ])
    r = run_trade(0, E, S, T, df)  # realistic_gaps=False
    assert r.realistic_gaps is False
    assert r.exit_reason == "STOP"
    assert r.exit_px == S          # NOT the 85 open
    assert r.blended_r == -1.0     # NOT R(85) = -1.5


def test_gap_through_stop_realistic_fills_at_open():
    df = bars([
        (100, 105, 98, 102),
        (85, 88, 80, 82),
    ])
    r = run_trade(0, E, S, T, df, realistic_gaps=True)
    assert r.realistic_gaps is True
    assert r.exit_reason == "STOP"
    assert r.exit_px == 85.0       # first tradable price beyond the stop
    assert r.blended_r == -1.5     # R(85) = (85-100)/10


def test_gap_through_stop_realistic_runner():
    df = bars([
        (100, 105, 98, 102),
        (102, 121, 101, 119),  # TP1
        (85, 88, 80, 82),      # runner gaps through stop
    ])
    r_live = run_trade(0, E, S, T, df)
    r_real = run_trade(0, E, S, T, df, realistic_gaps=True)
    assert r_live.exit_px == S and r_live.blended_r == 0.5
    assert r_real.exit_px == 85.0
    # blended = 0.5*R(120) + 0.5*R(85) = 1.0 - 0.75 = 0.25
    assert r_real.blended_r == 0.25


def test_intrabar_stop_touch_realistic_fills_at_stop():
    # Open above the stop, low touches it intrabar -> resting stop fills at
    # the stop price in BOTH conventions.
    df = bars([
        (100, 105, 98, 102),
        (95, 96, 89, 92),
    ])
    r = run_trade(0, E, S, T, df, realistic_gaps=True)
    assert r.exit_reason == "STOP"
    assert r.exit_px == S
    assert r.blended_r == -1.0


def test_gap_through_tp1_live_fills_at_tp1():
    # Live: the TP1 limit always credits the exact tp1 price, ignoring the
    # price improvement of a gap above it (conservative).
    df = bars([
        (100, 105, 98, 102),
        (130, 135, 128, 132),  # opens above TP1
        (132, 133, 131, 132),
    ])
    r = run_trade(0, E, S, T, df)
    assert r.tp1_taken is True
    assert r.tp1_fill_px == T      # NOT the 130 open
    assert r.partial_r is None    # still open (runner riding)


def test_gap_through_tp1_realistic_fills_at_open():
    df = bars([
        (100, 105, 98, 102),
        (130, 135, 128, 132),
        (132, 133, 89, 90),    # runner then stops
    ])
    r = run_trade(0, E, S, T, df, realistic_gaps=True)
    assert r.tp1_fill_px == 130.0
    assert r.partial_r == 1.5      # 0.5 * R(130) = 0.5 * 3.0
    # blended = 1.5 + 0.5 * R(90) = 1.5 - 0.5 = 1.0
    assert r.blended_r == 1.0


def test_gap_above_target_at_entry():
    # Entry fills at/above TP1 (e.g. a gap-up open) -> immediate close at the
    # entry price, blended 0. Live: open_position, v54_exit_tracker.py:92-95.
    df = bars([(130, 135, 128, 132)])
    r = run_trade(0, 130.0, 120.0, 125.0, df)
    assert r.exit_reason == "GAP_ABOVE_TARGET"
    assert r.live_reason == "gap-above-target"
    assert r.exit_px == 130.0
    assert r.blended_r == 0.0
    assert r.bars_held == 0
    assert r.tp1_taken is False


# ---------------------------------------------------------------------------
# Rule 9/10: entry conventions, mfe/mae, invalid trades
# ---------------------------------------------------------------------------

def test_entry_bar_counts_as_bar_1_and_mfe_mae_include_it():
    df = bars([
        (100, 112, 97, 110),   # b0: mfe=1.2 (arms), mae=-0.3
        (110, 111, 109, 110),
    ])
    r = run_trade(0, E, S, T, df)
    assert r.bars_held == 2
    assert r.mfe_r == 1.2
    assert r.mae_r == -0.3
    assert r.pp_armed is True
    assert r.pp_arming_bar == "b0"


def test_entry_at_or_below_stop_is_invalid():
    df = bars(flat(5))
    with pytest.raises(ValueError):
        run_trade(0, 90.0, 90.0, 120.0, df)
    with pytest.raises(ValueError):
        run_trade(0, 85.0, 90.0, 120.0, df)


def test_stop_never_moves_except_pp_or_timeout():
    # Stop is a constant: the runner is never stopped at breakeven or any
    # ratcheted level. Sweep: after TP1, only the structural stop (or PP /
    # timeout) can end the runner.
    df = bars([
        (100, 121, 101, 119),  # b0: TP1
        (119, 125, 100.5, 124),  # b1: low 100.5 (above breakeven) -> survives
        (124, 126, 100.1, 125),  # b2: still above stop -> survives
        (125, 126, 90.0, 95),    # b3: touches structural stop exactly
    ])
    r = run_trade(0, E, S, T, df)
    assert r.exit_reason == "TP1_THEN_STOP"
    assert r.exit_bar == "b3"
    assert r.exit_px == S


def test_entry_bar_idx_offsets_into_larger_frame():
    # entry_bar_idx may point mid-frame; earlier rows are ignored.
    rows = flat(5, 200.0) + [(100, 105, 98, 102), (102, 108, 89, 92)]
    df = bars(rows)
    r = run_trade(5, E, S, T, df)
    assert r.exit_reason == "STOP"
    assert r.exit_bar == "b6"
    assert r.bars_held == 2


def test_r_convention_full_position_pp():
    # Full-position PP exit: blended = R(exit_px) on the FULL position.
    df = bars([
        (100, 105, 98, 102),
        (102, 111, 101, 109),   # arms; EXIT
        (115, 118, 113, 116),   # fills at open 115
    ])
    r = run_trade(0, E, S, T, df, scanner_states=[None, "EXIT", None])
    assert r.blended_r == 1.5     # R(115) = 1.5, full position
    assert r.partial_r is None    # no scale-out happened
