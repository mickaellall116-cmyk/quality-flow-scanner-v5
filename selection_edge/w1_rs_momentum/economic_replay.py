"""W1 economic check: portfolio replay with a per-signal selection filter.

Faithful copy of canonical_baseline/run_portfolio.build_v5 (same $75k book,
1% risk, max 6 open, 5% heat cap, rs_top2 slot competition, busy rule, 50bps
walk costs) PLUS:
  - sig_filter(signal_dict) -> bool hook applied right after signal generation
  - marked-equity curve capture for max-DD / total-return deltas

Validation: with sig_filter=None on the full 131-name universe, the accepted
signal_id set must EXACTLY match canonical_baseline/canonical_trades.json.
Only then are the 123-name working-set runs (none / F1 / F2) trusted.

Engine + helpers imported, never rebuilt: simlib, run_ablation (exec_modeb,
net_r_legs, summarize, START_EQUITY, RISK_USD, MAX_OPEN, HEAT_CAP),
modeb_engine.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
BASE = os.path.join(REPO, "canonical_baseline")
OUT = os.path.join(REPO, "selection_edge", "w1_rs_momentum")
sys.path.insert(0, BASE)
sys.path.insert(0, REPO)

import simlib
from run_ablation import (exec_modeb, net_r_legs, summarize, build_symbol_table,
                          START_EQUITY, MAX_OPEN, HEAT_CAP)

COST_LEVELS = [0.0025, 0.005, 0.0075, 0.01]


def build_v5_filtered(symbols, factor_map, sig_filter, tag="V5f"):
    """factor_map: signal_id -> dict of factor values (for the filter)."""
    tab = build_symbol_table(symbols)
    all_sigs = []
    sym_dfs = {}
    sym_xs = {}
    for sym in symbols:
        ws, we = tab[sym]
        sigs, df = simlib.v54_signals(sym, ws, we)
        all_sigs.extend(sigs)
        sym_dfs[sym] = df
        sym_xs[sym] = simlib.exit_states_vector(sym)
    if sig_filter is not None:
        kept = [s for s in all_sigs if sig_filter(s, factor_map.get(s["signal_id"]))]
        print(f"[{tag}] filter: {len(all_sigs)} -> {len(kept)} signals", flush=True)
        all_sigs = kept
    print(f"[{tag}] total v54 candidate signals: {len(all_sigs)}", flush=True)

    by_sym = {}
    for s in all_sigs:
        by_sym.setdefault(s["symbol"], []).append(s)
    rs_scores = simlib.rs_top2_scores(by_sym)

    all_sigs.sort(key=lambda s: (s["signal_bar_close_at"], s["symbol"]))
    batches = []
    prev_key = None
    for s in all_sigs:
        k = s["signal_bar_close_at"]
        if k != prev_key:
            batches.append((k, []))
            prev_key = k
        batches[-1][1].append(s)

    busy_through = {}
    accepted = []
    counts = {"busy": 0, "slot": 0, "heat": 0, "candidates": len(all_sigs)}
    open_book = []
    realized = START_EQUITY
    equity_curve = []  # (ts, marked_equity)

    def current_risk(tr, t_next):
        r = tr["risk_usd"]
        if tr["tp1_taken"] and tr["tp1_fill_ts"] is not None and t_next > tr["tp1_fill_ts"]:
            r = r / 2.0
        return r

    def marked_equity(t_c):
        nonlocal realized
        still_open = []
        for tr in open_book:
            if tr["tp1_taken"] and not tr.get("tp1_cost_done") and tr["tp1_fill_ts"] <= t_c:
                realized -= tr["tp1_cost"]
                tr["tp1_cost_done"] = True
            if tr["exit_ts"] <= t_c:
                realized += tr["gross_usd"] - tr["exit_cost"]
            else:
                still_open.append(tr)
        open_book[:] = still_open
        unreal = 0.0
        for tr in open_book:
            df = sym_dfs[tr["symbol"]]
            j = df.index.searchsorted(pd.Timestamp(t_c), side="right") - 1
            if j < 0:
                continue
            mark = float(df["Close"].iloc[j])
            sh = tr["shares"] / 2.0 if (tr["tp1_taken"] and tr["tp1_fill_ts"] <= t_c) else tr["shares"]
            unreal += (mark - tr["entry"]) * sh
        return realized + unreal

    for close_at, batch in batches:
        t_next = batch[0]["entry_bar_ts"]
        qualified = []
        for s in sorted(batch, key=lambda x: x["symbol"]):
            bt = busy_through.get(s["symbol"])
            if bt is not None and s["signal_bar_close_at"] <= bt:
                counts["busy"] += 1
            else:
                qualified.append(s)
        if not qualified:
            continue
        ranked = sorted(qualified,
                        key=lambda s: (-rs_scores[s["signal_id"]],
                                       s["signal_bar_close_at"], s["symbol"]))
        used = sum(1 for tr in open_book
                   if tr["entry_ts"] <= t_next <= tr["exit_ts"])
        free = MAX_OPEN - used
        eq = marked_equity(close_at)
        equity_curve.append((close_at, eq))
        for s in ranked:
            if free <= 0:
                counts["slot"] += 1
                continue
            rec = exec_modeb(s["symbol"], sym_dfs[s["symbol"]], sym_xs[s["symbol"]], s)
            risk_usd = rec["shares"] * (rec["entry"] - rec["stop"])
            heat_now = sum(current_risk(tr, t_next) for tr in open_book
                           if tr["entry_ts"] <= t_next <= tr["exit_ts"]) / eq
            if (heat_now + risk_usd / eq) > HEAT_CAP:
                counts["heat"] += 1
                continue
            rec["risk_usd"] = float(risk_usd)
            rec["gross_usd"] = float(rec["blended_r"] * risk_usd)
            rec["entry_cost"] = float(0.0025 * rec["shares"] * rec["entry"])
            if rec["tp1_taken"]:
                rec["tp1_cost"] = float(0.0025 * 0.5 * rec["shares"] * rec["tp1_fill_px"])
                rec["exit_cost"] = float(0.0025 * 0.5 * rec["shares"] * rec["exit_px"])
            else:
                rec["tp1_cost"] = 0.0
                rec["exit_cost"] = float(0.0025 * rec["shares"] * rec["exit_px"])
            realized -= rec["entry_cost"]
            open_book.append(rec)
            accepted.append(rec)
            busy_through[s["symbol"]] = rec["exit_ts"]
            free -= 1
            eq = marked_equity(close_at)
    # settle everything to the end for the final equity point
    if batches:
        eq = marked_equity("2099-01-01")
        equity_curve.append(("end", eq))
    print(f"[{tag}] skip counts: {counts}", flush=True)
    print(f"[{tag}] accepted: {len(accepted)}", flush=True)
    return accepted, counts, equity_curve


def econ_stats(accepted, equity_curve):
    levels = {}
    for bps in COST_LEVELS:
        rs = [net_r_legs(t, bps) for t in accepted]
        levels[f"{bps*10000:.0f}bps"] = summarize(f"econ {bps*10000:.0f}bps", rs)
    eq = np.array([e for _, e in equity_curve], dtype=float)
    peak = np.maximum.accumulate(eq)
    dd = float(((eq - peak) / peak).min()) if len(eq) else 0.0
    return {
        "levels": levels,
        "n_trades": len(accepted),
        "final_equity": round(float(eq[-1]), 2) if len(eq) else None,
        "total_return_pct": (round(float((eq[-1] / START_EQUITY - 1) * 100), 2)
                             if len(eq) else None),
        "max_drawdown_pct": round(float(dd * 100), 2),
    }


def main():
    with open(os.path.join(OUT, "signals_factors.json")) as fh:
        sigrecs = json.load(fh)
    factor_map = {r["signal_id"]: r for r in sigrecs}

    uni131 = [u["symbol"] for u in simlib.load_universe()]
    mask14 = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB", "ONDS", "DRAM",
              "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
    work = [s for s in uni131 if s not in mask14]

    # ---- validation: 131-name no-filter run must match canonical_trades.json ----
    acc131, _, _ = build_v5_filtered(uni131, factor_map, None, tag="VALIDATE-131")
    with open(os.path.join(BASE, "canonical_trades.json")) as fh:
        canon = json.load(fh)
    mine = sorted(t["signal_id"] for t in acc131)
    theirs = sorted(t["signal_id"] for t in canon)
    if mine == theirs:
        print(f"VALIDATION PASS: 131-name no-filter run reproduces canonical "
              f"({len(mine)} trades, identical signal_ids)", flush=True)
    else:
        only_mine = set(mine) - set(theirs)
        only_theirs = set(theirs) - set(mine)
        print(f"VALIDATION FAIL: mine={len(mine)} theirs={len(theirs)} "
              f"only_mine={len(only_mine)} only_theirs={len(only_theirs)}", flush=True)
        print("only_mine sample:", sorted(only_mine)[:3], flush=True)
        print("only_theirs sample:", sorted(only_theirs)[:3], flush=True)
        return

    def f1_sel(s, f):
        return f is not None and f.get("f1_20d") is not None and f["f1_20d"] > 0

    def f2_sel(s, f):
        return f is not None and f.get("f2_10_50") is not None and f["f2_10_50"] > 0

    results = {}
    for tag, filt in (("work123_none", None), ("work123_F1", f1_sel), ("work123_F2", f2_sel)):
        acc, counts, curve = build_v5_filtered(work, factor_map, filt, tag=tag)
        st = econ_stats(acc, curve)
        st["skip_counts"] = counts
        results[tag] = st
        print(f"[{tag}] {json.dumps(st, indent=1)[:600]}", flush=True)

    with open(os.path.join(OUT, "economic_replay.json"), "w") as fh:
        json.dump(results, fh, indent=1)
    print("wrote economic_replay.json", flush=True)


if __name__ == "__main__":
    main()
