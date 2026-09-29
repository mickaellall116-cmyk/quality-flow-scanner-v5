"""V5.4 forward-test lone-wolf paper overlay.

Paper-only annotation of the LIVE V5.4 forward-test signals: for each new
canonical V5.4 signal in v54_forward/forward_test.jsonl, compute the
pre-declared lone-wolf filter inputs (P10 definition, reused verbatim --
20-trading-day stock RS vs SPY and sector-ETF RS vs SPY on daily bars,
point-in-time at the signal bar) and log what the filter WOULD have done:

    would_block = (stockRS > 0) and (sectorRS <= 0)

Exists to forward-validate the lone-wolf confirmatory result
(pine_lonewolf_backtest/: MAYBE (strong), +0.108R pooled / +0.144R OOS,
blocked PASS on lookback sensitivity). At the ~50-signal checkpoint
(late Oct 2026) the overlay log + closed-trade outcomes give a realized
blocked-vs-allowed comparison. Recommended by the study's "next experiment".

APPROVED PATTERN (mirrors v54_fvg_sidecar.py). Additive and fail-closed:
- Own state file (v54_forward/lonewolf_overlay_state.json), own append-only
  log (v54_forward/lonewolf_overlay.jsonl), own daily-bar cache
  (v54_forward/lonewolf_cache/). NEVER writes to forward_test.jsonl,
  v54_forward/state.json, forward_test/v54_closed_trades.json,
  latest_v54_signals.json, or any frozen artifact -- those are READ ONLY.
- The overlay never changes what the harness records, sends, or trades.
  Every record carries "paper": true and variant "hybrid+no-lonewolf".
- run_overlay_cycle never raises: per-signal errors are logged to the
  overlay log and swallowed; a cycle-level exception returns
  {"ok": False, ...} instead of propagating into any caller.

Filter definition (verbatim from pine_sector_rs_backtest/, pre-declared):
    stockRS  = stock_ret20  - SPY_ret20
    sectorRS = sectorETF_ret20 - SPY_ret20
on DAILY bars, 20-trading-day returns, point-in-time at the signal bar.
Sector mapping: QQQ->XLK SMCI->SOXX PLTR->XLK ANET->XLK SOFI->XLF RKLB->XLI
ONDS->XLK DRAM->SOXX SPCX->XLI ASTX->XLK BBAI->XLK NIO->XLY HOOD->XLF AMD->SOXX.

Point-in-time note: the study used the signal DATE's daily close. Live,
today's daily bar is incomplete intraday, so for a signal fired today the
endpoint is the last COMPLETED trading day (strictly point-in-time, no
lookahead); for signals on past dates the signal date's close is used,
exactly matching the study. The effective endpoint is logged as
rs_asof_date on every record.

Unlike the FVG sidecar this overlay runs STANDALONE (it is not called from
the frozen harness -- the harness must not be edited). Intended trigger: a
lightweight hourly cron right after v54-forward-test-cycle. The first cycle
backfills all existing signals (annotation-only, point-in-time RS -- safe);
later cycles only classify new signal_ids.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VARIANT = "hybrid+no-lonewolf"
LOOKBACK = 20  # trading days -- pre-declared, do not tune

# P10's exact sector-ETF mapping (pre-declared in pine_sector_rs_backtest).
SECTOR = {
    "QQQ": "XLK", "SMCI": "SOXX", "PLTR": "XLK", "ANET": "XLK",
    "SOFI": "XLF", "RKLB": "XLI", "ONDS": "XLK", "DRAM": "SOXX",
    "SPCX": "XLI", "ASTX": "XLK", "BBAI": "XLK", "NIO": "XLY",
    "HOOD": "XLF", "AMD": "SOXX",
}
BENCH = "SPY"

FROZEN_LOG = os.path.join(BASE_DIR, "v54_forward", "forward_test.jsonl")
CLOSED_TRADES = os.path.join(BASE_DIR, "forward_test", "v54_closed_trades.json")
LOG_PATH = os.path.join(BASE_DIR, "v54_forward", "lonewolf_overlay.jsonl")
STATE_PATH = os.path.join(BASE_DIR, "v54_forward", "lonewolf_overlay_state.json")
CACHE_DIR = os.path.join(BASE_DIR, "v54_forward", "lonewolf_cache")

ET_NOW = "America/New_York"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# State + log (own files; never the frozen ones).
# ---------------------------------------------------------------------------

def _blank_state() -> Dict[str, Any]:
    return {"seen_signal_ids": [], "overlay": {}, "close_logged": {},
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


def _read_frozen_signals() -> List[Dict[str, Any]]:
    """Read-only scan of the frozen forward-test log for V5.4 signals."""
    out: List[Dict[str, Any]] = []
    if not os.path.exists(FROZEN_LOG):
        return out
    with open(FROZEN_LOG, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("type") == "signal" and str(r.get("signal_id", "")).startswith("v54:"):
                out.append(r)
    return out


def _read_closed_trades() -> List[Dict[str, Any]]:
    """Read-only read of the harness's closed-trade snapshot."""
    if not os.path.exists(CLOSED_TRADES):
        return []
    try:
        doc = json.load(open(CLOSED_TRADES, encoding="utf-8"))
        return doc.get("trades", []) or []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Daily data (own cache; yfinance; never touches study caches).
# ---------------------------------------------------------------------------


def _get_daily(sym: str, cache_dir: str = CACHE_DIR) -> Optional[pd.Series]:
    """Daily closes for `sym`, tz-naive date index. Merges cache + fresh."""
    import yfinance as yf

    cached: Optional[pd.Series] = None
    p = os.path.join(cache_dir, f"d_{sym}.pkl")
    if os.path.exists(p):
        try:
            cached = pd.read_pickle(p)
        except Exception:
            cached = None
    try:
        df = yf.download(sym, period="3mo", interval="1d", progress=False,
                         auto_adjust=True)
    except Exception:
        df = None
    fresh: Optional[pd.Series] = None
    if df is not None and len(df):
        try:
            closes = df["Close"]
            if isinstance(closes, pd.DataFrame):
                closes = closes.iloc[:, 0]
            idx = pd.to_datetime(closes.index)
            if idx.tz is not None:
                idx = idx.tz_convert(ET_NOW).tz_localize(None)
            idx = idx.normalize()
            s = pd.Series(np.asarray(closes, dtype=float), index=idx)
            s = s[~s.index.duplicated(keep="last")].sort_index().dropna()
            fresh = s
        except Exception:
            fresh = None
    if cached is not None and fresh is not None:
        merged = pd.concat([cached, fresh])
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    else:
        merged = fresh if fresh is not None else cached
    if merged is None or len(merged) == 0:
        return None
    try:
        os.makedirs(cache_dir, exist_ok=True)
        pd.to_pickle(merged, p)
    except Exception:
        pass
    return merged


def _ret20(series: pd.Series, asof: pd.Timestamp) -> float:
    """20-trading-day return ending at `asof` (point-in-time). Study verbatim."""
    idx = series.index
    pos = int(idx.searchsorted(asof, side="right")) - 1
    if pos < LOOKBACK:
        return float("nan")
    base = series.iloc[pos - LOOKBACK]
    if not base or pd.isna(base):
        return float("nan")
    return float(series.iloc[pos] / base - 1.0)


def classify(sym: str, signal_bar_close_at: str,
             daily: Dict[str, pd.Series]) -> Dict[str, Any]:
    """Lone-wolf classification for one signal. Pure function of inputs."""
    rec: Dict[str, Any] = {"would_block": False, "stock_rs": None,
                           "sector_rs": None, "rs_asof_date": None,
                           "reason": None}
    etf = SECTOR.get(sym)
    if etf is None:
        rec["reason"] = "no_sector_mapping"
        return rec
    for t in (sym, etf, BENCH):
        if daily.get(t) is None or len(daily[t]) < LOOKBACK + 1:
            rec["reason"] = "insufficient_daily_data"
            return rec
    sig_dt = pd.Timestamp(signal_bar_close_at)
    today = pd.Timestamp.now(tz=ET_NOW).normalize().tz_localize(None)
    # Point-in-time: today's daily bar is incomplete -> last completed bar.
    asof = min(sig_dt.tz_localize(None).normalize(), today - pd.Timedelta(days=1)) \
        if sig_dt.tz_localize(None).normalize() >= today \
        else sig_dt.tz_localize(None).normalize()
    # asof must be a bar actually present; searchsorted handles weekends.
    srs = _ret20(daily[sym], asof) - _ret20(daily[BENCH], asof)
    secrs = _ret20(daily[etf], asof) - _ret20(daily[BENCH], asof)
    if pd.isna(srs) or pd.isna(secrs):
        rec["reason"] = "insufficient_rs_history"
        return rec
    rec["stock_rs"] = round(float(srs), 4)
    rec["sector_rs"] = round(float(secrs), 4)
    rec["sector_etf"] = etf
    rec["rs_asof_date"] = asof.strftime("%Y-%m-%d")
    rec["would_block"] = bool(srs > 0 and secrs <= 0)
    rec["reason"] = "lone_wolf" if rec["would_block"] else "sector_tailwind_or_weak_stock"
    return rec


# ---------------------------------------------------------------------------
# Live cycle.
# ---------------------------------------------------------------------------

def run_overlay_cycle() -> Dict[str, Any]:
    """One overlay cycle. Reads frozen logs, writes only overlay files.

    Never raises.
    """
    started = _now()
    result: Dict[str, Any] = {
        "ok": True, "paper": True, "variant": VARIANT,
        "new_signals": 0, "would_block": 0, "closes_joined": 0,
        "errors": [],
    }
    try:
        state = _load_state()
        seen = set(state.get("seen_signal_ids", []))
        overlay = state.get("overlay", {})

        signals = _read_frozen_signals()
        new = [s for s in signals if s.get("signal_id") not in seen]
        daily: Dict[str, pd.Series] = {}

        def need(t: str) -> Optional[pd.Series]:
            if t not in daily:
                daily[t] = _get_daily(t)
            return daily[t]

        for s in new:
            sid = s["signal_id"]
            sym = s.get("symbol")
            try:
                if sym in SECTOR:
                    need(sym); need(SECTOR[sym]); need(BENCH)
                cls = classify(sym, s.get("signal_bar_close_at"), daily)
                rec = {
                    "type": "signal_overlay", "paper": True, "variant": VARIANT,
                    "signal_id": sid, "symbol": sym,
                    "signal_bar_close_at": s.get("signal_bar_close_at"),
                    "entry": s.get("entry"), "v54_grade": s.get("v54_grade"),
                    "would_block": cls["would_block"],
                    "stock_rs": cls["stock_rs"], "sector_rs": cls["sector_rs"],
                    "sector_etf": cls.get("sector_etf"),
                    "rs_asof_date": cls["rs_asof_date"],
                    "reason": cls["reason"],
                    "logged_at": _now(),
                }
                _append(rec)
                overlay[sid] = {"would_block": cls["would_block"],
                                "stock_rs": cls["stock_rs"],
                                "sector_rs": cls["sector_rs"]}
                seen.add(sid)
                result["new_signals"] += 1
                result["would_block"] += 1 if cls["would_block"] else 0
            except Exception as exc:  # one signal never kills the overlay
                result["errors"].append({"signal_id": sid,
                                        "error": str(exc)[:200]})
                _append({"type": "error", "paper": True, "variant": VARIANT,
                         "signal_id": sid, "error": str(exc)[:300],
                         "logged_at": _now()})

        # Join closed trades -> realized outcomes for blocked vs allowed.
        close_logged = state.get("close_logged", {})
        for t in _read_closed_trades():
            sid = t.get("signal_id")
            if not sid or sid in close_logged or sid not in overlay:
                continue
            info = overlay[sid]
            _append({
                "type": "close_overlay", "paper": True, "variant": VARIANT,
                "signal_id": sid, "symbol": t.get("symbol"),
                "would_block": info["would_block"],
                "stock_rs": info["stock_rs"], "sector_rs": info["sector_rs"],
                "blended_r": t.get("blended_r"),
                "exit_reason": t.get("exit_reason"),
                "entry": t.get("entry"), "exit_px": t.get("exit_px"),
                "logged_at": _now(),
            })
            close_logged[sid] = True
            result["closes_joined"] += 1

        state["seen_signal_ids"] = sorted(seen)
        state["overlay"] = overlay
        state["close_logged"] = close_logged
        state["runs"] = state.get("runs", 0) + 1
        state["last_run"] = started
        _save_state(state)

        finished = _now()
        result["started_at"] = started
        result["finished_at"] = finished
        _append({"type": "cycle", "paper": True, "variant": VARIANT,
                 "started_at": started, "finished_at": finished,
                 "new_signals": result["new_signals"],
                 "would_block": result["would_block"],
                 "closes_joined": result["closes_joined"],
                 "errors": result["errors"]})
    except Exception as exc:  # fail closed: never raise into any caller
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
# --verify: dry run over the frozen logs. ZERO writes (no state, no log).
# ---------------------------------------------------------------------------

def _verify() -> int:
    import tempfile
    print("=== lone-wolf overlay --verify (dry run, zero writes) ===")
    frozen_before = (os.path.getsize(FROZEN_LOG), os.path.getmtime(FROZEN_LOG)) \
        if os.path.exists(FROZEN_LOG) else None
    closed_before = (os.path.getsize(CLOSED_TRADES), os.path.getmtime(CLOSED_TRADES)) \
        if os.path.exists(CLOSED_TRADES) else None
    log_existed = os.path.exists(LOG_PATH)
    state_existed = os.path.exists(STATE_PATH)
    log_mtime = os.path.getmtime(LOG_PATH) if log_existed else None
    state_mtime = os.path.getmtime(STATE_PATH) if state_existed else None

    signals = _read_frozen_signals()
    print(f"frozen signals readable: {len(signals)}")
    daily: Dict[str, pd.Series] = {}
    tmp_cache = tempfile.mkdtemp(prefix="lonewolf_verify_")

    def need(t: str) -> Optional[pd.Series]:
        if t not in daily:
            daily[t] = _get_daily(t, cache_dir=tmp_cache)
        return daily[t]

    n_block = 0
    for s in signals:
        sym = s.get("symbol")
        if sym in SECTOR:
            need(sym); need(SECTOR[sym]); need(BENCH)
        cls = classify(sym, s.get("signal_bar_close_at"), daily)
        if cls["would_block"]:
            n_block += 1
        print(f"  WOULD LOG {s['signal_id'][:40]:42s} {sym:6s} "
              f"would_block={cls['would_block']!s:5s} "
              f"stock_rs={cls['stock_rs']} sector_rs={cls['sector_rs']} "
              f"asof={cls['rs_asof_date']} reason={cls['reason']}")
    print(f"\n{len(signals)} signal(s) -> {n_block} would-block")

    ok = True
    if os.path.exists(FROZEN_LOG):
        ok &= (os.path.getsize(FROZEN_LOG), os.path.getmtime(FROZEN_LOG)) == frozen_before
    if os.path.exists(CLOSED_TRADES):
        ok &= (os.path.getsize(CLOSED_TRADES), os.path.getmtime(CLOSED_TRADES)) == closed_before
    ok &= (os.path.exists(LOG_PATH) == log_existed)
    ok &= (os.path.exists(STATE_PATH) == state_existed)
    if log_existed:
        ok &= os.path.getmtime(LOG_PATH) == log_mtime
    if state_existed:
        ok &= os.path.getmtime(STATE_PATH) == state_mtime
    # cache dir may have been created by reads -- that is read-side data,
    # but flag it so the operator knows verify touched the cache.
    print(f"frozen logs untouched: {ok}")
    print("VERIFY " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--verify" in sys.argv:
        raise SystemExit(_verify())
    if "--cycle" in sys.argv:
        print(json.dumps(run_overlay_cycle(), indent=1, default=str))
    else:
        print("v54_lonewolf_overlay: run with --cycle (live, own files only) "
              "or --verify (dry run, zero writes).")
