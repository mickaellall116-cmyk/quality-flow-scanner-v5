"""V4 (cost ladder) + V5 (full portfolio walk). Reads v3_trades.json.

Cost model (round-trip, leg-based): cost_$ = (bps/2) x sum of leg notionals.
Legs: entry (full shares) + exits; TP1 partial counts as a half-size leg,
runner exit as a half-size leg; full exit as a full leg. A standard round
trip = 2 leg-equivalents, so cost ~= bps x notional. Headline = 50bps.

V5 portfolio: $75k start, $750 fixed risk/trade (shares=floor(750/(entry-stop))),
max 6 open, 5% heat cap (sum of current position risks / marked equity),
slot competition by rs_top2 (20-bar 4H return minus SPY, strict PIT) with
deterministic tie-break (signal timestamp, then symbol alpha), one position
per symbol (live _busy rule). Equity marked at 4H closes; costs deducted
from equity at event legs.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import simlib
from simlib import m53, sr
import modeb_engine
from run_ablation import (exec_modeb, leg_cost_usd, net_r_legs, summarize,
                          save_json, walk_independent, shares_for,
                          START_EQUITY, RISK_USD, MAX_OPEN, HEAT_CAP, TAB131,
                          TAB14, OVERLAY14)

BASE = simlib.BASE
COST_LEVELS = [0.0025, 0.005, 0.0075, 0.01]


def load_trades(name):
    with open(os.path.join(BASE, name)) as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# V4: cost ladder on the V3 trade set
# --------------------------------------------------------------------------

def run_v4(v3tr):
    out = {}
    for bps in COST_LEVELS:
        rs = [net_r_legs(t, bps) for t in v3tr]
        out[f"{bps*10000:.0f}bps"] = summarize(f"V4 {bps*10000:.0f}bps", rs)
    return out


# --------------------------------------------------------------------------
# V5: full portfolio walk
# --------------------------------------------------------------------------

def build_v5(symbols, tag="V5"):
    # ---- signals (v54, selected symbols) ----
    all_sigs = []
    sym_dfs = {}
    sym_xs = {}
    tab = {s: (TAB131 if s in TAB131 else TAB14)[s] for s in symbols}
    for sym in symbols:
        ws, we = tab[sym]
        sigs, df = simlib.v54_signals(sym, ws, we)
        all_sigs.extend(sigs)
        sym_dfs[sym] = df
        sym_xs[sym] = simlib.exit_states_vector(sym)
        if sigs:
            print(f"  sig {sym}: {len(sigs)}", flush=True)
    print(f"[{tag}] total v54 candidate signals: {len(all_sigs)}", flush=True)

    # ---- rs_top2 scores for slot competition ----
    by_sym = {}
    for s in all_sigs:
        by_sym.setdefault(s["symbol"], []).append(s)
    rs_scores = simlib.rs_top2_scores(by_sym)

    # ---- chronological batches ----
    all_sigs.sort(key=lambda s: (s["signal_bar_close_at"], s["symbol"]))
    batches = []
    prev_key = None
    for s in all_sigs:
        k = s["signal_bar_close_at"]
        if k != prev_key:
            batches.append((k, []))
            prev_key = k
        batches[-1][1].append(s)
    print(f"[{tag}] batches: {len(batches)}", flush=True)

    busy_through = {}
    accepted = []
    counts = {"busy": 0, "slot": 0, "heat": 0, "candidates": len(all_sigs)}

    # open-position bookkeeping for slot/heat: list of dicts
    open_book = []  # accepted trades not yet settled at current batch
    realized = START_EQUITY
    # per-trade econ precomputed at acceptance
    def current_risk(tr, t_next):
        r = tr["risk_usd"]
        if tr["tp1_taken"] and tr["tp1_fill_ts"] is not None and t_next > tr["tp1_fill_ts"]:
            r = r / 2.0
        return r

    def marked_equity(t_c):
        # settle events with ts <= t_c, then mark open at t_c
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
        t_next = batch[0]["entry_bar_ts"]  # same entry bar for the batch
        # 1. per-symbol busy dedup (live _busy rule), symbol order
        qualified = []
        for s in sorted(batch, key=lambda x: x["symbol"]):
            bt = busy_through.get(s["symbol"])
            if bt is not None and s["signal_bar_close_at"] <= bt:
                counts["busy"] += 1
            else:
                qualified.append(s)
        if not qualified:
            continue
        # 2. rank by rs_top2 (deterministic tie-break: ts, then symbol)
        ranked = sorted(qualified,
                        key=lambda s: (-rs_scores[s["signal_id"]],
                                       s["signal_bar_close_at"], s["symbol"]))
        # slots used at entry bar
        used = sum(1 for tr in open_book
                   if tr["entry_ts"] <= t_next <= tr["exit_ts"])
        free = MAX_OPEN - used
        eq = marked_equity(close_at)
        for s in ranked:
            if free <= 0:
                counts["slot"] += 1
                continue
            sym = s["symbol"]
            rec = exec_modeb(sym, sym_dfs[sym], sym_xs[sym], s)
            risk_usd = rec["shares"] * (rec["entry"] - rec["stop"])
            heat_now = sum(current_risk(tr, t_next) for tr in open_book
                           if tr["entry_ts"] <= t_next <= tr["exit_ts"]) / eq
            if (heat_now + risk_usd / eq) > HEAT_CAP:
                counts["heat"] += 1
                continue
            # accept
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
            # equity changed (entry cost); refresh for next candidate
            eq = marked_equity(close_at)
    print(f"[{tag}] skip counts:", counts, flush=True)
    print(f"[{tag}] accepted: {len(accepted)}", flush=True)
    return accepted, counts


def main():
    v3tr = load_trades("v3_trades.json")
    v4 = run_v4(v3tr)
    save_json("v4_cost_ladder.json", v4)
    print("V4:", json.dumps(v4, indent=1), flush=True)

    accepted, counts = build_v5(list(TAB131.keys()), tag="V5")
    # net R at each cost level (costs already modeled per-leg at 50bps in
    # the walk for equity; net_r recomputed per level for the ladder)
    v5_levels = {}
    for bps in COST_LEVELS:
        rs = [net_r_legs(t, bps) for t in accepted]
        v5_levels[f"{bps*10000:.0f}bps"] = summarize(f"V5 {bps*10000:.0f}bps", rs)
    for t in accepted:
        for bps in COST_LEVELS:
            t[f"net_r_{bps*10000:.0f}bps"] = net_r_legs(t, bps)
    save_json("canonical_trades.json", accepted)
    save_json("v5_summary.json", {"levels": v5_levels, "skip_counts": counts})
    print("V5:", json.dumps(v5_levels, indent=1), flush=True)

    # 14-name overlay (separate, never the canonical universe)
    ov_acc, ov_counts = build_v5(OVERLAY14, tag="V5-overlay14")
    ov_levels = {}
    for bps in COST_LEVELS:
        rs = [net_r_legs(t, bps) for t in ov_acc]
        ov_levels[f"{bps*10000:.0f}bps"] = summarize(
            f"V5-overlay14 {bps*10000:.0f}bps", rs)
    for t in ov_acc:
        for bps in COST_LEVELS:
            t[f"net_r_{bps*10000:.0f}bps"] = net_r_legs(t, bps)
    save_json("v5_overlay14.json",
              {"levels": ov_levels, "skip_counts": ov_counts,
               "trades": ov_acc})
    print("V5-overlay14:", json.dumps(ov_levels, indent=1), flush=True)


if __name__ == "__main__":
    main()
