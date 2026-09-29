"""Phase-2 Family 7 data audit: what fundamental series exist with strict PIT
for the 131-name universe over Oct 2023 - Sep 2026 (14 blinded out)."""
import json, time, warnings
from datetime import datetime, timezone
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
OUT = "/home/hatch/workspace/quality-flow-scanner-v5/selection_edge/phase2_fundamentals"
BLIND = {"QQQ","SMCI","PLTR","ANET","SOFI","RKLB","ONDS","DRAM","SPCX","ASTX","BBAI","NIO","HOOD","AMD"}
PERIOD_START = "2023-10-01"
PERIOD_END = "2026-09-30"
EXPECTED_Q = 12  # 12 quarter-ends in window

u = json.load(open("/home/hatch/workspace/quality-flow-scanner-v5/canonical_baseline/universe.json"))
names = [e["symbol"] for e in u if e["symbol"] not in BLIND and e["sector"] != "ETF"]
print(f"audit set: {len(names)} non-ETF, non-blind names", flush=True)

results = []
for i, sym in enumerate(names):
    r = {"symbol": sym, "earnings_dates_ok": False, "n_q_announced": 0,
         "n_q_with_estimate": 0, "qrev_quarters": 0, "qrev_range": None,
         "error": None}
    try:
        t = yf.Ticker(sym)
        ed = t.get_earnings_dates(limit=16)
        if ed is not None and len(ed):
            ed.index = pd.to_datetime(ed.index).tz_convert(None)
            mask = (ed.index >= PERIOD_START) & (ed.index < PERIOD_END)
            inwin = ed[mask]
            announced = inwin[inwin["Reported EPS"].notna()]
            withest = inwin[inwin["EPS Estimate"].notna()]
            r["n_q_announced"] = len(announced)
            r["n_q_with_estimate"] = len(withest)
            r["earnings_dates_ok"] = True
            r["ed_span"] = f"{inwin.index.min().date()}..{inwin.index.max().date()}" if len(inwin) else None
        qi = t.quarterly_income_stmt
        if qi is not None and len(qi.columns):
            cols = pd.to_datetime(qi.columns).tz_convert(None)
            mask = (cols >= PERIOD_START) & (cols < PERIOD_END)
            # Total Revenue row may be named differently
            revrow = None
            for cand in ["Total Revenue", "TotalRevenue", "Revenue"]:
                if cand in qi.index:
                    revrow = cand; break
            if revrow:
                vals = qi.loc[revrow, cols[mask]]
                r["qrev_quarters"] = int(vals.notna().sum())
                r["qrev_range"] = f"{cols[mask].min().date()}..{cols[mask].max().date()}" if mask.any() else None
                r["rev_row"] = revrow
    except Exception as e:
        r["error"] = str(e)[:120]
    results.append(r)
    if (i + 1) % 15 == 0:
        print(f"  {i+1}/{len(names)}", flush=True)
    time.sleep(0.25)

json.dump(results, open(f"{OUT}/audit_raw.json", "w"), indent=1)
print("done, saved audit_raw.json", flush=True)
