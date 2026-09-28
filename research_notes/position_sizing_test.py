#!/usr/bin/env python3
"""
Pre-registered position-sizing risk-constraint test.

Research-only. Uses the DST-safe 30-symbol QF structural-core surrogate and
keeps signal/exit mechanics unchanged while constraining entry sizing.
"""
from __future__ import annotations

import json, math
from pathlib import Path
import numpy as np
import pandas as pd

from research_notes.hema_research import fetch_symbol, regular_1h, resample_closed_4h
from research_notes.hema_qf_portfolio import (
    SYMBOLS, INITIAL_EQUITY, RISK_FRAC, MAX_OPEN, MAX_HEAT,
    ROUND_TRIP_BPS, Position, cost_dollars, prepare_symbol,
)

OUT = Path("position_sizing")
OUT.mkdir(exist_ok=True)

COSTS = [25.0, 50.0, 75.0, 100.0]
SCENARIOS = {
    "RAW": {"max_position_frac": None, "min_stop_pct": 0.0},
    "NO_LEVERAGE_1PCT_STOP": {"max_position_frac": 1.0, "min_stop_pct": 0.01},
    "HALF_BOOK_1PCT_STOP": {"max_position_frac": 0.5, "min_stop_pct": 0.01},
    "NO_LEVERAGE_2PCT_STOP": {"max_position_frac": 1.0, "min_stop_pct": 0.02},
}


def pf(vals: pd.Series) -> float | None:
    x = vals.dropna().astype(float)
    w = x[x > 0]
    l = x[x <= 0]
    if len(l) == 0 or float(l.sum()) == 0:
        return None
    v = float(w.sum() / abs(l.sum()))
    return v if np.isfinite(v) else None


def top_removal(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    x = df.sort_values("net_r", ascending=False)
    out = {}
    for k in [1, 3, 5, 10]:
        y = x.iloc[k:] if len(x) > k else x.iloc[0:0]
        out[str(k)] = {
            "n": int(len(y)),
            "net_expectancy_r": float(y["net_r"].mean()) if len(y) else None,
            "total_net_r": float(y["net_r"].sum()) if len(y) else 0.0,
            "net_profit_factor": pf(y["net_r"]) if len(y) else None,
        }
    return out


def yearly(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    x = df.copy()
    dt = pd.to_datetime(x["entry_time"], utc=True)
    x["year"] = dt.dt.tz_convert("America/New_York").dt.year
    out = []
    for y, g in x.groupby("year"):
        nr = g["net_r"].astype(float)
        out.append({
            "year": int(y), "n": int(len(g)),
            "total_net_r": float(nr.sum()),
            "net_expectancy_r": float(nr.mean()),
            "net_profit_factor": pf(nr),
            "win_pct": float((nr > 0).mean() * 100.0),
        })
    return out


def mark_equity(equity: float, positions: dict[str, Position], frames: dict[str, pd.DataFrame], ts) -> float:
    mark = float(equity)
    for sym, p in positions.items():
        df = frames[sym]
        if ts not in df.index:
            continue
        row = df.loc[ts]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[-1]
        px = float(row["Close"])
        qty = p.runner_shares if p.tp1_taken else p.shares
        mark += (px - p.entry) * qty
    return mark


def simulate(
    frames: dict[str, pd.DataFrame],
    cost_bps: float,
    max_position_frac: float | None,
    min_stop_pct: float,
) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    equity = INITIAL_EQUITY
    positions: dict[str, Position] = {}
    pending_entries: list[dict] = []
    trades: list[dict] = []
    entries: list[dict] = []
    rejects: list[dict] = []

    candidates = {}
    for sym, df in frames.items():
        q = df["qf_event"].fillna(False).to_numpy()
        for i in np.flatnonzero(q):
            if i + 1 >= len(df):
                continue
            raw_rs = df["rs20_spy"].iloc[i]
            rs_valid = bool(np.isfinite(raw_rs))
            rs = float(raw_rs) if rs_valid else -999.0
            candidates.setdefault(df.index[i], []).append({
                "sym": sym, "i": int(i), "rs": rs, "rs_valid": rs_valid
            })

    timeline = sorted(set().union(*[set(df.index) for df in frames.values()]))
    peak = INITIAL_EQUITY
    max_dd_pct = 0.0
    max_dd_dollars = 0.0
    cap_binds = 0
    tight_rejects = 0
    missing_rs_accepted = 0
    slot_rejects = 0
    heat_rejects = 0

    for ts in timeline:
        # Fill scheduled entries at the next actual 4H bar open.
        still = []
        for pe in pending_entries:
            sym = pe["sym"]
            df = frames[sym]
            ei = pe["entry_i"]
            if df.index[ei] != ts:
                still.append(pe)
                continue
            if sym in positions:
                continue

            entry = float(df["Open"].iloc[ei])
            stop = float(pe["stop"])
            tp1 = float(pe["tp1"])
            rps = entry - stop
            if not np.isfinite(rps) or rps <= 0 or entry <= 0:
                rejects.append({"time": str(ts), "symbol": sym, "reason": "INVALID_GEOMETRY"})
                continue
            stop_pct = rps / entry
            if stop_pct + 1e-12 < min_stop_pct:
                tight_rejects += 1
                rejects.append({
                    "time": str(ts), "symbol": sym, "reason": "MIN_STOP",
                    "entry": entry, "stop": stop, "stop_pct": stop_pct,
                })
                continue

            risk_budget = equity * RISK_FRAC
            shares_risk = int(math.floor(risk_budget / rps))
            if shares_risk < 1:
                rejects.append({"time": str(ts), "symbol": sym, "reason": "RISK_BUDGET_LT_1_SHARE"})
                continue
            shares = shares_risk
            if max_position_frac is not None:
                shares_cap = int(math.floor((equity * max_position_frac) / entry))
                if shares_cap < shares:
                    shares = shares_cap
                    cap_binds += 1
            if shares < 1:
                rejects.append({"time": str(ts), "symbol": sym, "reason": "POSITION_CAP_LT_1_SHARE"})
                continue

            actual_risk = shares * rps
            heat = sum(p.planned_risk for p in positions.values()) / max(equity, 1.0)
            if len(positions) >= MAX_OPEN:
                slot_rejects += 1
                rejects.append({"time": str(ts), "symbol": sym, "reason": "MAX_OPEN"})
                continue
            if heat + actual_risk / max(equity, 1.0) > MAX_HEAT + 1e-12:
                heat_rejects += 1
                rejects.append({"time": str(ts), "symbol": sym, "reason": "MAX_HEAT"})
                continue

            notional = shares * entry
            ecost = cost_dollars(notional, cost_bps)
            equity -= ecost
            positions[sym] = Position(
                sym=sym, entry_i=ei, entry_time=ts, entry=entry, stop=stop, tp1=tp1,
                shares=shares, risk_per_share=rps, planned_risk=actual_risk,
                tp1_taken=False, runner_shares=shares, partial_r=0.0,
                armed=False, pending_exit=False, pending_reason="", bars=0,
                entry_cost=ecost, partial_pnl=0.0, partial_cost=0.0,
            )
            if not pe["rs_valid"]:
                missing_rs_accepted += 1
            entries.append({
                "symbol": sym, "entry_time": str(ts), "signal_time": str(pe["signal_time"]),
                "rs": pe["rs"], "rs_valid": pe["rs_valid"],
                "entry_px": entry, "stop_px": stop, "tp1_px": tp1,
                "stop_pct": stop_pct, "shares": shares,
                "risk_budget": risk_budget, "planned_risk": actual_risk,
                "entry_notional": notional, "book_equity": equity + ecost,
                "notional_equity": notional / max(equity + ecost, 1e-12),
                "risk_budget_used_pct": actual_risk / max(risk_budget, 1e-12) * 100.0,
            })
        pending_entries = still

        # Existing current QF trade management.
        to_close = []
        for sym, p in list(positions.items()):
            df = frames[sym]
            if ts not in df.index:
                continue
            j = df.index.get_loc(ts)
            if isinstance(j, slice) or isinstance(j, np.ndarray) or j < p.entry_i:
                continue
            row = df.iloc[j]
            o, h, l, c = map(float, [row.Open, row.High, row.Low, row.Close])
            p.bars += 1

            if p.pending_exit:
                fill = o
                qty = p.runner_shares if p.tp1_taken else p.shares
                pnl = (fill - p.entry) * qty
                cc = cost_dollars(fill * qty, cost_bps)
                equity += pnl - cc
                rr = (fill - p.entry) / p.risk_per_share
                blend = (0.5*p.partial_r + 0.5*rr) if p.tp1_taken else rr
                net_pnl = p.partial_pnl + pnl - p.entry_cost - p.partial_cost - cc
                trades.append({
                    "symbol": sym, "entry_time": str(p.entry_time), "exit_time": str(ts),
                    "reason": p.pending_reason, "gross_r": blend,
                    "net_pnl": net_pnl, "net_r": net_pnl / p.planned_risk,
                    "bars": p.bars, "tp1": p.tp1_taken,
                    "entry_px": p.entry, "stop_px": p.stop,
                    "stop_pct": p.risk_per_share / p.entry,
                    "shares": p.shares, "planned_risk": p.planned_risk,
                    "entry_notional": p.entry * p.shares,
                })
                to_close.append(sym)
                continue

            if h >= p.entry + p.risk_per_share:
                p.armed = True

            if l <= p.stop:
                fill = o if o < p.stop else p.stop
                qty = p.runner_shares if p.tp1_taken else p.shares
                pnl = (fill - p.entry) * qty
                cc = cost_dollars(fill * qty, cost_bps)
                equity += pnl - cc
                rr = (fill - p.entry) / p.risk_per_share
                blend = (0.5*p.partial_r + 0.5*rr) if p.tp1_taken else rr
                net_pnl = p.partial_pnl + pnl - p.entry_cost - p.partial_cost - cc
                trades.append({
                    "symbol": sym, "entry_time": str(p.entry_time), "exit_time": str(ts),
                    "reason": "STOP", "gross_r": blend,
                    "net_pnl": net_pnl, "net_r": net_pnl / p.planned_risk,
                    "bars": p.bars, "tp1": p.tp1_taken,
                    "entry_px": p.entry, "stop_px": p.stop,
                    "stop_pct": p.risk_per_share / p.entry,
                    "shares": p.shares, "planned_risk": p.planned_risk,
                    "entry_notional": p.entry * p.shares,
                })
                to_close.append(sym)
                continue

            if not p.tp1_taken and h >= p.tp1:
                fill = o if o > p.tp1 else p.tp1
                qty = max(1, p.shares // 2)
                pnl = (fill - p.entry) * qty
                cc = cost_dollars(fill * qty, cost_bps)
                equity += pnl - cc
                p.partial_r = (fill - p.entry) / p.risk_per_share
                p.partial_pnl += pnl
                p.partial_cost += cc
                p.tp1_taken = True
                p.runner_shares = p.shares - qty
                if p.bars >= 30:
                    qty2 = p.runner_shares
                    pnl2 = (c - p.entry) * qty2
                    cc2 = cost_dollars(c * qty2, cost_bps)
                    equity += pnl2 - cc2
                    rr = (c - p.entry) / p.risk_per_share
                    blend = 0.5*p.partial_r + 0.5*rr
                    net_pnl = p.partial_pnl + pnl2 - p.entry_cost - p.partial_cost - cc2
                    trades.append({
                        "symbol": sym, "entry_time": str(p.entry_time), "exit_time": str(ts),
                        "reason": "TIMEOUT", "gross_r": blend,
                        "net_pnl": net_pnl, "net_r": net_pnl / p.planned_risk,
                        "bars": p.bars, "tp1": True,
                        "entry_px": p.entry, "stop_px": p.stop,
                        "stop_pct": p.risk_per_share / p.entry,
                        "shares": p.shares, "planned_risk": p.planned_risk,
                        "entry_notional": p.entry * p.shares,
                    })
                    to_close.append(sym)
                continue

            if not p.tp1_taken:
                if p.armed and bool(row["scanner_exit"]):
                    p.pending_exit = True
                    p.pending_reason = "PP_PRE_TP1"
            else:
                if p.armed and bool(row["scanner_exit"]):
                    p.pending_exit = True
                    p.pending_reason = "CURRENT_RUNNER_EXIT"

            if p.bars >= 30:
                qty = p.runner_shares if p.tp1_taken else p.shares
                pnl = (c - p.entry) * qty
                cc = cost_dollars(c * qty, cost_bps)
                equity += pnl - cc
                rr = (c - p.entry) / p.risk_per_share
                blend = (0.5*p.partial_r + 0.5*rr) if p.tp1_taken else rr
                net_pnl = p.partial_pnl + pnl - p.entry_cost - p.partial_cost - cc
                trades.append({
                    "symbol": sym, "entry_time": str(p.entry_time), "exit_time": str(ts),
                    "reason": "TIMEOUT", "gross_r": blend,
                    "net_pnl": net_pnl, "net_r": net_pnl / p.planned_risk,
                    "bars": p.bars, "tp1": p.tp1_taken,
                    "entry_px": p.entry, "stop_px": p.stop,
                    "stop_pct": p.risk_per_share / p.entry,
                    "shares": p.shares, "planned_risk": p.planned_risk,
                    "entry_notional": p.entry * p.shares,
                })
                to_close.append(sym)

        for sym in to_close:
            positions.pop(sym, None)

        # Existing rs ranking. Missing values sort last exactly as documented.
        batch = candidates.get(ts, [])
        if batch:
            batch = [
                x for x in batch
                if x["sym"] not in positions
                and not any(pe["sym"] == x["sym"] for pe in pending_entries)
            ]
            free = max(0, MAX_OPEN - len(positions) - len(pending_entries))
            heat = sum(p.planned_risk for p in positions.values()) / max(equity, 1.0)
            # Keep the original conservative 1%-risk reservation at signal time.
            heat_slots = max(0, int(math.floor((MAX_HEAT - heat) / RISK_FRAC + 1e-9)))
            take = min(free, heat_slots, len(batch))
            ranked = sorted(batch, key=lambda x: (not x["rs_valid"], -x["rs"], x["sym"]))
            accepted = ranked[:take]
            for x in accepted:
                sym = x["sym"]
                i = x["i"]
                df = frames[sym]
                pending_entries.append({
                    "sym": sym, "entry_i": i + 1, "signal_time": ts,
                    "stop": float(df["qf_stop"].iloc[i]),
                    "tp1": float(df["qf_tp1"].iloc[i]),
                    "rs": x["rs"], "rs_valid": x["rs_valid"],
                })

        marked = mark_equity(equity, positions, frames, ts)
        peak = max(peak, marked)
        dd_dollars = peak - marked
        dd_pct = dd_dollars / peak if peak > 0 else 0.0
        max_dd_dollars = max(max_dd_dollars, dd_dollars)
        max_dd_pct = max(max_dd_pct, dd_pct)

    open_mark = 0.0
    for sym, p in positions.items():
        last = float(frames[sym]["Close"].iloc[-1])
        qty = p.runner_shares if p.tp1_taken else p.shares
        open_mark += (last - p.entry) * qty
    ending = equity + open_mark

    tdf = pd.DataFrame(trades)
    edf = pd.DataFrame(entries)
    rdf = pd.DataFrame(rejects)

    s = {
        "cost_bps": cost_bps,
        "max_position_frac": max_position_frac,
        "min_stop_pct": min_stop_pct,
        "accepted_entries": int(len(edf)),
        "closed_trades": int(len(tdf)),
        "tight_stop_rejects": int(tight_rejects),
        "cap_binds": int(cap_binds),
        "missing_rs_accepted": int(missing_rs_accepted),
        "slot_rejects_at_fill": int(slot_rejects),
        "heat_rejects_at_fill": int(heat_rejects),
        "ending_equity_marked": float(ending),
        "return_pct_marked": float((ending / INITIAL_EQUITY - 1.0) * 100.0),
        "max_marked_dd_pct": float(max_dd_pct * 100.0),
        "max_marked_dd_dollars": float(max_dd_dollars),
        "open_positions": int(len(positions)),
    }
    if not tdf.empty:
        nr = tdf["net_r"].astype(float)
        s.update({
            "total_net_r": float(nr.sum()),
            "net_expectancy_r": float(nr.mean()),
            "net_profit_factor": pf(nr),
            "win_pct": float((nr > 0).mean() * 100.0),
            "realized_net_pnl": float(tdf["net_pnl"].sum()),
        })
    return s, tdf, edf, rdf


def without_apld(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    x = df.copy()
    mask = ~(
        (x["symbol"].astype(str) == "APLD")
        & x["entry_time"].astype(str).str.startswith("2024-01-03")
    )
    y = x[mask]
    nr = y["net_r"].astype(float)
    return {
        "n": int(len(y)), "total_net_r": float(nr.sum()),
        "net_expectancy_r": float(nr.mean()) if len(y) else None,
        "net_profit_factor": pf(nr) if len(y) else None,
    }


def entry_diag(edf: pd.DataFrame) -> dict:
    if edf.empty:
        return {}
    lev = edf["notional_equity"].astype(float)
    sp = edf["stop_pct"].astype(float) * 100.0
    return {
        "max_notional_equity": float(lev.max()),
        "p95_notional_equity": float(lev.quantile(0.95)),
        "count_gt_1x": int((lev > 1.0 + 1e-9).sum()),
        "count_gt_0_5x": int((lev > 0.5 + 1e-9).sum()),
        "min_stop_pct_points": float(sp.min()),
        "p05_stop_pct_points": float(sp.quantile(0.05)),
        "median_stop_pct_points": float(sp.median()),
        "mean_risk_budget_used_pct": float(edf["risk_budget_used_pct"].mean()),
    }


def main() -> None:
    spy_i = regular_1h(fetch_symbol("SPY", "1h", "729d"))
    spy_h4 = resample_closed_4h(spy_i, "SPY")

    frames = {}
    for k, sym in enumerate(SYMBOLS, 1):
        print(f"[{k}/{len(SYMBOLS)}] {sym}")
        h = prepare_symbol(sym, spy_h4)
        if h is not None:
            frames[sym] = h
    print("frames", len(frames))

    summaries = []
    trades_all = []
    entries_all = []
    rejects_all = []
    results = {}

    for name, cfg in SCENARIOS.items():
        results[name] = {}
        for cost in COSTS:
            print("RUN", name, cost)
            s, t, e, r = simulate(
                frames, cost,
                cfg["max_position_frac"],
                cfg["min_stop_pct"],
            )
            s["scenario"] = name
            summaries.append(s)
            if not t.empty:
                t = t.copy(); t["scenario"] = name; t["cost_bps"] = cost
                trades_all.append(t)
            if not e.empty:
                e = e.copy(); e["scenario"] = name; e["cost_bps"] = cost
                entries_all.append(e)
            if not r.empty:
                r = r.copy(); r["scenario"] = name; r["cost_bps"] = cost
                rejects_all.append(r)

            results[name][str(int(cost))] = {
                "summary": s,
                "yearly": yearly(t),
                "top_removal": top_removal(t),
                "without_apld_2024_01_03": without_apld(t),
                "entry_diagnostics": entry_diag(e),
            }

    pd.DataFrame(summaries).to_csv(OUT / "summary.csv", index=False)
    if trades_all:
        pd.concat(trades_all, ignore_index=True).to_csv(OUT / "trades.csv", index=False)
    if entries_all:
        pd.concat(entries_all, ignore_index=True).to_csv(OUT / "entries.csv", index=False)
    if rejects_all:
        pd.concat(rejects_all, ignore_index=True).to_csv(OUT / "rejects.csv", index=False)

    payload = {
        "data_note": "30-symbol DST-safe recent-history structural-core surrogate; not canonical 131-symbol PIT",
        "primary": "NO_LEVERAGE_1PCT_STOP",
        "scenario_definitions": SCENARIOS,
        "results": results,
    }
    (OUT / "results.json").write_text(json.dumps(payload, indent=2))
    print("POSITION_SIZING_START")
    print(json.dumps(payload, indent=2))
    print("POSITION_SIZING_END")


if __name__ == "__main__":
    main()
