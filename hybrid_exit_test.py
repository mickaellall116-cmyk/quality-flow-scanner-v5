"""Hybrid exit test (Mike's step 1).

Same 4H signals (structural + ADX >= 20), entries identical -- only the exit
varies, isolating exit quality:

  A: protect-1R, all-or-nothing (current baseline, replicates backtest_v2)
  B: 50% at TP1, runner keeps structural stop, scanner EXIT gated until +1R
  C: 50% at TP1, runner stop -> breakeven at TP1, EXIT ungated after TP1

Conventions match backtest_v2: next-bar-open entry, stop wins same-bar
ties, gap-below-stop entries skipped, 30-bar max hold, 4/25bps costs,
$10k / 1%-risk / 5-position / 5%-portfolio-risk event-driven sim.

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

WARMUP = 215
MAX_HOLD = 30
START_EQUITY = 10_000.0
RISK_PRIMARY = 0.01
MAX_CONCURRENT = 5
MAX_PORTFOLIO_RISK = 0.05
COSTS = {"4bps": 0.0004, "25bps": 0.0025}
REQUIRED = {"adx"}  # structural + ADX >= 20 (V5.4 core entries)

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

GATES = {
    "market": ("market gate is",),
    "rvol": ("relative volume below 0.80x",),
    "adx": ("ADX below 20",),
    "rr": ("reward/risk below 2.0:1",),
    "mtf": ("weekly/daily/4h alignment not confirmed",),
}


def gate_failed(reasons, gate):
    pat = GATES[gate][0]
    if gate == "market":
        return any(r.startswith(pat) for r in reasons)
    return pat in reasons


def passes(row, required):
    if not row or not sr.is_structural_candidate(row):
        return False
    reasons = row.get("reject_reasons") or []
    return not any(gate_failed(reasons, g) for g in required)


def close_time(sym, ts):
    return pd.Timestamp(sr.bar_close_at(ts, sym))


def _outcome(entry, stop, exit_px, cost):
    risk_frac = (entry - stop) / entry
    gross_ret = (exit_px - entry) / entry
    net_ret = gross_ret - cost
    return risk_frac, gross_ret / risk_frac, net_ret / risk_frac, net_ret


def simulate_portfolio(trades, closes, cost, risk_pct):
    events = []
    for t in trades:
        if not t.get("instant"):
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
            if tr.get("instant"):
                _, _, net_r, _ = _outcome(tr["entry"], tr["stop"], tr["exit"], cost)
                realized += risk_pct * eq * net_r
            else:
                open_risk = sum(p["risk_dollars"] for p in open_pos) / eq if eq > 0 else 1
                if len(open_pos) >= MAX_CONCURRENT:
                    skipped_cap_count += 1
                    continue
                if open_risk + risk_pct > MAX_PORTFOLIO_RISK + 1e-9:
                    skipped_cap_risk += 1
                    continue
                risk_dollars = risk_pct * eq
                risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
                pos = {"trade": tr, "risk_dollars": risk_dollars,
                       "size": risk_dollars / risk_frac, "risk_frac": risk_frac}
                open_pos.append(pos)
                by_id[id(tr)] = pos
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
            "skipped_cap_risk": skipped_cap_risk, "exposure": exposure}


def walk_hybrid(sym, df, signals, i, entry, stop, tp1, mode):
    """Walk one trade. Returns (exit_synth, j, reason, mfe_r, tp_done)."""
    n = len(df)
    risk_frac = (entry - stop) / entry
    r_of = lambda px: ((px - entry) / entry) / risk_frac
    end = min(i + MAX_HOLD, n - 1)
    tp_done = False
    tp1_r = None
    runner_stop = stop
    mfe_r = 0.0
    for j in range(i + 1, end + 1):
        lo = float(df["Low"].iloc[j])
        hi = float(df["High"].iloc[j])
        mfe_r = max(mfe_r, r_of(hi))
        if lo <= runner_stop:
            if not tp_done:
                return stop, j, "stop", close_time(sym, df.index[j]), mfe_r, False
            runner_r = r_of(runner_stop)
            blend = 0.5 * tp1_r + 0.5 * runner_r
            return entry * (1 + blend * risk_frac), j, "runner-stop", \
                close_time(sym, df.index[j]), mfe_r, True
        if mode in ("B", "C") and not tp_done and hi >= tp1:
            tp_done = True
            tp1_r = r_of(tp1)
            if mode == "C":
                runner_stop = max(stop, entry)  # breakeven
            continue
        if mode == "A" and hi >= tp1:
            # all-or-nothing baseline: full exit at TP1
            return tp1, j, "target", close_time(sym, df.index[j]), mfe_r, False
        srow = signals[j]
        exit_sig = srow and srow.get("state") == "EXIT"
        if exit_sig:
            gated = (mode == "A" and mfe_r < 1.0) or (mode == "B" and mfe_r < 1.0)
            # mode C: EXIT ungated once TP1 taken
            if not gated:
                if j + 1 < n:
                    px = float(df["Open"].iloc[j + 1])
                    et = df.index[j + 1]
                else:
                    px, et = float(df["Close"].iloc[j]), df.index[j]
                if not tp_done:
                    return px, j + 1 if j + 1 < n else j, "scanner-exit", \
                        close_time(sym, et), mfe_r, False
                runner_r = r_of(px)
                blend = 0.5 * tp1_r + 0.5 * runner_r
                return entry * (1 + blend * risk_frac), j + 1 if j + 1 < n else j, \
                    "runner-exit", close_time(sym, et), mfe_r, True
    # time exit at max hold
    px = float(df["Close"].iloc[end])
    if not tp_done:
        return px, end, "time", close_time(sym, df.index[end]), mfe_r, False
    blend = 0.5 * tp1_r + 0.5 * r_of(px)
    return entry * (1 + blend * risk_frac), end, "runner-time", \
        close_time(sym, df.index[end]), mfe_r, True


def gen_trades(sym, df, signals, mode):
    trades, skipped_gap = [], 0
    n = len(df)
    i = WARMUP
    while i < n - 1:
        row = signals[i]
        if row and passes(row, REQUIRED):
            stop = float(row["stop"])
            tp1 = float(row["tp1"])
            entry = float(df["Open"].iloc[i + 1])
            entry_time = df.index[i + 1]
            if entry <= stop:
                skipped_gap += 1
                i += 1
                continue
            if entry >= tp1:
                t = {"symbol": sym, "entry_time": entry_time,
                     "exit_time": entry_time, "entry": entry, "stop": stop,
                     "exit": entry, "reason": "gap-above-target",
                     "hold_bars": 0, "instant": True,
                     "signal_id": row.get("signal_id")}
            else:
                ex, j, reason, et, mfe_r, tp_done = walk_hybrid(
                    sym, df, signals, i, entry, stop, tp1, mode)
                t = {"symbol": sym, "entry_time": entry_time, "exit_time": et,
                     "entry": entry, "stop": stop, "exit": ex, "reason": reason,
                     "hold_bars": j - i, "instant": False,
                     "signal_id": row.get("signal_id"), "tp_done": tp_done,
                     "mfe_r": round(mfe_r, 3)}
            trades.append(t)
            i = (j if not t["instant"] else i) + 1
        else:
            i += 1
    return trades, skipped_gap


def summarize(label, trades, port, skipped_gap, cost_name):
    t = pd.DataFrame(trades)
    if t.empty:
        return {"config": label, "cost": cost_name, "trades": 0}
    rows = []
    for tr in trades:
        if tr.get("instant"):
            _, _, net_r, _ = _outcome(tr["entry"], tr["stop"], tr["exit"], COSTS[cost_name])
        else:
            _, _, net_r, _ = _outcome(tr["entry"], tr["stop"], tr["exit"], COSTS[cost_name])
        rows.append(net_r)
    t["net_r"] = rows
    wins = t[t["net_r"] > 0]
    n = len(t)
    gw, gl = wins["net_r"].sum(), -t[t["net_r"] <= 0]["net_r"].sum()
    return {
        "config": label, "cost": cost_name, "trades": n,
        "win_rate_pct": round(len(wins) / n * 100, 1),
        "expectancy_net_r": round(float(t["net_r"].mean()), 3),
        "profit_factor": round(gw / gl, 2) if gl > 0 else None,
        "total_return_pct": round((port["final_equity"] / START_EQUITY - 1) * 100, 2),
        "max_drawdown_pct": round(port["max_drawdown"] * 100, 2),
        "avg_hold_bars": round(float(t["hold_bars"].mean()), 1),
        "tp1_take_pct": round(float(t["tp_done"].fillna(False).mean()) * 100, 1),
        "skipped_gap_below_stop": skipped_gap,
        "exit_reasons": t["reason"].value_counts().to_dict(),
    }


def run_universe(tag, sig_tag, universe, mode):
    trades_all, closes, skipped = [], {}, 0
    for sym in universe:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        spath = os.path.join(CACHE, f"signals_{sig_tag}_{sym}.pkl")
        if not os.path.exists(spath):
            continue
        signals, _, _ = pd.read_pickle(spath)
        closes[sym] = df["Close"]
        tr, sg = gen_trades(sym, df, signals, mode)
        trades_all.extend(tr)
        skipped += sg
    trades_all.sort(key=lambda t: t["entry_time"])
    # instant trades bypass the sim's position logic? keep v2 convention:
    # v2 simulate_portfolio handles tr.get("instant") -> scratch at open
    out = []
    for cost_name, cost in COSTS.items():
        port = simulate_portfolio(trades_all, closes, cost, RISK_PRIMARY)
        out.append(summarize(f"HYBRID_{mode}:{tag}", trades_all, port, skipped, cost_name))
    return out


def main():
    results = {"modes": {
        "A": "protect-1R all-or-nothing (baseline)",
        "B": "50% at TP1, runner structural stop, EXIT gated to +1R",
        "C": "50% at TP1, runner breakeven, EXIT ungated after TP1",
    }, "runs": []}
    for tag, sig_tag, uni in [("U15", "U15", UNIVERSE_15), ("UX51", "UX", UNIVERSE_X)]:
        for mode in ["A", "B", "C"]:
            print(f"== {mode} {tag} ==", flush=True)
            results["runs"].extend(run_universe(tag, sig_tag, uni, mode))
    with open(os.path.join(BASE, "hybrid_exit_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    for r in results["runs"]:
        print(f"{r['config']} [{r['cost']}]: n={r['trades']} win={r['win_rate_pct']}% "
              f"exp={r['expectancy_net_r']}R pf={r['profit_factor']} "
              f"ret={r['total_return_pct']}% dd={r['max_drawdown_pct']}% "
              f"hold={r['avg_hold_bars']} tp1={r['tp1_take_pct']}%", flush=True)


if __name__ == "__main__":
    main()
