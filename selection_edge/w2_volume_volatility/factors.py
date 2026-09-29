"""W2 factor computation library: F3 (dollar-volume expansion) and F4 (volatility
expansion), strict point-in-time.

Conventions (pre-registered in selection_edge/FACTOR_MENU.md):
- F3: 20-trading-day ADDV / 60-trading-day ADDV, endpoint = last COMPLETED
  daily bar as of signal time. Select ratio > 1.25.
- F4: 14-day ATR / 60-day median ATR, strict PIT on daily bars.
  Select ratio > 1.2.
- "Last completed daily bar as of signal time": daily bars are timestamped
  at 00:00 America/New_York of the trading day and complete at 16:00 ET.
  A signal at 13:30 ET therefore uses the PREVIOUS trading day's bar.
  (Matches the strict-PIT convention that fixed the sector-RS leak:
  never the signal-day daily close.)
- ATR: true range = max(H-L, |H-prevC|, |L-prevC|); 14-day ATR = trailing
  14-bar simple mean of TR (causal); denominator = trailing 60-bar median
  of the 14-day ATR series (causal).
- All math is computed once on the full causal series and read at the
  PIT index j; rolling windows use min_periods so values before warmup
  are NaN and those signals are marked uncomputable.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "..", "canonical_baseline"))
import simlib  # noqa: E402

TZ = "America/New_York"

# The 14 names: MASKED OUT of the working universe for all construction,
# threshold-setting, and evaluation. They appear here ONLY so the mask can
# be enforced programmatically. Never computed on, never tuned toward.
MASKED_14 = frozenset([
    "QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB", "ONDS", "DRAM",
    "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD",
])

_F3_CACHE = {}
_F4_CACHE = {}


def working_symbols():
    """117-name working set: 131-name PIT universe minus the masked 14."""
    uni = [u["symbol"] for u in simlib.load_universe()]
    ws = [s for s in uni if s not in MASKED_14]
    assert len(ws) == len(uni) - len(MASKED_14 & set(uni)), "mask mismatch"
    assert not (set(ws) & MASKED_14), "mask leak"
    return sorted(ws)


def last_completed_daily_pos(idx, t):
    """Positional index of the last completed daily bar as of timestamp t.

    Daily bars timestamped at 00:00 ET of the trading day complete at
    16:00 ET. Returns -1 if no completed bar exists.
    """
    t = pd.Timestamp(t).tz_convert(TZ)
    # last bar whose midnight timestamp is <= t
    j = idx.searchsorted(t, side="left") - 1
    if j < 0:
        return -1
    # if t falls on the same calendar day as bar j's date and the market
    # has not closed yet, bar j is incomplete -> step back one
    if idx[j].date() == t.date() and t.time() < pd.Timestamp("16:00").time():
        j -= 1
    return j


def f3_series(symbol, num_window=20, den_window=60):
    """Full causal series of the F3 ratio (num_window-d ADDV / den_window-d ADDV)."""
    key = (symbol, num_window, den_window)
    if key not in _F3_CACHE:
        d = simlib.load_d1(symbol)
        dv = d["Close"] * d["Volume"]  # split-adjusted price x raw volume = true dollars
        num = dv.rolling(num_window, min_periods=num_window).mean()
        den = dv.rolling(den_window, min_periods=den_window).mean()
        _F3_CACHE[key] = (num / den).replace([np.inf, -np.inf], np.nan)
    return _F3_CACHE[key]


def f4_series(symbol, atr_window=14, med_window=60):
    """Full causal series of the F4 ratio (14d ATR / 60d median ATR)."""
    key = (symbol, atr_window, med_window)
    if key not in _F4_CACHE:
        d = simlib.load_d1(symbol)
        hi, lo, cl = d["High"], d["Low"], d["Close"]
        pc = cl.shift(1)
        tr = pd.concat([hi - lo, (hi - pc).abs(), (lo - pc).abs()], axis=1).max(axis=1)
        atr = tr.rolling(atr_window, min_periods=atr_window).mean()
        med = atr.rolling(med_window, min_periods=med_window).median()
        _F4_CACHE[key] = (atr / med).replace([np.inf, -np.inf], np.nan)
    return _F4_CACHE[key]


def factor_at(series_fn, symbol, signal_ts, **kw):
    """Factor value at signal time, strict PIT. NaN if uncomputable."""
    s = series_fn(symbol, **kw)
    d = simlib.load_d1(symbol)
    j = last_completed_daily_pos(d.index, signal_ts)
    if j < 0 or j >= len(s):
        return np.nan
    v = s.iloc[j]
    return float(v) if not pd.isna(v) else np.nan
