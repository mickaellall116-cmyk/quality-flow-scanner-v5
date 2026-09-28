#!/usr/bin/env python3
"""
Pre-registered full-portfolio screen of KAMA20>KAMA40 as a QF filter.

Research-only. Frozen/live Quality Flow remains unchanged.
"""
from __future__ import annotations

import json, math
from pathlib import Path
import numpy as np
import pandas as pd

from research_notes.hema_research import fetch_symbol, regular_1h, resample_closed_4h
from research_notes.hema_qf_portfolio import (
    SYMBOLS, INITIAL_EQUITY, RISK_FRAC, MAX_OPEN, MAX_HEAT,
    Position, cost_dollars, prepare_symbol,
)

OUT = Path("kama_qf_filter")
OUT.mkdir(exist_ok=True)

COSTS = [25.0, 50.0, 75.0, 100.0]
MIN_STOP_PCT = 0.01
MAX_POS_FRAC = 1.0
MAX_GROSS_FRAC = 1.0


def kama(s: pd.Series, er_length: int, fast: int = 2, slow: int = 30) -> pd.Series:
    n = int(er_length)
    change = (s - s.shift(n)).abs()
    volatility = s.diff().abs().rolling(n).sum()
    er = (change / volatility.replace(0.0, np.nan)).fillna(0.0)
    fast_sc = 2.0 / (fast + 1.0)
    slow_sc = 2.0 / (slow + 1.0)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    out = pd.Series(np.nan, index=s.index, dtype=float)
    vals = s.to_numpy(dtype=float)
    scv = sc.to_numpy(dtype=float)
    first = None
    for i, v in enumerate(vals):
        if np.isfinite(v):
            first = i
            out.iloc[i] = v
            break
    if first is None:
        return out
    prev = float(out.iloc[first])
    for i in range(first + 1, len(s)):
        v = vals[i]
        if not np.isfinite(v):
            out.iloc[i] = prev
            continue
        a = scv[i] if np.isfinite(scv[i]) else slow_sc ** 2
        prev = prev + a * (v - prev)
        out.iloc[i] = prev
    return out


def add_kama(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    close = x["Close"].astype(float)
    x["KAMA20"] = kama(close, 20, 2, 30)
    x["KAMA40"] = kama(close, 40, 2, 30)
    x["KAMA_BULL"] = x["KAMA20"] > x["KAMA40"]
    return x


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
            "total_net_r": float(y["net_r"].sum()) if len(y) else 0.0,
            "net_expectancy_r": float(y["net_r"].mean()) if len(y) else None,
            "net_profit_factor": pf(y["net_r"]) if len(y) else None,
        }
    return out


def yearly(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    x = df.copy()
    dt = pd.to_datetime(x["entry_time"], utc=True)
    x["year"] = dt.dt.tz_convert("America/New_York").dt.year
    rows = []
    for y, g in x.groupby("year"):
        nr = g["net_r"].astype(float)
        rows.append({
            "year": int(y),
            "n": int(len(g)),
            "total_net_r": float(nr.sum()),
            "net_expectancy_r": float(nr.mean()),
            "net_profit_factor": pf(nr),
            "win_pct": float((nr > 0).mean() * 100.0),
        })
    return rows


def best_year_removed(df: pd.DataFrame) -> dict:
    ys = yearly(df)
    if not ys:
        return {}
    best = max(ys, key=lambda x: x["total_net_r"])
    x = df.copy()
    dt = pd.to_datetime(x["entry_time"], utc=True)
    years = dt.dt.tz_convert("America/New_York").dt.year
    y = x[years != best["year"]]
    return {
        "best_year": best["year"],
        "best_year_total_net_r": best["total_net_r"],
        "remaining_n": int(len(y)),
        "remaining_expectancy_r": float(y["net_r"].mean()) if len(y) else None,
        "remaining_total_net_r": float(y["net_r"].sum()) if len(y) else 0.0,
    }


def symbol_concentration(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    rows = []
    for sym, g in df.groupby("symbol"):
        rows.append({
            "symbol": sym,
            "n": int(len(g)),
            "total_net_r": float(g["net_r"].sum()),
            "net_expectancy_r": float(g["net_r"].mean()),
        })
    return sorted(rows, key=lambda x: x["total_net_r"], reverse=True)


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


def gross_notional(positions: dict[str, Position], frames: dict[str, pd.DataFrame], ts) -> float:
    total = 0.0
    for sym, p in positions.items():
        df = frames[sym]
        px = p.entry
        if ts in df.index:
            row = df.loc[ts]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[-1]
            px = float(row["Close"])
        qty = p.runner_shares if p.tp1_taken else p.shares
        total += abs(px * qty)
    return float(total)


def simulate(frames: dict[str, pd.DataFrame], cost_bps: float, use_kama_filter: bool):
    equity = INITIAL_EQUITY
    positions: dict[str, Position] = {}
    pending: list[dict] = []
    trades, entries, rejects = [], [], []

    candidates = {}
    raw_qf = 0
    kama_filter_rejects = 0

    for sym, df in frames.items():
        for i in np.flatnonzero(df["qf_event"].fillna(False).to_numpy()):
            if i + 1 >= len(df):
                continue
            raw_qf += 1
            kama_bull = bool(df["KAMA_BULL"].iloc[i])
            if use_kama_filter and not kama_bull:
                kama_filter_rejects += 1
                continue

            raw_rs = df["rs20_spy"].iloc[i]
            rs_valid = bool(np.isfinite(raw_rs))
            rs = float(raw_rs) if rs_valid else None
            candidates.setdefault(df.index[i], []).append({
                "sym": sym, "i": int(i), "rs": rs, "rs_valid": rs_valid,
                "kama_bull": kama_bull,
            })

    timeline = sorted(set().union(*[set(df.index) for df in frames.values()]))
    peak = INITIAL_EQUITY
    max_dd = 0.0
    max_dd_dollars = 0.0
    max_gross_frac_seen = 0.0

    tight_rejects = 0
    gross_rejects = 0
    slot_rejects = 0
    heat_rejects = 0
    pos_cap_binds = 0
    missing_rs_accepted = 0

    for ts in timeline:
        # Fill ranked pending entries in their preserved order.
        still = []
        for pe in pending:
            sym = pe["sym"]
            df = frames[sym]
            ei = pe["entry_i"]
            if df.index[ei] != ts:
                still.append(pe)
                continue
            if sym in positions:
                continue

            marked_before = mark_equity(equity, positions, frames, ts)
            gross_before = gross_notional(positions, frames, ts)
            if marked_before <= 0:
                rejects.append({"time": str(ts), "symbol": sym, "reason": "NONPOSITIVE_EQUITY"})
                continue

            if len(positions) >= MAX_OPEN:
                slot_rejects += 1
                rejects.append({"time": str(ts), "symbol": sym, "reason": "MAX_OPEN"})
                continue

            entry = float(df["Open"].iloc[ei])
            stop = float(pe["stop"])
            tp1 = float(pe["tp1"])
            rps = entry - stop
            if not np.isfinite(rps) or rps <= 0 or entry <= 0:
                rejects.append({"time": str(ts), "symbol": sym, "reason": "INVALID_GEOMETRY"})
                continue

            stop_pct = rps / entry
            if stop_pct + 1e-12 < MIN_STOP_PCT:
                tight_rejects += 1
                rejects.append({
                    "time": str(ts), "symbol": sym, "reason": "MIN_STOP",
                    "entry": entry, "stop": stop, "stop_pct": stop_pct,
                })
                continue

            risk_budget = marked_before * RISK_FRAC
            shares_risk = int(math.floor(risk_budget / rps))
            if shares_risk < 1:
                rejects.append({"time": str(ts), "symbol": sym, "reason": "RISK_BUDGET_LT_1_SHARE"})
                continue

            shares_poscap = int(math.floor((marked_before * MAX_POS_FRAC) / entry))
            remaining_gross = max(0.0, marked_before * MAX_GROSS_FRAC - gross_before)
            shares_gross = int(math.floor(remaining_gross / entry))

            shares = min(shares_risk, shares_poscap, shares_gross)
            if shares_poscap < shares_risk:
                pos_cap_binds += 1
            if shares_gross < min(shares_risk, shares_poscap):
                gross_rejects += 1

            if shares < 1:
                rejects.append({
                    "time": str(ts), "symbol": sym, "reason": "GROSS_EXPOSURE_CAP",
                    "gross_before": gross_before, "marked_equity": marked_before,
                })
                continue

            actual_risk = shares * rps
            heat = sum(p.planned_risk for p in positions.values()) / max(marked_before, 1.0)
            if heat + actual_risk / max(marked_before, 1.0) > MAX_HEAT + 1e-12:
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

            gross_after = gross_before + notional
            max_gross_frac_seen = max(max_gross_frac_seen, gross_after / max(marked_before, 1.0))

            entries.append({
                "symbol": sym,
                "entry_time": str(ts),
                "signal_time": str(pe["signal_time"]),
                "kama_bull": pe["kama_bull"],
                "rs": pe["rs"],
                "rs_valid": pe["rs_valid"],
                "entry_px": entry,
                "stop_px": stop,
                "tp1_px": tp1,
                "stop_pct": stop_pct,
                "shares": shares,
                "risk_budget": risk_budget,
                "planned_risk": actual_risk,
                "entry_notional": notional,
                "marked_equity_before": marked_before,
                "gross_before": gross_before,
                "gross_after": gross_after,
                "gross_after_equity": gross_after / marked_before,
            })
        pending = still

        # Current QF management, realistic gap-through stop handling.
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

            def close_trade(fill: float, qty: int, reason: str, rr: float, blend: float):
                nonlocal equity
                pnl = (fill - p.entry) * qty
                cc = cost_dollars(fill * qty, cost_bps)
                equity += pnl - cc
                net_pnl = p.partial_pnl + pnl - p.entry_cost - p.partial_cost - cc
                trades.append({
                    "symbol": sym,
                    "entry_time": str(p.entry_time),
                    "exit_time": str(ts),
                    "reason": reason,
                    "gross_r": blend,
                    "net_pnl": net_pnl,
                    "net_r": net_pnl / p.planned_risk,
                    "bars": p.bars,
                    "tp1": p.tp1_taken,
                    "entry_px": p.entry,
                    "stop_px": p.stop,
                    "shares": p.shares,
                    "planned_risk": p.planned_risk,
                })

            if p.pending_exit:
                fill = o
                qty = p.runner_shares if p.tp1_taken else p.shares
                rr = (fill - p.entry) / p.risk_per_share
                blend = (0.5*p.partial_r + 0.5*rr) if p.tp1_taken else rr
                close_trade(fill, qty, p.pending_reason, rr, blend)
                to_close.append(sym)
                continue

            if h >= p.entry + p.risk_per_share:
                p.armed = True

            if l <= p.stop:
                fill = o if o < p.stop else p.stop
                qty = p.runner_shares if p.tp1_taken else p.shares
                rr = (fill - p.entry) / p.risk_per_share
                blend = (0.5*p.partial_r + 0.5*rr) if p.tp1_taken else rr
                close_trade(fill, qty, "STOP", rr, blend)
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
                    fill2 = c
                    rr2 = (fill2 - p.entry) / p.risk_per_share
                    blend2 = 0.5*p.partial_r + 0.5*rr2
                    close_trade(fill2, qty2, "TIMEOUT", rr2, blend2)
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
                rr = (c - p.entry) / p.risk_per_share
                blend = (0.5*p.partial_r + 0.5*rr) if p.tp1_taken else rr
                close_trade(c, qty, "TIMEOUT", rr, blend)
                to_close.append(sym)

        for sym in to_close:
            positions.pop(sym, None)

        # Signal-time ranking, missing RS explicit/unrankable and sorted last.
        batch = candidates.get(ts, [])
        if batch:
            batch = [
                x for x in batch
                if x["sym"] not in positions
                and not any(pe["sym"] == x["sym"] for pe in pending)
            ]
            marked_now = mark_equity(equity, positions, frames, ts)
            free = max(0, MAX_OPEN - len(positions) - len(pending))
            heat = sum(p.planned_risk for p in positions.values()) / max(marked_now, 1.0)
            heat_slots = max(0, int(math.floor((MAX_HEAT - heat) / RISK_FRAC + 1e-9)))
            take = min(free, heat_slots, len(batch))
            ranked = sorted(
                batch,
                key=lambda x: (
                    not x["rs_valid"],
                    -(x["rs"] if x["rs"] is not None else -1e100),
                    x["sym"],
                )
            )
            for x in ranked[:take]:
                sym = x["sym"]
                i = x["i"]
                df = frames[sym]
                pending.append({
                    "sym": sym,
                    "entry_i": i + 1,
                    "signal_time": ts,
                    "stop": float(df["qf_stop"].iloc[i]),
                    "tp1": float(df["qf_tp1"].iloc[i]),
                    "rs": x["rs"],
                    "rs_valid": x["rs_valid"],
                    "kama_bull": x["kama_bull"],
                })

        marked = mark_equity(equity, positions, frames, ts)
        gross = gross_notional(positions, frames, ts)
        if marked > 0:
            max_gross_frac_seen = max(max_gross_frac_seen, gross / marked)
        peak = max(peak, marked)
        dd_dollars = peak - marked
        dd_pct = dd_dollars / peak if peak > 0 else 0.0
        max_dd_dollars = max(max_dd_dollars, dd_dollars)
        max_dd = max(max_dd, dd_pct)

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
        "use_kama_filter": use_kama_filter,
        "raw_qf_candidates": raw_qf,
        "kama_filter_rejects": kama_filter_rejects,
        "accepted_entries": int(len(edf)),
        "closed_trades": int(len(tdf)),
        "tight_stop_rejects": tight_rejects,
        "gross_exposure_rejects_or_binds": gross_rejects,
        "single_position_cap_binds": pos_cap_binds,
        "slot_rejects_at_fill": slot_rejects,
        "heat_rejects_at_fill": heat_rejects,
        "missing_rs_accepted": missing_rs_accepted,
        "ending_equity_marked": float(ending),
        "return_pct_marked": float((ending / INITIAL_EQUITY - 1.0) * 100.0),
        "max_marked_dd_pct": float(max_dd * 100.0),
        "max_marked_dd_dollars": float(max_dd_dollars),
        "max_gross_exposure_equity": float(max_gross_frac_seen),
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


def keyset(df: pd.DataFrame) -> set[tuple[str, str]]:
    if df.empty:
        return set()
    return set(zip(df["symbol"].astype(str), df["entry_time"].astype(str)))


def trade_slice(df: pd.DataFrame, keys: set[tuple[str, str]]) -> dict:
    if df.empty or not keys:
        return {"n": 0}
    mask = [(s, t) in keys for s, t in zip(df["symbol"].astype(str), df["entry_time"].astype(str))]
    x = df[pd.Series(mask, index=df.index)]
    if x.empty:
        return {"n": 0}
    return {
        "n": int(len(x)),
        "total_net_r": float(x["net_r"].sum()),
        "net_expectancy_r": float(x["net_r"].mean()),
        "net_profit_factor": pf(x["net_r"]),
    }


def main():
    spy_i = regular_1h(fetch_symbol("SPY", "1h", "729d"))
    spy_h4 = resample_closed_4h(spy_i, "SPY")

    frames = {}
    for k, sym in enumerate(SYMBOLS, 1):
        print(f"[{k}/{len(SYMBOLS)}] {sym}")
        df = prepare_symbol(sym, spy_h4)
        if df is not None:
            frames[sym] = add_kama(df)
    print("frames", len(frames))

    summaries, trades_all, entries_all, rejects_all = [], [], [], []
    result = {}

    for cost in COSTS:
        result[str(int(cost))] = {}
        for label, use_filter in [("baseline", False), ("kama_filter", True)]:
            print("SIM", label, cost)
            s, t, e, r = simulate(frames, cost, use_filter)
            s["variant"] = label
            summaries.append(s)
            if not t.empty:
                t = t.copy(); t["variant"] = label; t["cost_bps"] = cost
                trades_all.append(t)
            if not e.empty:
                e = e.copy(); e["variant"] = label; e["cost_bps"] = cost
                entries_all.append(e)
            if not r.empty:
                r = r.copy(); r["variant"] = label; r["cost_bps"] = cost
                rejects_all.append(r)

            result[str(int(cost))][label] = {
                "summary": s,
                "yearly": yearly(t),
                "top_removal": top_removal(t),
                "best_year_removed": best_year_removed(t),
                "symbol_concentration": symbol_concentration(t),
            }

    # Trade-set comparison at primary 50 bps.
    base_t = next(
        x[(x["variant"] == "baseline") & (x["cost_bps"] == 50.0)]
        for x in trades_all
        if ((x["variant"] == "baseline") & (x["cost_bps"] == 50.0)).any()
    )
    kama_t = next(
        x[(x["variant"] == "kama_filter") & (x["cost_bps"] == 50.0)]
        for x in trades_all
        if ((x["variant"] == "kama_filter") & (x["cost_bps"] == 50.0)).any()
    )
    bk, kk = keyset(base_t), keyset(kama_t)

    payload = {
        "data_note": "30-symbol DST-safe 4H surrogate; not canonical 131-symbol PIT",
        "kama_definition": "KAMA20>KAMA40, ER length equals line length, fast=2, slow=30",
        "risk_rules": {
            "min_stop_pct": MIN_STOP_PCT,
            "max_single_position_equity": MAX_POS_FRAC,
            "max_total_gross_equity": MAX_GROSS_FRAC,
            "risk_frac": RISK_FRAC,
            "max_open": MAX_OPEN,
            "max_heat": MAX_HEAT,
            "realistic_gap_stops": True,
        },
        "results": result,
        "primary_50bps_trade_sets": {
            "baseline_unique": trade_slice(base_t, bk - kk),
            "kama_unique": trade_slice(kama_t, kk - bk),
            "shared_n": int(len(bk & kk)),
        },
    }

    pd.DataFrame(summaries).to_csv(OUT / "summary.csv", index=False)
    if trades_all:
        pd.concat(trades_all, ignore_index=True).to_csv(OUT / "trades.csv", index=False)
    if entries_all:
        pd.concat(entries_all, ignore_index=True).to_csv(OUT / "entries.csv", index=False)
    if rejects_all:
        pd.concat(rejects_all, ignore_index=True).to_csv(OUT / "rejects.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(payload, indent=2))

    print("KAMA_QF_FILTER_START")
    print(json.dumps(payload, indent=2))
    print("KAMA_QF_FILTER_END")


if __name__ == "__main__":
    main()
