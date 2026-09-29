"""TRACK B (the real bet): the PROVEN LONG framework, unchanged, on inverse ETFs.

Runs backtest.py's "structural" variant verbatim — the variant behind the
reference numbers (+11.3%, +0.165R/trade, PF 1.41 on 2024-09-16 -> 2026-09-14):
  - point-in-time classify_symbol on closed bars (read-only reuse),
  - sr.is_structural_candidate as the ONLY entry filter (no market-gate,
    rel-vol, R:R, MTF, or 15m gates — exactly like the reference variant),
  - next-bar-open entry, structural stop/TP1 from the scanner's trade_levels,
  - stop wins same-bar ties, scanner EXIT early exit, 30-bar max hold,
  - 4 bps round trip, 1 position/symbol, no borrow (longs).

Deliberately UNCHANGED, including the framework's own RISK-OFF rule that
downgrades entry YES -> WATCH when the market regime is RISK-OFF (counted as
an observation, not overridden).

Two windows:
  W1: 4H bars, yfinance 2y (directly comparable to the long backtest window).
  W2: 2022-01-01 -> 2022-12-31 bear market. yfinance serves no 2022 intraday
      bars (730-day limit, verified), and no free keyless source has 2022
      hourly SH/PSQ (Dukascopy lacks inverse ETFs). So W2 runs at DAILY
      resolution with the bar-count rules kept literally unchanged
      (30-bar max hold = 30 trading days here). Labeled as a daily-resolution
      adaptation — the verdict weight stays on W1 and its RISK-OFF split.

Only single-inverse SH/PSQ. No leveraged products.

RESEARCH ONLY. Nothing frozen is touched. No forward test, no signals, no money.
"""

import json
import os
import sys
import time

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
import scanner_rules as sr  # read-only: is_structural_candidate

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

UNIVERSE = ["SH", "PSQ"]
WARMUP = 215
MAX_HOLD_BARS = 30
ROUNDTRIP_COST = 0.0004
START_EQUITY = 10_000.0
RISK_PER_TRADE = 0.01
THEME = "Inverse ETF"

W2_START = pd.Timestamp("2022-01-01", tz="America/New_York")
W2_END = pd.Timestamp("2023-01-01", tz="America/New_York")  # exclusive


def cached(name, build):
    path = os.path.join(CACHE_DIR, name + ".pkl")
    if os.path.exists(path):
        return pd.read_pickle(path)
    df = build()
    df.to_pickle(path)
    return df


def regime_at(qqq_ind, qqq_raw, spy_raw, j):
    """Verbatim copy of backtest.py's regime_at."""
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


def generate_signals(sym, df, qqq, spy, qqq_ind, timeframe):
    """backtest.py generate_signals, minus daily/weekly MTF (unused by the
    structural variant). Counts risk-off-vetoed would-be entries as an
    observation (approx: BUY/PULLBACK BUY + SAFE + above VWAP, entry WATCH)."""
    qqq_idx = qqq.index
    n = len(df)
    signals = [None] * n
    n_struct = 0
    n_vetoed = 0
    for i in range(WARMUP, n):
        ts = df.index[i]
        j = int(qqq_idx.searchsorted(ts, side="right") - 1)
        if j < m.TREND_EMA + 5:
            continue
        regime = regime_at(qqq_ind, qqq, spy, j)
        sl = df.iloc[: i + 1]
        mk = qqq.iloc[: j + 1]
        try:
            row = m.classify_symbol(sym, THEME, sl, mk, regime, timeframe)
        except Exception:
            continue
        if not row:
            continue
        row["regime_label"] = regime["regime"]
        if sr.is_structural_candidate(row):
            n_struct += 1
        elif (row.get("state") in ("BUY", "PULLBACK BUY")
              and row.get("protection") == "SAFE"
              and row.get("above_vwap") is True
              and row.get("entry") == "WATCH"
              and "risk-off" in str(row.get("note", "")).lower()):
            n_vetoed += 1
        signals[i] = row
    return signals, n_struct, n_vetoed


def walk_exit(df, signals, i, entry, stop, tp1):
    """Verbatim backtest.py walk_exit: stop-first ties, scanner EXIT, 30-bar."""
    n = len(df)
    end = min(i + MAX_HOLD_BARS, n - 1)
    for j in range(i + 1, end + 1):
        lo = float(df["Low"].iloc[j])
        hi = float(df["High"].iloc[j])
        stop_hit = lo <= stop
        tp_hit = hi >= tp1
        if stop_hit:                      # conservative: stop wins ties
            return stop, j, "stop"
        if tp_hit:
            return tp1, j, "target"
        srow = signals[j]
        if srow and srow.get("state") == "EXIT":
            return float(df["Close"].iloc[j]), j, "scanner-exit"
    return float(df["Close"].iloc[end]), end, "time"


def run_structural(sym, signals, df, win_start=None, win_end=None):
    """Verbatim backtest.py run_variant (structural, next-bar-open entry)."""
    trades = []
    skipped = 0
    n = len(df)
    i = WARMUP
    while i < n - 1:
        row = signals[i]
        ts = df.index[i]
        if row is None or not sr.is_structural_candidate(row):
            i += 1
            continue
        if win_start is not None and not (win_start <= ts < win_end):
            i += 1
            continue
        stop = float(row["stop"])
        tp1 = float(row["tp1"])
        entry = float(df["Open"].iloc[i + 1])
        if entry <= stop:
            skipped += 1
            i += 1
            continue
        if entry >= tp1:
            trades.append(mk_trade(sym, row, entry, entry, i, i + 1,
                                   "gap-above-target"))
            i += 1
            continue
        exit_px, j, reason = walk_exit(df, signals, i, entry, stop, tp1)
        trades.append(mk_trade(sym, row, entry, exit_px, i, j, reason))
        i = j + 1
    return trades, skipped


def mk_trade(sym, row, entry, exit_px, i, j, reason):
    """Verbatim backtest.py mk_trade (longs: no borrow)."""
    risk = entry - float(row["stop"])
    ret = (exit_px - entry) / entry - ROUNDTRIP_COST
    return {"symbol": sym,
            "entry_date": pd.Timestamp(row["signal_bar_close_at"]).isoformat(),
            "exit_bar": j, "hold_bars": j - i,
            "state": row["state"], "regime": row.get("regime_label"),
            "entry": round(entry, 4), "stop": round(float(row["stop"]), 4),
            "tp1": round(float(row["tp1"]), 4), "exit": round(exit_px, 4),
            "reason": reason,
            "ret_pct": round(ret * 100, 3),
            "r_multiple": round((exit_px - entry) / risk, 3) if risk > 0 else 0.0}


def summarize(trades, label):
    """Verbatim backtest.py summarize (by_symbol / by_regime / by_state)."""
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
        risk_frac = (r["entry"] - r["stop"]) / r["entry"]
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
           "exit_reasons": t["reason"].value_counts().to_dict(),
           "final_equity_10k_1pct_risk": round(eq, 2),
           "max_drawdown_pct": round(maxdd, 2)}
    for key, grp in [("by_symbol", t.groupby("symbol")),
                     ("by_regime", t.groupby("regime")),
                     ("by_state", t.groupby("state"))]:
        rows = []
        for name, g in grp:
            w = g[g["ret_pct"] > 0]
            rows.append({"group": str(name), "trades": len(g),
                         "win_rate_pct": round(len(w) / len(g) * 100, 1),
                         "expectancy_pct": round(g["ret_pct"].mean(), 3),
                         "expectancy_r": round(g["r_multiple"].mean(), 3)})
        out[key] = sorted(rows, key=lambda r: -r["trades"])
    return out


def bh_pct(sym, start, end):
    d = yf.download(sym, interval="1d", start=start, end=end, progress=False,
                    auto_adjust=True, threads=False)
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = [c[0] for c in d.columns]
    d = d.dropna()
    return round(float(d["Close"].iloc[-1] / d["Close"].iloc[0] - 1) * 100, 2)


def run_window_w1():
    print("== W1: SH/PSQ 4H, 2y ==", flush=True)
    data = {}
    for n, sym in enumerate(UNIVERSE + ["QQQ", "SPY"]):
        print(f"  [{n+1}/4] 4h {sym}", flush=True)
        data[sym] = cached(f"h4_{sym}",
                            lambda s=sym: m.download_data(s, "4h", "2y"))
        time.sleep(0.4)
    qqq, spy = data["QQQ"], data["SPY"]
    qqq_ind = m.add_indicators(qqq)
    all_trades, skipped, sig_counts = [], 0, {}
    for sym in UNIVERSE:
        df = data[sym]
        print(f"  signals: {sym} ...", flush=True)
        signals, n_struct, n_vetoed = generate_signals(sym, df, qqq, spy,
                                                       qqq_ind, "4h")
        trades, sk = run_structural(sym, signals, df)
        all_trades.extend(trades)
        skipped += sk
        sig_counts[sym] = {"structural": n_struct,
                           "risk_off_vetoed_approx": n_vetoed,
                           "trades": len(trades)}
        print(f"    -> {n_struct} structural, ~{n_vetoed} risk-off vetoed, "
              f"{len(trades)} trades", flush=True)
    summary = summarize(all_trades, "long structural on SH/PSQ / 4H 2y")
    return all_trades, skipped, sig_counts, summary, \
        f"{data['SH'].index[0]} -> {data['SH'].index[-1]}"


def run_window_w2():
    print("== W2: SH/PSQ daily 2022 (adaptation) ==", flush=True)
    data = {}

    def dl(s):
        d = yf.download(s, interval="1d", start="2020-06-01", end="2023-01-15",
                        progress=False, auto_adjust=True, threads=False)
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = [c[0] for c in d.columns]
        d = d.dropna()
        if d.index.tz is None:
            d.index = d.index.tz_localize("America/New_York")
        return d

    for n, sym in enumerate(UNIVERSE + ["QQQ", "SPY"]):
        print(f"  [{n+1}/4] 1d {sym}", flush=True)
        data[sym] = cached(f"d1_2022_{sym}", lambda s=sym: dl(s))
        time.sleep(0.4)
    qqq, spy = data["QQQ"], data["SPY"]
    qqq_ind = m.add_indicators(qqq)
    all_trades, skipped, sig_counts = [], 0, {}
    for sym in UNIVERSE:
        df = data[sym]
        print(f"  signals: {sym} ...", flush=True)
        signals, n_struct, n_vetoed = generate_signals(sym, df, qqq, spy,
                                                       qqq_ind, "1d")
        trades, sk = run_structural(sym, signals, df, W2_START, W2_END)
        all_trades.extend(trades)
        skipped += sk
        sig_counts[sym] = {"structural": n_struct,
                           "risk_off_vetoed_approx": n_vetoed,
                           "trades": len(trades)}
        print(f"    -> {n_struct} structural, ~{n_vetoed} risk-off vetoed, "
              f"{len(trades)} trades", flush=True)
    summary = summarize(all_trades, "long structural on SH/PSQ / daily 2022")
    return all_trades, skipped, sig_counts, summary, \
        f"{data['SH'].index[0]} -> {data['SH'].index[-1]}"


def main():
    t1, sk1, sc1, s1, win1 = run_window_w1()
    t2, sk2, sc2, s2, win2 = run_window_w2()
    results = {
        "framework": ("backtest.py structural variant verbatim (is_structural_candidate "
                      "only; no market-gate/rel-vol/RR/MTF/15m filters), next-bar-open "
                      "entry, scanner stop/TP1, stop-first ties, scanner-EXIT early "
                      "exit, 30-bar max hold, 4bps, 1 position/symbol. RISK-OFF "
                      "entry YES->WATCH downgrade kept unchanged (vetoed count logged)."),
        "universe": UNIVERSE,
        "window_w1": {
            "bars": "4H", "data": "yfinance 2y 1h -> scanner 4H resample",
            "actual": win1, "skipped_adverse_gap": sk1,
            "signal_counts": sc1, "summary": s1,
            "buy_hold_pct": {s: bh_pct(s, "2024-09-16", "2026-09-14")
                             for s in UNIVERSE + ["QQQ", "SPY"]},
        },
        "window_w2": {
            "bars": "DAILY (adaptation — 4H unavailable for 2022; bar-count rules kept literal, so 30-bar hold = 30 trading days)",
            "data": "yfinance daily 2020-06-01 -> 2023-01-15; signals 2022-01-01 -> 2022-12-31",
            "actual": win2, "skipped_adverse_gap": sk2,
            "signal_counts": sc2, "summary": s2,
            "buy_hold_pct_2022": {s: bh_pct(s, "2022-01-01", "2023-01-01")
                                  for s in UNIVERSE + ["QQQ", "SPY"]},
        },
    }
    out = os.path.join(HERE, "track_b_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    pd.DataFrame(t1).to_csv(os.path.join(HERE, "track_b_trades_w1.csv"), index=False)
    pd.DataFrame(t2).to_csv(os.path.join(HERE, "track_b_trades_w2.csv"), index=False)
    for tag, s in (("W1 4H 2y", s1), ("W2 daily 2022", s2)):
        print(f"\n==== TRACK B {tag} ====")
        print(json.dumps({k: s[k] for k in s if not k.startswith("by_")}, indent=2))
        print("-- by regime --")
        print(json.dumps(s.get("by_regime", []), indent=2))
    print(f"\nResults saved to {out}")


if __name__ == "__main__":
    main()
