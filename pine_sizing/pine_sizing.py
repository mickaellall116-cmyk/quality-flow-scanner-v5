"""POSITION SIZING study on Pine V3.6 baseline trades.

RESEARCH ONLY. Compares 5 pre-registered sizing schemes on identical trades.
V3.6 entries/exits byte-identical (trade gen copied from pine_mfe_mae, which
itself copied pine_backtest). Nothing is implemented anywhere.

Spec: SIZING_SPEC.md (frozen before any runs). Local-only.
"""

import glob
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # repo root -> pine_backtest
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "pine_mfe_mae"))
import pine_backtest as pb
from pine_mfe_mae import gen_trades_lifecycle, load_bull, load_2022, CUTOFF_2022

SEED = 20260918
START = pb.START_EQUITY
N_BOOT = 10_000

# ---------------------------------------------------------------- schemes
# Each scheme: {"id", "base", "adaptive": bool}
SCHEMES = [
    {"id": "S0_fixed_1.00", "base": 0.0100, "adaptive": False},
    {"id": "S1_fixed_0.50", "base": 0.0050, "adaptive": False},
    {"id": "S2_fixed_0.75", "base": 0.0075, "adaptive": False},
    {"id": "S3_fixed_1.25", "base": 0.0125, "adaptive": False},
    {"id": "S4_dd_gated",   "base": 0.0100, "adaptive": True},   # halve below -10% DD, restore at -5%
]
DD_HALT = 0.90   # marked equity <= 90% of peak -> risk halves
DD_RESUME = 0.95 # marked equity >= 95% of peak -> risk restores


def simulate_portfolio_risk_hook(trades, closes, cost, scheme):
    """Copy of pb.simulate_portfolio with a per-entry risk hook.

    Fixed schemes: risk_pct constant. S4: cur_risk flips 1.0%<->0.5% on the
    DD gate using marked equity vs running peak (hysteresis). Everything else
    (5-position cap, 5% portfolio-risk gate, costs, marked DD) identical.
    """
    events = []
    for t in trades:
        events.append((t["exit_time"], 0, t))
        events.append((t["entry_time"], 1, t))
    events.sort(key=lambda e: (e[0], e[1]))
    realized = START
    open_pos, by_id = [], {}
    skipped_cap_count = skipped_cap_risk = 0
    peak, max_dd = realized, 0.0
    curve, prev_t = [], None
    open_time = total_time = pd.Timedelta(0)
    cur_risk = scheme["base"]

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
            if scheme["adaptive"]:
                if eq <= DD_HALT * peak:
                    cur_risk = scheme["base"] / 2.0
                elif eq >= DD_RESUME * peak:
                    cur_risk = scheme["base"]
            risk_pct = cur_risk
            open_risk = sum(p["risk_dollars"] for p in open_pos) / eq if eq > 0 else 1
            if len(open_pos) >= pb.MAX_CONCURRENT:
                skipped_cap_count += 1
                continue
            if open_risk + risk_pct > pb.MAX_PORTFOLIO_RISK + 1e-9:
                skipped_cap_risk += 1
                continue
            risk_dollars = risk_pct * eq
            risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
            open_pos.append({"trade": tr, "risk_dollars": risk_dollars,
                             "size": risk_dollars / risk_frac, "risk_frac": risk_frac})
            by_id[id(tr)] = open_pos[-1]
        else:
            pos = by_id.pop(id(tr), None)
            if pos is None:
                continue
            _, _, net_r, _ = pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)
            realized += pos["risk_dollars"] * net_r
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
            "exposure": exposure, "curve": curve,
            "final_peak": peak}


def longest_losing_streak_trades(net_rs):
    best = cur = 0
    for r in net_rs:
        cur = cur + 1 if r <= 0 else 0
        best = max(best, cur)
    return best


def evaluate_scheme(scheme, trades, closes, cost):
    """Event-engine evaluation. Returns portfolio-space metrics dict."""
    port = simulate_portfolio_risk_hook(trades, closes, cost, scheme)
    ret_pct = (port["final_equity"] / START - 1) * 100
    dd_pct = port["max_drawdown"] * 100
    calmar = ret_pct / dd_pct if dd_pct > 0 else float("inf")
    # worst peak-to-trough in % is dd_pct; losing streak in trades from net_r order
    net_rs = []
    for t in trades:
        _, _, net_r, _ = pb._outcome(t["entry"], t["stop"], t["exit"], cost)
        net_rs.append(net_r)
    return {
        "scheme": scheme["id"],
        "terminal_return_pct": round(ret_pct, 2),
        "max_drawdown_pct": round(dd_pct, 2),
        "max_drawdown_R_of_base_risk": round(port["max_drawdown"] / 0.01, 2),
        "calmar": round(calmar, 3) if np.isfinite(calmar) else None,
        "longest_losing_streak_trades": longest_losing_streak_trades(net_rs),
        "skipped_cap_count": port["skipped_cap_count"],
        "skipped_cap_risk": port["skipped_cap_risk"],
        "final_equity": round(port["final_equity"], 2),
        "_net_rs": net_rs,  # kept for bootstrap; stripped before JSON dump
    }


def bootstrap_scheme(scheme, net_rs, n_boot=N_BOOT, seed=SEED):
    """Sequential-compounding bootstrap of R-space trade list at the scheme's
    risk rule. Approximation (ignores concurrency-cap drag) — same accounting
    as the pine_montecarlo study; all schemes compared within this accounting.
    """
    rng = np.random.default_rng(seed)
    arr = np.array(net_rs)
    n = len(arr)
    maxdds, ruined, dd_over20 = [], 0, 0
    for _ in range(n_boot):
        sample = arr[rng.integers(0, n, n)]
        eq, peak = START, START
        cur_risk = scheme["base"]
        worst_dd = 0.0
        for r in sample:
            if scheme["adaptive"]:
                if eq <= DD_HALT * peak:
                    cur_risk = scheme["base"] / 2.0
                elif eq >= DD_RESUME * peak:
                    cur_risk = scheme["base"]
            eq += (cur_risk * eq) * r
            peak = max(peak, eq)
            worst_dd = max(worst_dd, (peak - eq) / peak if peak > 0 else 0)
        maxdds.append(worst_dd)
        if eq <= 0.5 * START:
            ruined += 1
        if worst_dd > 0.20:
            dd_over20 += 1
    maxdds = np.array(maxdds)
    return {
        "n_boot": n_boot,
        "p_ruin_le50pct": round(ruined / n_boot, 4),
        "p_dd_over20pct": round(dd_over20 / n_boot, 4),
        "maxdd_median_pct": round(float(np.median(maxdds)) * 100, 2),
        "maxdd_p75_pct": round(float(np.percentile(maxdds, 75)) * 100, 2),
        "maxdd_p95_pct": round(float(np.percentile(maxdds, 95)) * 100, 2),
    }


def gen_trades(data, cutoff=None, eod_liquidate=False):
    trades = []
    for sym, df in sorted(data.items()):
        tr, _ = gen_trades_lifecycle(sym, df, cutoff=cutoff,
                                    eod_liquidate=eod_liquidate)
        trades.extend(tr)
    trades.sort(key=lambda t: t["entry_time"])
    return trades


def closes_map(data):
    return {sym: df["Close"] for sym, df in data.items()}


def r_space_stats(trades, cost):
    net_rs = []
    for t in trades:
        _, _, net_r, _ = pb._outcome(t["entry"], t["stop"], t["exit"], cost)
        net_rs.append(net_r)
    a = np.array(net_rs)
    wins = a[a > 0]
    losses = a[a <= 0]
    pf = float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() != 0 else None
    return {"n": len(a), "expectancy_R": round(float(a.mean()), 4),
            "total_R": round(float(a.sum()), 2),
            "win_rate": round(float((a > 0).mean()), 4),
            "profit_factor": round(pf, 3) if pf else None}


def main():
    print("== bull window trade generation ==", flush=True)
    data = load_bull()
    closes = closes_map(data)
    trades = gen_trades(data)
    cost = pb.COSTS["4bps"]
    rs = r_space_stats(trades, cost)
    print(f"FIDELITY: n={rs['n']} exp={rs['expectancy_R']}R (baseline: 263, +0.195R)", flush=True)
    assert rs["n"] == 263, f"trade count mismatch: {rs['n']}"
    assert abs(rs["expectancy_R"] - 0.195) < 0.005, f"expectancy mismatch: {rs['expectancy_R']}"

    results = {"label": "bull_2024-2026_UX51_4h", "cost": "4bps",
               "r_space": rs, "schemes": {}}
    for scheme in SCHEMES:
        ev = evaluate_scheme(scheme, trades, closes, cost)
        net_rs = ev.pop("_net_rs")
        bs = bootstrap_scheme(scheme, net_rs)
        ev["bootstrap"] = bs
        results["schemes"][scheme["id"]] = ev
        print(f"  {scheme['id']}: ret={ev['terminal_return_pct']}% "
              f"dd={ev['max_drawdown_pct']}% calmar={ev['calmar']} "
              f"ruin={bs['p_ruin_le50pct']} pDD20={bs['p_dd_over20pct']}", flush=True)

    with open(os.path.join(HERE, "sizing_results_bull.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print("wrote sizing_results_bull.json", flush=True)
    print("DONE_BULL — freeze candidates in CANDIDATES_FROZEN.md, then run --validate2022", flush=True)


def validate_2022(scheme_ids):
    print("== 2022 validation ==", flush=True)
    data22, syms = load_2022()
    print(f"  {len(syms)} symbols", flush=True)
    closes = closes_map(data22)
    trades22 = gen_trades(data22, cutoff=CUTOFF_2022, eod_liquidate=True)
    print(f"  2022 trades: {len(trades22)}", flush=True)
    out = {"label": "bear_2022_4h", "n": len(trades22), "schemes": {}}
    for cid in scheme_ids:
        scheme = next(s for s in SCHEMES if s["id"] == cid)
        for leg in ("4bps", "25bps"):
            cost = pb.COSTS[leg]
            ev = evaluate_scheme(scheme, trades22, closes, cost)
            net_rs = ev.pop("_net_rs")
            ev["bootstrap"] = bootstrap_scheme(scheme, net_rs, seed=SEED + 1)
            ev["r_space"] = r_space_stats(trades22, cost)
            out["schemes"].setdefault(cid, {})[leg] = ev
            print(f"  {cid} [{leg}]: ret={ev['terminal_return_pct']}% "
                  f"dd={ev['max_drawdown_pct']}% calmar={ev['calmar']}", flush=True)
    with open(os.path.join(HERE, "sizing_results_2022.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    print("wrote sizing_results_2022.json", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--validate2022":
        with open(os.path.join(HERE, "CANDIDATES_FROZEN.md")) as f:
            txt = f.read()
        ids = []
        for l in txt.splitlines():
            s = l.strip()
            if "CANDIDATE:" in s:
                ids.append(s.split("CANDIDATE:")[1].strip().split()[0])
        assert ids, "no CANDIDATE lines found in CANDIDATES_FROZEN.md"
        validate_2022(ids)
    else:
        main()
