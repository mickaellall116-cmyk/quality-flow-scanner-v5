"""Regression: SPY daily benchmark must be UTC-normalized before rs_score.

On 2026-09-20 the paper runner HALTed with
    TypeError: Cannot compare tz-naive and tz-aware datetime-like objects
because download_spy() returned the raw yfinance daily frame, whose index is
tz-naive, while crypto 4h frames are tz-aware UTC. The first contender of the
corrected paper phase then crashed in rs_score -> bench_ret.searchsorted.

Fix: download_spy() localizes a naive daily index to UTC (the contract
rs_score's docstring already requires: "spy_daily: daily SPY frame
(UTC index, adjusted closes) or None"). Plumbing only; strategy untouched.

Run: cd ~/workspace/quality-flow-scanner-v5 && \\
     python3 -m pytest pine_live/tests/test_spy_tz_regression.py -q
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import masterscanner_api
from pine_live.paper.runner import WakeUp
from pine_live.ranking import rs_score


def _naive_spy_daily(n: int = 380) -> pd.DataFrame:
    """Mimics yfinance 1d output: tz-naive DatetimeIndex.

    Sized to cover 2026-09 crypto bar dates so bench_ret finds a span.
    """
    idx = pd.date_range("2025-06-01", periods=n, freq="B")
    assert idx.tz is None
    close = 500.0 * (1.001 ** np.arange(n))
    return pd.DataFrame({"Open": close, "High": close, "Low": close,
                         "Close": close, "Volume": 1_000}, index=idx)


def _aware_crypto_4h(n: int = 30) -> pd.DataFrame:
    """Mimics the resampled crypto 4h frame: tz-aware UTC index."""
    idx = pd.date_range("2026-09-18", periods=n, freq="4h", tz="UTC")
    close = 100.0 * (1.002 ** np.arange(n))
    return pd.DataFrame({"Open": close, "High": close, "Low": close,
                         "Close": close, "Volume": 1_000}, index=idx)


def test_download_spy_normalizes_naive_index_to_utc(tmp_path, monkeypatch):
    monkeypatch.setattr(masterscanner_api, "download_data",
                        lambda *a, **k: _naive_spy_daily())
    spy = WakeUp(str(tmp_path)).download_spy()
    assert isinstance(spy.index, pd.DatetimeIndex)
    assert str(spy.index.tz) == "UTC"


def test_download_spy_leaves_aware_index_alone(tmp_path, monkeypatch):
    frame = _naive_spy_daily()
    frame.index = frame.index.tz_localize("America/New_York")
    monkeypatch.setattr(masterscanner_api, "download_data",
                        lambda *a, **k: frame)
    spy = WakeUp(str(tmp_path)).download_spy()
    assert str(spy.index.tz) == "America/New_York"


def test_rs_score_no_tz_crash_after_normalization():
    spy = _naive_spy_daily()
    spy.index = spy.index.tz_localize("UTC")  # what download_spy now guarantees
    bars = _aware_crypto_4h(30)
    score, reason = rs_score(bars, 29, spy)
    assert reason is None
    assert np.isfinite(score)


def test_rs_score_crashes_on_raw_naive_spy():
    """Documents the original bug: naive SPY + aware crypto -> TypeError."""
    spy = _naive_spy_daily()
    bars = _aware_crypto_4h(30)
    with pytest.raises(TypeError):
        rs_score(bars, 29, spy)
