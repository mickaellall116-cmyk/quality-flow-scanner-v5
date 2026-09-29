#!/usr/bin/env python3
"""Stage C (redo): fetch fresh 1H bars from yfinance for the 137-symbol 4H set.

137 symbols = 131 rebuilt universe (canonical_stage_b/universe_rebuilt.json)
+ 6 overlay outsiders (SOFI, RKLB, ONDS, ASTX, BBAI, HOOD).

FETCH SHAPE CORRECTION (verified 2026-09-29, replaces the flawed
explicit-range probe of the first attempt):
  - yfinance 1H with EXPLICIT start/end is capped at 730 CALENDAR days
    (a 2023-10-26->2025-10-26 pull returns 0 rows).
  - yfinance 1H with period="730d" serves 730 TRADING SESSIONS:
    reproducible, 730 distinct sessions, oldest bar 2023-10-31 09:30 ET.
  - This is the correct fetch shape. The documented 2023-10-26 start is
    3 trading days (10-26/27/30) older than what Yahoo serves; per §5B the
    effective-history start may be within ±5 trading days with the
    divergence recorded and caused. Not a miss — a tolerated shift.

ONE period="730d" pull per symbol. Modest pacing: ~1.2s between requests,
8s every 10 symbols, 2 bounded retries. A failed symbol is recorded as a
finding; no vendor substitution, no hammering.

Output: raw 1H CSVs under canonical_stage_c/raw_1h/{SYM}_p730.csv
plus canonical_stage_c/fetch_4h_manifest.json (per-symbol fetch record).
"""
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

WORKTREE = Path(__file__).resolve().parent.parent
STAGE_C = WORKTREE / "canonical_stage_c"
RAW_DIR = STAGE_DIR = STAGE_C / "raw_1h"
UNIVERSE_REBUILT = WORKTREE / "canonical_stage_b" / "universe_rebuilt.json"
OVERLAY_OUTSIDERS = ["SOFI", "RKLB", "ONDS", "ASTX", "BBAI", "HOOD"]

SLEEP_BETWEEN = 1.2
SLEEP_EVERY10 = 8.0
MAX_RETRIES = 2


def symbols():
    uni = json.loads(UNIVERSE_REBUILT.read_text())
    syms = [e["symbol"] for e in uni]
    for o in OVERLAY_OUTSIDERS:
        if o not in syms:
            syms.append(o)
    return sorted(syms)


def fetch_one(sym):
    """Return (rows, error). rows = list of dicts with iso ts (tz-aware)."""
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            t = yf.Ticker(sym)
            df = t.history(period="730d", interval="1h",
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
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(3 * (attempt + 1))
    return [], last_err


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    syms = symbols()
    print(f"{len(syms)} symbols, one period=730d pull each")
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "fetch_shape": "period=730d, interval=1h, prepost=False, auto_adjust=False",
        "fetch_shape_note": "period-based fetch serves 730 trading sessions; "
                            "explicit start/end 1H is capped at 730 calendar days",
        "symbols": [],
    }
    n = 0
    for sym in syms:
        t0 = datetime.now(timezone.utc).isoformat()
        rows, err = fetch_one(sym)
        t1 = datetime.now(timezone.utc).isoformat()
        if err is None:
            p = RAW_DIR / f"{sym}_p730.csv"
            with open(p, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["t", "o", "h", "l", "c", "v"])
                w.writeheader()
                w.writerows(rows)
        manifest["symbols"].append({
            "symbol": sym,
            "fetched_at_utc": t0,
            "completed_at_utc": t1,
            "n_1h": len(rows),
            "error": err,
        })
        n += 1
        if n % 10 == 0:
            print(f"  {n}/137 done, last={sym}", flush=True)
            time.sleep(SLEEP_EVERY10)
        time.sleep(SLEEP_BETWEEN)
    out = STAGE_C / "fetch_4h_manifest.json"
    out.write_text(json.dumps(manifest, indent=2))
    fails = sum(1 for s in manifest["symbols"] if s["error"])
    ok = [s for s in manifest["symbols"] if not s["error"]]
    print(f"done. failures: {fails}/137")
    if ok:
        print("sample SPY-equivalent check: min/max 1H rows:",
              min(s["n_1h"] for s in ok), max(s["n_1h"] for s in ok))
    print(f"manifest: {out}")


if __name__ == "__main__":
    main()
