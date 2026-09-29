"""V6 short research: walk-forward backtest of structural SHORT setups.

Implements v6_short_research/SHORT_SPEC.md — the short mirror of the V5.4 long
framework. RESEARCH ONLY. Local only. Never touches frozen files (read-only
imports of masterscanner_api/backtest helpers), never pushes anywhere.

Methodology mirrors backtest.py (the long walk-forward test):
  2y 4H bars, point-in-time signals (no lookahead), next-bar-open entry,
  stop-first same-bar ties, 4bps round-trip costs, 1 position/symbol,
  max hold 30 bars. PLUS borrow cost: 1% annualized over trading days held
  (approximation for liquid large caps — see SHORT_SPEC.md).
"""

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# fastapi is not installed in this environment and the HTTP surface is not
# needed: a minimal stub satisfies masterscanner_api's module-level import so
# we can use its pure data/download/indicator functions read-only.
# (Same documented pattern as v54_engine.py; no existing file is modified.)
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
os.makedirs(CACHE_DIR, exist_ok=True)
LONG_CACHE = os.path.join(os.path.dirname(HERE), "backtest_cache")

UNIVERSE = ["NVDA", "AAPL", "MSFT", "META", "AMD", "AVGO", "TSLA", "PLTR",
            "NFLX", "CRM", "ORCL", "JPM", "XOM", "LLY", "COST", "GOOGL",
            "AMZN", "WMT"]
PERIOD_4H = "2y"
WARMUP = 215          # > TREND_EMA(200)+5 so indicators are settled
MAX_HOLD_BARS = 30    # ~15 trading days for stocks
ROUNDTRIP_COST = 0.0004
BORROW_ANNUAL = 0.01  # 1% annualized borrow on liquid large caps (approx)
START_EQUITY = 10_000.0
RISK_PER_TRADE = 0.01

MIN_ADX = 20.0        # mirror of the frozen V5.4 hard gate
SUPPORT_LOOKBACK = 20
PULLBACK_WINDOW = 15  # bars within which a breakdown zone stays valid for S2


# ---------------------------------------------------------------- data ---
def cached(name, build):
    path = os.path.join(CACHE_DIR, name + ".pkl")
    if os.path.exists(path):
        return pd.read_pickle(path)
    # read-only reuse of the long backtest's downloads where available
    legacy = os.path.join(LONG_CACHE, name + ".pkl")
    if os.path.exists(legacy):
        return pd.read_pickle(legacy)
    df = build()
    df.to_pickle(path)
    return df


def load_all():
    data = {}
    syms = UNIVERSE + ["QQQ", "SPY"]
    for n, sym in enumerate(syms):
        print(f"  [{n+1}/{len(syms)}] 4h {sym}", flush=True)
        try:
            data[sym] = cached(f"h4_{sym}",
                               lambda s=sym: m.download_data(s, "4h", PERIOD_4H))
        except Exception as e:
            print(f"    WARNING: {sym} download failed ({e}) — dropped", flush=True)
            data[sym] = None
        time.sleep(0.4)
    return data


# ------------------------------------------------------- point-in-time ---
def regime_at(qqq_ind, qqq_raw, spy_raw, j):
    """Verbatim copy of backtest.py's regime_at (QQQ-based market regime).

    Replicates get_market_regime scoring using only bars <= j (no lookahead).
    """
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
    """Walk forward; detect short setups on each closed 4H bar, point-in-time.

    Indicators are causal (EMA/ADX/ATR/VWAP at bar i depend only on bars <= i);
    rolling support/resistance windows end at i-1. Warmup absorbs seed effects.
    """
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

    # rolling levels, all ending at i-1 (no lookahead)
    support20 = ind["Low"].rolling(SUPPORT_LOOKBACK).min().shift(1).to_numpy()
    res_4_23 = ind["High"].rolling(SUPPORT_LOOKBACK).max().shift(4).to_numpy()

    qqq_idx = qqq_4h.index
    n = len(df)
    signals = [None] * n
    last_breakdown = None  # (bar_idx, zone_low, zone_high) for S2
    counts = {"S1": 0, "S2": 0, "S3": 0}

    for i in range(WARMUP, n):
        if not (np.isfinite([close[i], atr[i], adx[i], vwap[i],
                             ema21[i], support20[i]]).all()):
            continue
        # shared hard gates (mirror of V5.4: ADX>=20; below-VWAP mirrors above_vwap)
        if not (adx[i] >= MIN_ADX and close[i] < vwap[i] and close[i] < ema21[i]):
            continue
        ts = df.index[i]
        j = int(qqq_idx.searchsorted(ts, side="right") - 1)
        if j < m.TREND_EMA + 5:
            continue
        regime = regime_at(qqq_ind, qqq_4h, spy_4h, j)

        sig = None
        # S2 first (priority S2 > S3 > S1): pullback into broken support
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
                           "zone_low": zl, "zone_high": zh}
        # S3: bull trap (failed upside breakout)
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
                           "resistance": res}
        # S1: breakdown (also refreshes the S2 zone)
        if close[i] < support20[i] and vol[i] > volbase[i]:
            stop = high[i] + 0.5 * atr[i]
            risk = stop - close[i]
            if risk > 0:
                last_breakdown = (i, support20[i], high[i])
                if sig is None:  # S2/S3 outrank S1 on the same bar
                    sig = {"setup": "S1_BREAKDOWN", "stop": stop,
                           "target": close[i] - 2.0 * risk,
                           "support": support20[i]}
        elif sig is not None and sig["setup"] == "S2_PULLBACK_SHORT":
            pass  # zone already set from the earlier breakdown

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


# ------------------------------------------------------------- trading ---
def walk_exit_short(df, i, stop, target):
    n = len(df)
    end = min(i + MAX_HOLD_BARS, n - 1)
    hi = df["High"].to_numpy()
    lo = df["Low"].to_numpy()
    for j in range(i + 1, end + 1):
        if hi[j] >= stop:                 # conservative: stop wins ties
            return stop, j, "stop"
        if lo[j] <= target:
            return target, j, "target"
    return float(df["Close"].iloc[end]), end, "time"


def borrow_cost(entry, entry_i, exit_j, df):
    """1% annualized borrow over distinct trading days held (approximation)."""
    days = {d.date() for d in df.index[entry_i:exit_j + 1]}
    return BORROW_ANNUAL * len(days) / 252.0


def mk_trade(sym, sig, entry, exit_px, i, j, reason, df):
    risk = sig["stop"] - entry
    borrow = borrow_cost(entry, i + 1, j, df)
    ret = (entry - exit_px) / entry - ROUNDTRIP_COST - borrow
    return {"symbol": sym, "setup": sig["setup"],
            "entry_date": sig["signal_bar_close_at"],
            "exit_bar": j, "hold_bars": j - i,
            "regime": sig["regime"], "market_gate": sig["market_gate"],
            "entry": round(entry, 4), "stop": round(sig["stop"], 4),
            "target": round(sig["target"], 4), "exit": round(exit_px, 4),
            "reason": reason, "borrow_pct": round(borrow * 100, 4),
            "ret_pct": round(ret * 100, 3),
            "r_multiple": round((entry - exit_px) / risk, 3) if risk > 0 else 0.0}


def run_symbol(sym, signals, df):
    trades = []
    skipped = 0
    n = len(df)
    opens = df["Open"].to_numpy()
    i = WARMUP
    while i < n - 1:
        sig = signals[i]
        if sig is None:
            i += 1
            continue
        entry = float(opens[i + 1])
        stop, target = float(sig["stop"]), float(sig["target"])
        if entry >= stop:                      # adverse gap through stop
            skipped += 1
            i += 1
            continue
        if entry <= target:                     # gap beyond target: instant cover
            trades.append(mk_trade(sym, sig, entry, entry, i, i + 1,
                                   "gap-below-target", df))
            i += 1
            continue
        exit_px, j, reason = walk_exit_short(df, i, stop, target)
        trades.append(mk_trade(sym, sig, entry, exit_px, i, j, reason, df))
        i = j + 1
    return trades, skipped


# ------------------------------------------------------------- metrics ---
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
    print("Downloading data (cached in v6_short_research/cache/)...", flush=True)
    data = load_all()
    syms = [s for s in UNIVERSE if data.get(s) is not None and not data[s].empty]
    dropped = [s for s in UNIVERSE if s not in syms]
    print(f"Universe: {len(syms)} symbols; dropped: {dropped}", flush=True)
    qqq_4h, spy_4h = data["QQQ"], data["SPY"]
    qqq_ind = m.add_indicators(qqq_4h)

    all_trades = []
    total_skipped = 0
    setup_counts = {"S1": 0, "S2": 0, "S3": 0}
    per_symbol_signals = {}
    for sym in syms:
        df = data[sym]
        print(f"Signals: {sym} ...", flush=True)
        signals, counts = generate_signals(sym, df, qqq_4h, spy_4h, qqq_ind)
        for k in setup_counts:
            setup_counts[k] += counts[k]
        n_sig = sum(1 for s in signals if s)
        per_symbol_signals[sym] = n_sig
        trades, skipped = run_symbol(sym, signals, df)
        all_trades.extend(trades)
        total_skipped += skipped
        print(f"  -> {n_sig} short signals, {len(trades)} trades", flush=True)

    qd = m.download_confirmation_data("QQQ", "1d", "5y").dropna()
    if qd.index.tz is None:
        qd.index = qd.index.tz_localize("America/New_York")
    qd = qd[qd.index >= pd.Timestamp("2024-09-16", tz="America/New_York")]
    bh = float((qd["Close"].iloc[-1] / qd["Close"].iloc[0] - 1) * 100)

    summary = summarize(all_trades, "short / next-bar open")
    results = {
        "spec": "v6_short_research/SHORT_SPEC.md (written before coding)",
        "universe": syms,
        "dropped_symbols": dropped,
        "window": f"{qqq_4h.index[0]} -> {qqq_4h.index[-1]}",
        "signals_total": sum(per_symbol_signals.values()),
        "signals_by_setup": setup_counts,
        "signals_per_symbol": per_symbol_signals,
        "skipped_adverse_gap": total_skipped,
        "qqq_buy_hold_pct_same_window": round(bh, 2),
        "borrow_assumption": ("1% annualized over trading days held, "
                              "liquid large caps only — approximation, see spec"),
        "notes": ("Short mirror of the long walk-forward backtest: point-in-time "
                  "signals on closed 4H bars, next-bar-open entry, stop-first ties, "
                  "4bps round trip + borrow, 1 position/symbol, 30-bar max hold. "
                  "No market-gate entry filter by design — regime is measured, "
                  "not filtered (see by_regime split)."),
        "summary": summary,
    }
    out = os.path.join(HERE, "short_backtest_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    pd.DataFrame(all_trades).to_csv(os.path.join(HERE, "short_backtest_trades.csv"),
                                    index=False)
    s = summary
    print("\n==== SHORT BACKTEST RESULTS ====")
    print(json.dumps({k: s[k] for k in s if not k.startswith("by_")}, indent=2))
    print("\n-- by regime --")
    print(json.dumps(s.get("by_regime", []), indent=2))
    print("\n-- by setup --")
    print(json.dumps(s.get("by_setup", []), indent=2))
    print(f"\nQQQ buy-and-hold same window: {results['qqq_buy_hold_pct_same_window']}%")
    print(f"Results saved to {out}")


if __name__ == "__main__":
    main()
