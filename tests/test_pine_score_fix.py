"""Regression tests for the NumPy boolean-addition trendScore bug (2026-09-20).

Bug: pine_backtest.pine_buy_signal computed the 0-5 trend score as a raw
sum of NumPy booleans. With NumPy 1.26.4, `(np_bool)+(np_bool)+...`
collapses to a single Boolean, so `score >= 4` and `score >= 3` were never
true and confirmed/ready entries were dead in every run to date.

The fix casts each condition to int before summing, in both
pine_backtest.pine_buy_signal (canonical decision) and
pine_live.decompose_signal (the read-only mirror).

These tests pin the correct behavior:
  - trend_score returns a true 0-5 integer for crafted bars
  - confirmedBuy and readyBuy can actually become True
  - the decompose mirror agrees with the canonical decision
"""

import os
import sys

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from pine_backtest import pine_buy_signal  # noqa: E402
from pine_live.decompose import decompose_signal  # noqa: E402

COLS = ["Open", "High", "Low", "Close", "Volume",
        "e9", "e21", "e55", "e200", "atr", "atr_base", "atr_ratio",
        "adx", "vol_ma"]


def bar(close=122.0, vol=1000.0, vol_ma=800.0, e9=120.0, e21=110.0,
        e55=100.0, e200=90.0, atr=2.0, atr_ratio=1.2, adx=30.0,
        high=None, low=None, open_=None):
    high = close + 1.0 if high is None else high
    low = close - 1.0 if low is None else low
    open_ = close - 0.5 if open_ is None else open_
    return {"Open": open_, "High": high, "Low": low, "Close": close,
            "Volume": vol, "e9": e9, "e21": e21, "e55": e55, "e200": e200,
            "atr": atr, "atr_base": atr / atr_ratio, "atr_ratio": atr_ratio,
            "adx": adx, "vol_ma": vol_ma}


def make_df(*rows):
    return pd.DataFrame([dict(r) for r in rows], columns=COLS)


def score_bar(n_true):
    """Build a bar with exactly n_true of the 5 trend-score conditions true.

    Conditions: e9>e21 | e21>e55 | close>e200 | adx>25 | atr_ratio>1.
    The first n_true conditions are made true, the rest false.
    """
    b = bar()
    # reset to all-false baseline first
    b["e9"] = 90.0      # e9>e21: false (90 < 110)
    b["e21"] = 110.0
    b["e55"] = 120.0    # e21>e55: false
    b["Close"] = 80.0   # close>e200: false (80 < 90)
    b["e200"] = 90.0
    b["adx"] = 20.0     # adx>25: false
    b["atr_ratio"] = 0.9  # atr_ratio>1: false
    b["atr_base"] = b["atr"] / b["atr_ratio"]
    if n_true >= 1:
        b["e9"] = 120.0
    if n_true >= 2:
        b["e55"] = 100.0
    if n_true >= 3:
        b["Close"] = 122.0
    if n_true >= 4:
        b["adx"] = 30.0
    if n_true >= 5:
        b["atr_ratio"] = 1.2
        b["atr_base"] = b["atr"] / b["atr_ratio"]
    return b


def test_score_0():
    d = decompose_signal(make_df(bar(), score_bar(0), bar()), 1)
    assert d["trend_score"] == 0


def test_score_1():
    d = decompose_signal(make_df(bar(), score_bar(1), bar()), 1)
    assert d["trend_score"] == 1


def test_score_3():
    d = decompose_signal(make_df(bar(), score_bar(3), bar()), 1)
    assert d["trend_score"] == 3


def test_score_4():
    d = decompose_signal(make_df(bar(), score_bar(4), bar()), 1)
    assert d["trend_score"] == 4


def test_score_5():
    d = decompose_signal(make_df(bar(), score_bar(5), bar()), 1)
    assert d["trend_score"] == 5


def test_score_5_distinct_from_1():
    # The buggy version collapsed every positive score to Boolean True (1).
    d = decompose_signal(make_df(bar(), score_bar(5), bar()), 1)
    assert d["trend_score"] != 1
    assert isinstance(d["trend_score"], int)


def test_confirmed_can_fire():
    # score=5, close>e21, e21>e55, close>e200, volume>SMA20, not HOT
    b = bar(close=122.0, e9=120.0, e21=110.0, e55=100.0, e200=90.0,
            atr=2.0, atr_ratio=1.2, adx=30.0)
    df = make_df(bar(), b, bar())
    d = decompose_signal(df, 1)
    assert d["trend_score"] == 5
    assert d["confirmed"] is True
    assert pine_buy_signal(df, 1) is True
    assert d["reference_decision"] is True


def test_ready_can_fire():
    # prev bar: close<e21, close>e55, e21>e55, atr_ratio>0.85 (ready state)
    prev = bar(close=105.0, e9=100.0, e21=110.0, e55=100.0, e200=90.0,
               atr=2.0, atr_ratio=1.0, adx=20.0)
    # current bar: close>e21, score=3 (conds 1,2,3), volume ok, not HOT
    cur = bar(close=115.0, e9=112.0, e21=110.0, e55=100.0, e200=90.0,
              atr=2.0, atr_ratio=0.9, adx=20.0)
    df = make_df(bar(), prev, cur, bar())
    d = decompose_signal(df, 2)
    assert d["trend_score"] == 3
    assert d["ready_prev"] is True
    assert d["ready_buy"] is True
    assert pine_buy_signal(df, 2) is True
    assert d["reference_decision"] is True


def test_mirror_matches_canonical_on_random_bars():
    # The mirror and the canonical decision must never disagree.
    import numpy as np
    rng = np.random.default_rng(7)
    rows = []
    for _ in range(12):
        rows.append(bar(
            close=float(rng.uniform(80, 140)),
            e9=float(rng.uniform(80, 140)), e21=float(rng.uniform(80, 140)),
            e55=float(rng.uniform(80, 140)), e200=float(rng.uniform(80, 140)),
            atr=float(rng.uniform(1, 5)), atr_ratio=float(rng.uniform(0.5, 1.5)),
            adx=float(rng.uniform(5, 50)), vol=float(rng.uniform(200, 2000)),
            vol_ma=float(rng.uniform(200, 2000)),
            high=float(rng.uniform(130, 150)), low=float(rng.uniform(60, 80)),
        ))
    df = make_df(*rows)
    for i in range(1, len(df) - 1):
        d = decompose_signal(df, i)
        assert d["decision"] == pine_buy_signal(df, i), f"bar {i} diverged"
        assert 0 <= d["trend_score"] <= 5, f"bar {i} score out of range"
