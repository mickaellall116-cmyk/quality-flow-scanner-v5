"""QF-EQUITY43-DEV-ORDER-CENSOR-20261023-13 — deterministic fixture for the
right-censored terminal-candidate treatment (adjudication step 2).

Usage:
  python test_censoring.py --impl successor --engine <successor tree>
      # expect exit 0 — the treatment contract HOLDS
  python test_censoring.py --impl frozen --engine <pristine -09 fork tree>
      # expect exit 1 — the frozen construction VIOLATES the contract: the
      # terminal-open candidate is never emitted (gen_candidates drops it),
      # so it has no selection disposition, is absent from terminal
      # inventory, and its as-of mark never reaches account equity.

ALL prices are invented fixture numbers. Timestamps are synthetic 4H bar
starts (America/New_York). The contract asserted (identical for both
simulator paths, C0 configuration):
  C1  A taken censored candidate is held in inventory to the cutoff, valued
      at the last-completed-bar as-of mark, and that unrealized value is
      included in final equity — with NO exit event, NO exit cash flow and
      NO trade R fabricated for it.
  C2  A censored candidate that cannot be taken receives the same gate
      disposition as any candidate (here: skipped_cap) in both paths.
  C3  Both paths agree trade-by-trade: taken identities, exit cash flows,
      skip dispositions, terminal inventory, final equity.
  C4  Results are invariant under a seeded permutation of the input list
      once the pinned canonical (symbol, signal_idx) order is applied
      (and the stack path is invariant even without re-sorting).
"""
import argparse
import os
import random
import sys

import pandas as pd

ET = "America/New_York"
BARS = pd.DatetimeIndex([
    pd.Timestamp("2026-10-14 09:30", tz=ET), pd.Timestamp("2026-10-14 13:30", tz=ET),
    pd.Timestamp("2026-10-15 09:30", tz=ET), pd.Timestamp("2026-10-15 13:30", tz=ET),
    pd.Timestamp("2026-10-16 09:30", tz=ET), pd.Timestamp("2026-10-16 13:30", tz=ET)])
CUTOFF = BARS[-1] + pd.Timedelta(hours=4)

RESULTS = []


def check(name, holds, detail):
    RESULTS.append((name, bool(holds)))
    print(f"  [{'HOLDS' if holds else 'VIOLATED'}] {name}: {detail}")


def closes_map():
    flat = [100.0] * 6
    return {
        "AAA": pd.Series([100.0, 100.0, 100.0, 100.0, 100.0, 110.0], index=BARS),
        "BBB": pd.Series(flat, index=BARS),
        "CCC": pd.Series(flat, index=BARS),
        **{f"F{k}": pd.Series(flat, index=BARS) for k in range(1, 6)},
    }


def cand(sym, signal_idx, entry_time, entry, stop, exit_px, exit_time, censored=False):
    return {"symbol": sym, "signal_idx": signal_idx, "entry": entry, "stop": stop,
            "tp1": entry + 5.0, "exit": exit_px, "exit_time": exit_time,
            "entry_time": entry_time,
            "reason": "censored_terminal_open" if censored else "stop",
            "tp1_hit": False, "hold_bars": None if censored else 4,
            "signal_time": str(entry_time), "censored": censored}


def fixture_a():
    """BBB closed (+2.0R at zero cost); AAA censored, taken and marked +$200."""
    return [
        cand("BBB", 1, BARS[1], 100.0, 95.0, 110.0, BARS[3]),
        cand("AAA", 2, BARS[2], 100.0, 95.0, None, None, censored=True),
    ]


def fixture_b():
    """Five flat closed fillers occupy all slots; CCC censored -> skipped_cap."""
    out = [cand(f"F{k}", k, BARS[1], 100.0, 95.0, 100.0, BARS[5])
           for k in range(1, 6)]
    out.append(cand("CCC", 3, BARS[2], 100.0, 95.0, None, None, censored=True))
    return out


def canon(trades):
    return sorted(trades, key=lambda t: (t["symbol"], t["signal_idx"]))


def keyset(trades, idxs):
    return sorted((trades[i]["symbol"], trades[i]["signal_idx"]) for i in idxs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", choices=["frozen", "successor"], required=True)
    ap.add_argument("--engine", required=True)
    args = ap.parse_args()
    ENG = os.path.abspath(args.engine)
    for p in (ENG, os.path.join(ENG, "pine_stack"), os.path.join(ENG, "pine_ranking"),
              os.path.join(ENG, "pine_exposure"), os.path.join(ENG, "pine_signal_quality")):
        sys.path.insert(0, p)
    import pine_backtest as pb
    import pine_stack as st
    from pine_exposure import SECTOR

    closes = closes_map()
    SECT = dict(SECTOR)
    for s in closes:
        SECT.setdefault(s, "TEST")
    COST = 0.0

    for fname, fixture, want in (
            ("A", fixture_a, {"final": 10400.0, "realized": 10200.0}),
            ("B", fixture_b, {"final": 10000.0, "realized": 10000.0})):
        trades = canon(fixture())
        if args.impl == "frozen":
            # The frozen construction: terminal-open candidates are never
            # emitted, so the pipeline silently drops them before simulation.
            sim_trades = [t for t in trades if not t.get("censored")]
            ppb = pb.simulate_portfolio(sim_trades, closes, COST, pb.RISK_PCT)
            pc0 = st.simulate_stack(sim_trades, closes, COST, False, False,
                                    False, SECT)
        else:
            sim_trades = trades
            ppb = pb.simulate_portfolio(sim_trades, closes, COST, pb.RISK_PCT,
                                        cutoff=CUTOFF)
            pc0 = st.simulate_stack(sim_trades, closes, COST, False, False,
                                    False, SECT, cutoff=CUTOFF)
        # ---- C3: trade-by-trade agreement between the two paths
        pb_taken = sorted(e["key"] for e in ppb.get("ledger", [])
                          if e["action"] == "taken")
        st_taken = keyset(sim_trades, pc0["taken"])
        check(f"{fname}/C3 taken identities agree",
              pb_taken == st_taken, f"pb={pb_taken} stack={st_taken}")
        pb_cf = {e["key"]: e["cash_flow"] for e in ppb.get("ledger", [])
                 if e["action"] == "exit"}
        st_cf = {e["key"]: e["cash_flow"] for e in pc0.get("exit_cashflows", [])}
        check(f"{fname}/C3 exit cash flows agree",
              pb_cf == st_cf, f"pb={pb_cf} stack={st_cf}")
        check(f"{fname}/C3 final equity agrees",
              abs(ppb["final_equity"] - pc0["final_equity"]) < 1e-9,
              f"pb={ppb['final_equity']} stack={pc0['final_equity']}")
        # ---- C1 / C2: the treatment contract for the censored candidate
        cens = [t for t in trades if t.get("censored")]
        for t in cens:
            key = (t["symbol"], t["signal_idx"])
            term = pc0.get("terminal_open", [])
            in_inv = any(x["symbol"] == key[0] for x in term)
            disp = None
            if "disposition" in pc0:
                idx = sim_trades.index(t) if t in sim_trades else None
                disp = pc0["disposition"].get(idx) if idx is not None else None
            if fname == "A":
                check("A/C1 censored taken, in terminal inventory, marked "
                      "into equity, no exit fabricated",
                      in_inv and disp == "taken"
                      and abs(term[0]["mark"] - 110.0) < 1e-12
                      and abs(term[0]["unreal_dollars"] - 200.0) < 1e-9
                      and key not in pb_cf and key not in st_cf
                      and abs(ppb["final_equity"] - want["final"]) < 1e-9
                      and ppb.get("realized_equity") is not None
                      and abs(ppb["realized_equity"] - want["realized"]) < 1e-9,
                      f"disp={disp} inv={in_inv} final={ppb['final_equity']} "
                      f"realized={ppb.get('realized_equity')}")
            else:
                check("B/C2 censored rejected with documented gate reason "
                      "(skipped_cap) in both paths, absent from equity",
                      disp == "skipped_cap" and not in_inv
                      and abs(ppb["final_equity"] - want["final"]) < 1e-9,
                      f"disp={disp} inv={in_inv} final={ppb['final_equity']}")
        # ---- C4: seeded permutation invariance (canonical pipeline + stack)
        if args.impl == "successor":
            shuffled = list(trades)
            random.Random(20261023).shuffle(shuffled)
            ppb2 = pb.simulate_portfolio(canon(shuffled), closes, COST,
                                         pb.RISK_PCT, cutoff=CUTOFF)
            pc02 = st.simulate_stack(shuffled, closes, COST, False, False,
                                     False, SECT, cutoff=CUTOFF)
            _ = ppb2, pc02
            check(f"{fname}/C4 permutation invariance",
                  abs(ppb2["final_equity"] - ppb["final_equity"]) < 1e-9
                  and abs(pc02["final_equity"] - pc0["final_equity"]) < 1e-9
                  and keyset(shuffled, pc02["taken"]) == st_taken,
                  f"pb_perm={ppb2['final_equity']} stack_raw_shuffled="
                  f"{pc02['final_equity']}")

    n_hold = sum(1 for _, h in RESULTS if h)
    print(f"SUMMARY impl={args.impl}: {n_hold}/{len(RESULTS)} assertions hold")
    if args.impl == "successor":
        return 0 if n_hold == len(RESULTS) else 1
    return 1 if n_hold < len(RESULTS) else 0


if __name__ == "__main__":
    sys.exit(main())
