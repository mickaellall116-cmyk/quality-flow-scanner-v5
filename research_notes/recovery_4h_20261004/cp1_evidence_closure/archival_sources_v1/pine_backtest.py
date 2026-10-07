"""Backtest of Mike's TradingView strategy 'Quality Flow System V3.6'
(V3.3 engine, Hybrid entry mode, default inputs) on the same data and
portfolio assumptions as backtest_v2.py, so results are directly comparable
to the MasterScanner V5.3 walk-forward study.

Pine logic reimplemented faithfully (see quality_flow_v36_notes in output):
- Entries (Hybrid): confirmedBuy OR breakoutBuy OR readyBuy
    confirmedBuy = close>EMA21 & EMA21>EMA55 & close>EMA200 & trendScore>=4
                   & volume>SMA20 & not HOT
    breakoutBuy  = trendBull & strongTrend & close>highest(high,10)[1]
                   & volume>SMA20 & not HOT
    readyBuy     = readyState[1] & close>EMA21 & trendScore>=3
                   & volume>SMA20 & not HOT
- Trade management (Pine strategy semantics):
    entry at next 4h bar open; initial stop = signal close - ATR*1.5
    TP1 = fill + ATR*2.0, takes 50% (limit)
    runner trails at close - ATR*2.5 after TP1 (updated per completed bar)
    exits: intrabar stop (stop-first on ties), TP1, close<EMA55 or trendBear
           -> remainder at next bar open. No max hold (Pine has none).

Approximations vs TradingView (documented, not hidden):
 1. Session-aligned 4h bars (same as scanner backtest), not TV's regular 4h.
 2. TP1 level fixed from signal-bar ATR; Pine recomputes it with live ATR.
 3. Entries gapping below the stop are skipped (same convention as v2).
 4. Costs/portfolio identical to backtest_v2: 4/25bps, $10k, 1%/trade,
    max 5 positions, 5% portfolio risk, mark-to-market drawdown.

Local-only research. No live rules modified.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "backtest_cache", "v3")

UNIVERSE_15 = ["NVDA", "PLTR", "TSLA", "SOFI", "SMCI", "AMD", "AAPL", "MSFT",
               "META", "COIN", "MSTR", "AVGO", "BTC-USD", "ETH-USD", "SOL-USD"]
UNIVERSE_X = UNIVERSE_15 + [
    "GOOGL", "AMZN", "NFLX", "CRM",
    "MU", "INTC", "LRCX", "AMAT", "QCOM", "ARM",
    "HOOD", "APP", "NET", "SNOW", "DDOG", "CRWD", "SHOP",
    "RKLB", "ASTS", "LUNR",
    "PYPL", "NU", "MELI",
    "SPY", "IWM", "SMH", "ARKK", "XLF",
    "DOGE-USD", "AVAX-USD", "LINK-USD", "XRP-USD",
    "NIO", "MRNA", "PFE", "F",
]

WARMUP = 215
START_EQUITY = 10_000.0
RISK_PCT = 0.01
MAX_CONCURRENT = 5
MAX_PORTFOLIO_RISK = 0.05
COSTS = {"4bps": 0.0004, "25bps": 0.0025}

# Pine defaults
EMA9_L, EMA21_L, EMA55_L, EMA200_L = 9, 21, 55, 200
ATR_L, ADX_L, ADX_SMOOTH = 14, 14, 14
VOL_L = 20
BREAKOUT_BARS = 10
TP_ATR, SL_ATR, TRAIL_ATR, HOT_ATR = 2.0, 1.5, 2.5, 1.5


# ---------------------------------------------------------------- indicators
def ema(s, l):
    return s.ewm(span=l, adjust=False).mean()


def atr(df, l=ATR_L):
    h, lw, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([h - lw, (h - pc).abs(), (lw - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / l, adjust=False).mean()  # Wilder's RMA, like Pine ta.atr


def adx(df, l=ADX_L):
    h, lw = df["High"], df["Low"]
    plus_raw, minus_raw = h.diff(), -lw.diff()
    plus = pd.Series(np.where((plus_raw > minus_raw) & (plus_raw > 0), plus_raw, 0.0), index=df.index)
    minus = pd.Series(np.where((minus_raw > plus_raw) & (minus_raw > 0), minus_raw, 0.0), index=df.index)
    trur = atr(df, l)
    pdi = 100 * plus.ewm(alpha=1 / l, adjust=False).mean() / trur
    mdi = 100 * minus.ewm(alpha=1 / l, adjust=False).mean() / trur
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / l, adjust=False).mean()


def add_pine_indicators(df):
    out = df.copy()
    c = out["Close"]
    out["e9"] = ema(c, EMA9_L)
    out["e21"] = ema(c, EMA21_L)
    out["e55"] = ema(c, EMA55_L)
    out["e200"] = ema(c, EMA200_L)
    out["atr"] = atr(out)
    out["atr_base"] = out["atr"].rolling(50).mean()
    out["atr_ratio"] = out["atr"] / out["atr_base"]
    out["adx"] = adx(out)
    out["vol_ma"] = out["Volume"].rolling(VOL_L).mean()
    return out


# ------------------------------------------------------------------- signals
def pine_buy_signal(df, i):
    """Hybrid buySignal evaluated on completed bar i (point-in-time)."""
    r = df.iloc[i]
    rp = df.iloc[i - 1]
    if pd.isna(r["e200"]) or pd.isna(r["atr_base"]) or pd.isna(r["adx"]):
        return False
    close, vol = r["Close"], r["Volume"]
    volume_ok = vol > r["vol_ma"]
    hot = close > r["e9"] + r["atr"] * HOT_ATR
    safe = not hot
    trend_bull = r["e21"] > r["e55"] and close > r["e200"]
    strong_trend = r["adx"] > 20 and r["atr_ratio"] > 0.85
    # trendScore: cast each Boolean to int before summing so the result is a
    # true 0-5 integer count (plain NumPy boolean addition collapses to a
    # single Boolean, which made `score >= 4`/`>= 3` unreachable).
    score = int(r["e9"] > r["e21"]) + int(r["e21"] > r["e55"]) \
        + int(close > r["e200"]) + int(r["adx"] > 25) + int(r["atr_ratio"] > 1)
    breakout = close > df["High"].iloc[i - BREAKOUT_BARS:i].max()
    ready_prev = rp["Close"] < rp["e21"] and rp["Close"] > rp["e55"] \
        and rp["e21"] > rp["e55"] and rp["atr_ratio"] > 0.85

    confirmed = close > r["e21"] and r["e21"] > r["e55"] and close > r["e200"] \
        and score >= 4 and volume_ok and safe
    breakout_buy = trend_bull and strong_trend and breakout and volume_ok and safe
    ready_buy = ready_prev and close > r["e21"] and score >= 3 and volume_ok and safe
    return bool(confirmed or breakout_buy or ready_buy)


# -------------------------------------------------------------------- trades
def gen_pine_trades(sym, df):
    """Walk-forward trade generation with Pine strategy management."""
    trades = []
    skipped_gap = 0
    n = len(df)
    i = WARMUP
    in_trade = False
    while i < n - 1:
        if not in_trade:
            if pine_buy_signal(df, i):
                sig = df.iloc[i]
                entry = float(df["Open"].iloc[i + 1])
                stop0 = float(sig["Close"] - sig["atr"] * SL_ATR)
                if entry <= stop0:
                    skipped_gap += 1
                    i += 1
                    continue
                in_trade = True
                pos = {"symbol": sym, "entry": entry, "stop": stop0,
                       "tp1": entry + float(sig["atr"]) * TP_ATR,
                       "tp_hit": False, "runner": stop0,
                       "entry_idx": i + 1,
                       "entry_time": df.index[i + 1]}
                i += 1  # start managing from the entry bar
                continue
            i += 1
            continue
        # manage open position on completed bar i (entry bar is i = entry_idx)
        # Pine truth: TP1 is a real intrabar LIMIT order; the "stop"/trail/
        # EMA55 exits are all close-evaluated -> market exit at NEXT bar open.
        # (The script never passes a stop= to strategy.exit.)
        bar = df.iloc[i]
        lo, hi, close = float(bar["Low"]), float(bar["High"]), float(bar["Close"])
        if not pos["tp_hit"] and hi >= pos["tp1"]:
            pos["tp_hit"] = True  # 50% filled at TP1 limit
        # trail update at bar close (Pine recomputes runnerStop every bar)
        if pos["tp_hit"]:
            pos["runner"] = max(pos["runner"], close - float(bar["atr"]) * TRAIL_ATR)
        # close-based exits -> next bar open
        trend_bear = bar["e21"] < bar["e55"] and close < bar["e200"]
        done = False
        if close < pos["runner"]:
            reason = "stop"
            done = True
        elif close < bar["e55"] or trend_bear:
            reason = "ema55-bear" if trend_bear else "ema55-break"
            done = True
        if done:
            if i + 1 < n:
                exit_px = float(df["Open"].iloc[i + 1])
                exit_idx, exit_time = i + 1, df.index[i + 1]
            else:
                exit_px, exit_time = close, df.index[i]
                exit_idx = i
        if done:
            risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]
            r1 = (pos["tp1"] - pos["entry"]) / pos["entry"] / risk_frac if pos["tp_hit"] else None
            r2 = (exit_px - pos["entry"]) / pos["entry"] / risk_frac
            # blended R: 50% at TP1 (if hit) + 50% at final exit
            r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
            net_ret_blend = r_blend * risk_frac
            exit_synth = pos["entry"] * (1 + net_ret_blend)
            trades.append({
                "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
                "exit": exit_synth, "reason": reason,
                "tp1_hit": pos["tp_hit"],
                "entry_time": pos["entry_time"], "exit_time": exit_time,
                "hold_bars": exit_idx - pos["entry_idx"],
                "signal_time": df.index[pos["entry_idx"] - 1].isoformat(),
            })
            in_trade = False
        i += 1
    return trades, skipped_gap


# ------------------------------------------------------------- portfolio sim
def _outcome(entry, stop, exit_px, cost):
    risk_frac = (entry - stop) / entry
    gross_ret = (exit_px - entry) / entry
    net_ret = gross_ret - cost
    return risk_frac, gross_ret / risk_frac, net_ret / risk_frac, net_ret


def simulate_portfolio(trades, closes, cost, risk_pct):
    events = []
    for t in trades:
        events.append((t["exit_time"], 0, t))
        events.append((t["entry_time"], 1, t))
    events.sort(key=lambda e: (e[0], e[1]))
    realized = START_EQUITY
    open_pos, by_id = [], {}
    skipped_cap_count = skipped_cap_risk = 0
    peak, max_dd = realized, 0.0
    curve, prev_t = [], None
    open_time = total_time = pd.Timedelta(0)

    def mark(sym, t):
        s = closes[sym]
        idx = s.index.searchsorted(t, side="right") - 1
        return float(s.iloc[idx]) if idx >= 0 else float(s.iloc[0])

    def marked_equity(t):
        unreal = sum(((mark(tr["symbol"], t) - tr["entry"]) / tr["entry"]) * p["size"]
                     for p, tr in ((p, p["trade"]) for p in open_pos))
        return realized + unreal

    for t, kind, tr in events:
        if prev_t is not None and t > prev_t:
            dt = t - prev_t
            total_time += dt
            if open_pos:
                open_time += dt
        prev_t = t
        if kind == 1:
            eq = marked_equity(t)
            open_risk = sum(p["risk_dollars"] for p in open_pos) / eq if eq > 0 else 1
            if len(open_pos) >= MAX_CONCURRENT:
                skipped_cap_count += 1
                continue
            if open_risk + risk_pct > MAX_PORTFOLIO_RISK + 1e-9:
                skipped_cap_risk += 1
                continue
            risk_dollars = risk_pct * eq
            risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
            open_pos.append({"trade": tr, "risk_dollars": risk_dollars,
                             "size": risk_dollars / risk_frac, "risk_frac": risk_frac})
            by_id[id(tr)] = open_pos[-1]
        else:
            pos = by_id.pop(id(tr), None)
            if pos is None:
                continue
            _, _, net_r, _ = _outcome(tr["entry"], tr["stop"], tr["exit"], cost)
            realized += pos["risk_dollars"] * net_r
            open_pos.remove(pos)
        eq = marked_equity(t)
        curve.append((t, eq, realized, len(open_pos)))
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    exposure = float(open_time / total_time) if total_time > pd.Timedelta(0) else 0.0
    return {"final_equity": realized, "max_drawdown": max_dd,
            "skipped_cap_count": skipped_cap_count,
            "skipped_cap_risk": skipped_cap_risk,
            "exposure": exposure, "curve": curve}


def summarize(label, trades, port, skipped_gap, cost_name):
    t = pd.DataFrame(trades)
    if t.empty:
        return {"config": label, "cost": cost_name, "trades": 0}
    # re-derive net R from blended exit
    rows = []
    for tr in trades:
        _, _, net_r, net_ret = _outcome(tr["entry"], tr["stop"], tr["exit"],
                                        COSTS[cost_name])
        rows.append(net_r)
    t["net_r"] = rows
    wins = t[t["net_r"] > 0]
    losses = t[t["net_r"] <= 0]
    n = len(t)
    gw = wins["net_r"].sum()
    gl = -losses["net_r"].sum()
    return {
        "config": label, "cost": cost_name, "trades": n,
        "win_rate_pct": round(len(wins) / n * 100, 1),
        "expectancy_net_r": round(float(t["net_r"].mean()), 3),
        "profit_factor": round(gw / gl, 2) if gl > 0 else None,
        "total_return_pct": round((port["final_equity"] / START_EQUITY - 1) * 100, 2),
        "max_drawdown_pct": round(port["max_drawdown"] * 100, 2),
        "avg_hold_bars": round(float(t["hold_bars"].mean()), 1),
        "market_exposure_pct": round(port["exposure"] * 100, 1),
        "tp1_hit_rate_pct": round(float(t["tp1_hit"].mean()) * 100, 1),
        "skipped_gap_below_stop": skipped_gap,
        "skipped_max_positions": port["skipped_cap_count"],
        "skipped_max_risk": port["skipped_cap_risk"],
        "exit_reasons": t["reason"].value_counts().to_dict(),
    }


# ---------------------------------------------------------------------- main
def run_universe(universe, tag, tf="4h"):
    prefix = "h4_" if tf == "4h" else "d1_5y_"
    tail = 504 if tf == "1d2y" else None
    all_trades, closes, skipped = [], {}, 0
    for sym in universe:
        path = os.path.join(CACHE, f"{prefix}{sym}.pkl")
        if not os.path.exists(path):
            print(f"  [warn] no cache for {sym}, skipping", flush=True)
            continue
        df = pd.read_pickle(path)
        if tail:
            df = df.iloc[-tail:]
        if "Volume" not in df.columns or df["Volume"].isna().all():
            print(f"  [warn] no volume for {sym}, skipping", flush=True)
            continue
        df = add_pine_indicators(df)
        closes[sym] = df["Close"]
        tr, sg = gen_pine_trades(sym, df)
        all_trades.extend(tr)
        skipped += sg
        print(f"  {sym}: {len(tr)} trades", flush=True)
    all_trades.sort(key=lambda t: t["entry_time"])
    out = []
    for cost_name, cost in COSTS.items():
        port = simulate_portfolio(all_trades, closes, cost, RISK_PCT)
        out.append(summarize(f"PINE_V36_hybrid:{tag}:{tf}", all_trades, port, skipped, cost_name))
    return out, all_trades


def main():
    tf = sys.argv[1] if len(sys.argv) > 1 else "4h"
    out_name = "pine_backtest_results_daily.json" if tf == "1d" else "pine_backtest_results.json"
    results = {"timeframe": tf, "notes": [
        "Reimplementation of Mike's TradingView strategy 'Quality Flow System V3.6' "
        "(V3.3 engine, Hybrid mode, default inputs).",
        "Approximations vs TV: 4h uses session-aligned bars (not TV regular 4h); "
        "TP1 fixed from signal-bar ATR (Pine recomputes live); gap-below-stop "
        "entries skipped.",
        "Same costs/portfolio as backtest_v2: 4/25bps, $10k, 1%/trade, max 5 "
        "positions, 5% portfolio risk.",
    ], "runs": []}
    for tag, uni in [("U15", UNIVERSE_15), ("UX51", UNIVERSE_X)]:
        print(f"== {tag} ({len(uni)} symbols) [{tf}] ==", flush=True)
        rows, trades = run_universe(uni, tag, tf)
        results["runs"].extend(rows)
        if tf == "4h" and tag == "UX51":
            all_trades_last = trades  # UX51 run already includes U15 symbols
        by_sym = {}
        for t in trades:
            _, _, net_r, _ = _outcome(t["entry"], t["stop"], t["exit"], COSTS["4bps"])
            by_sym.setdefault(t["symbol"], []).append(net_r)
        results[f"per_symbol_{tag}"] = {
            s: {"n": len(v), "mean_r": round(float(np.mean(v)), 3)}
            for s, v in sorted(by_sym.items())}
    with open(os.path.join(BASE, out_name), "w") as f:
        json.dump(results, f, indent=1, default=str)
    if tf == "4h":
        # per-trade dump for the MTF conditional study
        dump = []
        for t in all_trades_last:
            _, _, net_r, _ = _outcome(t["entry"], t["stop"], t["exit"], COSTS["4bps"])
            dump.append({
                "symbol": t["symbol"], "signal_time": t["signal_time"],
                "entry": t["entry"], "stop": t["stop"], "exit": t["exit"],
                "reason": t["reason"], "net_r": round(net_r, 3),
                "universe": "U15" if t["symbol"] in UNIVERSE_15 else "UX",
            })
        with open(os.path.join(BASE, "pine_trades_4h.json"), "w") as f:
            json.dump(dump, f, default=str)
        print(f"wrote pine_trades_4h.json ({len(dump)} trades)")
    for r in results["runs"]:
        print(f"{r['config']} [{r['cost']}]: n={r['trades']} win={r['win_rate_pct']}% "
              f"exp={r['expectancy_net_r']}R PF={r['profit_factor']} "
              f"ret={r['total_return_pct']}% dd={r['max_drawdown_pct']}% "
              f"hold={r['avg_hold_bars']} tp1={r['tp1_hit_rate_pct']}% "
              f"reasons={r['exit_reasons']}", flush=True)


if __name__ == "__main__":
    main()
