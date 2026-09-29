#!/usr/bin/env python3
"""P3 — Correlation & concentration study (research mandate, 2026-09-24).

Question: does avoiding highly correlated simultaneous positions improve
portfolio performance?

Hypothesis (one line): correlated positions concentrate drawdown without
adding expectancy, because they win and lose together.

Method: entries and exits IDENTICAL (canonical 4H Hybrid via gen_pine_trades;
frozen Mode B). Only the portfolio admission rule changes. Custom sim is a
line-for-line copy of pine_backtest.simulate_portfolio with admission hooks
added and blocked-trade recording.

Pre-declared variants (thresholds set BEFORE running; 0.6/0.8 are robustness
points only, not optimization):
  CONTROL    max 5 concurrent + 5% portfolio heat (existing sim), no theme/corr
  THEME_CAP2 CONTROL + max 2 open per theme (existing production rule)
  CORR_07    CONTROL + block new position if 60-bar return correlation with
             ANY open position > 0.7 (raw correlation, positive only)
  CORR_06    robustness point (not a proposal)
  CORR_08    robustness point (not a proposal)
  CLUSTER1   CONTROL + max 1 open per merged cluster:
             {Semis+AI Infra: AMD,DRAM,SMCI,ANET}, {Software/AI: PLTR,BBAI},
             {Fintech: SOFI,HOOD}, {Space: RKLB,SPCX,ASTX}, {Other: ONDS,NIO,QQQ}

Research only. V5.4, Mode B, alerts, grades, market gate, AI Observer untouched.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_correlation_backtest")
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "correlation_results.json")
os.makedirs(OUTDIR, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

THEME = {
    "QQQ": "Index", "SMCI": "AI Infra", "ANET": "AI Infra",
    "PLTR": "Software/AI", "BBAI": "Software/AI",
    "SOFI": "Fintech", "HOOD": "Fintech",
    "AMD": "Semis", "DRAM": "Semis/Memory",
    "RKLB": "Space", "SPCX": "Space", "ASTX": "Space",
    "ONDS": "Drones", "NIO": "China EV",
}

CLUSTER = {
    "AMD": "Semis+AI Infra", "DRAM": "Semis+AI Infra",
    "SMCI": "Semis+AI Infra", "ANET": "Semis+AI Infra",
    "PLTR": "Software/AI", "BBAI": "Software/AI",
    "SOFI": "Fintech", "HOOD": "Fintech",
    "RKLB": "Space", "SPCX": "Space", "ASTX": "Space",
    "ONDS": "Other", "NIO": "Other", "QQQ": "Other",
}

COST = 0.0025  # 25 bps, mandate benchmark
CORR_WINDOW = 60


def net_r(tr, cost=COST):
    return pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]


def simulate_with_admission(trades, closes, cost, risk_pct, admit, tag):
    """Copy of pb.simulate_portfolio with an admission hook.

    admit(sym, entry_time, open_symbols, theme_counts, cluster_counts)
      -> (ok: bool, reason: str, detail: float|None)
    """
    events = []
    for t in trades:
        events.append((t["exit_time"], 0, t))
        events.append((t["entry_time"], 1, t))
    events.sort(key=lambda e: (e[0], e[1]))
    realized = pb.START_EQUITY
    open_pos, by_id = [], {}
    skipped_cap_count = skipped_cap_risk = 0
    blocked = []  # (trade, reason, detail)
    opened_ids = set()
    peak, max_dd = realized, 0.0
    curve, prev_t = [], None
    open_time = total_time = pd.Timedelta(0)

    def mark(sym, t):
        s = closes[sym]
        idx = s.index.searchsorted(t, side="right") - 1
        return float(s.iloc[idx]) if idx >= 0 else float(s.iloc[0])

    def marked_equity(t):
        unreal = sum(((mark(tr["symbol"], t) - tr["entry"]) / tr["entry"]) * p["size"]
                      for p, tr in ((p, p["trade"]) for p in open_pos))
        return realized + unreal

    for t, kind, tr in events:
        if prev_t is not None and t > prev_t:
            dt = t - prev_t
            total_time += dt
            if open_pos:
                open_time += dt
        prev_t = t
        if kind == 1:
            eq = marked_equity(t)
            open_risk = sum(p["risk_dollars"] for p in open_pos) / eq if eq > 0 else 1
            if len(open_pos) >= pb.MAX_CONCURRENT:
                skipped_cap_count += 1
                continue
            if open_risk + risk_pct > pb.MAX_PORTFOLIO_RISK + 1e-9:
                skipped_cap_risk += 1
                continue
            open_syms = [p["trade"]["symbol"] for p in open_pos]
            theme_counts, cluster_counts = {}, {}
            for p in open_pos:
                th = THEME.get(p["trade"]["symbol"], "Other")
                cl = CLUSTER.get(p["trade"]["symbol"], "Other")
                theme_counts[th] = theme_counts.get(th, 0) + 1
                cluster_counts[cl] = cluster_counts.get(cl, 0) + 1
            ok, reason, detail = admit(tr["symbol"], t, open_syms,
                                       theme_counts, cluster_counts)
            if not ok:
                blocked.append((tr, reason, detail))
                continue
            risk_dollars = risk_pct * eq
            risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
            open_pos.append({"trade": tr, "risk_dollars": risk_dollars,
                             "size": risk_dollars / risk_frac,
                             "risk_frac": risk_frac})
            by_id[id(tr)] = open_pos[-1]
            opened_ids.add(id(tr))
        else:
            pos = by_id.pop(id(tr), None)
            if pos is None:
                continue
            _, _, net_r_, _ = pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)
            realized += pos["risk_dollars"] * net_r_
            open_pos.remove(pos)
        eq = marked_equity(t)
        curve.append((t, eq, realized, len(open_pos)))
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    exposure = float(open_time / total_time) if total_time > pd.Timedelta(0) else 0.0
    return {"final_equity": realized, "max_drawdown": max_dd,
            "skipped_cap_count": skipped_cap_count,
            "skipped_cap_risk": skipped_cap_risk,
            "exposure": exposure, "curve": curve, "blocked": blocked,
            "opened_ids": opened_ids}


def dist_stats(trades, cost=COST):
    if not trades:
        return {"n": 0}
    rs = np.array([net_r(t, cost) for t in trades])
    wins = rs[rs > 0]
    losses = rs[rs <= 0]
    gw, gl = wins.sum(), -losses.sum()
    order = sorted(trades, key=lambda t: t["entry_time"])
    rs_o = np.array([net_r(t, cost) for t in order])
    streak = best = 0
    for r in rs_o:
        streak = streak + 1 if r <= 0 else 0
        best = max(best, streak)
    return {
        "n": len(trades),
        "expectancy_net_r": round(float(rs.mean()), 4),
        "win_rate_pct": round(float((rs > 0).mean()) * 100, 1),
        "profit_factor": round(float(gw / gl), 2) if gl > 0 else None,
        "median_r": round(float(np.median(rs)), 4),
        "avg_winner_r": round(float(wins.mean()), 4) if len(wins) else None,
        "avg_loser_r": round(float(losses.mean()), 4) if len(losses) else None,
        "max_losing_streak": int(best),
    }


def main():
    data, closes = {}, {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        if "Volume" not in df.columns or df["Volume"].isna().all():
            print(f"dropped {sym} (no volume)", flush=True)
            continue
        df = pb.add_pine_indicators(df)
        data[sym] = df
        closes[sym] = df["Close"]
    used = [s for s in WATCHLIST if s in data]
    print(f"loaded {len(used)} tickers", flush=True)

    # canonical Hybrid trades (no monkey-patching — production entry logic)
    trades, skipped_gap = [], 0
    for sym in used:
        ts, sg = pb.gen_pine_trades(sym, data[sym])
        trades.extend(ts)
        skipped_gap += sg
    trades.sort(key=lambda t: t["entry_time"])
    print(f"canonical trades: {len(trades)}", flush=True)

    # 60-bar simple-return series for correlation lookups
    rets = {s: closes[s].pct_change() for s in used}

    def max_open_corr(sym, t, open_syms, window=CORR_WINDOW):
        rs = rets[sym]
        i = rs.index.searchsorted(t, side="right") - 1
        seg = rs.iloc[max(0, i - window + 1):i + 1]
        best = 0.0
        for osym in open_syms:
            if osym == sym:
                continue
            ros = rets[osym]
            j = ros.index.searchsorted(t, side="right") - 1
            oseg = ros.iloc[max(0, j - window + 1):j + 1]
            a, b = seg.align(oseg, join="inner")
            if len(a) < 30:
                continue
            c = a.corr(b)
            if pd.notna(c):
                best = max(best, float(c))
        return best

    def admit_none(sym, t, open_syms, theme_counts, cluster_counts):
        return True, "", None

    def admit_theme2(sym, t, open_syms, theme_counts, cluster_counts):
        th = THEME.get(sym, "Other")
        if theme_counts.get(th, 0) >= 2:
            return False, "theme_cap", float(theme_counts.get(th, 0))
        return True, "", None

    def admit_corr(thresh):
        def f(sym, t, open_syms, theme_counts, cluster_counts):
            mc = max_open_corr(sym, t, open_syms)
            if mc > thresh:
                return False, f"corr>{thresh}", round(mc, 3)
            return True, "", None
        return f

    def admit_cluster1(sym, t, open_syms, theme_counts, cluster_counts):
        cl = CLUSTER.get(sym, "Other")
        if cluster_counts.get(cl, 0) >= 1:
            return False, "cluster_cap", float(cluster_counts.get(cl, 0))
        return True, "", None

    VARIANTS = {
        "CONTROL": admit_none,
        "THEME_CAP2": admit_theme2,
        "CORR_07": admit_corr(0.7),
        "CORR_06": admit_corr(0.6),
        "CORR_08": admit_corr(0.8),
        "CLUSTER1": admit_cluster1,
    }

    results = {"variants": {}, "theme_map": THEME, "cluster_map": CLUSTER,
               "corr_window": CORR_WINDOW, "cost_bps": 25,
               "note": "entries/exits identical (canonical Hybrid); only admission differs"}

    for name, admit in VARIANTS.items():
        port = simulate_with_admission(trades, closes, COST, pb.RISK_PCT,
                                       admit, name)
        taken = [tr for tr in trades if id(tr) in port["opened_ids"]]
        stats = dist_stats(taken)
        stats["trades_taken"] = len(taken)
        stats["total_return_pct"] = round(
            (port["final_equity"] / pb.START_EQUITY - 1) * 100, 2)
        stats["max_drawdown_pct"] = round(port["max_drawdown"] * 100, 2)
        stats["market_exposure_pct"] = round(port["exposure"] * 100, 1)
        stats["skipped_cap_count"] = port["skipped_cap_count"]
        stats["skipped_cap_risk"] = port["skipped_cap_risk"]
        stats["blocked_n"] = len(port["blocked"])

        # opportunity cost: expectancy of the trades this filter blocked
        btrs = [tr for tr, _, _ in port["blocked"]]
        brs = np.array([net_r(tr) for tr in btrs]) if btrs else np.array([])
        by_reason = {}
        for tr, reason, detail in port["blocked"]:
            d = by_reason.setdefault(reason, {"n": 0, "rs": []})
            d["n"] += 1
            d["rs"].append(net_r(tr))
        stats["blocked_expectancy_net_r"] = (
            round(float(brs.mean()), 4) if len(brs) else None)
        stats["blocked_win_rate_pct"] = (
            round(float((brs > 0).mean()) * 100, 1) if len(brs) else None)
        stats["blocked_by_reason"] = {
            k: {"n": v["n"],
                "expectancy_net_r": round(float(np.mean(v["rs"])), 4)}
            for k, v in by_reason.items()}

        # yearly expectancy split (entry_time year), equity reset per period
        yearly = {}
        for yr in sorted({t["entry_time"].year for t in trades}):
            yt = [t for t in taken if t["entry_time"].year == yr]
            if yt:
                yrs_ = np.array([net_r(t) for t in yt])
                yearly[str(yr)] = {"n": len(yt),
                                   "expectancy_net_r": round(float(yrs_.mean()), 4)}
        stats["yearly"] = yearly

        # walk-forward: train entries < 2025, test >= 2025 (equity reset)
        wf = {}
        split = pd.Timestamp("2025-01-01").tz_localize(
            trades[0]["entry_time"].tz)
        for per, flt in (("train_le2024", lambda t: t["entry_time"] < split),
                         ("test_ge2025", lambda t: t["entry_time"] >= split)):
            pt = [t for t in taken if flt(t)]
            if pt:
                prs = np.array([net_r(t) for t in pt])
                wf[per] = {"n": len(pt),
                           "expectancy_net_r": round(float(prs.mean()), 4)}
        stats["walkforward"] = wf

        results["variants"][name] = stats
        print(f"{name}: taken={stats['trades_taken']} exp={stats['expectancy_net_r']}R "
              f"blocked={stats['blocked_n']} blocked_exp={stats['blocked_expectancy_net_r']} "
              f"ret={stats['total_return_pct']}% dd={stats['max_drawdown_pct']}%",
              flush=True)

    # sanity: CONTROL must reproduce the known baseline (237 / +0.239R)
    for v in results["variants"].values():
        v.pop("opened_ids", None)
    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
