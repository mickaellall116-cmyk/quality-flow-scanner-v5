"""Fetch daily bars for the remaining sector ETFs (worker e, lone-wolf rerun).

Same conventions as scripts/fetch_daily.py: 2023-06-01 -> 2026-10-03,
split/dividend-adjusted OHLC (Adj Close factor) + raw Volume,
America/New_York, regular session only.
Writes data/d1_{SYM}.pkl. Appends to fetch_sector_etfs_log.json.
"""
import os, json, time
import pandas as pd
import yfinance as yf

REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
CB = os.path.join(REPO, "canonical_baseline")
DATA = os.path.join(CB, "data")
os.makedirs(DATA, exist_ok=True)

ETFS = ["XLV", "XLI", "XLP", "XLY", "XLU", "XLRE", "XLB", "XLC"]
log_path = os.path.join(CB, "fetch_sector_etfs_log.json")
done = json.load(open(log_path)) if os.path.exists(log_path) else {}

def path(sym):
    return os.path.join(DATA, f"d1_{sym}.pkl")

def clean_one(df):
    if df is None or df.empty:
        return None, "empty"
    need = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    miss = [c for c in need if c not in df.columns]
    if miss:
        return None, f"missing-cols:{','.join(miss)}"
    df = df[need].copy().dropna(subset=["Close", "Adj Close"])
    df = df[~df.index.duplicated(keep="last")].sort_index()
    if df.empty:
        return None, "no-valid-rows"
    factor = (df["Adj Close"] / df["Close"]).replace([float("inf")], float("nan")).fillna(1.0)
    for c in ["Open", "High", "Low", "Close"]:
        df[c] = df[c] * factor
    out = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    out.index = out.index.tz_localize("America/New_York") if out.index.tz is None \
        else out.index.tz_convert("America/New_York")
    return out, None

todo = [s for s in ETFS if not (done.get(s, {}).get("ok") and os.path.exists(path(s)))]
print(f"{len(ETFS)} etfs, {len(todo)} to fetch", flush=True)
for attempt in range(4):
    try:
        df = yf.download(todo if todo else ETFS, start="2023-06-01", end="2026-10-03",
                         interval="1d", auto_adjust=False, progress=False,
                         prepost=False, threads=True, group_by="ticker")
        break
    except Exception as e:
        print(f"  attempt {attempt+1} {type(e).__name__}: {e}", flush=True)
        time.sleep(15 + 10 * attempt)
else:
    df = None
if df is None or df.empty:
    print("FAILED: batch download returned nothing", flush=True)
    raise SystemExit(1)
for s in (todo or ETFS):
    try:
        sub = df[s] if s in df.columns.get_level_values(0) else None
    except Exception:
        sub = None
    if sub is None:
        done[s] = {"ok": False, "error": "not-in-batch-result"}
        continue
    if isinstance(sub.columns, pd.MultiIndex):
        sub.columns = sub.columns.get_level_values(-1)
    out, err = clean_one(sub)
    if err:
        done[s] = {"ok": False, "error": err}
    else:
        out.to_pickle(path(s))
        done[s] = {"ok": True, "bars": len(out),
                   "start": out.index[0].strftime("%Y-%m-%d"),
                   "end": out.index[-1].strftime("%Y-%m-%d")}
    print(f"  {s}: {done[s]}", flush=True)
with open(log_path, "w") as f:
    json.dump(done, f, indent=1)
print("DONE sector ETF fetch")
