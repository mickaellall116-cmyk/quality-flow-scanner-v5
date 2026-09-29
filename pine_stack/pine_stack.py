"""Combined portfolio-risk stack test on Pine V3.6. Spec: STACK_SPEC.md (frozen).
Final sizing/exposure study. R1/R2/R3 imported as validated; no re-tuning.
Four cases on identical trades: C0 baseline, C1=R1+R2, C2=R1+R3, C3=R1+R2+R3."""
import glob
import json
import os
import sys
import traceback
from collections import defaultdict

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "pine_ranking"))
sys.path.insert(0, os.path.join(HERE, "pine_exposure"))
sys.path.insert(0, os.path.join(HERE, "pine_signal_quality"))
import pine_backtest as pb
from pine_ranking import gen_candidates, compute_features
from pine_signal_quality import load_benchmarks, extend_row
from pine_exposure import SECTOR

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(BASE, "stack_results.json")
OUT_JSON_2022 = os.path.join(BASE, "stack_results_2022.json")

DD_HALT = 0.90    # S4: marked equity <= 90% of peak -> risk halves
DD_RESUME = 0.95  # S4: marked equity >= 95% of peak -> risk restores
SECTOR_2022 = dict(SECTOR)
SECTOR_2022.update({"COST": "STAPLES", "WMT": "STAPLES", "JPM": "BANKS",  # as in exposure validation
                    "LLY": "HEALTHCARE", "QQQ": "ETF", "XOM": "ENERGY",
                    # 2026-09-20: ORCL missing from map; corrected trendScore
                    # generated a 2022 ORCL candidate -> KeyError. Classified
                    # as in pine_exposure_validate.py ("AI_SOFTWARE"), not a
                    # strategy/parameter change.
                    "ORCL": "AI_SOFTWARE"})  # 2022-only symbols


def simulate_stack(all_trades, closes, cost, use_ranking, sector_cap, dd_gate,
                   sector_map, diag=None):
    """One event-driven sim for all four cases. Mirrors pine_exposure_stacked's
    run_stacked (bug-fixed) + the S4 risk gate from pine_sizing."""
    def mark(sym, t):
        s = closes[sym]
        ii = s.index.searchsorted(t, side="right") - 1
        return float(s.iloc[ii]) if ii >= 0 else float(s.iloc[0])

    entries_by_t = defaultdict(list)
    exits_by_t = defaultdict(list)
    for idx, tr in enumerate(all_trades):
        entries_by_t[tr["entry_time"]].append(idx)
        exits_by_t[tr["exit_time"]].append(idx)
    times = sorted(set(entries_by_t) | set(exits_by_t))
    order_of = {idx: idx for idx in range(len(all_trades))}

    realized = pb.START_EQUITY
    open_pos, by_id = [], {}
    peak, max_dd = realized, 0.0
    skipped_rank = skipped_cap = skipped_risk = skipped_gate = 0
    n_half_risk = n_full_risk = 0
    taken = []
    open_time = total_time = pd.Timedelta(0)
    prev_t = None

    def marked_equity(t):
        unreal = sum(((mark(tr["symbol"], t) - tr["entry"]) / tr["entry"]) * p["size"]
                      for p, tr in ((p, p["trade"]) for p in open_pos))
        return realized + unreal

    for t in times:
        if prev_t is not None and t > prev_t:
            dt = t - prev_t
            total_time += dt
            if open_pos:
                open_time += dt
        prev_t = t
        for idx in sorted(exits_by_t.get(t, [])):
            pos = by_id.pop(id(all_trades[idx]), None)
            if pos is None:
                continue
            tr = all_trades[idx]
            _, _, net_r, _ = pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)
            realized += pos["risk_dollars"] * net_r
            open_pos.remove(pos)
        cands = entries_by_t.get(t, [])
        if cands:
            n_cands_t = len(cands)
            if use_ranking:
                scored = [(-rs[id(all_trades[i])], i) for i in cands]
                scored.sort()
                ordered = [i for _, i in scored]
            else:
                ordered = sorted(cands)  # deterministic candidate order
            free0 = pb.MAX_CONCURRENT - len(open_pos)
            taken_at_t = 0
            for idx in ordered:
                tr = all_trades[idx]
                free = pb.MAX_CONCURRENT - len(open_pos)
                contested_now = n_cands_t > free
                if use_ranking and contested_now and taken_at_t >= min(2, free):
                    skipped_rank += 1
                    continue
                if free <= 0:
                    skipped_cap += 1
                    continue
                eq = marked_equity(t)
                if sector_cap:
                    s = sector_map[tr["symbol"]]
                    n_sec = sum(1 for p in open_pos
                                if sector_map[p["trade"]["symbol"]] == s)
                    if n_sec >= 2:
                        skipped_gate += 1
                        continue
                # S4 drawdown gate (identical to pine_sizing: check BEFORE sizing)
                cur_risk = pb.RISK_PCT
                if dd_gate:
                    if eq <= DD_HALT * peak:
                        cur_risk = pb.RISK_PCT / 2.0
                    elif eq >= DD_RESUME * peak:
                        cur_risk = pb.RISK_PCT
                open_risk = (sum(p["risk_dollars"] for p in open_pos) / eq
                             if eq > 0 else 1)
                if open_risk + cur_risk > pb.MAX_PORTFOLIO_RISK + 1e-9:
                    skipped_risk += 1
                    continue
                risk_dollars = cur_risk * eq
                risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
                pos = {"trade": tr, "risk_dollars": risk_dollars,
                       "size": risk_dollars / risk_frac, "risk_frac": risk_frac,
                       "risk_pct": cur_risk}
                open_pos.append(pos)
                by_id[id(tr)] = pos
                taken.append(idx)
                taken_at_t += 1
                if cur_risk < pb.RISK_PCT:
                    n_half_risk += 1
                else:
                    n_full_risk += 1
        eq = marked_equity(t)
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    exposure = float(open_time / total_time) if total_time > pd.Timedelta(0) else 0.0
    return {"final_equity": realized, "max_drawdown": max_dd,
            "skipped_rank": skipped_rank, "skipped_cap": skipped_cap,
            "skipped_risk": skipped_risk, "skipped_gate": skipped_gate,
            "n_half_risk": n_half_risk, "n_full_risk": n_full_risk,
            "taken": taken, "exposure": exposure,
            "skipped_cap_count": skipped_cap + skipped_rank,
            "skipped_cap_risk": skipped_risk}


def load_bull():
    data, closes = {}, {}
    for sym in pb.UNIVERSE_X:
        path = os.path.join(pb.CACHE, f"h4_{sym}.pkl")
        if not os.path.exists(path):
            continue
        df = pd.read_pickle(path)
        if "Volume" not in df.columns or df["Volume"].isna().all():
            continue
        data[sym] = pb.add_pine_indicators(df)
        closes[sym] = data[sym]["Close"]
    all_trades, skipped_gap = [], 0
    order_of = {}
    for sym, df in data.items():
        tr, sg = gen_candidates(sym, df)
        skipped_gap += sg
        for t in tr:
            order_of[id(t)] = len(order_of)
        all_trades.extend(tr)
    all_trades.sort(key=lambda t: order_of[id(t)])
    return all_trades, closes, data, order_of, skipped_gap


CACHE_OLD = os.path.join(HERE, "v6_short_v2", "cache")
CACHE_NEW = os.path.join(HERE, "pine_exit_fix", "cache_2022")
CUTOFF = pd.Timestamp("2022-01-01", tz="UTC")


def load_2022():
    paths = {}
    for d in (CACHE_OLD, CACHE_NEW):
        for p in glob.glob(os.path.join(d, "d4h_2022_*.pkl")):
            sym = os.path.basename(p)[len("d4h_2022_"):-len(".pkl")]
            paths.setdefault(sym, p)
    data, closes = {}, {}
    for sym, p in sorted(paths.items()):
        df = pd.read_pickle(p)
        if "Volume" not in df.columns or df["Volume"].isna().all():
            continue
        if not isinstance(df.index, pd.DatetimeIndex) or df.index.tz is None:
            df.index = pd.to_datetime(df.index, utc=True)
        data[sym] = pb.add_pine_indicators(df)
        closes[sym] = data[sym]["Close"]
    # identical engine to pine_ranking_validate.gen_trades_2022
    all_trades, skipped_gap = [], 0
    for sym, df in data.items():
        trades = []
        n = len(df)
        i = pb.WARMUP
        in_trade = False
        pos = None
        while i < n - 1:
            if not in_trade:
                if df.index[i] >= CUTOFF and pb.pine_buy_signal(df, i):
                    sig = df.iloc[i]
                    entry = float(df["Open"].iloc[i + 1])
                    stop0 = float(sig["Close"] - sig["atr"] * pb.SL_ATR)
                    if entry <= stop0:
                        skipped_gap += 1
                        i += 1
                        continue
                    in_trade = True
                    pos = {"symbol": sym, "entry": entry, "stop": stop0,
                           "tp1": entry + float(sig["atr"]) * pb.TP_ATR,
                           "tp_hit": False, "runner": stop0,
                           "entry_idx": i + 1, "signal_idx": i,
                           "entry_time": df.index[i + 1],
                           "signal_time": df.index[i].isoformat()}
                i += 1
                continue
            bar = df.iloc[i]
            lo, hi, close = float(bar["Low"]), float(bar["High"]), float(bar["Close"])
            if not pos["tp_hit"] and hi >= pos["tp1"]:
                pos["tp_hit"] = True
            if pos["tp_hit"]:
                pos["runner"] = max(pos["runner"], close - float(bar["atr"]) * pb.TRAIL_ATR)
            trend_bear = bar["e21"] < bar["e55"] and close < bar["e200"]
            done = False
            if close < pos["runner"]:
                reason = "stop"
                done = True
            elif close < bar["e55"] or trend_bear:
                reason = "ema55-bear" if trend_bear else "ema55-break"
                done = True
            if done:
                if i + 1 < n:
                    exit_px = float(df["Open"].iloc[i + 1])
                    exit_idx, exit_time = i + 1, df.index[i + 1]
                else:
                    exit_px, exit_time = close, df.index[i]
                    exit_idx = i
            if done:
                risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]
                r1 = ((pos["tp1"] - pos["entry"]) / pos["entry"] / risk_frac
                      if pos["tp_hit"] else None)
                r2 = (exit_px - pos["entry"]) / pos["entry"] / risk_frac
                r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
                exit_synth = pos["entry"] * (1 + r_blend * risk_frac)
                trades.append({
                    "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
                    "tp1": pos["tp1"], "exit": exit_synth, "reason": reason,
                    "tp1_hit": pos["tp_hit"],
                    "entry_time": pos["entry_time"], "exit_time": exit_time,
                    "hold_bars": exit_idx - pos["entry_idx"],
                    "signal_time": pos["signal_time"],
                    "signal_idx": pos["signal_idx"]})
                in_trade = False
                pos = None
            i += 1
        if in_trade:
            exit_px = float(df["Close"].iloc[-1])
            risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]
            r1 = ((pos["tp1"] - pos["entry"]) / pos["entry"] / risk_frac
                  if pos["tp_hit"] else None)
            r2 = (exit_px - pos["entry"]) / pos["entry"] / risk_frac
            r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
            exit_synth = pos["entry"] * (1 + r_blend * risk_frac)
            trades.append({
                "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
                "tp1": pos["tp1"], "exit": exit_synth, "reason": "eod",
                "tp1_hit": pos["tp_hit"],
                "entry_time": pos["entry_time"], "exit_time": df.index[-1],
                "hold_bars": (n - 1) - pos["entry_idx"],
                "signal_time": pos["signal_time"],
                "signal_idx": pos["signal_idx"]})
        all_trades.extend(trades)
    order_of = {}
    for t in all_trades:
        order_of[id(t)] = len(order_of)
    all_trades.sort(key=lambda t: order_of[id(t)])
    return all_trades, closes, data, order_of, skipped_gap


def run_case(all_trades, closes, sector_map, cost_name, use_ranking, sector_cap,
             dd_gate, skipped_gap):
    cost = pb.COSTS[cost_name]
    port = simulate_stack(all_trades, closes, cost, use_ranking, sector_cap,
                          dd_gate, sector_map)
    taken = [all_trades[i] for i in port["taken"]]
    row = pb.summarize("stack", taken, port, skipped_gap, cost_name)
    row = extend_row(row, taken, cost_name)
    row["pct_entries_half_risk"] = round(
        100.0 * port["n_half_risk"] / max(1, port["n_half_risk"] + port["n_full_risk"]), 1)
    row["sector_cap_skips"] = port["skipped_gate"]
    row["rank_skips"] = port["skipped_rank"]
    return row


def main():
    global rs
    print("== BULL WINDOW ==", flush=True)
    all_trades, closes, data, order_of, skipped_gap = load_bull()
    print(f"candidates: {len(all_trades)}", flush=True)
    bench, _ = load_benchmarks()
    feats = compute_features(all_trades, data, bench)
    rs = {id(tr): feats[i]["rs"] for i, tr in enumerate(all_trades)}

    # NOTE 2026-09-20: verification expectations below are the
    # C1_CORRECTED_SCORE_BASELINE values (corrected 0-5 trendScore). The
    # pre-correction values (C0 263/+0.195R, R1-only 154/+0.324/52.78/32.65,
    # R1+R2 143/+0.337/52.25/31.63, R3 29.49/29.86) were generated with the
    # NumPy boolean-addition bug and are archived as INVALID.
    # (a) C0 fidelity: my sim == pb.simulate_portfolio, 263 / +0.195R
    port_pb = pb.simulate_portfolio(all_trades, closes, pb.COSTS["4bps"], pb.RISK_PCT)
    port_c0 = simulate_stack(all_trades, closes, pb.COSTS["4bps"],
                             False, False, False, SECTOR)
    ok_c0 = (abs(port_pb["final_equity"] - port_c0["final_equity"]) < 1e-6
             and port_pb["skipped_cap_count"] == port_c0["skipped_cap"])
    r0 = pb.summarize("C0", all_trades, port_pb, skipped_gap, "4bps")
    print(f"fidelity C0 == pb control: {'PASS' if ok_c0 else 'FAIL'} "
          f"(n={r0['trades']}, exp={r0['expectancy_net_r']}R; want 877/+0.141R)",
          flush=True)
    # (b) ranking-only leg == rs_top2 (154 / +0.324R / 52.78% / 32.65%)
    row_rk = run_case(all_trades, closes, SECTOR, "4bps", True, False, False,
                      skipped_gap)
    print(f"verify R1-only: n={row_rk['trades']} exp={row_rk['expectancy_net_r']}R "
          f"ret={row_rk['total_return_pct']}% dd={row_rk['max_drawdown_pct']}% "
          f"(want 277 / +0.176 / 42.11 / 51.23)", flush=True)
    # (c) ranking+sector == stacked_C1 (143 / +0.337R / 52.25% / 31.63%)
    row_rksec = run_case(all_trades, closes, SECTOR, "4bps", True, True, False,
                         skipped_gap)
    print(f"verify R1+R2: n={row_rksec['trades']} exp={row_rksec['expectancy_net_r']}R "
          f"ret={row_rksec['total_return_pct']}% dd={row_rksec['max_drawdown_pct']}% "
          f"(want 240 / +0.178 / 42.24 / 38.46)", flush=True)
    # (d) gate-only leg == S4 (29.49% / 29.86%)
    row_gt = run_case(all_trades, closes, SECTOR, "4bps", False, False, True,
                      skipped_gap)
    print(f"verify R3-only: ret={row_gt['total_return_pct']}% "
          f"dd={row_gt['max_drawdown_pct']}% half%={row_gt['pct_entries_half_risk']} "
          f"(want 13.03 / 30.22)", flush=True)
    if not ok_c0:
        print("FIDELITY FAILED — aborting", flush=True)
        sys.exit(2)

    results = {"spec": "STACK_SPEC.md frozen before runs",
               "accounting": "one consistent accounting for all four cases: "
               "synthetic blended exit price via pb._outcome; absolute returns "
               "comparable WITHIN this study only",
               "verification": {"C0_fidelity_pass": ok_c0,
                                "R1_only": {k: row_rk[k] for k in
                                            ("trades", "expectancy_net_r",
                                             "total_return_pct", "max_drawdown_pct")},
                                "R1_R2": {k: row_rksec[k] for k in
                                          ("trades", "expectancy_net_r",
                                           "total_return_pct", "max_drawdown_pct")},
                                "R3_only": {k: row_gt[k] for k in
                                            ("trades", "total_return_pct",
                                             "max_drawdown_pct",
                                             "pct_entries_half_risk")}},
               "cases": {}}
    cases = [("C0", False, False, False),
             ("C1", True, True, False),
             ("C2", True, False, True),
             ("C3", True, True, True)]
    for cname, ur, sc, dg in cases:
        results["cases"][cname] = {}
        for cost_name in pb.COSTS:
            row = run_case(all_trades, closes, SECTOR, cost_name, ur, sc, dg,
                           skipped_gap)
            results["cases"][cname][cost_name] = row
            print(f"{cname} [{cost_name}]: n={row['trades']} "
                  f"exp={row['expectancy_net_r']}R PF={row['profit_factor']} "
                  f"ret={row['total_return_pct']}% dd={row['max_drawdown_pct']}% "
                  f"calmar={row.get('calmar')} half%={row['pct_entries_half_risk']} "
                  f"secskip={row['sector_cap_skips']}", flush=True)
        json.dump(results, open(OUT_JSON, "w"), indent=1, default=str)

    print("== 2022 WINDOW ==", flush=True)
    all22, closes22, data22, order_of22, sg22 = load_2022()
    print(f"2022 candidates: {len(all22)} symbols={len(data22)}", flush=True)
    missing = sorted({t["symbol"] for t in all22} - set(SECTOR_2022))
    print(f"2022 symbols missing from sector map: {missing}", flush=True)
    feats22 = compute_features(all22, data22, bench)
    rs = {id(tr): feats22[i]["rs"] for i, tr in enumerate(all22)}
    results22 = {"notes": ["2022 validation of all four stack cases; same "
                           "framework as every prior study. No refit."],
                 "cases": {}}
    for cname, ur, sc, dg in cases:
        results22["cases"][cname] = {}
        for cost_name in pb.COSTS:
            row = run_case(all22, closes22, SECTOR_2022, cost_name, ur, sc, dg,
                           sg22)
            results22["cases"][cname][cost_name] = row
            print(f"2022 {cname} [{cost_name}]: n={row['trades']} "
                  f"exp={row['expectancy_net_r']}R ret={row['total_return_pct']}% "
                  f"dd={row['max_drawdown_pct']}% half%={row['pct_entries_half_risk']} "
                  f"secskip={row['sector_cap_skips']}", flush=True)
        json.dump(results22, open(OUT_JSON_2022, "w"), indent=1, default=str)
    print("DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
