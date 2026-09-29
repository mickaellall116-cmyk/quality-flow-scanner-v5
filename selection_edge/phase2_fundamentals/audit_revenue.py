"""Audit 3: quarterly_income_stmt (revenue) coverage on a stratified sample of 25."""
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
sample = names[::4][:25]  # deterministic stride sample
print("sample:", sample, flush=True)

res = []
for i, sym in enumerate(sample):
    r = {"symbol": sym, "n_cols": 0, "rev_row": None, "rev_q_inwin": 0,
         "rev_span": None, "error": None}
    try:
        qi = yf.Ticker(sym).quarterly_income_stmt
        if qi is not None and len(qi.columns):
            cols = pd.to_datetime(qi.columns); cols = cols.tz_localize(None) if cols.tz is not None else cols
            r["n_cols"] = len(cols)
            for cand in ["Total Revenue", "TotalRevenue", "Revenue"]:
                if cand in qi.index:
                    r["rev_row"] = cand; break
            if r["rev_row"]:
                mask = (cols >= PERIOD_START) & (cols < PERIOD_END)
                vals = qi.loc[r["rev_row"], cols[mask]]
                r["rev_q_inwin"] = int(vals.notna().sum())
                r["rev_span"] = f"{cols.min().date()}..{cols.max().date()}"
    except Exception as e:
        r["error"] = str(e)[:120]
    res.append(r)
    print(f"  {i+1}/{len(sample)} {sym}: {r['rev_q_inwin']} rev quarters, err={r['error']}", flush=True)

json.dump(res, open(f"{OUT}/audit_revenue_raw.json", "w"), indent=1)
print("done", flush=True)
