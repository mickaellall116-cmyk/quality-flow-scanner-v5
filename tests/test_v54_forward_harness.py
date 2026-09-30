"""Outage/recovery containment tests for the PR #7 amendment.

Covers ChatGPT's four required cases (bridge review 2026-09-30):
 1. one-cycle pending outage -> entry still fills (timely, same bar)
 2. multi-cycle pending outage -> entry voided, never backfilled
 3. recovery with multiple historical bars -> even a would-be-winning
    stale fill is refused (no phantom fill)
 4. open-position chronological exit catch-up unchanged after outage

Frozen rule under test: a pending entry whose intended next-bar execution
was missed because data was unavailable / the cycle budget was exhausted
is recorded as `entry_unexecutable_after_outage` and never filled
retrospectively. The original signal record is preserved for audit.
"""

import os
import sys
import tempfile

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import v54_forward_harness as hz
from v54_forward_log import ForwardLog


def _outage_df():
    # 6 4H bars. Signal on bar 0; bar 1 is the intended fill bar
    # (open 101 > stop 95). Bar 3 rallies through TP1 (high 110), so a
    # stale fill there would be a phantom winner - it must be refused.
    idx = pd.date_range("2026-01-06 09:30", periods=6, freq="4h",
                        tz="America/New_York")
    return pd.DataFrame({
        "Open":   [100.0, 101.0, 102.0, 103.0, 104.0, 105.0],
        "High":   [101.0, 102.0, 103.0, 110.0, 106.0, 107.0],
        "Low":    [99.0, 100.0, 101.0, 102.0, 103.0, 104.0],
        "Close":  [100.5, 101.5, 102.5, 109.0, 105.0, 106.0],
        "Volume": [1e6] * 6,
    }, index=idx)


def _stop_df():
    # Fill at bar 1 open (101 > stop 95); bar 3 tags the structural stop
    # (low 94) with no TP1 hit before it.
    idx = pd.date_range("2026-01-06 09:30", periods=5, freq="4h",
                        tz="America/New_York")
    return pd.DataFrame({
        "Open":   [100.0, 101.0, 102.0, 103.0, 104.0],
        "High":   [101.0, 102.0, 103.0, 103.5, 104.5],
        "Low":    [99.0, 100.5, 101.5, 94.0, 103.0],
        "Close":  [100.5, 101.5, 102.5, 95.5, 103.5],
        "Volume": [1e6] * 5,
    }, index=idx)


def _row(ts0):
    return {
        "signal_id": f"v54:SYN:4h:{ts0.isoformat()}:v",
        "symbol": "SYN", "stop": 95.0, "tp1": 108.0,
        "v54_eligible": True, "v54_grade": "A", "v54_grade_label": "EARLY",
        "signal_bar_start_at": ts0.isoformat(),
        "signal_bar_close_at": ts0.isoformat(),
        "market_gate": "BLOCK", "market_regime": "RISK-OFF",
        "rel_vol": 1.1, "daily_trend": "not_confirmed",
        "weekly_trend": "not_confirmed", "risk_reward": 2.4,
        "confirmation_15m": False,
    }


def _fresh(tmp):
    state = hz.blank_state()
    log = ForwardLog(os.path.join(tmp, "f.jsonl"))
    tracker = hz._tracker_with_sink(log)
    return state, log, tracker


class _ScriptedFeed:
    """get_4h callable that can be switched into outage per cycle."""

    def __init__(self, df):
        self.df = df
        self.outage = False

    def __call__(self, symbol):
        if self.outage:
            raise hz.DataUnavailable(symbol, "cycle_budget_exhausted",
                                     "scripted test outage")
        return self.df


def _now(s):
    # Pin wall-clock to the fictional bar timeline (bars are America/New_York).
    return pd.Timestamp(s, tz="America/New_York")


def _cycle(df_full, row_or_rows, state, log, tracker, feed, n_bars, now=None):
    feed.df = df_full.iloc[:n_bars]
    ctx = hz.CycleContext(
        scan_rows=row_or_rows, regime={"gate": "BLOCK", "regime": "RISK-OFF",
                                       "score": 35},
        get_4h=feed, get_market_4h=lambda: df_full.iloc[:0], now=now)
    return hz.run_cycle(ctx, state, log, tracker)


def test_pending_entry_one_cycle_outage_still_fills_timely():
    """One deferred cycle that costs no fill bar: the entry still fills at
    the intended bar's open. The data-missed flag alone never voids."""
    tmp = tempfile.mkdtemp()
    df = _outage_df()
    row = _row(df.index[0])
    sid = row["signal_id"]
    state, log, tracker = _fresh(tmp)
    feed = _ScriptedFeed(df.iloc[:1])

    s1 = _cycle(df, [row], state, log, tracker, feed, 1)
    assert s1["new_signals"] == 1 and s1["opened"] == 0
    assert sid in state["pending"], "fill bar not complete yet -> stays pending"

    feed.outage = True
    # Fill bar is 13:30-17:30 ET; the blind deferral at 14:00 ET lands while
    # it is still forming, so the fill stays timely.
    s2 = _cycle(df, [], state, log, tracker, feed, 1,
                now=_now("2026-01-06 14:00"))
    assert s2["opened"] == 0
    assert state["pending"][sid].get("data_missed_while_pending") is True
    assert any(e["event"] == "entry_data_deferred"
               for e in log.get_events(sid))

    feed.outage = False
    s3 = _cycle(df, [], state, log, tracker, feed, 2)
    assert s3["opened"] == 1, "one lost cycle must not void a still-timely entry"
    assert s3["entries_unexecutable"] == []
    assert tracker.get(sid)["entry"] == 101.0
    assert not any(e["event"] == "entry_unexecutable_after_outage"
                   for e in log.get_events(sid))


def test_pending_entry_multi_cycle_outage_voided_not_backfilled():
    """Two deferred cycles, then recovery with three new bars: the intended
    next-bar execution was missed -> voided, never filled."""
    tmp = tempfile.mkdtemp()
    df = _outage_df()
    row = _row(df.index[0])
    sid = row["signal_id"]
    state, log, tracker = _fresh(tmp)
    feed = _ScriptedFeed(df.iloc[:1])

    _cycle(df, [row], state, log, tracker, feed, 1)
    assert sid in state["pending"]

    feed.outage = True
    _cycle(df, [], state, log, tracker, feed, 1)
    _cycle(df, [], state, log, tracker, feed, 1)
    assert state["pending"][sid].get("data_missed_while_pending") is True

    feed.outage = False
    s4 = _cycle(df, [], state, log, tracker, feed, 4)
    assert s4["opened"] == 0, "missed entry must never be backfilled"
    assert s4["entries_unexecutable"] == [sid]
    assert sid not in state["pending"]
    assert tracker.get(sid) is None

    evs = log.get_events(sid)
    kinds = [e["event"] for e in evs]
    assert "entry_unexecutable_after_outage" in kinds
    assert kinds.count("entry_data_deferred") == 2
    # original signal/pending record preserved for audit
    assert log.get_signal(sid) is not None
    assert "pending_entry" in kinds


def test_pending_entry_stale_single_bar_voided_by_timing_state():
    """Mike's edge case: the intended fill bar starts 13:30 ET and its
    canonical close is 16:00 ET (session bar, not a full 4h bar). A Yahoo
    outage at 16:30 ET leaves the fill bar complete while blind, and data
    recovers before a second bar completes, so only one new bar exists.
    The bar-count proxy cannot catch this, and a naive start+4h rule
    (17:30 > 16:30) would wrongly allow the stale fill. The canonical
    bar_close_at (16:00 <= 16:30) must void it."""
    tmp = tempfile.mkdtemp()
    df = _outage_df()
    row = _row(df.index[0])
    sid = row["signal_id"]
    state, log, tracker = _fresh(tmp)
    feed = _ScriptedFeed(df.iloc[:1])

    _cycle(df, [row], state, log, tracker, feed, 1)
    assert sid in state["pending"]

    feed.outage = True
    # Both blind deferrals land after the canonical 16:00 ET close but
    # before the naive 17:30 ET close a start+4h rule would assume.
    _cycle(df, [], state, log, tracker, feed, 1,
           now=_now("2026-01-06 16:30"))
    _cycle(df, [], state, log, tracker, feed, 1,
           now=_now("2026-01-06 17:00"))
    feed.outage = False

    # Recovery: bars 0-1 only; the next bar has not completed yet.
    s = _cycle(df, [], state, log, tracker, feed, 2)
    assert s["opened"] == 0, "stale single-bar fill must be refused"
    assert s["entries_unexecutable"] == [sid]
    assert sid not in state["pending"]
    assert tracker.get(sid) is None

    voids = [e for e in log.get_events(sid)
             if e["event"] == "entry_unexecutable_after_outage"]
    assert len(voids) == 1
    assert voids[0]["stale_basis"] == "fill_bar_completed_while_blind"
    assert voids[0]["newer_completed_bars"] == 0
    assert voids[0]["intended_fill_open"] == 101.0
    assert log.get_signal(sid) is not None, "signal record preserved"


def test_pending_entry_recovery_many_historical_bars_no_phantom_fill():
    """Long outage, then the full window returns at once (backfilled bars
    included). The stale fill bar rallied through TP1, so the refused fill
    would have been a winner - it must still be refused."""
    tmp = tempfile.mkdtemp()
    df = _outage_df()
    row = _row(df.index[0])
    sid = row["signal_id"]
    state, log, tracker = _fresh(tmp)
    feed = _ScriptedFeed(df.iloc[:1])

    _cycle(df, [row], state, log, tracker, feed, 1)

    feed.outage = True
    for _ in range(4):
        _cycle(df, [], state, log, tracker, feed, 1)
    feed.outage = False

    s = _cycle(df, [], state, log, tracker, feed, 6)
    assert s["opened"] == 0
    assert tracker.get(sid) is None, "no phantom position from stale bars"
    assert s["entries_unexecutable"] == [sid]

    voids = [e for e in log.get_events(sid)
             if e["event"] == "entry_unexecutable_after_outage"]
    assert len(voids) == 1
    assert voids[0]["intended_fill_open"] == 101.0
    assert voids[0]["newer_completed_bars"] == 4
    assert log.get_signal(sid) is not None, "signal record preserved"


def test_open_position_exit_catchup_chronological_after_outage():
    """Open positions keep chronological bar-by-bar exit processing across
    an outage: defer explicitly, then catch up in order on recovery."""
    tmp = tempfile.mkdtemp()
    df = _stop_df()
    row = _row(df.index[0])
    sid = row["signal_id"]
    state, log, tracker = _fresh(tmp)
    feed = _ScriptedFeed(df.iloc[:2])

    s1 = _cycle(df, [row], state, log, tracker, feed, 2)
    assert s1["opened"] == 1 and tracker.get(sid)["entry"] == 101.0

    feed.outage = True
    s2 = _cycle(df, [], state, log, tracker, feed, 2)
    s3 = _cycle(df, [], state, log, tracker, feed, 2)
    assert s2["closed"] == [] and s3["closed"] == []
    assert tracker.get(sid)["status"] != "closed", "no invented exits"
    assert any(e["event"] == "exit_data_deferred"
               for e in log.get_events(sid))

    feed.outage = False
    s4 = _cycle(df, [], state, log, tracker, feed, 4)
    assert s4["closed"] == [sid]
    close = log.get_close(sid)
    assert close is not None and close["exit_reason"] == "stop"
    # stopped on bar 3 (low 94 < stop 95), walked chronologically
    pos = tracker.get(sid)
    assert pos["status"] == "closed"
    assert pos["exit"]["exit_bar"] == df.index[3].isoformat()
    rec = [e for e in log.get_events(sid)
           if e["event"] == "data_outage_recovered"]
    assert len(rec) == 1 and rec[0]["bars_caught_up"] >= 2
