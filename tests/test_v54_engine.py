"""Tests for v54_engine.py.

The critical invariant: V5.3's score must never determine V5.4 eligibility.
test_score_cannot_change_v54_eligibility pins this by running the same
market data under a vetoed V5.3 score and a passing V5.3 score and
asserting every V5.4-determined field is identical.
"""

import os
import sys
from unittest import mock

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import v54_engine as eng
import v54_rules

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "backtest_cache", "v3")


def _series(**kw):
    base = {"EMA9": 105.0, "EMA21": 104.0, "EMA55": 100.0, "EMA200": 90.0}
    base.update(kw)
    return pd.Series(base)


# ---- pure triggers -----------------------------------------------------

def test_pure_triggers_pullback():
    last = _series()
    prev = _series(EMA21=103.5, EMA55=100.2, EMA9=104.5)
    t = eng._pure_setup_triggers(last, prev, price=104.5, e9=105.0, e21=104.0,
                                 e55=100.0, e200=90.0, adx=25.0, above_vwap=True)
    assert t["pullback_buy"] is True
    assert t["exit_signal"] is False


def test_pure_triggers_fresh_cross():
    last = _series(EMA21=100.5, EMA55=100.0)
    prev = _series(EMA21=99.8, EMA55=100.0)
    t = eng._pure_setup_triggers(last, prev, price=101.0, e9=101.5, e21=100.5,
                                 e55=100.0, e200=90.0, adx=25.0, above_vwap=True)
    assert t["fresh_buy"] is True


def test_pure_triggers_exit_on_break():
    last = _series()
    t = eng._pure_setup_triggers(last, last, price=99.0, e9=105.0, e21=104.0,
                                 e55=100.0, e200=90.0, adx=25.0, above_vwap=True)
    assert t["exit_signal"] is True
    assert t["pullback_buy"] is False


def test_pure_triggers_take_no_score_input():
    import inspect
    params = inspect.signature(eng._pure_setup_triggers).parameters
    assert "score" not in params, "score must not be an input to trigger logic"


# ---- score guardrail -----------------------------------------------------

def _synth_df(n=300, seed=11):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-06-01", periods=n, freq="4h", tz="UTC")
    drift = 100 * (1.0012 ** np.arange(n))
    close = drift * (1 + rng.normal(0, 0.003, n))
    return pd.DataFrame({
        "Open": close * (1 + rng.normal(0, 0.001, n)),
        "High": close * 1.004,
        "Low": close * 0.996,
        "Close": close,
        "Volume": np.full(n, 1_000_000.0),
    }, index=idx)


def _patched_classify(score, state, entry):
    real = eng.m53.classify_symbol

    def _fake(symbol, theme, df, market_df, market_regime, timeframe):
        row = real(symbol, theme, df, market_df, market_regime, timeframe)
        row = dict(row)
        row["score"] = score
        row["rank_score"] = score
        row["state"] = state
        row["entry"] = entry
        return row

    return mock.patch.object(eng.m53, "classify_symbol", _fake)


def test_score_cannot_change_v54_eligibility():
    df = _synth_df()
    regime = {"gate": "BLOCK", "regime": "RISK-OFF", "score": 35}
    kwargs = dict(symbol="SYNTH", theme="Test", df=df, market_df=None,
                  market_regime=regime, timeframe="4h",
                  daily_df=None, weekly_df=None)
    with _patched_classify(score=1, state="NEUTRAL", entry="NO"):
        vetoed = eng.v54_classify(**kwargs)
    with _patched_classify(score=99, state="PULLBACK BUY", entry="YES"):
        passed = eng.v54_classify(**kwargs)
    for field in ("state", "entry", "protection", "v54_eligible",
                  "v54_grade", "v54_grade_label"):
        assert vetoed[field] == passed[field], (
            f"V5.3 score leaked into V5.4 decision via {field}: "
            f"{vetoed[field]!r} != {passed[field]!r}"
        )


def test_v53_fields_logged_for_control():
    df = _synth_df()
    regime = {"gate": "CONFIRM", "regime": "RISK-ON", "score": 80}
    row = eng.v54_classify(symbol="SYNTH", theme="Test", df=df, market_df=None,
                           market_regime=regime, timeframe="4h")
    assert row is not None
    for key in ("v53_state", "v53_entry", "v53_score", "v53_would_veto", "score"):
        assert key in row, f"missing control/logging field {key}"
    assert row["signal_id"].startswith("v54:")
    assert v54_rules.V54_RULE_VERSION in row["signal_id"]


# ---- trend-state helper ---------------------------------------------------

def test_trend_state_unknown_on_short_data():
    idx = pd.date_range("2026-01-01", periods=50, freq="1D", tz="UTC")
    df = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0,
                       "Volume": 1.0}, index=idx)
    assert eng._v54_trend_state(df, "1d") == "unknown"
    assert eng._v54_trend_state(None, "1d") == "unknown"


# ---- qualified filter keeps C ---------------------------------------------

def test_qualified_keeps_all_grades_including_c():
    rows = [
        {"v54_eligible": True, "v54_grade": "A"},
        {"v54_eligible": True, "v54_grade": "B"},
        {"v54_eligible": True, "v54_grade": "C"},
        {"v54_eligible": False, "v54_grade": None},
    ]
    q = eng.v54_qualified_signals(rows)
    assert [r["v54_grade"] for r in q] == ["A", "B", "C"]


# ---- envelope ---------------------------------------------------------------

def test_envelope_namespace_and_grade_counts():
    rows = [
        {"v54_eligible": True, "v54_grade": "A", "symbol": "X"},
        {"v54_eligible": True, "v54_grade": "C", "symbol": "Y"},
    ]
    regime = {"gate": "BLOCK", "signal_bar_close_at": "2026-09-14T16:00:00-04:00"}
    env = eng.v54_envelope(rows, regime, "4h", "180d")
    assert env["scanner_version"] == "5.4"
    assert env["rule_version"] == v54_rules.V54_RULE_VERSION
    assert env["signal_id"].startswith("v54:")
    assert env["grades"] == {"A": 1, "B": 0, "C": 1}
    assert env["count"] == 2
    assert "latest_buy_now" not in str(env)


# ---- real cached data smoke test (no network) --------------------------------

def test_classify_on_real_cached_bars():
    df = pd.read_pickle(os.path.join(CACHE, "h4_NVDA.pkl"))
    market_df = pd.read_pickle(os.path.join(CACHE, "h4_QQQ.pkl"))
    daily_df = pd.read_pickle(os.path.join(CACHE, "d1_5y_NVDA.pkl"))
    weekly_df = pd.read_pickle(os.path.join(CACHE, "w1_NVDA.pkl"))
    regime = {"gate": "BLOCK", "regime": "RISK-OFF", "score": 35}
    row = eng.v54_classify("NVDA", "AI Infrastructure", df, market_df, regime,
                           "4h", daily_df, weekly_df)
    assert row is not None
    assert row["v54_grade"] in ("A", "B", "C", None)
    assert row["daily_trend"] in ("confirmed", "not_confirmed", "unknown")
    assert row["weekly_trend"] in ("confirmed", "not_confirmed", "unknown")
    assert row["market_gate"] == "BLOCK"
    # structural consistency: entry YES implies the V5.3 structural contract
    import scanner_rules as sr
    if row["entry"] == "YES":
        assert sr.is_structural_candidate(row)
