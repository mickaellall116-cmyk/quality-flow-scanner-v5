#!/usr/bin/env python3
"""
Pre-registered HEMA slot-ranking test.

Research-only. Does not change live/frozen Quality Flow logic.

Candidate rule (frozen before this script was added):
- baseline: rs20_spy descending
- HEMA: recent_big_green_4 preferred, then rs20_spy
- EMA control: ema20_40_bull preferred, then rs20_spy
- matched random: preserve the count of HEMA-preferred candidates in each
  decision batch, but randomly assign that preference within the batch.

HEMA never gates a valid QF setup. It can only reorder candidates when actual
slot/heat pressure means not every candidate can be accepted.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from research_notes.hema_research import fetch_symbol, regular_1h, resample_closed_4h
from research_notes.hema_qf_portfolio import (
    SYMBOLS, INITIAL_EQUITY, RISK_FRAC, MAX_OPEN, MAX_HEAT,
    ROUND_TRIP_BPS, Position, cost_dollars, prepare_symbol,
)

OUT = Path("hema_ranking")
OUT.mkdir(exist_ok=True)

COSTS = [25.0, 50.0, 75.0, 100.0]
RANDOM_SEEDS = list(range(200))


def pf(vals: pd.Series) -> float | None:
    vals = vals.astype(float)
    w = vals[vals > 0]
    l = vals[vals <= 0]
    if len(l) == 0 or float(l.sum()) == 0:
        return None
    v = float(w.sum() / abs(l.sum()))
    return v if np.isfinite(v) else None


def stable_rng(seed: int, ts: object) -> np.random.Generator:
    raw = hashlib.sha256(f"{seed}|{ts}".encode()).digest()[:8]
    n = int.from_bytes(raw, "little", signed=False)
    return np.random.default_rng(n)


def rank_batch(batch: list[dict], mode: str, ts: object, seed: int | None = None) -> list[dict]:
    b = [dict(x) for x in batch]
    if mode == "rs":
        return sorted(b, key=lambda x: (-x["rs"], x["sym"]))
    if mode == "hema":
        return sorted(b, key=lambda x: (-int(x["hema_pref"]), -x["rs"], x["sym"]))
    if mode == "ema":
        return sorted(b, key=lambda x: (-int(x["ema_pref"]), -x["rs"], x["sym"]))
    if mode == "random":
        if seed is None:
            raise ValueError("random mode requires seed")
        k = int(sum(int(x["hema_pref"]) for x in b))
        chosen: set[int] = set()
        if k > 0 and len(b) > 0:
            rng = stable_rng(seed, ts)
            chosen = set(map(int, rng.choice(len(b), size=min(k, len(b)), replace=False)))
        for i, x in enumerate(b):
            x["random_pref"] = i in chosen
        return sorted(b, key=lambda x: (-int(x["random_pref"]), -x["rs"], x["sym"]))
    raise KeyError(mode)


def mark_equity(equity: float, positions: dict[str, Position], frames: dict[str, pd.DataFrame], ts: object) -> float:
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


def simulate_ranked(
    frames: dict[str, pd.DataFrame],
    rank_mode: str,
    cost_bps: float = ROUND_TRIP_BPS,
    seed: int | None = None,
) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    equity = INITIAL_EQUITY
    positions: dict[str, Position] = {}
    trades: list[dict] = []
    entries: list[dict] = []
    decisions: list[dict] = []
    pending_entries: list[dict] = []

    timeline = sorted(set().union(*[set(df.index) for df in frames.values()]))

    candidates: dict[object, list[dict]] = {}
    for sym, df in frames.items():
        q = df["qf_event"].fillna(False).to_numpy()
        for i in np.flatnonzero(q):
            if i + 1 >= len(df):
                continue
            rs = float(df["rs20_spy"].iloc[i]) if np.isfinite(df["rs20_spy"].iloc[i]) else -999.0
            candidates.setdefault(df.index[i], []).append({
                "sym": sym,
                "i": int(i),
                "rs": rs,
                "hema_pref": bool(df["recent_big_green_4"].iloc[i]),
                "ema_pref": bool(df["ema20_40_bull"].iloc[i]),
            })

    peak = INITIAL_EQUITY
    max_dd = 0.0
    max_dd_dollars = 0.0
    competitive_decisions = 0
    competitive_candidates = 0
    competitive_ranked_out = 0
    no_capacity_rejects = 0
    total_candidate_batches = 0
    total_candidates_after_busy = 0

    for ts in timeline:
        # 1) Fill previously selected entries at their next actual symbol bar.
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

            planned_risk = equity * RISK_FRAC
            heat = sum(p.planned_risk for p in positions.values()) / max(equity, 1.0)
            if len(positions) >= MAX_OPEN or heat + planned_risk / max(equity, 1.0) > MAX_HEAT + 1e-12:
                continue

            entry = float(df["Open"].iloc[ei])
            stop = float(pe["stop"])
            tp1 = float(pe["tp1"])
            rps = entry - stop
            if not np.isfinite(rps) or rps <= 0 or entry <= 0:
                continue
            shares = max(1, int(math.floor(planned_risk / rps)))
            notional = shares * entry
            ecost = cost_dollars(notional, cost_bps)
            equity -= ecost
            p = Position(
                sym=sym, entry_i=ei, entry_time=ts, entry=entry, stop=stop, tp1=tp1,
                shares=shares, risk_per_share=rps, planned_risk=shares*rps,
                tp1_taken=False, runner_shares=shares, partial_r=0.0, armed=False,
                pending_exit=False, pending_reason="", bars=0, entry_cost=ecost,
                partial_pnl=0.0, partial_cost=0.0,
            )
            positions[sym] = p
            entries.append({
                "symbol": sym, "entry_time": str(ts), "rank_mode": rank_mode,
                "cost_bps": cost_bps, "seed": seed,
                "signal_time": str(pe["signal_time"]), "rs": pe["rs"],
                "hema_pref": pe["hema_pref"], "ema_pref": pe["ema_pref"],
                "entry_px": entry, "stop_px": stop, "tp1_px": tp1,
                "shares": shares, "planned_risk": p.planned_risk,
                "entry_notional": notional,
                "entry_book": planned_risk / RISK_FRAC,
                "entry_notional_book": notional / max(planned_risk / RISK_FRAC, 1e-12),
            })
        pending_entries = still

        # 2) Manage open positions with the unchanged current exit logic.
        to_close: list[str] = []
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
                    "rank_mode": rank_mode, "cost_bps": cost_bps, "seed": seed,
                    "reason": p.pending_reason, "gross_r": blend,
                    "net_pnl": net_pnl, "net_r": net_pnl / p.planned_risk,
                    "bars": p.bars, "tp1": p.tp1_taken,
                    "entry_px": p.entry, "stop_px": p.stop, "tp1_px": p.tp1,
                    "shares": p.shares, "planned_risk": p.planned_risk,
                    "entry_notional_book": (p.entry*p.shares) / max(p.planned_risk/RISK_FRAC, 1e-12),
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
                    "rank_mode": rank_mode, "cost_bps": cost_bps, "seed": seed,
                    "reason": "STOP", "gross_r": blend,
                    "net_pnl": net_pnl, "net_r": net_pnl / p.planned_risk,
                    "bars": p.bars, "tp1": p.tp1_taken,
                    "entry_px": p.entry, "stop_px": p.stop, "tp1_px": p.tp1,
                    "shares": p.shares, "planned_risk": p.planned_risk,
                    "entry_notional_book": (p.entry*p.shares) / max(p.planned_risk/RISK_FRAC, 1e-12),
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
                        "rank_mode": rank_mode, "cost_bps": cost_bps, "seed": seed,
                        "reason": "TIMEOUT", "gross_r": blend,
                        "net_pnl": net_pnl, "net_r": net_pnl / p.planned_risk,
                        "bars": p.bars, "tp1": True,
                        "entry_px": p.entry, "stop_px": p.stop, "tp1_px": p.tp1,
                        "shares": p.shares, "planned_risk": p.planned_risk,
                        "entry_notional_book": (p.entry*p.shares) / max(p.planned_risk/RISK_FRAC, 1e-12),
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
                    "rank_mode": rank_mode, "cost_bps": cost_bps, "seed": seed,
                    "reason": "TIMEOUT", "gross_r": blend,
                    "net_pnl": net_pnl, "net_r": net_pnl / p.planned_risk,
                    "bars": p.bars, "tp1": p.tp1_taken,
                    "entry_px": p.entry, "stop_px": p.stop, "tp1_px": p.tp1,
                    "shares": p.shares, "planned_risk": p.planned_risk,
                    "entry_notional_book": (p.entry*p.shares) / max(p.planned_risk/RISK_FRAC, 1e-12),
                })
                to_close.append(sym)

        for sym in to_close:
            positions.pop(sym, None)

        # 3) Rank QF signals only when capacity pressure exists.
        raw_batch = candidates.get(ts, [])
        if raw_batch:
            total_candidate_batches += 1
            batch = [
                x for x in raw_batch
                if x["sym"] not in positions
                and not any(pe["sym"] == x["sym"] for pe in pending_entries)
            ]
            total_candidates_after_busy += len(batch)

            free = max(0, MAX_OPEN - len(positions) - len(pending_entries))
            heat = sum(p.planned_risk for p in positions.values()) / max(equity, 1.0)
            heat_slots = max(0, int(math.floor((MAX_HEAT - heat) / RISK_FRAC + 1e-9)))
            take = min(free, heat_slots, len(batch))

            ranked = rank_batch(batch, rank_mode, ts, seed)
            accepted = ranked[:take]
            rejected = ranked[take:]

            competitive = bool(0 < take < len(batch))
            if competitive:
                competitive_decisions += 1
                competitive_candidates += len(batch)
                competitive_ranked_out += len(rejected)
            elif take == 0:
                no_capacity_rejects += len(batch)

            decisions.append({
                "time": str(ts), "rank_mode": rank_mode, "cost_bps": cost_bps, "seed": seed,
                "candidates": len(batch), "take": take, "competitive": competitive,
                "accepted": ";".join(x["sym"] for x in accepted),
                "rejected": ";".join(x["sym"] for x in rejected),
                "hema_preferred_in_batch": int(sum(int(x["hema_pref"]) for x in batch)),
                "ema_preferred_in_batch": int(sum(int(x["ema_pref"]) for x in batch)),
            })

            for x in accepted:
                sym = x["sym"]
                i = x["i"]
                df = frames[sym]
                if i + 1 >= len(df):
                    continue
                pending_entries.append({
                    "sym": sym, "entry_i": i+1, "signal_time": ts,
                    "stop": float(df["qf_stop"].iloc[i]),
                    "tp1": float(df["qf_tp1"].iloc[i]),
                    "rs": x["rs"], "hema_pref": x["hema_pref"], "ema_pref": x["ema_pref"],
                })

        marked = mark_equity(equity, positions, frames, ts)
        if marked > peak:
            peak = marked
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
    ddf = pd.DataFrame(decisions)

    summary = {
        "rank_mode": rank_mode, "cost_bps": cost_bps, "seed": seed,
        "candidate_batches": total_candidate_batches,
        "candidates_after_busy": total_candidates_after_busy,
        "competitive_decisions": competitive_decisions,
        "competitive_candidates": competitive_candidates,
        "competitive_ranked_out": competitive_ranked_out,
        "no_capacity_rejects": no_capacity_rejects,
        "closed_trades": int(len(tdf)),
        "accepted_entries": int(len(edf)),
        "ending_equity_marked": float(ending),
        "return_pct_marked": float((ending / INITIAL_EQUITY - 1.0) * 100.0),
        "max_marked_dd_pct": float(max_dd * 100.0),
        "max_marked_dd_dollars": float(max_dd_dollars),
        "open_positions": int(len(positions)),
    }
    if not tdf.empty:
        nr = tdf["net_r"].astype(float)
        summary.update({
            "total_net_r": float(nr.sum()),
            "net_expectancy_r": float(nr.mean()),
            "net_median_r": float(nr.median()),
            "net_win_pct": float((nr > 0).mean() * 100.0),
            "net_profit_factor": pf(nr),
        })
    return summary, tdf, edf, ddf


def yearly_stats(tdf: pd.DataFrame) -> list[dict]:
    if tdf.empty:
        return []
    x = tdf.copy()
    dt = pd.to_datetime(x["entry_time"], utc=True)
    x["year"] = dt.dt.tz_convert("America/New_York").dt.year
    out = []
    for y, g in x.groupby("year"):
        nr = g["net_r"].astype(float)
        out.append({
            "year": int(y), "n": int(len(g)), "total_net_r": float(nr.sum()),
            "net_expectancy_r": float(nr.mean()), "net_profit_factor": pf(nr),
        })
    return out


def top_removal(tdf: pd.DataFrame) -> dict:
    if tdf.empty:
        return {}
    x = tdf.sort_values("net_r", ascending=False)
    out = {}
    for k in [1, 3, 5, 10]:
        y = x.iloc[k:] if len(x) > k else x.iloc[0:0]
        out[str(k)] = {
            "n": int(len(y)),
            "net_expectancy_r": float(y["net_r"].mean()) if len(y) else None,
            "total_net_r": float(y["net_r"].sum()) if len(y) else 0.0,
        }
    return out


def leverage_diag(tdf: pd.DataFrame) -> dict:
    if tdf.empty:
        return {}
    x = tdf.copy()
    lev = x["entry_notional_book"].astype(float)
    out = {
        "median": float(lev.median()),
        "p95": float(lev.quantile(0.95)),
        "max": float(lev.max()),
        "count_gt_1x": int((lev > 1.0).sum()),
        "count_gt_2x": int((lev > 2.0).sum()),
    }
    for th in [1.0, 2.0]:
        y = x[lev <= th]
        out[f"le_{th:g}x"] = {
            "n": int(len(y)),
            "net_expectancy_r": float(y["net_r"].mean()) if len(y) else None,
            "total_net_r": float(y["net_r"].sum()) if len(y) else 0.0,
            "net_profit_factor": pf(y["net_r"]) if len(y) else None,
        }
    return out


def keyset(df: pd.DataFrame) -> set[tuple[str, str]]:
    if df.empty:
        return set()
    return set(zip(df["symbol"].astype(str), df["entry_time"].astype(str)))


def main() -> None:
    spy_i = regular_1h(fetch_symbol("SPY", "1h", "729d"))
    spy_h4 = resample_closed_4h(spy_i, "SPY")
    frames: dict[str, pd.DataFrame] = {}
    for k, sym in enumerate(SYMBOLS, 1):
        print(f"[{k}/{len(SYMBOLS)}] {sym}")
        df = prepare_symbol(sym, spy_h4)
        if df is not None:
            frames[sym] = df
    print("frames", len(frames))

    summaries = []
    all_trades = []
    all_entries = []
    all_decisions = []
    main_results: dict[str, dict] = {}

    for bps in COSTS:
        for mode in ["rs", "hema", "ema"]:
            print("SIM", mode, bps)
            s, t, e, d = simulate_ranked(frames, mode, bps)
            summaries.append(s)
            if not t.empty:
                t["test_group"] = "main"
                all_trades.append(t)
            if not e.empty:
                e["test_group"] = "main"
                all_entries.append(e)
            if not d.empty:
                d["test_group"] = "main"
                all_decisions.append(d)
            if bps == 50.0:
                main_results[mode] = {"summary": s, "trades": t, "entries": e, "decisions": d}

    random_rows = []
    for seed in RANDOM_SEEDS:
        s, _, _, _ = simulate_ranked(frames, "random", 50.0, seed=seed)
        random_rows.append(s)
        if seed % 25 == 0:
            print("RANDOM", seed)

    rdf = pd.DataFrame(random_rows)
    sdf = pd.DataFrame(summaries)
    tdf = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    edf = pd.concat(all_entries, ignore_index=True) if all_entries else pd.DataFrame()
    ddf = pd.concat(all_decisions, ignore_index=True) if all_decisions else pd.DataFrame()

    baseline = main_results["rs"]
    hema = main_results["hema"]
    ema = main_results["ema"]

    bkeys = keyset(baseline["trades"])
    hkeys = keyset(hema["trades"])
    hin = hkeys - bkeys
    bout = bkeys - hkeys

    h_in_df = hema["trades"][
        list(zip(hema["trades"]["symbol"].astype(str), hema["trades"]["entry_time"].astype(str)))
        and pd.Series(
            [k in hin for k in zip(hema["trades"]["symbol"].astype(str), hema["trades"]["entry_time"].astype(str))],
            index=hema["trades"].index,
        )
    ] if not hema["trades"].empty else pd.DataFrame()
    b_out_df = baseline["trades"][
        pd.Series(
            [k in bout for k in zip(baseline["trades"]["symbol"].astype(str), baseline["trades"]["entry_time"].astype(str))],
            index=baseline["trades"].index,
        )
    ] if not baseline["trades"].empty else pd.DataFrame()

    # Pressure-decision accepted-set agreement between baseline and HEMA.
    bd = baseline["decisions"]
    hd = hema["decisions"]
    pressure_compare = []
    if not bd.empty and not hd.empty:
        bmap = {r["time"]: r for _, r in bd[bd["competitive"] == True].iterrows()}
        hmap = {r["time"]: r for _, r in hd[hd["competitive"] == True].iterrows()}
        for ts in sorted(set(bmap) & set(hmap)):
            bs = set(filter(None, str(bmap[ts]["accepted"]).split(";")))
            hs = set(filter(None, str(hmap[ts]["accepted"]).split(";")))
            pressure_compare.append({
                "time": ts, "baseline": ";".join(sorted(bs)), "hema": ";".join(sorted(hs)),
                "same_set": bs == hs, "overlap": len(bs & hs),
                "baseline_n": len(bs), "hema_n": len(hs),
            })
    pcdf = pd.DataFrame(pressure_compare)

    random_summary = {}
    if not rdf.empty:
        hsum = hema["summary"]
        for metric in ["total_net_r", "net_expectancy_r", "return_pct_marked", "max_marked_dd_pct"]:
            vals = rdf[metric].dropna().astype(float)
            if len(vals):
                hv = float(hsum.get(metric, np.nan))
                if metric == "max_marked_dd_pct":
                    p = (1 + int((vals <= hv).sum())) / (len(vals) + 1)
                else:
                    p = (1 + int((vals >= hv).sum())) / (len(vals) + 1)
                random_summary[metric] = {
                    "hema": hv, "random_mean": float(vals.mean()),
                    "random_p2_5": float(vals.quantile(0.025)),
                    "random_p50": float(vals.quantile(0.5)),
                    "random_p97_5": float(vals.quantile(0.975)),
                    "one_sided_p": float(p),
                }

    def trade_slice_stats(x: pd.DataFrame) -> dict:
        if x is None or x.empty:
            return {"n": 0}
        nr = x["net_r"].astype(float)
        return {
            "n": int(len(x)), "total_net_r": float(nr.sum()),
            "net_expectancy_r": float(nr.mean()), "net_profit_factor": pf(nr),
        }

    payload = {
        "data_note": "30-symbol recent-history structural-core surrogate; not canonical 131-symbol V5.4",
        "preregistered_hema_rule": "recent_big_green_4 priority, then unchanged rs20_spy; no gating",
        "symbols": list(frames),
        "main_50bps": {
            mode: {
                "summary": main_results[mode]["summary"],
                "yearly": yearly_stats(main_results[mode]["trades"]),
                "top_removal": top_removal(main_results[mode]["trades"]),
                "leverage": leverage_diag(main_results[mode]["trades"]),
                "contains_apld_2024_01_03": bool(
                    (
                        (main_results[mode]["trades"].get("symbol", pd.Series(dtype=str)) == "APLD")
                        & main_results[mode]["trades"].get("entry_time", pd.Series(dtype=str)).astype(str).str.startswith("2024-01-03")
                    ).any()
                ) if not main_results[mode]["trades"].empty else False,
            }
            for mode in ["rs", "hema", "ema"]
        },
        "slot_pressure": {
            "baseline": {
                k: baseline["summary"][k] for k in [
                    "candidate_batches", "candidates_after_busy", "competitive_decisions",
                    "competitive_candidates", "competitive_ranked_out", "no_capacity_rejects"
                ]
            },
            "pressure_events_compared": int(len(pcdf)),
            "same_accepted_set_pct": float(pcdf["same_set"].mean()*100.0) if len(pcdf) else None,
        },
        "displaced_closed_trades": {
            "hema_unique": trade_slice_stats(h_in_df),
            "baseline_unique": trade_slice_stats(b_out_df),
        },
        "matched_random_200": random_summary,
    }

    sdf.to_csv(OUT / "cost_ladder.csv", index=False)
    rdf.to_csv(OUT / "random_controls_50bps.csv", index=False)
    tdf.to_csv(OUT / "trades.csv", index=False)
    edf.to_csv(OUT / "entries.csv", index=False)
    ddf.to_csv(OUT / "decisions.csv", index=False)
    pcdf.to_csv(OUT / "pressure_overlap.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(payload, indent=2))

    print("HEMA_RANKING_START")
    print(json.dumps(payload, indent=2))
    print("HEMA_RANKING_END")


if __name__ == "__main__":
    main()
