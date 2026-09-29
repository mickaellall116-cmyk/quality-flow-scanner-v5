"""Fetch full timestamped upgrades/downgrades series per ticker (the PIT input)."""
import json, time, warnings
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
OUT = "/home/hatch/workspace/quality-flow-scanner-v5/selection_edge/phase2_fundamentals"
BLIND = {"QQQ","SMCI","PLTR","ANET","SOFI","RKLB","ONDS","DRAM","SPCX","ASTX","BBAI","NIO","HOOD","AMD"}

u = json.load(open("/home/hatch/workspace/quality-flow-scanner-v5/canonical_baseline/universe.json"))
names = [e["symbol"] for e in u if e["symbol"] not in BLIND and e["sector"] != "ETF"]

series = {}
for i, sym in enumerate(names):
    evts = []
    try:
        ud = yf.Ticker(sym).get_upgrades_downgrades()
        if ud is not None and len(ud):
            for ts, row in ud.iterrows():
                try:
                    d = pd.to_datetime(ts).tz_convert(None)
                except Exception:
                    d = pd.to_datetime(ts)
                evts.append({"date": d.strftime("%Y-%m-%d"),
                             "action": str(row.get("Action", "")).lower(),
                             "firm": str(row.get("Firm", "")),
                             "to": str(row.get("ToGrade", "")),
                             "from": str(row.get("FromGrade", ""))})
    except Exception as e:
        evts = [{"error": str(e)[:120]}]
    series[sym] = evts
    if (i + 1) % 10 == 0:
        print(f"  {i+1}/{len(names)}", flush=True)

json.dump(series, open(f"{OUT}/revision_series.json", "w"))
print("done", flush=True)
