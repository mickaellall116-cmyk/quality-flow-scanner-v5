"""29r synthetic fixtures for the repaired all-bar MTM fork.

Run: python3 tests/test_mtm_allbar.py  (exit 0 = all assertions hold)

Fixtures A–D are the -29 battery, unchanged in expectation (the
repair moves only the causal timestamps of bar-close marks, never a
value): A downward excursion (fail-before event DD 0 -> pass-after
all-bar DD 5.0% exactly), B upward excursion (DD 500/10500),
C dd_gate refused, D empty book.

Fixtures E–H are the repair battery required by ChatGPT's -29
verdict: E second-bin marks stamped at the table bin end 16:00
(never 17:30); F an early-close session (single bin ending 13:00)
marked through a held position; G a DST transition week (bin ends
carry -05:00 before, -04:00 after, same wall clock); H fail-closed
grids — a bar on a non-session date, a bar at a non-bin start, and a
phantom second bin on an early-close session each raise
SessionTableError instead of being stamped by +4h arithmetic.
"""
import os
import sys
import types

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "code"))
import mtm_allbar  # noqa: E402
import session_bins  # noqa: E402

ET = "America/New_York"
FAILURES = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        FAILURES.append(name)


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


def _event_sampled_dd(trades, closes):
    """Frozen event-grid semantics, recomputed independently here:
    mark only at entry/exit event times (as-of close on table bin
    ends), DD on that path."""
    table = session_bins.load_pinned_table()

    def mark(sym, t):
        s = closes[sym]
        ends = pd.DatetimeIndex([pd.Timestamp(table.bin_end(x))
                                 for x in s.index])
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


def _bar_close_stamps(out):
    return [t for t, _e, k in out["allbar_equity_series"]
            if k == "bar_close"]


def main():
    pb = _pb_stub()

    # Fixture A: downward excursion between events.
    trades, closes, cutoff = _fixture(50.0)
    ev = _event_sampled_dd(trades, closes)
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
        [{"symbol": "AAA", "entry": 100.0,
          "entry_time": trades[0]["entry_time"],
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

    # Fixture E (repair): second-bin completions stamped 16:00.
    stamps = _bar_close_stamps(out)
    check("E bin2 completion stamped 16:00-05:00, never 17:30",
          "2025-01-06 16:00:00-05:00" in stamps
          and all("17:30" not in s for s in stamps),
          f"stamps={stamps}")

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

    # Fixture F (repair): early-close session, position held over it.
    # 2025-07-03 single bar close 100 (bin ends 13:00-04:00);
    # 2025-07-07 bars close 80 / 100. Entry at the early-close bar's
    # open, exit at 2025-07-07 13:30 for 100 (0R). The Jul-07 09:30
    # bar's completion (13:30) marks the position at 80 -> eq 9800
    # -> all-bar DD 2.0%; the event grid never sees it.
    idx = pd.DatetimeIndex(["2025-07-03 09:30", "2025-07-07 09:30",
                            "2025-07-07 13:30"]).tz_localize(ET)
    closes_f = {"AAA": pd.Series([100.0, 80.0, 100.0], index=idx)}
    trades_f = [{"symbol": "AAA", "entry": 100.0, "stop": 90.0,
                 "exit": 100.0, "signal_idx": 1,
                 "entry_time": idx[0], "exit_time": idx[2]}]
    out = mtm_allbar.simulate_stack_allbar(
        trades_f, closes_f, 0.0, False, False, False, {},
        cutoff=idx[2] + pd.Timedelta(hours=4), pb=pb)
    stamps = _bar_close_stamps(out)
    check("F early-close completion stamped 13:00-04:00",
          "2025-07-03 13:00:00-04:00" in stamps, f"stamps={stamps}")
    check("F all-bar DD == 2.0%, event track == 0",
          abs(out["allbar_max_drawdown"] - 0.02) < 1e-12
          and out["event_sampled_max_drawdown"] == 0.0,
          f"allbar={out['allbar_max_drawdown']}")

    # Fixture G (repair): DST transition week via interval rebuild.
    idx = pd.DatetimeIndex(["2025-03-07 09:30", "2025-03-07 13:30",
                            "2025-03-10 09:30",
                            "2025-03-10 13:30"]).tz_localize(ET)
    closes_g = {"AAA": pd.Series([100.0, 100.0, 100.0, 100.0], index=idx)}
    ser, dd = mtm_allbar.equity_series_from_intervals(
        [{"symbol": "AAA", "entry": 100.0, "entry_time": idx[0],
          "exit_time": idx[3], "size": 1000.0, "exit_cash_flow": 0.0}],
        closes_g, 10_000.0, idx[0],
        pd.Timestamp("2025-03-10 16:00", tz=ET))
    stamps = [t for t, _e in ser]
    check("G DST bin ends: Fri -05:00, Mon -04:00, no 17:30",
          "2025-03-07 16:00:00-05:00" in stamps
          and "2025-03-10 16:00:00-04:00" in stamps
          and all("17:30" not in s for s in stamps),
          f"stamps={stamps}")
    check("G flat closes -> DD 0", dd == 0.0)

    # Fixture H (repair): fail-closed grids.
    def expect_grid_refusal(name, bad_idx):
        bad_closes = {"AAA": pd.Series([100.0] * len(bad_idx),
                                       index=bad_idx)}
        try:
            mtm_allbar.simulate_stack_allbar(
                [], bad_closes, 0.0, False, False, False, {},
                cutoff=bad_idx[-1] + pd.Timedelta(hours=4), pb=pb)
            check(name, False, "no error raised")
        except session_bins.SessionTableError:
            check(name, True)
        except Exception as e:  # wrong failure mode is still a failure
            check(name, False, f"wrong error: {type(e).__name__} {e}")

    expect_grid_refusal(
        "H1 bar on non-session date refused (Sat 2025-01-04)",
        pd.DatetimeIndex(["2025-01-04 09:30"]).tz_localize(ET))
    expect_grid_refusal(
        "H2 bar at non-bin start refused (10:30)",
        pd.DatetimeIndex(["2025-01-06 10:30"]).tz_localize(ET))
    expect_grid_refusal(
        "H3 phantom second bin on early close refused",
        pd.DatetimeIndex(["2025-07-03 09:30",
                          "2025-07-03 13:30"]).tz_localize(ET))

    print("SUMMARY", "FAIL" if FAILURES else "PASS", FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
