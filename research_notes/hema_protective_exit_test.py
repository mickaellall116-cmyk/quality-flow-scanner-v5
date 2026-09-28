#!/usr/bin/env python3
"""
Pre-registered HEMA pre-TP1 protective-exit study.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

from research_notes.hema_research import fetch_symbol, regular_1h, resample_closed_4h
from research_notes.hema_qf_portfolio import SYMBOLS, prepare_symbol
from research_notes.hema_ranking_test import simulate_ranked
from research_notes.hema_exit_test import (
    augment_exit_controls, leg_cost, pf, paired_boot, month_block_boot
)

OUT = Path("hema_protective_exit")
OUT.mkdir(exist_ok=True)

RULES = [
    "current",
    "h4_hema_emergency",
    "daily_hema_emergency",
    "unarmed_scanner_exit_control",
    "h4_ema20_40_emergency",
]
COSTS = [25.0, 50.0, 75.0, 100.0]


def pre_tp1_fire(row: pd.Series, rule: str, armed: bool) -> tuple[bool, str]:
    current = bool(row["scanner_exit"]) and armed
    if rule == "current":
        return current, "PP_PRE_TP1"
    if rule == "h4_hema_emergency":
        if bool(row["big_red"]):
            return True, "H4_HEMA_EMERGENCY"
        return current, "PP_PRE_TP1"
    if rule == "daily_hema_emergency":
        if bool(row["daily_hema_big_red_evt"]):
            return True, "DAILY_HEMA_EMERGENCY"
        return current, "PP_PRE_TP1"
    if rule == "unarmed_scanner_exit_control":
        if bool(row["scanner_exit"]):
            return True, "UNARMED_SCANNER_EXIT"
        return False, ""
    if rule == "h4_ema20_40_emergency":
        if bool(row["h4_ema_big_red_evt"]):
            return True, "H4_EMA_EMERGENCY"
        return current, "PP_PRE_TP1"
    raise KeyError(rule)


def simulate_one(entry_row: pd.Series, df: pd.DataFrame, rule: str, cost_bps: float) -> dict | None:
    sym = str(entry_row["symbol"])
    ets = pd.Timestamp(entry_row["entry_time"])
    if df.index.tz is not None:
        ets = ets.tz_localize(df.index.tz) if ets.tzinfo is None else ets.tz_convert(df.index.tz)
    elif ets.tzinfo is not None:
        ets = ets.tz_localize(None)
    if ets not in df.index:
        return None
    ei = df.index.get_loc(ets)
    if isinstance(ei, slice) or isinstance(ei, np.ndarray):
        return None
    ei = int(ei)

    entry = float(entry_row["entry_px"])
    stop = float(entry_row["stop_px"])
    tp1 = float(entry_row["tp1_px"])
    shares = int(entry_row["shares"])
    planned_risk = float(entry_row["planned_risk"])
    rps = entry - stop
    if shares <= 0 or planned_risk <= 0 or rps <= 0:
        return None

    entry_cost = leg_cost(entry * shares, cost_bps)
    partial_pnl = 0.0
    partial_cost = 0.0
    partial_r = 0.0
    tp1_taken = False
    runner_shares = shares
    armed = False
    pending = False
    pending_reason = ""

    max_i = min(len(df) - 1, ei + 29)
    for j in range(ei, max_i + 1):
        row = df.iloc[j]
        o, h, l, c = map(float, [row["Open"], row["High"], row["Low"], row["Close"]])

        if pending:
            fill = o
            qty = runner_shares if tp1_taken else shares
            pnl = (fill - entry) * qty
            cc = leg_cost(fill * qty, cost_bps)
            rr = (fill - entry) / rps
            gross = (0.5 * partial_r + 0.5 * rr) if tp1_taken else rr
            net_pnl = partial_pnl + pnl - entry_cost - partial_cost - cc
            return {
                "symbol": sym, "entry_time": str(ets), "exit_time": str(df.index[j]),
                "rule": rule, "cost_bps": cost_bps, "exit_reason": pending_reason,
                "gross_r": gross, "net_r": net_pnl / planned_risk,
                "tp1": tp1_taken, "bars": j - ei + 1,
            }

        if h >= entry + rps:
            armed = True

        # Structural stop has priority.
        if l <= stop:
            fill = o if o < stop else stop
            qty = runner_shares if tp1_taken else shares
            pnl = (fill - entry) * qty
            cc = leg_cost(fill * qty, cost_bps)
            rr = (fill - entry) / rps
            gross = (0.5 * partial_r + 0.5 * rr) if tp1_taken else rr
            net_pnl = partial_pnl + pnl - entry_cost - partial_cost - cc
            return {
                "symbol": sym, "entry_time": str(ets), "exit_time": str(df.index[j]),
                "rule": rule, "cost_bps": cost_bps, "exit_reason": "STOP",
                "gross_r": gross, "net_r": net_pnl / planned_risk,
                "tp1": tp1_taken, "bars": j - ei + 1,
            }

        if not tp1_taken and h >= tp1:
            fill = o if o > tp1 else tp1
            qty = max(1, shares // 2)
            partial_pnl += (fill - entry) * qty
            partial_cost += leg_cost(fill * qty, cost_bps)
            partial_r = (fill - entry) / rps
            tp1_taken = True
            runner_shares = shares - qty
            # Preserve Mode B: no exit evaluation on TP1 bar.
            if j == max_i:
                qty2 = runner_shares
                pnl2 = (c - entry) * qty2
                cc2 = leg_cost(c * qty2, cost_bps)
                rr = (c - entry) / rps
                gross = 0.5 * partial_r + 0.5 * rr
                net_pnl = partial_pnl + pnl2 - entry_cost - partial_cost - cc2
                return {
                    "symbol": sym, "entry_time": str(ets), "exit_time": str(df.index[j]),
                    "rule": rule, "cost_bps": cost_bps, "exit_reason": "TIMEOUT",
                    "gross_r": gross, "net_r": net_pnl / planned_risk,
                    "tp1": True, "bars": j - ei + 1,
                }
            continue

        if not tp1_taken:
            fire, reason = pre_tp1_fire(row, rule, armed)
            if fire:
                pending = True
                pending_reason = reason
        else:
            # Post-TP1 remains current for every variant.
            if armed and bool(row["scanner_exit"]):
                pending = True
                pending_reason = "CURRENT_RUNNER_EXIT"

        if j == max_i:
            qty = runner_shares if tp1_taken else shares
            pnl = (c - entry) * qty
            cc = leg_cost(c * qty, cost_bps)
            rr = (c - entry) / rps
            gross = (0.5 * partial_r + 0.5 * rr) if tp1_taken else rr
            net_pnl = partial_pnl + pnl - entry_cost - partial_cost - cc
            return {
                "symbol": sym, "entry_time": str(ets), "exit_time": str(df.index[j]),
                "rule": rule, "cost_bps": cost_bps, "exit_reason": "TIMEOUT",
                "gross_r": gross, "net_r": net_pnl / planned_risk,
                "tp1": tp1_taken, "bars": j - ei + 1,
            }
    return None


def summarize(g: pd.DataFrame) -> dict:
    nr = g["net_r"].astype(float)
    return {
        "n": int(len(g)),
        "total_net_r": float(nr.sum()),
        "net_expectancy_r": float(nr.mean()),
        "net_median_r": float(nr.median()),
        "net_win_pct": float((nr > 0).mean() * 100.0),
        "net_profit_factor": pf(nr),
        "avg_bars": float(g["bars"].mean()),
        "tp1_n": int(g["tp1"].astype(bool).sum()),
        "stop_n": int((g["exit_reason"] == "STOP").sum()),
    }


def yearly(g: pd.DataFrame) -> list[dict]:
    x = g.copy()
    dt = pd.to_datetime(x["entry_time"], utc=True)
    x["year"] = dt.dt.tz_convert("America/New_York").dt.year
    return [{"year": int(y), **summarize(h)} for y, h in x.groupby("year")]


def main() -> None:
    spy_i = regular_1h(fetch_symbol("SPY", "1h", "729d"))
    spy_h4 = resample_closed_4h(spy_i, "SPY")
    frames = {}
    for k, sym in enumerate(SYMBOLS, 1):
        print(f"[{k}/{len(SYMBOLS)}] {sym}")
        h = prepare_symbol(sym, spy_h4)
        if h is not None:
            frames[sym] = augment_exit_controls(h)

    _, _, entries, _ = simulate_ranked(frames, "rs", 50.0)
    entries.to_csv(OUT / "baseline_entries.csv", index=False)

    rows = []
    for cost in COSTS:
        for rule in RULES:
            print("SIM", rule, cost)
            for _, er in entries.iterrows():
                sym = str(er["symbol"])
                rec = simulate_one(er, frames[sym], rule, cost)
                if rec is not None:
                    rows.append(rec)
    trades = pd.DataFrame(rows)
    trades.to_csv(OUT / "trades.csv", index=False)

    result = {"rules": {}, "paired_vs_current_50bps": {}}
    for cost in COSTS:
        result["rules"][str(int(cost))] = {}
        for rule in RULES:
            g = trades[(trades["cost_bps"] == cost) & (trades["rule"] == rule)]
            result["rules"][str(int(cost))][rule] = summarize(g)

    cur = trades[(trades["cost_bps"] == 50.0) & (trades["rule"] == "current")].copy()
    cur = cur.set_index(["symbol", "entry_time"]).sort_index()

    emergency_reasons = {
        "h4_hema_emergency": "H4_HEMA_EMERGENCY",
        "daily_hema_emergency": "DAILY_HEMA_EMERGENCY",
        "unarmed_scanner_exit_control": "UNARMED_SCANNER_EXIT",
        "h4_ema20_40_emergency": "H4_EMA_EMERGENCY",
    }

    for rule in RULES:
        if rule == "current":
            continue
        can = trades[(trades["cost_bps"] == 50.0) & (trades["rule"] == rule)].copy()
        can = can.set_index(["symbol", "entry_time"]).sort_index()
        idx = cur.index.intersection(can.index)
        c0 = cur.loc[idx]
        c1 = can.loc[idx]
        diff = c1["net_r"].astype(float) - c0["net_r"].astype(float)
        ddf = pd.DataFrame({
            "symbol": [i[0] for i in idx],
            "entry_time": [i[1] for i in idx],
            "diff": diff.to_numpy(),
        })
        changed = (
            (c1["exit_time"].astype(str).to_numpy() != c0["exit_time"].astype(str).to_numpy())
            | (np.abs(diff.to_numpy()) > 1e-12)
        )
        ereason = emergency_reasons[rule]
        emergency_mask = c1["exit_reason"].astype(str) == ereason
        stop_avoided = emergency_mask & (c0["exit_reason"].astype(str) == "STOP")
        sacrificed_winner = emergency_mask & (c0["net_r"].astype(float) > 0)
        result["paired_vs_current_50bps"][rule] = {
            "paired_n": int(len(idx)),
            "changed_trades": int(changed.sum()),
            "emergency_fires": int(emergency_mask.sum()),
            "baseline_stops_avoided": int(stop_avoided.sum()),
            "baseline_winners_cut_early": int(sacrificed_winner.sum()),
            "mean_net_r_diff": float(diff.mean()),
            "paired_boot": paired_boot(diff),
            "month_block_boot": month_block_boot(ddf),
            "candidate_yearly": yearly(c1.reset_index()),
        }

    (OUT / "results.json").write_text(json.dumps(result, indent=2))
    print("HEMA_PROTECTIVE_START")
    print(json.dumps(result, indent=2))
    print("HEMA_PROTECTIVE_END")


if __name__ == "__main__":
    main()
