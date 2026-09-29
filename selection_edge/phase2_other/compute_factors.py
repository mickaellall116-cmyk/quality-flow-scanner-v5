"""Worker C: compute strict-PIT factor series for FAM2/FAM3/FAM5/FAM6 and attach
cross-sectional quartile buckets to each canonical trade.

Definitions are PRE-REGISTERED in REPORT.md (Section 1) and locked. This script
only implements them. Masked 14 names never enter construction or ranking.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
BASE = os.path.join(REPO, "canonical_baseline")
OUT = os.path.join(REPO, "selection_edge", "phase2_other")
sys.path.insert(0, BASE)
sys.path.insert(0, REPO)
import simlib  # noqa: E402

MASK14 = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB", "ONDS", "DRAM",
          "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
COST_BPS = [0.0025, 0.005, 0.0075, 0.01]


def working_symbols():
    uni = [u["symbol"] for u in simlib.load_universe()]
    work = [s for s in uni if s not in MASK14]
    assert not any(s in MASK14 for s in work)
    return work


def pit_endpoint_idx(d1idx, signal_ts):
    """Index of last COMPLETED daily bar as of signal-bar close (W1 convention)."""
    ts = pd.Timestamp(signal_ts)
    j = d1idx.searchsorted(ts, side="right") - 1
    if ts.hour < 16:
        j -= 1
    return int(j)


def _slope_roll(ldv, n):
    """OLS slope of ldv over trailing n-day windows via rolling sums (exact)."""
    # window positions k=0..n-1; global index j; k = j - (i-n+1)
    T1 = n * (n - 1) / 2.0
    T2 = (n - 1) * n * (2 * n - 1) / 6.0
    denom = n * T2 - T1 * T1
    j = np.arange(len(ldv), dtype=float)
    S1 = ldv.rolling(n, min_periods=n).sum()
    S2 = (ldv * j).rolling(n, min_periods=n).sum()
    i = j
    S2w = S2 - (i - n + 1) * S1          # sum(k*y) within window
    slope = (n * S2w - T1 * S1) / denom
    return slope


def factor_series(sym):
    """Causal daily factor series dict -> pandas Series (NaN until warm)."""
    df = simlib.load_d1(sym)
    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    vol = df["Volume"].astype(float)
    out = {"index": df.index}

    # ---- FAM2: % of last N days with close above 50d EMA ----
    ema50 = close.ewm(span=50, adjust=False).mean()
    above = (close > ema50).astype(float)
    above = above.where(close.notna() & ema50.notna())
    for n in (42, 63, 84):
        out[f"fam2_{n}"] = above.rolling(n, min_periods=n).mean()

    # ---- FAM3: N-day return / (ATR14/close), Wilder ATR ----
    prev_close = close.shift(1)
    tr = pd.DataFrame({
        "a": (high - low).abs(),
        "b": (high - prev_close).abs(),
        "c": (low - prev_close).abs(),
    }).max(axis=1)
    atr14 = tr.ewm(alpha=1.0 / 14.0, adjust=False).mean()
    scale = atr14 / close
    scale = scale.where((scale > 0) & scale.notna())
    for n in (84, 126, 168):
        ret = close / close.shift(n) - 1.0
        out[f"fam3_{n}"] = ret / scale

    # ---- FAM5: N-day realized-vol percentile vs own trailing 252 ----
    logret = np.log(close / prev_close)
    for n in (42, 63, 84):
        rv = logret.rolling(n, min_periods=n).std(ddof=1) * np.sqrt(252.0)
        out[f"fam5_{n}"] = rv.rolling(252, min_periods=252).rank(pct=True)

    # ---- FAM6: OLS slope of log(dollar volume) over trailing N days ----
    dvol = (close * vol).where((close > 0) & (vol > 0))
    ldv = np.log(dvol)
    for n in (42, 63, 84):
        out[f"fam6_{n}"] = _slope_roll(ldv, n)

    return out


def bucketize(val, xs):
    """Quartile bucket of val within cross-section xs (pre-registered rule)."""
    if val is None or np.isnan(val) or len(xs) == 0:
        return None
    q25, q75 = np.percentile(xs, [25, 75])
    if val >= q75:
        return "TOP"
    if val <= q25:
        return "BOTTOM"
    return "MIDDLE"


def main():
    t0 = time.time()
    work = working_symbols()
    print(f"working set: {len(work)}", flush=True)

    trades = json.load(open(os.path.join(BASE, "canonical_trades.json")))
    masked_trades = [t for t in trades if t["symbol"] in MASK14]
    trades = [t for t in trades if t["symbol"] not in MASK14]
    print(f"canonical trades: {len(trades)} (masked out {len(masked_trades)}: "
          f"{sorted(set(t['symbol'] for t in masked_trades))})", flush=True)

    # ---- precompute factor series for every working symbol ----
    F = {}
    for k, sym in enumerate(work):
        F[sym] = factor_series(sym)
        if (k + 1) % 30 == 0:
            print(f"  series {k+1}/{len(work)} ({time.time()-t0:.0f}s)", flush=True)

    fams = {
        "fam2": [("fam2_63", "fam2_42", "fam2_84")],
        "fam3": [("fam3_126", "fam3_84", "fam3_168")],
        "fam5": [("fam5_63", "fam5_42", "fam5_84")],
        "fam6": [("fam6_63", "fam6_42", "fam6_84")],
    }
    keys = ["fam2_63", "fam2_42", "fam2_84", "fam3_126", "fam3_84", "fam3_168",
            "fam5_63", "fam5_42", "fam5_84", "fam6_63", "fam6_42", "fam6_84"]

    records = []
    n_null = {k: 0 for k in keys}
    for ti, t in enumerate(trades):
        ts = t["signal_bar_close_at"]
        rec = {
            "signal_id": t["signal_id"], "symbol": t["symbol"],
            "signal_bar_close_at": ts, "entry_ts": t["entry_ts"],
            "exit_ts": t["exit_ts"], "exit_reason": t["exit_reason"],
            "net_r_25bps": t["net_r_25bps"], "net_r_50bps": t["net_r_50bps"],
            "net_r_75bps": t["net_r_75bps"], "net_r_100bps": t["net_r_100bps"],
        }
        # cross-section per factor key at this signal's PIT endpoint
        for key in keys:
            xs = []
            own = None
            for sym in work:
                idx = F[sym]["index"]
                j = pit_endpoint_idx(idx, ts)
                if j < 0:
                    continue
                v = F[sym][key].iloc[j]
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    continue
                v = float(v)
                xs.append(v)
                if sym == t["symbol"]:
                    own = v
            if own is None:
                n_null[key] += 1
            rec[f"{key}_val"] = own
            rec[f"{key}_bucket"] = bucketize(own, np.array(xs))
            rec[f"{key}_xs_n"] = len(xs)
        records.append(rec)
        if (ti + 1) % 100 == 0:
            print(f"  bucketed {ti+1}/{len(trades)} ({time.time()-t0:.0f}s)", flush=True)

    print("null-own-value counts:", n_null, flush=True)
    out_path = os.path.join(OUT, "trade_factors.json")
    with open(out_path, "w") as fh:
        json.dump(records, fh, default=str)
    print(f"wrote {out_path} ({len(records)} trades) in {time.time()-t0:.0f}s",
          flush=True)


if __name__ == "__main__":
    main()
