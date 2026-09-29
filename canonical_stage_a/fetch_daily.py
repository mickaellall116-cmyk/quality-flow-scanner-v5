#!/usr/bin/env python3
"""Stage A — fresh daily PIT cache rebuild (rev-6.1, §11).

Recipe (frozen):
  source yfinance; window 2023-06-01 -> 2026-09-24 (end-exclusive 2026-09-25);
  auto_adjust=False; OHLC scaled by AdjClose/Close factor (split- AND
  dividend-adjusted); raw Volume; America/New_York; regular session only.

One deterministic JSON cache file per symbol under canonical_stage_a/data/.
Never reuses canonical_baseline/data/*.pkl (quarantine). Never invents or
splices data: persistent vendor blocks become a data-availability finding.
"""
import json, time, hashlib, datetime, os, sys
import pandas as pd
import yfinance as yf

WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(WORKTREE, "canonical_stage_a", "data")
POOL_SRC = "/home/hatch/workspace/quality-flow-scanner-v5/canonical_baseline/candidate_pool.json"

START = "2023-06-01"
END = "2026-09-25"          # end-exclusive -> last bar 2026-09-24
BATCH = 20
SLEEP_BETWEEN_BATCHES = 4.0
MAX_RETRIES = 3

def sanitize(sym):
    return sym.replace("-", "_").replace(".", "_")

def fetch_batch(symbols):
    """Single yfinance request for a batch; returns {symbol: df or None}."""
    df = yf.download(
        symbols, start=START, end=END, interval="1d",
        auto_adjust=False, prepost=False, progress=False, threads=False,
    )
    out = {}
    if df is None or df.empty:
        return {s: None for s in symbols}
    cols = df.columns
    if isinstance(cols, pd.MultiIndex):
        tickers = cols.get_level_values(1).unique().tolist() if cols.nlevels > 1 else []
        for s in symbols:
            sub = None
            for t in tickers:
                if t.upper() == s.upper():
                    sub = df.xs(t, axis=1, level=1); break
            out[s] = sub
    else:
        # single-symbol fallback shape
        if len(symbols) == 1:
            out[symbols[0]] = df
        else:
            out = {s: None for s in symbols}
    return out

def normalize(s, raw):
    """Apply the frozen adjustment recipe; return list of rows or None."""
    if raw is None or raw.empty:
        return None
    need = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}
    if not need.issubset(set(raw.columns)):
        return None
    r = raw.copy()
    r.index = pd.to_datetime(r.index)
    if r.index.tz is None:
        r.index = r.index.tz_localize("America/New_York")
    else:
        r.index = r.index.tz_convert("America/New_York")
    r = r.sort_index()
    # Drop calendar-padding rows: batch downloads align all tickers on the
    # union of dates (crypto trades 24/7), so stock symbols can carry
    # NaN-OHLC weekend/holiday rows. Equivalent of the documented dropna().
    r = r.dropna(subset=["Open", "High", "Low", "Close"])
    close = r["Close"].astype(float)
    adj = r["Adj Close"].astype(float)
    factor = (adj / close).where(close != 0, 1.0).fillna(1.0)
    rows = []
    for ts, row in r.iterrows():
        vol = row["Volume"]
        rows.append([
            ts.strftime("%Y-%m-%d"),
            float(row["Open"] * factor.loc[ts]),
            float(row["High"] * factor.loc[ts]),
            float(row["Low"] * factor.loc[ts]),
            float(row["Close"] * factor.loc[ts]),
            float(row["Adj Close"]),
            0 if pd.isna(vol) else int(vol),
        ])
    return rows

def write_cache(symbol, rows, fetch_ts):
    payload = {
        "symbol": symbol,
        "spec": "rev-6.1 §11 daily cache",
        "window": {"start": START, "end_exclusive": END},
        "adjustment": "auto_adjust=False; OHLC scaled by AdjClose/Close; Volume raw",
        "timezone": "America/New_York",
        "fetch_timestamp_utc": fetch_ts,
        "n_bars": len(rows),
        "first_bar": rows[0][0] if rows else None,
        "last_bar": rows[-1][0] if rows else None,
        "columns": ["date", "open_adj", "high_adj", "low_adj", "close_adj", "adj_close", "volume_raw"],
        "rows": rows,
    }
    text = json.dumps(payload, indent=1, sort_keys=False) + "\n"
    path = os.path.join(DATA_DIR, f"d1_{sanitize(symbol)}.json")
    with open(path, "w") as f:
        f.write(text)
    return hashlib.sha256(text.encode()).hexdigest(), path

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    pool = json.load(open(POOL_SRC))
    symbols = [e["symbol"] for e in pool]
    print(f"[fetch] {len(symbols)} symbols, batches of {BATCH}", flush=True)
    manifest = {}
    pending = list(symbols)
    attempt = 0
    while pending and attempt < MAX_RETRIES:
        attempt += 1
        remaining = []
        for i in range(0, len(pending), BATCH):
            batch = pending[i:i + BATCH]
            try:
                res = fetch_batch(batch)
            except Exception as e:
                print(f"[fetch] batch error ({batch[0]}..{batch[-1]}): {e}; retrying individually", flush=True)
                res = {s: None for s in batch}
            for s in batch:
                rows = normalize(s, res.get(s))
                ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                if rows:
                    digest, path = write_cache(s, rows, ts)
                    manifest[s] = {"status": "ok", "n_bars": len(rows),
                                   "first_bar": rows[0][0], "last_bar": rows[-1][0],
                                   "fetch_timestamp_utc": ts,
                                   "sha256": digest, "file": os.path.basename(path)}
                    print(f"[fetch] {s}: {len(rows)} bars {rows[0][0]}->{rows[-1][0]}", flush=True)
                else:
                    remaining.append(s)
            time.sleep(SLEEP_BETWEEN_BATCHES)
        pending = remaining
        if pending:
            print(f"[fetch] attempt {attempt}: {len(pending)} still missing: {pending}", flush=True)
            time.sleep(10 * attempt)
    for s in pending:
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        manifest[s] = {"status": "missing_no_data", "n_bars": 0,
                       "fetch_timestamp_utc": ts, "note": "yfinance returned no daily bars after retries"}
        print(f"[fetch] MISSING: {s}", flush=True)
    mpath = os.path.join(WORKTREE, "canonical_stage_a", "fetch_manifest.json")
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    ok = sum(1 for v in manifest.values() if v["status"] == "ok")
    print(f"[fetch] DONE: {ok}/{len(symbols)} ok, {len(pending)} missing", flush=True)

if __name__ == "__main__":
    main()
