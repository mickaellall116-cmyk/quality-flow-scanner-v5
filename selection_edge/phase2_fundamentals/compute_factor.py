"""F7-REV factor computation: strict-PIT net analyst revisions, cross-sectional
quartile buckets on the 353-trade working set. Pre-registered in REPORT.md."""
import json, warnings
from datetime import datetime
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
DIR = "/home/hatch/workspace/quality-flow-scanner-v5/selection_edge/phase2_fundamentals"
BLIND = {"QQQ","SMCI","PLTR","ANET","SOFI","RKLB","ONDS","DRAM","SPCX","ASTX","BBAI","NIO","HOOD","AMD"}

# --- universe (117 working names) ---
u = json.load(open("/home/hatch/workspace/quality-flow-scanner-v5/canonical_baseline/universe.json"))
names = [e["symbol"] for e in u if e["symbol"] not in BLIND and e["sector"] != "ETF"]
assert len(names) == 113, len(names)

# --- revision event log ---
series = json.load(open(f"{DIR}/revision_series.json"))
evts = {}
for s in names:
    ev = []
    for e in series.get(s, []):
        if "error" in e:
            continue
        if e["action"] in ("up", "down"):
            ev.append((pd.Timestamp(e["date"]).date(), e["action"]))
    evts[s] = sorted(ev)

# --- NYSE trading calendar from downloaded daily closes ---
px = pd.read_pickle(f"{DIR}/daily_prices.pkl")
closes = px.xs("Close", axis=1, level=1)
# a trading day = any day with >50% names non-NaN close
cal = sorted(d for d in closes.index
             if closes.loc[d].notna().mean() > 0.5)
cal = [d.date() for d in cal]
cal_idx = {d: i for i, d in enumerate(cal)}
print("calendar days:", len(cal), cal[0], "->", cal[-1], flush=True)

def asof(signal_close_ts):
    """last completed daily bar <= signal-bar close (canonical PIT)."""
    ts = pd.Timestamp(signal_close_ts).tz_convert("America/New_York")
    d = ts.date()
    i = cal_idx.get(d)
    if i is None:  # non-trading day -> step back
        cands = [c for c in cal if c <= d]
        return cands[-1] if cands else None
    # signal-bar close 13:30 ET -> that day's daily bar still forming -> prior day
    if ts.hour < 16:
        return cal[i - 1]
    return d

def V(s, d):
    """net up-down in trailing 63 trading days, GradeDate in (d-63td, d]."""
    i = cal_idx[d]
    lo = cal[max(0, i - 63)]
    n_up = n_dn = 0
    for (ed, a) in evts[s]:
        if lo < ed <= d:
            if a == "up":
                n_up += 1
            else:
                n_dn += 1
    return n_up - n_dn

# --- trades, blinded names masked; ETF/notes excluded (factor is a STOCK
# selection factor: no analyst coverage exists for ETFs, so V is undefined).
# Scope decision made before results: 353 -> 330 stock trades. ---
usec = {e["symbol"]: e["sector"] for e in u}
trades = json.load(open("/home/hatch/workspace/quality-flow-scanner-v5/canonical_baseline/canonical_trades.json"))
trades = [t for t in trades if t["symbol"] not in BLIND and usec.get(t["symbol"]) != "ETF"]
n_etf_excluded = 353 - len(trades)
print("working stock trades:", len(trades), f"({n_etf_excluded} ETF trades excluded)", flush=True)

# unique as-of dates -> compute V for all 117 names once per date
asofs = {}
for t in trades:
    d = asof(t["signal_bar_close_at"])
    asofs.setdefault(d, []).append(t["signal_id"])
print("unique asof dates:", len(asofs), flush=True)

Vmat = {}  # d -> {symbol: V}
for j, d in enumerate(sorted(asofs)):
    Vmat[d] = {s: V(s, d) for s in names}
    if (j + 1) % 50 == 0:
        print(f"  V computed {j+1}/{len(asofs)}", flush=True)

rows = []
for t in trades:
    d = asof(t["signal_bar_close_at"])
    vals = Vmat[d]
    v = vals[t["symbol"]]
    arr = np.array([vals[s] for s in names])
    pct = (arr < v).mean() + 0.5 * (arr == v).mean()  # average-rank percentile
    bucket = "top" if pct >= 0.75 else ("bottom" if pct < 0.25 else "mid")
    rows.append({
        "signal_id": t["signal_id"], "symbol": t["symbol"],
        "signal_date": pd.Timestamp(t["signal_bar_close_at"]).tz_convert("America/New_York").strftime("%Y-%m-%d"),
        "asof": str(d), "V": v, "pct": round(float(pct), 4), "bucket": bucket,
        "r25": t["net_r_25bps"], "r50": t["net_r_50bps"],
        "r75": t["net_r_75bps"], "r100": t["net_r_100bps"],
    })

df = pd.DataFrame(rows)
df.to_json(f"{DIR}/factor_values.json", orient="records", indent=1)
print(df["bucket"].value_counts().to_dict(), flush=True)
print("saved factor_values.json", flush=True)
