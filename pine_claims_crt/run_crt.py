"""Weekly outside-claims sweep: Candle Range Theory (CRT) sweep-and-return.

Source: @think_ict IG reel (2026-10-10) + TTrades fractal-model article + corroborating
reels (see README.md). Rule: on 4H bar i, if the candle sweeps the PRIOR candle's range
extreme and CLOSES back inside that range, expect price to gravitate toward the prior
candle's far end. Bullish (swept low) -> LONG; bearish (swept high) -> SHORT.

Rule is pre-registered in README.md (frozen before running). pine_backtest.py is
imported UNMODIFIED. Mode B exits mirrored bar-for-bar from the canonical engine
(gen_pine_trades), direction-aware for shorts. Local-only research.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_claims_crt")
sys.path.insert(0, BASE)
import pine_backtest as pb

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "crt_results.json")
os.makedirs(OUTDIR, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

TP1_R_MULT = pb.TP_ATR / pb.SL_ATR  # 2.0/1.5 = 1.333, canonical Mode B ratio
MARGIN_ATR = 0.25                   # perturbation: sweep must exceed 0.25*ATR
for _k, _v in (("50bps", 0.005), ("75bps", 0.0075), ("100bps", 0.01)):
    pb.COSTS.setdefault(_k, _v)
COSTS_ALL = [("4bps", 0.0004), ("25bps", 0.0025), ("50bps", 0.005),
             ("75bps", 0.0075), ("100bps", 0.01)]


# ------------------------------------------------ direction-aware plumbing
def outcome_dir(entry, stop, exit_px, cost, d):
    """pb._outcome generalized: d=+1 long, d=-1 short."""
    risk_frac = (entry - stop) / entry * d
    gross_ret = (exit_px - entry) / entry * d
    net_ret = gross_ret - cost
    return risk_frac, gross_ret / risk_frac, net_ret / risk_frac, net_ret


def simulate_portfolio_dir(trades, closes, cost, risk_pct):
    """Mirror of pb.simulate_portfolio, long/short aware via trade['dir']."""
    events = []
    for t in trades:
        events.append((t["exit_time"], 0, t))
        events.append((t["entry_time"], 1, t))
    events.sort(key=lambda e: (e[0], e[1]))
    realized = pb.START_EQUITY
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
        unreal = sum(((mark(tr["symbol"], t) - tr["entry"]) / tr["entry"])
                      * tr["dir"] * p["size"]
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
            if len(open_pos) >= pb.MAX_CONCURRENT:
                skipped_cap_count += 1
                continue
            if open_risk + risk_pct > pb.MAX_PORTFOLIO_RISK + 1e-9:
                skipped_cap_risk += 1
                continue
            risk_dollars = risk_pct * eq
            risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"] * tr["dir"]
            open_pos.append({"trade": tr, "risk_dollars": risk_dollars,
                             "size": risk_dollars / risk_frac, "risk_frac": risk_frac})
            by_id[id(tr)] = open_pos[-1]
        else:
            pos = by_id.pop(id(tr), None)
            if pos is None:
                continue
            _, _, net_r, _ = outcome_dir(tr["entry"], tr["stop"], tr["exit"],
                                         cost, tr["dir"])
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


def summarize_dir(label, trades, port, skipped_gap, cost_name):
    """Mirror of pb.summarize, direction-aware."""
    t = pd.DataFrame(trades)
    if t.empty:
        return {"config": label, "cost": cost_name, "trades": 0}
    rows = [outcome_dir(tr["entry"], tr["stop"], tr["exit"],
                        pb.COSTS[cost_name], tr["dir"])[2] for tr in trades]
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
        "total_return_pct": round((port["final_equity"] / pb.START_EQUITY - 1) * 100, 2),
        "max_drawdown_pct": round(port["max_drawdown"] * 100, 2),
        "avg_hold_bars": round(float(t["hold_bars"].mean()), 1),
        "market_exposure_pct": round(port["exposure"] * 100, 1),
        "tp1_hit_rate_pct": round(float(t["tp1_hit"].mean()) * 100, 1),
        "skipped_gap_below_stop": skipped_gap,
        "skipped_max_positions": port["skipped_cap_count"],
        "skipped_max_risk": port["skipped_cap_risk"],
        "exit_reasons": t["reason"].value_counts().to_dict(),
    }


# ------------------------------------------------ trade management (Mode B)
def _manage(pos, df, i, n, sym):
    """Mode B management, mirrored from gen_pine_trades; direction-aware."""
    d = pos["dir"]
    bar = df.iloc[i]
    lo, hi, close = float(bar["Low"]), float(bar["High"]), float(bar["Close"])
    atr = float(bar["atr"])
    if not pos["tp_hit"]:
        if d == 1 and hi >= pos["tp1"]:
            pos["tp_hit"] = True  # 50% filled at TP1 limit
        elif d == -1 and lo <= pos["tp1"]:
            pos["tp_hit"] = True
    if pos["tp_hit"]:
        if d == 1:
            pos["runner"] = max(pos["runner"], close - atr * pb.TRAIL_ATR)
        else:
            pos["runner"] = min(pos["runner"], close + atr * pb.TRAIL_ATR)
    trend_bull = bar["e21"] > bar["e55"] and close > bar["e200"]
    trend_bear = bar["e21"] < bar["e55"] and close < bar["e200"]
    done = False
    if d == 1:
        if close < pos["runner"]:
            reason = "stop"
            done = True
        elif close < bar["e55"] or trend_bear:
            reason = "ema55-bear" if trend_bear else "ema55-break"
            done = True
    else:
        if close > pos["runner"]:
            reason = "stop"
            done = True
        elif close > bar["e55"] or trend_bull:
            reason = "ema55-bull" if trend_bull else "ema55-break"
            done = True
    if done:
        if i + 1 < n:
            exit_px = float(df["Open"].iloc[i + 1])
            exit_idx, exit_time = i + 1, df.index[i + 1]
        else:
            exit_px, exit_time = close, df.index[i]
            exit_idx = i
        risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"] * d
        r1 = ((pos["tp1"] - pos["entry"]) / pos["entry"] * d / risk_frac
              if pos["tp_hit"] else None)
        r2 = (exit_px - pos["entry"]) / pos["entry"] * d / risk_frac
        r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
        net_ret_blend = r_blend * risk_frac
        exit_synth = pos["entry"] * (1 + net_ret_blend * d)
        trade = {
            "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
            "exit": exit_synth, "reason": reason, "dir": d,
            "tp1_hit": pos["tp_hit"],
            "entry_time": pos["entry_time"], "exit_time": exit_time,
            "hold_bars": exit_idx - pos["entry_idx"],
            "signal_time": pos["signal_time"],
        }
        return True, trade
    return False, None


def _open_pos(entry, stop, df, entry_idx, sig_idx, d):
    risk = (entry - stop) * d
    return {
        "entry": float(entry), "stop": float(stop),
        "tp1": float(entry + d * risk * TP1_R_MULT),
        "tp_hit": False, "runner": float(stop), "dir": d,
        "entry_idx": entry_idx,
        "entry_time": df.index[entry_idx],
        "signal_time": df.index[sig_idx].isoformat(),
    }


# ------------------------------------------------ signal generation
def gen_crt_trades(sym, df, mode, margin=False):
    """CRT sweep-and-return. mode in {'long','short','ls'}.
    margin=True -> perturbation: sweep depth must exceed 0.25*ATR."""
    trades = []
    stats = {"sweep_bull": 0, "sweep_bear": 0, "ambiguous": 0,
             "trades_long": 0, "trades_short": 0, "skipped_gap": 0}
    n = len(df)
    o = df["Open"].to_numpy()
    h = df["High"].to_numpy()
    l = df["Low"].to_numpy()
    c = df["Close"].to_numpy()
    atr = df["atr"].to_numpy()
    i = pb.WARMUP + 1
    in_trade = False
    pos = None
    while i < n - 1:  # need i+1 for entry bar
        if in_trade:
            done, trade = _manage(pos, df, i, n, sym)
            if done:
                trades.append(trade)
                in_trade = False
                pos = None
            i += 1
            continue
        bull_sweep = l[i] < l[i - 1]
        bear_sweep = h[i] > h[i - 1]
        bull_close = c[i] > l[i - 1] and c[i] <= h[i - 1]
        bear_close = c[i] < h[i - 1] and c[i] >= l[i - 1]
        if margin:
            bull_sweep = bull_sweep and (l[i - 1] - l[i]) >= MARGIN_ATR * atr[i]
            bear_sweep = bear_sweep and (h[i] - h[i - 1]) >= MARGIN_ATR * atr[i]
        bull = bull_sweep and bull_close
        bear = bear_sweep and bear_close
        if bull:
            stats["sweep_bull"] += 1
        if bear:
            stats["sweep_bear"] += 1
        if bull and bear:
            stats["ambiguous"] += 1
        elif (mode in ("long", "ls") and bull) or \
             (mode == "short" and bear and not bull) or \
             (mode == "ls" and bear and not bull):
            d = 1 if bull else -1
            entry = float(o[i + 1])
            stop = float(l[i]) if d == 1 else float(h[i])
            if (entry - stop) * d > 0:
                pos = _open_pos(entry, stop, df, i + 1, i, d)
                in_trade = True
                stats["trades_long" if d == 1 else "trades_short"] += 1
                done, trade = _manage(pos, df, i + 1, n, sym)
                if done:
                    trades.append(trade)
                    in_trade = False
                    pos = None
                i += 2
                continue
            else:
                stats["skipped_gap"] += 1
        i += 1
    return trades, stats


# ------------------------------------------------ stats / reporting
def per_ticker_stats(sym, trades):
    out = {"symbol": sym, "trades": len(trades)}
    if not trades:
        return out
    for cost_name, cost in pb.COSTS.items():
        net_rs = [outcome_dir(tr["entry"], tr["stop"], tr["exit"], cost,
                              tr.get("dir", 1))[2] for tr in trades]
        s = pd.Series(net_rs)
        wins = s[s > 0]
        losses = s[s <= 0]
        gw, gl = float(wins.sum()), float(-losses.sum())
        out[cost_name] = {
            "trades": len(trades),
            "win_rate_pct": round(float((s > 0).mean()) * 100, 1),
            "expectancy_net_r": round(float(s.mean()), 3),
            "profit_factor": round(gw / gl, 2) if gl > 0 else None,
            "total_net_r": round(float(s.sum()), 2),
        }
    return out


def split_stats(trades, cost):
    def rs(t):
        return outcome_dir(t["entry"], t["stop"], t["exit"], cost,
                           t.get("dir", 1))[2]
    def ts(t):
        return pd.to_datetime(t["entry_time"]).tz_localize(None)
    years = {}
    for t in trades:
        y = ts(t).year
        years.setdefault(y, []).append(rs(t))
    dev = [rs(t) for t in trades if ts(t) < pd.Timestamp("2025-01-01")]
    val = [rs(t) for t in trades if ts(t) >= pd.Timestamp("2025-01-01")]
    return {
        "by_year": {y: {"n": len(v), "exp_r": round(float(np.mean(v)), 3)}
                    for y, v in sorted(years.items())},
        "dev_2023_2024": {"n": len(dev),
                          "exp_r": round(float(np.mean(dev)), 3) if dev else None},
        "val_2025_2026": {"n": len(val),
                          "exp_r": round(float(np.mean(val)), 3) if val else None},
    }


def run_variant(name, mode, margin, data, closes):
    all_trades, per_sym, agg = [], {}, {
        "sweep_bull": 0, "sweep_bear": 0, "ambiguous": 0,
        "trades_long": 0, "trades_short": 0, "skipped_gap": 0}
    for sym in data:
        tr, st = gen_crt_trades(sym, data[sym], mode, margin)
        per_sym[sym] = tr
        all_trades.extend(tr)
        for k in agg:
            agg[k] += st[k]
    all_trades.sort(key=lambda t: t["entry_time"])
    pooled = []
    for cost_name, cost in COSTS_ALL:
        port = simulate_portfolio_dir(all_trades, closes, cost, pb.RISK_PCT)
        pooled.append(summarize_dir(f"CRT:{name}:4h", all_trades, port,
                                    agg["skipped_gap"], cost_name))
    return {
        "name": name, "mode": mode, "margin_025atr": margin,
        "trades": len(all_trades), "attribution": dict(agg), "pooled": pooled,
        "per_ticker": [per_ticker_stats(s, per_sym.get(s, [])) for s in data],
        "splits_25bps": split_stats(all_trades, 0.0025),
        "splits_50bps": split_stats(all_trades, 0.005),
    }, all_trades


def main():
    data, closes = {}, {}
    dropped = []
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        if "Volume" not in df.columns or df["Volume"].isna().all():
            dropped.append(sym)
            continue
        df = pb.add_pine_indicators(df)
        data[sym] = df
        closes[sym] = df["Close"]
    used = [s for s in WATCHLIST if s in data]
    print(f"loaded {len(used)} tickers; dropped: {dropped}", flush=True)

    results = {"variant": "CRT", "tp1_r_mult": TP1_R_MULT,
               "gate": "README.md", "variants": []}

    # BASE: canonical engine, rerun in-study
    base_trades, base_per, base_skipped = [], {}, 0
    for sym in used:
        tr, sg = pb.gen_pine_trades(sym, data[sym])
        base_per[sym] = tr
        base_trades.extend(tr)
        base_skipped += sg
    base_trades.sort(key=lambda t: t["entry_time"])
    base_pooled = []
    for cost_name, cost in COSTS_ALL:
        port = pb.simulate_portfolio(base_trades, closes, cost, pb.RISK_PCT)
        base_pooled.append(pb.summarize("CRT:BASE:4h", base_trades, port,
                                        base_skipped, cost_name))
    results["variants"].append({
        "name": "BASE", "trades": len(base_trades), "pooled": base_pooled,
        "per_ticker": [per_ticker_stats(s, base_per.get(s, [])) for s in used],
        "splits_25bps": split_stats(base_trades, 0.0025),
    })
    for p in base_pooled:
        print(f"BASE [{p['cost']}]: n={p['trades']} win={p['win_rate_pct']}% "
              f"exp={p['expectancy_net_r']}R PF={p['profit_factor']} "
              f"maxDD={p.get('max_drawdown_pct', '?')}%", flush=True)

    for name, mode, margin in [("CRT-LONG", "long", False),
                               ("CRT-LONG-MARGIN", "long", True),
                               ("CRT-SHORT", "short", False),
                               ("CRT-LS", "ls", False)]:
        v, trades = run_variant(name, mode, margin, data, closes)
        results["variants"].append(v)
        for p in v["pooled"]:
            print(f"{name} [{p['cost']}]: n={p['trades']} "
                  f"win={p['win_rate_pct']}% exp={p['expectancy_net_r']}R "
                  f"PF={p['profit_factor']} maxDD={p.get('max_drawdown_pct', '?')}% "
                  f"| bull={v['attribution']['sweep_bull']} "
                  f"bear={v['attribution']['sweep_bear']} "
                  f"amb={v['attribution']['ambiguous']}", flush=True)

    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
