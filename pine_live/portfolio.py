"""Portfolio state machine — SLICE 2.

Locked-stack entry logic (C1 = rs_top2 ranking + E1 sector cap), as an
explicit, serializable, append-only state machine. No duplicate suppression
(slice 3), no alert delivery, no trading.

The decision logic mirrors pine_stack.simulate_stack's entry loop EXACTLY,
branch order included:

    for each contender at timestamp t (ordered by -rs_score, then
    deterministic candidate order):
        free = MAX_CONCURRENT - n_open
        contested = n_candidates_at_t > free          # after exits at t
        if contested and taken_at_t >= min(2, free):  # RANKED_OUT
        elif free <= 0:                               # NO_SLOT
        elif sector count >= 2:                       # SECTOR_CAP
        elif open_risk + RISK_PCT > 5%:               # RISK_CAP
        else:                                         # TAKEN

REFERENCE-BEHAVIOR NOTES (pinned, not "fixed"):
- In the ranked (C1) configuration the `free <= 0` branch is UNREACHABLE:
  when free <= 0 and any candidate exists, contested is true and the
  ranking cutoff fires first (taken_at_t >= min(2, free) with free <= 0).
  All slot-driven skips are therefore recorded as RANKED_OUT, never
  NO_SLOT. The branch is kept because the unranked reference has it, and
  the full-window test asserts the C1 counts reproduce exactly
  (RANKED_OUT=94, SECTOR_CAP=16, NO_SLOT=0, RISK_CAP=10).
- marked_equity(t) is recomputed per candidate (positions taken earlier at
  the same t change it), exactly as in the reference.
- Exits at t are processed BEFORE entries at t (kind=0 before kind=1).

Exit events are consumed (symbol, exit_px, reason); per-bar V3.6 exit
evaluation for live positions is future work — the state machine does not
invent exits.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pine_backtest as pb  # noqa: E402  (canonical constants + _outcome)
from pine_live.ranking import RANK_TOP_N  # noqa: E402
from pine_live.sector import (  # noqa: E402
    SECTOR_CAP as SECTOR_CAP_LIMIT,
    sector_counts,
    sector_of,
)

# Reason codes. TAKEN is the only accept; the rest are rejections.
TAKEN = "TAKEN"
RANKED_OUT = "RANKED_OUT"
NO_SLOT = "NO_SLOT"
SECTOR_CAP = "SECTOR_CAP"
RISK_CAP = "RISK_CAP"

_RISK_TOL = 1e-9


def reference_mark(closes: dict, symbol: str, t) -> float:
    """Mark-to-market price: last close with bar start <= t (searchsorted
    right - 1). Direct mirror of the `mark` closure inside
    pine_stack.simulate_stack / pb.simulate_portfolio. Pinned by the
    bit-identical full-window test."""
    s = closes[symbol]
    ii = s.index.searchsorted(t, side="right") - 1
    return float(s.iloc[ii]) if ii >= 0 else float(s.iloc[0])


class PortfolioState:
    """Explicit portfolio state. All mutations go through process_exits /
    decide_entries and are appended to the event log; the state (and any
    past state) reconstructs from the event log."""

    def __init__(self, mark_fn, cost: float):
        """
        mark_fn: (symbol, t) -> float, mark-to-market price.
        cost: round-trip cost fraction applied on exits (pb._outcome).
        """
        self._mark = mark_fn
        self._cost = float(cost)
        self.positions: dict = {}   # symbol -> position dict
        self.events: list = []      # append-only; each has a 'seq'
        self.realized: float = pb.START_EQUITY
        self.peak: float = pb.START_EQUITY
        self.max_dd: float = 0.0
        self.counters = {TAKEN: 0, RANKED_OUT: 0, NO_SLOT: 0,
                         SECTOR_CAP: 0, RISK_CAP: 0}
        self._seq = 0
        self._prev_t = None
        self.open_time = pd.Timedelta(0)
        self.total_time = pd.Timedelta(0)

    # ------------------------------------------------------------- helpers
    def _log(self, event: dict) -> dict:
        event = dict(event)
        event["seq"] = self._seq
        self._seq += 1
        self.events.append(event)
        return event

    def n_open(self) -> int:
        return len(self.positions)

    @property
    def cost(self) -> float:
        """Round-trip cost fraction (read-only; used by exit accounting)."""
        return self._cost

    def free_slots(self) -> int:
        return pb.MAX_CONCURRENT - self.n_open()

    def marked_equity(self, t) -> float:
        unreal = 0.0
        for sym, p in self.positions.items():
            px = self._mark(sym, t)
            unreal += ((px - p["entry_px"]) / p["entry_px"]) * p["size"]
        return self.realized + unreal

    # ---------------------------------------------------------------- clock
    def advance_clock(self, t) -> None:
        """Account open/total time from the previous timestamp to t.
        Mirrors the reference: accounting happens at the START of each t
        iteration, using the position set carried over from before t."""
        if self._prev_t is not None and t > self._prev_t:
            dt = t - self._prev_t
            self.total_time += dt
            if self.positions:
                self.open_time += dt
        self._prev_t = t

    # ---------------------------------------------------------------- exits
    def process_exits(self, t, exits: list) -> list:
        """Apply exit events at t. exits: list of dicts with keys
        symbol, exit_px, reason, universe_order (for deterministic order).
        Reference: exits sorted by candidate index, unknown ids skipped."""
        applied = []
        for e in sorted(exits, key=lambda e: e.get("universe_order", 0)):
            sym = e["symbol"]
            pos = self.positions.pop(sym, None)
            if pos is None:
                continue  # reference: by_id.pop(id, None) -> skip
            _, _, net_r, _ = pb._outcome(
                pos["entry_px"], pos["stop_px"], float(e["exit_px"]), self._cost)
            self.realized += pos["risk_dollars"] * net_r
            ev = self._log({
                "t": pd.Timestamp(t).isoformat(),
                "kind": "close",
                "symbol": sym,
                "signal_id": pos["signal_id"],
                "exit_px": float(e["exit_px"]),
                "exit_reason": e.get("reason"),
                "net_r": float(net_r),
                "realized_after": float(self.realized),
            })
            applied.append(ev)
        return applied

    # --------------------------------------------------------------- entries
    def decide_entries(self, t, contenders: list) -> list:
        """Decide one timestamp's candidate entries. contenders: list of
        dicts with keys signal_id, symbol, entry_px, stop_px, tp1_px,
        rs_score, universe_order. Returns a list of decision dicts in the
        order candidates were evaluated (rank order).

        Branch order mirrors simulate_stack exactly (see module docstring).
        """
        t_iso = pd.Timestamp(t).isoformat()
        n_cands = len(contenders)
        ordered = sorted(
            contenders,
            key=lambda c: (-c["rs_score"], c["universe_order"], c["signal_id"]),
        )
        contested = n_cands > self.free_slots()
        decisions = []
        taken_at_t = 0
        for rank, c in enumerate(ordered, start=1):
            free = self.free_slots()
            contested_now = n_cands > free
            eq = self.marked_equity(t)
            if contested_now and taken_at_t >= min(RANK_TOP_N, free):
                reason, detail = RANKED_OUT, (
                    f"contested bar ({n_cands} candidates, {free} free): "
                    f"rank cutoff at top {min(RANK_TOP_N, free)}")
            elif free <= 0:
                reason, detail = NO_SLOT, "no free position slots"
            else:
                sector = sector_of(c["symbol"])  # fail-closed on unknown
                n_sec = sum(1 for p in self.positions.values()
                            if p["sector"] == sector)
                if n_sec >= SECTOR_CAP_LIMIT:
                    reason, detail = SECTOR_CAP, (
                        f"sector {sector} already has {n_sec} open "
                        f"(cap {SECTOR_CAP_LIMIT})")
                else:
                    open_risk = (sum(p["risk_dollars"]
                                     for p in self.positions.values()) / eq
                                 if eq > 0 else 1.0)
                    if open_risk + pb.RISK_PCT > pb.MAX_PORTFOLIO_RISK + _RISK_TOL:
                        reason, detail = RISK_CAP, (
                            f"open risk {open_risk:.4f} + {pb.RISK_PCT} > "
                            f"{pb.MAX_PORTFOLIO_RISK}")
                    else:
                        reason, detail = TAKEN, ""
            if reason == TAKEN:
                risk_dollars = pb.RISK_PCT * eq
                risk_frac = (c["entry_px"] - c["stop_px"]) / c["entry_px"]
                pos = {
                    "symbol": c["symbol"],
                    "signal_id": c["signal_id"],
                    "sector": sector_of(c["symbol"]),
                    "entry_px": float(c["entry_px"]),
                    "stop_px": float(c["stop_px"]),
                    "tp1_px": float(c.get("tp1_px")) if c.get("tp1_px") is not None else None,
                    "entry_time": t_iso,
                    "risk_dollars": float(risk_dollars),
                    "risk_frac": float(risk_frac),
                    "size": float(risk_dollars / risk_frac),
                }
                self.positions[c["symbol"]] = pos
                self._log({
                    "t": t_iso,
                    "kind": "open",
                    "symbol": c["symbol"],
                    "signal_id": c["signal_id"],
                    "sector": pos["sector"],
                    "entry_px": pos["entry_px"],
                    "risk_dollars": pos["risk_dollars"],
                    "rs_score": float(c["rs_score"]),
                })
                taken_at_t += 1
            self.counters[reason] += 1
            decisions.append({
                "signal_id": c["signal_id"],
                "symbol": c["symbol"],
                "decision": reason,
                "reason_detail": detail,
                "rs_score": float(c["rs_score"]),
                "rank": rank,
                "contested": bool(contested),
                "marked_equity_at_t": float(eq),
            })
        return decisions

    # ---------------------------------------------------------------- settle
    def settle(self, t) -> dict:
        """End-of-timestamp peak/drawdown update. Mirrors the reference:
        one eq/peak/dd update per t, after that t's exits and entries."""
        eq = self.marked_equity(t)
        self.peak = max(self.peak, eq)
        if self.peak > 0:
            self.max_dd = max(self.max_dd, (self.peak - eq) / self.peak)
        return {"t": pd.Timestamp(t).isoformat(), "marked_equity": float(eq),
                "peak": float(self.peak), "max_dd": float(self.max_dd)}

    def exposure(self) -> float:
        return (float(self.open_time / self.total_time)
                if self.total_time > pd.Timedelta(0) else 0.0)

    # ------------------------------------------------------- serialization
    def to_dict(self) -> dict:
        return {
            "realized": self.realized,
            "peak": self.peak,
            "max_dd": self.max_dd,
            "positions": {s: dict(p) for s, p in self.positions.items()},
            "events": list(self.events),
            "counters": dict(self.counters),
            "seq": self._seq,
            "prev_t": self._prev_t.isoformat() if self._prev_t is not None else None,
            "open_time_s": self.open_time.total_seconds(),
            "total_time_s": self.total_time.total_seconds(),
            "cost": self._cost,
        }

    @classmethod
    def from_dict(cls, d: dict, mark_fn) -> "PortfolioState":
        st = cls(mark_fn, d["cost"])
        st.realized = d["realized"]
        st.peak = d["peak"]
        st.max_dd = d["max_dd"]
        st.positions = {s: dict(p) for s, p in d["positions"].items()}
        st.events = list(d["events"])
        st.counters = dict(d["counters"])
        st._seq = d["seq"]
        st._prev_t = (pd.Timestamp(d["prev_t"]) if d["prev_t"] is not None
                      else None)
        st.open_time = pd.Timedelta(seconds=d["open_time_s"])
        st.total_time = pd.Timedelta(seconds=d["total_time_s"])
        return st
