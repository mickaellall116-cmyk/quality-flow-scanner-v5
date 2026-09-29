"""MTF conditional study for the Pine V3.6 indicator backtest (4h engine).

Tags every Pine 4h trade's signal bar with daily/weekly trend confirmation,
market gate/regime, and RVOL bucket -- the same panels as the MasterScanner
conditional study -- so the two systems can be compared symmetrically.

Local-only research. No live rules modified.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scanner_rules as sr

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "backtest_cache", "v3")


def ema(s, l):
    return s.ewm(span=l, adjust=False).mean()


def regime_at(qqq_ind, qqq_raw, spy_raw, ts):
    """Point-in-time market regime/gate at timestamp ts (mirrors backtest_v2)."""
    j = int(qqq_raw.index.searchsorted(ts, side="right") - 1)
    if j < 205:
        return {"regime": "UNKNOWN", "score": 0, "gate": "BLOCK"}
    last, prev = qqq_ind.iloc[j], qqq_ind.iloc[j - 1]
    score = 0
    if last["Close"] > last["EMA200"]:
        score += 35
    if last["EMA21"] > last["EMA55"]:
        score += 35
    if last["EMA21"] > prev["EMA21"]:
        score += 15
    if last["Close"] > last["EMA21"]:
        score += 15
    h, lw, c = qqq_raw["High"], qqq_raw["Low"], qqq_raw["Close"]
    sess_ret = float((c.iloc[j] / c.iloc[max(0, j - 6)] - 1) * 100) if j >= 6 else 0.0
    sp = spy_raw[spy_raw.index <= ts]
    spy_ret = float((sp["Close"].iloc[-1] / sp["Close"].iloc[-7] - 1) * 100) if len(sp) >= 7 else 0.0
    if sess_ret <= -0.75 or (sess_ret <= -0.40 and spy_ret <= -0.40):
        gate = "BLOCK"
    elif sess_ret < 0 or spy_ret < 0 or score < 75:
        gate = "CAUTION"
    else:
        gate = "CONFIRM"
    regime = "RISK-ON" if score >= 75 else "CAUTIOUS" if score >= 50 else "RISK-OFF"
    return {"regime": regime, "score": int(score), "gate": gate}


def bucket_rvol(rv):
    if rv < 0.8:
        return "rvol<0.8"
    if rv < 1.0:
        return "rvol 0.8-1.0"
    if rv < 1.5:
        return "rvol 1.0-1.5"
    return "rvol 1.5+"


def stats(df):
    n = len(df)
    if n == 0:
        return {"n": 0}
    wins = df[df["net_r"] > 0]
    gw, gl = wins["net_r"].sum(), -df[df["net_r"] <= 0]["net_r"].sum()
    return {"n": n, "win_pct": round(len(wins) / n * 100, 1),
            "mean_net_r": round(float(df["net_r"].mean()), 3),
            "total_net_r": round(float(df["net_r"].sum()), 1),
            "pf": round(gw / gl, 2) if gl > 0 else None}


def main():
    with open(os.path.join(BASE, "pine_trades_4h.json")) as f:
        trades = pd.DataFrame(json.load(f))
    print(f"pine 4h trades: {len(trades)}", flush=True)

    qqq_4h = pd.read_pickle(os.path.join(CACHE, "h4_QQQ.pkl"))
    spy_4h = pd.read_pickle(os.path.join(CACHE, "h4_SPY.pkl"))
    qc = qqq_4h["Close"]
    qqq_ind = pd.DataFrame({"Close": qc, "EMA21": ema(qc, 21),
                            "EMA55": ema(qc, 55), "EMA200": ema(qc, 200)})

    h4, d1, w1 = {}, {}, {}
    for sym in trades["symbol"].unique():
        h4[sym] = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        d1[sym] = pd.read_pickle(os.path.join(CACHE, f"d1_5y_{sym}.pkl"))
        w1[sym] = pd.read_pickle(os.path.join(CACHE, f"w1_{sym}.pkl"))
        h4[sym]["vol_ma"] = h4[sym]["Volume"].rolling(20).mean()

    tags = []
    for _, t in trades.iterrows():
        sym = t["symbol"]
        sig_ts = pd.Timestamp(t["signal_time"])
        df = h4[sym]
        j = int(df.index.searchsorted(sig_ts, side="right") - 1)
        rvol = float(df["Volume"].iloc[j] / df["vol_ma"].iloc[j]) \
            if df["vol_ma"].iloc[j] > 0 else 0.0
        now_ts = df.index[j] + pd.Timedelta(hours=4)
        try:
            d_ok = bool(sr.timeframe_trend_confirmed(d1[sym], "1d", now=now_ts))
        except Exception:
            d_ok = False
        try:
            w_ok = bool(sr.timeframe_trend_confirmed(w1[sym], "1wk", now=now_ts))
        except Exception:
            w_ok = False
        reg = regime_at(qqq_ind, qqq_4h, spy_4h, sig_ts)
        tags.append({"d_ok": "Y" if d_ok else "N", "w_ok": "Y" if w_ok else "N",
                     "mtf": ("both" if d_ok and w_ok else "daily-only" if d_ok
                             else "weekly-only" if w_ok else "neither"),
                     "gate": reg["gate"], "regime": reg["regime"],
                     "rvol": bucket_rvol(rvol)})
    trades = trades.join(pd.DataFrame(tags))
    out = {}
    for tag in ["U15", "UX"]:
        sub = trades[trades["universe"] == tag]
        if sub.empty:
            continue
        panels = {
            "mtf": {k: stats(g) for k, g in sub.groupby("mtf")},
            "market_gate": {k: stats(g) for k, g in sub.groupby("gate")},
            "regime": {k: stats(g) for k, g in sub.groupby("regime")},
            "rvol": {k: stats(g) for k, g in sub.groupby("rvol")},
        }
        both, nb = sub[sub["mtf"] == "both"], sub[sub["mtf"] != "both"]
        panels["interaction_mtf"] = {"mtf_both": stats(both), "mtf_not_both": stats(nb)}
        out[tag] = {"n_trades": len(sub), "panels": panels}
        print(f"\n===== PINE V3.6 4h [{tag}] =====")
        for pname, panel in panels.items():
            print(f"--- {pname} ---")
            for k, s in panel.items():
                if s["n"]:
                    print(f"  {k}: n={s['n']} win={s['win_pct']}% "
                          f"mean={s['mean_net_r']}R total={s['total_net_r']}R pf={s['pf']}")
    with open(os.path.join(BASE, "conditional_pine_mtf.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("\nwrote conditional_pine_mtf.json")


if __name__ == "__main__":
    main()
