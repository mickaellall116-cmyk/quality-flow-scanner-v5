"""Stale-FVG invalidation backtest: does the FVG entry edge live only in fresh gaps?

Idea (pre-registered 2026-09-25): the 4H FVG-as-entry toggle fires whenever
price sits in a bull fair-value gap, no matter how old. The Pine port keeps
lastBullFvgLow/High persisting until the NEXT bull FVG forms, so a gap printed
weeks ago counts the same as yesterday's. Test: take FVG-entry signals only
when the gap formed within the last 10 bars; ignore signals leaning on stale
gaps. Pre-registered cutoff K=10 -- no tuning across K (K=5 and K=20 reported
as secondary context only, not decision criteria).

- BASE: all-off canonical Hybrid, rerun in-study (never reuse old numbers).
- FVG-ALL: canonical OR fvg sub-signal (current sidecar behavior, rerun).
- FVG-FRESH: canonical OR (fvg sub-signal AND fvg_age <= 10 bars).

pine_backtest.py is imported UNMODIFIED. Only pb.pine_buy_signal is
monkey-patched per variant (same pattern as pine_entry_timing_backtest).
The FVG port is copied from pine_entry_timing_backtest/run_entry_timing.py
with one added field: fvg_age (bars since the currently-active lastBullFvg
formed; NaN when no FVG is active). Research-port change only; nothing frozen
is touched. Costs, portfolio sim, exits (frozen Mode B via gen_pine_trades)
untouched. Local-only research.

Success gate: FVG-FRESH beats FVG-ALL by >0.02R at 25bps AND clears +0.15R.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_stalefvg_backtest")
sys.path.insert(0, BASE)
import pine_backtest as pb

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "stalefvg_results.json")
os.makedirs(OUTDIR, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

K_FRESH = 10  # pre-registered age cutoff (bars)

_orig_signal = pb.pine_buy_signal


def add_fvg_columns(df):
    """FVG state machine ported from Quality-Flow-System-V3.7.pine, plus
    fvg_age: bars since the currently-active lastBullFvg formed (NaN if none
    active). Identical activation semantics to the entry-timing port."""
    out = df.copy()
    n = len(out)
    low = out["Low"].to_numpy()
    high = out["High"].to_numpy()
    close = out["Close"].to_numpy()
    e21 = out["e21"].to_numpy()
    atr = out["atr"].to_numpy()

    last_lo, last_hi = np.nan, np.nan
    form_bar = -1
    in_fvg = np.zeros(n, dtype=bool)
    age = np.full(n, np.nan)
    for i in range(n):
        if i >= 2 and low[i] > high[i - 2]:
            last_lo, last_hi = high[i - 2], low[i]
            form_bar = i
        c, a = close[i], atr[i]
        if np.isnan(a):
            continue
        if not np.isnan(last_lo):
            in_fvg[i] = bool(low[i] <= last_hi and c >= last_lo)
            age[i] = i - form_bar
    out["inBullFvgSupport"] = in_fvg
    out["fvgAge"] = age
    return out


def fvg_sub(df, i):
    """The Pine FVG sub-signal + formation age at bar i.

    Returns (fired, age_bars). age_bars is NaN when the sub-signal did not
    fire (or no gap active).
    """
    r = df.iloc[i]
    if pd.isna(r["e200"]) or pd.isna(r["atr_base"]) or pd.isna(r["adx"]):
        return False, np.nan
    close, vol = r["Close"], r["Volume"]
    volume_ok = vol > r["vol_ma"]
    safe = not (close > r["e9"] + r["atr"] * pb.HOT_ATR)
    trend_bull = r["e21"] > r["e55"] and close > r["e200"]
    fired = bool(trend_bull and r["inBullFvgSupport"] and close > r["e21"]
                 and volume_ok and safe)
    age = float(r["fvgAge"]) if fired else np.nan
    return fired, age


def make_signal(mode, k=K_FRESH):
    """mode in {"base", "all", "fresh"}; fresh uses age <= k."""
    assert mode in ("base", "all", "fresh")

    def sig(df, i):
        base = _orig_signal(df, i)
        if mode == "base":
            return base
        fired, age = fvg_sub(df, i)
        if mode == "all":
            return bool(base or fired)
        return bool(base or (fired and not np.isnan(age) and age <= k))

    return sig


def per_ticker_stats(sym, trades):
    out = {"symbol": sym, "trades": len(trades)}
    if not trades:
        return out
    t = pd.DataFrame(trades)
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
        }
    return out


def bucket_stats(trades, cost=0.0025):
    """n, win%, expectancy for a list of trades at given cost."""
    if not trades:
        return {"n": 0}
    rs = [pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]
          for tr in trades]
    s = pd.Series(rs)
    gw = float(s[s > 0].sum())
    gl = float(-s[s <= 0].sum())
    return {
        "n": len(trades),
        "win_rate_pct": round(float((s > 0).mean()) * 100, 1),
        "expectancy_net_r": round(float(s.mean()), 3),
        "profit_factor": round(gw / gl, 2) if gl > 0 else None,
    }


def attribute_trades(data, sig_index, trades):
    """Split trades by FVG sub-signal state at their signal bar.

    Returns dict with per-trade annotations:
      fvg_fired (bool), fvg_age (float/None), canonical (bool),
      marginal (fvg fired and not canonical).
    """
    out = []
    for tr in trades:
        sym = tr["symbol"]
        i = sig_index[sym].get(tr["signal_time"])
        if i is None:
            out.append({"marginal": False, "fvg_fired": False,
                        "fvg_age": None, "canonical": None})
            continue
        df = data[sym]
        fired, age = fvg_sub(df, i)
        canon = _orig_signal(df, i)
        out.append({
            "marginal": bool(fired and not canon),
            "fvg_fired": bool(fired),
            "fvg_age": None if np.isnan(age) else float(age),
            "canonical": bool(canon),
        })
    return out


def main():
    data, closes, sig_index = {}, {}, {}
    dropped = []
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        if "Volume" not in df.columns or df["Volume"].isna().all():
            dropped.append(sym)
            continue
        df = pb.add_pine_indicators(df)
        df = add_fvg_columns(df)
        data[sym] = df
        closes[sym] = df["Close"]
        sig_index[sym] = {df.index[i].isoformat(): i for i in range(len(df))}
    used = [s for s in WATCHLIST if s in data]
    print(f"loaded {len(used)} tickers; dropped: {dropped}", flush=True)

    results = {"variants": [], "k_fresh": K_FRESH,
               "deployment_gate_r": 0.15, "success_margin_r": 0.02}

    variants = [("BASE", "base", None),
                ("FVG-ALL", "all", None),
                ("FVG-FRESH", "fresh", K_FRESH),
                ("FVG-FRESH5", "fresh", 5),    # secondary context only
                ("FVG-FRESH20", "fresh", 20)]  # secondary context only

    per_sym_trades = {}
    for name, mode, k in variants:
        pb.pine_buy_signal = make_signal(mode) if k is None \
            else make_signal(mode, k)
        all_trades, skipped = [], 0
        per_sym = {}
        for sym in used:
            tr, sg = pb.gen_pine_trades(sym, data[sym])
            per_sym[sym] = tr
            all_trades.extend(tr)
            skipped += sg
        all_trades.sort(key=lambda t: t["entry_time"])
        per_sym_trades[name] = (per_sym, all_trades)
        pooled = []
        for cost_name, cost in pb.COSTS.items():
            port = pb.simulate_portfolio(all_trades, closes, cost,
                                         pb.RISK_PCT)
            pooled.append(pb.summarize(f"STALEFVG:{name}:4h", all_trades,
                                       port, skipped, cost_name))
        rec = {"name": name, "mode": mode, "k": k,
               "trades": len(all_trades), "skipped_gap": skipped,
               "pooled": pooled,
               "per_ticker": [per_ticker_stats(s, per_sym.get(s, []))
                              for s in used]}
        results["variants"].append(rec)
        for p in pooled:
            print(f"{name} [{p['cost']}]: n={p['trades']} "
                  f"win={p['win_rate_pct']}% exp={p['expectancy_net_r']}R "
                  f"PF={p['profit_factor']} maxDD={p.get('max_drawdown_pct', '?')}%",
                  flush=True)
    pb.pine_buy_signal = _orig_signal  # restore

    # ---- attribution on FVG-ALL trades -----------------------------------
    _, fvg_all_trades = per_sym_trades["FVG-ALL"]
    ann = attribute_trades(data, sig_index, fvg_all_trades)
    for tr, a in zip(fvg_all_trades, ann):
        tr["_ann"] = a

    fvg_trades = [t for t in fvg_all_trades if t["_ann"]["fvg_fired"]]
    marginal = [t for t in fvg_all_trades if t["_ann"]["marginal"]]
    fresh = [t for t in fvg_trades if t["_ann"]["fvg_age"] is not None
             and t["_ann"]["fvg_age"] <= K_FRESH]
    stale = [t for t in fvg_trades if t["_ann"]["fvg_age"] is not None
             and t["_ann"]["fvg_age"] > K_FRESH]
    fresh_marg = [t for t in marginal if t["_ann"]["fvg_age"] is not None
                  and t["_ann"]["fvg_age"] <= K_FRESH]
    stale_marg = [t for t in marginal if t["_ann"]["fvg_age"] is not None
                  and t["_ann"]["fvg_age"] > K_FRESH]
    unmapped = sum(1 for t in fvg_all_trades
                   if t["_ann"]["canonical"] is None)

    age_buckets = {"0-10": [], "11-20": [], "21-40": [], "41+": []}
    for t in fvg_trades:
        a = t["_ann"]["fvg_age"]
        if a is None:
            continue
        if a <= 10:
            age_buckets["0-10"].append(t)
        elif a <= 20:
            age_buckets["11-20"].append(t)
        elif a <= 40:
            age_buckets["21-40"].append(t)
        else:
            age_buckets["41+"].append(t)

    results["attribution"] = {
        "fvg_all_trades": len(fvg_all_trades),
        "fvg_entry_trades": bucket_stats(fvg_trades),
        "marginal_trades": bucket_stats(marginal),
        "fresh_le10": bucket_stats(fresh),
        "stale_gt10": bucket_stats(stale),
        "marginal_fresh": bucket_stats(fresh_marg),
        "marginal_stale": bucket_stats(stale_marg),
        "marginal_share_fresh_pct": round(
            len(fresh_marg) / len(marginal) * 100, 1) if marginal else None,
        "age_buckets_25bps": {k: bucket_stats(v)
                              for k, v in age_buckets.items()},
        "unmapped_signal_bars": unmapped,
    }

    # strip helper annotations before writing
    for _, (_, trades) in per_sym_trades.items():
        for t in trades:
            t.pop("_ann", None)

    with open(OUT, "w") as f:
        json.dump(results, f, indent=1)
    print(f"wrote {OUT}")

    a = results["attribution"]
    print("\n-- attribution (25bps) --")
    print(f"FVG-entry trades: n={a['fvg_entry_trades']['n']} "
          f"win={a['fvg_entry_trades'].get('win_rate_pct')}% "
          f"exp={a['fvg_entry_trades'].get('expectancy_net_r')}R")
    print(f"Marginal (fvg-only): n={a['marginal_trades']['n']} "
          f"win={a['marginal_trades'].get('win_rate_pct')}% "
          f"exp={a['marginal_trades'].get('expectancy_net_r')}R "
          f"| fresh share={a['marginal_share_fresh_pct']}%")
    print(f"Fresh<=10: n={a['fresh_le10']['n']} exp={a['fresh_le10'].get('expectancy_net_r')}R | "
          f"Stale>10: n={a['stale_gt10']['n']} exp={a['stale_gt10'].get('expectancy_net_r')}R")
    for k, b in a["age_buckets_25bps"].items():
        print(f"  age {k}: n={b['n']} win={b.get('win_rate_pct')}% "
              f"exp={b.get('expectancy_net_r')}R")


if __name__ == "__main__":
    main()
