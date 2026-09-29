"""Append-only decision packets and bar snapshots (parity spec Part B).

Packets: one immutable JSON object per line, fsync'd on write, never
rewritten. Snapshots: the exact OHLCV frame a decision used, stored as
canonical JSON with a sha256 the packet references, so any decision can be
replayed deterministically from packet + snapshot + reference code.
"""

from __future__ import annotations

import hashlib
import json
import os

import pandas as pd

PACKET_SCHEMA_VERSION = "slice1-v1"

# Slice 2: portfolio-decision packets (per timestamp where entries were
# considered). Versioned separately; slice-1 signal packets are unchanged.
PORTFOLIO_PACKET_SCHEMA = "slice2-v2"

PORTFOLIO_DECISION_CODES = ("TAKEN", "RANKED_OUT", "SECTOR_CAP",
                            "NO_SLOT", "RISK_CAP")


def engine_version_extended(extra_files=()) -> dict:
    """engine_version() plus hashes of the slice-2 modules and the frozen
    sector map, so a packet pins the exact code AND map that decided."""
    import hashlib
    import subprocess
    from pine_live.sector import SECTOR_SHA256
    base = os.path.dirname(os.path.abspath(__file__))
    try:
        sha = subprocess.run(
            ["git", "-C", os.path.dirname(base), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except Exception:
        sha = "unknown"
    hashes = {}
    for name in ("live_path.py", "assertions.py", "decompose.py",
                 "packets.py", "replay.py", "ranking.py", "sector.py",
                 "portfolio.py") + tuple(extra_files):
        path = os.path.join(base, name)
        if os.path.exists(path):
            with open(path, "rb") as f:
                hashes[name] = hashlib.sha256(f.read()).hexdigest()
    return {"repo_git_sha": sha or "unknown",
            "reference_sha256": hashes,
            "sector_sha256": SECTOR_SHA256}


def append_portfolio_packet(packet_log: "PacketLog", packet: dict) -> dict:
    """Append a portfolio-decision packet (schema slice2-v2). Required keys
    are validated; the packet is never rewritten after append."""
    required = ("decision_time", "computed_at", "contenders", "contested",
                "n_candidates", "free_slots_at_t", "decisions",
                "sector_counts_before", "sector_counts_after",
                "n_open_before", "n_open_after", "state_event_log_range",
                "data_vintage", "engine_version")
    missing = [k for k in required if k not in packet]
    if missing:
        raise ValueError(f"portfolio packet missing keys: {missing}")
    for d in packet["decisions"]:
        if d["decision"] not in PORTFOLIO_DECISION_CODES:
            raise ValueError(f"bad decision code: {d['decision']}")
    packet = dict(packet)
    packet["packet_schema"] = PORTFOLIO_PACKET_SCHEMA
    packet["type"] = "portfolio_decision"
    line = _canonical(packet)
    with open(packet_log.path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())
    return packet


def build_portfolio_packet(*, decision_time, contenders: list, decisions: list,
                           free_slots_at_t: int, n_open_before: int,
                           n_open_after: int, sector_counts_before: dict,
                           sector_counts_after: dict, seq_before: int,
                           seq_after: int, vintage: dict, engine: dict) -> dict:
    """Assemble (not append) a slice2-v2 portfolio-decision packet.

    contenders: the contender dicts passed to decide_entries (must carry
    signal_id, symbol, rs_score, universe_order, entry_px, stop_px, tp1_px;
    may carry rs_unavailable / rs_unavailable_reason).
    decisions: the decision dicts returned by decide_entries, in order.
    """
    from datetime import datetime, timezone
    from pine_live.sector import sector_of

    packet_contenders = []
    for c in contenders:
        rs_unav = bool(c.get("rs_unavailable", False))
        packet_contenders.append({
            "signal_id": c["signal_id"],
            "symbol": c["symbol"],
            "sector": sector_of(c["symbol"]),
            "rs_score": float(c["rs_score"]),
            "rs_unavailable": rs_unav,
            "rs_unavailable_reason": c.get("rs_unavailable_reason"),
            "universe_order": int(c["universe_order"]),
            "entry_px": float(c["entry_px"]),
            "stop_px": float(c["stop_px"]),
            "tp1_px": (float(c["tp1_px"])
                       if c.get("tp1_px") is not None else None),
        })
    return {
        "decision_time": pd.Timestamp(decision_time).isoformat(),
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "contenders": packet_contenders,
        "contested": bool(decisions[0]["contested"]) if decisions else False,
        "n_candidates": len(contenders),
        "free_slots_at_t": int(free_slots_at_t),
        "decisions": [
            {
                "signal_id": d["signal_id"],
                "symbol": d["symbol"],
                "decision": d["decision"],
                "reason_detail": d["reason_detail"],
                "rs_score": float(d["rs_score"]),
                "rank": int(d["rank"]),
                "contested": bool(d["contested"]),
                "marked_equity_at_t": float(d["marked_equity_at_t"]),
            }
            for d in decisions
        ],
        "sector_counts_before": dict(sector_counts_before),
        "sector_counts_after": dict(sector_counts_after),
        "n_open_before": int(n_open_before),
        "n_open_after": int(n_open_after),
        "state_event_log_range": [int(seq_before), int(seq_after)],
        "data_vintage": dict(vintage),
        "engine_version": dict(engine),
    }


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def snapshot_id_for(symbol: str, last_bar_start_iso: str) -> str:
    safe = last_bar_start_iso.replace(":", "").replace("+", "p").replace("-", "m")
    return f"{symbol}_{safe}"


def write_snapshot(symbol: str, bars: pd.DataFrame, snapshot_dir: str) -> dict:
    """Persist the exact OHLCV frame used. Returns {path, sha256, n_bars}."""
    os.makedirs(snapshot_dir, exist_ok=True)
    records = [
        {
            "t": ts.isoformat(),
            "o": float(row["Open"]),
            "h": float(row["High"]),
            "l": float(row["Low"]),
            "c": float(row["Close"]),
            "v": float(row["Volume"]),
        }
        for ts, row in bars[["Open", "High", "Low", "Close", "Volume"]].iterrows()
    ]
    payload = {
        "symbol": symbol,
        "index_tz": str(bars.index.tz),
        "bars": records,
    }
    body = _canonical(payload)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    snap_id = snapshot_id_for(symbol, records[-1]["t"])
    path = os.path.join(snapshot_dir, f"{snap_id}.json")
    # Immutable: never overwrite an existing snapshot with different content.
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
        if hashlib.sha256(existing.encode("utf-8")).hexdigest() != digest:
            raise RuntimeError(
                f"snapshot {path} exists with different content; "
                "history is never rewritten"
            )
        return {"path": path, "sha256": digest, "n_bars": len(records)}
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
        f.flush()
        os.fsync(f.fileno())
    return {"path": path, "sha256": digest, "n_bars": len(records)}


def load_snapshot(path: str, expected_sha256: str) -> pd.DataFrame:
    """Rebuild the bar frame; the hash must match or replay refuses."""
    with open(path, "r", encoding="utf-8") as f:
        body = f.read()
    if hashlib.sha256(body.encode("utf-8")).hexdigest() != expected_sha256:
        raise RuntimeError(f"snapshot hash mismatch: {path}")
    payload = json.loads(body)
    idx = pd.DatetimeIndex(
        [pd.Timestamp(r["t"]) for r in payload["bars"]],
        tz=payload["index_tz"],
    )
    return pd.DataFrame(
        {
            "Open": [r["o"] for r in payload["bars"]],
            "High": [r["h"] for r in payload["bars"]],
            "Low": [r["l"] for r in payload["bars"]],
            "Close": [r["c"] for r in payload["bars"]],
            "Volume": [r["v"] for r in payload["bars"]],
        },
        index=idx,
    )


class PacketLog:
    """Append-only JSONL decision log. One packet per evaluated bar."""

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    def append(self, packet: dict) -> dict:
        packet = dict(packet)
        packet["packet_schema"] = PACKET_SCHEMA_VERSION
        line = _canonical(packet)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
        return packet

    def read_all(self) -> list:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]


# --- Slice 5: live exit packets -------------------------------------------

EXIT_PACKET_SCHEMA = "slice5-v1"

# Snapshot record keys for the bars the exit walk used: t = ISO timestamp,
# o/h/l/c/v = OHLCV, then the indicator columns the walk reads.
EXIT_BAR_RECORD_KEYS = ("t", "o", "h", "l", "c", "v",
                        "e21", "e55", "e200", "atr")

REQUIRED_EXIT_PACKET_KEYS = (
    "decision_time", "computed_at", "symbol", "signal_id", "cost",
    "position", "evaluation", "trigger", "exit", "pre_exit_state",
    "post_exit_state",
    "realized_after", "bars_snapshot_ref", "data_vintage", "engine_version",
)


def _safe_exit_id(s: str) -> str:
    return (str(s).replace(":", "").replace("+", "p").replace("-", "m")
            .replace(".", "d").replace("T", "t"))


def write_exit_bars_snapshot(symbol: str, records: list,
                             snapshot_dir: str,
                             index_tz: str | None = None) -> dict:
    """Persist the exact bars the exit walk used (OHLCV + indicators).

    ``records``: list of dicts with keys ``EXIT_BAR_RECORD_KEYS``,
    ``t`` an ISO timestamp. ``index_tz``: the IANA tz name of the frame
    the records came from (e.g. ``America/New_York``) — required for
    correct DST handling on load; a fixed offset from the first bar is
    WRONG when the snapshot spans a DST boundary, because the loader
    converts every bar to it. Canonicalized, sha256-pinned, fsync'd —
    the same durability as entry snapshots. An existing snapshot is never
    rewritten: a content mismatch raises (history is immutable). Returns
    ``{"path", "sha256", "n_bars"}``.
    """
    symbol = str(symbol).upper()
    if not records:
        raise ValueError(f"{symbol}: no bars to snapshot")
    for r in records:
        missing = [k for k in EXIT_BAR_RECORD_KEYS if k not in r]
        if missing:
            raise ValueError(f"{symbol}: snapshot record missing {missing}")
    os.makedirs(snapshot_dir, exist_ok=True)
    if index_tz is None:
        # Fallback: the first bar's offset. Only correct when the snapshot
        # does not span a DST boundary; callers should pass the frame tz.
        first_tz = pd.Timestamp(records[0]["t"]).tz
        index_tz = str(first_tz) if first_tz is not None else "UTC"
    payload = {"symbol": symbol, "kind": "exit_walk_bars",
               "index_tz": index_tz,
               "bars": records}
    body = _canonical(payload)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    snap_id = (f"{symbol}_exit_{_safe_exit_id(records[0]['t'])}"
               f"_{_safe_exit_id(records[-1]['t'])}")
    path = os.path.join(snapshot_dir, f"{snap_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
        if hashlib.sha256(existing.encode("utf-8")).hexdigest() != digest:
            raise RuntimeError(
                f"exit snapshot {path} exists with different content; "
                "history is never rewritten")
        return {"path": path, "sha256": digest, "n_bars": len(records)}
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
        f.flush()
        os.fsync(f.fileno())
    return {"path": path, "sha256": digest, "n_bars": len(records)}


def load_exit_snapshot(path: str, expected_sha256: str) -> pd.DataFrame:
    """Rebuild the exit-walk bar frame. The hash must match or replay
    refuses: a tampered snapshot can never silently change an exit."""
    with open(path, "r", encoding="utf-8") as f:
        body = f.read()
    if hashlib.sha256(body.encode("utf-8")).hexdigest() != expected_sha256:
        raise RuntimeError(f"exit snapshot hash mismatch: {path}")
    payload = json.loads(body)
    recs = payload["bars"]
    idx = pd.DatetimeIndex(
        [pd.Timestamp(r["t"]) for r in recs], tz=payload["index_tz"])
    return pd.DataFrame({
        "Open": [float(r["o"]) for r in recs],
        "High": [float(r["h"]) for r in recs],
        "Low": [float(r["l"]) for r in recs],
        "Close": [float(r["c"]) for r in recs],
        "Volume": [float(r["v"]) for r in recs],
        "e21": [float(r["e21"]) for r in recs],
        "e55": [float(r["e55"]) for r in recs],
        "e200": [float(r["e200"]) for r in recs],
        "atr": [float(r["atr"]) for r in recs],
    }, index=idx)


def build_exit_packet(*, decision_time: str, computed_at: str, cost: float,
                      position: dict, evaluation: dict, trigger: dict,
                      exit_detail: dict, pre_exit_state: dict,
                      post_exit_state: dict,
                      realized_after: float, snapshot_ref: dict,
                      vintage: dict, engine: dict) -> dict:
    """Assemble a slice-5 exit decision packet.

    ``position``: the exact pre-exit position fields (entry_px, stop_px,
    tp1_px, entry_time, risk_dollars, risk_frac, size, sector,
    signal_id). ``evaluation``: the exit walk report. ``trigger``:
    trigger bar/reason/fill. ``exit_detail``: exit_px, R breakdown,
    hold_bars, net_r. ``pre_exit_state``: the full portfolio
    ``to_dict()`` immediately before THIS exit (sequential when several
    exits share a timestamp). ``post_exit_state``: the full
    ``to_dict()`` immediately after THIS exit — the replay target.
    ``realized_after``: from the applied close event (redundant with
    post_exit_state, kept for direct assertions).
    """
    packet = {
        "packet_schema": EXIT_PACKET_SCHEMA,
        "decision_time": decision_time,
        "computed_at": computed_at,
        "symbol": str(position["symbol"]).upper(),
        "signal_id": position["signal_id"],
        "cost": float(cost),
        "position": {
            "entry_px": float(position["entry_px"]),
            "stop_px": float(position["stop_px"]),
            "tp1_px": float(position["tp1_px"]),
            "entry_time": str(position["entry_time"]),
            "risk_dollars": float(position["risk_dollars"]),
            "risk_frac": float(position["risk_frac"]),
            "size": float(position["size"]),
            "sector": str(position["sector"]),
        },
        "evaluation": dict(evaluation),
        "trigger": dict(trigger),
        "exit": dict(exit_detail),
        "pre_exit_state": dict(pre_exit_state),
        "post_exit_state": dict(post_exit_state),
        "realized_after": float(realized_after),
        "bars_snapshot_ref": dict(snapshot_ref),
        "data_vintage": dict(vintage),
        "engine_version": dict(engine),
    }
    return packet


def append_exit_packet(exit_packet_log: str, packet: dict) -> dict:
    """Validate and fsync-append an exit packet to its own JSONL log.

    Fail closed on malformed packets: a bad packet never reaches the log,
    and the error is raised to the caller (the live loop catches it, logs
    it, and leaves state untouched).
    """
    packet = dict(packet)
    missing = [k for k in REQUIRED_EXIT_PACKET_KEYS if k not in packet]
    if missing:
        raise RuntimeError(
            f"exit packet missing required keys {missing}; not logged")
    packet["packet_schema"] = EXIT_PACKET_SCHEMA
    line = _canonical(packet)
    os.makedirs(os.path.dirname(os.path.abspath(exit_packet_log)),
                exist_ok=True)
    with open(exit_packet_log, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())
    return packet


def read_exit_packets(exit_packet_log: str) -> list:
    """Read back the exit packet log (empty list if it does not exist)."""
    if not os.path.exists(exit_packet_log):
        return []
    with open(exit_packet_log, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def engine_with_extra_files(engine: dict, extra_files=()) -> dict:
    """Copy of an engine_version dict with extra pine_live module hashes
    pinned (e.g. ``exits.py`` for exit packets)."""
    base = os.path.dirname(os.path.abspath(__file__))
    hashes = dict(engine.get("reference_sha256", {}))
    for name in extra_files:
        path = os.path.join(base, name)
        if os.path.exists(path):
            with open(path, "rb") as f:
                hashes[name] = hashlib.sha256(f.read()).hexdigest()
    out = dict(engine)
    out["reference_sha256"] = hashes
    return out
