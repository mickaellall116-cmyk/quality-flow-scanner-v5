"""W3 economic check: portfolio replay on the working set.

1. Baseline repro: build_v5 over the 123-name working set, verify exact
   reproduction of canonical_trades.json (working-set subset) - validates the
   machinery before any filtered replay is trusted.
2. Selected-only replays: same walk, but candidates restricted to signals
   passing F5 base (top-3) / F6 base (>0.8) at candidate stage (mirrors the
   corrected lone-wolf rerun's candidate-stage block convention).

Same $75k / 1% / 6-slot / 5%-heat / rs_top2 machinery imported from
canonical_baseline (simlib, modeb_engine, run_ablation). Equity curve sampled
at each batch close for max DD; net R per cost level via net_r_legs.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
CB = os.path.expanduser("~/workspace/quality-flow-scanner-v5/canonical_baseline")
sys.path.insert(0, CB)

import simlib
from simlib import m53, sr
import modeb_engine
from run_ablation import (exec_modeb, leg_cost_usd, net_r_legs, summarize,
                          save_json, START_EQUITY, RISK_USD, MAX_OPEN,
                          HEAT_CAP, TAB131)
import factors as F

COST_LEVELS = [0.0025, 0.005, 0.0075, 0.01]


def build_selection_map(symbols, sec):
    """signal_id -> (f5_selected, f6_selected), strict PIT."""
    sel = {}
    for sym in symbols:
        ws, we = TAB131[sym]
        sigs, _df = simlib.v54_signals(sym, ws, we)
        for s in sigs:
            ts = pd.Timestamp(s["signal_bar_close_at"])
            r = F.factor_row(sym, sec[sym], ts)
            sel[s["signal_id"]] = (r["f5_selected"], r["f6_selected"])
    return sel


def build_v5(symbols, tag, keep_fn=None, selmap=None):
    all_sigs = []
    sym_dfs = {}
    sym_xs = {}
    for sym in symbols:
        ws, we = TAB131[sym]
        sigs, df = simlib.v54_signals(sym, ws, we)
        all_sigs.extend(sigs)
        sym_dfs[sym] = df
        sym_xs[sym] = simlib.exit_states_vector(sym)
    if keep_fn is not None:
        n0 = len(all_sigs)
        all_sigs = [s for s in all_sigs if keep_fn(s)]
        print(f"[{tag}] candidates {n0} -> {len(all_sigs)} after factor filter",
              flush=True)
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
    eq_curve = []

    def current_risk(tr, t_next):
        r = tr["risk_usd"]
        if tr["tp1_taken"] and tr["tp1_fill_ts"] is not None and t_next > tr["tp1_fill_ts"]:
            r = r / 2.0
        return r

    def marked_equity(t_c):
        nonlocal realized
        still_open = []
        for tr in open_book:
            df = sym_dfs[tr["symbol"]]
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
        eq_curve.append((close_at, eq))
        for s in ranked:
            if free <= 0:
                counts["slot"] += 1
                continue
            sym = s["symbol"]
            rec = exec_modeb(sym, sym_dfs[sym], sym_xs[sym], s)
            rec["signal_id"] = s["signal_id"]
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
            busy_through[sym] = rec["exit_ts"]
            free -= 1
            eq = marked_equity(close_at)
    # settle to the end
    if open_book:
        last_exit = max(tr["exit_ts"] for tr in open_book)
        eq = marked_equity(last_exit)
        eq_curve.append((last_exit, eq))
    print(f"[{tag}] accepted: {len(accepted)} skips: {counts}", flush=True)
    return accepted, counts, eq_curve


def report(accepted, eq_curve, tag):
    levels = {}
    for bps in COST_LEVELS:
        rs = [net_r_legs(t, bps) for t in accepted]
        levels[f"{bps*10000:.0f}bps"] = {
            "n": len(rs), "exp": float(np.mean(rs)) if rs else 0.0,
            "win_rate": float(np.mean([r > 0 for r in rs])) if rs else 0.0,
            "pf": (float(np.sum([r for r in rs if r > 0])) /
                   abs(float(np.sum([r for r in rs if r < 0])))) if any(r < 0 for r in rs) else None,
        }
    eqs = np.array([e for _, e in eq_curve])
    peak = np.maximum.accumulate(eqs)
    dd = (eqs - peak) / peak
    final = float(eqs[-1]) if len(eqs) else START_EQUITY
    return {
        "tag": tag,
        "n_trades": len(accepted),
        "levels": levels,
        "final_equity": final,
        "total_return": final / START_EQUITY - 1,
        "max_dd": float(dd.min()) if len(dd) else 0.0,
    }


def main():
    syms, sec = F.working_set()
    print("working set:", len(syms), flush=True)

    # ---- baseline repro ----
    acc0, c0, eq0 = build_v5(syms, "baseline")
    rep0 = report(acc0, eq0, "baseline_working_set")
    with open(os.path.join(CB, "canonical_trades.json")) as fh:
        canon = json.load(fh)
    wset = set(syms)
    canon_ids = {t["signal_id"] for t in canon if t["symbol"] in wset}
    repro_ids = {t["signal_id"] for t in acc0}
    print("canonical working-set trades:", len(canon_ids),
          "| repro:", len(repro_ids),
          "| match:", canon_ids == repro_ids, flush=True)
    rep0["repro_exact_match"] = (canon_ids == repro_ids)
    rep0["skip_counts"] = c0

    # ---- selection maps ----
    selmap = build_selection_map(syms, sec)

    def keep_f5(s):
        return selmap[s["signal_id"]][0]

    def keep_f6(s):
        return selmap[s["signal_id"]][1]

    acc5, c5, eq5 = build_v5(syms, "F5-selected", keep_fn=keep_f5)
    rep5 = report(acc5, eq5, "F5_selected")
    rep5["skip_counts"] = c5

    acc6, c6, eq6 = build_v5(syms, "F6-selected", keep_fn=keep_f6)
    rep6 = report(acc6, eq6, "F6_selected")
    rep6["skip_counts"] = c6

    out = {"baseline": rep0, "F5": rep5, "F6": rep6}
    with open(os.path.join(HERE, "replay_results.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    for r in (rep0, rep5, rep6):
        l = r["levels"]["50bps"]
        print(f"{r['tag']}: n={r['n_trades']} exp50={l['exp']:+.4f} "
              f"wr={l['win_rate']:.3f} ret={r['total_return']:+.3f} "
              f"dd={r['max_dd']:.3f}", flush=True)


if __name__ == "__main__":
    main()
