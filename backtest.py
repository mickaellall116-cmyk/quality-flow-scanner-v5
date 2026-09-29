"""Walk-forward backtest of Quality Flow Scanner V5 BUY NOW signals.

Reproduces the live /buy-now pipeline point-in-time on historical 4h bars:
  classify_symbol -> is_structural_candidate -> MTF (daily/weekly) gates
  -> ADX / relative-volume / risk-reward / market-gate(CONFIRM) gates.

NOT reproduced (no historical data at 2y scale, documented limitation):
  - completed 15-minute confirmation (yfinance 15m history caps at 60d)
  - premarket snapshot (intraday, live-only)
Signals below are BUY NOW signals *excluding* the 15m confirmation gate.

Trade management: enter at signal-bar close (variant A) or next-bar open
(variant B); stop = scanner stop; target = scanner tp1; first touch wins
(stop wins ties, conservative); exit early if scanner flips to EXIT state;
otherwise exit at close after MAX_HOLD_BARS. One position per symbol.
Costs: 4 bps round trip.

Local-only research script. Nothing is pushed anywhere.
"""

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import masterscanner_api as m
import scanner_rules as sr

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

UNIVERSE = ["NVDA", "PLTR", "TSLA", "SOFI", "SMCI", "AMD", "AAPL", "MSFT",
            "META", "COIN", "MSTR", "AVGO", "BTC-USD", "ETH-USD", "SOL-USD"]
PERIOD_4H = "2y"
WARMUP = 215          # > TREND_EMA(200)+5 so indicators are settled
MAX_HOLD_BARS = 30    # ~15 trading days for stocks
ROUNDTRIP_COST = 0.0004
START_EQUITY = 10_000.0
RISK_PER_TRADE = 0.01


# ---------------------------------------------------------------- data ---
def cached(name, build):
    path = os.path.join(CACHE_DIR, name + ".pkl")
    if os.path.exists(path):
        return pd.read_pickle(path)
    df = build()
    df.to_pickle(path)
    return df


def load_all():
    data = {}
    syms = UNIVERSE + ["QQQ", "SPY"]
    for n, sym in enumerate(syms):
        print(f"  [{n+1}/{len(syms)}] 4h {sym}", flush=True)
        data[sym] = cached(f"h4_{sym}",
                           lambda s=sym: m.download_data(s, "4h", PERIOD_4H))
        time.sleep(0.4)
    for n, sym in enumerate(UNIVERSE):
        print(f"  [{n+1}/{len(UNIVERSE)}] daily/weekly {sym}", flush=True)
        data[sym + "_1d"] = cached(f"d1_{sym}",
                                   lambda s=sym: m.download_confirmation_data(s, "1d", "5y"))
        data[sym + "_1w"] = cached(f"w1_{sym}",
                                   lambda s=sym: m.download_confirmation_data(s, "1wk", "10y"))
        time.sleep(0.4)
    return data


# ------------------------------------------------------- point-in-time ---
def regime_at(qqq_ind, qqq_raw, spy_raw, j):
    """Replicate get_market_regime scoring using only bars <= j (no lookahead)."""
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


def _as_et(df):
    if df.index.tz is None:
        df = df.copy()
        df.index = df.index.tz_localize("America/New_York")
    return df


def generate_signals(sym, df, daily, weekly, qqq_4h, spy_4h, qqq_ind):
    """Walk forward; classify each closed 4h bar using only data known then."""
    daily = _as_et(daily)
    weekly = _as_et(weekly)
    qqq_idx = qqq_4h.index
    signals = [None] * len(df)
    gate_tally = {}
    n_struct = 0
    for i in range(WARMUP, len(df)):
        ts = df.index[i]
        j = int(qqq_idx.searchsorted(ts, side="right") - 1)
        if j < m.TREND_EMA + 5:
            continue
        regime = regime_at(qqq_ind, qqq_4h, spy_4h, j)
        sl = df.iloc[: i + 1]
        mk = qqq_4h.iloc[: j + 1]
        try:
            row = m.classify_symbol(sym, "Backtest", sl, mk, regime, "4h")
        except Exception:
            continue
        if not row:
            continue
        # MTF gates, point-in-time (now = signal bar close)
        now_ts = pd.Timestamp(row["signal_bar_close_at"])
        d = daily[daily.index <= ts]
        w = weekly[weekly.index <= ts]
        try:
            daily_ok = bool(sr.timeframe_trend_confirmed(d, "1d", now=now_ts))
            weekly_ok = bool(sr.timeframe_trend_confirmed(w, "1wk", now=now_ts))
        except Exception:
            daily_ok = weekly_ok = False
        row["daily_trend_confirmed"] = daily_ok
        row["weekly_trend_confirmed"] = weekly_ok
        row["mtf_confirmed"] = bool(daily_ok and weekly_ok)
        row["regime_label"] = regime["regime"]
        if sr.is_structural_candidate(row):
            n_struct += 1
            for r in sr.validation_reasons(row):
                gate_tally[r] = gate_tally.get(r, 0) + 1
        # BUY NOW ex-15m: all live gates except the (unreproducible) 15m one
        reasons = [r for r in sr.validation_reasons(row) if "15-minute" not in r]
        row["buy_now_ex15m"] = not reasons
        row["reject_reasons"] = reasons
        signals[i] = row
    return signals, n_struct, gate_tally


# ------------------------------------------------------------- trading ---
def walk_exit(df, signals, i, entry, stop, tp1):
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


def run_variant(sym, signals, df, entry_mode, signal_key="buy_now_ex15m"):
    """signal_key: 'buy_now_ex15m' (full gates ex-15m) or 'structural' (raw 4h setup)."""
    import scanner_rules as _sr
    trades = []
    n = len(df)
    i = WARMUP
    while i < n - 1:
        row = signals[i]
        fire = row and (row.get("buy_now_ex15m") if signal_key == "buy_now_ex15m"
                        else _sr.is_structural_candidate(row))
        if fire:
            stop = float(row["stop"])
            tp1 = float(row["tp1"])
            if entry_mode == "close":
                entry = float(df["Close"].iloc[i])
            else:
                entry = float(df["Open"].iloc[i + 1])
                if entry <= stop:
                    trades.append({"symbol": sym, "skipped": True,
                                   "skip_reason": "gap-below-stop"})
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
        else:
            i += 1
    return [t for t in trades if not t.get("skipped")], \
           sum(1 for t in trades if t.get("skipped"))


def mk_trade(sym, row, entry, exit_px, i, j, reason):
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


# ------------------------------------------------------------- metrics ---
def summarize(trades, label):
    t = pd.DataFrame(trades)
    if t.empty:
        return {"variant": label, "trades": 0}
    wins = t[t["ret_pct"] > 0]
    losses = t[t["ret_pct"] <= 0]
    gross_win = wins["ret_pct"].sum()
    gross_loss = -losses["ret_pct"].sum()
    # equity: 1% risk per trade
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


def main():
    print("Downloading data (cached in backtest_cache/)...", flush=True)
    data = load_all()
    qqq_4h, spy_4h = data["QQQ"], data["SPY"]
    qqq_ind = m.add_indicators(qqq_4h)

    all_trades = {"close": [], "open": [], "structural_close": [], "structural_open": []}
    total_skipped = 0
    total_struct = 0
    gate_tally = {}
    per_symbol_signals = {}
    per_symbol_struct = {}
    for sym in UNIVERSE:
        df = data[sym]
        sig_path = os.path.join(CACHE_DIR, f"signals_{sym}.pkl")
        if os.path.exists(sig_path):
            print(f"Signals: {sym} (cached) ...", flush=True)
            signals, n_struct, tally = pd.read_pickle(sig_path)
        else:
            print(f"Signals: {sym} ...", flush=True)
            signals, n_struct, tally = generate_signals(
                sym, df, data[sym + "_1d"], data[sym + "_1w"],
                qqq_4h, spy_4h, qqq_ind)
            pd.to_pickle((signals, n_struct, tally), sig_path)
        total_struct += n_struct
        for k, v in tally.items():
            gate_tally[k] = gate_tally.get(k, 0) + v
        n_sig = sum(1 for s in signals if s and s.get("buy_now_ex15m"))
        per_symbol_signals[sym] = n_sig
        per_symbol_struct[sym] = sum(
            1 for s in signals if s and sr.is_structural_candidate(s))
        for variant, entry_mode, signal_key in (
                ("close", "close", "buy_now_ex15m"),
                ("open", "open", "buy_now_ex15m"),
                ("structural_close", "close", "structural"),
                ("structural_open", "open", "structural")):
            trades, skipped = run_variant(sym, signals, df, entry_mode, signal_key)
            all_trades[variant].extend(trades)
            total_skipped += skipped
        print(f"  -> {n_sig} BUY NOW (ex-15m), {per_symbol_struct[sym]} structural", flush=True)

    # QQQ buy-and-hold over the backtest window
    qd = m.download_confirmation_data("QQQ", "1d", "5y").dropna()
    qd = _as_et(qd)
    qd = qd[qd.index >= pd.Timestamp("2024-09-16", tz="America/New_York")]
    bh = float((qd["Close"].iloc[-1] / qd["Close"].iloc[0] - 1) * 100)

    results = {
        "universe": UNIVERSE,
        "window": f"{qqq_4h.index[0]} -> {qqq_4h.index[-1]}",
        "structural_candidates": total_struct,
        "gate_rejections": gate_tally,
        "signals_per_symbol_ex15m": per_symbol_signals,
        "structural_per_symbol": per_symbol_struct,
        "skipped_gap_below_stop": total_skipped,
        "qqq_buy_hold_pct_same_window": round(bh, 2),
        "notes": ("BUY NOW ex-15m: all live validation gates except the completed "
                  "15-minute confirmation (no 2y intraday history) and the live-only "
                  "premarket snapshot. Entry variants: signal-bar close, next-bar open. "
                  "Stop-first on same-bar stop/target touches. 4bps round-trip costs. "
                  "Max hold 30 4h bars; early exit if scanner flips to EXIT."),
        "close_entry": summarize(all_trades["close"], "signal-bar close"),
        "open_entry": summarize(all_trades["open"], "next-bar open"),
        "structural_close_entry": summarize(all_trades["structural_close"],
                                            "structural / signal-bar close"),
        "structural_open_entry": summarize(all_trades["structural_open"],
                                           "structural / next-bar open"),
    }
    out = os.path.join(CACHE_DIR, "backtest_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    pd.DataFrame(all_trades["open"]).to_csv(
        os.path.join(CACHE_DIR, "trades_open_entry.csv"), index=False)
    pd.DataFrame(all_trades["structural_open"]).to_csv(
        os.path.join(CACHE_DIR, "trades_structural_open_entry.csv"), index=False)
    print("\n==== RESULTS (next-bar open entry, full gates ex-15m) ====")
    print(json.dumps(results["open_entry"], indent=2))
    print("\n==== RESULTS (next-bar open entry, STRUCTURAL only) ====")
    s = results["structural_open_entry"]
    print(json.dumps(s, indent=2))
    print("\n==== RESULTS (signal-bar close entry) ====")
    c = results["close_entry"]
    print(json.dumps({k: c[k] for k in c if not k.startswith("by_")}, indent=2))
    print(f"\nQQQ buy-and-hold same window: {results['qqq_buy_hold_pct_same_window']}%")
    print(f"Structural candidates: {total_struct}; gate rejections: {gate_tally}")
    print(f"Results saved to {out}")


if __name__ == "__main__":
    main()
