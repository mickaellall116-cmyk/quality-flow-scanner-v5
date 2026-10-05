#!/usr/bin/env python3
"""CP1 follow-up: full 52-symbol h4 cache audit.
Task 2 of ChatGPT bounded assignment (Issue #1 comment 5986944792).

READ-ONLY: never mutates cache files. All findings tagged COMPUTED.
Calendar: pandas_market_calendars XNYS v5.5.0 (named explicitly for provenance).

Outputs:
  - audit_52symbol.json : machine-readable per-symbol audit table
  - audit_52symbol.md   : human-readable summary
"""
import pickle, hashlib, json, os
import pandas as pd
import pandas_market_calendars as mcal

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = "/home/hatch/workspace/quality-flow-scanner-v5/backtest_cache/v3"
CAL_NAME, CAL_VER = "XNYS", "pandas_market_calendars 5.5.0"

CRYPTO = {"BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "LINK-USD", "AVAX-USD", "XRP-USD"}

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def expected_equity_grid(start, end):
    """Expected session-anchored 4H labels: 09:30 and 13:30 America/New_York,
    on XNYS trading days. Returns set of tz-aware Timestamps."""
    cal = mcal.get_calendar("XNYS")
    sched = cal.schedule(start_date=start.date(), end_date=end.date())
    out = set()
    ny = "America/New_York"
    for day in sched.index:
        d = pd.Timestamp(day.date())
        out.add(pd.Timestamp(d.date().isoformat() + " 09:30").tz_localize(ny))
        out.add(pd.Timestamp(d.date().isoformat() + " 13:30").tz_localize(ny))
    return out

def expected_crypto_grid(start, end):
    """Crypto: 24/7 at 00/04/08/12/16/20 UTC."""
    out = set()
    cur = pd.Timestamp(start.date()).tz_localize("UTC")
    end_u = pd.Timestamp(end.date()).tz_localize("UTC") + pd.Timedelta(days=1)
    while cur < end_u:
        for hh in (0, 4, 8, 12, 16, 20):
            out.add(cur + pd.Timedelta(hours=hh))
        cur += pd.Timedelta(days=1)
    return out

def audit_symbol(sym):
    path = os.path.join(CACHE, f"h4_{sym}.pkl")
    df = pickle.load(open(path, "rb"))  # read-only
    idx = df.index
    rec = {
        "symbol": sym,
        "sha256": sha256_file(path),
        "n_bars": len(df),
        "tz": str(idx.tz),
        "start": idx[0].isoformat(),
        "end": idx[-1].isoformat(),
        "is_monotonic": bool(idx.is_monotonic_increasing),
        "n_duplicates": int(idx.duplicated().sum()),
        "columns": list(df.columns),
        "asset_class": "crypto" if sym in CRYPTO or sym.endswith("-USD") else "equity",
    }
    # duplicate timestamps list
    dup = idx[idx.duplicated()].tolist()
    rec["duplicate_timestamps"] = [t.isoformat() for t in dup[:20]]
    rec["n_duplicate_extra"] = max(0, len(dup) - 20)

    if rec["asset_class"] == "equity":
        exp = expected_equity_grid(idx[0], idx[-1])
        actual = set(idx)
        missing = sorted(exp - actual)
        extra = sorted(actual - exp)
        # classify missing against XNYS schedule: scheduled closure vs unexplained
        cal = mcal.get_calendar("XNYS")
        sched = cal.schedule(start_date=idx[0].date(), end_date=idx[-1].date())
        trading_days = set(sched.index.date)
        unexplained, scheduled = [], []
        for t in missing:
            if t.date() not in trading_days:
                scheduled.append(t.isoformat())
            else:
                unexplained.append(t.isoformat())
        rec["expected_grid"] = "09:30/13:30 America/New_York on XNYS days"
        rec["n_missing_vs_expected"] = len(missing)
        rec["n_extra_vs_expected"] = len(extra)
        rec["missing_unexplained_sample"] = unexplained[:20]
        rec["n_missing_unexplained"] = len(unexplained)
        rec["missing_scheduled_closures"] = len(scheduled)
        rec["extra_sample"] = [t.isoformat() for t in extra[:20]]
        # off-grid = actual bar not on the intended session grid (label check)
        et = idx.tz_convert("America/New_York")
        ongrid = ((et.hour == 9) & (et.minute == 30)) | ((et.hour == 13) & (et.minute == 30))
        rec["n_offgrid_labels"] = int((~ongrid).sum())
    else:
        exp = expected_crypto_grid(idx[0], idx[-1])
        actual = set(idx.tz_convert("UTC"))
        missing = sorted(exp - actual)
        extra = sorted(actual - exp)
        rec["expected_grid"] = "00/04/08/12/16/20 UTC daily"
        rec["n_missing_vs_expected"] = len(missing)
        rec["n_extra_vs_expected"] = len(extra)
        rec["missing_sample"] = [t.isoformat() for t in missing[:20]]
        rec["extra_sample"] = [t.isoformat() for t in extra[:20]]
        rec["n_offgrid_labels"] = 0
    return rec

def main():
    files = sorted(f[3:-4] for f in os.listdir(CACHE) if f.startswith("h4_") and f.endswith(".pkl"))
    assert len(files) == 52, f"expected 52, got {len(files)}"
    results = [audit_symbol(s) for s in files]
    out = {
        "provenance": {
            "method": "COMPUTED",
            "calendar": f"{CAL_NAME} ({CAL_VER})",
            "read_only": True,
            "n_files": 52,
        },
        "symbols": results,
    }
    with open(os.path.join(HERE, "audit_52symbol.json"), "w") as f:
        json.dump(out, f, indent=1)
    # markdown summary
    lines = ["# 52-symbol h4 cache audit (COMPUTED)", "",
             f"Calendar: {CAL_NAME} {CAL_VER}. Read-only; originals unmutated.", "",
             "| Symbol | Bars | Start | End | Dups | Missing | Extra | Off-grid labels |",
             "|---|---|---|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['symbol']} | {r['n_bars']} | {r['start'][:10]} | {r['end'][:10]} | "
                     f"{r['n_duplicates']} | {r['n_missing_vs_expected']} | {r['n_extra_vs_expected']} | "
                     f"{r['n_offgrid_labels']} |")
    open(os.path.join(HERE, "audit_52symbol.md"), "w").write("\n".join(lines) + "\n")
    print(f"audited {len(results)} symbols")

if __name__ == "__main__":
    main()
