#!/usr/bin/env python3
"""TEST 1 — Mike's EXACT validation prompt for the lone-wolf sector-RS filter.

Rule (fixed for the main test): BLOCK when stock 20-bar RS vs SPY > 0 AND
sector ETF 20-bar RS vs SPY <= 0.
Baseline: all 237 original V5.4 trades (per-trade, same population).
Variant: same 237 trades minus the blocked ones (simple removal).
Universe: all historical V5.4 trades (all 14 symbols have sector mappings).
Period: Oct 2023 – Sep 2026.

First report + checks A–H per the prompt. pine_backtest imported UNMODIFIED.
Research only. Nothing frozen touched.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_lonewolf_protocol")
CACHE4H = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
CACHED = os.path.join(BASE, "pine_sector_rs_backtest", "cache")
OUT = os.path.join(OUTDIR, "mike_validation_results.json")
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
SECTOR = {
    "QQQ": "XLK", "SMCI": "SOXX", "PLTR": "XLK", "ANET": "XLK", "SOFI": "XLF",
    "RKLB": "XLI", "ONDS": "XLK", "DRAM": "SOXX", "SPCX": "XLI", "ASTX": "XLK",
    "BBAI": "XLK", "NIO": "XLY", "HOOD": "XLF", "AMD": "SOXX",
}
COSTS = [0.0025, 0.005, 0.0075, 0.01]
ROLL = [("2024-10-01", "2025-03-31"), ("2025-04-01", "2025-09-30"),
        ("2025-10-01", "2026-03-31"), ("2026-04-01", "2026-09-23")]


def daily_closes_4h(df4h):
    s = df4h["Close"].copy()
    s.index = s.index.tz_convert("America/New_York").tz_localize(None)
    return s.resample("1D").last().dropna()


def ret_n(series, date, n):
    idx = series.index
    pos = idx.searchsorted(date, side="right") - 1
    if pos < n:
        return np.nan
    return series.iloc[pos] / series.iloc[pos - n] - 1.0


def summarize(rs):
    """First-report stats for an R array."""
    rs = np.asarray(rs, float)
    n = len(rs)
    if n == 0:
        return {"n": 0}
    w = rs[rs > 0]
    l = rs[rs <= 0]
    gw, gl = w.sum(), -l.sum()
    eq = np.cumsum(np.sort(rs))  # placeholder; DD computed time-ordered below
    return {
        "n": n,
        "expectancy": round(float(rs.mean()), 4),
        "win_rate_pct": round(float((rs > 0).mean()) * 100, 1),
        "profit_factor": round(float(gw / gl), 2) if gl > 0 else None,
        "avg_winner": round(float(w.mean()), 4) if len(w) else None,
        "avg_loser": round(float(l.mean()), 4) if len(l) else None,
    }


def max_dd_of(rs_timeordered):
    """Max drawdown in absolute R units of a cumulative-R equity curve
    starting at 0: max over time of (running peak - current value)."""
    eq = np.cumsum(np.asarray(rs_timeordered, float))
    peak = np.maximum.accumulate(np.insert(eq, 0, 0.0))[1:]
    dd = peak - eq
    return float(dd.max()) if len(dd) else 0.0


def main():
    # ---------- data ----------
    stock_d, etf_d, h4 = {}, {}, {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE4H, f"h4_{sym}.pkl"))
        h4[sym] = df
        stock_d[sym] = daily_closes_4h(df)
    for sym in ["SPY", "XLK", "SOXX", "XLF", "XLI", "XLY"]:
        df = pd.read_pickle(os.path.join(CACHED, f"d_{sym}.pkl"))
        s = df["Close"].copy()
        s.index = pd.to_datetime(s.index.tz_localize(None)
                                if s.index.tz is not None else s.index).normalize()
        etf_d[sym] = s.asfreq("1D").ffill().dropna()

    trades = []
    for sym in WATCHLIST:
        df = pb.add_pine_indicators(h4[sym])
        ts, _ = pb.gen_pine_trades(sym, df)
        trades.extend(ts)
    trades.sort(key=lambda t: t["entry_time"])
    N = len(trades)
    print(f"baseline trades: {N}", flush=True)
    t0 = trades[0]["entry_time"]

    def sig_date(tr):
        return pd.Timestamp(tr["signal_time"]).tz_convert(
            "America/New_York").tz_localize(None).normalize()

    # ---------- flags: 15/20/25 sign-cut (B check) ----------
    flags = {}
    for L in (15, 20, 25):
        fl = {}
        for tr in trades:
            sym = tr["symbol"]
            d = sig_date(tr)
            srs = ret_n(stock_d[sym], d, L) - ret_n(etf_d["SPY"], d, L)
            secrs = ret_n(etf_d[SECTOR[sym]], d, L) - ret_n(etf_d["SPY"], d, L)
            fl[id(tr)] = bool(srs > 0 and secrs <= 0) if not (
                pd.isna(srs) or pd.isna(secrs)) else False
        flags[L] = fl
        print(f"L{L}: blocked={sum(fl.values())}", flush=True)
    FB = flags[20]  # the fixed rule

    # ---------- per-trade net R + MFE/MAE ----------
    Rc = {c: np.array([pb._outcome(t["entry"], t["stop"], t["exit"], c)[2]
                       for t in trades]) for c in COSTS}

    def excursion(tr):
        df = h4[tr["symbol"]]
        seg = df.loc[tr["entry_time"]:tr["exit_time"]]
        if len(seg) == 0:
            return np.nan, np.nan
        risk = tr["entry"] - tr["stop"]
        mfe = float(((seg["High"] - tr["entry"]) / risk).max())
        mae = float(((tr["entry"] - seg["Low"]) / risk).max())
        return mfe, mae

    exc = np.array([excursion(t) for t in trades])  # (MFE, MAE) in R
    MFE, MAE = exc[:, 0], exc[:, 1]

    is_blocked = np.array([FB[id(t)] for t in trades])
    order = np.argsort([t["entry_time"] for t in trades])

    def dd_of(mask, cost):
        return round(max_dd_of(Rc[cost][order][mask[order]]), 3)

    # ---------- FIRST REPORT ----------
    c = COSTS[0]
    rep = {"n_baseline": N, "n_blocked": int(is_blocked.sum()),
           "n_retained": int((~is_blocked).sum())}
    for name, mask in (("baseline", np.ones(N, bool)),
                       ("retained", ~is_blocked), ("blocked", is_blocked)):
        s = summarize(Rc[c][mask])
        s["max_dd_R"] = dd_of(mask, c)
        s["avg_MFE_R"] = round(float(np.nanmean(MFE[mask])), 3)
        s["avg_MAE_R"] = round(float(np.nanmean(MAE[mask])), 3)
        rep[name] = s
    print("first report:", json.dumps(rep, indent=1), flush=True)

    out = {"first_report": rep, "checks": {}}

    # ---------- A. YEAR TEST ----------
    yrs = {}
    for y in (2023, 2024, 2025, 2026):
        m = np.array([t["entry_time"].year == y for t in trades])
        if m.sum() == 0:
            continue
        b, r = Rc[c][m], Rc[c][m & ~is_blocked]
        yrs[str(y)] = {"n": int(m.sum()),
                       "baseline_exp": round(float(b.mean()), 4),
                       "retained_exp": round(float(r.mean()), 4) if len(r) else None,
                       "delta": round(float(r.mean() - b.mean()), 4) if len(r) else None}
    out["checks"]["A_year"] = yrs

    # ---------- B. LOOKBACK ROBUSTNESS (15/20/25, directional) ----------
    lk = {}
    for L in (15, 20, 25):
        m = np.array([flags[L][id(t)] for t in trades])
        b, r = Rc[c], Rc[c][~m]
        lk[str(L)] = {"blocked": int(m.sum()),
                      "delta": round(float(r.mean() - b.mean()), 4)}
    out["checks"]["B_lookback"] = lk

    # ---------- C. COST TEST ----------
    ct = {}
    for cost in COSTS:
        b, r = Rc[cost], Rc[cost][~is_blocked]
        ct[f"{int(cost*10000)}bps"] = {
            "baseline_exp": round(float(b.mean()), 4),
            "retained_exp": round(float(r.mean()), 4),
            "delta": round(float(r.mean() - b.mean()), 4)}
    out["checks"]["C_cost"] = ct

    # ---------- D. LEAVE-ONE-SYMBOL-OUT (20-bar) ----------
    loso = {}
    for sym in WATCHLIST:
        m = np.array([t["symbol"] != sym for t in trades])
        b, r = Rc[c][m], Rc[c][m & ~is_blocked]
        loso[sym] = {"delta": round(float(r.mean() - b.mean()), 4),
                     "n": int(m.sum())}
    ds = [v["delta"] for v in loso.values()]
    out["checks"]["D_loso"] = {"per_symbol": loso, "min_delta": round(min(ds), 4),
                               "max_delta": round(max(ds), 4),
                               "any_destroyed": bool(min(ds) <= 0)}

    # ---------- E. CONCENTRATION ----------
    base_mean = float(Rc[c].mean())
    contrib = [(trades[i]["symbol"], SECTOR[trades[i]["symbol"]],
                base_mean - Rc[c][i])
               for i in np.where(is_blocked)[0]]
    tot = sum(x[2] for x in contrib)
    def topk(dim, k):
        agg = {}
        for s, sec, x in contrib:
            k_ = s if dim == "symbol" else sec
            agg[k_] = agg.get(k_, 0) + x
        ranked = sorted(agg.items(), key=lambda kv: -kv[1])
        top = ranked[:k]
        return {"top": [(n_, round(v_, 2)) for n_, v_ in top],
                "share": round(sum(v for _, v in top) / tot, 3) if tot else None}
    out["checks"]["E_concentration"] = {
        "total_improvement_units": round(tot, 2),
        "by_symbol": {f"top{k}": topk("symbol", k) for k in (1, 3, 5)},
        "by_sector": {f"top{k}": topk("sector", k) for k in (1, 3, 5)}}

    # ---------- F. DEV / VAL ----------
    dev_m = np.array([t["entry_time"] < pd.Timestamp("2025-01-01").tz_localize(t0.tz)
                      for t in trades])
    fsplit = {}
    for name, m in (("dev", dev_m), ("val", ~dev_m)):
        b, r = Rc[c][m], Rc[c][m & ~is_blocked]
        fsplit[name] = {"n": int(m.sum()),
                        "baseline_exp": round(float(b.mean()), 4),
                        "retained_exp": round(float(r.mean()), 4),
                        "delta": round(float(r.mean() - b.mean()), 4)}
    out["checks"]["F_dev_val"] = fsplit

    # ---------- G. WALK-FORWARD (rolling 12mo obs / 6mo test / roll 6mo) ----------
    tz = t0.tz
    wf, cb_, cr_ = [], [], []
    for s, e in ROLL:
        s = pd.Timestamp(s).tz_localize(tz)
        e = pd.Timestamp(e).tz_localize(tz) + pd.Timedelta(days=1)
        m = np.array([(t["entry_time"] >= s) and (t["entry_time"] < e)
                      for t in trades])
        b, r = Rc[c][m], Rc[c][m & ~is_blocked]
        wf.append({"window": f"{s.date()}→{(e - pd.Timedelta(days=1)).date()}",
                   "n": int(m.sum()),
                   "delta": round(float(r.mean() - b.mean()), 4) if len(r) else None})
        cb_.append(b)
        cr_.append(r)
    cb_, cr_ = np.concatenate(cb_), np.concatenate(cr_)
    out["checks"]["G_walkforward"] = {
        "windows": wf,
        "combined_test_delta": round(float(cr_.mean() - cb_.mean()), 4),
        "combined_n": len(cb_)}

    # ---------- H. BOOTSTRAP (>=5000; use 10000) + DD distribution ----------
    rng = np.random.default_rng(42)
    B = 10000
    base, blk = Rc[c], is_blocked
    d_exp = np.empty(B)
    dd_base, dd_ret = np.empty(B), np.empty(B)
    for i in range(B):
        idx = rng.integers(0, N, N)
        rb, mb = base[idx], blk[idx]
        d_exp[i] = rb[~mb].mean() - rb.mean()
        # DD on time-ordered resample: order resampled trades by entry time
        eo = np.argsort([trades[j]["entry_time"] for j in idx])
        rbo, mbo = rb[eo], mb[eo]
        dd_base[i] = max_dd_of(rbo)
        dd_ret[i] = max_dd_of(rbo[~mbo])
    out["checks"]["H_bootstrap"] = {
        "B": B,
        "exp_median": round(float(np.median(d_exp)), 4),
        "exp_p5": round(float(np.percentile(d_exp, 5)), 4),
        "exp_p95": round(float(np.percentile(d_exp, 95)), 4),
        "P_exp_gt_0": round(float((d_exp > 0).mean()), 4),
        "dd_baseline_median": round(float(np.median(dd_base)), 3),
        "dd_baseline_p95": round(float(np.percentile(dd_base, 95)), 3),
        "dd_retained_median": round(float(np.median(dd_ret)), 3),
        "dd_retained_p95": round(float(np.percentile(dd_ret, 95)), 3),
    }
    print("bootstrap:", json.dumps(out["checks"]["H_bootstrap"], indent=1),
          flush=True)

    # ---------- verdict per Mike's rule ----------
    v = out["checks"]
    vd = {
        "validation_positive": v["F_dev_val"]["val"]["delta"] > 0,
        "all_costs_positive": all(x["delta"] > 0 for x in v["C_cost"].values()),
        "lookbacks_positive": {k: x["delta"] > 0
                               for k, x in v["B_lookback"].items()},
        "loso_survives": not v["D_loso"]["any_destroyed"],
    }
    if (vd["validation_positive"] and vd["all_costs_positive"]
            and all(vd["lookbacks_positive"].values()) and vd["loso_survives"]):
        verdict = "PASS"
    elif (vd["validation_positive"] and vd["all_costs_positive"]
          and vd["loso_survives"]):
        verdict = "MAYBE"
    else:
        verdict = "FAIL"
    out["verdict_inputs"] = vd
    out["verdict"] = verdict

    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"VERDICT: {verdict}", flush=True)
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
