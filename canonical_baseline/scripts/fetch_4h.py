"""Step 5: fetch 1H bars (trailing 730d, the yfinance intraday limit) and
resample to session-aligned 4H bars, same convention as the repo's
pine_entry_timing_backtest/fetch_resample_4h.py:
  - per-day groups, 4h bins anchored at 09:30 ET session open
    (bars at 09:30 and 13:30 ET; no bar spans the overnight gap)
  - agg: Open first, High max, Low min, Close last, Volume sum
  - America/New_York, regular session only (prepost=False), no premarket
  - split-adjusted (Yahoo retro-applies splits to intraday); dividends are
    NOT adjusted on intraday bars (immaterial at 4H horizon; daily cache
    is fully split/dividend-adjusted)
Writes canonical_baseline/data/h4_{SYM}.pkl
"""
import os, json, time
import pandas as pd
import yfinance as yf

REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
CB = os.path.join(REPO, "canonical_baseline")
DATA = os.path.join(CB, "data")

rows = json.load(open(os.path.join(CB, "addv_ranking_20230930.json")))[:120]
new = [r["symbol"] for r in json.load(open(os.path.join(CB, "new_listings_eval.json"))) if r["pass_gate"]]
OVERLAY_EXTRA = ["SOFI", "RKLB", "ONDS", "BBAI", "HOOD", "ASTX"]  # overlay-14 names outside universe
syms = sorted(set([r["symbol"] for r in rows] + new + OVERLAY_EXTRA))

log_path = os.path.join(CB, "fetch_4h_log.json")
done = json.load(open(log_path)) if os.path.exists(log_path) else {}
AGG = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}

def resample_4h(df):
    tz = df.index.tz
    out_days = []
    for day, g in df.groupby(df.index.date, sort=True):
        g = g.sort_index()
        origin = pd.Timestamp(day).tz_localize(tz) + pd.Timedelta(hours=9, minutes=30)
        r = g.resample("4h", origin=origin).agg(AGG)
        r = r.dropna(subset=["Close"])
        if not r.empty:
            out_days.append(r)
    if not out_days:
        return df.iloc[0:0]
    out = pd.concat(out_days).sort_index()
    return out[~out.index.duplicated(keep="last")]

if __name__ == "__main__":
    todo = [s for s in syms if not (done.get(s, {}).get("ok") and os.path.exists(os.path.join(DATA, f"h4_{s}.pkl")))]
    print(f"{len(syms)} symbols, {len(todo)} to fetch", flush=True)
    B = 25
    for b in range(0, len(todo), B):
        batch = todo[b:b+B]
        df = None
        for attempt in range(4):
            try:
                df = yf.download(batch, period="730d", interval="1h",
                                 auto_adjust=False, progress=False,
                                 prepost=False, threads=True, group_by="ticker")
                break
            except Exception as e:
                print(f"  batch {b//B+1}: attempt {attempt+1} {type(e).__name__}: {e}", flush=True)
                time.sleep(15 + 10 * attempt)
        if df is None or df.empty:
            for s in batch: done[s] = {"ok": False, "error": "batch-failed"}
            continue
        for s in batch:
            try:
                sub = df[s] if s in df.columns.get_level_values(0) else None
            except Exception:
                sub = None
            if sub is None:
                done[s] = {"ok": False, "error": "not-in-batch-result"}; continue
            if isinstance(sub.columns, pd.MultiIndex):
                sub.columns = sub.columns.get_level_values(-1)
            keep = [c for c in ["Open","High","Low","Close","Volume"] if c in sub.columns]
            sub = sub[keep].dropna(subset=["Close"])
            sub = sub[~sub.index.duplicated(keep="last")].sort_index()
            if sub.empty:
                done[s] = {"ok": False, "error": "no-valid-rows"}; continue
            if sub.index.tz is None:
                sub.index = sub.index.tz_localize("America/New_York")
            h4 = resample_4h(sub)
            h4.to_pickle(os.path.join(DATA, f"h4_{s}.pkl"))
            done[s] = {"ok": True, "bars_1h": len(sub), "bars_4h": len(h4),
                       "start": h4.index[0].isoformat(), "end": h4.index[-1].isoformat()}
            print(f"    {s}: {len(sub)} 1H -> {len(h4)} 4H ({h4.index[0].date()} .. {h4.index[-1].date()})", flush=True)
        ok = sum(1 for s in batch if done.get(s, {}).get("ok"))
        print(f"  batch {b//B+1} ({len(batch)} sym): {ok} ok", flush=True)
        with open(log_path, "w") as f: json.dump(done, f, indent=1)
        time.sleep(4)
    print("DONE 4h fetch")
