#!/usr/bin/env python3
"""N-wave price-target hit-rate study (clean-room).

Implements textbook Ichimoku (Hosoda) price-theory projections from scratch:
developing N-wave detection on confirmed pivot swings, V/E/N/NT targets,
30-bar forward hit/invalidation measurement. No third-party indicator code
is used or referenced.

FROZEN PREREG: selection_edge/nwave_targets_prereg.md (commit 41a1229).
This script implements it exactly; no tuning.
"""
import pickle, json, statistics, os

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
TICKERS = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB", "ONDS",
           "DRAM", "SPCX", "BBAI", "NIO", "HOOD", "AMD"]
TFS = {
    "1H":    os.path.join(REPO, "pine_1h", "cache", "h1_{t}.pkl"),
    "4H":    os.path.join(REPO, "backtest_cache", "h4_{t}.pkl"),
    "daily": os.path.join(REPO, "backtest_cache", "d1_{t}.pkl"),
}
L = 10          # pivot length
SPAN_MIN = 9    # min wave span in bars
FWD = 30        # forward measurement window
TOL = 0.2       # tolerance band fraction of |A-B|

def load(ticker, tf):
    p = TFS[tf].format(t=ticker)
    if not os.path.exists(p):
        return None
    df = pickle.load(open(p, "rb"))
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    return df.reset_index(drop=True) if len(df) > 2 * L + FWD + 10 else None

def find_pivots(df):
    """Confirmed alternating pivot swings. Returns list of dicts
    (bar, price, side) with bar = pivot bar index; confirmed separately."""
    hi = df["High"].to_numpy()
    lo = df["Low"].to_numpy()
    n = len(df)
    cands = []  # (bar, price, side)
    for i in range(L, n - L):
        w_hi = hi[i - L:i + L + 1]
        w_lo = lo[i - L:i + L + 1]
        # earliest-bar-wins ties: strictly greater than left part of window
        if hi[i] == w_hi.max() and hi[i] > w_hi[:L].max():
            cands.append((i, float(hi[i]), "H"))
        elif lo[i] == w_lo.min() and lo[i] < w_lo[:L].min():
            cands.append((i, float(lo[i]), "L"))
    # enforce strict alternation, keep more extreme on same-side runs
    swings = []
    for bar, price, side in cands:
        if swings and swings[-1][2] == side:
            pb, pp, ps = swings[-1]
            if (side == "H" and price > pp) or (side == "L" and price < pp):
                swings[-1] = (bar, price, side)
        else:
            swings.append((bar, price, side))
    return swings

def detect_events(df):
    """Yield detection events: dict with d (detection bar), A, B, C, side."""
    swings = find_pivots(df)
    events = []
    for k in range(2, len(swings)):
        A = swings[k - 2]; B = swings[k - 1]; C = swings[k]
        d = C[0] + L  # confirmation bar of pivot C
        if C[0] - A[0] < SPAN_MIN:
            continue
        ap, bp, cp = A[1], B[1], C[1]
        T = TOL * abs(ap - bp)
        bull = ap < bp and cp > ap + T and cp < bp - T
        bear = ap > bp and cp < ap - T and cp > bp + T
        if not (bull or bear):
            continue
        if bull:
            targets = {"V": bp + (bp - cp), "E": bp + (bp - ap),
                       "N": cp + (bp - ap), "NT": cp + (cp - ap)}
        else:
            targets = {"V": bp - (cp - bp), "E": bp - (ap - bp),
                       "N": cp - (ap - bp), "NT": cp - (cp - ap)}
        events.append({"d": d, "side": "bull" if bull else "bear",
                       "Cprice": cp, "targets": targets,
                       "Abar": A[0], "Bbar": B[0], "Cbar": C[0]})
    return events

def measure(df, ev):
    """Measure one event. Returns dict target -> (status, bars_to_touch)."""
    hi = df["High"].to_numpy(); lo = df["Low"].to_numpy()
    cl = df["Close"].to_numpy()
    n = len(df)
    d = ev["d"]
    if d + FWD >= n or d < 1:
        return None  # incomplete window
    bull = ev["side"] == "bull"
    # running extremes up to and including d (already-hit check)
    if bull:
        hit_so_far = {t: (hi[:d + 1].max() >= v) for t, v in ev["targets"].items()}
    else:
        hit_so_far = {t: (lo[:d + 1].min() <= v) for t, v in ev["targets"].items()}
    out = {}
    for t, v in ev["targets"].items():
        if hit_so_far[t]:
            out[t] = ("excluded", None)
            continue
        status, btt = "miss", None
        for k in range(1, FWD + 1):
            j = d + k
            if bull:
                inv = lo[j] < ev["Cprice"]
                tch = hi[j] >= v
            else:
                inv = hi[j] > ev["Cprice"]
                tch = lo[j] <= v
            if inv:                      # structure break checked first:
                status = "invalidated"  # conservative vs the hypothesis
                break
            if tch:
                status, btt = "hit", k
                break
        out[t] = (status, btt)
    return out

def main():
    agg = {}   # tf -> target -> stats
    per_ticker = {}
    for tf in TFS:
        agg[tf] = {t: {"n": 0, "hits": 0, "invalidated": 0,
                       "btt": []} for t in ("V", "E", "N", "NT")}
        per_ticker[tf] = {}
        for tk in TICKERS:
            df = load(tk, tf)
            if df is None:
                per_ticker[tf][tk] = {"error": "no data"}
                continue
            evs = detect_events(df)
            cnt = {"events": 0, "measured": 0}
            for ev in evs:
                r = measure(df, ev)
                if r is None:
                    continue
                cnt["events"] += 1
                for t, (st, btt) in r.items():
                    if st == "excluded":
                        continue
                    cnt["measured"] += 1
                    s = agg[tf][t]
                    s["n"] += 1
                    if st == "hit":
                        s["hits"] += 1
                        s["btt"].append(btt)
                    elif st == "invalidated":
                        s["invalidated"] += 1
            per_ticker[tf][tk] = cnt
    summary = {}
    for tf in TFS:
        summary[tf] = {}
        for t, s in agg[tf].items():
            n = s["n"]
            summary[tf][t] = {
                "n": n,
                "hit_rate": round(s["hits"] / n, 4) if n else None,
                "invalidation_rate": round(s["invalidated"] / n, 4) if n else None,
                "median_bars_to_touch": (statistics.median(s["btt"])
                                         if s["btt"] else None),
                "hits": s["hits"], "invalidated": s["invalidated"],
            }
    json.dump({"summary": summary, "per_ticker": per_ticker},
              open(os.path.join(BASE, "nwave_targets_results.json"), "w"),
              indent=1)
    # console table
    for tf in TFS:
        print(f"--- {tf} ---")
        for t in ("V", "E", "N", "NT"):
            s = summary[tf][t]
            print(f"  {t}: n={s['n']} hit={s['hit_rate']} "
                  f"inv={s['invalidation_rate']} med_btt={s['median_bars_to_touch']}")
    # PASS/FAIL vs pre-set criteria
    verdict = "FAIL"
    for t in ("N", "NT"):
        ok_tfs = [tf for tf in TFS
                  if (summary[tf][t]["hit_rate"] or 0) >= 0.60
                  and (summary[tf][t]["median_bars_to_touch"] or 999) <= 15]
        if len(ok_tfs) >= 2:
            verdict = "PASS"
    print("VERDICT:", verdict)
    return verdict

if __name__ == "__main__":
    main()
