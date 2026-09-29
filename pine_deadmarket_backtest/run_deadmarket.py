"""P5 follow-up (pre-registered): NO-DEAD-MARKET filter.

HYPOTHESIS (pre-registered from P5): skipping new entries when the market is in
a bottom-tercile realized-volatility regime improves expectancy, because
breakouts need movement and dead markets starve them.

P5 EVIDENCE: per-symbol 20-bar realized-vol percentile (trailing 500 4H bars)
low tercile (<33): -0.034R overall, -1.15R in 2026 (n=39). High tercile:
+0.402R (n=107), best bucket every year.

DEFINITION (exact P5 definition, no re-tuning):
  rv         = std of 20-bar log returns (per symbol, 4H bars)
  rv_pctile  = percentile rank of rv within trailing 500 bars (min_periods 250)
  SKIP entry if rv_pctile < 33 at the signal bar.

NOTE: the task text said "SPY ... trailing 1 year" but P5's actual
pre-registered definition is per-symbol trailing-500-bars. This study follows
P5's definition exactly (the evidence it is confirming).

Method: canonical 4H Hybrid trades via pb.gen_pine_trades (production entry
logic, unmodified). Portfolio sim is a copy of pb.simulate_portfolio with an
admission hook (same pattern as pine_correlation_backtest). CONTROL reproduces
the known baseline; only the admission rule differs.

Research only. V5.4, Mode B, alerts, grades, market gate, AI Observer untouched.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_deadmarket_backtest")
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "deadmarket_results.json")
COST = 0.0025  # 25 bps
TRAIL = 500    # exact P5 definition
RV_SKIP = 33.0  # bottom tercile — pre-declared, not tuned

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]


def add_rv(df):
    out = df.copy()
    logret = np.log(out["Close"] / out["Close"].shift(1))
    out["rv"] = logret.rolling(20).std()
    out["rv_pctile"] = out["rv"].rolling(TRAIL, min_periods=250).rank(pct=True) * 100
    return out


def simulate_with_admission(trades, closes, cost, risk_pct, admit):
    """Copy of pb.simulate_portfolio with an admission hook.
    admit(tr) -> (ok, reason, detail). Records blocked trades."""
    events = []
    for t in trades:
        events.append((t["exit_time"], 0, t))
        events.append((t["entry_time"], 1, t))
    events.sort(key=lambda e: (e[0], e[1]))
    realized = pb.START_EQUITY
    open_pos, by_id = [], {}
    skipped_cap_count = skipped_cap_risk = 0
    blocked = []
    opened_ids = set()
    peak, max_dd = realized, 0.0
    curve, prev_t = [], None

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
            ok, reason, detail = admit(tr)
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
        curve.append((t, float(eq), float(realized), len(open_pos)))
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    return {"final_equity": realized, "max_drawdown": max_dd,
            "skipped_cap_count": skipped_cap_count,
            "skipped_cap_risk": skipped_cap_risk,
            "blocked": blocked, "opened_ids": opened_ids, "curve": curve}


def net_r(t, cost=COST):
    return pb._outcome(t["entry"], t["stop"], t["exit"], cost)[2]


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
        df = add_rv(df)
        data[sym] = df
        closes[sym] = df["Close"]
    used = [s for s in WATCHLIST if s in data]
    print(f"loaded {len(used)} tickers", flush=True)

    # canonical trades
    trades, skipped_gap = [], 0
    for sym in used:
        ts, sg = pb.gen_pine_trades(sym, data[sym])
        trades.extend(ts)
        skipped_gap += sg
    trades.sort(key=lambda t: t["entry_time"])
    print(f"canonical trades: {len(trades)} (skipped_gap={skipped_gap})", flush=True)

    # tag rv_pctile at the SIGNAL bar (decision point), exact P5 convention
    for tr in trades:
        df = data[tr["symbol"]]
        st = pd.Timestamp(tr["signal_time"])
        i = df.index.searchsorted(st, side="right") - 1
        tr["rv_pctile"] = float(df["rv_pctile"].iloc[i]) if i >= 0 else float("nan")
        tr["dead_market"] = bool(tr["rv_pctile"] < RV_SKIP)
    n_dead = sum(t["dead_market"] for t in trades)
    print(f"dead-market (rv_pctile<33) signals: {n_dead}/{len(trades)}", flush=True)

    def admit_all(tr):
        return True, "", None

    def admit_no_dead(tr):
        if tr["dead_market"]:
            return False, "dead_market", round(tr["rv_pctile"], 1)
        return True, "", None

    res = {}
    for tag, admit in [("CONTROL", admit_all), ("NO_DEAD_MARKET", admit_no_dead)]:
        port = simulate_with_admission(trades, closes, COST, pb.RISK_PCT, admit)
        taken = [t for t in trades if id(t) in port["opened_ids"]]
        blocked = [b[0] for b in port["blocked"]]
        stats = dist_stats(taken)
        stats.update({
            "total_return_pct": round((port["final_equity"] / pb.START_EQUITY - 1) * 100, 2),
            "max_drawdown_pct": round(port["max_drawdown"] * 100, 2),
            "skipped_cap": port["skipped_cap_count"],
            "skipped_risk": port["skipped_cap_risk"],
            "blocked_n": len(blocked),
        })
        res[tag] = {"taken": stats, "blocked": dist_stats(blocked)}
        # year cross-tab on taken trades
        yrs = {}
        for t in taken:
            y = str(pd.Timestamp(t["entry_time"]).year)
            yrs.setdefault(y, []).append(t)
        res[tag]["by_year"] = {y: dist_stats(v) for y, v in sorted(yrs.items())}
        # walk-forward split (pre-declared: test = entries >= 2025)
        cutoff = pd.Timestamp("2025-01-01", tz=pd.Timestamp(taken[0]["entry_time"]).tz)
        wf = {"train": [t for t in taken if pd.Timestamp(t["entry_time"]) < cutoff],
              "test": [t for t in taken if pd.Timestamp(t["entry_time"]) >= cutoff]}
        res[tag]["walk_forward"] = {k: dist_stats(v) for k, v in wf.items()}

    # skipped-trade detail: expectancy of everything the filter blocked
    nd = res["NO_DEAD_MARKET"]["blocked"]
    c, f = res["CONTROL"]["taken"], res["NO_DEAD_MARKET"]["taken"]
    print(f"CONTROL taken={c['n']} exp={c['expectancy_net_r']}R DD={c['max_drawdown_pct']}% ret={c['total_return_pct']}%")
    print(f"FILTER  taken={f['n']} exp={f['expectancy_net_r']}R DD={f['max_drawdown_pct']}% ret={f['total_return_pct']}% blocked={nd['n']} exp={nd['expectancy_net_r']}R")

    json.dump(res, open(OUT, "w"), indent=1, default=str)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
