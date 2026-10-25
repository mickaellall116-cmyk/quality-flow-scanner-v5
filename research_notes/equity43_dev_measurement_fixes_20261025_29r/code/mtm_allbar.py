"""P1 (repaired, 29r) — All-bar marked-to-market equity / drawdown.

QF-EQUITY43-DEV-MEASUREMENT-FIXES-20261025-29r — successor of the -29
module of the same name, repaired per ChatGPT's independent -29
verdict (Slack TS 1792935577.054259): P1 was HELD on session-time
causality. The -29 module derived every bar completion as
`bar start + 4h` (BAR = 4h), stamping second-bin marks 17:30 ET; the
equity grid is session-aware — bins are 09:30->13:30 and 13:30->16:00
ET, with calendar-specific early closes (single bin 09:30->13:00).

Repair: every completion instant is the pinned session table's
`bin_end` (session_bins.py; adopted 751-session table, sha256
00c5555c…), resolved per bar from its (session, bin start). No duration
arithmetic remains anywhere in this module. A bar whose start is not
a table bin start, or whose session is absent from the table, raises
SessionTableError (fail-closed) instead of being stamped by formula.

Everything else is the -29 measurement fork, unchanged:

  (i)   Equity is marked at every admitted 4H bar completion on the
        union calendar of the run's symbols, in addition to the event
        times.
  (ii)  Valuation is byte-identical to the frozen `marked_equity`:
        realized cash + sum over open positions of size * (as-of
        close - entry) / entry. Only WHEN marking happens changes,
        never HOW a position is valued.
  (iii) Max drawdown is computed on the all-bar series; the
        event-sampled series is computed in parallel on the identical
        run and returned separately (`event_sampled_max_drawdown`).
        The invariant all-bar DD >= event-sampled DD is asserted.
  (iv)  Decision invariance: entries/exits/gates run at event times
        only, with the identical marked_equity(t) values as the
        frozen code. At every event time (always a bin start), the
        as-of mark selects the same completed bar under table bin
        ends as under the superseded +4h ends: the bin ending AT a
        13:30 event is bin 1 under both, and the bin ending before a
        09:30 event is the prior session's last bin under both. So
        decisions and the event-sampled track are unchanged; only
        the causal timestamps of the bar-close marks move (17:30 ->
        16:00 for second bins; 13:30 -> 13:00 for early-close bins).

Fail-closed guards (retained from -29):
  * dd_gate=True is REFUSED: with the S4 drawdown gate active, the
    peak feeds sizing decisions, so an all-bar peak could alter
    decisions. The frozen DEV C1 configuration runs with
    dd_gate=False, so the refusal never triggers on the DEV record.
  * use of this module never mutates the frozen sources.

`equity_series_from_intervals` remains the INDEPENDENT reconstruction
of the all-bar marked equity path from a finished run's recorded
position intervals; it shares no code with the fork's loop and is
repaired to the same table bin ends.
"""
from collections import defaultdict

import pandas as pd

import session_bins

_TABLE = None


def _table():
    global _TABLE
    if _TABLE is None:
        _TABLE = session_bins.load_pinned_table()
    return _TABLE


def set_session_table(table):
    """Test hook: inject a SessionTable (the pinned one is the only
    table production callers get)."""
    global _TABLE
    _TABLE = table


def _ends_for(symbol, series, cache):
    """pd.DatetimeIndex of pinned bin ends aligned with series.index.
    Fail-closed: any bar start not in the table raises."""
    key = (symbol, id(series))
    ends = cache.get(key)
    if ends is None:
        table = _table()
        ends = pd.DatetimeIndex(
            [pd.Timestamp(table.bin_end(ts)) for ts in series.index])
        cache[key] = ends
    return ends


def _bar_completion_times(closes, lo, hi, cache):
    """Union of bar-completion instants (pinned bin ends) in [lo, hi]."""
    out = set()
    for sym, s in closes.items():
        for ts in _ends_for(sym, s, cache):
            if lo <= ts <= hi:
                out.add(ts)
    return sorted(out)


def simulate_stack_allbar(all_trades, closes, cost, use_ranking, sector_cap,
                          dd_gate, sector_map, diag=None, cutoff=None,
                          pb=None, rs_map=None):
    """All-bar measurement fork of successor pine_stack.simulate_stack.

    Returns the frozen simulator's result dict with `max_drawdown`
    replaced by the ALL-BAR marked max drawdown, plus:
      event_sampled_max_drawdown, allbar_max_drawdown,
      allbar_equity_series (list of [iso_time, equity] at every event
      time and every union-calendar bar completion in [first event,
      cutoff]).
    All decision outputs (taken, disposition, exit_cashflows,
    final_equity, realized_equity, terminal_open, skip counts,
    exposure) are produced by the identical event-time logic as the
    frozen code.
    """
    if dd_gate:
        raise ValueError(
            "all-bar marking refused with dd_gate=True: the peak feeds "
            "sizing decisions under S4, so extending the marking grid "
            "could alter decisions. Out of scope for a measurement fork.")
    if pb is None:
        import pine_backtest as pb

    ends_cache = {}
    # Fail-closed grid validation: every bar of every series must
    # resolve through the pinned session table before any marking.
    for _sym, _s in closes.items():
        _ends_for(_sym, _s, ends_cache)

    def mark(sym, t):
        # Frozen as-of mark (identical to successor pine_stack.mark):
        # latest bar COMPLETED at or before t, completion = pinned
        # table bin_end.
        s = closes[sym]
        ends = _ends_for(sym, s, ends_cache)
        ii = ends.searchsorted(t, side="right") - 1
        return float(s.iloc[ii]) if ii >= 0 else float(s.iloc[0])

    entries_by_t = defaultdict(list)
    exits_by_t = defaultdict(list)
    for idx, tr in enumerate(all_trades):
        entries_by_t[tr["entry_time"]].append(idx)
        if not tr.get("censored"):
            exits_by_t[tr["exit_time"]].append(idx)
    times = sorted(set(entries_by_t) | set(exits_by_t))

    realized = pb.START_EQUITY
    open_pos, by_id = [], {}
    # Event-sampled track (frozen semantics; only event-time marks).
    peak_e, max_dd_e = realized, 0.0
    # All-bar track (event times + every bar completion).
    peak_a, max_dd_a = realized, 0.0
    series = []
    skipped_rank = skipped_cap = skipped_risk = skipped_gate = 0
    n_half_risk = n_full_risk = 0
    taken = []
    disposition = {}
    exit_cashflows = []
    open_time = total_time = pd.Timedelta(0)
    prev_t = None

    def marked_equity(t):
        unreal = sum(((mark(tr["symbol"], t) - tr["entry"]) / tr["entry"])
                     * p["size"]
                     for p, tr in ((p, p["trade"]) for p in open_pos))
        return realized + unreal

    def mark_allbar(t, kind):
        nonlocal peak_a, max_dd_a
        eq = marked_equity(t)
        peak_a = max(peak_a, eq)
        if peak_a > 0:
            max_dd_a = max(max_dd_a, (peak_a - eq) / peak_a)
        series.append([str(t), eq, kind])
        return eq

    if cutoff is None:
        cutoff_eff = max(_ends_for(sym, s, ends_cache)[-1]
                         for sym, s in closes.items())
    else:
        cutoff_eff = cutoff
    bar_times = _bar_completion_times(closes, times[0], cutoff_eff,
                                      ends_cache) if times else []
    bar_ptr = 0

    bar_time_set = set(bar_times)
    for t in times:
        # Bar completions strictly before this event time: positions
        # are exactly those left by the previous event's processing
        # (no state changes occur between event times).
        while bar_ptr < len(bar_times) and bar_times[bar_ptr] < t:
            mark_allbar(bar_times[bar_ptr], "bar_close")
            bar_ptr += 1
        # The completion AT t (end of the previous bar): positions
        # exiting at t are still open at that close and are valued at
        # the just-completed bar's close BEFORE the exit fill;
        # positions entering at t open at t's bar open, after the
        # close print, and are not yet in this mark. This is the mark
        # the event grid can never see (the frozen loop realizes the
        # exit first).
        if t in bar_time_set:
            mark_allbar(t, "bar_close")
            bar_ptr += 1
        if prev_t is not None and t > prev_t:
            dt = t - prev_t
            total_time += dt
            if open_pos:
                open_time += dt
        prev_t = t
        for idx in sorted(exits_by_t.get(t, [])):
            pos = by_id.pop(id(all_trades[idx]), None)
            if pos is None:
                continue
            tr = all_trades[idx]
            _, _, net_r, _ = pb._outcome(tr["entry"], tr["stop"],
                                         tr["exit"], cost)
            realized += pos["risk_dollars"] * net_r
            open_pos.remove(pos)
            exit_cashflows.append({
                "key": (tr["symbol"], tr.get("signal_idx", -1)),
                "net_r": net_r, "cash_flow": pos["risk_dollars"] * net_r,
                "risk_dollars": pos["risk_dollars"]})
        cands = entries_by_t.get(t, [])
        if cands:
            n_cands_t = len(cands)
            if use_ranking:
                if rs_map is None:
                    raise ValueError(
                        "rs_map is required when use_ranking=True (the "
                        "frozen stack reads the module-global rs map "
                        "set by the driver; the fork takes it "
                        "explicitly)")
                scored = [(-rs_map[id(all_trades[i])],
                           all_trades[i]["symbol"],
                           all_trades[i].get("signal_idx", -1), i)
                          for i in cands]
                scored.sort()
                ordered = [x[-1] for x in scored]
            else:
                ordered = sorted(cands, key=lambda i: (
                    all_trades[i]["symbol"],
                    all_trades[i].get("signal_idx", -1), i))
            taken_at_t = 0
            for idx in ordered:
                tr = all_trades[idx]
                free = pb.MAX_CONCURRENT - len(open_pos)
                contested_now = n_cands_t > free
                if use_ranking and contested_now \
                        and taken_at_t >= min(2, free):
                    skipped_rank += 1
                    disposition[idx] = "skipped_rank"
                    continue
                if free <= 0:
                    skipped_cap += 1
                    disposition[idx] = "skipped_cap"
                    continue
                eq = marked_equity(t)
                if sector_cap:
                    s = sector_map[tr["symbol"]]
                    n_sec = sum(1 for p in open_pos
                                if sector_map[p["trade"]["symbol"]] == s)
                    if n_sec >= 2:
                        skipped_gate += 1
                        disposition[idx] = "skipped_gate"
                        continue
                cur_risk = pb.RISK_PCT
                open_risk = (sum(p["risk_dollars"] for p in open_pos) / eq
                             if eq > 0 else 1)
                if open_risk + cur_risk > pb.MAX_PORTFOLIO_RISK + 1e-9:
                    skipped_risk += 1
                    disposition[idx] = "skipped_risk"
                    continue
                risk_dollars = cur_risk * eq
                risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
                pos = {"trade": tr, "risk_dollars": risk_dollars,
                       "size": risk_dollars / risk_frac,
                       "risk_frac": risk_frac, "risk_pct": cur_risk}
                open_pos.append(pos)
                by_id[id(tr)] = pos
                taken.append(idx)
                disposition[idx] = "taken"
                taken_at_t += 1
                n_full_risk += 1
        eq = marked_equity(t)
        peak_e = max(peak_e, eq)
        if peak_e > 0:
            max_dd_e = max(max_dd_e, (peak_e - eq) / peak_e)
        mark_allbar(t, "event")
    # Terminal segment: bar completions up to the cutoff, then the
    # frozen terminal accounting (taken censored positions only).
    terminal_open = []
    final_equity = realized
    if not open_pos:
        # Flat tail: equity is constant at `realized`; marking the
        # remaining bar completions cannot change either DD track.
        while bar_ptr < len(bar_times) and bar_times[bar_ptr] <= cutoff_eff:
            mark_allbar(bar_times[bar_ptr], "bar_close")
            bar_ptr += 1
    if open_pos:
        assert all(p["trade"].get("censored") for p in open_pos), \
            "non-censored position open after last event"
        if prev_t is not None and cutoff_eff > prev_t:
            dt = cutoff_eff - prev_t
            total_time += dt
            open_time += dt
        while bar_ptr < len(bar_times) and bar_times[bar_ptr] < cutoff_eff:
            mark_allbar(bar_times[bar_ptr], "bar_close")
            bar_ptr += 1
        for p in open_pos:
            tr = p["trade"]
            m = mark(tr["symbol"], cutoff_eff)
            unreal = ((m - tr["entry"]) / tr["entry"]) * p["size"]
            terminal_open.append({
                "symbol": tr["symbol"],
                "signal_idx": tr.get("signal_idx", -1),
                "entry": tr["entry"], "entry_time": str(tr["entry_time"]),
                "risk_dollars": p["risk_dollars"], "size": p["size"],
                "mark": m, "mark_time": str(cutoff_eff),
                "unreal_dollars": unreal})
        final_equity = marked_equity(cutoff_eff)
        peak_e = max(peak_e, final_equity)
        if peak_e > 0:
            max_dd_e = max(max_dd_e, (peak_e - final_equity) / peak_e)
        mark_allbar(cutoff_eff, "event")
    assert max_dd_a >= max_dd_e - 1e-12, \
        f"invariant violated: all-bar DD {max_dd_a} < event DD {max_dd_e}"
    exposure = float(open_time / total_time) \
        if total_time > pd.Timedelta(0) else 0.0
    return {"final_equity": final_equity, "realized_equity": realized,
            "max_drawdown": max_dd_a,
            "event_sampled_max_drawdown": max_dd_e,
            "allbar_max_drawdown": max_dd_a,
            "allbar_equity_series": series,
            "skipped_rank": skipped_rank, "skipped_cap": skipped_cap,
            "skipped_risk": skipped_risk, "skipped_gate": skipped_gate,
            "n_half_risk": n_half_risk, "n_full_risk": n_full_risk,
            "taken": taken, "exposure": exposure,
            "skipped_cap_count": skipped_cap + skipped_rank,
            "skipped_cap_risk": skipped_risk,
            "disposition": disposition, "exit_cashflows": exit_cashflows,
            "terminal_open": terminal_open,
            "cutoff": str(cutoff_eff) if terminal_open else None}


def equity_series_from_intervals(positions, closes, start_equity,
                                 first_t, cutoff):
    """Independent all-bar equity reconstruction from recorded
    intervals.

    positions: list of dicts with symbol, entry, entry_time, exit_time
    (None for censored/terminal), size, exit_cash_flow (None for
    censored). Marks every union-calendar bar completion (pinned
    table bin ends) in [first_t, cutoff] plus the cutoff itself,
    using the frozen as-of mark. Boundary semantics match the fork's
    bar_close marks: at a completion tau, an exit with exit_time ==
    tau has NOT yet realized (the position is valued at the
    just-completed bar's close, before its fill at tau's bar open);
    an entry with entry_time == tau has NOT yet opened. Returns
    (series, max_drawdown).
    """
    ends_cache = {}
    for _sym, _s in closes.items():
        _ends_for(_sym, _s, ends_cache)

    def mark(sym, t):
        s = closes[sym]
        ends = _ends_for(sym, s, ends_cache)
        ii = ends.searchsorted(t, side="right") - 1
        return float(s.iloc[ii]) if ii >= 0 else float(s.iloc[0])

    grid = set(_bar_completion_times(closes, first_t, cutoff,
                                     ends_cache))
    grid.add(cutoff)
    series = []
    peak, max_dd = start_equity, 0.0
    for tau in sorted(grid):
        realized = start_equity + sum(
            p["exit_cash_flow"] for p in positions
            if p["exit_time"] is not None and p["exit_time"] < tau)
        unreal = 0.0
        for p in positions:
            if p["entry_time"] < tau and \
                    (p["exit_time"] is None or tau <= p["exit_time"]):
                unreal += ((mark(p["symbol"], tau) - p["entry"])
                           / p["entry"]) * p["size"]
        eq = realized + unreal
        series.append([str(tau), eq])
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    return series, max_dd
