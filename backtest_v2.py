"""Quality Flow Scanner V5.3 - rigorous walk-forward backtest (v2).

Spec:
 1. Live-exact: uses masterscanner_api + scanner_rules functions directly.
    4h bars via sr.resample_closed_4h; daily history 2y / weekly 5y exactly
    like the live scanner (download_confirmation_data + timeframe_trend_confirmed
    with now = signal-bar close). Completed 4h bars only, point-in-time.
    Primary entry: next 4h bar open.
 2. R: gross R and net R (net of round-trip costs). Expectancy judged on net R.
 3. Event-driven portfolio: $10k start, 1% risk/trade of current (marked)
    equity, simultaneous positions, max 5% open portfolio risk, max 5
    concurrent positions, skips recorded, chronological, mark-to-market
    drawdown. Sensitivity at 0.5% risk/trade.
 4. Gate ablation on is_structural_candidate baseline.
 5. Exits: A scanner EXIT (next-bar open), B ignore EXIT, C EXIT only after
    the trade first reached +1R. Counterfactual recorded for EXIT trades.
 6. Fresh-BUY funnel audit (no rule changes).
 7. Cost sensitivity: 4 / 10 / 25 bps round trip. Stop wins same-bar ties.
 8. Breakdowns: ticker, regime, state, stocks vs crypto, year.
 9. 15-symbol universe + expanded ~50-symbol universe (2y 1h cap noted).
10. Files: backtest_results_v2.json, backtest_ablation.csv, backtest_trades.csv,
    backtest_equity_curve.csv, backtest_exit_comparison.csv.

Local-only research. Live MasterScanner rules are NOT modified.
"""

import json
import os
import sys
import time
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import masterscanner_api as m
import scanner_rules as sr

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "backtest_cache", "v3")
os.makedirs(CACHE, exist_ok=True)

UNIVERSE_15 = ["NVDA", "PLTR", "TSLA", "SOFI", "SMCI", "AMD", "AAPL", "MSFT",
               "META", "COIN", "MSTR", "AVGO", "BTC-USD", "ETH-USD", "SOL-USD"]
UNIVERSE_X = UNIVERSE_15 + [
    # mega-cap tech
    "GOOGL", "AMZN", "NFLX", "CRM",
    # semiconductors
    "MU", "INTC", "LRCX", "AMAT", "QCOM", "ARM",
    # AI / high-beta growth
    "HOOD", "APP", "NET", "SNOW", "DDOG", "CRWD", "SHOP",
    # space
    "RKLB", "ASTS", "LUNR",
    # fintech
    "PYPL", "NU", "MELI",
    # broad / sector ETFs
    "SPY", "IWM", "SMH", "ARKK", "XLF",
    # crypto
    "DOGE-USD", "AVAX-USD", "LINK-USD", "XRP-USD",
    # laggards / chop (deliberately not all winners)
    "NIO", "MRNA", "PFE", "F",
]
COSTS = {"4bps": 0.0004, "10bps": 0.0010, "25bps": 0.0025}
PRIMARY_COST = "4bps"
MAX_HOLD_BARS = 30
WARMUP = 215
START_EQUITY = 10_000.0
RISK_PRIMARY = 0.01
RISK_SENS = 0.005
MAX_CONCURRENT = 5
MAX_PORTFOLIO_RISK = 0.05
MIN_TRADES_ELIGIBLE = 10

GATES = {
    "market": ("market gate is",),
    "rvol": ("relative volume below 0.80x",),
    "adx": ("ADX below 20",),
    "rr": ("reward/risk below 2.0:1",),
    "mtf": ("weekly/daily/4h alignment not confirmed",),
}
ALL_GATES = list(GATES)
CONFIGS = [("S0_structural", set())]
CONFIGS += [(f"S_plus_{g}", {g}) for g in ALL_GATES]
CONFIGS.append(("F0_full_ex15m", set(ALL_GATES)))
CONFIGS += [(f"F_minus_{g}", set(ALL_GATES) - {g}) for g in ALL_GATES]
EXITS = ["scanner", "noexit", "protect1R"]


# ------------------------------------------------------------------ data
def cached(name, build):
    path = os.path.join(CACHE, name + ".pkl")
    if os.path.exists(path):
        return pd.read_pickle(path)
    df = build()
    df.to_pickle(path)
    return df


def load_symbol(sym):
    """Live-exact data: 4h bars, 2y daily, 5y weekly (same fns as live)."""
    h4 = cached(f"h4_{sym}", lambda: m.download_data(sym, "4h", "2y"))
    d1 = cached(f"d1_{sym}", lambda: m.download_confirmation_data(sym, "1d", "2y"))
    w1 = cached(f"w1_{sym}", lambda: m.download_confirmation_data(sym, "1wk", "5y"))
    time.sleep(0.25)
    return h4, d1, w1


def _as_et(df):
    if df.index.tz is None:
        df = df.copy()
        df.index = df.index.tz_localize("America/New_York")
    return df


# ------------------------------------------------------- point-in-time
def regime_at(qqq_ind, qqq_raw, spy_raw, j):
    """Mirror get_market_regime scoring using only bars <= j (no lookahead)."""
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


def generate_signals(sym, df, daily, weekly, qqq_4h, spy_4h, qqq_ind):
    """Walk forward; classify each closed 4h bar using only data known then."""
    daily = _as_et(daily)
    weekly = _as_et(weekly)
    qqq_idx = qqq_4h.index
    signals = [None] * len(df)
    tally = Counter()
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
        # Live-exact MTF: same functions, now = signal-bar close
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
        row["regime_score"] = regime["score"]
        if sr.is_structural_candidate(row):
            n_struct += 1
            for r in sr.validation_reasons(row):
                tally[r] += 1
        reasons = [r for r in sr.validation_reasons(row) if "15-minute" not in r]
        row["reject_reasons"] = reasons
        signals[i] = row
    return signals, n_struct, dict(tally)


def fresh_buy_audit(sym, df, signals):
    """Audit the fresh_buy -> BUY -> entry -> structural funnel. No rule change."""
    ind = m.add_indicators(df)
    a = {"symbol": sym, "bars": 0, "fresh_buy_raw": 0, "state_BUY": 0,
         "buy_entry_yes": 0, "buy_structural": 0,
         "blockers": Counter(), "pullback_state": 0}
    for i in range(WARMUP, len(df)):
        row = signals[i]
        if not row:
            continue
        a["bars"] += 1
        last, prev = ind.iloc[i], ind.iloc[i - 1]
        fb = (last["EMA21"] > last["EMA55"] and prev["EMA21"] <= prev["EMA55"]
              and last["Close"] > last["EMA200"])
        if fb:
            a["fresh_buy_raw"] += 1
        if row.get("state") == "PULLBACK BUY":
            a["pullback_state"] += 1
        if row.get("state") == "BUY":
            a["state_BUY"] += 1
            if row.get("entry") == "YES":
                a["buy_entry_yes"] += 1
            else:
                a["blockers"]["entry_not_YES(state BUY)"] += 1
            if sr.is_structural_candidate(row):
                a["buy_structural"] += 1
            else:
                if row.get("protection") != "SAFE":
                    a["blockers"][f"protection={row.get('protection')}"] += 1
                if row.get("above_vwap") is not True:
                    a["blockers"]["above_vwap False"] += 1
                try:
                    lo, hi = map(float, str(row["buy_zone"]).split("-", 1))
                    px = float(row["price"])
                    if not (lo <= px <= hi):
                        a["blockers"]["price outside buy_zone"] += 1
                except Exception:
                    a["blockers"]["buy_zone unparsable"] += 1
    a["blockers"] = dict(a["blockers"])
    return a


# ----------------------------------------------------------------- gates
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

# ---------------------------------------------------------------- trading
def close_time(sym, ts):
    return pd.Timestamp(sr.bar_close_at(ts, sym))


def _outcome(entry, stop, exit_px, cost):
    risk_frac = (entry - stop) / entry
    gross_ret = (exit_px - entry) / entry
    net_ret = gross_ret - cost
    return risk_frac, gross_ret / risk_frac, net_ret / risk_frac, net_ret


def walk_exit(sym, df, signals, i, entry, stop, tp1, exit_mode, cost, start_j=None):
    """First touch wins; stop wins same-bar ties. EXIT exits at NEXT bar open.

    Returns (exit_px, j, reason, exit_time, mfe_r, counterfactual|None).
    Counterfactual: for EXIT-triggered exits, what stop/tp1/time would have done.
    """
    n = len(df)
    end = min(i + MAX_HOLD_BARS, n - 1)
    j0 = i + 1 if start_j is None else start_j
    risk_frac = (entry - stop) / entry
    mfe_r = 0.0
    for j in range(j0, end + 1):
        lo = float(df["Low"].iloc[j])
        hi = float(df["High"].iloc[j])
        mfe_r = max(mfe_r, ((hi - entry) / entry) / risk_frac)
        if lo <= stop:
            return stop, j, "stop", close_time(sym, df.index[j]), mfe_r, None
        if hi >= tp1:
            return tp1, j, "target", close_time(sym, df.index[j]), mfe_r, None
        srow = signals[j]
        if exit_mode != "noexit" and srow and srow.get("state") == "EXIT":
            trigger = exit_mode == "scanner" or mfe_r >= 1.0
            if trigger:
                cf = None
                if start_j is None:  # only top-level calls record counterfactual
                    cf_px, cf_j, cf_r, _, cf_mfe, _ = walk_exit(
                        sym, df, signals, i, entry, stop, tp1, "noexit", cost,
                        start_j=j)
                    _, _, cf_net_r, _ = _outcome(entry, stop, cf_px, cost)
                    cf = {"reason": cf_r, "net_r": round(cf_net_r, 3),
                          "exit_bar": cf_j, "mfe_r": round(cf_mfe, 3)}
                if j + 1 < n:
                    px = float(df["Open"].iloc[j + 1])
                    return px, j + 1, "scanner-exit", df.index[j + 1], mfe_r, cf
                px = float(df["Close"].iloc[j])
                return px, j, "scanner-exit", close_time(sym, df.index[j]), mfe_r, cf
    px = float(df["Close"].iloc[end])
    return px, end, "time", close_time(sym, df.index[end]), mfe_r, None


def gen_trades(sym, signals, df, required, exit_mode):
    """Trades are cost-independent; costs applied later in metrics/portfolio."""
    trades = []
    skipped_gap = 0
    n = len(df)
    i = WARMUP
    while i < n - 1:
        row = signals[i]
        if row and passes(row, required):
            stop = float(row["stop"])
            tp1 = float(row["tp1"])
            entry = float(df["Open"].iloc[i + 1])
            entry_time = df.index[i + 1]
            if entry <= stop:
                skipped_gap += 1
                i += 1
                continue
            if entry >= tp1:
                exit_px, j, reason = entry, i + 1, "gap-above-target"
                exit_time, mfe_r, cf = entry_time, 0.0, None
                instant = True
            else:
                exit_px, j, reason, exit_time, mfe_r, cf = walk_exit(
                    sym, df, signals, i, entry, stop, tp1, exit_mode, 0.0)
                instant = False
            t = {"symbol": sym, "entry_time": entry_time, "exit_time": exit_time,
                 "state": row["state"], "regime": row.get("regime_label"),
                 "entry": entry, "stop": stop, "tp1": tp1, "exit": exit_px,
                 "reason": reason, "hold_bars": j - i, "mfe_r": round(mfe_r, 3),
                 "signal_id": row.get("signal_id"), "instant": instant,
                 "exit_counterfactual": cf}
            trades.append(t)
            i = j + 1
        else:
            i += 1
    return trades, skipped_gap


# ------------------------------------------------------- portfolio (v2)
def simulate_portfolio(trades, closes, cost, risk_pct):
    """Event-driven, chronological.

    Size = risk_pct * marked equity at entry. Caps: 5 concurrent positions,
    5% total open risk. Mark-to-market equity curve for drawdown.
    """
    events = []
    for t in trades:
        if not t.get("instant"):
            events.append((t["exit_time"], 0, t))
        events.append((t["entry_time"], 1, t))
    events.sort(key=lambda e: (e[0], e[1]))

    realized = START_EQUITY
    open_pos = []
    by_id = {}
    skipped_cap_count = 0
    skipped_cap_risk = 0
    peak = realized
    max_dd = 0.0
    curve = []
    prev_t = None
    open_time = pd.Timedelta(0)
    total_time = pd.Timedelta(0)

    def mark(sym, t):
        s = closes[sym]
        idx = s.index.searchsorted(t, side="right") - 1
        return float(s.iloc[idx]) if idx >= 0 else float(s.iloc[0])

    def marked_equity(t):
        unreal = 0.0
        for p in open_pos:
            tr = p["trade"]
            unreal += ((mark(tr["symbol"], t) - tr["entry"]) / tr["entry"]) * p["size"]
        return realized + unreal

    for t, kind, tr in events:
        if prev_t is not None and t > prev_t:
            dt = t - prev_t
            total_time += dt
            if open_pos:
                open_time += dt
        prev_t = t
        if kind == 1:  # entry
            eq = marked_equity(t)
            if tr.get("instant"):
                # gap-above-target: scratched at the open, no position held
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
        else:  # exit
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


def apply_cost(trades, cost):
    out = []
    for t in trades:
        risk_frac, gross_r, net_r, net_ret = _outcome(
            t["entry"], t["stop"], t["exit"], cost)
        d = dict(t)
        d.update(gross_r=round(gross_r, 3), net_r=round(net_r, 3),
                 net_ret_pct=round(net_ret * 100, 3),
                 year=pd.Timestamp(t["entry_time"]).year,
                 asset="crypto" if t["symbol"].endswith("-USD") else "stock")
        out.append(d)
    return out


def summarize(label, trades, port, skipped_gap, cost_name):
    t = pd.DataFrame(trades)
    if t.empty:
        return {"config": label, "cost": cost_name, "trades": 0}
    wins = t[t["net_ret_pct"] > 0]
    losses = t[t["net_ret_pct"] <= 0]
    gw, gl = wins["net_ret_pct"].sum(), -losses["net_ret_pct"].sum()
    n = len(t)
    exp_net_r = float(t["net_r"].mean())
    max_dd = float(port["max_drawdown"])
    eligible = n >= MIN_TRADES_ELIGIBLE
    return {
        "config": label, "cost": cost_name, "trades": n,
        "win_rate_pct": round(len(wins) / n * 100, 1),
        "avg_win_pct": round(float(wins["net_ret_pct"].mean()), 2) if len(wins) else 0.0,
        "avg_loss_pct": round(float(losses["net_ret_pct"].mean()), 2) if len(losses) else 0.0,
        "expectancy_net_r": round(exp_net_r, 3),
        "expectancy_gross_r": round(float(t["gross_r"].mean()), 3),
        "profit_factor": round(gw / gl, 2) if gl > 0 else None,
        "total_return_pct": round((port["final_equity"] / START_EQUITY - 1) * 100, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "avg_hold_bars": round(float(t["hold_bars"].mean()), 1),
        "market_exposure_pct": round(port["exposure"] * 100, 1),
        "skipped_gap_below_stop": skipped_gap,
        "skipped_max_positions": port["skipped_cap_count"],
        "skipped_max_risk": port["skipped_cap_risk"],
        "exit_reasons": t["reason"].value_counts().to_dict(),
        "eligible": eligible,
    }

# ------------------------------------------------------------------- main
def run_universe(universe, tag):
    """Generate (or load) signals for every symbol; return dicts."""
    print(f"[{tag}] loading data + signals for {len(universe)} symbols", flush=True)
    qqq_4h, _, _ = load_symbol("QQQ")
    spy_4h, _, _ = load_symbol("SPY")
    qqq_ind = m.add_indicators(qqq_4h)
    sigs, dfs, audits = {}, {}, {}
    n_struct_total = 0
    tally = Counter()
    for n, sym in enumerate(universe):
        print(f"  [{n+1}/{len(universe)}] {sym}", flush=True)
        df, d1, w1 = load_symbol(sym)
        if df.empty or len(df) < WARMUP + 50:
            print(f"    SKIP {sym}: insufficient 4h history ({len(df)} bars)")
            continue
        spath = os.path.join(CACHE, f"signals_{tag}_{sym}.pkl")
        if os.path.exists(spath):
            signals, n_struct, tal = pd.read_pickle(spath)
        else:
            signals, n_struct, tal = generate_signals(
                sym, df, d1, w1, qqq_4h, spy_4h, qqq_ind)
            pd.to_pickle((signals, n_struct, tal), spath)
        sigs[sym], dfs[sym] = signals, df
        n_struct_total += n_struct
        tally.update(tal)
        audits[sym] = fresh_buy_audit(sym, df, signals)
    closes = {s: dfs[s]["Close"] for s in dfs}
    return sigs, dfs, closes, audits, n_struct_total, dict(tally)


def run_configs(sigs, dfs, closes, configs, exits, tag, risk_pct, cost_name,
                trade_rows, curve_rows):
    """Generate trades once per config x exit; portfolio per cost/risk."""
    cost = COSTS[cost_name]
    results = []
    for cfg_name, required in configs:
        for exit_mode in exits:
            label = f"{cfg_name}__{exit_mode}"
            trades, skipped_gap = [], 0
            for sym in sigs:
                tr, sk = gen_trades(sym, sigs[sym], dfs[sym], required, exit_mode)
                trades.extend(tr)
                skipped_gap += sk
            tc = apply_cost(trades, cost)
            port = simulate_portfolio(tc, closes, cost, risk_pct)
            m_ = summarize(f"{tag}:{label}", tc, port, skipped_gap, cost_name)
            m_["universe"] = tag
            m_["exit_mode"] = exit_mode
            m_["risk_pct"] = risk_pct
            results.append(m_)
            for tr in tc:
                cf = tr.get("exit_counterfactual") or {}
                r = {k: v for k, v in tr.items()
                     if k != "exit_counterfactual"}
                r.update(config=cfg_name, exit_mode=exit_mode, cost=cost_name,
                         universe=tag, risk_pct=risk_pct,
                         cf_reason=cf.get("reason"), cf_net_r=cf.get("net_r"))
                r["entry_time"] = pd.Timestamp(r["entry_time"]).isoformat()
                r["exit_time"] = pd.Timestamp(r["exit_time"]).isoformat()
                trade_rows.append(r)
            for t, eq, real, nopen in port["curve"]:
                curve_rows.append(
                    {"config": f"{tag}:{label}", "cost": cost_name,
                     "risk_pct": risk_pct, "time": pd.Timestamp(t).isoformat(),
                     "equity": round(eq, 2), "realized": round(real, 2),
                     "open_positions": nopen})
            print(f"    {tag}:{label} @{cost_name}/{risk_pct}: "
                  f"n={m_['trades']} exp_net_r={m_.get('expectancy_net_r')}",
                  flush=True)
    return results


def breakdowns(trades):
    t = pd.DataFrame(trades)
    out = {}
    if t.empty:
        return out
    for key in ["symbol", "regime", "state", "asset", "year"]:
        rows = []
        for name, g in t.groupby(key):
            w = g[g["net_ret_pct"] > 0]
            rows.append({"group": str(name), "trades": len(g),
                         "win_rate_pct": round(len(w) / len(g) * 100, 1),
                         "expectancy_net_r": round(g["net_r"].mean(), 3),
                         "expectancy_pct": round(g["net_ret_pct"].mean(), 3)})
        out[f"by_{key}"] = sorted(rows, key=lambda r: -r["trades"])
    return out


def exit_comparison_rows(trade_rows, configs):
    """For scanner-EXIT trades: what would stop/tp1/time have done?"""
    rows = []
    for r in trade_rows:
        if r["config"] not in configs or r["exit_mode"] == "noexit":
            continue
        if r["reason"] != "scanner-exit":
            continue
        rows.append({
            "config": r["config"], "exit_mode": r["exit_mode"],
            "symbol": r["symbol"], "entry_time": r["entry_time"],
            "entry": r["entry"], "exit": r["exit"],
            "realized_net_r": r["net_r"], "mfe_r_at_exit": r.get("mfe_r"),
            "counterfactual_reason": r.get("cf_reason"),
            "counterfactual_net_r": r.get("cf_net_r"),
        })
    return rows


def main():
    # ---------------- Phase 1: 15-symbol universe, full ablation @4bps
    sigs15, dfs15, closes15, audits15, n_struct15, tally15 = run_universe(
        UNIVERSE_15, "U15")
    trade_rows, curve_rows = [], []
    abl15 = run_configs(sigs15, dfs15, closes15, CONFIGS, EXITS, "U15",
                        RISK_PRIMARY, PRIMARY_COST, trade_rows, curve_rows)
    pd.DataFrame(abl15).to_csv(os.path.join(BASE, "backtest_ablation.csv"),
                               index=False)

    # best eligible configs by net expectancy R (primary sort per spec)
    elig = [r for r in abl15 if r["eligible"] and r["cost"] == PRIMARY_COST]
    by_net_r = sorted(elig, key=lambda r: -r["expectancy_net_r"])
    top_cfgs = [r["config"].split(":", 1)[1].split("__")[0] for r in by_net_r[:3]]
    print("\nTop configs by net expectancy R:", top_cfgs, flush=True)

    # ---------------- cost sensitivity: S0 + top3, all exits, 10/25bps
    sens_targets = ["S0_structural"] + [c for c in top_cfgs if c != "S0_structural"]
    sens_cfgs = [(c, dict(CONFIGS)[c]) for c in sens_targets]
    cost_rows = []
    for cost_name in ["10bps", "25bps"]:
        cost_rows += run_configs(sigs15, dfs15, closes15, sens_cfgs, EXITS, "U15",
                                 RISK_PRIMARY, cost_name, trade_rows, curve_rows)

    # ---------------- risk sensitivity 0.5%: S0 + top3 + F0, all exits @4bps
    risk_targets = list(dict.fromkeys(
        ["S0_structural"] + top_cfgs + ["F0_full_ex15m"]))
    risk_cfgs = [(c, dict(CONFIGS)[c]) for c in risk_targets]
    risk_rows = run_configs(sigs15, dfs15, closes15, risk_cfgs, EXITS, "U15",
                            RISK_SENS, PRIMARY_COST, trade_rows, curve_rows)

    # ---------------- Phase 2: expanded universe, key configs @4bps
    sigsX, dfsX, closesX, auditsX, n_structX, tallyX = run_universe(
        UNIVERSE_X, "UX")
    key_cfgs = [(c, dict(CONFIGS)[c]) for c in risk_targets]
    ablX = run_configs(sigsX, dfsX, closesX, key_cfgs, EXITS, "UX",
                       RISK_PRIMARY, PRIMARY_COST, trade_rows, curve_rows)

    # ---------------- breakdowns on S0 protect1R (U15) + winner
    s0_protect = [r for r in trade_rows if r["universe"] == "U15"
                  and r["config"] == "S0_structural"
                  and r["exit_mode"] == "protect1R"
                  and r["cost"] == PRIMARY_COST and r["risk_pct"] == RISK_PRIMARY]
    bd = {"S0_structural__protect1R_U15": breakdowns(s0_protect)}
    if by_net_r:
        w = by_net_r[0]
        wcfg, wexit = w["config"].split(":", 1)[1].split("__")
        wtr = [r for r in trade_rows if r["universe"] == "U15"
               and r["config"] == wcfg and r["exit_mode"] == wexit
               and r["cost"] == PRIMARY_COST and r["risk_pct"] == RISK_PRIMARY]
        bd[f"winner_{wcfg}__{wexit}_U15"] = breakdowns(wtr)

    # ---------------- exit comparison: baseline + top configs
    exit_cfgs = list(dict.fromkeys(["S0_structural"] + top_cfgs))
    exit_rows = exit_comparison_rows(trade_rows, exit_cfgs)
    pd.DataFrame(exit_rows).to_csv(os.path.join(BASE, "backtest_exit_comparison.csv"),
                                   index=False)
    # counterfactual tally
    cf_tally = Counter()
    cf_net = []
    for r in exit_rows:
        cr = r["counterfactual_reason"]
        if cr:
            cf_tally[cr] += 1
            if cr == "target":
                cf_net.append(1)
    n_exit_trades = len(exit_rows)
    n_would_tp1 = cf_tally.get("target", 0)
    n_would_stop = cf_tally.get("stop", 0)

    # ---------------- QQQ benchmark
    import yfinance as yf
    qd = yf.download("QQQ", interval="1d", period="5y", progress=False,
                     auto_adjust=True, threads=False)
    if isinstance(qd.columns, pd.MultiIndex):
        qd.columns = [c[0] for c in qd.columns]
    qd = qd.dropna()
    qbh = float(qd["Close"].iloc[-1] / qd["Close"].iloc[0] - 1) * 100

    # ---------------- files
    pd.DataFrame(trade_rows).to_csv(os.path.join(BASE, "backtest_trades.csv"),
                                    index=False)
    pd.DataFrame(curve_rows).to_csv(os.path.join(BASE, "backtest_equity_curve.csv"),
                                    index=False)
    results = {
        "scanner_version": sr.SCANNER_VERSION, "rule_version": sr.RULE_VERSION,
        "window_note": "2024-09-16 -> 2026-09-14 (2y 1h history cap)",
        "universes": {"U15": UNIVERSE_15, "UX": UNIVERSE_X},
        "structural_candidates": {"U15": n_struct15, "UX": n_structX},
        "gate_rejections": {"U15": tally15, "UX": tallyX},
        "ablation_U15_4bps_1pct": abl15,
        "cost_sensitivity_U15": cost_rows,
        "risk_sensitivity_U15_05pct": risk_rows,
        "expanded_UX_4bps_1pct": ablX,
        "breakdowns": bd,
        "exit_counterfactual": {
            "n_scanner_exit_trades": n_exit_trades,
            "would_have_hit_tp1": n_would_tp1,
            "would_have_hit_stop": n_would_stop,
            "would_have_timed_out": cf_tally.get("time", 0),
            "tally": dict(cf_tally),
        },
        "fresh_buy_audit_U15": audits15,
        "fresh_buy_audit_UX": auditsX,
        "qqq_buy_hold_pct_5y": round(qbh, 2),
        "notes": ("Live-exact 4h bars (sr.resample_closed_4h), daily 2y / weekly 5y "
                  "via live download_confirmation_data + timeframe_trend_confirmed; "
                  "15m confirmation excluded (no 2y intraday history); premarket "
                  "excluded (live-only). Next-bar-open entry. Stop wins same-bar "
                  "ties. R net of costs; expectancy judged on net R. Portfolio: "
                  "event-driven, 1% marked-equity risk/trade, max 5 concurrent, "
                  "max 5% open risk. Configs with <10 trades flagged ineligible."),
    }
    with open(os.path.join(BASE, "backtest_results_v2.json"), "w") as f:
        json.dump(results, f, indent=2)

    # ---------------- printed ranking + conclusion
    df_abl = pd.DataFrame(abl15)
    df_abl["sort_r"] = df_abl["expectancy_net_r"]
    df_abl.loc[~df_abl["eligible"], "sort_r"] = -999
    df_abl = df_abl.sort_values("sort_r", ascending=False)
    cols = ["config", "trades", "win_rate_pct", "avg_win_pct", "avg_loss_pct",
            "expectancy_net_r", "profit_factor", "total_return_pct",
            "max_drawdown_pct", "market_exposure_pct", "eligible"]
    print("\n==== ABLATION (U15, 4bps, 1% risk) sorted by net expectancy R ====")
    print(df_abl[cols].to_string(index=False))
    print(f"\nEXIT counterfactual: {n_exit_trades} scanner-EXIT trades -> "
          f"would-be TP1 {n_would_tp1}, stop {n_would_stop}, "
          f"time {cf_tally.get('time', 0)}")
    print("Files written: backtest_results_v2.json, backtest_ablation.csv, "
          "backtest_trades.csv, backtest_equity_curve.csv, "
          "backtest_exit_comparison.csv")
    return results


if __name__ == "__main__":
    main()
