"""Paper-phase wake-up runner: one invocation = one wake-up.

Usage:
    cd ~/workspace/quality-flow-scanner-v5
    python -m pine_live.paper.runner [--state-dir pine_live/paper_state]

Paper ONLY. No orders, no broker, no real money. Alerts go through
PaperOutbox with paper_sender — a local file append; VERIFIED by reading
pine_live/alerts.py: paper_sender() returns True and records nothing
external, deliver_pending() only writes local JSONL logs. Nothing in this
module can reach Mike's phone/chat/email.

One wake-up:
  1. HALT file present -> log + exit 0 (clearing HALT is human-only).
  2. Download fresh 4H bars for all 51 UNIVERSE_X symbols through a caching
     provider (one download per symbol per wake-up; the cycle's exit path
     re-calls provider(symbol) and the cache absorbs it with zero extra
     network). SPY daily 1y downloaded once for rs_score; on failure the
     run proceeds with rs_score -> -inf + logged reason (parity spec A8).
  3. First run ever: set each watermark to the latest bar open and run NO
     cycles (paper starts now; history is never backfilled as paper).
  4. New-bar detection per symbol (bar open > watermark), grouped by
     distinct bar open time t, chronological.
  5. For each t: run_cycle(..., signal_bar="previous", live_exits=True)
     with dedup + outbox + paper_sender, then classify exit-eval skips
     (misaligned = expected; aligned = HALT), update watermarks, ledger,
     and replay-verify every new packet (any mismatch = HALT, non-zero).
  6. Persist state (atomic, fsync), write status.json + the three-question
     report.

Exit codes: 0 = ok (or already halted); 1 = usage error; 2 = halted this
wake-up (HALT written; see the HALT file + status.json).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from collections import defaultdict
from datetime import datetime, timezone

import pandas as pd

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pine_backtest as pb  # noqa: E402  (frozen params + _outcome)
from pine_live.alerts import PaperOutbox, paper_sender  # noqa: E402
from pine_live.cycle import _append_jsonl, _utcnow_iso  # noqa: E402
from pine_live.dedup import DedupStore  # noqa: E402
from pine_live.multicycle import default_frame_provider, run_cycle  # noqa: E402
from pine_live.packets import PacketLog  # noqa: E402
from pine_live.portfolio import PortfolioState, reference_mark  # noqa: E402
from pine_live.sector import sector_of  # noqa: E402
from pine_live.paper import state as st  # noqa: E402
from pine_live.paper import dual as dual_ledger  # noqa: E402  (read-only
# achievable-fill measurement; never touches strategy/parameters)
from pine_live.paper.ledger import Ledger, read_new_jsonl, read_jsonl  # noqa: E402
from pine_live.paper.report import write_report  # noqa: E402
from pine_live.paper.verify import (  # noqa: E402
    halt_path,
    is_halted,
    verify_wake_up,
    write_halt,
)

FROZEN_COST = pb.COSTS["4bps"]  # primary leg; ledger also tracks 25bps
COST_25BPS = pb.COSTS["25bps"]
MAX_DOWNLOAD_FAILURES = 5  # consecutive wake-ups before a symbol is flagged
STATE_SCHEMA = "paper-status-v1"


# ------------------------------------------------------------ provider ----
class CachingProvider:
    """Wraps default_frame_provider: one download per symbol per wake-up.

    The cycle's exit path calls provider(symbol) again for positions whose
    symbol is not in the cycle's symbol list — the cache absorbs that with
    zero extra network. A download failure raises to the caller (the
    runner fails that symbol closed); it is NOT cached, so a retry next
    wake-up re-attempts the download.
    """

    def __init__(self, inner=None):
        self._inner = inner or default_frame_provider
        self.cache: dict = {}

    def __call__(self, symbol: str) -> pd.DataFrame:
        s = str(symbol).upper()
        if s not in self.cache:
            self.cache[s] = self._inner(s)
        return self.cache[s]


# ------------------------------------------------------------------ runner
class WakeUp:
    def __init__(self, state_dir: str, provider=None):
        self.state_dir = os.path.abspath(state_dir)
        self.paths = {
            "packet_log": os.path.join(self.state_dir, "packets.jsonl"),
            "exit_packet_log": os.path.join(self.state_dir,
                                            "exit_packets.jsonl"),
            "snapshot_dir": os.path.join(self.state_dir, "snapshots"),
            "dedup": os.path.join(self.state_dir, "dedup.jsonl"),
            "outbox": os.path.join(self.state_dir, "outbox.jsonl"),
            "delivery_log": os.path.join(self.state_dir, "delivery.jsonl"),
            "actions_log": os.path.join(self.state_dir, "actions.jsonl"),
            "cycle_log": os.path.join(self.state_dir, "cycle_log.jsonl"),
            "ledger_dir": os.path.join(self.state_dir, "ledger"),
        }
        self.provider = CachingProvider(provider)
        self.ledger = Ledger(self.paths["ledger_dir"])
        self.flags: list = []
        self.cycle_records: list = []
        self.packets_replayed = 0
        self.replay_mismatches = 0

    # ------------------------------------------------------------- logging
    def log(self, event: dict) -> None:
        _append_jsonl(self.paths["cycle_log"], event)

    # ------------------------------------------------------------ download
    def download_all(self, symbols: list) -> tuple[dict, dict]:
        """Download every symbol. Returns (frames, failures).

        A per-symbol failure is fail-closed: the symbol sits out this
        wake-up (no evaluation, no exit walk) and the failure is logged;
        the rest of the wake-up proceeds. Consecutive failures are
        tracked in download_health.json and flagged at >= 5.
        """
        frames, failures = {}, {}
        health = st.load_health(self.state_dir)
        for sym in symbols:
            try:
                fr = self.provider(sym)
                if fr is None or len(fr) == 0:
                    # An empty frame is a download failure, not a usable
                    # symbol: fail closed per symbol (no evaluation, no
                    # exit walk) so downstream index[-1]/index[0] access
                    # can't raise on zero bars.
                    raise RuntimeError("empty frame: provider returned "
                                       "no bars")
                frames[sym] = fr
                health[sym] = 0
            except Exception as exc:  # noqa: BLE001 — fail closed per symbol
                failures[sym] = f"{type(exc).__name__}: {exc}"
                health[sym] = int(health.get(sym, 0)) + 1
                self.log({"event": "download_failed", "symbol": sym,
                          "error_type": type(exc).__name__,
                          "error": str(exc),
                          "consecutive_failures": health[sym]})
                if health[sym] >= MAX_DOWNLOAD_FAILURES:
                    self.flags.append(
                        f"download_failed_5x:{sym} "
                        f"({health[sym]} consecutive wake-ups)")
        st.save_health(self.state_dir, health)
        return frames, failures

    def download_spy(self):
        """Daily SPY for rs_score. None on failure (A8 fallback)."""
        try:
            from masterscanner_api import download_data
            spy = download_data("SPY", "1d", "1y")
            if spy is None or len(spy) == 0:
                raise RuntimeError("empty SPY frame")
            if isinstance(spy.index, pd.DatetimeIndex) and spy.index.tz is None:
                # yfinance daily bars arrive tz-naive; crypto 4h frames are
                # UTC-aware. Normalize the benchmark to UTC so bench_ret's
                # searchsorted comparisons can't raise tz-naive/tz-aware.
                spy.index = spy.index.tz_localize("UTC")
            return spy
        except Exception as exc:  # noqa: BLE001 — A8 fallback, never silent
            self.log({"event": "spy_download_failed",
                      "error_type": type(exc).__name__, "error": str(exc),
                      "fallback": "rs_score -> -inf with logged reason"})
            self.flags.append("spy_unavailable_rs_minus_inf")
            return None

    # -------------------------------------------------------------- cycles
    def _mark_fn(self, frames: dict):
        closes = {s: f["Close"] for s, f in frames.items()}

        def _mark(symbol: str, t) -> float:
            return reference_mark(closes, symbol, t)

        return _mark

    def _vintage(self, frames: dict, failures: dict, spy) -> dict:
        per_symbol = {}
        for sym, fr in frames.items():
            per_symbol[sym] = {
                "bars_source": "yfinance",
                "bars_downloaded_at": _utcnow_iso(),
                "n_bars": len(fr),
                "first_bar_start": fr.index[0].isoformat(),
                "last_bar_start": fr.index[-1].isoformat(),
            }
        return {
            "engine": "paper-runner-v1",
            "bars_source": "yfinance",
            "bars_downloaded_at": _utcnow_iso(),
            "per_symbol": per_symbol,
            "download_failures": sorted(failures),
            "spy_daily": ("unavailable: rs_score -> -inf (logged per signal)"
                          if spy is None else {
                              "source": "yfinance",
                              "downloaded_at": _utcnow_iso(),
                              "n_bars": len(spy),
                              "last_daily_bar": spy.index[-1].isoformat(),
                          }),
        }

    def _exit_skip_aligned(self, symbol: str, t: pd.Timestamp,
                           frames: dict) -> bool:
        """True if the symbol's cached frame has a bar opening at t."""
        fr = frames.get(symbol)
        if fr is None:
            return False
        try:
            t_loc = t.tz_convert(fr.index.tz)
        except Exception:  # noqa: BLE001 — tz conversion failure: not aligned
            return False
        return bool((fr.index == t_loc).any())

    # --------------------------------- dual-ledger helpers (read-only) --
    def _achievable_entry_for(self, signal_id: str) -> float | None:
        """Achievable entry fill (signal-bar close) for a closing trade.

        Primary source: the entry fill record already in ledger/fills.jsonl
        (written at entry time from the pinned signal packet). Fallback:
        scan packets.jsonl for the signal packet. None when neither has
        it -- the caller records nulls and logs loudly.
        """
        if not signal_id:
            return None
        try:
            for rec in read_jsonl(os.path.join(self.paths["ledger_dir"],
                                               "fills.jsonl")):
                if (rec.get("kind") == "entry"
                        and rec.get("signal_id") == signal_id):
                    px = rec.get("achievable_fill_px")
                    if isinstance(px, (int, float)) and px > 0:
                        return float(px)
        except Exception:  # noqa: BLE001 -- fallback below
            pass
        try:
            for rec in read_jsonl(self.paths["packet_log"]):
                if (rec.get("decision") == "signal"
                        and rec.get("signal_id") == signal_id):
                    px = dual_ledger.achievable_entry_px(rec)
                    if px is not None:
                        return px
        except Exception:  # noqa: BLE001 -- caller handles None
            pass
        return None

    def _dual_trade_legs(self, *, signal_id: str, symbol: str, t_iso: str,
                         exit_packet: dict | None, entry_px: float,
                         stop_px: float, net_r_4bps: float,
                         net_r_25bps: float, risk_dollars: float,
                         size: float) -> dict:
        """Compute the achievable leg + drag for one closing trade.

        Never raises: any failure returns all-None legs and logs loudly.
        The canonical trade record is always written by the caller.
        """
        nulls = {"ach_entry_px": None, "ach_tp1_px": None,
                 "ach_exit_fill_px": None, "ach_exit_px": None,
                 "ach_gross_r": None, "ach_net_r_4bps": None,
                 "ach_net_r_25bps": None, "drag_r_4bps": None,
                 "drag_r_25bps": None, "drag_bps": None}
        try:
            ach_entry = self._achievable_entry_for(signal_id)
            ach_exit_fill = dual_ledger.achievable_trigger_close(exit_packet)
            out = dict(nulls)
            out["ach_entry_px"] = ach_entry
            out["ach_exit_fill_px"] = ach_exit_fill
            if ach_entry is None or ach_exit_fill is None:
                raise ValueError("achievable fill price unavailable")
            tp1_px = (exit_packet.get("position", {}) or {}).get("tp1_px")
            tp_hit = (exit_packet.get("trigger", {}) or {}).get("tp1_hit",
                                                                False)
            atrade = dual_ledger.achievable_trade(
                entry_px=entry_px, stop_px=stop_px, tp1_px=tp1_px,
                tp_hit=tp_hit, ach_entry_px=ach_entry,
                ach_exit_fill_px=ach_exit_fill)
            if atrade is None:
                raise ValueError("achievable_trade rejected inputs")
            out.update(atrade)
            drag = dual_ledger.trade_drag(
                net_r_4bps=net_r_4bps, net_r_25bps=net_r_25bps,
                ach_net_r_4bps=atrade["ach_net_r_4bps"],
                ach_net_r_25bps=atrade["ach_net_r_25bps"],
                risk_dollars=risk_dollars, size=size, entry_px=entry_px)
            if drag is None:
                raise ValueError("trade_drag rejected inputs")
            out.update(drag)
            return out
        except Exception as exc:  # noqa: BLE001 -- instrumentation only
            self.log({"event": "dual_ledger_uncomputable",
                      "signal_id": signal_id, "symbol": symbol,
                      "bar_time": t_iso,
                      "error": f"{type(exc).__name__}: {exc}"})
            return nulls

    def _record_cycle_ledger(self, *, report: dict, t: pd.Timestamp,
                             state: PortfolioState, delay_min: float,
                             new_packets: list, state_before: dict) -> None:
        t_iso = t.isoformat()
        ts_rep = report.get("timestamp", {})
        # --- decisions ---------------------------------------------------
        port_packets = [p for p in new_packets
                        if p.get("type") == "portfolio_decision"
                        and p.get("decision_time") == t_iso]
        free_slots = (port_packets[0].get("free_slots_at_t")
                      if port_packets else None)
        contenders_by_id = {}
        if port_packets:
            for c in port_packets[0].get("contenders", []):
                contenders_by_id[c["signal_id"]] = c
        open_by_signal = {}
        for e in state.events:
            if e.get("kind") == "open":
                open_by_signal[e.get("signal_id")] = e
        for d in ts_rep.get("decisions", []):
            c = contenders_by_id.get(d["signal_id"], {})
            op = open_by_signal.get(d["signal_id"])
            self.ledger.decision(
                bar_time=t_iso, signal_id=d["signal_id"],
                symbol=d["symbol"], decision=d["decision"],
                reason_detail=d.get("reason_detail", ""),
                rs_score=d["rs_score"], rank=d["rank"],
                contested=d["contested"],
                sector=c.get("sector") or sector_of(d["symbol"]),
                marked_equity_at_t=d["marked_equity_at_t"],
                risk_dollars=(op["risk_dollars"] if op else None),
                free_slots_at_t=free_slots)
        # --- fills + trades (from new state events) ----------------------
        seq_before = state_before["seq"]
        new_events = [e for e in state.events if e["seq"] >= seq_before]
        exit_hold = {}
        exit_pos_by_signal = {}
        exit_pkt_by_signal = {}
        for p in new_packets:
            if p.get("packet_schema") == "slice5-v1":
                exit_hold[p.get("signal_id")] = (p.get("exit") or {}).get(
                    "hold_bars")
                # The exit packet pins the full pre-exit position
                # (entry_px, stop_px, tp1_px, size, risk_dollars, ...).
                if isinstance(p.get("position"), dict):
                    exit_pos_by_signal[p.get("signal_id")] = p["position"]
                exit_pkt_by_signal[p.get("signal_id")] = p
        # Signal packets pin the signal bar's OHLCV -- the achievable
        # entry fill (signal-bar close) comes from here, never from a
        # fresh download (history can restate under auto_adjust).
        sig_by_id = {p.get("signal_id"): p for p in new_packets
                     if p.get("decision") == "signal" and p.get("signal_id")}
        opens = {e.get("signal_id"): e for e in state.events
                 if e.get("kind") == "open"}
        for e in new_events:
            if e.get("kind") == "open":
                # Share count from the canonical sizing: size =
                # risk_dollars / risk_frac, risk_frac from the contender's
                # entry/stop (pinned in the portfolio packet).
                oc = contenders_by_id.get(e.get("signal_id"), {})
                o_entry = float(oc.get("entry_px") or e["entry_px"])
                o_stop = float(oc.get("stop_px") or 0.0)
                risk_frac = ((o_entry - o_stop) / o_entry
                             if o_entry > o_stop > 0 else float("nan"))
                o_size = (float(e["risk_dollars"]) / risk_frac
                          if risk_frac == risk_frac and risk_frac > 0
                          else float("nan"))
                # Dual ledger, entry leg: achievable fill = CLOSE of the
                # signal bar (last visible price at detection). Guarded:
                # instrumentation never breaks the canonical wake-up.
                try:
                    ach_entry = dual_ledger.achievable_entry_px(
                        sig_by_id.get(e.get("signal_id")))
                except Exception as exc:  # noqa: BLE001
                    ach_entry = None
                    self.log({"event": "achievable_entry_uncomputable",
                              "signal_id": e.get("signal_id"),
                              "symbol": e.get("symbol"),
                              "bar_time": t_iso,
                              "error": f"{type(exc).__name__}: {exc}"})
                if ach_entry is None:
                    self.log({"event": "achievable_entry_missing",
                              "signal_id": e.get("signal_id"),
                              "symbol": e.get("symbol"),
                              "bar_time": t_iso})
                self.ledger.fill(
                    kind="entry", bar_time=t_iso,
                    signal_id=e["signal_id"], symbol=e["symbol"],
                    theoretical_px=e["entry_px"],
                    paper_fill_px=e["entry_px"], deviation_r=0.0,
                    cost_dollars=0.0,  # round-trip cost modeled once, at exit
                    size=o_size,
                    detection_delay_minutes=delay_min,
                    achievable_fill_px=ach_entry)
            elif e.get("kind") == "close":
                op = opens.get(e.get("signal_id"), {})
                xp = exit_pos_by_signal.get(e.get("signal_id"), {})
                xpkt = exit_pkt_by_signal.get(e.get("signal_id"))
                size = float(op.get("size") or xp.get("size") or 0.0)
                risk_dollars = float(op.get("risk_dollars")
                                     or xp.get("risk_dollars") or 0.0)
                entry_px = float(op.get("entry_px") or xp.get("entry_px")
                                 or float("nan"))
                # stop_px is on neither the open event nor this cycle's
                # contenders; the exit packet pins the pre-exit position.
                stop_px = float(xp.get("stop_px") or float("nan"))
                exit_px = float(e["exit_px"])
                _, gross_r, net_r_4, _ = pb._outcome(
                    entry_px, stop_px, exit_px, FROZEN_COST)
                _, _, net_r_25, _ = pb._outcome(
                    entry_px, stop_px, exit_px, COST_25BPS)
                # Dual ledger, exit leg + per-trade drag. All achievable
                # inputs come from pinned packets/snapshots; any failure
                # records nulls and logs loudly -- the canonical trade
                # record is always written.
                ach = self._dual_trade_legs(
                    signal_id=e.get("signal_id"), symbol=e.get("symbol"),
                    t_iso=t_iso, exit_packet=xpkt,
                    entry_px=entry_px, stop_px=stop_px,
                    net_r_4bps=float(net_r_4), net_r_25bps=float(net_r_25),
                    risk_dollars=risk_dollars, size=size)
                self.ledger.fill(
                    kind="exit", bar_time=t_iso,
                    signal_id=e["signal_id"], symbol=e["symbol"],
                    theoretical_px=exit_px, paper_fill_px=exit_px,
                    deviation_r=0.0,
                    cost_dollars=FROZEN_COST * size,  # modeled round-trip
                    size=size, detection_delay_minutes=delay_min,
                    achievable_fill_px=ach["ach_exit_fill_px"])
                self.ledger.trade(
                    signal_id=e["signal_id"], symbol=e["symbol"],
                    sector=op.get("sector") or sector_of(e["symbol"]),
                    entry_time=op.get("t", ""), exit_time=e["t"],
                    entry_px=entry_px, stop_px=stop_px, exit_px=exit_px,
                    exit_reason=e.get("exit_reason", ""),
                    risk_dollars=risk_dollars, size=size,
                    hold_bars=exit_hold.get(e.get("signal_id")),
                    detection_delay_minutes=delay_min,
                    gross_r=float(gross_r), net_r_4bps=float(net_r_4),
                    net_r_25bps=float(net_r_25),
                    ach_entry_px=ach["ach_entry_px"],
                    ach_tp1_px=ach["ach_tp1_px"],
                    ach_exit_fill_px=ach["ach_exit_fill_px"],
                    ach_exit_px=ach["ach_exit_px"],
                    ach_gross_r=ach["ach_gross_r"],
                    ach_net_r_4bps=ach["ach_net_r_4bps"],
                    ach_net_r_25bps=ach["ach_net_r_25bps"],
                    drag_r_4bps=ach["drag_r_4bps"],
                    drag_r_25bps=ach["drag_r_25bps"],
                    drag_bps=ach["drag_bps"])
        # --- rejections ---------------------------------------------------
        for s in report.get("skipped", []):
            self.ledger.rejection(bar_time=t_iso, symbol=s["symbol"],
                                  signal_id=s.get("signal_id"),
                                  reason=s["reason"],
                                  detail=s.get("refused_reason")
                                  or s.get("error"))
        for p in report.get("pending_entry", []):
            self.ledger.rejection(bar_time=t_iso, symbol=p["symbol"],
                                  signal_id=p.get("signal_id"),
                                  reason="signal_pending_entry")
        refused_packets = {(p.get("symbol")): p for p in new_packets
                           if p.get("decision") == "refused"}
        for ev in report.get("evaluated", []):
            if ev.get("decision") in ("signal", "refused"):
                if ev.get("decision") == "refused":
                    rp = refused_packets.get(ev["symbol"], {})
                    rr = rp.get("refused_reason", "")
                    reason = ("warmup" if rr.startswith("warmup:")
                              else "input_assertion"
                              if rr.startswith("input_assertion:")
                              else "evaluation_refused")
                    self.ledger.rejection(
                        bar_time=t_iso, symbol=ev["symbol"],
                        signal_id=ev.get("signal_id"), reason=reason,
                        detail=rr)
            else:
                self.ledger.rejection(bar_time=t_iso, symbol=ev["symbol"],
                                      signal_id=ev.get("signal_id"),
                                      reason="no_signal")
        if ts_rep.get("status") == "refused":
            self.ledger.rejection(bar_time=t_iso, symbol=None, reason=
                                  "timestamp_refused",
                                  detail=ts_rep.get("refused_reason"))
        # --- equity -------------------------------------------------------
        eq = state.marked_equity(t)
        self.ledger.equity(bar_time=t_iso, marked_equity=float(eq),
                           realized=float(state.realized),
                           peak=float(state.peak),
                           max_dd=float(state.max_dd),
                           n_open=state.n_open(),
                           detection_delay_minutes=delay_min)

    def run_wake_up(self) -> int:
        """Run one full wake-up. Returns the process exit code."""
        if is_halted(self.state_dir):
            print(f"HALTED: {halt_path(self.state_dir)} exists; "
                  f"not running. Clear it per PAPER.md after root-cause + "
                  f"sign-off.")
            return 0

        symbols = sorted(pb.UNIVERSE_X)
        frames, failures = self.download_all(symbols)
        if not frames:
            self.log({"event": "wake_up_no_frames",
                      "reason": "all downloads failed"})
            self._write_status(initialized=False)
            return 0
        spy = self.download_spy()
        mark_fn = self._mark_fn(frames)

        # --- state -------------------------------------------------------
        state, existed = st.load_portfolio(self.state_dir, mark_fn,
                                           FROZEN_COST)
        watermarks = st.load_watermarks(self.state_dir)
        first_run = not existed and not watermarks

        # --- new-bar detection -------------------------------------------
        new_points: list = []  # (bar_open_time, symbol)
        for sym, fr in frames.items():
            latest_open = fr.index[-1]
            wm_raw = watermarks.get(sym)
            if wm_raw is None:
                # Backfill guard: a symbol with no watermark starts NOW.
                watermarks[sym] = latest_open.isoformat()
                self.log({"event": "watermark_initialized", "symbol": sym,
                          "watermark": latest_open.isoformat(),
                          "reason": "no prior watermark; paper starts now"})
                continue
            wm = pd.Timestamp(wm_raw)
            for ts in fr.index:
                if ts > wm.tz_convert(fr.index.tz):
                    new_points.append((ts, sym))
        if first_run:
            # First run ever: watermarks set above to latest opens; no
            # cycles, no decisions, no backfill.
            st.save_portfolio(self.state_dir, state)
            st.save_watermarks(self.state_dir, watermarks)
            self.log({"event": "paper_initialized",
                      "n_symbols": len(frames),
                      "note": "watermarks set to latest bar opens; "
                              "zero cycles on first run"})
            self._write_status(initialized=True)
            write_report(self.state_dir)
            print("Paper phase initialized: watermarks set, 0 cycles run. "
                  "Next wake-up starts live paper.")
            return 0

        by_t: dict = defaultdict(list)
        for ts, sym in new_points:
            by_t[pd.Timestamp(ts)].append(sym)
        ordered_t = sorted(by_t)

        packet_log = PacketLog(self.paths["packet_log"])
        exit_packet_log_path = self.paths["exit_packet_log"]
        dedup_store = DedupStore(self.paths["dedup"])
        outbox = PaperOutbox(self.paths["outbox"])
        vintage = self._vintage(frames, failures, spy)
        now = datetime.now(timezone.utc)

        state_before_by_t: dict = {}
        n_cycles = 0
        for t in ordered_t:
            syms = sorted(by_t[t])
            cycle_start = datetime.now(timezone.utc)
            state_before = state.to_dict()
            state_before_by_t[t.isoformat()] = state_before
            pkt_off = self._file_size(self.paths["packet_log"])
            exit_off = self._file_size(exit_packet_log_path)
            try:
                report = run_cycle(
                    symbols=syms, bar_time=t, signal_bar="previous",
                    live_exits=True, state=state, mark_fn=mark_fn,
                    packet_log=packet_log,
                    snapshot_dir=self.paths["snapshot_dir"],
                    vintage=vintage,
                    dedup_store=dedup_store, outbox=outbox,
                    delivery_log_path=self.paths["delivery_log"],
                    sender=paper_sender,
                    actions_log_path=self.paths["actions_log"],
                    cycle_log_path=self.paths["cycle_log"],
                    frame_provider=self.provider, spy_daily=spy, now=now,
                    exit_packet_log=exit_packet_log_path)
            except Exception as exc:  # noqa: BLE001 — HALT: fail closed
                tb = traceback.format_exc(limit=8)
                self.log({"event": "run_cycle_exception",
                          "bar_time": t.isoformat(),
                          "error_type": type(exc).__name__,
                          "error": str(exc), "traceback_tail": tb})
                halt_file = write_halt(
                    self.state_dir,
                    reason=f"exception escaped run_cycle at {t.isoformat()}",
                    classification={"category": "unclassified",
                                    "layer": "cycle exception",
                                    "error": f"{type(exc).__name__}: {exc}"},
                    context={"bar_time": t.isoformat(), "symbols": syms})
                self._persist(state, watermarks, initialized=True,
                              halted=True)
                write_report(self.state_dir)
                print(f"HALTED: exception escaped run_cycle: {exc}\n"
                      f"HALT file: {halt_file}")
                return 2

            delay_min = ((datetime.now(timezone.utc) - cycle_start)
                         .total_seconds() / 60.0)
            ts_status = report.get("timestamp", {}).get("status")

            # --- exit-skip classification (task step g) -------------------
            exit_skips = report.get("live_exits", {}).get("skipped", [])
            n_expected_skips = 0
            for sk in exit_skips:
                sym = sk["symbol"]
                if self._exit_skip_aligned(sym, t, frames):
                    # A position whose symbol HAS a bar at t but whose walk
                    # could not be evaluated: HALT (category 6 candidate).
                    halt_file = write_halt(
                        self.state_dir,
                        reason=f"exit-eval skip for aligned symbol {sym} "
                               f"at {t.isoformat()}",
                        classification={
                            "category": 6,
                            "layer": "state/slot: exit walk failed on an "
                                     "aligned symbol",
                            "skip_record": sk},
                        context={"bar_time": t.isoformat(), "symbol": sym})
                    self._persist(state, watermarks, initialized=True,
                                  halted=True)
                    write_report(self.state_dir)
                    print(f"HALTED: exit-eval skip for aligned symbol "
                          f"{sym}: {sk.get('error')}\nHALT file: {halt_file}")
                    return 2
                n_expected_skips += 1
                self.ledger.rejection(
                    bar_time=t.isoformat(), symbol=sym,
                    signal_id=sk.get("signal_id"),
                    reason="exit_skip_misaligned_expected",
                    detail=sk.get("error"))

            # --- watermarks (advance only on non-failed-closed cycles) ----
            if ts_status != "failed_closed":
                for sym in syms:
                    watermarks[sym] = t.isoformat()
            else:
                self.flags.append(f"timestamp_failed_closed:{t.isoformat()}")
                self.log({"event": "timestamp_failed_closed",
                          "bar_time": t.isoformat(),
                          "reason": report["timestamp"].get("reason")})

            # --- new packets this cycle ----------------------------------
            new_packets, _ = read_new_jsonl(self.paths["packet_log"],
                                            pkt_off)
            new_exit_packets, _ = read_new_jsonl(exit_packet_log_path,
                                                 exit_off)
            all_new = new_packets + new_exit_packets

            # --- ledger ---------------------------------------------------
            self._record_cycle_ledger(
                report=report, t=t, state=state, delay_min=delay_min,
                new_packets=all_new, state_before=state_before)

            # --- continuous verification (category 2-7 check) ------------
            vrep = verify_wake_up(
                state_dir=self.state_dir, new_packets=all_new,
                state_before_by_t=state_before_by_t,
                snapshot_dir=self.paths["snapshot_dir"], mark_fn=mark_fn,
                fresh_provider=self.provider)
            self.packets_replayed += vrep["n_replayed"]
            self.replay_mismatches += len(vrep["mismatches"])
            if vrep["halted"]:
                self.log({"event": "verification_halt",
                          "bar_time": t.isoformat(),
                          "mismatch": vrep["mismatches"][0],
                          "halt_file": vrep["halt_file"]})
                self._persist(state, watermarks, initialized=True,
                              halted=True)
                write_report(self.state_dir)
                print(f"HALTED: replay mismatch at {t.isoformat()}:\n"
                      f"{json.dumps(vrep['mismatches'][0], indent=1, default=str)}\n"
                      f"HALT file: {vrep['halt_file']}")
                return 2

            n_cycles += 1
            self.cycle_records.append({
                "bar_time": t.isoformat(),
                "n_symbols": len(syms),
                "evaluated": len(report.get("evaluated", [])),
                "signals": len(report.get("signals", [])),
                "skipped": len(report.get("skipped", [])),
                "pending_entry": len(report.get("pending_entry", [])),
                "timestamp_status": ts_status,
                "exit_evaluated": len(report.get("live_exits",
                                                {}).get("evaluated", [])),
                "exit_skips_expected": n_expected_skips,
                "n_exits_applied": report.get("timestamp", {}).get(
                    "n_exits_applied", 0),
                "detection_delay_minutes": round(delay_min, 2),
                "n_new_packets": len(all_new),
                "n_replayed": vrep["n_replayed"],
            })
            self.log({"event": "cycle_complete", "bar_time": t.isoformat(),
                      "timestamp_status": ts_status,
                      "detection_delay_minutes": round(delay_min, 2)})

        # --- persist + report ---------------------------------------------
        # Persistence failure is a HALT condition: never proceed to the
        # next wake-up on unpersisted state.
        try:
            self._persist(state, watermarks, initialized=True, halted=False)
        except Exception as exc:  # noqa: BLE001
            self.log({"event": "persistence_failed",
                      "error_type": type(exc).__name__, "error": str(exc)})
            halt_file = write_halt(
                self.state_dir, reason="state persistence failed",
                classification={"category": "unclassified",
                                "layer": "persistence",
                                "error": f"{type(exc).__name__}: {exc}"},
                context={})
            print(f"HALTED: state persistence failed: {exc}\n"
                  f"HALT file: {halt_file}")
            return 2
        write_report(self.state_dir)
        print(f"Wake-up complete: {n_cycles} cycles, "
              f"{self.packets_replayed} packets replayed, "
              f"{self.replay_mismatches} mismatches, "
              f"{len(self.flags)} flags.")
        return 0

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _file_size(path: str) -> int:
        try:
            return os.path.getsize(path)
        except OSError:
            return 0

    def _persist(self, state: PortfolioState, watermarks: dict, *,
                 initialized: bool, halted: bool) -> None:
        st.save_portfolio(self.state_dir, state)
        st.save_watermarks(self.state_dir, watermarks)
        self._write_status(initialized=initialized, halted=halted)

    def _write_status(self, initialized: bool, halted: bool = False) -> None:
        prev = {}
        path = os.path.join(self.state_dir, "status.json")
        if os.path.exists(path):
            with open(path) as f:
                prev = json.load(f)
        cycles = prev.get("cycles", []) + self.cycle_records
        status = {
            "schema": STATE_SCHEMA,
            "updated_at": _utcnow_iso(),
            "halted": halted or is_halted(self.state_dir),
            "halt_file": halt_path(self.state_dir)
            if (halted or is_halted(self.state_dir)) else None,
            "initialized": initialized,
            "n_wakeups": int(prev.get("n_wakeups", 0)) + 1,
            "universe": sorted(pb.UNIVERSE_X),
            "frozen_cost": FROZEN_COST,
            "packets_replayed": int(prev.get("packets_replayed", 0))
            + self.packets_replayed,
            "replay_mismatches": int(prev.get("replay_mismatches", 0))
            + self.replay_mismatches,
            "cycles": cycles,
            "flags": sorted(set(prev.get("flags", [])) | set(self.flags)),
            "download_health": st.load_health(self.state_dir),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=1, sort_keys=True, default=str)
            f.flush()
            os.fsync(f.fileno())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Pine V3.6 paper-phase wake-up runner (paper only).")
    ap.add_argument("--state-dir",
                    default=os.path.join(_REPO_ROOT, "pine_live",
                                         "paper_state"),
                    help="paper state directory (default: "
                         "pine_live/paper_state)")
    args = ap.parse_args(argv)
    try:
        return WakeUp(args.state_dir).run_wake_up()
    except Exception as exc:  # noqa: BLE001 — never die silently
        print(f"WAKE-UP FAILED: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        traceback.print_exc(limit=10)
        return 1


if __name__ == "__main__":
    sys.exit(main())
