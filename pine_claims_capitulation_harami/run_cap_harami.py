"""Weekly outside-claims sweep #1: capitulation-candle harami reversal.

Source: @smart.forexpips IG reel (2026-09-21):
after a sharp downtrend, the largest red candle of the move is capitulation;
a fully-inside green harami the next bar = sellers stopped; enter long when
price closes above the big red candle's high; stop below its low.

Rule is pre-registered in README.md (frozen before running). pine_backtest.py
is imported UNMODIFIED. Mode B exits mirrored bar-for-bar from the canonical
engine. Adaptation (stated): claim defines risk = entry - low[i]; TP1 keeps
the canonical Mode B multiple TP1 = entry + 1.333*risk. Local-only research.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_claims_capitulation_harami")
sys.path.insert(0, BASE)
import pine_backtest as pb

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "cap_harami_results.json")
os.makedirs(OUTDIR, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

LOOKBACK = 10          # "largest of the move" window + downtrend length
TP1_R_MULT = pb.TP_ATR / pb.SL_ATR  # 2.0/1.5 = 1.333, canonical Mode B ratio
START_I_EXTRA = LOOKBACK  # need i-10 available on top of pb.WARMUP
# cost stress per canonical protocol item 6 (pb.COSTS only ships 4/25bps).
# Extra tiers are registered on the imported module at runtime only
# (pine_backtest.py file untouched; summarize() reads COSTS by name).
for _k, _v in (("50bps", 0.005), ("75bps", 0.0075), ("100bps", 0.01)):
    pb.COSTS.setdefault(_k, _v)
COSTS_ALL = [("4bps", 0.0004), ("25bps", 0.0025), ("50bps", 0.005),
             ("75bps", 0.0075), ("100bps", 0.01)]


def _manage(pos, df, i, n, sym):
    """Mode B management, mirrored from gen_pine_trades via run_pullback.py."""
    bar = df.iloc[i]
    lo, hi, close = float(bar["Low"]), float(bar["High"]), float(bar["Close"])
    if not pos["tp_hit"] and hi >= pos["tp1"]:
        pos["tp_hit"] = True  # 50% filled at TP1 limit
    if pos["tp_hit"]:
        pos["runner"] = max(pos["runner"],
                            close - float(bar["atr"]) * pb.TRAIL_ATR)
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
        risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]
        r1 = ((pos["tp1"] - pos["entry"]) / pos["entry"] / risk_frac
              if pos["tp_hit"] else None)
        r2 = (exit_px - pos["entry"]) / pos["entry"] / risk_frac
        r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
        net_ret_blend = r_blend * risk_frac
        exit_synth = pos["entry"] * (1 + net_ret_blend)
        trade = {
            "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
            "exit": exit_synth, "reason": reason,
            "tp1_hit": pos["tp_hit"],
            "entry_time": pos["entry_time"], "exit_time": exit_time,
            "hold_bars": exit_idx - pos["entry_idx"],
            "signal_time": pos["signal_time"],
        }
        return True, trade
    return False, None


def _open_pos(entry, stop, atr_tp1_risk, df, entry_idx, sig_idx):
    risk = entry - stop
    return {
        "entry": float(entry), "stop": float(stop),
        "tp1": float(entry + risk * atr_tp1_risk),
        "tp_hit": False, "runner": float(stop),
        "entry_idx": entry_idx,
        "entry_time": df.index[entry_idx],
        "signal_time": df.index[sig_idx].isoformat(),
    }


def gen_cap_harami_trades(sym, df):
    """Variant generator per frozen prereg. Returns (trades, stats)."""
    trades = []
    stats = {"capitulation_signals": 0, "haramis": 0, "triggers": 0,
             "expired": 0, "trades": 0, "skipped_gap": 0}
    n = len(df)
    o = df["Open"].to_numpy()
    h = df["High"].to_numpy()
    l = df["Low"].to_numpy()
    c = df["Close"].to_numpy()
    rng = h - l
    i = pb.WARMUP + START_I_EXTRA
    in_trade = False
    pos = None
    while i < n - 2:
        if in_trade:
            done, trade = _manage(pos, df, i, n, sym)
            if done:
                trades.append(trade)
                in_trade = False
                pos = None
            i += 1
            continue
        # capitulation candle at i, harami at i+1, trigger bar at i+2
        red = c[i] < o[i]
        biggest = rng[i] > rng[i - LOOKBACK:i].max()
        downtrend = c[i] < c[i - LOOKBACK]
        if red and biggest and downtrend:
            stats["capitulation_signals"] += 1
            j = i + 1
            green = c[j] > o[j]
            inside = h[j] <= h[i] and l[j] >= l[i]
            if green and inside:
                stats["haramis"] += 1
                k = i + 2
                if c[k] > h[i]:
                    entry = float(c[k])
                    stop = float(l[i])
                    if entry > stop:
                        pos = _open_pos(entry, stop, TP1_R_MULT, df, k, i)
                        stats["triggers"] += 1
                        stats["trades"] += 1
                        in_trade = True
                        done, trade = _manage(pos, df, k, n, sym)
                        if done:
                            trades.append(trade)
                            in_trade = False
                            pos = None
                    i = k + 1
                    continue
                else:
                    stats["expired"] += 1
        i += 1
    return trades, stats


def per_ticker_stats(sym, trades):
    out = {"symbol": sym, "trades": len(trades)}
    if not trades:
        return out
    for cost_name, cost in pb.COSTS.items():
        net_rs = [pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]
                  for tr in trades]
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
    """Expectancy by year and by dev/val split, at one cost."""
    def rs(t):
        return pb._outcome(t["entry"], t["stop"], t["exit"], cost)[2]
    def ts(t):
        return pd.to_datetime(t["entry_time"]).tz_localize(None)
    years = {}
    for t in trades:
        y = ts(t).year
        years.setdefault(y, []).append(rs(t))
    dev = [rs(t) for t in trades if ts(t) < pd.Timestamp("2025-01-01")]
    val = [rs(t) for t in trades if ts(t) >= pd.Timestamp("2025-01-01")]
    out = {
        "by_year": {y: {"n": len(v),
                        "exp_r": round(float(np.mean(v)), 3)} for y, v in
                    sorted(years.items())},
        "dev_2023_2024": {"n": len(dev),
                          "exp_r": round(float(np.mean(dev)), 3) if dev else None},
        "val_2025_2026": {"n": len(val),
                          "exp_r": round(float(np.mean(val)), 3) if val else None},
    }
    return out


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

    results = {"variant": "CAP_HARAMI", "tp1_r_mult": TP1_R_MULT,
               "lookback": LOOKBACK, "gate": "README.md", "variants": []}

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
        base_pooled.append(pb.summarize("CAP:BASE:4h", base_trades, port,
                                        base_skipped, cost_name))
    results["variants"].append({
        "name": "BASE", "trades": len(base_trades),
        "pooled": base_pooled,
        "per_ticker": [per_ticker_stats(s, base_per.get(s, [])) for s in used],
        "splits_25bps": split_stats(base_trades, pb.COSTS["25bps"])
        if "25bps" in pb.COSTS else split_stats(base_trades,
                                                list(pb.COSTS.values())[0]),
    })
    for p in base_pooled:
        print(f"BASE [{p['cost']}]: n={p['trades']} win={p['win_rate_pct']}% "
              f"exp={p['expectancy_net_r']}R PF={p['profit_factor']} "
              f"maxDD={p.get('max_drawdown_pct', '?')}%", flush=True)

    # CAP_HARAMI variant
    all_trades, per_sym, agg = [], {}, {
        "capitulation_signals": 0, "haramis": 0, "triggers": 0,
        "expired": 0, "trades": 0, "skipped_gap": 0}
    for sym in used:
        tr, st = gen_cap_harami_trades(sym, data[sym])
        per_sym[sym] = tr
        all_trades.extend(tr)
        for k in agg:
            agg[k] += st[k]
    all_trades.sort(key=lambda t: t["entry_time"])
    var_pooled = []
    cost_keys = [k for k, _ in COSTS_ALL]
    var_cost_map = dict(COSTS_ALL)
    for cost_name, cost in COSTS_ALL:
        port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
        var_pooled.append(pb.summarize("CAP:CAP_HARAMI:4h", all_trades, port,
                                       agg["skipped_gap"], cost_name))
    results["variants"].append({
        "name": "CAP_HARAMI", "trades": len(all_trades),
        "attribution": dict(agg),
        "pooled": var_pooled,
        "per_ticker": [per_ticker_stats(s, per_sym.get(s, [])) for s in used],
        "splits_25bps": split_stats(all_trades, var_cost_map["25bps"]),
        "splits_50bps": split_stats(all_trades, var_cost_map["50bps"]),
    })
    for p in var_pooled:
        print(f"CAP_HARAMI [{p['cost']}]: n={p['trades']} "
              f"win={p['win_rate_pct']}% exp={p['expectancy_net_r']}R "
              f"PF={p['profit_factor']} maxDD={p.get('max_drawdown_pct', '?')}% "
              f"| cap={agg['capitulation_signals']} harami={agg['haramis']} "
              f"trig={agg['triggers']} expired={agg['expired']}", flush=True)

    with open(OUT, "w") as f:
        json.dump(results, f, indent=1)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
