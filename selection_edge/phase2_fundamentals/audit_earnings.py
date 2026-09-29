"""Audit 1 (fast): earnings_dates coverage only, all 113 names."""
import json, time, warnings
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
OUT = "/home/hatch/workspace/quality-flow-scanner-v5/selection_edge/phase2_fundamentals"
BLIND = {"QQQ","SMCI","PLTR","ANET","SOFI","RKLB","ONDS","DRAM","SPCX","ASTX","BBAI","NIO","HOOD","AMD"}
PERIOD_START = "2023-10-01"
PERIOD_END = "2026-09-30"

u = json.load(open("/home/hatch/workspace/quality-flow-scanner-v5/canonical_baseline/universe.json"))
names = [e["symbol"] for e in u if e["symbol"] not in BLIND and e["sector"] != "ETF"]

res = []
for i, sym in enumerate(names):
    r = {"symbol": sym, "n_rows": 0, "n_inwin": 0, "n_announced": 0,
         "n_with_estimate": 0, "span": None, "error": None}
    try:
        ed = yf.Ticker(sym).get_earnings_dates(limit=16)
        if ed is not None and len(ed):
            r["n_rows"] = len(ed)
            idx = pd.to_datetime(ed.index).tz_convert(None)
            inwin = ed[(idx >= PERIOD_START) & (idx < PERIOD_END)]
            r["n_inwin"] = len(inwin)
            r["n_announced"] = int(inwin["Reported EPS"].notna().sum())
            r["n_with_estimate"] = int(inwin["EPS Estimate"].notna().sum())
            widx = pd.to_datetime(inwin.index).tz_convert(None)
            r["span"] = f"{widx.min().date()}..{widx.max().date()}" if len(inwin) else None
    except Exception as e:
        r["error"] = str(e)[:120]
    res.append(r)
    if (i + 1) % 10 == 0:
        print(f"  {i+1}/{len(names)}", flush=True)

json.dump(res, open(f"{OUT}/audit_earnings_raw.json", "w"), indent=1)
print("done", flush=True)
