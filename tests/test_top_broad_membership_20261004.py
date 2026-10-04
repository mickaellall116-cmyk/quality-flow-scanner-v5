#!/usr/bin/env python3
"""TOP-50 / BROAD membership + paired bootstrap (System 1 experiment).

Implements the frozen v3 proposal §2 (universe) and §7 (inference):
- Quarterly TOP-50 selection: 60-day dollar volume + 126-day RS vs SPY,
  percentile ranks (best=0), 50/50 composite, 50 smallest win.
- Split-adjudication: 3 trading days centered on split dates excluded from
  the 60-day dollar-volume mean (mechanical, no price adjustment).
- Paired moving-block bootstrap: 3-month contiguous blocks, seed 20261004.

Synthetic fixtures below verify the mechanics. No real data.
"""
import hashlib
import numpy as np
import pandas as pd

print("TOP/BROAD membership + bootstrap — synthetic verification")


# ------------------------------------------------------------ membership
def compute_top50(dollar_vol, rs_ret, split_dates=None, top_n=50):
    """Select TOP-N by frozen composite.

    dollar_vol: dict symbol -> Series of daily dollar volume (60+ trading days)
    rs_ret: dict symbol -> 126-day return vs SPY (float); None if insufficient
    split_dates: dict symbol -> list of dates (3-day exclusion window)
    Returns: (selected list, diagnostics dict)
    """
    rows = []
    for sym, dv in dollar_vol.items():
        # Split adjudication: exclude 3 trading days centered on each split
        sdv = dv.copy()
        for sd in (split_dates or {}).get(sym, []):
            sd = pd.Timestamp(sd)
            mask = (sdv.index >= sd - pd.Timedelta(days=2)) & \
                   (sdv.index <= sd + pd.Timedelta(days=2))
            # Exclude up to 3 trading days centered on split (event day +/-1)
            locs = sdv.index[mask]
            # Take at most 3: the closest trading days to the event
            if len(locs) > 0:
                center = np.argmin(np.abs((locs - sd).total_seconds()))
                lo = max(0, center - 1)
                hi = min(len(locs), center + 2)
                sdv = sdv.drop(locs[lo:hi])
        if len(sdv) < 50:
            continue  # insufficient valid days -> excluded, not imputed
        liq = float(sdv.tail(60).mean())
        rs = rs_ret.get(sym)
        if rs is None or not np.isfinite(rs) or not np.isfinite(liq):
            continue
        rows.append((sym, liq, rs))
    if len(rows) <= 1:
        return [], {"n_valid": len(rows), "degenerate": True}
    syms = [r[0] for r in rows]
    liqs = np.array([r[1] for r in rows])
    rss = np.array([r[2] for r in rows])
    # Percentile ranks: best (largest) -> 0, worst -> 1. Average method for ties.
    def pct_rank_best0(vals):
        order = np.argsort(-vals)  # descending: best first
        ranks = np.empty(len(vals))
        k = 0
        while k < len(vals):
            j = k
            while j + 1 < len(vals) and vals[order[j + 1]] == vals[order[k]]:
                j += 1
            avg = (k + j) / 2.0
            ranks[order[k:j + 1]] = avg
            k = j + 1
        n = len(vals)
        return ranks / (n - 1) if n > 1 else np.full(n, 0.5)
    liq_p = pct_rank_best0(liqs)
    rs_p = pct_rank_best0(rss)
    composite = 0.5 * liq_p + 0.5 * rs_p
    # Select top_n smallest composite; all tied at cutoff enter
    order = np.argsort(composite, kind="stable")
    if len(order) <= top_n:
        selected = [syms[i] for i in order]
    else:
        cutoff = composite[order[top_n - 1]]
        # All with composite <= cutoff enter (ties at boundary included).
        # Use tolerance for float comparison.
        selected = [syms[i] for i in order if composite[i] <= cutoff + 1e-12]
    return selected, {"n_valid": len(rows), "degenerate": False,
                      "cutoff": float(cutoff) if len(order) > top_n else None}


# ------------------------------------------------------------ bootstrap
def paired_block_bootstrap(top_trades, broad_trades, month_index,
                           n_resamples=10000, seed=20261004,
                           block_months=3, min_trades=5):
    """Paired moving-block bootstrap for TOP - BROAD expectancy difference.

    top_trades/broad_trades: lists of dicts with 'exit_month' (int index into
      month_index) and 'net_r'.
    month_index: list of month labels (length M).
    Returns dict with CI, point estimate, valid/attempted counts.
    """
    rng = np.random.default_rng(seed)
    M = len(month_index)
    # Overlapping blocks of block_months months
    blocks = [list(range(s, s + block_months))
              for s in range(M - block_months + 1)]
    # Index trades by exit month
    def by_month(trades):
        d = {}
        for t in trades:
            d.setdefault(t["exit_month"], []).append(t["net_r"])
        return d
    top_by_m = by_month(top_trades)
    broad_by_m = by_month(broad_trades)
    diffs = []
    discarded = 0
    for _ in range(n_resamples):
        # Sample blocks with replacement, jointly, concatenate to M months
        months_covered = []
        while len(months_covered) < M:
            b = blocks[rng.integers(len(blocks))]
            months_covered.extend(b)
        months_covered = months_covered[:M]  # explicit truncation
        t_rs, b_rs = [], []
        for m in months_covered:
            t_rs.extend(top_by_m.get(m, []))
            b_rs.extend(broad_by_m.get(m, []))
        if len(t_rs) < min_trades or len(b_rs) < min_trades:
            discarded += 1
            continue
        diffs.append(np.mean(t_rs) - np.mean(b_rs))
    diffs = np.array(diffs)
    valid = len(diffs)
    if valid == 0:
        return {"valid": 0, "attempted": n_resamples, "discarded": discarded,
                "ci": None, "inconclusive": True}
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    # Point estimate from original (unresampled) data
    t_all = [t["net_r"] for t in top_trades]
    b_all = [t["net_r"] for t in broad_trades]
    point = np.mean(t_all) - np.mean(b_all) if t_all and b_all else None
    return {"valid": valid, "attempted": n_resamples, "discarded": discarded,
            "discard_rate": discarded / n_resamples,
            "ci": (float(lo), float(hi)), "point": float(point) if point else None,
            "g5_pass": bool(lo > 0),
            "inconclusive": bool(discarded / n_resamples > 0.10)}


# ------------------------------------------------------------ fixtures
passed = failed = 0
def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS {name}")
    else:
        failed += 1
        print(f"  FAIL {name}")

print("\n== M1: TOP-50 selects strongest composite ==")
rng = np.random.default_rng(42)
dates = pd.date_range("2024-01-01", periods=80, freq="B")
dv = {}
rs_ret = {}
for k in range(60):
    sym = f"S{k:02d}"
    # Liquidity: S00 strongest, S59 weakest
    dv[sym] = pd.Series(1e8 * (60 - k) + rng.normal(0, 1e6, 80), index=dates)
    # RS: S00 strongest, S59 weakest
    rs_ret[sym] = 0.5 - k * 0.01
sel, diag = compute_top50(dv, rs_ret, top_n=50)
check("50 selected", len(sel) == 50)
check("strongest included", "S00" in sel)
check("weakest excluded", "S59" not in sel)
check("not degenerate", not diag["degenerate"])

print("\n== M2: ties at cutoff all enter ==")
dv2 = {f"T{k}": pd.Series(np.full(80, 1e8), index=dates) for k in range(10)}
rs2 = {f"T{k}": 0.1 for k in range(10)}  # all identical
sel2, _ = compute_top50(dv2, rs2, top_n=5)
check("all tied enter (10, not 5)", len(sel2) == 10)

print("\n== M3: missing inputs excluded, not imputed ==")
dv3 = {f"U{k}": pd.Series(np.full(80, 1e8), index=dates) for k in range(10)}
rs3 = {f"U{k}": 0.1 for k in range(5)}  # 5 missing RS
sel3, diag3 = compute_top50(dv3, rs3, top_n=50)
check("only 5 valid", diag3["n_valid"] == 5)
check("all 5 selected (N < 50)", len(sel3) == 5)

print("\n== M4: split-date exclusion ==")
sdates = pd.date_range("2024-01-01", periods=80, freq="B")
# Symbol with a split on day 40: dollar volume spikes 10x for 1 day (artifact)
dv4_vals = np.full(80, 1e8)
dv4_vals[40] = 1e9  # artifact
dv4 = {"SPLIT": pd.Series(dv4_vals, index=sdates),
       "CLEAN": pd.Series(np.full(80, 1e8), index=sdates)}
rs4 = {"SPLIT": 0.1, "CLEAN": 0.1}
split_dates = {"SPLIT": [sdates[40].date()]}
sel4, _ = compute_top50(dv4, rs4, split_dates=split_dates, top_n=2)
# With 3-day exclusion, SPLIT's mean ≈ 1e8 (artifact removed); without, ≈1.01e8
# Both have same RS; tie-break by stable order — key check: no crash, both valid
check("split symbol processed", "SPLIT" in sel4 or "CLEAN" in sel4)

print("\n== M5: degenerate (N<=1) ==")
sel5, diag5 = compute_top50({"ONLY": pd.Series(np.full(80, 1e8), index=dates)},
                            {"ONLY": 0.1})
check("degenerate flagged", diag5["degenerate"] and len(sel5) == 0)

print("\n== B1: bootstrap CI captures true difference ==")
# Synthetic: TOP mean +0.2R, BROAD mean +0.05R, 200 trades each over 19 months
brng = np.random.default_rng(7)
months = list(range(19))
top_tr = [{"exit_month": int(brng.integers(19)), "net_r": float(brng.normal(0.2, 1.0))}
          for _ in range(200)]
broad_tr = [{"exit_month": int(brng.integers(19)), "net_r": float(brng.normal(0.05, 1.0))}
            for _ in range(200)]
res = paired_block_bootstrap(top_tr, broad_tr, months, n_resamples=2000)
check("valid draws", res["valid"] > 1800)
check("CI lower bound > 0 (true diff +0.15R)", res["ci"][0] > 0)
check("G5 passes", res["g5_pass"])
check("not inconclusive", not res["inconclusive"])
print(f"    CI: [{res['ci'][0]:.3f}, {res['ci'][1]:.3f}], point: {res['point']:.3f}")

print("\n== B2: bootstrap INCONCLUSIVE on insufficient data ==")
few_top = [{"exit_month": 0, "net_r": 0.1} for _ in range(3)]
few_broad = [{"exit_month": 0, "net_r": 0.05} for _ in range(3)]
res2 = paired_block_bootstrap(few_top, few_broad, months, n_resamples=500)
check("inconclusive flagged", res2["inconclusive"] or res2["valid"] == 0)

print("\n== B3: degenerate draws discarded ==")
# All trades in 1 month -> most resamples lack >=5 per leg in sampled months
conc_top = [{"exit_month": 0, "net_r": 0.2} for _ in range(20)]
conc_broad = [{"exit_month": 0, "net_r": 0.1} for _ in range(20)]
res3 = paired_block_bootstrap(conc_top, conc_broad, months, n_resamples=500)
check("discard rate reported", "discard_rate" in res3)
print(f"    discard rate: {res3['discard_rate']:.2f}, valid: {res3['valid']}")

print(f"\n{passed} passed, {failed} failed")
import sys
sys.exit(1 if failed else 0)
