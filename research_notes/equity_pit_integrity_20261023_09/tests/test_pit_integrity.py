"""QF-EQUITY-PIT-INTEGRITY-20261023-09 — synthetic fail-before / pass-after fixtures.

Usage:
  python test_pit_integrity.py --impl original --engine <tree>   # expect exit 1 (defects reproduce)
  python test_pit_integrity.py --impl fork     --engine <tree>   # expect exit 0 (all as-of assertions hold)

--engine points at an engine tree laid out like the -08 stage engine/
(pine_backtest.py at root; pine_ranking/, pine_signal_quality/, pine_exposure/,
pine_stack/ subpackages). The fork tree is the same tree with fork/pine_backtest.py
and fork/pine_stack.py overlaid. The benchmark constructor (original midnight vs
fork as-of) is selected by --impl via ../fork/asof_benchmark.py.

ALL prices below are invented fixture numbers. The only real-world values used
are five coincident entry TIMESTAMPS taken from the -08 trade ledger
(2025-05-16, 2025-09-05, 2025-10-17, 2026-02-11, 2026-04-16, all 13:30 ET) —
timestamps only, never prices.

Assertions (each must HOLD under a causally correct implementation):
  B1  Mutating today's not-yet-finished SPY daily close (x40) cannot change
      the RS ranking feature of a candidate signaled today at 09:30 or 13:30 ET
      (exercised through the frozen compute_features -> bench_ret path).
  B2a In pine_backtest.simulate_portfolio (C0), mutating the unfinished 4H
      bar's close at an entry event cannot change final equity or the marked
      equity recorded at that event.
  B2b Same invariance in pine_stack.simulate_stack (the staged ranked stack
      carries its own identical mark()).
  ORD At a contested coincident-entry timestamp with equal RS, the taken
      candidate (by identity) is invariant to all_trades input permutation.
"""
import argparse
import importlib
import itertools
import os
import sys

import numpy as np
import pandas as pd

ET = "America/New_York"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "fork"))
import asof_benchmark  # noqa: E402

RESULTS = []


def check(name, holds, detail):
    RESULTS.append((name, bool(holds)))
    print(f"  [{'HOLDS' if holds else 'VIOLATED'}] {name}: {detail}")


# ----------------------------------------------------------------- B1 fixture
def spy_intraday(mutated):
    """Synthetic SPY 1h bars, 7 sessions ending 2025-05-16 (a real-ledger
    double-entry date). Closes drift 100 -> ~110. In the mutated variant the
    FINAL bar of 2025-05-16 (the day's close, not knowable until 16:00) is x40."""
    sessions = [str(d.date()) for d in pd.bdate_range("2025-04-28", "2025-05-16")]
    rows, idx = [], []
    px = 100.0
    for d in sessions:
        for h in ["09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30"]:
            px += 0.25
            c = px
            if mutated and d == "2025-05-16" and h == "15:30":
                c = px * 40.0
            idx.append(pd.Timestamp(f"{d} {h}", tz=ET))
            rows.append({"Open": c - 0.1, "High": c + 0.1, "Low": c - 0.2,
                         "Close": c, "Volume": 1000.0})
    return pd.DataFrame(rows, index=pd.DatetimeIndex(idx))


def sym_frame(seed_close):
    """Synthetic 4H frame for a candidate symbol: two bars/day 09:30 & 13:30 ET
    from 2025-04-21 through 2025-05-16, gentle invented drift."""
    days = pd.bdate_range("2025-04-21", "2025-05-16")
    idx, closes = [], []
    px = seed_close
    for d in days:
        for h in ["09:30", "13:30"]:
            px += 0.3
            idx.append(pd.Timestamp(f"{d.date()} {h}", tz=ET))
            closes.append(px)
    return pd.DataFrame({"Open": closes, "High": closes, "Low": closes,
                         "Close": closes, "Volume": [5000.0] * len(closes),
                         "vol_ma": [4000.0] * len(closes)},
                        index=pd.DatetimeIndex(idx))


def test_b1(compute_features, impl):
    print("B1 — SPY daily future-close leak into RS ranking feature")
    build = (asof_benchmark.build_daily_midnight if impl == "original"
             else asof_benchmark.build_daily_asof)
    data = {"AAA": sym_frame(50.0), "BBB": sym_frame(80.0)}
    for tlabel, tstamp in [("09:30", "2025-05-16 09:30"), ("13:30", "2025-05-16 13:30")]:
        ts = pd.Timestamp(tstamp, tz=ET)
        si = data["AAA"].index.get_loc(ts)
        cands = [{"symbol": "AAA", "signal_idx": si, "tp1": 999.0, "entry": 60.0, "stop": 55.0},
                 {"symbol": "BBB", "signal_idx": si, "tp1": 999.0, "entry": 90.0, "stop": 85.0}]
        rs = {}
        for mutated in (False, True):
            bench = {"SPY": build(spy_intraday(mutated))}
            feats = compute_features(cands, data, bench)
            rs[mutated] = (feats[0]["rs"], feats[1]["rs"])
        same = all(abs(a - b) < 1e-12 for a, b in zip(rs[False], rs[True]))
        check(f"B1 rs invariant to unfinished SPY close @ {tlabel}",
              same, f"rs normal={rs[False]} vs mutated-close={rs[True]}")


# ----------------------------------------------------------------- B2 fixture
def closes_4h(mutated):
    """One symbol, 6 invented 4H bars over 3 sessions. Bar idx 2 (2025-06-03
    09:30) is trade B's entry bar: unfinished at B's entry event. Mutated x30."""
    stamps = ["2025-06-02 09:30", "2025-06-02 13:30", "2025-06-03 09:30",
              "2025-06-03 13:30", "2025-06-04 09:30", "2025-06-04 13:30"]
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    if mutated:
        closes[2] = 102.0 * 30.0
    idx = pd.DatetimeIndex([pd.Timestamp(s, tz=ET) for s in stamps])
    return pd.Series(closes, index=idx, dtype=float)


def b2_trades(idx):
    """A enters at bar1 open, B enters at bar2 open (A still open); both exit
    at bar5 open. All prices invented."""
    return [
        {"symbol": "AAA", "entry": 100.0, "stop": 95.0, "exit": 104.0,
         "entry_time": idx[1], "exit_time": idx[5]},
        {"symbol": "AAA", "entry": 101.0, "stop": 96.0, "exit": 105.0,
         "entry_time": idx[2], "exit_time": idx[5]},
    ]


def test_b2(pb, stack, impl):
    print("B2 — unfinished-bar close in mark-to-market (sizing + marked equity)")
    outs = {}
    for mutated in (False, True):
        cl = closes_4h(mutated)
        trades = b2_trades(cl.index)
        port = pb.simulate_portfolio(trades, {"AAA": cl}, pb.COSTS["4bps"], pb.RISK_PCT)
        eq_at_b_entry = [e for e in port["curve"] if e[0] == cl.index[2]][0][1]
        outs[mutated] = (port["final_equity"], eq_at_b_entry)
    same = all(abs(a - b) < 1e-9 for a, b in zip(outs[False], outs[True]))
    check("B2a C0 simulate_portfolio invariant to unfinished-bar close",
          same, f"(final_equity, eq@B-entry) normal={outs[False]} vs mutated={outs[True]}")

    outs = {}
    for mutated in (False, True):
        cl = closes_4h(mutated)
        trades = b2_trades(cl.index)
        res = stack.simulate_stack(trades, {"AAA": cl}, pb.COSTS["4bps"],
                                   False, False, False, {})
        outs[mutated] = res["final_equity"]
    same = abs(outs[False] - outs[True]) < 1e-9
    check("B2b pine_stack simulate_stack invariant to unfinished-bar close",
          same, f"final_equity normal={outs[False]} vs mutated={outs[True]}")


# ------------------------------------------------------------- ordering audit
def test_ordering(stack, pb, impl):
    print("ORD — coincident-entry ordering determinism (real ledger timestamp "
          "2025-09-05 13:30 ET, invented prices)")
    T = pd.Timestamp("2025-09-05 13:30", tz=ET)
    grid = []
    for d in pd.bdate_range("2025-09-02", "2025-09-19"):
        for h in ["09:30", "13:30"]:
            grid.append(pd.Timestamp(f"{d.date()} {h}", tz=ET))
    grid = pd.DatetimeIndex(grid)
    closes = {s: pd.Series([100.0] * len(grid), index=grid, dtype=float)
              for s in ("AAA", "BBB", "FLL")}
    t_exit = pd.Timestamp("2025-09-08 09:30", tz=ET)
    # 4 fillers entered at DISTINCT earlier timestamps (1 per timestamp, so
    # the stack's at-most-2-per-contested-timestamp rule never fires for
    # them) and still open at T -> free slots at T = 1 (cap 5), so the pair
    # at T is genuinely contested and exactly one can be taken.
    filler_times = [pd.Timestamp(s, tz=ET) for s in
                    ("2025-09-02 09:30", "2025-09-02 13:30",
                     "2025-09-03 09:30", "2025-09-03 13:30")]
    fillers = [{"symbol": "FLL", "entry": 100.0, "stop": 95.0, "exit": 101.0,
                "entry_time": filler_times[k], "exit_time": t_exit,
                "signal_idx": 10 + k}
               for k in range(4)]
    cand = {
        "AAA": {"symbol": "AAA", "entry": 100.0, "stop": 95.0, "exit": 101.0,
                "entry_time": T, "exit_time": t_exit, "signal_idx": 40},
        "BBB": {"symbol": "BBB", "entry": 100.0, "stop": 95.0, "exit": 101.0,
                "entry_time": T, "exit_time": t_exit, "signal_idx": 41},
    }
    taken_syms = []
    for perm in itertools.permutations(["AAA", "BBB"]):
        trades = fillers + [cand[s] for s in perm]
        stack.rs = {id(tr): 0.05 for tr in trades}  # equal RS for the pair
        res = stack.simulate_stack(trades, closes, pb.COSTS["4bps"],
                                   True, False, False, {})
        taken = [trades[i]["symbol"] for i in res["taken"]
                 if trades[i]["entry_time"] == T]
        taken_syms.append(tuple(taken))
    same = len(set(taken_syms)) == 1
    check("ORD taken candidate at contested coincident timestamp is "
          "input-order invariant", same,
          f"taken at T per input permutation (AAA,BBB)/(BBB,AAA) = {taken_syms}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", choices=["original", "fork"], required=True)
    ap.add_argument("--engine", required=True)
    a = ap.parse_args()
    eng = os.path.abspath(a.engine)
    for p in [eng, os.path.join(eng, "pine_stack"), os.path.join(eng, "pine_ranking"),
              os.path.join(eng, "pine_exposure"), os.path.join(eng, "pine_signal_quality")]:
        sys.path.insert(0, p)
    pb = importlib.import_module("pine_backtest")
    ranking = importlib.import_module("pine_ranking")
    stack = importlib.import_module("pine_stack")
    print(f"impl={a.impl} engine={eng}")
    print(f"pine_backtest={pb.__file__}")
    print(f"pine_stack={stack.__file__}")
    test_b1(ranking.compute_features, a.impl)
    test_b2(pb, stack, a.impl)
    test_ordering(stack, pb, a.impl)
    bad = [n for n, ok in RESULTS if not ok]
    print(f"SUMMARY impl={a.impl}: {len(RESULTS) - len(bad)}/{len(RESULTS)} assertions hold"
          + (f"; VIOLATED: {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
