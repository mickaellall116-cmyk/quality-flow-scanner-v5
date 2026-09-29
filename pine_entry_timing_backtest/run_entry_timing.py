"""V3.7 entry-timing toggle backtest: 8 combos of Pullback/FVG/Sweep as real entry.

Semantics ported 1:1 from Quality-Flow-System-V3.7.pine (lines 200-207):
each toggle adds an EXTRA buy signal OR'd into the Hybrid buySignal.
No priority order (pure OR). Entry mechanics and exits are identical for
extra signals — only which bars fire changes.

pine_backtest.py is imported UNMODIFIED; only pb.pine_buy_signal is
monkey-patched per combo (canonical OR extraEntry), same pattern as
pine_sensitivity/run_liveconfig.py.

Local-only research. No frozen files modified.
"""
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_entry_timing_backtest")
sys.path.insert(0, BASE)
import pine_backtest as pb

CACHE = os.path.join(OUTDIR, "cache")
OUT = os.path.join(OUTDIR, "entry_timing_results.json")

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

SWEEP_LB = 20          # Liquidity Sweep Lookback
BZ_W = 0.35            # Buy Zone ATR Width
NEAR_ATR = 0.50        # Near Buy Zone ATR

_orig_signal = pb.pine_buy_signal


def add_entry_timing_columns(df):
    """Port of the Pine smart-money geometry feeding the three sub-signals."""
    out = df.copy()
    n = len(out)
    low = out["Low"].to_numpy()
    high = out["High"].to_numpy()
    close = out["Close"].to_numpy()
    e21 = out["e21"].to_numpy()
    atr = out["atr"].to_numpy()

    # bullSweep = low < lowest(low,20)[1] and close > lowest(low,20)[1]
    sweep_ref = out["Low"].rolling(SWEEP_LB).min().shift(1).to_numpy()
    out["bullSweep"] = (low < sweep_ref) & (close > sweep_ref)

    # FVG state machine: bullFVG = low > high[2]; vars persist until next FVG
    last_lo, last_hi = np.nan, np.nan
    in_fvg = np.zeros(n, dtype=bool)
    use_fvg = np.zeros(n, dtype=bool)
    near = np.zeros(n, dtype=bool)
    for i in range(n):
        if i >= 2 and low[i] > high[i - 2]:
            last_lo, last_hi = high[i - 2], low[i]
        c, a, e = close[i], atr[i], e21[i]
        if np.isnan(a) or np.isnan(e):
            continue
        uf = (not np.isnan(last_lo)
              and abs(c - last_hi) <= a * 3
              and last_hi <= c * 1.08)
        use_fvg[i] = uf
        ez_lo, ez_hi = e - a * BZ_W, e + a * BZ_W
        zlo = min(ez_lo, last_lo) if uf else ez_lo
        zhi = max(ez_hi, last_hi) if uf else ez_hi
        in_zone = zlo <= c <= zhi
        near[i] = (abs(c - zhi) <= a * NEAR_ATR
                   or abs(c - zlo) <= a * NEAR_ATR
                   or in_zone)
        if not np.isnan(last_lo):
            in_fvg[i] = bool(low[i] <= last_hi and c >= last_lo)
    out["inBullFvgSupport"] = in_fvg
    out["nearBuyZone"] = near
    return out


def sub_signals(df, i):
    """The three Pine sub-signals (before toggle gating). Returns dict."""
    r = df.iloc[i]
    if pd.isna(r["e200"]) or pd.isna(r["atr_base"]) or pd.isna(r["adx"]):
        return {"pullback": False, "fvg": False, "sweep": False}
    close, vol = r["Close"], r["Volume"]
    volume_ok = vol > r["vol_ma"]
    safe = not (close > r["e9"] + r["atr"] * pb.HOT_ATR)
    trend_bull = r["e21"] > r["e55"] and close > r["e200"]
    return {
        "pullback": bool(trend_bull and r["nearBuyZone"] and close >= r["e21"]
                         and r["adx"] > 18 and volume_ok and safe),
        "fvg": bool(trend_bull and r["inBullFvgSupport"] and close > r["e21"]
                    and volume_ok and safe),
        "sweep": bool(trend_bull and r["bullSweep"] and close > r["e21"]
                      and volume_ok and safe),
    }


def make_combo_signal(use_pb, use_fvg, use_sw):
    def sig(df, i):
        base = _orig_signal(df, i)
        if not (use_pb or use_fvg or use_sw):
            return base
        ss = sub_signals(df, i)
        extra = ((use_pb and ss["pullback"])
                 or (use_fvg and ss["fvg"])
                 or (use_sw and ss["sweep"]))
        return bool(base or extra)
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


def main():
    # ---- load data once -------------------------------------------------
    data, closes = {}, {}
    dropped = []
    for sym in WATCHLIST:
        path = os.path.join(CACHE, f"h4_{sym}.pkl")
        df = pd.read_pickle(path)
        if "Volume" not in df.columns or df["Volume"].isna().all():
            dropped.append(sym)
            continue
        df = pb.add_pine_indicators(df)
        df = add_entry_timing_columns(df)
        data[sym] = df
        closes[sym] = df["Close"]
    used = [s for s in WATCHLIST if s in data]
    print(f"loaded {len(used)} tickers; dropped: {dropped}", flush=True)

    # ---- signal-bar sets for attribution ---------------------------------
    # canonical bars + per-toggle sub-signal bars (evaluated WARMUP..n-1,
    # the same range gen_pine_trades scans)
    sig_sets = {}
    for sym in used:
        df = data[sym]
        canon, sub = set(), {"pullback": set(), "fvg": set(), "sweep": set()}
        for i in range(pb.WARMUP, len(df) - 1):
            if _orig_signal(df, i):
                canon.add(df.index[i])
            for k, v in sub_signals(df, i).items():
                if v:
                    sub[k].add(df.index[i])
        sig_sets[sym] = {"canonical": canon, "sub": sub}

    combos = list(itertools.product([False, True], repeat=3))  # (pb, fvg, sw)
    results = {"combos": [], "toggle_marginals": {}}

    # marginal signal counts per toggle (sub-signal fired, canonical did not)
    for k in ("pullback", "fvg", "sweep"):
        marg = sum(len(sig_sets[s]["sub"][k] - sig_sets[s]["canonical"]) for s in used)
        tot = sum(len(sig_sets[s]["sub"][k]) for s in used)
        results["toggle_marginals"][k] = {
            "sub_signal_bars": tot,
            "marginal_bars_not_canonical": marg,
        }

    for use_pb, use_fvg, use_sw in combos:
        name = ("PB" if use_pb else "") + ("FVG" if use_fvg else "") \
            + ("SW" if use_sw else "") or "BASE(all-off)"
        pb.pine_buy_signal = make_combo_signal(use_pb, use_fvg, use_sw)

        all_trades, skipped = [], 0
        per_sym_trades = {}
        for sym in used:
            tr, sg = pb.gen_pine_trades(sym, data[sym])
            per_sym_trades[sym] = tr
            all_trades.extend(tr)
            skipped += sg
        all_trades.sort(key=lambda t: t["entry_time"])

        # attribution: trades whose signal bar was NOT a canonical signal bar
        added = 0
        for tr in all_trades:
            st = pd.Timestamp(tr["signal_time"])
            if st.tzinfo is None:
                st = st.tz_localize("America/New_York")
            if st not in sig_sets[tr["symbol"]]["canonical"]:
                added += 1

        pooled = []
        for cost_name, cost in pb.COSTS.items():
            port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
            pooled.append(pb.summarize(f"ENTRY_TIMING:{name}:4h",
                                      all_trades, port, skipped, cost_name))
        per_ticker = [per_ticker_stats(s, per_sym_trades.get(s, [])) for s in used]
        rec = {"combo": {"pullback": use_pb, "fvg": use_fvg, "sweep": use_sw},
               "name": name,
               "trades": len(all_trades),
               "trades_added_by_toggles": added,
               "skipped_gap": skipped,
               "pooled": pooled,
               "per_ticker": per_ticker}
        results["combos"].append(rec)
        for p in pooled:
            print(f"{name} [{p['cost']}]: n={p['trades']} "
                  f"(+{added} by toggles) win={p['win_rate_pct']}% "
                  f"exp={p['expectancy_net_r']}R PF={p['profit_factor']}",
                  flush=True)

    pb.pine_buy_signal = _orig_signal  # restore
    with open(OUT, "w") as f:
        json.dump(results, f, indent=1)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
