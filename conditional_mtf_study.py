"""Multi-timeframe conditional study (Mike's proposal).

Every 4H signal behind the V5.4-core trades (structural + ADX >= 20,
protect-1R exit) is tagged with the conditions that existed at the signal
bar -- daily/weekly trend confirmation, market gate/regime, RVOL, R:R --
by joining trades back to the cached per-bar signal rows. Then expectancy
is compared across buckets.

No live rules modified. Local-only research.
"""

import json
import os

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "backtest_cache", "v3")

CORE = {"config": "S_plus_adx", "exit_mode": "protect1R",
        "cost": "4bps", "risk_pct": 0.01}


def load_signal_map(tag, symbols):
    """signal_id -> signal row dict for one universe tag."""
    smap = {}
    for sym in symbols:
        p = os.path.join(CACHE, f"signals_{tag}_{sym}.pkl")
        if not os.path.exists(p):
            continue
        signals, _, _ = pd.read_pickle(p)
        for r in signals:
            if r:
                smap[r["signal_id"]] = r
    return smap


def bucket_rr(row):
    try:
        rr = (float(row["tp1"]) - float(row["price"])) / (
            float(row["price"]) - float(row["stop"]))
    except (ZeroDivisionError, TypeError, ValueError):
        return "n/a"
    if rr < 2:
        return "rr<2"
    if rr < 3:
        return "rr 2-3"
    return "rr 3+"


def bucket_rvol(rv):
    try:
        rv = float(rv)
    except (TypeError, ValueError):
        return "n/a"
    if rv < 0.8:
        return "rvol<0.8"
    if rv < 1.0:
        return "rvol 0.8-1.0"
    if rv < 1.5:
        return "rvol 1.0-1.5"
    return "rvol 1.5+"


def stats(df):
    n = len(df)
    if n == 0:
        return {"n": 0}
    wins = df[df["net_r"] > 0]
    gw = wins["net_r"].sum()
    gl = -df[df["net_r"] <= 0]["net_r"].sum()
    return {
        "n": n,
        "win_pct": round(len(wins) / n * 100, 1),
        "mean_net_r": round(float(df["net_r"].mean()), 3),
        "total_net_r": round(float(df["net_r"].sum()), 1),
        "pf": round(gw / gl, 2) if gl > 0 else None,
    }


def main():
    trades = pd.read_csv(os.path.join(BASE, "backtest_trades.csv"))
    core = trades[(trades["config"] == CORE["config"])
                  & (trades["exit_mode"] == CORE["exit_mode"])
                  & (trades["cost"] == CORE["cost"])
                  & (trades["risk_pct"] == CORE["risk_pct"])].copy()
    print(f"core trades: {len(core)}", flush=True)

    out = {}
    for tag in ["U15", "UX"]:
        sub = core[core["universe"] == tag].copy()
        if sub.empty:
            continue
        smap = load_signal_map(tag, sub["symbol"].unique())
        tags = []
        missing = 0
        for _, t in sub.iterrows():
            r = smap.get(t["signal_id"])
            if r is None:
                missing += 1
                continue
            d, w = bool(r["daily_trend_confirmed"]), bool(r["weekly_trend_confirmed"])
            tags.append({
                "idx": t.name,
                "d_ok": "Y" if d else "N",
                "w_ok": "Y" if w else "N",
                "mtf": ("both" if d and w else "daily-only" if d else
                        "weekly-only" if w else "neither"),
                "gate": r.get("market_gate"),
                "regime_tag": r.get("regime_label"),
                "rvol": bucket_rvol(r.get("rel_vol")),
                "rr": bucket_rr(r),
                "adx": float(r["adx"]) if r.get("adx") is not None else None,
            })
        print(f"[{tag}] tagged={len(tags)} missing={missing}", flush=True)
        tg = pd.DataFrame(tags).set_index("idx")
        sub = sub.join(tg)

        panels = {}
        panels["daily"] = {k: stats(g) for k, g in sub.groupby("d_ok")}
        panels["weekly"] = {k: stats(g) for k, g in sub.groupby("w_ok")}
        panels["mtf"] = {k: stats(g) for k, g in sub.groupby("mtf")}
        panels["market_gate"] = {k: stats(g) for k, g in sub.groupby("gate")}
        panels["regime"] = {k: stats(g) for k, g in sub.groupby("regime_tag")}
        panels["rvol"] = {k: stats(g) for k, g in sub.groupby("rvol")}
        panels["rr"] = {k: stats(g) for k, g in sub.groupby("rr")}
        # key interactions
        both = sub[sub["mtf"] == "both"]
        not_both = sub[sub["mtf"] != "both"]
        panels["interaction_mtf"] = {"mtf_both": stats(both),
                                     "mtf_not_both": stats(not_both)}
        block = sub[sub["gate"] == "BLOCK"]
        panels["block_only"] = {"BLOCK": stats(block),
                                "not_BLOCK": stats(sub[sub["gate"] != "BLOCK"])}
        out[tag] = {"n_trades": len(sub), "panels": panels}

        print(f"\n===== {tag} (V5.4 core: structural+ADX, protect-1R) =====")
        for pname, panel in panels.items():
            print(f"--- {pname} ---")
            for k, s in panel.items():
                if s["n"] == 0:
                    continue
                print(f"  {k}: n={s['n']} win={s['win_pct']}% "
                      f"mean={s['mean_net_r']}R total={s['total_net_r']}R pf={s['pf']}")

    with open(os.path.join(BASE, "conditional_mtf_study.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("\nwrote conditional_mtf_study.json")


if __name__ == "__main__":
    main()
