"""Step 1: download daily data + reconstruct the scanner's market regime on daily bars.

Regime replicates backtest.py::regime_at / masterscanner_api::get_market_regime scoring
exactly, applied to daily bars (see HEDGE_SPEC.md section 2 for the documented adaptation).
Point-in-time: regime[t] uses only bars <= t.
"""
import os, pickle
import numpy as np
import pandas as pd
import yfinance as yf

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
os.makedirs(CACHE, exist_ok=True)

DL_START = "2020-01-01"
TEST_START = "2022-01-01"
TEST_END = "2026-09-14"
WARMUP = 205  # TREND_EMA(200) + 5

def ema(s, l):
    return s.ewm(span=l, adjust=False).mean()

def download(sym):
    df = yf.download(sym, interval="1d", start=DL_START, end="2026-09-16",
                     progress=False, auto_adjust=True, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    return df.dropna()

def build_regime(qqq, spy):
    ind = pd.DataFrame(index=qqq.index)
    c = qqq["Close"]
    ind["EMA21"] = ema(c, 21); ind["EMA55"] = ema(c, 55); ind["EMA200"] = ema(c, 200)
    spy_c = spy["Close"].reindex(qqq.index).ffill()
    regimes = []
    for j in range(len(qqq)):
        if j < WARMUP:
            regimes.append("UNKNOWN"); continue
        last, prev = ind.iloc[j], ind.iloc[j-1]
        score = 0
        if c.iloc[j] > last["EMA200"]: score += 35
        if last["EMA21"] > last["EMA55"]: score += 35
        if last["EMA21"] > prev["EMA21"]: score += 15
        if c.iloc[j] > last["EMA21"]: score += 15
        q_ret = (c.iloc[j] / c.iloc[j-1] - 1) * 100
        s_ret = (spy_c.iloc[j] / spy_c.iloc[j-1] - 1) * 100
        regime = "RISK-ON" if score >= 75 else "CAUTIOUS" if score >= 50 else "RISK-OFF"
        regimes.append(regime)
    return pd.Series(regimes, index=qqq.index, name="regime")

def main():
    print("downloading...", flush=True)
    qqq = download("QQQ"); spy = download("SPY"); sh = download("SH"); vix = download("^VIX")
    print(f"QQQ {qqq.index[0].date()}->{qqq.index[-1].date()} n={len(qqq)}")
    regime = build_regime(qqq, spy)
    test_idx = qqq.index[(qqq.index >= TEST_START) & (qqq.index <= TEST_END)]
    # align everything to QQQ test calendar
    data = {
        "qqq": qqq.reindex(test_idx), "spy": spy.reindex(test_idx),
        "sh": sh.reindex(test_idx), "vix": vix.reindex(test_idx),
        "regime": regime.reindex(test_idx),
    }
    # sanity: no UNKNOWN inside test window (warmup ended 2020)
    assert (data["regime"] != "UNKNOWN").all(), "warmup leaked into test window"
    n_off = (data["regime"] == "RISK-OFF").sum()
    print(f"test days: {len(test_idx)}, RISK-OFF days: {n_off} ({100*n_off/len(test_idx):.1f}%)")
    print(data["regime"].value_counts().to_dict())
    with open(os.path.join(CACHE, "data.pkl"), "wb") as f:
        pickle.dump(data, f)
    print("saved cache/data.pkl")

if __name__ == "__main__":
    main()
