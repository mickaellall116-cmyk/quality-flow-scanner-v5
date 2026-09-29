#!/usr/bin/env python3
"""Shadow hold/sell advisor — observation-only research run.

Reads open paper positions from ``paper_state/portfolio.json`` (READ-ONLY),
classifies each per SHADOW_ADVISOR_SPEC.md, and appends to the append-only
``research/shadow_log.jsonl``. Then processes newly closed canonical trades
into HYPOTHETICAL counterfactual records (``research/counterfactual.jsonl``).

This script NEVER writes to paper_state/, NEVER affects positions, fills,
runner decisions, gate thresholds, or alerts. It has no order path and no
alert path. Run on demand (not scheduled); safe to re-run (deduplicated).

Usage: python3 -m pine_live.research.run_shadow [--state-dir D] [--out-dir D]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pine_live.research import shadow  # noqa: E402

STATE_DIR_DEFAULT = os.path.join(REPO_ROOT, "pine_live", "paper_state")
OUT_DIR_DEFAULT = os.path.join(REPO_ROOT, "pine_live", "research")
HYPOTHETICAL_TAG = "HYPOTHETICAL — not a real fill; research only"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _read_jsonl(path: str) -> list:
    out = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    except OSError:
        pass
    return out


def _append_jsonl(path: str, rec: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def _parse_ts(s) -> datetime | None:
    if not isinstance(s, str):
        return None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def default_bars_provider(symbol: str) -> list | None:
    """Read-only 4H OHLC via yfinance. Returns ascending
    [{"t","o","h","l","c"}] or None on any failure. No state mutated."""
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        df = yf.download(symbol, period="90d", interval="4h",
                         auto_adjust=False, progress=False)
    except Exception:
        return None
    if df is None or len(df) == 0:
        return None
    # Flatten possible MultiIndex columns.
    if hasattr(df.columns, "levels"):
        try:
            df.columns = [c[0] if isinstance(c, tuple) else c
                          for c in df.columns]
        except Exception:
            return None
    out = []
    for ts, row in df.iterrows():
        try:
            o, h, l, c = (float(row["Open"]), float(row["High"]),
                          float(row["Low"]), float(row["Close"]))
        except (KeyError, TypeError, ValueError):
            continue
        if not all(v == v and abs(v) != float("inf")
                   for v in (o, h, l, c)) or c <= 0:
            continue
        t = ts.tz_convert("UTC") if ts.tzinfo is not None else ts.tz_localize("UTC")
        out.append({"t": t.isoformat(), "o": o, "h": h, "l": l, "c": c})
    out.sort(key=lambda b: b["t"])
    return out or None


def classify_positions(*, state_dir: str, out_dir: str,
                       bars_provider=default_bars_provider) -> dict:
    """Classify open positions; append new shadow_log.jsonl records."""
    portfolio = _read_json(os.path.join(state_dir, "portfolio.json"), {})
    positions = (portfolio.get("portfolio", {}) or {}).get("positions", {})
    if not isinstance(positions, dict):
        positions = {}

    log_path = os.path.join(out_dir, "shadow_log.jsonl")
    seen = set()
    for rec in _read_jsonl(log_path):
        if isinstance(rec, dict):
            seen.add((rec.get("signal_id"), rec.get("bar_time"),
                      rec.get("label")))
    run_date = _utcnow_iso()[:10]
    counts = {"classified": 0, "insufficient_data": 0, "skipped": 0}

    for _key, pos in positions.items():
        if not isinstance(pos, dict):
            counts["skipped"] += 1
            continue
        signal_id = pos.get("signal_id")
        symbol = pos.get("symbol")
        entry_time = pos.get("entry_time")
        if not signal_id or not symbol:
            counts["skipped"] += 1
            continue
        entry_dt = _parse_ts(entry_time)
        bars = None
        try:
            bars = bars_provider(symbol)
        except Exception:
            bars = None
        usable = None
        if bars and entry_dt:
            usable = [b for b in bars
                      if (_parse_ts(b.get("t")) or datetime.min.replace(
                          tzinfo=timezone.utc)) > entry_dt]
            usable = [{"t": b["t"], "c": b["c"]} for b in usable]
        inputs = shadow.compute_inputs(pos, usable) if usable else None
        label, rule_id = shadow.classify(inputs)
        if label == shadow.SENTINEL_INSUFFICIENT_DATA:
            dedup_key = (signal_id, None, label, run_date)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            _append_jsonl(log_path, {
                "ts": _utcnow_iso(), "bar_time": None,
                "signal_id": signal_id, "symbol": symbol,
                "label": label, "rule_id": None, "inputs": None,
                "note": "bars unavailable; not a classification",
            })
            counts["insufficient_data"] += 1
            continue
        bar_time = inputs["bar_time"]
        if (signal_id, bar_time, label) in seen:
            continue
        seen.add((signal_id, bar_time, label))
        _append_jsonl(log_path, {
            "ts": _utcnow_iso(), "bar_time": bar_time,
            "signal_id": signal_id, "symbol": symbol,
            "label": label, "rule_id": rule_id, "inputs": inputs,
        })
        counts["classified"] += 1
    return counts


def process_counterfactuals(*, state_dir: str, out_dir: str,
                             bars_provider=default_bars_provider) -> dict:
    """Counterfactual accounting for newly closed canonical trades."""
    trades_path = os.path.join(state_dir, "ledger", "trades.jsonl")
    trades = _read_jsonl(trades_path)
    state_path = os.path.join(out_dir, "counterfactual_state.json")
    st = _read_json(state_path, {})
    next_index = st.get("next_index", 0) if isinstance(st, dict) else 0
    new_trades = trades[next_index:] if isinstance(next_index, int) else []

    shadow_recs = _read_jsonl(os.path.join(out_dir, "shadow_log.jsonl"))
    cf_path = os.path.join(out_dir, "counterfactual.jsonl")
    counts = {"ok": 0, "no_candidate": 0, "insufficient_data": 0}

    for tr in new_trades:
        if not isinstance(tr, dict):
            continue
        signal_id = tr.get("signal_id")
        symbol = tr.get("symbol")
        exit_time = _parse_ts(tr.get("exit_time"))
        entry_px, stop_px = tr.get("entry_px"), tr.get("stop_px")
        actual_4 = tr.get("net_r_4bps")
        actual_25 = tr.get("net_r_25bps")
        base = {
            "ts": _utcnow_iso(),
            "signal_id": signal_id, "symbol": symbol,
            "exit_time": tr.get("exit_time"),
            "actual_net_r_4bps": actual_4,
            "actual_net_r_25bps": actual_25,
            "regime": tr.get("regime"),
            "tag": HYPOTHETICAL_TAG,
        }
        # Earliest EXIT-CANDIDATE strictly before the canonical exit.
        cand = None
        if signal_id and exit_time:
            for rec in shadow_recs:
                if not isinstance(rec, dict):
                    continue
                if (rec.get("signal_id") == signal_id
                        and rec.get("label") == "EXIT-CANDIDATE"):
                    bt = _parse_ts(rec.get("bar_time"))
                    if bt and bt < exit_time and (
                            cand is None or bt < cand):
                        cand = bt
        base["first_exit_candidate_bar_time"] = (
            cand.isoformat() if cand else None)
        base["exit_candidate_before_exit"] = cand is not None

        if cand is None:
            # Guidance would have held through the canonical exit.
            def _zero_or_none(v):
                return 0.0 if isinstance(v, (int, float)) and v == v else None
            base.update({
                "status": "no_candidate",
                "hypothetical_exit_bar_time": None,
                "hypothetical_exit_px": None,
                "hypothetical_gross_r": None,
                "hypothetical_net_r_4bps": actual_4,
                "hypothetical_net_r_25bps": actual_25,
                "delta_r_4bps": _zero_or_none(actual_4),
                "delta_r_25bps": _zero_or_none(actual_25),
            })
            _append_jsonl(cf_path, base)
            counts["no_candidate"] += 1
            continue

        fail = dict(base, status="insufficient_data",
                    hypothetical_exit_bar_time=None,
                    hypothetical_exit_px=None,
                    hypothetical_gross_r=None,
                    hypothetical_net_r_4bps=None,
                    hypothetical_net_r_25bps=None,
                    delta_r_4bps=None, delta_r_25bps=None)
        try:
            bars = bars_provider(symbol) if symbol else None
        except Exception:
            bars = None
        if not bars or exit_time is None:
            _append_jsonl(cf_path, fail)
            counts["insufficient_data"] += 1
            continue
        nxt = None
        for b in bars:
            bt = _parse_ts(b.get("t"))
            if bt and bt > cand:
                if bt > exit_time:
                    nxt = None
                    break
                nxt = b
                break
        if nxt is None:
            _append_jsonl(cf_path, fail)
            counts["insufficient_data"] += 1
            continue
        hyp = shadow.hypothetical_exit_r(
            entry_px=entry_px, stop_px=stop_px,
            next_open_px=nxt.get("o"))
        if hyp is None:
            _append_jsonl(cf_path, fail)
            counts["insufficient_data"] += 1
            continue
        h4, h25 = hyp["hypothetical_net_r_4bps"], hyp["hypothetical_net_r_25bps"]
        base.update({
            "status": "ok",
            "hypothetical_exit_bar_time": nxt.get("t"),
            "hypothetical_exit_px": nxt.get("o"),
            "hypothetical_gross_r": hyp["hypothetical_gross_r"],
            "hypothetical_net_r_4bps": h4,
            "hypothetical_net_r_25bps": h25,
            "delta_r_4bps": (h4 - actual_4)
            if isinstance(actual_4, (int, float)) else None,
            "delta_r_25bps": (h25 - actual_25)
            if isinstance(actual_25, (int, float)) else None,
        })
        _append_jsonl(cf_path, base)
        counts["ok"] += 1

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump({"next_index": len(trades)}, f)
    return counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state-dir", default=STATE_DIR_DEFAULT)
    ap.add_argument("--out-dir", default=OUT_DIR_DEFAULT)
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    c1 = classify_positions(state_dir=args.state_dir, out_dir=args.out_dir)
    c2 = process_counterfactuals(state_dir=args.state_dir,
                                 out_dir=args.out_dir)
    print(json.dumps({"classify": c1, "counterfactual": c2}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
