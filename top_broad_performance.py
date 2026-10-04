#!/usr/bin/env python3
"""TOP-vs-BROAD performance run (System 1) — PRE-AUTHORIZED.

Runs only via top_broad_run.py after preflight passes.
Mike pre-authorized (Bridge #1, 2026-10-04). No holdout. No paper. No launch.

System: gen_candidates -> compute_features -> simulate_stack
  (use_ranking=True, sector_cap=True, dd_gate=False) — the C1 stack.
Universe: BROAD=218 stocks; TOP=50 quarterly (frozen composite).
Window: 2025-03-17 -> 2026-09-14. Costs: 4bps + 25bps.
"""
import sys, os, json
import pandas as pd
import numpy as np
import yfinance as yf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "pine_ranking"))

import pine_backtest as pb
from pine_ranking import gen_candidates, compute_features
from pine_stack.pine_stack import simulate_stack, SECTOR
import scanner_rules as sr
import top_broad_experiment as tbe

STUDY_START = pd.Timestamp("2025-03-17", tz="America/New_York")
STUDY_END = pd.Timestamp("2026-09-14", tz="America/New_York")
REBAL_DATES = ["2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30",
               "2025-12-31", "2026-03-31", "2026-06-30"]
# Periods: (start, end, rebalance_used)
PERIODS = [
    ("2025-03-17", "2025-03-31", "2024-12-31"),
    ("2025-04-01", "2025-06-30", "2025-03-31"),
    ("2025-07-01", "2025-09-30", "2025-06-30"),
    ("2025-10-01", "2025-12-31", "2025-09-30"),
    ("2026-01-01", "2026-03-31", "2025-12-31"),
    ("2026-04-01", "2026-06-30", "2026-03-31"),
    ("2026-07-01", "2026-09-14", "2026-06-30"),
]
EXCLUDED = {"BMNR", "CRWV", "GLXY", "NBIS", "XYZ", "CLSK", "SBET"}
OUT = os.path.join(HERE, "research_notes", "top_broad_results_20261004.json")


def load_universe():
    import hybrid_exit_test as h
    import v54_universe_x2 as ux2
    u = set(h.UNIVERSE_X) | set(ux2.UNIVERSE_X2)
    stocks = sorted(s for s in u if "USD" not in s and s not in EXCLUDED)
    print(f"BROAD universe: {len(stocks)} stocks", flush=True)
    return stocks


def build_4h(symbols):
    """Build corrected 4H bars from verified 1H inputs."""
    data, closes = {}, {}
    for sym in symbols:
        p = os.path.join(HERE, "data_inventory_scratch_20261004", "h1_raw",
                         f"h1_{sym}.pkl")
        if not os.path.exists(p):
            p = os.path.join(HERE, "pine_1h", "cache", f"h1_{sym}.pkl")
        df1h = pd.read_pickle(p)
        # Corrected session-anchored 4H
        df4h = sr.resample_closed_4h_session_anchored(df1h, sym)
        # Restrict to study window + warmup (warmup already in 1H)
        df4h = df4h[df4h.index >= pd.Timestamp("2024-10-07", tz="America/New_York")]
        if "Volume" not in df4h.columns or df4h["Volume"].isna().all():
            print(f"  skip {sym}: no volume", flush=True)
            continue
        df4h = pb.add_pine_indicators(df4h)
        data[sym] = df4h
        closes[sym] = df4h["Close"]
    print(f"4H built for {len(data)} symbols", flush=True)
    return data, closes


def gen_all_trades(data):
    all_trades, skipped_gap = [], 0
    for sym, df in data.items():
        # Only signals at/after study start (warmup before)
        tr, sg = gen_candidates(sym, df)
        # Filter to study window entries
        tr = [t for t in tr if STUDY_START <= t["entry_time"] <= STUDY_END]
        skipped_gap += sg
        all_trades.extend(tr)
    # Deterministic order
    all_trades.sort(key=lambda t: (t["entry_time"], t["symbol"]))
    print(f"Candidates in window: {len(all_trades)}", flush=True)
    return all_trades, skipped_gap


def load_spy():
    spy = yf.download("SPY", start="2024-06-01", end="2026-09-16", interval="1d",
                      prepost=False, progress=False, auto_adjust=False)
    return spy


def compute_top_membership(symbols, spy):
    """Quarterly TOP-50 for each rebalance date. Returns dict rebal -> set."""
    # Daily data for ranking
    print("Downloading daily data for ranking...", flush=True)
    daily = {}
    for sym in symbols:
        try:
            df = yf.download(sym, start="2024-06-01", end="2026-09-16",
                             interval="1d", prepost=False, progress=False,
                             auto_adjust=False)
            if len(df) > 130:
                daily[sym] = df
        except Exception as e:
            print(f"  daily fail {sym}: {e}", flush=True)
    spy_close = spy["Close"].iloc[:, 0] if isinstance(spy["Close"], pd.DataFrame) else spy["Close"]
    # Split dates from manifest/adjudication (frozen)
    split_dates = {
        "ANET": ["2024-12-04"], "BKNG": ["2026-04-06"], "CRWD": ["2026-07-02"],
        "FDX": ["2026-06-01"], "HON": ["2025-10-30", "2026-06-29"],
        "KLAC": ["2026-06-12"], "LCID": ["2025-09-02"], "NFLX": ["2025-11-17"],
        "NOW": ["2025-12-18"], "PANW": ["2024-12-16"], "PPLT": ["2026-05-18"],
        "WDC": ["2025-02-24"], "XLE": ["2025-12-05"], "XLK": ["2025-12-05"],
    }
    membership = {}
    for rdate in REBAL_DATES:
        rd = pd.Timestamp(rdate)
        dv, rs_ret = {}, {}
        for sym, df in daily.items():
            d = df[df.index <= rd]
            if len(d) < 130:
                continue
            close = d["Close"].iloc[:, 0] if isinstance(d["Close"], pd.DataFrame) else d["Close"]
            vol = d["Volume"].iloc[:, 0] if isinstance(d["Volume"], pd.DataFrame) else d["Volume"]
            dollar_vol = close * vol
            # Pass full series; compute_top50 windows to last 60
            dv[sym] = dollar_vol
            # 126-day RS vs SPY
            if len(close) >= 127:
                sym_ret = float(close.iloc[-1] / close.iloc[-127] - 1)
                spy_d = spy_close[spy_close.index <= rd]
                if len(spy_d) >= 127:
                    spy_ret = float(spy_d.iloc[-1] / spy_d.iloc[-127] - 1)
                    rs_ret[sym] = sym_ret - spy_ret
        sel, diag = tbe.compute_top50(dv, rs_ret,
                                      split_dates={s: split_dates.get(s, [])
                                                   for s in dv},
                                      top_n=50)
        membership[rdate] = set(sel)
        print(f"  {rdate}: TOP-50 from {diag['n_valid']} valid", flush=True)
    return membership


def filter_top_trades(all_trades, membership):
    """Keep trades whose entry falls in a period where symbol was in TOP."""
    top_trades = []
    for t in all_trades:
        et = t["entry_time"]
        for p_start, p_end, rdate in PERIODS:
            ps = pd.Timestamp(p_start, tz="America/New_York")
            pe = pd.Timestamp(p_end, tz="America/New_York")
            if ps <= et <= pe:
                if t["symbol"] in membership[rdate]:
                    top_trades.append(t)
                break
    print(f"TOP-leg candidates: {len(top_trades)}", flush=True)
    return top_trades


def marked_equity_at_end(taken_trades, closes, study_end, cost):
    """Replay taken trades to compute marked equity at study end.

    Uses frozen System-1 sizing (1% of equity, halved under S4 DD gate).
    Does not modify pine_stack.py; replays from the taken trade list.
    """
    def mark(sym, t):
        s = closes[sym]
        idx = s.index.searchsorted(t, side="right") - 1
        return float(s.iloc[idx]) if idx >= 0 else float(s.iloc[0])

    events = []
    for tr in taken_trades:
        events.append((tr["entry_time"], "entry", tr))
        events.append((tr["exit_time"], "exit", tr))
    events.sort(key=lambda e: (e[0], e[1]))

    realized = pb.START_EQUITY
    peak = realized
    open_pos = []  # (trade, risk_dollars, size)

    for t, kind, tr in events:
        if t > study_end:
            break
        if kind == "entry":
            # Marked equity for DD gate
            unreal = sum(((mark(p[0]["symbol"], t) - p[0]["entry"]) / p[0]["entry"]) * p[2]
                         for p in open_pos)
            eq = realized + unreal
            peak = max(peak, eq)
            cur_risk = pb.RISK_PCT
            if eq <= 0.90 * peak:
                cur_risk = pb.RISK_PCT / 2.0
            risk_dollars = cur_risk * eq
            risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
            size = risk_dollars / risk_frac if risk_frac > 0 else 0.0
            open_pos.append((tr, risk_dollars, size))
        else:
            for i, (otr, rd, sz) in enumerate(open_pos):
                if otr is tr:
                    _, _, net_r, _ = pb._outcome(tr["entry"], tr["stop"],
                                                 tr["exit"], cost)
                    realized += rd * net_r
                    open_pos.pop(i)
                    break
            # Update peak on exits (marked)
            unreal = sum(((mark(p[0]["symbol"], t) - p[0]["entry"]) / p[0]["entry"]) * p[2]
                         for p in open_pos)
            peak = max(peak, realized + unreal)

    # Mark remaining open positions at study end
    unreal_end = sum(((mark(tr["symbol"], study_end) - tr["entry"]) / tr["entry"]) * sz
                     for tr, rd, sz in open_pos)
    return realized + unreal_end


def run_leg(trades, closes, data, spy, cost_name, tag):
    """Run simulate_stack + compute gates inputs."""
    from pine_signal_quality import load_benchmarks
    # Features for ranking
    bench, _ = load_benchmarks()
    feats = compute_features(trades, data, bench)
    # simulate_stack needs global rs
    from pine_stack import pine_stack as st
    st.rs = {id(tr): feats[i]["rs"] for i, tr in enumerate(trades)}
    # Sector map: unmapped -> unique sector (cap doesn't bind)
    sector_map = dict(SECTOR)
    for t in trades:
        if t["symbol"] not in sector_map:
            sector_map[t["symbol"]] = f"UNMAPPED_{t['symbol']}"
    cost = pb.COSTS[cost_name]
    port = simulate_stack(trades, closes, cost, True, True, False, sector_map)
    taken = [trades[i] for i in port["taken"]]
    # Per-trade net R
    net_rs = []
    for tr in taken:
        _, _, net_r, _ = pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)
        net_rs.append(net_r)
        tr["_net_r"] = net_r
    # Calmar from marked equity: max_dd from simulate_stack (marked),
    # final marked equity via replay (frozen sizing, no pine_stack changes).
    max_dd = port["max_drawdown"]
    years = (STUDY_END - STUDY_START).days / 365.25
    final_marked = marked_equity_at_end(taken, closes, STUDY_END, cost)
    if final_marked > 0 and pb.START_EQUITY > 0:
        cagr = (final_marked / pb.START_EQUITY) ** (1 / years) - 1
    else:
        cagr = 0.0
    calmar = cagr / max_dd if max_dd > 0 else 0.0
    return {"tag": tag, "cost": cost_name, "n_trades": len(taken),
            "expectancy": float(np.mean(net_rs)) if net_rs else 0.0,
            "net_rs": net_rs, "taken": taken,
            "calmar": float(calmar), "cagr": float(cagr),
            "max_dd": float(max_dd),
            "final_marked": float(final_marked),
            "port": port}


def run_performance():
    print("=== TOP-vs-BROAD performance run (System 1) ===", flush=True)
    symbols = load_universe()
    data, closes = build_4h(symbols)
    all_trades, skipped_gap = gen_all_trades(data)
    spy = load_spy()
    membership = compute_top_membership(symbols, spy)
    top_trades = filter_top_trades(all_trades, membership)

    results = {"window": ["2025-03-17", "2026-09-14"],
               "broad_n": len(symbols), "legs": {}}
    for cost_name in ["4bps", "25bps"]:
        broad = run_leg(all_trades, closes, data, spy, cost_name, "BROAD")
        top = run_leg(top_trades, closes, data, spy, cost_name, "TOP")
        results["legs"][cost_name] = {
            "broad": {k: v for k, v in broad.items()
                      if k not in ("net_rs", "taken", "port")},
            "top": {k: v for k, v in top.items()
                    if k not in ("net_rs", "taken", "port")},
        }
        # Gates (25bps primary)
        if cost_name == "25bps":
            b_exp, t_exp = broad["expectancy"], top["expectancy"]
            gates = {
                "G0": t_exp > 0.15,
                "G1": (t_exp - b_exp) > 0.10,
                "G2": top["calmar"] > 1.0 and top["calmar"] > broad["calmar"],
                "G4": len(top["taken"]) >= 100 and len(broad["taken"]) >= 100,
            }
            # G3: yearly splits by exit date
            y1_end = pd.Timestamp("2026-03-16", tz="America/New_York")
            def yr_exp(taken, y1):
                rs = [t["_net_r"] for t in taken
                      if (t["exit_time"] <= y1_end) == y1 and len([1]) and t["_net_r"] is not None]
                # Simpler: split by exit_time
                return rs
            t_y1 = [t["_net_r"] for t in top["taken"] if t["exit_time"] <= y1_end]
            t_y2 = [t["_net_r"] for t in top["taken"] if t["exit_time"] > y1_end]
            b_y1 = [t["_net_r"] for t in broad["taken"] if t["exit_time"] <= y1_end]
            b_y2 = [t["_net_r"] for t in broad["taken"] if t["exit_time"] > y1_end]
            g3_y1 = len(t_y1) >= 25 and len(b_y1) >= 25 and np.mean(t_y1) > np.mean(b_y1)
            g3_y2 = len(t_y2) >= 25 and len(b_y2) >= 25 and np.mean(t_y2) > np.mean(b_y2)
            gates["G3"] = bool(g3_y1 and g3_y2)
            gates["G3_detail"] = {"y1_n": (len(t_y1), len(b_y1)), "y2_n": (len(t_y2), len(b_y2))}
            # G5: bootstrap
            months = [f"{y}-{m:02d}" for y in (2025, 2026)
                      for m in range(1, 13)]
            # 19 buckets: Mar 2025 .. Sep 2026
            months = months[2:12] + months[12:21]  # Mar25-Dec25, Jan26-Sep26
            def to_boot(taken):
                out = []
                for t in taken:
                    et = t["exit_time"]
                    mi = (et.year - 2025) * 12 + (et.month - 3)
                    if 0 <= mi < 19:
                        out.append({"exit_month": mi, "net_r": t["_net_r"]})
                return out
            boot = tbe.paired_block_bootstrap(to_boot(top["taken"]),
                                              to_boot(broad["taken"]), months)
            gates["G5"] = bool(boot["g5_pass"] and not boot["inconclusive"])
            gates["G5_detail"] = {k: v for k, v in boot.items()
                                  if k in ("ci", "point", "valid", "discard_rate",
                                           "inconclusive")}
            results["gates"] = {k: (bool(v) if isinstance(v, (bool, np.bool_)) else v)
                                for k, v in gates.items()}
            results["gates"]["all_pass"] = all(
                v for k, v in gates.items() if k.startswith("G"))

    json.dump(results, open(OUT, "w"), indent=1, default=str)
    print(f"Results written to {OUT}", flush=True)
    g = results.get("gates", {})
    print(f"Gates: { {k: v for k, v in g.items() if k.startswith('G')} }", flush=True)
    return results
