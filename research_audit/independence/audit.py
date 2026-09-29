#!/usr/bin/env python3
"""AUDIT: trade independence + profit concentration for the Quality Flow scanner research.

Scope: the 237-trade baseline (canonical 4H Hybrid entries, per-trade net R @25bps
costs, Oct 2023 - Sep 2026, 14-stock watchlist) and the lone-wolf retained set
(154 trades). No new edge proposed or tested. pine_backtest.py is imported
UNMODIFIED; only the SIGN20 flag logic from pine_lonewolf_protocol/
run_mike_validation.py is replicated (deterministically) to rebuild the
retained set. ADX/FVG trade lists are not present in the study JSONs, so no
ADX-selected set can be audited at trade level (see REPORT for detail).

Everything is written to this directory only.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402  (UNMODIFIED import)

CACHE4H = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
CACHED = os.path.join(BASE, "pine_sector_rs_backtest", "cache")
WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
COST = 0.0025  # 25bps, matches the +0.2388R baseline

SECTOR = {"QQQ": "XLK", "SMCI": "SOXX", "PLTR": "XLK", "ANET": "XLK", "SOFI": "XLF",
          "RKLB": "XLI", "ONDS": "XLK", "DRAM": "SOXX", "SPCX": "XLI", "ASTX": "XLK",
          "BBAI": "XLK", "NIO": "XLY", "HOOD": "XLF", "AMD": "SOXX"}
THEME = {"QQQ": "Tech index (QQQ)",
         "SMCI": "AI infra/semis", "AMD": "AI infra/semis",
         "DRAM": "AI infra/semis", "ANET": "AI infra/semis",
         "PLTR": "AI software", "BBAI": "AI software",
         "RKLB": "Space", "ASTX": "Space", "SPCX": "Space",
         "SOFI": "Fintech", "HOOD": "Fintech",
         "ONDS": "Drones/IoT", "NIO": "EV/consumer"}


# ---------------------------------------------------------------- data build
def load_trades():
    trades = []
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE4H, f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        ts, _ = pb.gen_pine_trades(sym, df)
        trades.extend(ts)
    trades.sort(key=lambda t: t["entry_time"])
    return trades


def frame(trades, cost=COST):
    df = pd.DataFrame(trades)
    df["net_r"] = [pb._outcome(t["entry"], t["stop"], t["exit"], cost)[2]
                   for t in trades]
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df["exit_time"] = pd.to_datetime(df["exit_time"])
    df["signal_time"] = pd.to_datetime(df["signal_time"])
    df["theme"] = df["symbol"].map(THEME)
    df["sector"] = df["symbol"].map(SECTOR)
    et = df["entry_time"].dt.tz_convert("America/New_York")
    df["entry_ym"] = et.dt.strftime("%Y-%m")
    df["entry_date"] = et.dt.date
    df["entry_year"] = et.dt.year
    df["entry_bar"] = et.dt.floor("4h")  # same 4H signal/entry bar grouping
    return df


# lone-wolf SIGN20 flag replication (from run_mike_validation.py, verbatim logic)
def retained_mask(trades, h4):
    stock_d = {}
    for sym in WATCHLIST:
        df = h4[sym]
        s = df["Close"].copy()
        s.index = s.index.tz_convert("America/New_York").tz_localize(None)
        stock_d[sym] = s.resample("1D").last().dropna()
    etf_d = {}
    for sym in ["SPY", "XLK", "SOXX", "XLF", "XLI", "XLY"]:
        df = pd.read_pickle(os.path.join(CACHED, f"d_{sym}.pkl"))
        s = df["Close"].copy()
        s.index = pd.to_datetime(s.index.tz_localize(None)
                                if s.index.tz is not None else s.index).normalize()
        etf_d[sym] = s.asfreq("1D").ffill().dropna()

    def ret_n(series, date, n):
        idx = series.index
        pos = idx.searchsorted(date, side="right") - 1
        if pos < n:
            return np.nan
        return series.iloc[pos] / series.iloc[pos - n] - 1.0

    keep = []
    for tr in trades:
        sym = tr["symbol"]
        d = pd.Timestamp(tr["signal_time"]).tz_convert("America/New_York").tz_localize(None).normalize()
        srs = ret_n(stock_d[sym], d, 20) - ret_n(etf_d["SPY"], d, 20)
        secrs = ret_n(etf_d[SECTOR[sym]], d, 20) - ret_n(etf_d["SPY"], d, 20)
        blocked = bool(srs > 0 and secrs <= 0) if not (pd.isna(srs) or pd.isna(secrs)) else False
        keep.append(not blocked)
    return np.array(keep)


# ---------------------------------------------------------------- independence
def overlap_matrix(df):
    n = len(df)
    ent = df["entry_time"].values.astype("datetime64[ns]").astype(np.int64)
    ext = df["exit_time"].values.astype("datetime64[ns]").astype(np.int64)
    ov = (ent[:, None] < ext[None, :]) & (ent[None, :] < ext[:, None])
    np.fill_diagonal(ov, False)
    dur = np.maximum(ext - ent, 1)
    inter = np.maximum(0, np.minimum(ext[:, None], ext[None, :])
                       - np.maximum(ent[:, None], ent[None, :]))
    heavy = (inter >= 0.5 * np.minimum(dur[:, None], dur[None, :])) & ov
    return ov, heavy


def max_concurrent(df):
    ents = sorted(df["entry_time"].values)
    exts = sorted(df["exit_time"].values)
    events = [(t, 1) for t in ents] + [(t, -1) for t in exts]
    events.sort(key=lambda e: (e[0], e[1]))  # exits (-1) before entries (1) at ties
    cur, mx, hist = 0, 0, []
    for _, d in events:
        cur += d
        mx = max(mx, cur)
        hist.append(cur)
    return mx, hist


def corr_by_entry_cohort(df):
    out = {}
    rs = df["net_r"].to_numpy()
    for name, keys in {
        "same_bar_all": df["entry_bar"],
        "same_day_all": df["entry_date"],
    }.items():
        pairs = []
        for _, g in df.groupby(keys).indices.items():
            idx = list(g)
            if len(idx) > 1:
                for a in range(len(idx)):
                    for b in range(a + 1, len(idx)):
                        pairs.append((idx[a], idx[b]))
        if pairs:
            a = rs[[p[0] for p in pairs]]
            b = rs[[p[1] for p in pairs]]
            out[name] = {"n_pairs": len(pairs), "pearson_r": round(float(np.corrcoef(a, b)[0, 1]), 4)}
        else:
            out[name] = {"n_pairs": 0, "pearson_r": None}
    # same-bar, split by same-theme vs different-theme
    same, diff = [], []
    for _, g in df.groupby(df["entry_bar"]).indices.items():
        idx = list(g)
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                (same if df.iloc[idx[a]]["theme"] == df.iloc[idx[b]]["theme"] else diff).append((idx[a], idx[b]))
    for name, pairs in {"same_bar_same_theme": same, "same_bar_diff_theme": diff}.items():
        if pairs:
            a = rs[[p[0] for p in pairs]]
            b = rs[[p[1] for p in pairs]]
            out[name] = {"n_pairs": len(pairs), "pearson_r": round(float(np.corrcoef(a, b)[0, 1]), 4)}
        else:
            out[name] = {"n_pairs": 0, "pearson_r": None}
    # null: shuffle R across same-bar pairs
    rng = np.random.default_rng(42)
    if out["same_bar_all"]["n_pairs"]:
        pairs = []
        for _, g in df.groupby(df["entry_bar"]).indices.items():
            idx = list(g)
            for a in range(len(idx)):
                for b in range(a + 1, len(idx)):
                    pairs.append((idx[a], idx[b]))
        null = []
        for _ in range(2000):
            s = rng.permutation(rs)
            a = s[[p[0] for p in pairs]]
            b = s[[p[1] for p in pairs]]
            null.append(np.corrcoef(a, b)[0, 1])
        obs = out["same_bar_all"]["pearson_r"]
        out["null_same_bar"] = {"mean_r": round(float(np.mean(null)), 4),
                                "sd": round(float(np.std(null)), 4),
                                "p_two_sided": round(float(np.mean(np.abs(null) >= abs(obs))), 4)}
    return out


def effective_n(df, cluster_keys):
    """Design-effect effective n: cluster trades by (date, theme) etc."""
    n = len(df)
    groups = df.groupby(list(cluster_keys))
    sizes = groups.size().to_numpy()
    k = len(sizes)
    if k < 2:
        return {"n_eff": n, "icc": 0.0, "note": "fewer than 2 clusters"}
    y = df["net_r"].to_numpy()
    grand = y.mean()
    ssb = sum(len(g) * (g["net_r"].mean() - grand) ** 2 for _, g in groups)
    ssw = sum(((g["net_r"] - g["net_r"].mean()) ** 2).sum() for _, g in groups)
    msb, msw = ssb / (k - 1), ssw / (n - k)
    m0 = (n - (sizes ** 2).sum() / n) / (k - 1)
    icc = max(0.0, (msb - msw) / (msb + (m0 - 1) * msw)) if (msb + (m0 - 1) * msw) > 0 else 0.0
    deff = 1 + (m0 - 1) * icc
    return {"n_clusters": int(k), "mean_cluster_size": round(float(m0), 2),
            "icc": round(float(icc), 4), "design_effect": round(float(deff), 3),
            "n_eff": round(float(n / deff), 1)}


def collapse_bets(df):
    """Collapse same-entry-bar (then same-date) same-theme entries into single bets."""
    out = {}
    for name, keys in [("same_bar_same_theme", ["entry_bar", "theme"]),
                       ("same_date_same_theme", ["entry_date", "theme"]),
                       ("same_bar_any_theme", ["entry_bar"])]:
        g = df.groupby(keys)
        bet_r = g["net_r"].mean()
        out[name] = {"n_bets": int(len(bet_r)),
                     "bet_expectancy": round(float(bet_r.mean()), 4),
                     "bet_total_r": round(float(bet_r.sum()), 2)}
    return out


def theme_breakdown(df):
    t = df.groupby("theme").agg(n=("net_r", "size"), total_r=("net_r", "sum"),
                                mean_r=("net_r", "mean"))
    t = t.sort_values("total_r", ascending=False)
    t["share_trades_pct"] = (t["n"] / len(df) * 100).round(1)
    t["share_pnl_pct"] = (t["total_r"] / df["net_r"].sum() * 100).round(1)
    return t


# ---------------------------------------------------------------- concentration
def concentration(df, label):
    rs = df["net_r"].to_numpy()
    total = rs.sum()
    n = len(rs)
    res = {"label": label, "n": n, "total_r": round(float(total), 2),
           "expectancy": round(float(rs.mean()), 4)}

    def counterfactual(drop):
        sub = df.drop(df.index[drop])
        r = sub["net_r"].to_numpy()
        return {"n_left": len(r), "expectancy_left": round(float(r.mean()), 4) if len(r) else None,
                "total_r_left": round(float(r.sum()), 2)}

    # top trades
    order = np.argsort(rs)[::-1]
    res["top_trades"] = {}
    for k in (1, 3, 5, 10):
        top = order[:k]
        share = rs[top].sum() / total
        res["top_trades"][f"top_{k}"] = {
            "sum_r": round(float(rs[top].sum()), 2), "share_pnl_pct": round(float(share * 100), 1),
            "trades": [{"symbol": df.iloc[i]["symbol"],
                        "entry": str(df.iloc[i]["entry_time"]),
                        "r": round(float(rs[i]), 2)} for i in top]}
        if k <= 3:
            cf = counterfactual(top)
            res["top_trades"][f"top_{k}"]["expectancy_without"] = cf["expectancy_left"]
    res["top3_red_flag"] = bool(rs[order[:3]].sum() / total > 0.5)

    # HHI of per-trade P&L shares (scale-free concentration)
    shares = rs / total
    res["hhi_pnl"] = (round(float((shares ** 2).sum() * 10000), 1)
                      if total > 0 else None)

    # months / years / symbols / themes / sectors
    def group_stats(key):
        g = df.groupby(key)["net_r"].agg(["sum", "size"]).sort_values("sum", ascending=False)
        return g
    for name, key in [("month", "entry_ym"), ("year", "entry_year")]:
        g = group_stats(key)
        res[f"best_{name}"] = {"label": str(g.index[0]), "sum_r": round(float(g['sum'].iloc[0]), 2),
                               "n": int(g["size"].iloc[0]),
                               "share_pnl_pct": round(float(g['sum'].iloc[0] / total * 100), 1)}
        cf = counterfactual(df[df[key] == g.index[0]].index)
        res[f"best_{name}"]["expectancy_without"] = cf["expectancy_left"]
    g = group_stats("entry_ym")
    res["best_3_months"] = {"labels": [str(x) for x in g.index[:3]],
                            "sum_r": round(float(g['sum'].iloc[:3].sum()), 2),
                            "share_pnl_pct": round(float(g['sum'].iloc[:3].sum() / total * 100), 1)}
    cf = counterfactual(df[df["entry_ym"].isin(g.index[:3])].index)
    res["best_3_months"]["expectancy_without"] = cf["expectancy_left"]

    for name, key in [("symbol", "symbol"), ("theme", "theme"), ("sector", "sector")]:
        g = group_stats(key)
        res[f"by_{name}"] = [
            {"label": str(i), "sum_r": round(float(r['sum']), 2), "n": int(r["size"]),
             "share_pnl_pct": round(float(r['sum'] / total * 100), 1)}
            for i, r in g.iterrows()]
    return res


def main():
    trades = load_trades()
    df = frame(trades)
    assert len(df) == 237, f"baseline drift: {len(df)}"
    exp = round(float(df["net_r"].mean()), 4)
    assert exp == 0.2388, f"expectancy drift: {exp}"
    print(f"baseline verified: n=237, expectancy={exp}, total={df['net_r'].sum():.2f}R")

    h4 = {s: pd.read_pickle(os.path.join(CACHE4H, f"h4_{s}.pkl")) for s in WATCHLIST}
    keep = retained_mask(trades, h4)
    df_r = frame([t for t, k in zip(trades, keep) if k])
    print(f"retained verified: n={len(df_r)}, expectancy={df_r['net_r'].mean():.4f}")

    # ---------------- independence (baseline)
    ov, heavy = overlap_matrix(df)
    ov_counts = ov.sum(axis=1)
    heavy_counts = heavy.sum(axis=1)
    max_conc, _ = max_concurrent(df)
    mx_per_trade = []
    ent = df["entry_time"].values.astype("datetime64[ns]").astype(np.int64)
    ext = df["exit_time"].values.astype("datetime64[ns]").astype(np.int64)
    for i in range(len(df)):
        # open count at this trade's entry + at each event during its life (use same sweep per trade is O(n^2); reuse via counts)
        mx_per_trade.append(int(((ent <= ent[i]) & (ext > ent[i])).sum()))
    independence = {
        "n": len(df),
        "trades_overlapping_any_other": int((ov_counts > 0).sum()),
        "trades_overlapping_any_other_pct": round(float((ov_counts > 0).mean() * 100), 1),
        "mean_overlaps_per_trade": round(float(ov_counts.mean()), 2),
        "overlap_count_distribution": {str(int(k)): int((ov_counts == k).sum())
                                       for k in sorted(np.unique(ov_counts))},
        "trades_heavily_overlapping_any_pct": round(float((heavy_counts > 0).mean() * 100), 1),
        "max_concurrent_open": int(max_conc),
        "concurrent_open_at_entry": {
            "mean": round(float(np.mean(mx_per_trade)), 2),
            "median": float(np.median(mx_per_trade)),
            "p90": float(np.percentile(mx_per_trade, 90)),
            "dist": {str(int(k)): int((np.array(mx_per_trade) == k).sum())
                     for k in sorted(set(mx_per_trade))},
        },
        "same_entry_bar": {"n_bars_with_2plus": int((df.groupby('entry_bar').size() >= 2).sum()),
                           "n_bars_with_3plus": int((df.groupby('entry_bar').size() >= 3).sum())},
        "entry_r_correlation": corr_by_entry_cohort(df),
        "theme_breakdown": theme_breakdown(df).to_dict("index"),
        "effective_n": {
            "cluster_date_theme": effective_n(df, ["entry_date", "theme"]),
            "cluster_month_theme": effective_n(df, ["entry_ym", "theme"]),
            "cluster_date_sector": effective_n(df, ["entry_date", "sector"]),
        },
        "collapsed_bets": collapse_bets(df),
    }

    # ---------------- concentration
    conc_base = concentration(df, "baseline_237")
    conc_ret = concentration(df_r, "lonewolf_retained_154")

    report = {"independence": independence,
              "concentration_baseline": conc_base,
              "concentration_retained": conc_ret}
    with open(os.path.join(OUT, "audit_results.json"), "w") as f:
        json.dump(report, f, indent=1, default=str)
    df[["symbol", "theme", "sector", "entry_time", "exit_time",
        "signal_time", "entry", "stop", "exit", "net_r", "entry_ym"]].to_csv(
        os.path.join(OUT, "baseline_trades.csv"), index=False)
    df_r[["symbol", "theme", "sector", "entry_time", "exit_time",
          "signal_time", "entry", "stop", "exit", "net_r", "entry_ym"]].to_csv(
        os.path.join(OUT, "retained_trades.csv"), index=False)
    print("wrote audit_results.json, baseline_trades.csv, retained_trades.csv")
    return report


if __name__ == "__main__":
    main()
