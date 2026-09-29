"""MFE/MAE DIAGNOSTIC on Pine V3.6 baseline trades.

Diagnostic only: V3.6 entries/exits byte-identical to pine_backtest.py.
The trade-generation loop is copied here (not modified in the original) with
one addition: each trade records entry_idx and exit_trigger_idx so MFE/MAE
can be measured bar-by-bar from 4H high/low.

Spec: MFE_MAE_SPEC.md (frozen before analysis).
Local-only. No existing files modified.
"""

import glob
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # repo root: pine_backtest
import pine_backtest as pb

CACHE = os.path.join(os.path.dirname(HERE), "backtest_cache", "v3")
CACHE_2022_OLD = os.path.join(os.path.dirname(HERE), "v6_short_v2", "cache")
CACHE_2022_NEW = os.path.join(HERE, "..", "pine_exit_fix", "cache_2022")
CACHE_2022_NEW = os.path.normpath(os.path.join(HERE, CACHE_2022_NEW))
CUTOFF_2022 = pd.Timestamp("2022-01-01", tz="UTC")


def gen_trades_lifecycle(sym, df, cutoff=None, eod_liquidate=False):
    """Copy of pb.gen_pine_trades + entry/exit-trigger bar indices.

    cutoff: if given, only signals with signal bar time >= cutoff are taken
            (2022 framework). eod_liquidate: liquidate open position at last
            close (2022 framework); otherwise open-at-EOD trades are dropped,
            exactly like the baseline.
    """
    trades = []
    skipped_gap = 0
    n = len(df)
    i = pb.WARMUP
    in_trade = False
    pos = None
    while i < n - 1:
        if not in_trade:
            sig_ok = pb.pine_buy_signal(df, i)
            if cutoff is not None:
                sig_ok = sig_ok and df.index[i] >= CUTOFF_2022
            if sig_ok:
                sig = df.iloc[i]
                entry = float(df["Open"].iloc[i + 1])
                stop0 = float(sig["Close"] - sig["atr"] * pb.SL_ATR)
                if entry <= stop0:
                    skipped_gap += 1
                    i += 1
                    continue
                in_trade = True
                pos = {"symbol": sym, "entry": entry, "stop": stop0,
                       "tp1": entry + float(sig["atr"]) * pb.TP_ATR,
                       "tp_hit": False, "runner": stop0,
                       "entry_idx": i + 1,
                       "entry_time": df.index[i + 1],
                       "signal_time": df.index[i].isoformat()}
                i += 1
                continue
            i += 1
            continue
        # manage open position on completed bar i
        bar = df.iloc[i]
        lo, hi, close = float(bar["Low"]), float(bar["High"]), float(bar["Close"])
        if not pos["tp_hit"] and hi >= pos["tp1"]:
            pos["tp_hit"] = True
        if pos["tp_hit"]:
            pos["runner"] = max(pos["runner"], close - float(bar["atr"]) * pb.TRAIL_ATR)
        trend_bear = bar["e21"] < bar["e55"] and close < bar["e200"]
        done = False
        if close < pos["runner"]:
            reason = "stop"
            done = True
        elif close < bar["e55"] or trend_bear:
            reason = "ema55-bear" if trend_bear else "ema55-break"
            done = True
        if done:
            trigger_idx = i
            if i + 1 < n:
                exit_px = float(df["Open"].iloc[i + 1])
                exit_idx, exit_time = i + 1, df.index[i + 1]
            else:
                exit_px, exit_time = close, df.index[i]
                exit_idx = i
            trades.append(finalize_lifecycle(pos, df, exit_px, exit_idx,
                                             exit_time, trigger_idx, reason))
            in_trade = False
        i += 1
    if in_trade and eod_liquidate:
        exit_px = float(df["Close"].iloc[-1])
        trades.append(finalize_lifecycle(pos, df, exit_px, n - 1,
                                         df.index[-1], n - 1, "eod"))
    return trades, skipped_gap


def finalize_lifecycle(pos, df, exit_px, exit_idx, exit_time, trigger_idx, reason):
    risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]
    r1 = ((pos["tp1"] - pos["entry"]) / pos["entry"] / risk_frac
          if pos["tp_hit"] else None)
    r2 = (exit_px - pos["entry"]) / pos["entry"] / risk_frac
    r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
    exit_synth = pos["entry"] * (1 + r_blend * risk_frac)
    # excursion over [entry_idx, trigger_idx] from 4H bar high/low
    seg = df.iloc[pos["entry_idx"]:trigger_idx + 1]
    mfe = float(((seg["High"] - pos["entry"]) / pos["entry"] / risk_frac).max())
    mae = float(((seg["Low"] - pos["entry"]) / pos["entry"] / risk_frac).min())
    return {
        "symbol": pos["symbol"], "entry": pos["entry"], "stop": pos["stop"],
        "exit": exit_synth, "reason": reason, "tp1_hit": pos["tp_hit"],
        "entry_time": pos["entry_time"], "exit_time": exit_time,
        "hold_bars": exit_idx - pos["entry_idx"],
        "signal_time": pos["signal_time"],
        "entry_idx": pos["entry_idx"], "trigger_idx": trigger_idx,
        "mfe_r": mfe, "mae_r": mae,
        "r_gross": float(r_blend),
    }


def exit_bucket(t):
    if t["reason"] == "eod":
        return "eod"
    if t["reason"] == "stop":
        return "stop_after_tp1" if t["tp1_hit"] else "stop_no_tp1"
    return "ema55"


def pct(a, q):
    a = np.asarray(a, dtype=float)
    return {f"p{qv}": round(float(np.percentile(a, qv)), 3) for qv in q}


def dist_summary(vals):
    vals = [float(v) for v in vals]
    if not vals:
        return {"n": 0}
    s = {"n": len(vals), "mean": round(float(np.mean(vals)), 3),
         "median": round(float(np.median(vals)), 3)}
    s.update(pct(vals, [10, 25, 75, 90]))
    s["min"] = round(float(np.min(vals)), 3)
    s["max"] = round(float(np.max(vals)), 3)
    return s


def analyze(trades, label):
    for t in trades:
        _, _, net_r, _ = pb._outcome(t["entry"], t["stop"], t["exit"],
                                     pb.COSTS["4bps"])
        t["net_r"] = float(net_r)
        t["winner"] = bool(net_r > 0)
        t["bucket"] = exit_bucket(t)
    wins = [t for t in trades if t["winner"]]
    loss = [t for t in trades if not t["winner"]]
    stopped = [t for t in trades if t["reason"] == "stop"]

    out = {"label": label, "n": len(trades),
           "n_winners": len(wins), "n_losers": len(loss),
           "n_stopped": len(stopped)}
    # Q1/Q2: winner MFE, giveback, capture
    wmfe = [t["mfe_r"] for t in wins]
    out["winner_mfe"] = dist_summary(wmfe)
    giveback = [t["mfe_r"] - t["r_gross"] for t in wins]
    out["winner_giveback_mfe_minus_realized"] = dist_summary(giveback)
    capture = [t["r_gross"] / t["mfe_r"] for t in wins if t["mfe_r"] > 1e-9]
    out["winner_capture_realized_over_mfe"] = dist_summary(capture)
    # Q3: winner MAE
    wmae = [t["mae_r"] for t in wins]
    out["winner_mae"] = dist_summary(wmae)
    out["winner_mae_touch_neg05r_pct"] = round(
        sum(1 for t in wins if t["mae_r"] <= -0.5) / max(len(wins), 1) * 100, 1)
    out["winner_mae_touch_neg075r_pct"] = round(
        sum(1 for t in wins if t["mae_r"] <= -0.75) / max(len(wins), 1) * 100, 1)
    # Q4: stopped-trade MFE
    smfe = [t["mfe_r"] for t in stopped]
    out["stopped_mfe"] = dist_summary(smfe)
    for lvl in (1.0, 1.5, 2.0):
        out[f"stopped_mfe_reached_{lvl}r_pct"] = round(
            sum(1 for t in stopped if t["mfe_r"] >= lvl) / max(len(stopped), 1) * 100, 1)
    # Q5: winner vs loser distributions
    out["winner_mfe_vs_loser_mfe"] = {
        "winner": dist_summary(wmfe),
        "loser": dist_summary([t["mfe_r"] for t in loss])}
    out["winner_mae_vs_loser_mae"] = {
        "winner": dist_summary(wmae),
        "loser": dist_summary([t["mae_r"] for t in loss])}
    # splits by exit bucket
    out["by_bucket"] = {}
    for b in ("stop_no_tp1", "stop_after_tp1", "ema55", "eod"):
        bt = [t for t in trades if t["bucket"] == b]
        if not bt:
            continue
        out["by_bucket"][b] = {
            "n": len(bt),
            "mfe": dist_summary([t["mfe_r"] for t in bt]),
            "mae": dist_summary([t["mae_r"] for t in bt]),
            "net_r_mean": round(float(np.mean([t["net_r"] for t in bt])), 3),
        }
    return out, trades


def load_bull():
    data = {}
    for sym in pb.UNIVERSE_X:
        p = os.path.join(CACHE, f"h4_{sym}.pkl")
        if not os.path.exists(p):
            print(f"  [warn] no cache for {sym}", flush=True)
            continue
        df = pd.read_pickle(p)
        if "Volume" not in df.columns or df["Volume"].isna().all():
            continue
        data[sym] = pb.add_pine_indicators(df)
    return data


def load_2022():
    paths = {}
    for d in (CACHE_2022_OLD, CACHE_2022_NEW):
        if not os.path.isdir(d):
            continue
        for p in glob.glob(os.path.join(d, "d4h_2022_*.pkl")):
            sym = os.path.basename(p)[len("d4h_2022_"):-len(".pkl")]
            if sym not in pb.UNIVERSE_X:
                continue
            paths[sym] = p
    data = {}
    for sym, p in sorted(paths.items()):
        df = pd.read_pickle(p)
        if "Volume" not in df.columns or df["Volume"].isna().all():
            continue
        data[sym] = pb.add_pine_indicators(df)
    return data, sorted(paths)


def main():
    print("== bull window ==", flush=True)
    data = load_bull()
    trades = []
    for sym, df in sorted(data.items()):
        tr, _ = gen_trades_lifecycle(sym, df)
        trades.extend(tr)
        print(f"  {sym}: {len(tr)}", flush=True)
    trades.sort(key=lambda t: t["entry_time"])
    # fidelity check vs baseline
    net_rs = []
    for t in trades:
        _, _, net_r, _ = pb._outcome(t["entry"], t["stop"], t["exit"],
                                     pb.COSTS["4bps"])
        net_rs.append(net_r)
    exp = float(np.mean(net_rs))
    print(f"FIDELITY: n={len(trades)} exp={exp:.3f}R (baseline: 263, +0.195R)",
          flush=True)
    assert len(trades) == 263, f"trade count mismatch: {len(trades)}"
    assert abs(exp - 0.195) < 0.005, f"expectancy mismatch: {exp}"
    bull_out, bull_trades = analyze(trades, "bull_2024-2026_UX51_4h")
    with open(os.path.join(HERE, "mfe_mae_bull.json"), "w") as f:
        json.dump(bull_out, f, indent=1, default=str)

    print("== 2022 window ==", flush=True)
    data22, syms = load_2022()
    print(f"  {len(syms)} symbols", flush=True)
    trades22 = []
    for sym, df in sorted(data22.items()):
        tr, _ = gen_trades_lifecycle(sym, df, cutoff=CUTOFF_2022,
                                     eod_liquidate=True)
        trades22.extend(tr)
    trades22.sort(key=lambda t: t["entry_time"])
    out22, _ = analyze(trades22, "bear_2022_4h")
    with open(os.path.join(HERE, "mfe_mae_2022.json"), "w") as f:
        json.dump(out22, f, indent=1, default=str)
    print(f"2022: n={len(trades22)}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
