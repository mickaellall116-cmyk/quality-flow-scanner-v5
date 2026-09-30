#!/usr/bin/env python3
"""Stage C (redo): aggregate fetched 1H bars into 4H session bars per rev-6.1 §11.

Session rule (documented, deterministic — same as the first attempt's rule,
which was reviewed and kept):
  - Only regular-session 1H bars (fetched with prepost=False).
  - A 1H bar is assigned to the session containing its OPEN timestamp
    (America/New_York wall clock):
      morning   session: open in {09:30, 10:30, 11:30, 12:30} -> bar label 09:30
      afternoon session: open in {13:30, 14:30, 15:30}        -> bar label 13:30
    Bars with any other open time are anomalies: excluded from the 4H
    frame and counted (expected: 0 with prepost=False).
  - Bar timestamp = session date at 09:30 / 13:30 America/New_York,
    constructed from date+time (DST-safe; no arithmetic across transitions).
  - Early-close days (13:00): only morning 1H bars exist -> exactly one
    4H bar labeled 09:30. No bar spans the overnight gap.
  - OHLCV agg: Open first / High max / Low min / Close last / Volume sum,
    ordered by 1H bar timestamp within the session.
  - Intraday bars are Yahoo split-adjusted, NOT dividend-adjusted (per
    UNIVERSE.md; same property as the original cache).

Window: the fresh pull serves from 2023-10-31 (3 trading days after the
documented 2023-10-26 start — within the ±5td §5B tolerance, recorded with
cause). 4H output is clipped to the frozen window end 2026-09-24 for an
apples-to-apples comparison with the whitelisted coverage target (the raw
fetch may include newer sessions; they are recorded, not built).

Expected-bar calendar (independent of any quarantined data):
  - Trading days: dates with a SPY daily bar in the Stage-A fresh daily
    cache (canonical_stage_a/data/d1_SPY.json), within 2023-10-31..2026-09-24.
  - Early closes: the 7 documented NYSE 13:00 dates (all inside the window).
  - Expected 4H per symbol: 2 per full trading day, 1 per early close, over
    [symbol first-1H-bar date, 2026-09-24].

Output per symbol: <run>/data_4h/{SYM}.json
  {symbol, generated_at_utc, provenance, n_1h, first_1h, last_1h,
   bars: [{t (ISO, America/New_York), o,h,l,c,v, n_1h}], anomalies_1h: [...]}
plus <run>/build_4h_summary.json (per-symbol coverage/quality).

RUN ISOLATION (R2): --run-dir selects a run-specific directory
(default: canonical_stage_c, the Run 1 layout). Run 2 MUST use
--run-dir canonical_stage_c/run2. The builder only ever reads raw 1H files
from its own run dir, so a symbol changing fetch shape between runs cannot
merge stale prior-run bytes with fresh bytes.
"""
import argparse
import csv
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

WORKTREE = Path(__file__).resolve().parent.parent
STAGE_C = WORKTREE / "canonical_stage_c"
RAW_DIR = STAGE_C / "raw_1h"
OUT_DIR = STAGE_C / "data_4h"
STAGE_A_DATA = WORKTREE / "canonical_stage_a" / "data"
NY = ZoneInfo("America/New_York")

MORNING_OPENS = {"09:30", "10:30", "11:30", "12:30"}
AFTERNOON_OPENS = {"13:30", "14:30", "15:30"}
EARLY_CLOSES_DOC = {"2023-11-24", "2024-07-03", "2024-11-29", "2024-12-24",
                    "2025-07-03", "2025-11-28", "2025-12-24"}
WINDOW_START = date(2023, 10, 31)   # oldest session Yahoo 1H serves (verified)
WINDOW_END = date(2026, 9, 24)      # frozen window end (UNIVERSE.md / §5B)

# The 11 admitted new listings (Stage-A recomputed eval): per UNIVERSE.md,
# effective 4H eligibility = 60th 4H bar (listing + 30 trading days rule).
ADMITTED_LISTINGS = {"ARM", "BMNR", "CRWV", "DRAM", "GEV", "GLXY", "NBIS",
                     "RDDT", "SNDK", "SPCX", "TEM"}


def parse_args():
    p = argparse.ArgumentParser(description="Stage C 1H->4H build (rev-6.1 §11)")
    p.add_argument("--run-dir", default=os.environ.get("CANONICAL_RUN_DIR"),
                   help="run-specific directory; default canonical_stage_c "
                        "(Run 1 layout). Run 2: --run-dir canonical_stage_c/run2")
    return p.parse_args()


def trading_days():
    """Trading days from the Stage-A fresh SPY daily cache (own output)."""
    spy = json.loads((STAGE_A_DATA / "d1_SPY.json").read_text())
    rows = spy["rows"]
    di = spy["columns"].index("date")
    days = set()
    for r in rows:
        dd = date.fromisoformat(r[di][:10])
        if WINDOW_START <= dd <= WINDOW_END:
            days.add(dd)
    return sorted(days)


def load_1h(sym):
    rows = []
    # GEV/RDDT/TEM: period=730d server-errors for these tickers (Yahoo 1H
    # boundary at 2024-09-30); recovered with period=max, same endpoint.
    for tag in ("p730", "pmax"):
        p = RAW_DIR / f"{sym}_{tag}.csv"
        if not p.exists():
            continue
        with open(p, newline="") as f:
            for r in csv.DictReader(f):
                ts = datetime.fromisoformat(r["t"])
                rows.append((ts, float(r["o"]), float(r["h"]),
                             float(r["l"]), float(r["c"]), float(r["v"])))
    # clip to frozen window, dedupe by timestamp, sort
    seen = {}
    for ts, o, h, l, c, v in rows:
        if ts.astimezone(NY).date() > WINDOW_END:
            continue
        if ts not in seen:
            seen[ts] = (o, h, l, c, v)
    return sorted((ts, o, h, l, c, v) for ts, (o, h, l, c, v) in seen.items())


def session_of(ts_ny):
    hm = ts_ny.strftime("%H:%M")
    if hm in MORNING_OPENS:
        return "09:30"
    if hm in AFTERNOON_OPENS:
        return "13:30"
    return None


def bar_stamp(d, label):
    hh, mm = map(int, label.split(":"))
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=NY)


def aggregate(sym, rows_1h):
    sessions = {}
    anomalies = []
    for ts, o, h, l, c, v in rows_1h:
        ts_ny = ts.astimezone(NY)
        sess = session_of(ts_ny)
        if sess is None:
            anomalies.append({"t": ts.isoformat(), "reason": "open_outside_sessions"})
            continue
        key = (ts_ny.date().isoformat(), sess)
        sessions.setdefault(key, []).append((ts_ny, o, h, l, c, v))
    bars = []
    for (dstr, sess), grp in sorted(sessions.items()):
        grp.sort(key=lambda x: x[0])
        oo = grp[0][1]
        hh = max(g[2] for g in grp)
        ll = min(g[3] for g in grp)
        cc = grp[-1][4]
        vv = sum(g[5] for g in grp)
        bars.append({
            "t": bar_stamp(date.fromisoformat(dstr), sess).isoformat(),
            "o": oo, "h": hh, "l": ll, "c": cc, "v": vv,
            "n_1h": len(grp),
        })
    return bars, anomalies


def quality(bars):
    import math
    q = {"nan_ohlc": 0, "zero_volume": 0, "dup_ts": 0, "bad_wick": 0,
         "tz_ok": True, "bars_not_0930_1330": 0}
    seen = set()
    for b in bars:
        if b["t"] in seen:
            q["dup_ts"] += 1
        seen.add(b["t"])
        for k in ("o", "h", "l", "c"):
            if not math.isfinite(b[k]):
                q["nan_ohlc"] += 1
        if b["v"] == 0:
            q["zero_volume"] += 1
        if not (b["h"] >= max(b["o"], b["c"]) and b["l"] <= min(b["o"], b["c"])):
            q["bad_wick"] += 1
        ts = datetime.fromisoformat(b["t"])
        if ts.utcoffset() is None:
            q["tz_ok"] = False
        if ts.strftime("%H:%M") not in ("09:30", "13:30"):
            q["bars_not_0930_1330"] += 1
    return q


def main():
    global RAW_DIR, OUT_DIR
    args = parse_args()
    RUN = Path(args.run_dir) if args.run_dir else STAGE_C
    RAW_DIR = RUN / "raw_1h"
    OUT_DIR = RUN / "data_4h"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"run dir: {RUN}")
    days = trading_days()
    early = {d for d in days if d.isoformat() in EARLY_CLOSES_DOC}
    print(f"trading days in window: {len(days)}, early closes: "
          f"{sorted(d.isoformat() for d in early)}")

    manifest = json.loads((RUN / "fetch_4h_manifest.json").read_text())
    syms = [s["symbol"] for s in manifest["symbols"]]
    summary = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
               "rule": "1H open-time session assignment; agg o=first,h=max,l=min,c=last,v=sum; "
                       "4H clipped to frozen window end 2026-09-24",
               "symbols": []}
    for sym in syms:
        rows = load_1h(sym)
        bars, anomalies = aggregate(sym, rows)
        q = quality(bars)
        first_d = rows[0][0].astimezone(NY).date() if rows else None
        last_d = rows[-1][0].astimezone(NY).date() if rows else None
        # expected sessions over [first_1h_date, WINDOW_END]
        exp = 0
        if first_d:
            for d in days:
                if first_d <= d <= WINDOW_END:
                    exp += 1 if d in early else 2
        actual = len(bars)
        missing = exp - actual
        # effective_4h_from per documented rule: 60th 4H bar for admitted
        # new listings, else the first 4H bar.
        if sym in ADMITTED_LISTINGS and len(bars) >= 60:
            eff_bar = bars[59]
        elif bars:
            eff_bar = bars[0]
        else:
            eff_bar = None
        eff_from = eff_bar["t"][:10] if eff_bar else None
        n_eff = sum(1 for b in bars if eff_from and b["t"][:10] >= eff_from)
        rec = {
            "symbol": sym,
            "n_1h": len(rows),
            "n_4h": actual,
            "first_4h": bars[0]["t"] if bars else None,
            "last_4h": bars[-1]["t"] if bars else None,
            "effective_4h_from": eff_from,
            "n_4h_from_effective": n_eff,
            "effective_rule": "60th_4h_bar" if sym in ADMITTED_LISTINGS else "first_4h_bar",
            "expected_4h_servable_window": exp,
            "missing_vs_expected": missing,
            "missing_pct_servable": round(100 * missing / exp, 3) if exp else None,
            "anomalies_1h": len(anomalies),
            "quality": q,
        }
        summary["symbols"].append(rec)
        out = {
            "symbol": sym,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "provenance": "stage_c fresh yfinance 1H pull (period=730d) 2026-09-29; "
                          "session aggregation per rev-6.1 §11",
            "n_1h": len(rows),
            "first_1h": rows[0][0].isoformat() if rows else None,
            "last_1h": rows[-1][0].isoformat() if rows else None,
            "bars": bars,
            "anomalies_1h": anomalies,
        }
        (OUT_DIR / f"{sym}.json").write_text(json.dumps(out))
    (RUN / "build_4h_summary.json").write_text(json.dumps(summary, indent=2))
    n4 = sum(s["n_4h"] for s in summary["symbols"])
    print(f"built {len(summary['symbols'])} symbols, {n4} 4H bars total")


if __name__ == "__main__":
    main()
