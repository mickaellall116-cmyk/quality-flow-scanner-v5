"""W2 economic check: portfolio replay restricted to factor-selected signals
vs the full working-set replay.

Same $75k / 1% risk / max-6-open / 5%-heat / rs_top2 slot-competition
machinery as canonical_baseline/run_portfolio.py build_v5 (code copied
verbatim except for the candidate admit() hook). Symbol universe = the
123-name masked working set (131 PIT names minus the 14).

Variants:
  FULL : all candidates (working-set baseline)
  F3   : admit only signals with 20d/60d ADDV ratio > 1.25 (strict PIT)
  F4   : admit only signals with 14d ATR / 60d median ATR > 1.2 (strict PIT)

Writes econ_replay.json with per-variant summaries at 25/50/75/100bps
plus equity-curve drawdown and total return at 50bps.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "..", "canonical_baseline"))
import factors  # noqa: E402
import simlib  # noqa: E402
from simlib import m53, sr  # noqa: E402
import modeb_engine  # noqa: E402
from run_ablation import (exec_modeb, leg_cost_usd, net_r_legs, summarize,  # noqa: E402
                          save_json, shares_for,
                          START_EQUITY, RISK_USD, MAX_OPEN, HEAT_CAP, TAB131)

BASE = os.path.dirname(os.path.abspath(__file__))


def admit_none_extra(s):
    return True


def admit_f3(s):
    v = factors.factor_at(factors.f3_series, s["symbol"],
                          s["signal_bar_close_at"])
    return bool(not np.isnan(v) and v > 1.25)


def admit_f4(s):
    v = factors.factor_at(factors.f4_series, s["symbol"],
                          s["signal_bar_close_at"])
    return bool(not np.isnan(v) and v > 1.2)


def build_filtered(symbols, admit, tag="W"):
    # ---- signals (v54, selected symbols) ----
    all_sigs = []
    sym_dfs = {}
    sym_xs = {}
    tab = {s: TAB131[s] for s in symbols}
    for sym in symbols:
        ws, we = tab[sym]
        sigs, df = simlib.v54_signals(sym, ws, we)
        all_sigs.extend(sigs)
        sym_dfs[sym] = df
        sym_xs[sym] = simlib.exit_states_vector(sym)
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
    counts = {"busy": 0, "slot": 0, "heat": 0, "factor_skipped": 0,
              "candidates": len(all_sigs)}

    open_book = []
    realized = START_EQUITY

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
            elif not admit(s):
                counts["factor_skipped"] += 1
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
    print(f"[{tag}] skip counts:", counts, flush=True)
    print(f"[{tag}] accepted: {len(accepted)}", flush=True)
    return accepted, counts


def econ_summary(accepted, tag):
    COST_LEVELS = [0.0025, 0.005, 0.0075, 0.01]
    out = {"tag": tag, "n_trades": len(accepted)}
    for bps in COST_LEVELS:
        rs = np.array([net_r_legs(t, bps) for t in accepted])
        out[f"{bps*10000:.0f}bps"] = summarize(f"{tag} {bps*10000:.0f}bps", rs)
    # equity curve at 50bps: cumulative net $ sorted by exit_ts
    recs = sorted(accepted, key=lambda t: t["exit_ts"])
    net_usd = np.array([net_r_legs(t, 0.005) * t["risk_usd"] for t in recs])
    cum = np.cumsum(net_usd)
    peak = np.maximum.accumulate(np.concatenate([[0.0], cum]))
    dd = (np.concatenate([[0.0], cum]) - peak)
    out["total_net_usd_50bps"] = round(float(cum[-1]) if len(cum) else 0.0, 2)
    out["total_return_pct_50bps"] = round(float(cum[-1] / START_EQUITY * 100)
                                         if len(cum) else 0.0, 2)
    out["max_dd_usd_50bps"] = round(float(dd.min()), 2)
    out["max_dd_r_50bps"] = round(float(dd.min() / RISK_USD), 2)
    return out


def main():
    symbols = factors.working_symbols()
    print(f"working symbols: {len(symbols)}", flush=True)
    assert not (set(symbols) & factors.MASKED_14), "mask leak in replay"

    variants = [("FULL", admit_none_extra),
                ("F3", admit_f3),
                ("F4", admit_f4)]
    results = {}
    for tag, admit in variants:
        accepted, counts = build_filtered(symbols, admit, tag=tag)
        results[tag] = {"summary": econ_summary(accepted, tag),
                        "skip_counts": counts}
        with open(os.path.join(BASE, "econ_replay.json"), "w") as fh:
            json.dump(results, fh, indent=1, default=str)
        print(f"[{tag}] econ:", json.dumps(results[tag]["summary"], indent=1),
              flush=True)
    print("wrote econ_replay.json", flush=True)


if __name__ == "__main__":
    main()
