"""V5.4 forward-test FVG-entry paper sidecar.

Paper-only variant tracker: the Hybrid buy signal OR the V3.7 FVG
sub-signal ("Use FVG as Real Entry" semantics), tracked through the
IDENTICAL frozen Mode B exit stack. Exists to accumulate out-of-sample
data on the FVG variant ahead of the ~100-signal verdict (late Nov 2026).

APPROVED by Mike 2026-09-23. Additive and fail-closed:
- Own state file (v54_forward/fvg_sidecar_state.json) and own append-only
  log (v54_forward/fvg_sidecar.jsonl). NEVER writes to forward_test.jsonl,
  state.json, latest_v54_signals.json, or any frozen artifact.
- Only entry-signal generation differs from the frozen system; exits use
  the frozen ModeBTracker with the same V5.3 EXIT detection the harness
  uses, so the entry variant is the isolated difference.
- Every record carries "paper": true and variant "hybrid+fvg-entry".
- run_sidecar_cycle never raises: per-symbol errors are logged to the
  sidecar log and swallowed; a cycle-level exception returns
  {"ok": False, ...} instead of propagating into the harness.

FVG semantics ported 1:1 from Quality-Flow-System-V3.7.pine (lines
200-207), via pine_entry_timing_backtest/run_entry_timing.py
(port functions copied here with attribution so this module is
self-contained):
    fvgBuy = trendBull and inBullFvgSupport and close > ema21
             and volumeOK and safeToEnter
    extraEntry = useFvgAsEntry and fvgBuy
    buySignal  = confirmedBuy or breakoutBuy or readyBuy or extraEntry
No priority order (pure OR). Entry mechanics (next-bar-open fill,
stop = signal-bar close - 1.5*ATR, TP1 = entry + 2.0*ATR) are identical
for extra signals -- only which bars fire changes.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
import pine_backtest as pb
from v54_exit_tracker import ModeBTracker, close_summary

VARIANT = "hybrid+fvg-entry"
WATCHLIST_14 = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
                "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
STATE_PATH = os.path.join(BASE_DIR, "v54_forward", "fvg_sidecar_state.json")
LOG_PATH = os.path.join(BASE_DIR, "v54_forward", "fvg_sidecar.jsonl")
MIN_BARS = pb.WARMUP + 3  # indicators need WARMUP; +3 for signal/entry/next bar

# Ported Pine input defaults (Mike's live V3.7 inputs).
SWEEP_LB = 20
BZ_W = 0.35
NEAR_ATR = 0.50


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# FVG port (copied from pine_entry_timing_backtest/run_entry_timing.py,
# which ports Quality-Flow-System-V3.7.pine lines 200-207, 224-226, 1:1).
# ---------------------------------------------------------------------------

def add_entry_timing_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Port of the Pine smart-money geometry feeding the three sub-signals.

    Requires pb.add_pine_indicators(df) to have run first (needs e21, atr).
    """
    out = df.copy()
    n = len(out)
    low = out["Low"].to_numpy()
    high = out["High"].to_numpy()
    close = out["Close"].to_numpy()
    e21 = out["e21"].to_numpy()
    atr = out["atr"].to_numpy()

    # bullSweep = low < lowest(low,20)[1] and close > lowest(low,20)[1]
    sweep_ref = out["Low"].rolling(SWEEP_LB).min().shift(1).to_numpy()
    out["bullSweep"] = (low < sweep_ref) & (close > sweep_ref)

    # FVG state machine: bullFVG = low > high[2]; vars persist until next FVG
    last_lo, last_hi = np.nan, np.nan
    in_fvg = np.zeros(n, dtype=bool)
    use_fvg = np.zeros(n, dtype=bool)
    near = np.zeros(n, dtype=bool)
    for i in range(n):
        if i >= 2 and low[i] > high[i - 2]:
            last_lo, last_hi = high[i - 2], low[i]
        c, a, e = close[i], atr[i], e21[i]
        if np.isnan(a) or np.isnan(e):
            continue
        uf = (not np.isnan(last_lo)
              and abs(c - last_hi) <= a * 3
              and last_hi <= c * 1.08)
        use_fvg[i] = uf
        ez_lo, ez_hi = e - a * BZ_W, e + a * BZ_W
        zlo = min(ez_lo, last_lo) if uf else ez_lo
        zhi = max(ez_hi, last_hi) if uf else ez_hi
        in_zone = zlo <= c <= zhi
        near[i] = (abs(c - zhi) <= a * NEAR_ATR
                   or abs(c - zlo) <= a * NEAR_ATR
                   or in_zone)
        if not np.isnan(last_lo):
            in_fvg[i] = bool(low[i] <= last_hi and c >= last_lo)
    out["inBullFvgSupport"] = in_fvg
    out["nearBuyZone"] = near
    return out


def fvg_sub_signal(df: pd.DataFrame, i: int) -> bool:
    """The Pine fvgBuy sub-signal on completed bar i (point-in-time)."""
    r = df.iloc[i]
    if pd.isna(r["e200"]) or pd.isna(r["atr_base"]) or pd.isna(r["adx"]):
        return False
    close, vol = r["Close"], r["Volume"]
    volume_ok = vol > r["vol_ma"]
    safe = not (close > r["e9"] + r["atr"] * pb.HOT_ATR)
    trend_bull = r["e21"] > r["e55"] and close > r["e200"]
    return bool(trend_bull and r["inBullFvgSupport"] and close > r["e21"]
                and volume_ok and safe)


def scan_signals(df: pd.DataFrame, start_pos: int,
                 end_pos: int) -> List[Tuple[int, pd.Timestamp, bool, bool]]:
    """Scan positional bars [start_pos, end_pos) for the augmented signal.

    Returns (pos, ts, canonical_hybrid, fvg_sub) for each firing bar.
    Pure function: no state, no I/O. Shared by the live cycle and --verify.
    """
    out: List[Tuple[int, pd.Timestamp, bool, bool]] = []
    lo = max(start_pos, pb.WARMUP)
    for i in range(lo, end_pos):
        base = bool(pb.pine_buy_signal(df, i))
        fvg = fvg_sub_signal(df, i)
        if base or fvg:
            out.append((i, df.index[i], base, fvg))
    return out


def make_signal_record(sym: str, ts: pd.Timestamp, row: pd.Series,
                       base: bool, fvg: bool) -> Dict[str, Any]:
    """Paper signal record. Entry fills at next bar open (plan only here)."""
    close = float(row["Close"])
    atr = float(row["atr"])
    stop = close - atr * pb.SL_ATR
    return {
        "type": "signal",
        "paper": True,
        "variant": VARIANT,
        "signal_id": f"FVG-{sym}-{ts.isoformat()}",
        "symbol": sym,
        "timeframe": "4h",
        "signal_bar_start_at": ts.isoformat(),
        "signal_bar_close_at": ts.isoformat(),
        "close": round(close, 4),
        "atr": round(atr, 4),
        "stop": round(stop, 4),
        "tp1_plan": f"entry + {pb.TP_ATR} * ATR(signal bar)",
        "risk_reward_plan": round(pb.TP_ATR / pb.SL_ATR, 2),
        "entry_plan": "next-bar-open",
        "canonical_hybrid": base,
        "fvg_subsignal": fvg,
        "fvg_marginal": bool(fvg and not base),
        "logged_at": _now(),
    }


# ---------------------------------------------------------------------------
# State + log (own files; never the frozen ones).
# ---------------------------------------------------------------------------

def _blank_state() -> Dict[str, Any]:
    return {"seen_signal_ids": [], "last_scan_bar": {}, "pending": {},
            "positions": {}, "snapshots": {}, "close_logged": {},
            "runs": 0, "last_run": None}


def _load_state(path: str = STATE_PATH) -> Dict[str, Any]:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return _blank_state()


def _save_state(state: Dict[str, Any], path: str = STATE_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, default=str)
    os.replace(tmp, path)


def _append(record: Dict[str, Any], path: str = LOG_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str) + "\n")


def _busy(state: Dict[str, Any], tracker: ModeBTracker, sym: str) -> bool:
    if any(p["symbol"] == sym for p in state["pending"].values()):
        return True
    return any(p["symbol"] == sym and p["status"] != "closed"
               for p in tracker.positions.values())


def _make_sink() -> Callable[[Dict[str, Any]], None]:
    def _sink(event: Dict[str, Any]) -> None:
        event = dict(event)
        sid = event.pop("signal_id")
        _append({"type": "event", "paper": True, "variant": VARIANT,
                 "signal_id": sid, **event, "logged_at": _now()})
    return _sink


def _resolve_v53_state_fn() -> Callable[..., Optional[str]]:
    """V5.3 EXIT detection, same function the frozen harness uses.

    Deferred import (no module-level cycle with v54_forward_harness).
    Returns None for every bar if the import fails -- the tracker still
    enforces stops / TP1 / time exits; only the armed scanner-EXIT path
    stays dormant, and the outage is logged once per cycle.
    """
    try:
        from v54_forward_harness import v53_state_for_bar

        def _fn(sym: str, df: pd.DataFrame, market: Optional[pd.DataFrame],
                regime: Dict[str, Any], ts: pd.Timestamp) -> Optional[str]:
            try:
                return v53_state_for_bar(sym, df, market, regime, ts)
            except Exception:
                return None

        _fn.available = True  # type: ignore[attr-defined]
        return _fn
    except Exception:
        def _none(*a: Any, **k: Any) -> Optional[str]:
            return None

        _none.available = False  # type: ignore[attr-defined]
        return _none


# ---------------------------------------------------------------------------
# Live cycle.
# ---------------------------------------------------------------------------

def _process_symbol(sym: str, df: pd.DataFrame, market_full: Optional[pd.DataFrame],
                    regime: Dict[str, Any],
                    v53_state_fn: Callable[..., Optional[str]],
                    state: Dict[str, Any], seen: set,
                    tracker: ModeBTracker, result: Dict[str, Any]) -> None:
    if df is None or df.empty or len(df) < MIN_BARS:
        _append({"type": "note", "paper": True, "variant": VARIANT,
                 "symbol": sym, "note": "insufficient_history",
                 "bars": 0 if df is None else len(df), "logged_at": _now()})
        return
    if "Volume" not in df.columns or df["Volume"].isna().all():
        _append({"type": "note", "paper": True, "variant": VARIANT,
                 "symbol": sym, "note": "no_volume", "logged_at": _now()})
        return

    df = pb.add_pine_indicators(df)
    df = add_entry_timing_columns(df)

    # 1. New signals on completed bars since the last scan. The final bar
    #    may still be forming, so it never generates a signal.
    last_scan_iso = state["last_scan_bar"].get(sym)
    if last_scan_iso is None:
        # First run: seed forward-only. Historical bars never generate
        # sidecar signals (no backfill contamination); only future bars do.
        state["last_scan_bar"][sym] = df.index[-2].isoformat()
        _append({"type": "note", "paper": True, "variant": VARIANT,
                 "symbol": sym, "note": "seeded_forward_only",
                 "seed_bar": df.index[-2].isoformat(), "logged_at": _now()})
    else:
        start_pos = int(df.index.searchsorted(pd.Timestamp(last_scan_iso),
                                              side="right"))
        for i, ts, base, fvg in scan_signals(df, start_pos, len(df) - 1):
            sid = f"FVG-{sym}-{ts.isoformat()}"
            if sid in seen:
                continue
            seen.add(sid)
            row = df.iloc[i]
            sig = make_signal_record(sym, ts, row, base, fvg)
            state["snapshots"][sid] = sig
            _append(sig)
            result["new_signals"] += 1
            if _busy(state, tracker, sym):
                _append({"type": "event", "paper": True, "variant": VARIANT,
                         "signal_id": sid, "event": "signal_skipped",
                         "reason": "position already open/pending",
                         "symbol": sym, "logged_at": _now()})
            else:
                state["pending"][sid] = {
                    "symbol": sym,
                    "signal_bar_start": ts.isoformat(),
                    "stop": sig["stop"],
                    "atr": sig["atr"],
                }
                _append({"type": "event", "paper": True, "variant": VARIANT,
                         "signal_id": sid, "event": "pending_entry",
                         "signal_bar_start": ts.isoformat(),
                         "logged_at": _now()})
        state["last_scan_bar"][sym] = df.index[-2].isoformat()

    # 2. Pending entries: open at the first bar after the signal bar
    #    (same convention as the frozen harness).
    entry_bars: Dict[str, Any] = {}
    for sid, pend in list(state["pending"].items()):
        if pend["symbol"] != sym:
            continue
        sig_start = pd.Timestamp(pend["signal_bar_start"])
        newbars = df[df.index > sig_start]
        if newbars.empty:
            continue
        ts = newbars.index[0]
        entry = float(newbars.iloc[0]["Open"])
        stop = float(pend["stop"])
        tp1 = entry + float(pend["atr"]) * pb.TP_ATR
        pos = tracker.open_position(
            {"signal_id": sid, "symbol": sym, "v54_grade": None,
             "stop": stop, "tp1": tp1},
            entry, ts.isoformat())
        if pos is None:
            _append({"type": "event", "paper": True, "variant": VARIANT,
                     "signal_id": sid, "event": "entry_skipped",
                     "reason": "entry <= structural stop",
                     "logged_at": _now()})
        else:
            result["opened"] += 1
            entry_bars[sid] = ts
        del state["pending"][sid]

    # 3. Open positions: walk new completed bars through the frozen
    #    Mode B tracker with the same V5.3 EXIT detection as the harness.
    for sid, pos in list(tracker.positions.items()):
        if pos["symbol"] != sym or pos["status"] == "closed":
            continue
        if sid in entry_bars:
            newbars = df[df.index >= entry_bars[sid]]
        else:
            last = pos.get("last_processed_bar") or pos.get("entry_bar")
            newbars = df[df.index > pd.Timestamp(last)] if last else df
        for ts, bar in newbars.iterrows():
            scanner_state = v53_state_fn(sym, df, market_full, regime, ts)
            tracker.process_bar(sid, {
                "bar_id": ts.isoformat(),
                "open": float(bar["Open"]), "high": float(bar["High"]),
                "low": float(bar["Low"]), "close": float(bar["Close"]),
                "scanner_state": scanner_state,
            })


def run_sidecar_cycle(ctx: Any, regime: Dict[str, Any]) -> Dict[str, Any]:
    """One paper sidecar cycle. Never raises.

    ctx: the harness CycleContext (reuses ctx.get_4h / ctx.get_market_4h,
    i.e. the same bars the frozen cycle fetched -- zero extra downloads
    for symbols the harness already pulled).
    """
    started = _now()
    result: Dict[str, Any] = {
        "ok": True, "paper": True, "variant": VARIANT,
        "symbols_scanned": 0, "new_signals": 0, "opened": 0,
        "closed": [], "errors": [],
    }
    try:
        state = _load_state()
        seen = set(state.get("seen_signal_ids", []))
        tracker = ModeBTracker(event_sink=_make_sink())
        tracker.positions = state.get("positions", {})
        v53_state_fn = _resolve_v53_state_fn()
        if not getattr(v53_state_fn, "available", False):
            _append({"type": "note", "paper": True, "variant": VARIANT,
                     "note": "v53_exit_detection_unavailable",
                     "logged_at": _now()})

        try:
            market_full = ctx.get_market_4h()
        except Exception:
            market_full = None

        for sym in WATCHLIST_14:
            try:
                df = ctx.get_4h(sym)
                _process_symbol(sym, df, market_full, regime, v53_state_fn,
                                state, seen, tracker, result)
                result["symbols_scanned"] += 1
            except Exception as exc:  # one symbol never kills the sidecar
                result["errors"].append({"symbol": sym,
                                         "error": str(exc)[:200]})
                _append({"type": "error", "paper": True, "variant": VARIANT,
                         "symbol": sym, "error": str(exc)[:300],
                         "logged_at": _now()})

        for sid, pos in list(tracker.positions.items()):
            if pos["status"] == "closed" and not state["close_logged"].get(sid):
                snap = state["snapshots"].get(sid, {})
                rec = close_summary(pos, snap)
                rec.update({"type": "close", "paper": True, "variant": VARIANT,
                            "logged_at": _now()})
                _append(rec)
                state["close_logged"][sid] = True
                result["closed"].append(sid)

        state["seen_signal_ids"] = sorted(seen)
        state["positions"] = tracker.positions
        state["runs"] = state.get("runs", 0) + 1
        state["last_run"] = started
        _save_state(state)

        finished = _now()
        result["started_at"] = started
        result["finished_at"] = finished
        _append({"type": "cycle", "paper": True, "variant": VARIANT,
                 "started_at": started, "finished_at": finished,
                 "symbols_scanned": result["symbols_scanned"],
                 "new_signals": result["new_signals"],
                 "opened": result["opened"],
                 "closed": result["closed"],
                 "errors": result["errors"]})
    except Exception as exc:  # fail closed: never raise into the harness
        try:
            _append({"type": "error", "paper": True, "variant": VARIANT,
                     "scope": "cycle", "error": str(exc)[:300],
                     "logged_at": _now()})
        except Exception:
            pass
        return {"ok": False, "paper": True, "variant": VARIANT,
                "error": str(exc)[:200]}
    return result


# ---------------------------------------------------------------------------
# --verify: dry-run over cached 4H bars. ZERO writes (no state, no log).
# ---------------------------------------------------------------------------

def _verify() -> int:
    import glob

    print("=== FVG sidecar --verify (dry run, zero writes) ===")
    frozen = os.path.join(BASE_DIR, "v54_forward", "forward_test.jsonl")
    before = (os.path.getsize(frozen), os.path.getmtime(frozen)) \
        if os.path.exists(frozen) else None
    print(f"forward_test.jsonl before: "
          f"{'size=%d mtime=%f' % before if before else 'MISSING'}")
    print(f"sidecar log exists before: {os.path.exists(LOG_PATH)}; "
          f"sidecar state exists before: {os.path.exists(STATE_PATH)}")

    cache = os.path.join(BASE_DIR, "pine_entry_timing_backtest", "cache")
    picks = ["AMD", "PLTR", "QQQ"]  # 3 of the 14-stock watchlist with h4 cache
    all_sigs = []
    for sym in picks:
        path = os.path.join(cache, f"h4_{sym}.pkl")
        if not os.path.exists(path):
            print(f"  {sym}: no cached h4 data, skipped")
            continue
        df = pd.read_pickle(path)
        df = pb.add_pine_indicators(df)
        df = add_entry_timing_columns(df)
        cutoff = df.index.max() - pd.Timedelta(days=7)
        start_pos = max(int(df.index.searchsorted(cutoff, side="left")),
                        pb.WARMUP)
        sigs = scan_signals(df, start_pos, len(df))
        print(f"\n{sym}: {len(df)} cached bars, last={df.index.max()}, "
              f"scanning last 7d from pos {start_pos} -> {len(sigs)} signal(s)")
        for i, ts, base, fvg in sigs:
            row = df.iloc[i]
            sig = make_signal_record(sym, ts, row, base, fvg)
            all_sigs.append(sig)
            print(f"  WOULD LOG signal {sig['signal_id']}")
            print(f"    bar={ts} close={sig['close']} atr={sig['atr']} "
                  f"stop={sig['stop']} canonical={base} fvg={fvg} "
                  f"fvg_marginal={sig['fvg_marginal']}")
    print(f"\n7-day scan total: {len(all_sigs)} FVG-augmented signal(s) "
          f"across {picks} (0 is a valid result: quiet week)")

    # Bonus: 30-day in-memory lifecycle walk (proves the Mode B exit stack
    # end to end, including one synthetic armed-EXIT). No writes.
    print("\n--- 30-day in-memory lifecycle walk (no writes) ---")
    n_trades = 0
    for sym in picks:
        path = os.path.join(cache, f"h4_{sym}.pkl")
        if not os.path.exists(path):
            continue
        df = pd.read_pickle(path)
        df = pb.add_pine_indicators(df)
        df = add_entry_timing_columns(df)
        cutoff = df.index.max() - pd.Timedelta(days=30)
        start_pos = max(int(df.index.searchsorted(cutoff, side="left")),
                        pb.WARMUP)
        sigs = scan_signals(df, start_pos, len(df) - 1)
        tr = ModeBTracker()
        pend: Dict[str, Dict[str, Any]] = {}
        for i, ts, base, fvg in sigs:
            sid = f"VERIFY-{sym}-{ts.isoformat()}"
            row = df.iloc[i]
            pend[sid] = {"ts": ts, "stop": float(row["Close"] - row["atr"]
                                                 * pb.SL_ATR),
                         "atr": float(row["atr"])}
        # walk bars after the earliest signal
        if not pend:
            print(f"  {sym}: no signals in 30d window")
            continue
        first = min(v["ts"] for v in pend.values())
        wdf = df[df.index >= first]
        exited_demo = False
        for k in range(len(wdf)):
            bts, brow = wdf.index[k], wdf.iloc[k]
            for sid, p in list(pend.items()):
                if bts > p["ts"]:
                    entry = float(brow["Open"])
                    tp1 = entry + p["atr"] * pb.TP_ATR
                    pos = tr.open_position(
                        {"signal_id": sid, "symbol": sym, "v54_grade": None,
                         "stop": p["stop"], "tp1": tp1}, entry,
                        bts.isoformat())
                    del pend[sid]
            for sid, pos in list(tr.positions.items()):
                if pos["status"] == "closed":
                    continue
                # synthetic EXIT once, right after +1R arms, to prove the
                # armed-EXIT path (live uses the real V5.3 state instead)
                st = None
                if (not exited_demo and pos.get("plus_1r_armed")
                        and pos["status"] != "closed"):
                    st = "EXIT"
                    exited_demo = True
                tr.process_bar(sid, {"bar_id": bts.isoformat(),
                                     "open": float(brow["Open"]),
                                     "high": float(brow["High"]),
                                     "low": float(brow["Low"]),
                                     "close": float(brow["Close"]),
                                     "scanner_state": st})
        for sid, pos in tr.positions.items():
            if pos["status"] == "closed":
                n_trades += 1
                ex = pos["exit"]
                print(f"  {sym} {sid}: entry={pos['entry']:.2f} "
                      f"stop={pos['stop']:.2f} tp1={pos['tp1']:.2f} -> "
                      f"{ex['reason']} @ {ex['exit_px']:.2f} "
                      f"blended={ex['blended_r']}R "
                      f"(tp1_taken={pos['tp1_taken']}, "
                      f"armed={pos['plus_1r_armed']}, bars={ex['bars_held']})")
            else:
                print(f"  {sym} {sid}: still open "
                      f"(entry={pos['entry']:.2f}, bars_held={pos['bars_held']})")
    print(f"30-day walk: {n_trades} closed paper trade(s) "
          f"(scanner_state=None except one synthetic EXIT)")

    after = (os.path.getsize(frozen), os.path.getmtime(frozen)) \
        if os.path.exists(frozen) else None
    untouched = (before == after)
    print(f"\nforward_test.jsonl after:  "
          f"{'size=%d mtime=%f' % after if after else 'MISSING'}")
    print(f"forward_test.jsonl untouched: {untouched}")
    print(f"sidecar log exists after: {os.path.exists(LOG_PATH)} "
          f"(must be False)")
    print(f"sidecar state exists after: {os.path.exists(STATE_PATH)} "
          f"(must be False)")
    ok = untouched and not os.path.exists(LOG_PATH) \
        and not os.path.exists(STATE_PATH)
    print("VERIFY " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--verify" in sys.argv:
        raise SystemExit(_verify())
    print("v54_fvg_sidecar: import run_sidecar_cycle(ctx, regime); "
          "or run with --verify for a dry run.")
