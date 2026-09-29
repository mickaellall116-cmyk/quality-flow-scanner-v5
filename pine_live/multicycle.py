"""Slice-4/5 multi-symbol live cycle — one canonical cycle across all symbols.

Paper-only. Zero trading, zero real alerts.

One canonical cycle for one 4H bar_time:

    symbols -> per-symbol frame -> slice-1 assertions -> canonical
    pine_buy_signal (decision from the reference, decomposition for the
    packet) -> contenders -> slice-5 live exit evaluation (pure canonical
    walk per open position; exits-before-entries) -> slice-2 portfolio path
    (ranking -> sector cap -> 5% risk gate, locked branch order) ->
    slice-1/slice-5 packets -> slice-3 dedup + paper alerts (downstream
    only).

The per-timestamp engine is cycle.run_timestamp (slice 3); this module is
the multi-symbol fan-out in front of it. Causal separation is preserved:
multicycle.py may READ from the decision path but the delivery layers
(dedup.py, alerts.py — stdlib only, proven by the slice-3 import-graph
test) cannot reach back into it. A symbol that fails assertions or whose
frame cannot be obtained is SKIPPED with a logged reason — never evaluated
on bad data, and never poisoning the rest of the cycle. Exit evaluation
is fail-closed per position for the same reason: a position whose walk
cannot be evaluated stays open, the failure is logged, and the rest of
the cycle proceeds.

Exit/entry ordering (locked): live exits are evaluated AFTER the contender
loop and BEFORE run_timestamp, so exits free slots, sector capacity, and
risk budget for this timestamp's entries. Exits cannot alter entry
decisions retroactively — the entry path (qualification, ranking, reason
codes) is byte-identical whether exits come from live evaluation or from
externally supplied exit events (proven by test).

Reference-behavior pin (discovered slice 4, proven by sweep + full-window
replay): within ONE timestamp, RANKED_OUT and RISK_CAP are mutually
exclusive under the locked branch order. A veto freezes taken_at_t at k
with k < min(2, free); any later ranked-out would need k >= min(2, free)
at the same free (no takes can happen after a veto — heat only rises).
The contested scenario therefore exercises the four layers across two
crafted timestamps in one scenario run; see SLICE4.md and
test_four_layer_contested_scenario.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pine_backtest as pb  # noqa: E402  (canonical TP_ATR)
from pine_live.live_path import evaluate_frame  # noqa: E402
from pine_live.ranking import rs_score  # noqa: E402
from pine_live.exits import evaluate_position_exit, ExitEvaluationError  # noqa: E402
from pine_live.assertions import assert_valid_bars, assert_no_forming_bar  # noqa: E402
from pine_live.cycle import (  # noqa: E402
    _append_jsonl,
    _utcnow_iso,
    paper_sender,
    run_timestamp,
)
from pine_live.dedup import DedupStore  # noqa: E402
from pine_live.alerts import PaperOutbox  # noqa: E402
from pine_live.packets import (  # noqa: E402
    PacketLog,
    append_exit_packet,
    build_exit_packet,
    engine_with_extra_files,
    write_exit_bars_snapshot,
)
from pine_live.portfolio import PortfolioState  # noqa: E402


def default_frame_provider(symbol: str, period: str = "1y"):
    """Live frame provider: the reference download path (masterscanner_api),
    the ONLY network call, imported lazily so tests never touch it."""
    from masterscanner_api import download_data

    return download_data(symbol, "4h", period)


def _log_cycle_event(cycle_log_path, event: dict) -> None:
    if cycle_log_path is None:
        return
    rec = dict(event)
    rec["at"] = _utcnow_iso()
    _append_jsonl(cycle_log_path, rec)


def _check_exit_events_wellformed(events: list) -> None:
    """Defensive validation of generated exit events before the engine sees
    them. Raises ValueError naming the problem — the caller fails the
    timestamp closed (state untouched) instead of handing a malformed
    event to process_exits."""
    import math
    for e in events:
        missing = [k for k in ("symbol", "exit_px", "reason",
                               "universe_order")
                   if k not in e]
        if missing:
            raise ValueError(
                f"malformed exit event for {e.get('symbol', '?')}: "
                f"missing keys {missing}")
        px = e["exit_px"]
        if not isinstance(px, (int, float)) or not math.isfinite(float(px)):
            raise ValueError(
                f"malformed exit event for {e['symbol']}: "
                f"non-finite exit_px {px!r}")
        if float(px) <= 0:
            raise ValueError(
                f"malformed exit event for {e['symbol']}: "
                f"non-positive exit_px {px!r}")


def _log_sizes(paths: list) -> dict:
    """Snapshot current file sizes of append-only logs (for rollback)."""
    sizes = {}
    for p in paths:
        if p:
            try:
                sizes[p] = os.path.getsize(p)
            except OSError:
                sizes[p] = 0
    return sizes


def _rollback_logs(sizes: dict) -> None:
    """Truncate append-only logs back to their snapshotted sizes."""
    for p, size in sizes.items():
        try:
            with open(p, "r+b") as f:
                f.truncate(size)
        except OSError:
            pass  # rollback is best-effort on the logs; state is primary


def _restore_state(state: PortfolioState, before: dict, mark_fn) -> None:
    """Restore portfolio state from a to_dict() snapshot (in place)."""
    restored = PortfolioState.from_dict(before, mark_fn)
    state.__dict__.clear()
    state.__dict__.update(restored.__dict__)


def _exit_walk_records(symbol: str, ind: pd.DataFrame,
                       entry_idx: int, trigger_idx: int) -> list:
    """Build the hash-pinned bar records for an exit walk's bars."""
    walk = ind.iloc[entry_idx:trigger_idx + 1]
    return [
        {"t": ts.isoformat(),
         "o": float(row["Open"]), "h": float(row["High"]),
         "l": float(row["Low"]), "c": float(row["Close"]),
         "v": float(row["Volume"]),
         "e21": float(row["e21"]), "e55": float(row["e55"]),
         "e200": float(row["e200"]), "atr": float(row["atr"])}
        for ts, row in walk.iterrows()
    ]


def _evaluate_live_exits(*, state: PortfolioState, t: pd.Timestamp,
                         provider, frames: dict, signal_bar: str, now,
                         snapshot_dir: str, cycle_log_path) -> tuple:
    """Evaluate the canonical V3.6 exit walk for every open position.

    Pure evaluation only: no state is mutated here. Returns
    ``(exit_events, pending, report)`` where ``exit_events`` are
    process_exits-ready events in canonical (sorted-symbol) order and
    ``pending`` carries everything needed to write the exit packet AFTER
    the timestamp engine applies the exits — so a refused timestamp
    leaves no orphan exit packets. A position whose walk cannot be
    evaluated is skipped (fail closed: it stays open), the failure is
    logged, and the rest of the cycle proceeds.

    The exact pre-timestamp portfolio state (full ``to_dict()``) is
    captured once; the finalizer derives each exit's sequential
    pre/post state from it plus the engine's close events, so multiple
    exits at one timestamp each pin the book immediately before/after
    THAT exit — never the batch average.
    """
    exit_events: list = []
    pending: list = []
    report = {"evaluated": [], "skipped": [], "n_exits": 0}
    ind_cache: dict = {}

    pre_timestamp_state = state.to_dict()
    for symbol in sorted(state.positions):
        pos = state.positions[symbol]
        try:
            bars = frames.get(symbol)
            if bars is None:
                bars = provider(symbol)
            # Input gates, same as the entry path (slice-1 assertions).
            assert_valid_bars(symbol, bars)
            if now is not None:
                assert_no_forming_bar(symbol, bars, now)
            if symbol not in ind_cache:
                ind_cache[symbol] = pb.add_pine_indicators(bars)
            ind = ind_cache[symbol]
            bar_tz = bars.index.tz
            loc = int(bars.index.get_loc(t.tz_convert(bar_tz)))
            entry_idx = int(ind.index.get_loc(
                pd.Timestamp(pos["entry_time"]).tz_convert(bar_tz)))
            eval_end = loc - 1 if signal_bar == "previous" else loc
            res = evaluate_position_exit(
                symbol=symbol, entry_px=pos["entry_px"],
                stop_px=pos["stop_px"], tp1_px=pos["tp1_px"],
                entry_idx=entry_idx, ind=ind, eval_end_idx=eval_end)
        except Exception as exc:  # noqa: BLE001 — fail closed per position
            report["skipped"].append({
                "symbol": symbol, "reason": "exit_evaluation_failed",
                "error": f"{type(exc).__name__}: {exc}"})
            _log_cycle_event(cycle_log_path, {
                "event": "exit_evaluation_failed", "symbol": symbol,
                "signal_id": pos.get("signal_id"),
                "bar_time": t.isoformat(),
                "error_type": type(exc).__name__, "error": str(exc)})
            continue
        report["evaluated"].append({
            "symbol": symbol, "signal_id": pos.get("signal_id"),
            "triggered": bool(res["triggered"]),
            "n_bars_walked": res["n_bars_walked"]})
        if not res["triggered"]:
            continue
        # Snapshot the bars the exit decision depends on: the walked bars
        # through the trigger bar PLUS the fill bar (next-bar open). Replay
        # re-runs the walk over this snapshot and must reproduce the fill
        # exactly, so the fill bar has to be in it.
        records = _exit_walk_records(symbol, ind, res["entry_idx"],
                                     res["fill_idx"])
        snap = write_exit_bars_snapshot(symbol, records, snapshot_dir,
                                        index_tz=str(ind.index.tz))
        exit_events.append({
            "symbol": symbol,
            "exit_px": res["exit_px"],
            "reason": res["reason"],
            "exit_time": res["fill_bar_time"],
            "trigger_bar_time": res["trigger_bar_time"],
        })
        pending.append({
            "symbol": symbol, "position": dict(pos), "evaluation": res,
            "snapshot_ref": snap,
            "pre_timestamp_state": pre_timestamp_state,
        })
    # Canonical order: sorted symbols — input/position order cannot affect
    # outcomes.
    exit_events.sort(key=lambda e: e["symbol"])
    for uo, ev in enumerate(exit_events):
        ev["universe_order"] = uo
    pending.sort(key=lambda p: p["symbol"])
    report["n_exits"] = len(exit_events)
    return exit_events, pending, report


def _finalize_exit_packets(*, pending: list, state: PortfolioState,
                           t: pd.Timestamp, t_iso: str, cost: float,
                           exit_packet_log: str, vintage: dict, engine: dict,
                           cycle_log_path) -> int:
    """Write slice-5 exit packets for exits the engine actually applied.

    Each packet pins the exact portfolio state immediately before THAT
    exit (``pre_exit_state``) and immediately after it
    (``post_exit_state``), derived from the pre-timestamp state plus the
    engine's own close events in application order. ``net_r`` and the
    per-exit ``realized_after`` are read from the close events (ground
    truth), not recomputed prospectively. An exit with no matching close
    event is logged and skipped — never guessed. Returns the number of
    packets written.
    """
    import copy
    close_by_symbol = {}
    for e in state.events:
        if (e.get("kind") == "close" and e.get("t") == t_iso
                and e.get("symbol") not in close_by_symbol):
            close_by_symbol[e["symbol"]] = e
    engine_x = engine_with_extra_files(engine or {}, ("exits.py",))
    # Engine application order == pending order (sorted symbols with
    # universe_order assigned sequentially; process_exits sorts by it).
    applied = [(p, close_by_symbol[p["symbol"]]) for p in pending
               if p["symbol"] in close_by_symbol]
    for p in pending:
        if p["symbol"] not in close_by_symbol:
            _log_cycle_event(cycle_log_path, {
                "event": "exit_packet_skipped", "symbol": p["symbol"],
                "bar_time": t_iso, "reason": "no_matching_close_event"})
    n = 0
    for j, (p, close_ev) in enumerate(applied):
        base = p["pre_timestamp_state"]
        # Sequential pre-exit state: the timestamp-start book minus the
        # earlier exits at this timestamp, with their close events.
        # process_exits only touches positions/realized/events/seq, so
        # peak, max_dd, counters, and clock carry over unchanged.
        pre_state = copy.deepcopy(base)
        for i in range(j):
            sym_i, close_i = applied[i][0]["symbol"], applied[i][1]
            pre_state["positions"].pop(sym_i, None)
            pre_state["events"].append(copy.deepcopy(close_i))
        pre_state["realized"] = float(
            applied[j - 1][1]["realized_after"] if j > 0 else base["realized"])
        pre_state["seq"] = int(base["seq"]) + j
        # Sequential post-exit state: pre_state plus exactly this exit.
        post_state = copy.deepcopy(pre_state)
        post_state["positions"].pop(p["symbol"], None)
        post_state["realized"] = float(close_ev["realized_after"])
        post_state["events"].append(copy.deepcopy(close_ev))
        post_state["seq"] = int(pre_state["seq"]) + 1
        res = p["evaluation"]
        packet = build_exit_packet(
            decision_time=t_iso, computed_at=_utcnow_iso(), cost=cost,
            position=p["position"],
            evaluation={
                "entry_idx": res["entry_idx"],
                "eval_end_idx": res["eval_end_idx"],
                "trigger_idx": res["trigger_idx"],
                "fill_idx": res["fill_idx"],
                "n_bars_walked": res["n_bars_walked"],
                "n_snapshot_bars": p["snapshot_ref"]["n_bars"],
            },
            trigger={
                "trigger_bar_time": res["trigger_bar_time"],
                "fill_bar_time": res["fill_bar_time"],
                "fill_px": res["fill_px"],
                "reason": res["reason"],
                "tp1_hit": res["tp1_hit"],
                "runner_at_trigger": res["runner_at_trigger"],
            },
            exit_detail={
                "exit_px": res["exit_px"],
                "r1": res["r1"], "r2": res["r2"],
                "r_blend": res["r_blend"], "risk_frac": res["risk_frac"],
                "net_r": close_ev["net_r"],
                "hold_bars": res["hold_bars"],
            },
            pre_exit_state=pre_state,
            post_exit_state=post_state,
            realized_after=close_ev["realized_after"],
            snapshot_ref=p["snapshot_ref"],
            vintage=vintage, engine=engine_x)
        append_exit_packet(exit_packet_log, packet)
        n += 1
    return n


def run_cycle(*, symbols, bar_time, state: PortfolioState, mark_fn,
              packet_log: PacketLog, snapshot_dir: str, vintage: dict,
              engine: dict | None = None,
              dedup_store: DedupStore | None = None,
              outbox: PaperOutbox | None = None,
              delivery_log_path: str | None = None,
              sender=paper_sender,
              actions_log_path: str | None = None,
              cycle_log_path: str | None = None,
              frame_provider=None,
              spy_daily=None,
              now=None,
              exits: list | None = None,
              live_exits: bool = False,
              exit_packet_log: str | None = None,
              signal_bar: str = "previous") -> dict:
    """Run one canonical multi-symbol cycle for one 4H bar_time.

    bar_time is the DECISION time (the bar whose open triggers the cycle).
    signal_bar selects which closed bar is evaluated per symbol:
      - "previous" (default): the bar immediately before bar_time's bar.
        This is the canonical live semantic — the cycle runs at a bar open,
        evaluates the just-closed bar through the reference path, and enters
        at the known open. It is also the research-replay semantic: the
        reference decides entries at entry_time using the signal bar whose
        next open is entry_time.
      - "at": the bar at bar_time itself (evaluate-latest-closed-bar); entry
        is the next bar's open when in frame, else the signal is logged as
        entry-pending (the reference enters at next-bar open, which does not
        exist yet — no portfolio decision is made for it now).

    symbols: iterable of symbols (any order, any case; canonicalized
        internally — input order cannot affect outcomes).
    bar_time: tz-aware decision timestamp (the bar whose open triggers the
        cycle; must be present in each symbol's frame).
    frame_provider: symbol -> 4H DataFrame (tz-aware). Defaults to the live
        download path. Tests inject cached frames. A provider exception for
        one symbol logs a skip; the rest of the cycle proceeds.
    spy_daily: daily SPY frame for rs_score, or None (score -> -inf with a
        logged reason, never silent — parity spec A8).
    now: as-of time for the forming-bar assertion (live). None skips it
        (historical replay).
    exits: externally supplied exit events (slice-2/4 behavior).
    live_exits: evaluate exits from the canonical V3.6 walk (slice 5)
        instead of consuming external exit events. Exclusive with
        ``exits``. Requires ``exit_packet_log``.
    exit_packet_log: path of the slice-5 exit packet JSONL log. Every
        applied live exit gets an fsync'd replayable packet (pre-exit
        position, hash-pinned bar snapshot, close-event ground truth).

    Returns a cycle report. Never raises for per-symbol failures (they are
    logged skips). Raises ValueError for a naive bar_time (caller error).
    """
    t = pd.Timestamp(bar_time)
    if t.tzinfo is None:
        raise ValueError(f"run_cycle: naive bar_time rejected: {bar_time!r}")
    if signal_bar not in ("previous", "at"):
        raise ValueError(f"run_cycle: signal_bar must be 'previous' or 'at', "
                         f"got {signal_bar!r}")
    if live_exits and exits:
        raise ValueError(
            "run_cycle: live_exits=True is exclusive with externally "
            "supplied exits")
    if live_exits and not exit_packet_log:
        raise ValueError(
            "run_cycle: live_exits=True requires exit_packet_log")

    ordered_symbols = sorted({str(s).upper() for s in symbols})
    provider = frame_provider or default_frame_provider

    report = {
        "bar_time": t.isoformat(),
        "n_symbols": len(ordered_symbols),
        "evaluated": [],
        "skipped": [],
        "signals": [],
        "pending_entry": [],
        "contenders": [],
    }

    contenders = []
    frames: dict = {}
    for uo, symbol in enumerate(ordered_symbols):
        # --- frame ------------------------------------------------------
        try:
            bars = provider(symbol)
        except Exception as exc:  # noqa: BLE001 — one bad symbol never poisons the cycle
            report["skipped"].append({"symbol": symbol,
                                     "reason": "frame_provider_failed",
                                     "error": f"{type(exc).__name__}: {exc}"})
            _log_cycle_event(cycle_log_path, {
                "event": "symbol_skipped", "symbol": symbol,
                "bar_time": t.isoformat(), "reason": "frame_provider_failed",
                "error_type": type(exc).__name__, "error": str(exc)})
            continue
        frames[symbol] = bars
        try:
            loc = int(bars.index.get_loc(t.tz_convert(bars.index.tz)))
        except KeyError:
            report["skipped"].append({"symbol": symbol,
                                     "reason": "bar_time_not_in_frame"})
            _log_cycle_event(cycle_log_path, {
                "event": "symbol_skipped", "symbol": symbol,
                "bar_time": t.isoformat(), "reason": "bar_time_not_in_frame"})
            continue
        if signal_bar == "previous":
            if loc < 1:
                report["skipped"].append({"symbol": symbol,
                                         "reason": "no_prior_bar"})
                _log_cycle_event(cycle_log_path, {
                    "event": "symbol_skipped", "symbol": symbol,
                    "bar_time": t.isoformat(), "reason": "no_prior_bar"})
                continue
            sig_idx, entry_idx = loc - 1, loc
        else:
            sig_idx, entry_idx = loc, loc + 1

        # --- slice-1 evaluation (assertions inside; refusal -> skip) -----
        packet = evaluate_frame(symbol, bars, vintage, packet_log,
                                snapshot_dir, bar_index=sig_idx, now=now)
        ev = {"symbol": symbol, "decision": packet.get("decision"),
              "signal_id": packet.get("signal_id")}
        report["evaluated"].append(ev)
        if packet.get("decision") == "refused":
            report["skipped"].append({
                "symbol": symbol, "reason": "evaluation_refused",
                "refused_reason": packet.get("refused_reason")})
            _log_cycle_event(cycle_log_path, {
                "event": "symbol_skipped", "symbol": symbol,
                "bar_time": t.isoformat(), "reason": "evaluation_refused",
                "refused_reason": packet.get("refused_reason")})
            continue
        if packet.get("decision") != "signal":
            continue

        # --- signal -> contender ---------------------------------------
        n_bars = len(bars)
        if entry_idx >= n_bars:
            # Next bar not in frame (live terminal bar in "at" mode): the
            # reference enters at next-bar open, which does not exist yet.
            # The signal packet is logged; no portfolio decision is made
            # for it now.
            report["pending_entry"].append(ev)
            _log_cycle_event(cycle_log_path, {
                "event": "signal_pending_entry", "symbol": symbol,
                "signal_id": packet.get("signal_id"),
                "bar_time": t.isoformat(),
                "reason": "entry_pending_next_open"})
            continue
        entry_px = float(bars["Open"].iloc[entry_idx])
        stop_px = float(packet["entry_plan"]["stop_px"])
        if entry_px <= stop_px:
            # Mirrors the reference's skipped_gap guard (gen_candidates):
            # never take a trade whose entry is already through the stop.
            report["skipped"].append({"symbol": symbol,
                                     "reason": "entry_through_stop"})
            _log_cycle_event(cycle_log_path, {
                "event": "symbol_skipped", "symbol": symbol,
                "signal_id": packet.get("signal_id"),
                "bar_time": t.isoformat(), "reason": "entry_through_stop"})
            continue
        atr_i = packet["indicators_at_i"]["atr"]
        score, rs_reason = rs_score(bars, sig_idx, spy_daily)
        contender = {
            "signal_id": packet["signal_id"],
            "symbol": symbol,
            "entry_px": entry_px,
            "stop_px": stop_px,
            # Reference tp1 = next-bar entry + 2.0*ATR (signal bar's ATR).
            "tp1_px": float(entry_px + float(atr_i) * pb.TP_ATR),
            "rs_score": float(score),
            "rs_unavailable": rs_reason is not None,
            "rs_unavailable_reason": rs_reason,
            # Canonical order: sorted symbols, never input order.
            "universe_order": uo,
        }
        if rs_reason is not None:
            _log_cycle_event(cycle_log_path, {
                "event": "rs_unavailable", "symbol": symbol,
                "signal_id": packet.get("signal_id"),
                "bar_time": t.isoformat(), "reason": rs_reason})
        contenders.append(contender)
        report["signals"].append(ev)
    report["contenders"] = [
        {"signal_id": c["signal_id"], "symbol": c["symbol"],
         "rs_score": c["rs_score"], "universe_order": c["universe_order"]}
        for c in contenders
    ]

    # --- slice-5 live exit evaluation (exits before entries) ------------
    # Evaluated AFTER the contender loop, BEFORE the timestamp engine, so
    # exits free slots / sector capacity / risk budget for this
    # timestamp's entries. The entry path itself is untouched: qualification,
    # ranking, and reason codes are identical whether exits come from live
    # evaluation or external events.
    live_exit_events: list = []
    pending_exit_packets: list = []
    before_state: dict | None = None
    log_sizes: dict = {}
    if live_exits:
        live_exit_events, pending_exit_packets, exit_rep = _evaluate_live_exits(
            state=state, t=t, provider=provider, frames=frames,
            signal_bar=signal_bar, now=now, snapshot_dir=snapshot_dir,
            cycle_log_path=cycle_log_path)
        report["live_exits"] = exit_rep
        # The timestamp is atomic (criterion 8): malformed generated
        # events, engine exceptions, or exit-packet failures fail closed —
        # state and the append-only logs are restored, the failure is
        # logged, and no partially applied exit is ever left behind.
        try:
            _check_exit_events_wellformed(live_exit_events)
        except ValueError as exc:
            _log_cycle_event(cycle_log_path, {
                "event": "timestamp_failed_closed",
                "bar_time": t.isoformat(),
                "reason": f"malformed_exit_event: {exc}"})
            report["timestamp"] = {"t": t.isoformat(),
                                   "status": "failed_closed",
                                   "reason": f"malformed_exit_event: {exc}"}
            report["exit_packets"] = 0
            return report
        before_state = state.to_dict()
        log_sizes = _log_sizes([
            packet_log.path,
            getattr(dedup_store, "path", None),
            getattr(outbox, "path", None),
            delivery_log_path, actions_log_path, cycle_log_path,
            exit_packet_log])

    # --- the slice-3 per-timestamp engine (decide -> packet -> dedup) ---
    try:
        ts_rep = run_timestamp(
            state=state, mark_fn=mark_fn, t=t, contenders=contenders,
            exits=live_exit_events if live_exits else list(exits or []),
            packet_log=packet_log, vintage=vintage,
            engine=engine, dedup_store=dedup_store, outbox=outbox,
            delivery_log_path=delivery_log_path, sender=sender,
            actions_log_path=actions_log_path)
    except Exception as exc:  # noqa: BLE001 — fail closed, never half-applied
        if live_exits:
            _restore_state(state, before_state, mark_fn)
            _rollback_logs(log_sizes)
            _log_cycle_event(cycle_log_path, {
                "event": "timestamp_failed_closed",
                "bar_time": t.isoformat(),
                "reason": (f"timestamp_engine_exception: "
                           f"{type(exc).__name__}: {exc}")})
            report["timestamp"] = {
                "t": t.isoformat(), "status": "failed_closed",
                "reason": (f"timestamp_engine_exception: "
                           f"{type(exc).__name__}: {exc}")}
            report["exit_packets"] = 0
            return report
        raise
    report["timestamp"] = ts_rep

    # --- slice-5 exit packets (only for exits actually applied) ---------
    # Written AFTER the engine: a refused timestamp rolls exits back, so no
    # exit packet may exist for exits that never happened. A packet-write
    # failure rolls the whole timestamp back (all-or-nothing): the next
    # cycle re-walks the pure exit function and retries.
    n_exit_packets = 0
    if live_exits:
        if ts_rep.get("status") == "refused":
            _log_cycle_event(cycle_log_path, {
                "event": "exits_evaluated_but_timestamp_refused",
                "bar_time": t.isoformat(),
                "n_exits_evaluated": len(live_exit_events)})
        else:
            try:
                n_exit_packets = _finalize_exit_packets(
                    pending=pending_exit_packets, state=state, t=t,
                    t_iso=t.isoformat(), cost=state.cost,
                    exit_packet_log=exit_packet_log, vintage=vintage,
                    engine=engine, cycle_log_path=cycle_log_path)
            except Exception as exc:  # noqa: BLE001 — fail closed
                _restore_state(state, before_state, mark_fn)
                _rollback_logs(log_sizes)
                _log_cycle_event(cycle_log_path, {
                    "event": "timestamp_failed_closed",
                    "bar_time": t.isoformat(),
                    "reason": (f"exit_packet_failure: "
                               f"{type(exc).__name__}: {exc}")})
                report["timestamp"] = {
                    "t": t.isoformat(), "status": "failed_closed",
                    "reason": (f"exit_packet_failure: "
                               f"{type(exc).__name__}: {exc}")}
                report["exit_packets"] = 0
                return report
        report["exit_packets"] = n_exit_packets
    return report
