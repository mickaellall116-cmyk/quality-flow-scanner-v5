#!/usr/bin/env python3
"""Portfolio-realism audit: INDEPENDENT realistic replay of the 4H Hybrid
baseline trade list (237 trades, +0.2388R @25bps, Oct 2023-Sep 2026).

Audit only. Imports pine_backtest.py UNMODIFIED for trade generation (the
baseline trade list); the portfolio engine below is written from scratch and
is deliberately NOT a copy of simulate_portfolio. Research only -- nothing
frozen touched.

What the replay enforces (production rules, documented in MEMORY.md):
  * Fixed capital base: $75k trading book (Mike's number).
  * 1%-risk sizing with WHOLE shares: shares = floor(risk_budget / (entry-stop)).
    If shares < 1 (stop too wide for the risk budget), the trade is SKIPPED --
    a real affordability constraint the research sims never model.
  * Max 6 open positions (production rule; research used 5).
  * Max ~5% of book at risk (heat cap, production rule).
  * Costs 25bps on notional, entry AND exit legs (round-trip), not the
    research convention of one 25bps charge on blended return.
  * At each timestamp: exits fill first (next-bar-open fills free the slot),
    then entries compete in a documented ordering.
  * Skipped signals are gone forever (no re-entry, same as research).

Sensitivity / diagnostic variants:
  * ordering: how simultaneous entries compete for slots --
    primary = (entry_time, symbol alphabetical); alternates = watchlist order
    (the research artifact), reverse-alpha, 5 random shuffles.
  * theme cap: diagnostic variant enforcing max 2 per theme (production rule).
  * cash cap: diagnostic variant capping notional at equity (no margin).
  * fixed base: sizing always $750 risk / $3,750 heat vs compounding equity.

Outputs: research_audit/portfolio/replay_results.json
"""

import json
import os
import random
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "research_audit", "portfolio")
OUT = os.path.join(OUTDIR, "replay_results.json")
os.makedirs(OUTDIR, exist_ok=True)

sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402  (imported UNMODIFIED -- audit only)

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")

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

BOOK = 75_000.0
RISK_PCT = 0.01
MAX_POS = 6
HEAT_CAP = 0.05
COST = 0.0025  # 25bps per leg, on notional


# ------------------------------------------------------- baseline trade list
def load_baseline_trades():
    """Regenerate the canonical baseline trade list via pb (unmodified)."""
    data, closes = {}, {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        data[sym] = df
        closes[sym] = df["Close"]
    all_trades = []
    skipped_gap = 0
    for sym in WATCHLIST:
        tr, sg = pb.gen_pine_trades(sym, data[sym])
        all_trades.extend(tr)
        skipped_gap += sg
    all_trades.sort(key=lambda t: t["entry_time"])  # stable: ties keep WATCHLIST order
    return all_trades, closes, skipped_gap


def net_r_research(tr, cost=COST):
    """Research convention: single cost charge on blended return."""
    return pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]


# ------------------------------------------------------------ replay engine
def replay(trades, closes, ordering="alpha", theme_cap=None, cash_cap=False,
           fixed_base=False):
    """Independent event-driven portfolio replay with realistic constraints.

    ordering: 'alpha' (entry_time, symbol A-Z) | 'watchlist' | 'reverse' |
              ('random', seed)
    theme_cap: None or int (diagnostic max open per theme)
    cash_cap: cap shares so notional <= equity at entry (no margin)
    fixed_base: risk budget always 1% of BOOK, heat always vs BOOK
    """
    entries_by_t, exits_by_t = {}, {}
    for idx, t in enumerate(trades):
        entries_by_t.setdefault(t["entry_time"], []).append(idx)
        exits_by_t.setdefault(t["exit_time"], []).append(idx)

    def order_entries(idxs):
        if ordering == "alpha":
            return sorted(idxs, key=lambda i: (trades[i]["symbol"],))
        if ordering == "watchlist":
            return sorted(idxs, key=lambda i: WATCHLIST.index(trades[i]["symbol"]))
        if ordering == "reverse":
            return sorted(idxs, key=lambda i: (trades[i]["symbol"],), reverse=True)
        if isinstance(ordering, tuple) and ordering[0] == "random":
            rng = random.Random(ordering[1])
            out = list(idxs)
            rng.shuffle(out)
            return out
        raise ValueError(ordering)

    times = sorted(set(entries_by_t) | set(exits_by_t))
    ordered = []
    for t in times:
        for idx in sorted(exits_by_t.get(t, [])):
            ordered.append((t, 0, idx))
        for idx in order_entries(entries_by_t.get(t, [])):
            ordered.append((t, 1, idx))

    realized = BOOK
    open_pos, by_id = [], {}
    taken = []          # idx of trades actually taken
    skip = {"slots": 0, "heat": 0, "afford": 0, "theme": 0, "cash": 0}
    contested, genuine = 0, 0
    theme_max_seen = {}
    peak, max_dd = realized, 0.0

    def mark(sym, t):
        s = closes[sym]
        ii = s.index.searchsorted(t, side="right") - 1
        return float(s.iloc[ii]) if ii >= 0 else float(s.iloc[0])

    def marked_equity(t):
        unreal = sum((mark(p["symbol"], t) - p["entry"]) * p["shares"]
                     for p in open_pos)
        return realized + unreal

    for t, kind, idx in ordered:
        tr = trades[idx]
        if kind == 1:  # entry
            free = MAX_POS - len(open_pos)
            n_cands = len(entries_by_t[t])
            if n_cands > free:
                contested += 1
                if free > 0:
                    genuine += 1  # at least one slot to allocate among competitors
            if free <= 0:
                skip["slots"] += 1
                continue
            eq = marked_equity(t)
            base = BOOK if fixed_base else eq
            risk_budget = RISK_PCT * base
            risk_per_share = tr["entry"] - tr["stop"]
            shares = int(risk_budget // risk_per_share)
            if shares < 1:
                skip["afford"] += 1
                continue
            if cash_cap:
                max_shares = int(eq // tr["entry"])
                if max_shares < 1:
                    skip["cash"] += 1
                    continue
                if shares > max_shares:
                    shares = max_shares
            heat_now = sum(p["shares"] * (p["entry"] - p["stop"]) for p in open_pos)
            heat_base = BOOK if fixed_base else eq
            if (heat_now + shares * risk_per_share) / heat_base > HEAT_CAP + 1e-9:
                skip["heat"] += 1
                continue
            if theme_cap is not None:
                th = THEME[tr["symbol"]]
                if sum(1 for p in open_pos if THEME[p["symbol"]] == th) >= theme_cap:
                    skip["theme"] += 1
                    continue
            pos = {"idx": idx, "symbol": tr["symbol"], "entry": tr["entry"],
                   "stop": tr["stop"], "exit": tr["exit"], "shares": shares,
                   "risk": shares * risk_per_share,
                   "entry_cost": COST * shares * tr["entry"]}
            open_pos.append(pos)
            by_id[idx] = pos
            taken.append(idx)
            th = THEME[tr["symbol"]]
            theme_max_seen[th] = max(theme_max_seen.get(th, 0),
                                    sum(1 for p in open_pos if THEME[p["symbol"]] == th))
        else:  # exit
            pos = by_id.pop(idx, None)
            if pos is None:
                continue  # trade was never taken
            exit_cost = COST * pos["shares"] * pos["exit"]
            pnl = pos["shares"] * (pos["exit"] - pos["entry"]) \
                - pos["entry_cost"] - exit_cost
            realized += pnl
            open_pos.remove(pos)
        eq = marked_equity(t)
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)

    # portfolio-level stats on TAKEN trades
    rs = []
    for idx in taken:
        tr = trades[idx]
        # per-trade net R in the replay's cost convention (round-trip costs):
        # gross R minus entry-leg and exit-leg costs expressed in R units
        r_gross = (tr["exit"] - tr["entry"]) / (tr["entry"] - tr["stop"])
        cost_r = COST * (tr["entry"] + tr["exit"]) / (tr["entry"] - tr["stop"])
        rs.append(r_gross - cost_r)
    rs = np.array(rs)
    wins = rs[rs > 0]
    losses = rs[rs <= 0]
    gw, gl = wins.sum(), -losses.sum()
    return {
        "n_trades": len(trades),
        "n_taken": len(taken),
        "taken_pct": round(len(taken) / len(trades) * 100, 1),
        "expectancy_net_r": round(float(rs.mean()), 4) if len(rs) else None,
        "win_rate_pct": round(float((rs > 0).mean()) * 100, 1) if len(rs) else None,
        "profit_factor": round(float(gw / gl), 2) if gl > 0 else None,
        "total_r": round(float(rs.sum()), 2),
        "final_equity": round(realized, 2),
        "total_return_pct": round((realized / BOOK - 1) * 100, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "skipped": skip,
        "contested_timestamps": contested,
        "genuine_choice_timestamps": genuine,
        "theme_max_concurrency": theme_max_seen,
        "taken_idx": taken,
    }


def independent_trade_stats(trades):
    """No-portfolio benchmark: every trade taken, fixed 1R risk, costs 25bps."""
    rs = np.array([net_r_research(t) for t in trades])
    cum = np.cumsum(rs)
    peak = np.maximum.accumulate(cum)
    dd = (peak - cum).max()
    return {
        "n": len(rs), "expectancy_net_r": round(float(rs.mean()), 4),
        "max_drawdown_r": round(float(dd), 2),
        "total_r": round(float(rs.sum()), 2),
    }


def jaccard(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if sa | sb else 1.0


def main():
    trades, closes, skipped_gap = load_baseline_trades()
    base = independent_trade_stats(trades)
    print(f"baseline check: n={base['n']} exp={base['expectancy_net_r']}R "
          f"dd={base['max_drawdown_r']}R total={base['total_r']}R "
          f"(skipped_gap={skipped_gap})", flush=True)
    assert base["n"] == 237, "baseline trade count drifted"
    assert abs(base["expectancy_net_r"] - 0.2388) < 1e-3, "baseline expectancy drifted"

    results = {
        "config": {"book": BOOK, "risk_pct": RISK_PCT, "max_pos": MAX_POS,
                   "heat_cap": HEAT_CAP, "cost_per_leg": COST,
                   "universe": WATCHLIST, "period": "Oct2023-Sep2026 4H"},
        "independent_no_portfolio": base,
    }

    # primary: documented ordering (timestamp, symbol alphabetical)
    prim = replay(trades, closes, ordering="alpha")
    results["primary_alpha"] = {k: v for k, v in prim.items() if k != "taken_idx"}

    # ordering sensitivity
    sens = {}
    for name in ["watchlist", "reverse"]:
        r = replay(trades, closes, ordering=name)
        sens[name] = {k: v for k, v in r.items() if k != "taken_idx"}
        sens[name]["jaccard_vs_alpha"] = round(jaccard(prim["taken_idx"], r["taken_idx"]), 4)
    rand_exp, rand_j = [], []
    for s in range(5):
        r = replay(trades, closes, ordering=("random", s))
        rand_exp.append(r["expectancy_net_r"])
        rand_j.append(jaccard(prim["taken_idx"], r["taken_idx"]))
    sens["random5"] = {"expectancy_range": [round(min(rand_exp), 4), round(max(rand_exp), 4)],
                      "jaccard_vs_alpha_range": [round(min(rand_j), 4), round(max(rand_j), 4)]}
    results["ordering_sensitivity"] = sens

    # diagnostic variants
    for name, kw in [("theme_cap_2", {"theme_cap": 2}),
                     ("cash_cap", {"cash_cap": True}),
                     ("fixed_base", {"fixed_base": True}),
                     ("theme2_cash", {"theme_cap": 2, "cash_cap": True})]:
        r = replay(trades, closes, ordering="alpha", **kw)
        results[name] = {k: v for k, v in r.items() if k != "taken_idx"}

    # contested-candidate quality: at timestamps where slots bound, what was the
    # mean net R of candidates that got in vs were skipped (alpha ordering)?
    prim_full = replay(trades, closes, ordering="alpha")
    taken_set = set(prim_full["taken_idx"])
    in_r = [net_r_research(trades[i]) for i in prim_full["taken_idx"]]
    out_r = [net_r_research(t) for j, t in enumerate(trades) if j not in taken_set]
    results["taken_vs_skipped_quality"] = {
        "taken_mean_r": round(float(np.mean(in_r)), 4),
        "skipped_mean_r": round(float(np.mean(out_r)), 4) if out_r else None,
        "n_skipped": len(out_r),
    }

    with open(OUT, "w") as f:
        json.dump(results, f, indent=1)
    print(f"wrote {OUT}")
    for k, v in results.items():
        if isinstance(v, dict) and "n_taken" in v:
            print(f"{k}: n_taken={v['n_taken']} exp={v['expectancy_net_r']}R "
                  f"ret={v['total_return_pct']}% dd={v['max_drawdown_pct']}% "
                  f"skipped={v['skipped']}")


if __name__ == "__main__":
    main()
