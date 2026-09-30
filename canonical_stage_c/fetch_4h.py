#!/usr/bin/env python3
"""Stage C: fetch fresh 1H bars from yfinance for the 137-symbol 4H set.

137 symbols = 131 rebuilt universe (canonical_stage_b/universe_rebuilt.json)
+ 6 overlay outsiders (SOFI, RKLB, ONDS, ASTX, BBAI, HOOD).

FETCH PATH (audit-repaired; this is the exact path that produced Run 1):
  - Primary: ONE period="730d" pull per symbol, interval="1h",
    prepost=False, auto_adjust=False. period-based fetch serves 730 TRADING
    SESSIONS (verified 2026-09-29: oldest bar 2023-10-31 09:30 ET).
    Explicit start/end 1H is capped at 730 CALENDAR days and must not be
    used (that wrong shape caused the discarded first-attempt FAIL).
  - Fallback (deterministic, same vendor/endpoint/interval): if the primary
    shape fails all retries or returns empty, ONE attempt with period="max".
    This is the ticker-specific Yahoo 1H boundary quirk: GEV/RDDT/TEM
    server-error on period="730d" ("1h data not available ... must be
    within the last 730 days") because Yahoo bounds their 1H history at
    2024-09-30; period="max" recovers them (oldest bar 2024-09-30 09:30 ET).
    Not a vendor substitution; the shape used is recorded per symbol.
  - Pacing: ~1.2s between requests, 8s every 10 symbols, 2 bounded retries
    on the primary shape. A symbol failing both shapes is recorded as a
    finding; no hammering.

Output: raw 1H CSVs under canonical_stage_c/raw_1h/{SYM}_p730.csv or
{SYM}_pmax.csv (tag matches the shape actually used; build_4h.py loads
both), plus canonical_stage_c/fetch_4h_manifest.json with one record per
symbol: fetch_shape, first_1h, last_1h, n_1h, error, fetch timestamps.

Frozen-rule basis: rev-6.1 §11 (fresh 4H cache; no quarantined reuse).
"""
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

WORKTREE = Path(__file__).resolve().parent.parent
STAGE_C = WORKTREE / "canonical_stage_c"
RAW_DIR = STAGE_C / "raw_1h"
UNIVERSE_REBUILT = WORKTREE / "canonical_stage_b" / "universe_rebuilt.json"
OVERLAY_OUTSIDERS = ["SOFI", "RKLB", "ONDS", "ASTX", "BBAI", "HOOD"]

SLEEP_BETWEEN = 1.2
SLEEP_EVERY10 = 8.0
MAX_RETRIES = 2
SHAPES = ("730d", "max")  # primary, then deterministic fallback


def symbols():
    uni = json.loads(UNIVERSE_REBUILT.read_text())
    syms = [e["symbol"] for e in uni]
    for o in OVERLAY_OUTSIDERS:
        if o not in syms:
            syms.append(o)
    return sorted(syms)


def pull(sym, period):
    """One yfinance 1H pull. Returns (rows, error)."""
    try:
        t = yf.Ticker(sym)
        df = t.history(period=f"{period}", interval="1h",
                       prepost=False, auto_adjust=False)
        if df is None or len(df) == 0:
            return [], "empty"
        rows = []
        for ts, r in df.iterrows():
            rows.append({
                "t": ts.isoformat(),
                "o": float(r["Open"]), "h": float(r["High"]),
                "l": float(r["Low"]), "c": float(r["Close"]),
                "v": float(r["Volume"]),
            })
        return rows, None
    except Exception as e:  # noqa: BLE001 - bounded retry, recorded
        return [], f"{type(e).__name__}: {e}"


def fetch_one(sym):
    """Return (tag, rows, error, attempts). tag in {"p730","pmax"}.

    Primary shape first with bounded retries; deterministic period="max"
    fallback only after the primary is exhausted. The tag written here is
    the shape recorded in the manifest and used for the raw CSV filename.
    """
    attempts = []
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        rows, err = pull(sym, "730d")
        attempts.append(f"730d#{attempt + 1}:{'ok' if err is None else err[:60]}")
        if err is None:
            return "p730", rows, None, attempts
        last_err = err
        time.sleep(3 * (attempt + 1))
    rows, err = pull(sym, "max")
    attempts.append(f"max#1:{'ok' if err is None else err[:60]}")
    if err is None:
        return "pmax", rows, None, attempts
    return None, [], f"primary(730d) failed: {last_err}; fallback(max) failed: {err}", attempts


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    syms = symbols()
    print(f"{len(syms)} symbols; primary period=730d, deterministic period=max fallback")
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "fetch_shape": "primary period=730d then deterministic period=max fallback; "
                       "interval=1h, prepost=False, auto_adjust=False",
        "fetch_shape_note": "period-based fetch serves 730 trading sessions; "
                            "explicit start/end 1H is capped at 730 calendar days and "
                            "is not used. GEV/RDDT/TEM: period=730d server-errors "
                            "(Yahoo 1H boundary at 2024-09-30 for these tickers), "
                            "recovered with period=max, same endpoint/interval.",
        "symbols": [],
    }
    n = 0
    for sym in syms:
        t0 = datetime.now(timezone.utc).isoformat()
        tag, rows, err, attempts = fetch_one(sym)
        t1 = datetime.now(timezone.utc).isoformat()
        rec = {
            "symbol": sym,
            "fetched_at_utc": t0,
            "completed_at_utc": t1,
            "fetch_shape": f"period={tag[1:]}" if tag else "failed",
            "n_1h": len(rows),
            "first_1h": rows[0]["t"] if rows else None,
            "last_1h": rows[-1]["t"] if rows else None,
            "error": err,
            "attempts": attempts,
        }
        if err is None:
            p = RAW_DIR / f"{sym}_{tag}.csv"
            with open(p, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["t", "o", "h", "l", "c", "v"])
                w.writeheader()
                w.writerows(rows)
        manifest["symbols"].append(rec)
        n += 1
        if n % 10 == 0:
            print(f"  {n}/137 done, last={sym}", flush=True)
            time.sleep(SLEEP_EVERY10)
        time.sleep(SLEEP_BETWEEN)
    out = STAGE_C / "fetch_4h_manifest.json"
    out.write_text(json.dumps(manifest, indent=2))
    fails = sum(1 for s in manifest["symbols"] if s["error"])
    pmax = sum(1 for s in manifest["symbols"] if s["fetch_shape"] == "period=max")
    print(f"done. failures: {fails}/137; period=max fallback used: {pmax}")
    print(f"manifest: {out}")


if __name__ == "__main__":
    main()
