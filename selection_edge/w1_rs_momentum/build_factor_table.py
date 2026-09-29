"""W1 worker: build the per-signal factor table for F1 (RS vs SPY) + F2 (momentum acceleration).

Universe: canonical PIT 131-name universe MINUS any of the 14 masked names present.
    (8 of the 14 are in universe.json -> 123-name working set. The other 6 are
    not in the universe at all, so nothing to mask. NEVER computed on masked names.)

Strict PIT convention (per canonical_baseline/PIT_FEATURES.md + audit fix):
    factor endpoint = last COMPLETED daily bar as of signal-bar close.
    - signal-bar close 13:30 ET (first bar, ~91% of signals): today's daily bar
      is still forming -> endpoint = previous trading day in the d1 series.
    - signal-bar close 16:00 ET (second bar): session complete -> endpoint = signal date.
    Half-days: treated strictly (endpoint = prior trading day) — conservative.

F1: 20-trading-day stock return minus 20-trading-day SPY return. Select RS > 0.
    Variants (robustness): 15d, 25d.
F2: (10-trading-day return) minus (preceding 50-trading-day return). Select > 0.
    Variants (robustness): (20,50), (10,40), (10,60), (20,60).

Then per-symbol walk_independent (frozen Mode B engine, live _busy rule) on the
full candidate stream; factor values attached to surviving trades; net R at
25/50/75/100bps round-trip leg-based costs.

Outputs: signals_factors.json (candidate-level, for selection rates),
         factor_trades.json (trade-level, for all protocol tests).
"""

import json
import os
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
BASE = os.path.join(REPO, "canonical_baseline")
OUT = os.path.join(REPO, "selection_edge", "w1_rs_momentum")
sys.path.insert(0, BASE)
sys.path.insert(0, REPO)

import simlib
from run_ablation import walk_independent, net_r_legs, build_symbol_table

MASK14 = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB", "ONDS", "DRAM",
          "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
assert len(MASK14) == 14

COST_BPS = [0.0025, 0.005, 0.0075, 0.01]


def working_symbols():
    uni = [u["symbol"] for u in simlib.load_universe()]
    in_uni = [s for s in MASK14 if s in uni]
    work = [s for s in uni if s not in MASK14]
    return work, in_uni


def d1_closes(symbol):
    try:
        df = simlib.load_d1(symbol)
    except Exception:
        return None
    return df["Close"]


def pit_endpoint_idx(d1idx, signal_ts):
    """Index position of the last COMPLETED daily bar as of signal-bar close."""
    ts = pd.Timestamp(signal_ts)
    j = d1idx.searchsorted(ts, side="right") - 1
    if ts.hour < 16:
        j -= 1  # first-bar (13:30) signals: today's daily bar still forming
    return int(j)


def nday_ret(closes, j, n):
    if j is None or j < 0 or j - n < 0:
        return None
    c1 = float(closes.iloc[j])
    c0 = float(closes.iloc[j - n])
    if c0 <= 0 or np.isnan(c0) or np.isnan(c1):
        return None
    return c1 / c0 - 1.0


def compute_factors(sym_closes, spy_closes, signal_ts):
    """Return dict of factor values (None when data unavailable)."""
    out = {}
    j = pit_endpoint_idx(sym_closes.index, signal_ts)
    # ---- F1: N-day stock ret minus N-day SPY ret ----
    for n in (15, 20, 25):
        rs = nday_ret(sym_closes, j, n)
        rb = nday_ret(spy_closes, j, n)
        out[f"f1_{n}d"] = (rs - rb) if (rs is not None and rb is not None) else None
    # ---- F2: recent_N minus preceding_M ----
    for n, m in ((10, 50), (20, 50), (10, 40), (10, 60), (20, 60)):
        rec = nday_ret(sym_closes, j, n)
        if rec is None or j - n - m < 0:
            out[f"f2_{n}_{m}"] = None
            continue
        base = nday_ret(sym_closes, j - n, m)
        out[f"f2_{n}_{m}"] = (rec - base) if base is not None else None
    out["endpoint_row"] = j
    return out


def main():
    t0 = time.time()
    work, masked = working_symbols()
    print(f"working set: {len(work)} names; masked from universe: {masked}", flush=True)

    spy_closes = d1_closes("SPY")
    assert spy_closes is not None and len(spy_closes) > 100

    tab = build_symbol_table(work)
    sig_records = []
    n_nodata = 0
    for k, sym in enumerate(work):
        ws, we = tab[sym]
        sigs, _ = simlib.v54_signals(sym, ws, we)
        sc = d1_closes(sym)
        if sc is None or len(sc) < 80:
            n_nodata += 1
            for s in sigs:
                rec = {"signal_id": s["signal_id"], "symbol": sym,
                       "signal_bar_close_at": s["signal_bar_close_at"],
                       "signal_bar_idx": s["signal_bar_idx"],
                       "entry_bar_idx": s["entry_bar_idx"],
                       "entry": s["entry"], "stop": s["stop"], "tp1": s["tp1"],
                       "f1_20d": None, "f1_15d": None, "f1_25d": None,
                       "f2_10_50": None, "f2_20_50": None, "f2_10_40": None,
                       "f2_10_60": None, "f2_20_60": None}
                sig_records.append(rec)
            continue
        for s in sigs:
            f = compute_factors(sc, spy_closes, s["signal_bar_close_at"])
            rec = {"signal_id": s["signal_id"], "symbol": sym,
                   "signal_bar_close_at": s["signal_bar_close_at"],
                   "signal_bar_idx": s["signal_bar_idx"],
                   "entry_bar_idx": s["entry_bar_idx"],
                   "entry": s["entry"], "stop": s["stop"], "tp1": s["tp1"],
                   "f1_20d": f["f1_20d"], "f1_15d": f["f1_15d"], "f1_25d": f["f1_25d"],
                   "f2_10_50": f["f2_10_50"], "f2_20_50": f["f2_20_50"],
                   "f2_10_40": f["f2_10_40"], "f2_10_60": f["f2_10_60"],
                   "f2_20_60": f["f2_20_60"]}
            sig_records.append(rec)
        if (k + 1) % 20 == 0:
            print(f"  signals {k+1}/{len(work)} ({len(sig_records)} so far, "
                  f"{time.time()-t0:.0f}s)", flush=True)
    print(f"total candidate signals: {len(sig_records)}; no-d1 symbols: {n_nodata}",
          flush=True)
    with open(os.path.join(OUT, "signals_factors.json"), "w") as fh:
        json.dump(sig_records, fh, default=str)
    print("wrote signals_factors.json", flush=True)

    # ---- independent trade walk per symbol (busy rule), attach factors ----
    by_sym = {}
    for r in sig_records:
        by_sym.setdefault(r["symbol"], []).append(r)
    fmap = {r["signal_id"]: r for r in sig_records}
    trades = []
    t1 = time.time()
    for k, sym in enumerate(work):
        sigs = sorted(by_sym.get(sym, []), key=lambda r: r["signal_bar_idx"])
        # walk_independent needs the simlib signal dict shape
        tr = walk_independent(sym, sigs)
        for t in tr:
            f = fmap[t["signal_id"]]
            t["f1_20d"] = f["f1_20d"]
            t["f1_15d"] = f["f1_15d"]
            t["f1_25d"] = f["f1_25d"]
            t["f2_10_50"] = f["f2_10_50"]
            t["f2_20_50"] = f["f2_20_50"]
            t["f2_10_40"] = f["f2_10_40"]
            t["f2_10_60"] = f["f2_10_60"]
            t["f2_20_60"] = f["f2_20_60"]
            for bps in COST_BPS:
                t[f"net_r_{bps*10000:.0f}bps"] = net_r_legs(t, bps)
        trades.extend(tr)
        if (k + 1) % 20 == 0:
            print(f"  walked {k+1}/{len(work)} ({len(trades)} trades, "
                  f"{time.time()-t1:.0f}s)", flush=True)
    print(f"total independent trades: {len(trades)}", flush=True)
    with open(os.path.join(OUT, "factor_trades.json"), "w") as fh:
        json.dump(trades, fh, default=str)
    print("wrote factor_trades.json", flush=True)
    print(f"done in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
