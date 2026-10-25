"""P1 synthetic fixtures for the all-bar MTM measurement fork.

Run: python3 tests/test_mtm_allbar.py  (exit 0 = all assertions hold)

Fixture design (hand-computed expectations):
  Bars for AAA (4H, starts 09:30/13:30 over two days):
    idx0 2025-01-06 09:30 close 100   (pre-entry bar)
    idx1 2025-01-06 13:30 close 100   (entry bar; entry_time = idx1 start)
    idx2 2025-01-07 09:30 close  50   (intra-event excursion bar)
    idx3 2025-01-07 13:30 close 100   (exit bar; exit_time = idx3 start)
  One trade: entry 100 at idx1 start, stop 90 (risk_frac 0.1), exit 100
  at idx3 start (gross/net R = 0 at cost 0). Position size at entry:
  risk_dollars = 1% * 10000 = 100 -> size = 100 / 0.1 = 1000.
  Event marks: entry event (mark = idx0 close 100) eq 10000; exit event
  eq 10000 -> event-sampled DD = 0.  FAIL-BEFORE: the frozen event grid
  reports 0 and misses the excursion entirely.
  All-bar marks add idx2's completion (idx3 start): mark = idx2 close 50
  -> eq = 10000 + 1000 * (50-100)/100 = 9500 -> all-bar DD = 5.0% exactly.
  PASS-AFTER: fork allbar_max_drawdown == 0.05, event track == 0.

Fixture B mirrors A with the excursion UP (close 150): all-bar peak
10500 at idx2 completion, then exit event eq 10000 -> DD = 500/10500.
"""
import os
import sys
import types

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "code"))
import mtm_allbar  # noqa: E402

ET = "America/New_York"


def _pb_stub():
    pb = types.SimpleNamespace()
    pb.START_EQUITY = 10_000.0
    pb.RISK_PCT = 0.01
    pb.MAX_CONCURRENT = 5
    pb.MAX_PORTFOLIO_RISK = 0.05

    def _outcome(entry, stop, exit_px, cost):
        risk_frac = (entry - stop) / entry
        gross_ret = (exit_px - entry) / entry
        net_ret = gross_ret - cost
        return risk_frac, gross_ret / risk_frac, net_ret / risk_frac, net_ret
    pb._outcome = _outcome
    return pb


def _fixture(excursion_close):
    idx = pd.DatetimeIndex([
        "2025-01-06 09:30", "2025-01-06 13:30",
        "2025-01-07 09:30", "2025-01-07 13:30"]).tz_localize(ET)
    closes = {"AAA": pd.Series([100.0, 100.0, excursion_close, 100.0],
                               index=idx)}
    trades = [{"symbol": "AAA", "entry": 100.0, "stop": 90.0,
               "exit": 100.0, "signal_idx": 1,
               "entry_time": idx[1], "exit_time": idx[3]}]
    cutoff = idx[3] + pd.Timedelta(hours=4)
    return trades, closes, cutoff


def _event_sampled_dd(trades, closes, cutoff):
    """Frozen event-grid semantics, recomputed independently here:
    mark only at entry/exit event times (as-of close), DD on that path."""
    def mark(sym, t):
        s = closes[sym]
        ends = s.index + pd.Timedelta(hours=4)
        ii = ends.searchsorted(t, side="right") - 1
        return float(s.iloc[ii]) if ii >= 0 else float(s.iloc[0])
    realized, peak, dd = 10_000.0, 10_000.0, 0.0
    size = (0.01 * 10_000.0) / ((100.0 - 90.0) / 100.0)
    eq = realized + size * (mark("AAA", trades[0]["entry_time"]) - 100.0) / 100.0
    peak = max(peak, eq)
    dd = max(dd, (peak - eq) / peak)
    eq = realized  # exit processed, cash flow 0
    peak = max(peak, eq)
    dd = max(dd, (peak - eq) / peak)
    return dd


def main():
    pb = _pb_stub()
    failures = []

    def check(name, cond, detail=""):
        print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
        if not cond:
            failures.append(name)

    # Fixture A: downward excursion between events.
    trades, closes, cutoff = _fixture(50.0)
    ev = _event_sampled_dd(trades, closes, cutoff)
    check("A fail-before: event grid misses excursion (DD=0)",
          ev == 0.0, f"event DD={ev}")
    out = mtm_allbar.simulate_stack_allbar(
        trades, closes, 0.0, False, False, False, {}, cutoff=cutoff, pb=pb)
    check("A pass-after: all-bar DD == 5.0%",
          abs(out["allbar_max_drawdown"] - 0.05) < 1e-12,
          f"got {out['allbar_max_drawdown']}")
    check("A fork event track == 0", out["event_sampled_max_drawdown"] == 0.0)
    check("A decisions trivially intact",
          out["taken"] == [0] and out["final_equity"] == 10_000.0)
    ser, dd = mtm_allbar.equity_series_from_intervals(
        [{"symbol": "AAA", "entry": 100.0, "entry_time": trades[0]["entry_time"],
          "exit_time": trades[0]["exit_time"], "size": 1000.0,
          "exit_cash_flow": 0.0}],
        closes, 10_000.0, trades[0]["entry_time"], cutoff)
    check("A interval reconstruction DD == 5.0%",
          abs(dd - 0.05) < 1e-12, f"got {dd}")
    fork_bc = {t: e for t, e, k in out["allbar_equity_series"]
               if k == "bar_close"}
    fork_last = out["allbar_equity_series"][-1][1]
    check("A fork series == interval series at bar completions",
          all(abs((fork_bc[t] if t in fork_bc else fork_last) - e) < 1e-9
              for t, e in ser) and len(ser) >= 3,
          f"fork_bc={fork_bc} interval={ser}")

    # Fixture B: upward excursion (peak forms between events).
    trades, closes, cutoff = _fixture(150.0)
    out = mtm_allbar.simulate_stack_allbar(
        trades, closes, 0.0, False, False, False, {}, cutoff=cutoff, pb=pb)
    want = 500.0 / 10_500.0
    check("B all-bar DD == 500/10500",
          abs(out["allbar_max_drawdown"] - want) < 1e-12,
          f"got {out['allbar_max_drawdown']} want {want}")
    check("B event track == 0", out["event_sampled_max_drawdown"] == 0.0)

    # Fixture C: dd_gate refused (fail-closed).
    try:
        mtm_allbar.simulate_stack_allbar(
            trades, closes, 0.0, False, False, True, {}, cutoff=cutoff,
            pb=pb)
        check("C dd_gate=True refused", False)
    except ValueError:
        check("C dd_gate=True refused", True)

    # Fixture D: no trades -> both tracks zero.
    idx = pd.DatetimeIndex(["2025-01-06 09:30"]).tz_localize(ET)
    out = mtm_allbar.simulate_stack_allbar(
        [], {"AAA": pd.Series([100.0], index=idx)}, 0.0, False, False,
        False, {}, cutoff=idx[0] + pd.Timedelta(hours=4), pb=pb)
    check("D empty book DD 0/0",
          out["allbar_max_drawdown"] == 0.0
          and out["event_sampled_max_drawdown"] == 0.0)

    print("SUMMARY", "FAIL" if failures else "PASS", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
