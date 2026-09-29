"""Canonical baseline ablation ladder (worker d): V0 -> V5.

V0 : exact old system (pine_backtest.gen_pine_trades imported UNMODIFIED:
     V3.6 Hybrid entries, pine levels, pine-style management) + 25bps once
     + independent + 14-name overlay. Sanity anchor vs +0.2388R.
V1 : V0 on the PIT 131-universe (gen_pine_trades, window-filtered) -> UNIVERSE.
V2 : V1 entries (V3.6 Hybrid) + Mode B exits (live-faithful) + 25bps once
     + independent -> MODE B.
V3 : v54 entries (strict PIT contract) + Mode B + 25bps once + independent
     -> PIT / entry-definition.
V4 : V3 + round-trip leg-based costs @25/50/75/100 -> COSTS.
V5 : V4@50bps + full portfolio ($75k, 1% risk, max 6 open, 5% heat,
     rs_top2 slot competition) -> PORTFOLIO. Headline.

Writes: v0_trades.json, v1_trades.json, v2_trades.json, v3_trades.json,
        canonical_trades.json (V5), portfolio_results.json
"""

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import simlib
from simlib import m53, sr
import modeb_engine
import pine_backtest as pb  # frozen, read-only (V0/V1 only)

BASE = simlib.BASE
OUT = BASE

COST_ONCE = 0.0025
RISK_USD = 750.0
START_EQUITY = 75000.0
MAX_OPEN = 6
HEAT_CAP = 0.05


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def save_json(name, obj):
    with open(os.path.join(OUT, name), "w") as fh:
        json.dump(obj, fh, indent=1, default=str)
    print(f"wrote {name}", flush=True)


def net_r_once(blended_r, risk_frac, bps=0.0025):
    return float(blended_r - bps / risk_frac) if risk_frac > 0 else 0.0


def shares_for(entry, stop):
    risk = entry - stop
    if risk <= 0:
        return 0
    return int(RISK_USD // risk)


def leg_cost_usd(trade, bps_roundtrip):
    """Round-trip friction: (bps/2) x sum of leg notionals.

    Legs: entry (full shares) + exits. TP1 partial = leg on half size,
    runner exit = leg on half size; full-position exit = full-size leg.
    A standard round trip = 2 leg-equivalents, so cost ~= bps x notional.
    """
    sh = trade["shares"]
    legs = sh * trade["entry"]
    if trade["tp1_taken"]:
        legs += 0.5 * sh * trade["tp1_fill_px"]
        legs += 0.5 * sh * trade["exit_px"]
    else:
        legs += sh * trade["exit_px"]
    return float((bps_roundtrip / 2.0) * legs)


def net_r_legs(trade, bps_roundtrip):
    risk_usd = trade["shares"] * (trade["entry"] - trade["stop"])
    if risk_usd <= 0:
        return 0.0
    return float(trade["blended_r"] - leg_cost_usd(trade, bps_roundtrip) / risk_usd)


def exec_modeb(sym, df, xs, sig, realistic_gaps=False):
    res = modeb_engine.run_trade(
        sig["entry_bar_idx"], sig["entry"], sig["stop"], sig["tp1"],
        df, scanner_states=xs, realistic_gaps=realistic_gaps)
    idx = df.index
    n = len(df)
    if res.exit_bar is None:
        # OPEN at sample end (live never hits this): mark at the last close
        # so the P&L is counted; flagged via open_at_end.
        last_close = float(df["Close"].iloc[-1])
        risk = sig["entry"] - sig["stop"]
        r_exit = (last_close - sig["entry"]) / risk if risk > 0 else 0.0
        if res.tp1_taken and res.tp1_fill_px is not None:
            r_tp1 = (res.tp1_fill_px - sig["entry"]) / risk if risk > 0 else 0.0
            blended = 0.5 * r_tp1 + 0.5 * r_exit
        else:
            blended = r_exit
        exit_idx, exit_ts = n - 1, idx[-1].isoformat()
        open_at_end = True
        res_blended = round(float(blended), 4)
        res_exit_px = last_close
    else:
        exit_idx = int(idx.get_loc(res.exit_bar))
        exit_ts = idx[exit_idx].isoformat()
        open_at_end = False
        res_blended = res.blended_r
        res_exit_px = res.exit_px
    rec = {
        "symbol": sym,
        "signal_id": sig["signal_id"],
        "signal_bar_idx": sig["signal_bar_idx"],
        "signal_bar_close_at": sig["signal_bar_close_at"],
        "entry_bar_idx": int(sig["entry_bar_idx"]),
        "entry_ts": idx[int(sig["entry_bar_idx"])].isoformat(),
        "entry": float(sig["entry"]),
        "stop": float(sig["stop"]),
        "tp1": float(sig["tp1"]),
        "exit_bar_idx": exit_idx,
        "exit_ts": exit_ts,
        "exit_reason": res.exit_reason,
        "open_at_end": open_at_end,
        "live_reason": res.live_reason,
        "blended_r": res_blended,
        "partial_r": res.partial_r,
        "runner_r": res.runner_r,
        "mfe_r": res.mfe_r,
        "mae_r": res.mae_r,
        "bars_held": res.bars_held,
        "tp1_taken": bool(res.tp1_taken),
        "pp_armed": bool(res.pp_armed),
        "exit_px": res_exit_px,
        "tp1_fill_px": res.tp1_fill_px,
        "tp1_fill_bar": (res.tp1_fill_bar.isoformat()
                         if res.tp1_fill_bar is not None else None),
        "tp1_fill_ts": (res.tp1_fill_bar.isoformat()
                        if res.tp1_fill_bar is not None else None),
        "risk_frac": float((sig["entry"] - sig["stop"]) / sig["entry"]),
        "realistic_gaps": bool(realistic_gaps),
    }
    rec["shares"] = shares_for(rec["entry"], rec["stop"])
    return rec


def summarize(name, rs):
    rs = np.asarray(rs, dtype=float)
    n = len(rs)
    return {
        "variant": name,
        "n": int(n),
        "expectancy_r": round(float(np.mean(rs)), 4) if n else 0.0,
        "win_rate_pct": round(float((rs > 0).mean() * 100), 1) if n else 0.0,
        "profit_factor": (round(float(rs[rs > 0].sum() / -rs[rs <= 0].sum()), 2)
                          if n and (rs <= 0).any() and (rs > 0).any() else None),
        "total_r": round(float(rs.sum()), 2),
        "median_r": round(float(np.median(rs)), 4) if n else 0.0,
    }


# --------------------------------------------------------------------------
# universe / windows
# --------------------------------------------------------------------------

def build_symbol_table(symbols):
    uni = {u["symbol"]: u for u in simlib.load_universe()}
    cov = simlib.load_coverage()
    tab = {}
    for s in symbols:
        u = uni.get(s, {"eligible_from": "2023-10-01",
                        "eligible_to": "2026-09-30"})
        c = cov.get(s, {"effective_4h_from": "2023-10-26"})
        tab[s] = simlib.signal_window(s, u, c)
    return tab


OVERLAY14 = [x["symbol"] for x in simlib.load_overlay14()]
UNI131 = [u["symbol"] for u in simlib.load_universe()]
TAB14 = build_symbol_table(OVERLAY14)
TAB131 = build_symbol_table(UNI131)

print(f"V0/V1 symbols: {len(OVERLAY14)} / {len(UNI131)}", flush=True)


# --------------------------------------------------------------------------
# V0: exact old system on the 14 overlay (sanity anchor)
# --------------------------------------------------------------------------

def run_v0():
    all_trades = []
    for sym in OVERLAY14:
        df = simlib.load_h4(sym)
        d = pb.add_pine_indicators(df)
        tr, skipped = pb.gen_pine_trades(sym, d)
        for t in tr:
            rf = (t["entry"] - t["stop"]) / t["entry"]
            t["net_r_25bps_once"] = net_r_once(
                (t["exit"] - t["entry"]) / t["entry"] / rf, rf)
        all_trades.extend(tr)
        print(f"  V0 {sym}: {len(tr)}", flush=True)
    rs = [t["net_r_25bps_once"] for t in all_trades]
    save_json("v0_trades.json", all_trades)
    return summarize("V0 old-system 14-name", rs), all_trades


# --------------------------------------------------------------------------
# V1: old system on the PIT 131-universe (window-filtered)
# --------------------------------------------------------------------------

def run_v1():
    all_trades = []
    for sym in UNI131:
        ws, we = TAB131[sym]
        df = simlib.load_h4(sym)
        d = pb.add_pine_indicators(df)
        tr, _ = pb.gen_pine_trades(sym, d)
        kept = []
        for t in tr:
            st = pd.Timestamp(t["signal_time"])
            if not (ws <= st <= we):
                continue
            rf = (t["entry"] - t["stop"]) / t["entry"]
            t["net_r_25bps_once"] = net_r_once(
                (t["exit"] - t["entry"]) / t["entry"] / rf, rf)
            kept.append(t)
        all_trades.extend(kept)
        if kept:
            print(f"  V1 {sym}: {len(kept)}", flush=True)
    rs = [t["net_r_25bps_once"] for t in all_trades]
    save_json("v1_trades.json", all_trades)
    return summarize("V1 old-system 131-name", rs), all_trades


# --------------------------------------------------------------------------
# V2: V3.6 entries + Mode B exits, independent
# --------------------------------------------------------------------------

def v36_sigs_windowed(sym, ws, we):
    mask, d = simlib.v36_signal_mask(sym)
    df = simlib.load_h4(sym)
    idx = df.index
    atr = d["atr"].to_numpy()
    sigs = []
    for i in np.flatnonzero(mask):
        ts = idx[i]
        if not (ws <= ts <= we) or i >= len(df) - 1:
            continue
        entry = float(df["Open"].iloc[i + 1])
        stop = float(d["Close"].iloc[i] - atr[i] * pb.SL_ATR)
        if entry <= stop:
            continue
        tp1 = entry + float(atr[i]) * pb.TP_ATR
        sigs.append({
            "signal_id": f"v36:{sym}:4h:{sr.bar_close_at(ts, sym).isoformat()}",
            "symbol": sym,
            "signal_bar_idx": int(i),
            "signal_bar_close_at": sr.bar_close_at(ts, sym).isoformat(),
            "entry_bar_idx": int(i + 1),
            "entry": entry, "stop": stop, "tp1": tp1,
        })
    return sigs


def walk_independent(sym, sigs, realistic_gaps=False):
    """Chronological walk, one position per symbol (live _busy rule).

    Skip signal at bar c iff c <= busy_through (exit bar of prior trade).
    """
    df = simlib.load_h4(sym)
    xs = simlib.exit_states_vector(sym)
    sigs = sorted(sigs, key=lambda s: s["signal_bar_idx"])
    trades = []
    busy_through = -1
    n = len(df)
    for s in sigs:
        if s["signal_bar_idx"] <= busy_through:
            continue
        rec = exec_modeb(sym, df, xs, s, realistic_gaps=realistic_gaps)
        trades.append(rec)
        busy_through = (rec["exit_bar_idx"] if rec["exit_bar_idx"] is not None
                        else n - 1)
    return trades


def run_v2(realistic_gaps=False):
    all_trades = []
    for sym in UNI131:
        ws, we = TAB131[sym]
        sigs = v36_sigs_windowed(sym, ws, we)
        tr = walk_independent(sym, sigs, realistic_gaps=realistic_gaps)
        for t in tr:
            t["net_r_25bps_once"] = net_r_once(t["blended_r"], t["risk_frac"])
        all_trades.extend(tr)
        if tr:
            print(f"  V2{'-rg' if realistic_gaps else ''} {sym}: {len(tr)}",
                  flush=True)
    rs = [t["net_r_25bps_once"] for t in all_trades]
    tag = "V2 ModeB 131-name" + (" realistic-gaps" if realistic_gaps else "")
    return summarize(tag, rs), all_trades


# --------------------------------------------------------------------------
# V3: v54 entries + Mode B exits, independent
# --------------------------------------------------------------------------

def run_v3(realistic_gaps=False):
    all_trades = []
    for sym in UNI131:
        ws, we = TAB131[sym]
        sigs, _ = simlib.v54_signals(sym, ws, we)
        tr = walk_independent(sym, sigs, realistic_gaps=realistic_gaps)
        for t in tr:
            t["net_r_25bps_once"] = net_r_once(t["blended_r"], t["risk_frac"])
        all_trades.extend(tr)
        if tr:
            print(f"  V3{'-rg' if realistic_gaps else ''} {sym}: {len(tr)}",
                  flush=True)
    rs = [t["net_r_25bps_once"] for t in all_trades]
    tag = "V3 v54+ModeB 131-name" + (" realistic-gaps" if realistic_gaps else "")
    return summarize(tag, rs), all_trades


if __name__ == "__main__":
    results = {}
    v0sum, v0tr = run_v0()
    results["V0"] = v0sum
    print("V0:", v0sum, flush=True)
    v1sum, v1tr = run_v1()
    results["V1"] = v1sum
    print("V1:", v1sum, flush=True)
    v2sum, v2tr = run_v2()
    results["V2"] = v2sum
    print("V2:", v2sum, flush=True)
    v2rgsum, v2rgtr = run_v2(realistic_gaps=True)
    results["V2 realistic-gaps"] = v2rgsum
    print("V2-rg:", v2rgsum, flush=True)
    v3sum, v3tr = run_v3()
    results["V3"] = v3sum
    print("V3:", v3sum, flush=True)
    save_json("v2_trades.json", v2tr)
    save_json("v3_trades.json", v3tr)
    save_json("ablation_V0_V3.json", results)
