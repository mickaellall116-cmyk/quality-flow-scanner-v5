"""Append-only paper ledger (JSONL, one record per line, fsync'd).

Five logs under paper_state/ledger/:

  decisions.jsonl  — every contender decision per cycle (TAKEN/RANKED_OUT/
                     SECTOR_CAP/RISK_CAP/NO_SLOT) with rs_score, rank, sector,
                     contested flag, marked equity, and risk contribution.
  fills.jsonl      — every entry and exit: theoretical_px (the
                     strategy-specified price: next-bar open),
                     paper_fill_px (applied canonical fill, = theoretical
                     in paper), achievable_fill_px (detection-time price:
                     CLOSE of the signal bar for entries, CLOSE of the
                     exit-trigger bar for exits -- the first realistically
                     tradable price when the runner detects the signal),
                     fill deviation in R, modeled cost dollars, detection
                     delay. The canonical leg matches theory by
                     construction; the achievable leg is the dual-ledger
                     measurement (see pine_live/paper/dual.py).
  trades.jsonl     — one record per completed paper trade linking
                     entry -> exit, with gross and net R at BOTH cost legs
                     (4bps and 25bps) via the canonical pb._outcome formula,
                     PLUS the achievable leg (ach_* fields: same trade
                     re-priced at detection-time fills) and the
                     achievable-vs-canonical drag (drag_r_4bps,
                     drag_r_25bps, drag_bps). Positive drag = achievable
                     worse.
  rejections.jsonl — every skip/refusal: frame_provider_failed,
                     bar_time_not_in_frame, evaluation_refused (with the
                     refused_reason: warmup / input assertion / ...),
                     entry_through_stop, signal_pending_entry, no_signal,
                     plus timestamp-level fail-closed refusals.
  equity.jsonl     — marked equity per cycle (drawdown accounting).

Ledger writes never raise into the caller: a ledger failure is loud
(stderr + the wake-up's cycle log) but the canonical packet logs are the
audit trail of record — the ledger is a derived convenience view.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

LEDGER_FILES = ("decisions", "fills", "trades", "rejections", "equity")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Ledger:
    def __init__(self, ledger_dir: str):
        self.dir = ledger_dir
        os.makedirs(ledger_dir, exist_ok=True)
        self._handles: dict = {}

    def _append(self, name: str, rec: dict) -> None:
        path = os.path.join(self.dir, name + ".jsonl")
        rec = dict(rec)
        rec.setdefault("logged_at", _utcnow_iso())
        line = json.dumps(rec, sort_keys=True, separators=(",", ":"),
                          default=str)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())

    # ------------------------------------------------------------------ API
    def decision(self, *, bar_time: str, signal_id: str, symbol: str,
                 decision: str, reason_detail: str, rs_score: float,
                 rank: int, contested: bool, sector: str,
                 marked_equity_at_t: float, risk_dollars: float | None,
                 free_slots_at_t: int) -> None:
        self._append("decisions", {
            "bar_time": bar_time, "signal_id": signal_id, "symbol": symbol,
            "decision": decision, "reason_detail": reason_detail,
            "rs_score": rs_score, "rank": rank, "contested": bool(contested),
            "sector": sector, "marked_equity_at_t": marked_equity_at_t,
            "risk_dollars": risk_dollars, "free_slots_at_t": free_slots_at_t,
        })

    def fill(self, *, kind: str, bar_time: str, signal_id: str, symbol: str,
             theoretical_px: float, paper_fill_px: float,
             deviation_r: float, cost_dollars: float, size: float,
             detection_delay_minutes: float,
             achievable_fill_px: float | None = None) -> None:
        self._append("fills", {
            "kind": kind, "bar_time": bar_time, "signal_id": signal_id,
            "symbol": symbol, "theoretical_px": theoretical_px,
            "paper_fill_px": paper_fill_px,
            "achievable_fill_px": achievable_fill_px,
            "deviation_r": deviation_r,
            "cost_dollars": cost_dollars, "size": size,
            "detection_delay_minutes": detection_delay_minutes,
        })

    def trade(self, *, signal_id: str, symbol: str, sector: str,
              entry_time: str, exit_time: str, entry_px: float,
              stop_px: float, exit_px: float, exit_reason: str,
              risk_dollars: float, size: float, hold_bars: int | None,
              detection_delay_minutes: float,
              gross_r: float, net_r_4bps: float, net_r_25bps: float,
              ach_entry_px: float | None = None,
              ach_tp1_px: float | None = None,
              ach_exit_fill_px: float | None = None,
              ach_exit_px: float | None = None,
              ach_gross_r: float | None = None,
              ach_net_r_4bps: float | None = None,
              ach_net_r_25bps: float | None = None,
              drag_r_4bps: float | None = None,
              drag_r_25bps: float | None = None,
              drag_bps: float | None = None) -> None:
        self._append("trades", {
            "signal_id": signal_id, "symbol": symbol, "sector": sector,
            "entry_time": entry_time, "exit_time": exit_time,
            "entry_px": entry_px, "stop_px": stop_px, "exit_px": exit_px,
            "exit_reason": exit_reason, "risk_dollars": risk_dollars,
            "size": size, "hold_bars": hold_bars,
            "detection_delay_minutes": detection_delay_minutes,
            "gross_r": gross_r, "net_r_4bps": net_r_4bps,
            "net_r_25bps": net_r_25bps,
            "ach_entry_px": ach_entry_px, "ach_tp1_px": ach_tp1_px,
            "ach_exit_fill_px": ach_exit_fill_px,
            "ach_exit_px": ach_exit_px, "ach_gross_r": ach_gross_r,
            "ach_net_r_4bps": ach_net_r_4bps,
            "ach_net_r_25bps": ach_net_r_25bps,
            "drag_r_4bps": drag_r_4bps, "drag_r_25bps": drag_r_25bps,
            "drag_bps": drag_bps,
        })

    def rejection(self, *, bar_time: str | None, symbol: str | None,
                  reason: str, detail: str | None = None,
                  signal_id: str | None = None) -> None:
        self._append("rejections", {
            "bar_time": bar_time, "symbol": symbol, "signal_id": signal_id,
            "reason": reason, "detail": detail,
        })

    def equity(self, *, bar_time: str, marked_equity: float, realized: float,
               peak: float, max_dd: float, n_open: int,
               detection_delay_minutes: float) -> None:
        self._append("equity", {
            "bar_time": bar_time, "marked_equity": marked_equity,
            "realized": realized, "peak": peak, "max_dd": max_dd,
            "n_open": n_open,
            "detection_delay_minutes": detection_delay_minutes,
        })


def read_jsonl(path: str) -> list:
    """Read a JSONL log; missing file -> []."""
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def read_new_jsonl(path: str, offset: int) -> tuple[list, int]:
    """Read lines appended after byte `offset`; returns (records, new_offset)."""
    if not os.path.exists(path):
        return [], 0
    with open(path, "r", encoding="utf-8") as f:
        f.seek(offset)
        lines = [json.loads(ln) for ln in f if ln.strip()]
        new_offset = f.tell()
    return lines, new_offset
