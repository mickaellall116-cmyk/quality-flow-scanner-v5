"""Audit 2: upgrades/downgrades (timestamped analyst revisions) coverage."""
import json, time, warnings
from datetime import datetime
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
OUT = "/home/hatch/workspace/quality-flow-scanner-v5/selection_edge/phase2_fundamentals"
BLIND = {"QQQ","SMCI","PLTR","ANET","SOFI","RKLB","ONDS","DRAM","SPCX","ASTX","BBAI","NIO","HOOD","AMD"}
PERIOD_START = pd.Timestamp("2023-10-01")
PERIOD_END = pd.Timestamp("2026-09-30")

u = json.load(open("/home/hatch/workspace/quality-flow-scanner-v5/canonical_baseline/universe.json"))
names = [e["symbol"] for e in u if e["symbol"] not in BLIND and e["sector"] != "ETF"]

res = []
for i, sym in enumerate(names):
    r = {"symbol": sym, "n_events_inwin": 0, "n_up": 0, "n_down": 0,
         "first": None, "last": None, "error": None}
    try:
        ud = yf.Ticker(sym).get_upgrades_downgrades()
        if ud is not None and len(ud):
            idx = pd.to_datetime(ud.index).tz_localize(None)
            win = ud[(idx >= PERIOD_START) & (idx < PERIOD_END)]
            act = win["Action"].astype(str).str.lower()
            r["n_events_inwin"] = len(win)
            r["n_up"] = int((act == "up").sum())
            r["n_down"] = int((act == "down").sum())
            if len(win):
                r["first"] = str(pd.to_datetime(win.index).tz_localize(None).min().date())
                r["last"] = str(pd.to_datetime(win.index).tz_localize(None).max().date())
    except Exception as e:
        r["error"] = str(e)[:120]
    res.append(r)
    if (i + 1) % 15 == 0:
        print(f"  {i+1}/{len(names)}", flush=True)
    time.sleep(0.25)

json.dump(res, open(f"{OUT}/audit_revisions_raw.json", "w"), indent=1)
print("done", flush=True)
