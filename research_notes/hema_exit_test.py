#!/usr/bin/env python3
"""
Pre-registered HEMA runner-exit study.

Uses the exact 50-bps rs_top2 baseline accepted entries, then holds
entry/stop/TP1/shares fixed while changing only the post-TP1 runner rule.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

from research_notes.hema_research import (
    fetch_symbol, regular_1h, resample_closed_4h, daily_from_h4, add_hema, ema
)
from research_notes.hema_qf_portfolio import (
    SYMBOLS, ROUND_TRIP_BPS, prepare_symbol, carry_htf_to_h4, map_exact_htf_events
)
from research_notes.hema_ranking_test import simulate_ranked

OUT = Path("hema_exit")
OUT.mkdir(exist_ok=True)

RULES = [
    "current",
    "daily_hema_cross",
    "current_and_daily_hema_bear",
    "h4_hema_cross",
    "daily_ema20_40_cross",
    "h4_ema20_40_cross",
]
COSTS = [25.0, 50.0, 75.0, 100.0]


def leg_cost(notional: float, round_trip_bps: float) -> float:
    return abs(float(notional)) * (round_trip_bps / 2.0) / 10000.0


def map_completed_daily_event_to_next_h4(h4_index: pd.DatetimeIndex, daily: pd.DataFrame, col: str) -> pd.Series:
    """Map a completed daily event to the first *subsequent* 4H bar.

    daily_from_h4 labels the daily bar at that day's last 4H bucket (13:30 ET).
    The full daily close is only known at 16:00, so the event becomes actionable
    at the next trading day's first 4H bar, never on the 13:30 bar itself.
    """
    out = pd.Series(False, index=h4_index)
    if daily is None or daily.empty or col not in daily:
        return out
    for ts, v in daily[col].fillna(False).items():
        if not bool(v):
            continue
        pos = h4_index.searchsorted(ts, side="right")
        if pos < len(h4_index):
            out.iloc[pos] = True
    return out


def augment_exit_controls(h4: pd.DataFrame) -> pd.DataFrame:
    x = h4.copy()
    d, _ = daily_from_h4(x)
    d = add_hema(d) if not d.empty else d
    if not d.empty:
        d["EMA20_CTRL"] = ema(d["Close"], 20)
        d["EMA40_CTRL"] = ema(d["Close"], 40)
        d["ema_big_red"] = (
            (d["EMA20_CTRL"] < d["EMA40_CTRL"])
            & (d["EMA20_CTRL"].shift(1) >= d["EMA40_CTRL"].shift(1))
        )
        x["daily_hema_bear"] = carry_htf_to_h4(x.index, d, "bear_regime")
        x["daily_hema_big_red_evt"] = map_completed_daily_event_to_next_h4(x.index, d, "big_red")
        x["daily_ema_big_red_evt"] = map_completed_daily_event_to_next_h4(x.index, d, "ema_big_red")
    else:
        x["daily_hema_bear"] = False
        x["daily_hema_big_red_evt"] = False
        x["daily_ema_big_red_evt"] = False

    if "EMA20_CTRL" not in x:
        x["EMA20_CTRL"] = ema(x["Close"], 20)
    if "EMA40_CTRL" not in x:
        x["EMA40_CTRL"] = ema(x["Close"], 40)
    x["h4_ema_big_red_evt"] = (
        (x["EMA20_CTRL"] < x["EMA40_CTRL"])
        & (x["EMA20_CTRL"].shift(1) >= x["EMA40_CTRL"].shift(1))
    )
    return x


def runner_fire(row: pd.Series, rule: str) -> bool:
    if rule == "current":
        return bool(row["scanner_exit"])
    if rule == "daily_hema_cross":
        return bool(row["daily_hema_big_red_evt"])
    if rule == "current_and_daily_hema_bear":
        return bool(row["scanner_exit"]) and bool(row["daily_hema_bear"])
    if rule == "h4_hema_cross":
        return bool(row["big_red"])
    if rule == "daily_ema20_40_cross":
        return bool(row["daily_ema_big_red_evt"])
    if rule == "h4_ema20_40_cross":
        return bool(row["h4_ema_big_red_evt"])
    raise KeyError(rule)


def simulate_one(entry_row: pd.Series, df: pd.DataFrame, rule: str, cost_bps: float) -> dict | None:
    sym = str(entry_row["symbol"])
    ets = pd.Timestamp(entry_row["entry_time"])
    if df.index.tz is not None:
        if ets.tzinfo is None:
            ets = ets.tz_localize(df.index.tz)
        else:
            ets = ets.tz_convert(df.index.tz)
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
    tp1_i = None
    runner_mfe_r = np.nan

    max_i = min(len(df) - 1, ei + 29)
    for j in range(ei, max_i + 1):
        row = df.iloc[j]
        o, h, l, c = map(float, [row["Open"], row["High"], row["Low"], row["Close"]])

        # Runner MFE uses complete bars AFTER the TP1 bar to avoid intrabar ordering assumptions.
        if tp1_taken and tp1_i is not None and j > tp1_i:
            hr = (h - entry) / rps
            runner_mfe_r = hr if np.isnan(runner_mfe_r) else max(runner_mfe_r, hr)

        if pending:
            fill = o
            qty = runner_shares if tp1_taken else shares
            pnl = (fill - entry) * qty
            cc = leg_cost(fill * qty, cost_bps)
            rr = (fill - entry) / rps
            gross_blend = (0.5 * partial_r + 0.5 * rr) if tp1_taken else rr
            net_pnl = partial_pnl + pnl - entry_cost - partial_cost - cc
            if tp1_taken and np.isnan(runner_mfe_r):
                runner_mfe_r = max(partial_r, rr)
            elif tp1_taken:
                runner_mfe_r = max(runner_mfe_r, partial_r)
            return {
                "symbol": sym, "entry_time": str(ets), "exit_time": str(df.index[j]),
                "rule": rule, "cost_bps": cost_bps, "exit_reason": pending_reason,
                "gross_r": gross_blend, "net_r": net_pnl / planned_risk,
                "tp1": tp1_taken, "bars": j - ei + 1,
                "runner_exit_r": rr if tp1_taken else np.nan,
                "runner_mfe_r": runner_mfe_r if tp1_taken else np.nan,
                "runner_giveback_r": (runner_mfe_r - rr) if tp1_taken else np.nan,
            }

        if h >= entry + rps:
            armed = True

        # Structural stop always wins.
        if l <= stop:
            fill = o if o < stop else stop
            qty = runner_shares if tp1_taken else shares
            pnl = (fill - entry) * qty
            cc = leg_cost(fill * qty, cost_bps)
            rr = (fill - entry) / rps
            gross_blend = (0.5 * partial_r + 0.5 * rr) if tp1_taken else rr
            net_pnl = partial_pnl + pnl - entry_cost - partial_cost - cc
            if tp1_taken and np.isnan(runner_mfe_r):
                runner_mfe_r = max(partial_r, rr)
            elif tp1_taken:
                runner_mfe_r = max(runner_mfe_r, partial_r)
            return {
                "symbol": sym, "entry_time": str(ets), "exit_time": str(df.index[j]),
                "rule": rule, "cost_bps": cost_bps, "exit_reason": "STOP",
                "gross_r": gross_blend, "net_r": net_pnl / planned_risk,
                "tp1": tp1_taken, "bars": j - ei + 1,
                "runner_exit_r": rr if tp1_taken else np.nan,
                "runner_mfe_r": runner_mfe_r if tp1_taken else np.nan,
                "runner_giveback_r": (runner_mfe_r - rr) if tp1_taken else np.nan,
            }

        if (not tp1_taken) and h >= tp1:
            fill = o if o > tp1 else tp1
            qty = max(1, shares // 2)
            partial_pnl += (fill - entry) * qty
            partial_cost += leg_cost(fill * qty, cost_bps)
            partial_r = (fill - entry) / rps
            tp1_taken = True
            runner_shares = shares - qty
            tp1_i = j
            runner_mfe_r = partial_r

            # Same convention as Mode B: do not evaluate runner exit on TP1 bar.
            if j == max_i:
                qty2 = runner_shares
                pnl2 = (c - entry) * qty2
                cc2 = leg_cost(c * qty2, cost_bps)
                rr = (c - entry) / rps
                gross_blend = 0.5 * partial_r + 0.5 * rr
                net_pnl = partial_pnl + pnl2 - entry_cost - partial_cost - cc2
                runner_mfe_r = max(runner_mfe_r, rr)
                return {
                    "symbol": sym, "entry_time": str(ets), "exit_time": str(df.index[j]),
                    "rule": rule, "cost_bps": cost_bps, "exit_reason": "TIMEOUT",
                    "gross_r": gross_blend, "net_r": net_pnl / planned_risk,
                    "tp1": True, "bars": j - ei + 1,
                    "runner_exit_r": rr, "runner_mfe_r": runner_mfe_r,
                    "runner_giveback_r": runner_mfe_r - rr,
                }
            continue

        # Pre-TP1 remains exactly current Profit Protect.
        if not tp1_taken:
            if armed and bool(row["scanner_exit"]):
                pending = True
                pending_reason = "PP_PRE_TP1"
        else:
            if runner_fire(row, rule):
                pending = True
                pending_reason = rule

        if j == max_i:
            qty = runner_shares if tp1_taken else shares
            pnl = (c - entry) * qty
            cc = leg_cost(c * qty, cost_bps)
            rr = (c - entry) / rps
            gross_blend = (0.5 * partial_r + 0.5 * rr) if tp1_taken else rr
            net_pnl = partial_pnl + pnl - entry_cost - partial_cost - cc
            if tp1_taken:
                runner_mfe_r = max(runner_mfe_r if not np.isnan(runner_mfe_r) else partial_r, rr, partial_r)
            return {
                "symbol": sym, "entry_time": str(ets), "exit_time": str(df.index[j]),
                "rule": rule, "cost_bps": cost_bps, "exit_reason": "TIMEOUT",
                "gross_r": gross_blend, "net_r": net_pnl / planned_risk,
                "tp1": tp1_taken, "bars": j - ei + 1,
                "runner_exit_r": rr if tp1_taken else np.nan,
                "runner_mfe_r": runner_mfe_r if tp1_taken else np.nan,
                "runner_giveback_r": (runner_mfe_r - rr) if tp1_taken else np.nan,
            }
    return None


def pf(s: pd.Series) -> float | None:
    s = s.dropna().astype(float)
    w = s[s > 0]
    l = s[s <= 0]
    if len(l) == 0 or float(l.sum()) == 0:
        return None
    v = float(w.sum() / abs(l.sum()))
    return v if np.isfinite(v) else None


def summarize(g: pd.DataFrame) -> dict:
    nr = g["net_r"].astype(float)
    runners = g[g["tp1"] == True]
    return {
        "n": int(len(g)),
        "total_net_r": float(nr.sum()),
        "net_expectancy_r": float(nr.mean()),
        "net_median_r": float(nr.median()),
        "net_win_pct": float((nr > 0).mean() * 100.0),
        "net_profit_factor": pf(nr),
        "avg_bars": float(g["bars"].mean()),
        "tp1_n": int(len(runners)),
        "tp1_pct": float(len(runners) / len(g) * 100.0) if len(g) else 0.0,
        "runner_exit_r_mean": float(runners["runner_exit_r"].mean()) if len(runners) else None,
        "runner_mfe_r_mean": float(runners["runner_mfe_r"].mean()) if len(runners) else None,
        "runner_giveback_r_mean": float(runners["runner_giveback_r"].mean()) if len(runners) else None,
    }


def paired_boot(diff: pd.Series, seed: int = 260928, reps: int = 20000) -> dict:
    x = diff.dropna().to_numpy(dtype=float)
    if len(x) == 0:
        return {}
    rng = np.random.default_rng(seed)
    vals = np.empty(reps)
    n = len(x)
    for i in range(reps):
        vals[i] = rng.choice(x, size=n, replace=True).mean()
    return {
        "n": int(n), "mean_diff": float(x.mean()),
        "ci95_low": float(np.quantile(vals, 0.025)),
        "ci95_high": float(np.quantile(vals, 0.975)),
        "p_le_zero": float((1 + np.sum(vals <= 0)) / (reps + 1)),
    }


def month_block_boot(diff_df: pd.DataFrame, seed: int = 260929, reps: int = 20000) -> dict:
    if diff_df.empty:
        return {}
    x = diff_df.copy()
    dt = pd.to_datetime(x["entry_time"], utc=True)
    x["month"] = dt.dt.tz_convert("America/New_York").dt.to_period("M").astype(str)
    blocks = []
    for _, g in x.groupby("month"):
        vals = g["diff"].astype(float).to_numpy()
        blocks.append((float(vals.sum()), int(len(vals))))
    if not blocks:
        return {}
    rng = np.random.default_rng(seed)
    vals = np.empty(reps)
    m = len(blocks)
    for i in range(reps):
        idx = rng.integers(0, m, size=m)
        s = sum(blocks[j][0] for j in idx)
        n = sum(blocks[j][1] for j in idx)
        vals[i] = s / n if n else np.nan
    vals = vals[np.isfinite(vals)]
    return {
        "blocks": int(m),
        "ci95_low": float(np.quantile(vals, 0.025)),
        "ci95_high": float(np.quantile(vals, 0.975)),
        "p_le_zero": float((1 + np.sum(vals <= 0)) / (len(vals) + 1)),
    }


def top_removal(g: pd.DataFrame) -> dict:
    x = g.sort_values("net_r", ascending=False)
    out = {}
    for k in [1, 3, 5, 10]:
        y = x.iloc[k:] if len(x) > k else x.iloc[0:0]
        out[str(k)] = {
            "n": int(len(y)),
            "net_expectancy_r": float(y["net_r"].mean()) if len(y) else None,
            "total_net_r": float(y["net_r"].sum()) if len(y) else 0.0,
        }
    return out


def yearly(g: pd.DataFrame) -> list[dict]:
    x = g.copy()
    dt = pd.to_datetime(x["entry_time"], utc=True)
    x["year"] = dt.dt.tz_convert("America/New_York").dt.year
    out = []
    for y, h in x.groupby("year"):
        out.append({"year": int(y), **summarize(h)})
    return out


def main() -> None:
    spy_i = regular_1h(fetch_symbol("SPY", "1h", "729d"))
    spy_h4 = resample_closed_4h(spy_i, "SPY")

    frames = {}
    for k, sym in enumerate(SYMBOLS, 1):
        print(f"[{k}/{len(SYMBOLS)}] {sym}")
        h = prepare_symbol(sym, spy_h4)
        if h is not None:
            frames[sym] = augment_exit_controls(h)
    print("frames", len(frames))

    # Exact baseline accepted entries at 50 bps / existing rs ranking.
    base_summary, _, entries, _ = simulate_ranked(frames, "rs", 50.0)
    entries = entries.copy()
    entries.to_csv(OUT / "baseline_entries.csv", index=False)

    rows = []
    for cost in COSTS:
        for rule in RULES:
            print("FIXED", rule, cost)
            for _, er in entries.iterrows():
                sym = str(er["symbol"])
                if sym not in frames:
                    continue
                rec = simulate_one(er, frames[sym], rule, cost)
                if rec is not None:
                    rows.append(rec)
    trades = pd.DataFrame(rows)
    trades.to_csv(OUT / "fixed_entry_trades.csv", index=False)

    results = {"baseline_entry_summary": base_summary, "rules": {}, "paired_vs_current_50bps": {}}
    for cost in COSTS:
        results["rules"][str(int(cost))] = {}
        for rule in RULES:
            g = trades[(trades["cost_bps"] == cost) & (trades["rule"] == rule)]
            results["rules"][str(int(cost))][rule] = summarize(g)

    current = trades[(trades["cost_bps"] == 50.0) & (trades["rule"] == "current")].copy()
    current = current.set_index(["symbol", "entry_time"]).sort_index()

    for rule in RULES:
        if rule == "current":
            continue
        cand = trades[(trades["cost_bps"] == 50.0) & (trades["rule"] == rule)].copy()
        cand = cand.set_index(["symbol", "entry_time"]).sort_index()
        idx = current.index.intersection(cand.index)
        cur = current.loc[idx]
        can = cand.loc[idx]
        diff = can["net_r"].astype(float) - cur["net_r"].astype(float)
        ddf = pd.DataFrame({
            "symbol": [i[0] for i in idx],
            "entry_time": [i[1] for i in idx],
            "diff": diff.to_numpy(),
        })
        changed = (
            (can["exit_time"].astype(str).to_numpy() != cur["exit_time"].astype(str).to_numpy())
            | (np.abs(diff.to_numpy()) > 1e-12)
        )
        tpidx = idx[(cur.loc[idx, "tp1"].astype(bool) | can.loc[idx, "tp1"].astype(bool)).to_numpy()]
        tpdiff = (
            can.loc[tpidx, "net_r"].astype(float) - cur.loc[tpidx, "net_r"].astype(float)
            if len(tpidx) else pd.Series(dtype=float)
        )
        results["paired_vs_current_50bps"][rule] = {
            "paired_n": int(len(idx)),
            "changed_trades": int(changed.sum()),
            "mean_net_r_diff_all": float(diff.mean()) if len(diff) else None,
            "mean_net_r_diff_tp1": float(tpdiff.mean()) if len(tpdiff) else None,
            "paired_boot_all": paired_boot(diff),
            "paired_boot_tp1": paired_boot(tpdiff, seed=260930),
            "month_block_boot_all": month_block_boot(ddf),
            "candidate_yearly": yearly(can.reset_index()),
            "candidate_top_removal": top_removal(can.reset_index()),
            "current_top_removal": top_removal(cur.reset_index()),
        }

    (OUT / "results.json").write_text(json.dumps(results, indent=2))
    print("HEMA_EXIT_START")
    print(json.dumps(results, indent=2))
    print("HEMA_EXIT_END")


if __name__ == "__main__":
    main()
