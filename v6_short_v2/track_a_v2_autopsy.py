"""TRACK A (autopsy): v1 short setups + pre-specified v2 fast-failure exit.

Implements v6_short_v2/SHORT_V2_SPEC.md (written 2026-09-18 BEFORE this code).
Tests on 2022-01-01 -> 2022-12-31 4H bars — a window the v2 hypothesis never
saw (hypothesis was motivated by v1's 2024-2026 loss pattern only).

V2 rule (mechanical): after entry, on every closed 4H bar j (entry bar
excluded from intrabar checks, included for close evaluation), if
Close[j] >= breakdown_level (S1: broken support / S2: zone_low / S3: res)
OR Close[j] > VWAP[j] -> cover at Open[j+1]. Structural stop still wins all
intrabar ties (conservative). 2R target, 30-bar max hold, 4bps + 1% borrow,
1 position/symbol all unchanged from v1.

Data: Dukascopy hourly 2021-09 -> 2023-01 resampled with the repo's own
scanner_rules.resample_closed_4h (see data_2022.py for documented caveats:
no META, split status verified per-split vs yfinance — all already adjusted,
CFD tick volume, 9:00 ET bar dropped by the session filter).

RESEARCH ONLY. Nothing frozen is touched. No forward test, no signals, no money.
"""

import json
import os
import sys

import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import types as _types

if "fastapi" not in sys.modules:
    try:
        import fastapi  # noqa: F401
    except ImportError:
        _stub = _types.ModuleType("fastapi")

        class _App:
            def __init__(self, *a, **k):
                pass

            def get(self, *a, **k):
                return lambda f: f

            def post(self, *a, **k):
                return lambda f: f

        class _HTTPException(Exception):
            def __init__(self, status_code=500, detail=""):
                super().__init__(detail)
                self.status_code = status_code

        _stub.FastAPI = _App
        _stub.HTTPException = _HTTPException
        _stub.Query = lambda *a, **k: None
        sys.modules["fastapi"] = _stub

import masterscanner_api as m

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "cache")

# META absent from Dukascopy -> dropped (documented in data_2022.py)
UNIVERSE = ["NVDA", "AAPL", "MSFT", "AMD", "AVGO", "TSLA", "PLTR",
            "NFLX", "CRM", "ORCL", "JPM", "XOM", "LLY", "COST", "GOOGL",
            "AMZN", "WMT"]
WARMUP = 215
MAX_HOLD_BARS = 30
ROUNDTRIP_COST = 0.0004
BORROW_ANNUAL = 0.01
START_EQUITY = 10_000.0
RISK_PER_TRADE = 0.01
MIN_ADX = 20.0
SUPPORT_LOOKBACK = 20
PULLBACK_WINDOW = 15

WIN_START = pd.Timestamp("2022-01-01", tz="America/New_York")
WIN_END = pd.Timestamp("2023-01-01", tz="America/New_York")  # exclusive


def load(sym):
    path = os.path.join(CACHE_DIR, f"d4h_2022_{sym}.pkl")
    return pd.read_pickle(path)


def regime_at(qqq_ind, qqq_raw, spy_raw, j):
    """Verbatim copy of backtest.py's regime_at (QQQ-based market regime)."""
    if j < m.TREND_EMA + 5:
        return {"regime": "UNKNOWN", "risk_on": False, "score": 0, "gate": "BLOCK"}
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
    qqq_return = m._session_return(qqq_raw.iloc[: j + 1])
    ts = qqq_raw.index[j]
    spy_return = m._session_return(spy_raw[spy_raw.index <= ts])
    if qqq_return <= -0.75 or (qqq_return <= -0.40 and spy_return <= -0.40):
        gate = "BLOCK"
    elif qqq_return < 0 or spy_return < 0 or score < 75:
        gate = "CAUTION"
    else:
        gate = "CONFIRM"
    regime = "RISK-ON" if score >= 75 else "CAUTIOUS" if score >= 50 else "RISK-OFF"
    return {"regime": regime, "risk_on": score >= 50 and gate != "BLOCK",
            "score": int(score), "gate": gate}


def generate_signals(sym, df, qqq_4h, spy_4h, qqq_ind):
    """v1 signal logic verbatim, plus breakdown_level per SHORT_V2_SPEC.md."""
    ind = m.add_indicators(df)
    close = ind["Close"].to_numpy()
    open_ = ind["Open"].to_numpy()
    high = ind["High"].to_numpy()
    low = ind["Low"].to_numpy()
    vol = ind["Volume"].to_numpy()
    ema21 = ind["EMA21"].to_numpy()
    atr = ind["ATR"].to_numpy()
    adx = ind["ADX"].to_numpy()
    vwap = ind["VWAP"].to_numpy()
    volbase = ind["VOL_BASE"].to_numpy()

    support20 = ind["Low"].rolling(SUPPORT_LOOKBACK).min().shift(1).to_numpy()
    res_4_23 = ind["High"].rolling(SUPPORT_LOOKBACK).max().shift(4).to_numpy()

    qqq_idx = qqq_4h.index
    n = len(df)
    signals = [None] * n
    last_breakdown = None
    counts = {"S1": 0, "S2": 0, "S3": 0}

    for i in range(WARMUP, n):
        if not (np.isfinite([close[i], atr[i], adx[i], vwap[i],
                             ema21[i], support20[i]]).all()):
            continue
        if not (adx[i] >= MIN_ADX and close[i] < vwap[i] and close[i] < ema21[i]):
            continue
        ts = df.index[i]
        j = int(qqq_idx.searchsorted(ts, side="right") - 1)
        if j < m.TREND_EMA + 5:
            continue
        regime = regime_at(qqq_ind, qqq_4h, spy_4h, j)

        sig = None
        if last_breakdown is not None and i - last_breakdown[0] <= PULLBACK_WINDOW:
            zl, zh = last_breakdown[1], last_breakdown[2]
            touched = high[i] >= zl
            wick = high[i] - max(open_[i], close[i])
            rejected = (close[i] < zl) or (wick > 0.5 * atr[i] and close[i] < open_[i])
            if touched and rejected:
                stop = zh + 0.5 * atr[i]
                risk = stop - close[i]
                if risk > 0:
                    sig = {"setup": "S2_PULLBACK_SHORT", "stop": stop,
                           "target": close[i] - 2.0 * risk,
                           "breakdown_level": zl,
                           "zone_low": zl, "zone_high": zh}
        if sig is None and np.isfinite(res_4_23[i]):
            res = res_4_23[i]
            broke = (high[i - 1] > res) or (high[i - 2] > res) or (high[i - 3] > res)
            if broke and close[i] < res:
                stop = max(high[i - 3], high[i - 2], high[i - 1], high[i]) \
                    + 0.5 * atr[i]
                risk = stop - close[i]
                if risk > 0:
                    sig = {"setup": "S3_BULL_TRAP", "stop": stop,
                           "target": close[i] - 2.0 * risk,
                           "breakdown_level": res, "resistance": res}
        if close[i] < support20[i] and vol[i] > volbase[i]:
            stop = high[i] + 0.5 * atr[i]
            risk = stop - close[i]
            if risk > 0:
                last_breakdown = (i, support20[i], high[i])
                if sig is None:
                    sig = {"setup": "S1_BREAKDOWN", "stop": stop,
                           "target": close[i] - 2.0 * risk,
                           "breakdown_level": support20[i],
                           "support": support20[i]}

        if sig is not None:
            sig["regime"] = regime["regime"]
            sig["regime_score"] = regime["score"]
            sig["market_gate"] = regime["gate"]
            sig["signal_bar_close_at"] = ts.isoformat()
            sig["signal_close"] = round(float(close[i]), 4)
            signals[i] = sig
            counts["S1" if sig["setup"].startswith("S1") else
                   "S2" if sig["setup"].startswith("S2") else "S3"] += 1
    return signals, counts


def walk_exit_short_v2(df, i, stop, target, breakdown_level, vwap_arr):
    """v1 exit + pre-specified fast-fail cover (SHORT_V2_SPEC.md section 3)."""
    n = len(df)
    end = min(i + MAX_HOLD_BARS, n - 1)
    hi = df["High"].to_numpy()
    lo = df["Low"].to_numpy()
    cl = df["Close"].to_numpy()
    op = df["Open"].to_numpy()
    for j in range(i + 1, end + 1):
        if hi[j] >= stop:                 # conservative: stop wins ties
            return stop, j, "stop"
        if lo[j] <= target:
            return target, j, "target"
        # fast-fail: thesis invalidated on the closed bar -> cover next open
        if cl[j] >= breakdown_level or cl[j] > vwap_arr[j]:
            if j + 1 < n:
                return float(op[j + 1]), j + 1, "fast-fail"
            return float(cl[j]), j, "fast-fail"
    return float(cl[end]), end, "time"


def borrow_cost(entry_i, exit_j, df):
    days = {d.date() for d in df.index[entry_i:exit_j + 1]}
    return BORROW_ANNUAL * len(days) / 252.0


def mk_trade(sym, sig, entry, exit_px, i, j, reason, df):
    risk = sig["stop"] - entry
    borrow = borrow_cost(i + 1, j, df)
    ret = (entry - exit_px) / entry - ROUNDTRIP_COST - borrow
    return {"symbol": sym, "setup": sig["setup"],
            "entry_date": sig["signal_bar_close_at"],
            "exit_bar": j, "hold_bars": j - i,
            "regime": sig["regime"], "market_gate": sig["market_gate"],
            "entry": round(entry, 4), "stop": round(sig["stop"], 4),
            "target": round(sig["target"], 4),
            "breakdown_level": round(float(sig["breakdown_level"]), 4),
            "exit": round(exit_px, 4),
            "reason": reason, "borrow_pct": round(borrow * 100, 4),
            "ret_pct": round(ret * 100, 3),
            "r_multiple": round((entry - exit_px) / risk, 3) if risk > 0 else 0.0}


def run_symbol(sym, signals, df, vwap_arr):
    trades = []
    skipped = 0
    n = len(df)
    opens = df["Open"].to_numpy()
    i = WARMUP
    while i < n - 1:
        sig = signals[i]
        ts = df.index[i]
        if sig is None or not (WIN_START <= ts < WIN_END):
            i += 1
            continue
        entry = float(opens[i + 1])
        stop, target = float(sig["stop"]), float(sig["target"])
        if entry >= stop:
            skipped += 1
            i += 1
            continue
        if entry <= target:
            trades.append(mk_trade(sym, sig, entry, entry, i, i + 1,
                                   "gap-below-target", df))
            i += 1
            continue
        exit_px, j, reason = walk_exit_short_v2(
            df, i, stop, target, float(sig["breakdown_level"]), vwap_arr)
        trades.append(mk_trade(sym, sig, entry, exit_px, i, j, reason, df))
        i = j + 1
    return trades, skipped


def summarize(trades, label):
    t = pd.DataFrame(trades)
    if t.empty:
        return {"variant": label, "trades": 0}
    wins = t[t["ret_pct"] > 0]
    losses = t[t["ret_pct"] <= 0]
    gross_win = wins["ret_pct"].sum()
    gross_loss = -losses["ret_pct"].sum()
    eq = START_EQUITY
    peak = eq
    maxdd = 0.0
    for _, r in t.sort_values("entry_date").iterrows():
        risk_frac = (r["stop"] - r["entry"]) / r["entry"]
        if risk_frac <= 0:
            continue
        size = RISK_PER_TRADE * eq / risk_frac
        eq += size * (r["ret_pct"] / 100.0)
        peak = max(peak, eq)
        maxdd = max(maxdd, (peak - eq) / peak * 100)
    out = {"variant": label, "trades": len(t),
           "win_rate_pct": round(len(wins) / len(t) * 100, 1),
           "avg_win_pct": round(wins["ret_pct"].mean(), 2) if len(wins) else 0.0,
           "avg_loss_pct": round(losses["ret_pct"].mean(), 2) if len(losses) else 0.0,
           "expectancy_pct": round(t["ret_pct"].mean(), 3),
           "expectancy_r": round(t["r_multiple"].mean(), 3),
           "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else None,
           "avg_hold_bars": round(t["hold_bars"].mean(), 1),
           "avg_borrow_pct_per_trade": round(t["borrow_pct"].mean(), 4),
           "exit_reasons": t["reason"].value_counts().to_dict(),
           "final_equity_10k_1pct_risk": round(eq, 2),
           "max_drawdown_pct": round(maxdd, 2)}
    for key, grp in [("by_symbol", t.groupby("symbol")),
                     ("by_regime", t.groupby("regime")),
                     ("by_setup", t.groupby("setup")),
                     ("by_gate", t.groupby("market_gate"))]:
        rows = []
        for name, g in grp:
            w = g[g["ret_pct"] > 0]
            rows.append({"group": str(name), "trades": len(g),
                         "win_rate_pct": round(len(w) / len(g) * 100, 1),
                         "expectancy_pct": round(g["ret_pct"].mean(), 3),
                         "expectancy_r": round(g["r_multiple"].mean(), 3)})
        out[key] = sorted(rows, key=lambda r: -r["trades"])
    return out


def main():
    data = {}
    for sym in UNIVERSE + ["QQQ", "SPY"]:
        p = os.path.join(CACHE_DIR, f"d4h_2022_{sym}.pkl")
        if not os.path.exists(p):
            print(f"FATAL: missing {p} — run data_2022.py first", flush=True)
            sys.exit(1)
        data[sym] = pd.read_pickle(p)
    syms = [s for s in UNIVERSE if not data[s].empty]
    qqq_4h, spy_4h = data["QQQ"], data["SPY"]
    qqq_ind = m.add_indicators(qqq_4h)

    all_trades = []
    total_skipped = 0
    setup_counts = {"S1": 0, "S2": 0, "S3": 0}
    per_symbol_signals = {}
    for sym in syms:
        df = data[sym]
        print(f"Signals: {sym} ...", flush=True)
        vwap_arr = m.add_indicators(df)["VWAP"].to_numpy()
        signals, counts = generate_signals(sym, df, qqq_4h, spy_4h, qqq_ind)
        for k in setup_counts:
            setup_counts[k] += counts[k]
        in_win = sum(1 for k, s in enumerate(signals)
                     if s and WIN_START <= df.index[k] < WIN_END)
        per_symbol_signals[sym] = in_win
        trades, skipped = run_symbol(sym, signals, df, vwap_arr)
        all_trades.extend(trades)
        total_skipped += skipped
        print(f"  -> {in_win} in-window signals, {len(trades)} trades", flush=True)

    qd = yf.download("QQQ", interval="1d", start="2022-01-01",
                     end="2023-01-01", progress=False, auto_adjust=True,
                     threads=False)
    if isinstance(qd.columns, pd.MultiIndex):
        qd.columns = [c[0] for c in qd.columns]
    bh = float((qd["Close"].iloc[-1] / qd["Close"].iloc[0] - 1) * 100)
    sd = yf.download("SPY", interval="1d", start="2022-01-01",
                     end="2023-01-01", progress=False, auto_adjust=True,
                     threads=False)
    if isinstance(sd.columns, pd.MultiIndex):
        sd.columns = [c[0] for c in sd.columns]
    bh_spy = float((sd["Close"].iloc[-1] / sd["Close"].iloc[0] - 1) * 100)

    summary = summarize(all_trades, "short v2 (fast-fail exit) / 2022 4H")
    results = {
        "spec": "v6_short_v2/SHORT_V2_SPEC.md (written 2026-09-18, before code)",
        "universe": syms,
        "dropped_symbols": [s for s in UNIVERSE if s not in syms] + ["META (no Dukascopy feed)"],
        "window": "2022-01-01 -> 2022-12-31 (signal bars; exits may run into Jan 2023)",
        "data": ("Dukascopy hourly 2021-09 -> 2023-01, split status verified "
                 "per-split against yfinance adjusted closes (all already "
                 "adjusted, no-op), resampled with "
                 "scanner_rules.resample_closed_4h. "
                 "See data_2022.py docstring for caveats."),
        "signals_total_in_window": sum(per_symbol_signals.values()),
        "signals_by_setup": setup_counts,
        "signals_per_symbol": per_symbol_signals,
        "skipped_adverse_gap": total_skipped,
        "qqq_buy_hold_pct_2022": round(bh, 2),
        "spy_buy_hold_pct_2022": round(bh_spy, 2),
        "verdict_criteria": ("edge iff expectancy > +0.1R/trade AND PF > 1.2 AND "
                             ">= 30 trades; see SHORT_V2_SPEC.md section 5"),
        "summary": summary,
    }
    out = os.path.join(HERE, "track_a_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    pd.DataFrame(all_trades).to_csv(os.path.join(HERE, "track_a_trades.csv"),
                                    index=False)
    s = summary
    print("\n==== TRACK A: SHORT V2 (fast-fail) — 2022 4H ====")
    print(json.dumps({k: s[k] for k in s if not k.startswith("by_")}, indent=2))
    print("\n-- by regime --")
    print(json.dumps(s.get("by_regime", []), indent=2))
    print("\n-- by setup --")
    print(json.dumps(s.get("by_setup", []), indent=2))
    print(f"\nQQQ 2022 buy-and-hold: {results['qqq_buy_hold_pct_2022']}% | "
          f"SPY 2022: {results['spy_buy_hold_pct_2022']}%")
    print(f"Results saved to {out}")


if __name__ == "__main__":
    main()
