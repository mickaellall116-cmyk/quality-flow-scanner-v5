"""Step 4: pull sector assignments (yfinance info, labeled with pull date)."""
import os, json, time
import yfinance as yf

REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
CB = os.path.join(REPO, "canonical_baseline")

rows = json.load(open(os.path.join(CB, "addv_ranking_20230930.json")))[:120]
new = [r["symbol"] for r in json.load(open(os.path.join(CB, "new_listings_eval.json"))) if r["pass_gate"]]
syms = [r["symbol"] for r in rows] + new

out_path = os.path.join(CB, "sectors_raw.json")
out = json.load(open(out_path)) if os.path.exists(out_path) else {}
for i, s in enumerate(syms):
    if s in out: continue
    for attempt in range(3):
        try:
            info = yf.Ticker(s).info
            out[s] = {"sector": info.get("sector"), "industry": info.get("industry"),
                      "quoteType": info.get("quoteType"), "longName": info.get("longName")}
            print(f"  [{i+1}/{len(syms)}] {s}: {out[s]['sector']}", flush=True)
            break
        except Exception as e:
            print(f"  [{i+1}/{len(syms)}] {s}: retry {attempt+1} {type(e).__name__}", flush=True)
            time.sleep(10)
    with open(out_path, "w") as f: json.dump(out, f, indent=1)
    time.sleep(1.2)
print("DONE sectors")
