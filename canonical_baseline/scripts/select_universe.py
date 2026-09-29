"""Step 3: select the PIT universe.

Rule (all information available 2023-09-30):
  1. Rank candidate-pool names by trailing-63-trading-day average daily
     dollar volume (adj Close x Volume) ending 2023-09-30.
  2. Universe = top 120 rankable US common stocks / plain ETFs.
     - rankable = >=30 daily bars in the 63-day window
     - excluded from ranking: crypto pairs, leveraged/inverse ETFs
  3. New listings (first bar after 2023-09-30): enter from listing date +
     60 4H bars, subject to a PIT liquidity gate (trailing-20d ADDV >= $25M
     at eligibility). No backfill.
  4. Delisted/acquired names: kept through their last trading day.
Writes canonical_baseline/universe.json (list of dicts) and prints the ranking.
"""
import os, json
import pandas as pd

REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
CB = os.path.join(REPO, "canonical_baseline")
DATA = os.path.join(CB, "data")

CUTOFF = pd.Timestamp("2023-09-30", tz="America/New_York")
WIN_START = pd.Timestamp("2023-06-30", tz="America/New_York")
LEVERAGED = {"ASTX"}  # 2x daily-reset ETFs/ETNs in pool (documented exclusion)
N_TOP = 120

pool = [r["symbol"] for r in json.load(open(os.path.join(CB, "candidate_pool.json")))]
log = json.load(open(os.path.join(CB, "fetch_daily_log.json")))

def load(sym):
    p = os.path.join(DATA, f"d1_{sym}.pkl")
    return pd.read_pickle(p) if os.path.exists(p) else None

rows = []
unrankable = []
for sym in pool:
    if sym.endswith("-USD"):
        unrankable.append((sym, "crypto_pair")); continue
    if sym in LEVERAGED:
        unrankable.append((sym, "leveraged_etf")); continue
    if sym == "SQ":
        unrankable.append((sym, "renamed_XYZ_alias")); continue
    df = load(sym)
    if df is None or not log.get(sym, {}).get("ok"):
        unrankable.append((sym, "no_daily_data")); continue
    w = df[(df.index >= WIN_START) & (df.index <= CUTOFF)]
    first_bar = df.index[0]
    listed_after = first_bar > CUTOFF
    if not listed_after and len(w) < 30:
        unrankable.append((sym, f"thin_history_{len(w)}bars")); continue
    if listed_after:
        unrankable.append((sym, "listed_after_cutoff")); continue
    dv = (w["Close"] * w["Volume"]).mean()
    rows.append({"symbol": sym, "addv": float(dv), "win_bars": len(w),
                 "first_bar": first_bar.strftime("%Y-%m-%d"),
                 "last_bar": df.index[-1].strftime("%Y-%m-%d")})

rows.sort(key=lambda r: -r["addv"])
sel = rows[:N_TOP]
print(f"rankable: {len(rows)} | selected top {N_TOP}")
print(f"cutoff ADDV (rank {N_TOP}): ${sel[-1]['addv']/1e6:.1f}M/day")
print(f"rank 1: {rows[0]['symbol']} ${rows[0]['addv']/1e9:.2f}B/day")
print(f"rank {N_TOP+1} (first excluded): {rows[N_TOP]['symbol']} ${rows[N_TOP]['addv']/1e6:.1f}M/day")

with open(os.path.join(CB, "addv_ranking_20230930.json"), "w") as f:
    json.dump(rows, f, indent=1)
with open(os.path.join(CB, "addv_unrankable.json"), "w") as f:
    json.dump([{"symbol": s, "reason": r} for s, r in sorted(unrankable)], f, indent=1)
print("wrote addv_ranking + addv_unrankable")
