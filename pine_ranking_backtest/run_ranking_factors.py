#!/usr/bin/env python3
"""Ranking-factor study (P2 of research mandate, 2026-09-24).

Question: when crowded signal bars produce more valid signals than portfolio
slots, does any ranking factor beat the adopted rs_top2 control
(20-bar return minus SPY, take top 2)?

Factors are pre-declared in CANDIDATES.md (frozen before running).
Research only — nothing frozen touched.
"""
import json
import os
import sys
import traceback
from collections import defaultdict

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_ranking_backtest")
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "pine_signal_quality"))
import pine_backtest as pb
from pine_signal_quality import load_benchmarks, bench_ret

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "ranking_factor_results.json")
os.makedirs(OUTDIR, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

SECTOR_ETF = {"SMCI": "XLK", "PLTR": "XLK", "AMD": "XLK", "ANET": "XLK",
              "BBAI": "XLK", "DRAM": "XLK",
              "SOFI": "XLF", "HOOD": "XLF",
              "RKLB": "XLI", "SPCX": "XLI", "ASTX": "XLI", "ONDS": "XLI",
              "NIO": "XLY", "QQQ": "SPY"}

RS_LB, MOM50_LB, HIGH_LB = 20, 50, 50
COST = 0.0025  # 25bps primary


def compute_features(trades, data, bench, sig_index):
    feats = {}
    spy = bench.get("SPY")
    for idx, tr in enumerate(trades):
        sym = tr["symbol"]
        df = data[sym]
        i = sig_index[sym][tr["signal_time"]]
        c = float(df["Close"].iloc[i])
        row = {"rs_spy": float("-inf"), "rs_sector": float("-inf"),
               "mom20": float("-inf"), "mom50": float("-inf"),
               "adx": float("-inf"), "breakout_dist": float("-inf"),
               "vol_expansion": float("-inf"), "dollar_liq": float("-inf"),
               "atr_mom": float("-inf"), "dist_200ema": float("-inf"),
               "dist_high": float("-inf"), "trend_score": float("-inf"),
               "rr": float("-inf")}
        t1 = df.index[i].tz_convert("UTC")
        if i >= RS_LB and not pd.isna(df["Close"].iloc[i - RS_LB]):
            sym_ret = c / float(df["Close"].iloc[i - RS_LB]) - 1.0
            t0 = df.index[i - RS_LB].tz_convert("UTC")
            row["mom20"] = sym_ret
            if spy is not None:
                br = bench_ret(spy, t0, t1)
                if br is not None:
                    row["rs_spy"] = sym_ret - br
            setf = SECTOR_ETF.get(sym)
            sb = bench.get(setf) if setf else None
            if sb is not None:
                brs = bench_ret(sb, t0, t1)
                if brs is not None:
                    row["rs_sector"] = sym_ret - brs
            atr = float(df["atr"].iloc[i])
            if atr > 0 and not pd.isna(atr):
                row["atr_mom"] = sym_ret / (atr / c) if c > 0 else float("-inf")
                hh20 = float(df["High"].iloc[i - RS_LB:i].max())
                row["breakout_dist"] = (c - hh20) / atr
                e200 = float(df["e200"].iloc[i])
                if not pd.isna(e200):
                    row["dist_200ema"] = (c - e200) / atr
                if i >= HIGH_LB:
                    hh50 = float(df["High"].iloc[i - HIGH_LB:i].max())
                    row["dist_high"] = -(hh50 - c) / atr
        if i >= MOM50_LB and not pd.isna(df["Close"].iloc[i - MOM50_LB]):
            row["mom50"] = c / float(df["Close"].iloc[i - MOM50_LB]) - 1.0
        adx = float(df["adx"].iloc[i])
        if not pd.isna(adx):
            row["adx"] = adx
        vm = float(df["vol_ma"].iloc[i])
        vol = float(df["Volume"].iloc[i])
        if vm and not pd.isna(vm) and vm > 0 and not pd.isna(vol):
            row["vol_expansion"] = vol / vm
        dv = df["Close"].iloc[i - RS_LB:i] * df["Volume"].iloc[i - RS_LB:i]
        if i >= RS_LB and dv.notna().all() and (dv > 0).all():
            row["dollar_liq"] = float(dv.mean())
        e21 = float(df["e21"].iloc[i])
        e55 = float(df["e55"].iloc[i])
        e200 = float(df["e200"].iloc[i])
        if not any(pd.isna(x) for x in (e21, e55, e200, adx)):
            row["trend_score"] = float((e21 > e55) + (c > e200)
                                      + (adx >= 20) + (c > e21))
        risk = tr["entry"] - tr["stop"]
        if risk > 0:
            tp1 = tr["entry"] + float(df["atr"].iloc[i]) * pb.TP_ATR
            row["rr"] = (tp1 - tr["entry"]) / risk
        feats[idx] = row
    return feats


def pct_ranks(vals):
    order = sorted(range(len(vals)), key=lambda k: vals[k])
    ranks = [0.0] * len(vals)
    k = 0
    while k < len(vals):
        j = k
        while j + 1 < len(vals) and vals[order[j + 1]] == vals[order[k]]:
            j += 1
        avg = (k + j) / 2.0
        for t in range(k, j + 1):
            ranks[order[t]] = avg
        k = j + 1
    n = len(vals)
    return [r / (n - 1) if n > 1 else 0.5 for r in ranks]


COMBOS = {"C_rs_adx": ("rs_spy", "adx"),
          "C_rs_vol": ("rs_spy", "vol_expansion"),
          "C_rs_rr": ("rs_spy", "rr")}


def simulate_ranked(all_trades, closes, cost, feats, score_fn, n_cap=2,
                    diag=None, taken_out=None):
    entries_by_t = defaultdict(list)
    exits_by_t = defaultdict(list)
    for idx, t in enumerate(all_trades):
        entries_by_t[t["entry_time"]].append(idx)
        exits_by_t[t["exit_time"]].append(idx)
    times = sorted(set(entries_by_t) | set(exits_by_t))
    ordered = []
    for t in times:
        for idx in sorted(exits_by_t.get(t, [])):
            ordered.append((t, 0, idx))
        cands = entries_by_t.get(t, [])
        if score_fn is not None and len(cands) > 1:
            scored = [(score_fn(i, cands), i) for i in cands]
        else:
            scored = [(0.0, i) for i in cands]
        scored.sort(key=lambda s: (-s[0], s[1]))
        for _, idx in scored:
            ordered.append((t, 1, idx))

    realized = pb.START_EQUITY
    open_pos, by_id = [], {}
    skipped_rank = skipped_risk = 0
    peak, max_dd = realized, 0.0
    open_time = total_time = pd.Timedelta(0)
    prev_t, cur_t, taken_at_t, n_cands_t = None, None, 0, 0
    contested = {}

    def mark(sym, t):
        s = closes[sym]
        ii = s.index.searchsorted(t, side="right") - 1
        return float(s.iloc[ii]) if ii >= 0 else float(s.iloc[0])

    def marked_equity(t):
        unreal = sum(((mark(tr["symbol"], t) - tr["entry"]) / tr["entry"]) * p["size"]
                     for p, tr in ((p, p["trade"]) for p in open_pos))
        return realized + unreal

    for t, kind, idx in ordered:
        if prev_t is not None and t > prev_t:
            dt = t - prev_t
            total_time += dt
            if open_pos:
                open_time += dt
        prev_t = t
        if t != cur_t:
            cur_t, taken_at_t = t, 0
            n_cands_t = len(entries_by_t.get(t, []))
        tr = all_trades[idx]
        if kind == 1:
            free = pb.MAX_CONCURRENT - len(open_pos)
            contested_now = n_cands_t > free
            if contested_now and diag is not None and t not in contested:
                contested[t] = (n_cands_t, free)
                diag["contested"].append((str(t), n_cands_t, free))
            if contested_now and n_cap is not None and taken_at_t >= min(n_cap, free):
                skipped_rank += 1
                continue
            if free <= 0:
                skipped_rank += 1
                continue
            eq = marked_equity(t)
            open_risk = sum(p["risk_dollars"] for p in open_pos) / eq if eq > 0 else 1
            if open_risk + pb.RISK_PCT > pb.MAX_PORTFOLIO_RISK + 1e-9:
                skipped_risk += 1
                continue
            risk_dollars = pb.RISK_PCT * eq
            risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
            open_pos.append({"trade": tr, "risk_dollars": risk_dollars,
                             "size": risk_dollars / risk_frac,
                             "risk_frac": risk_frac})
            by_id[id(tr)] = open_pos[-1]
            if taken_out is not None:
                taken_out.append(idx)
            taken_at_t += 1
        else:
            pos = by_id.pop(id(tr), None)
            if pos is None:
                continue
            _, _, net_r, _ = pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)
            realized += pos["risk_dollars"] * net_r
            open_pos.remove(pos)
        eq = marked_equity(t)
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    exposure = float(open_time / total_time) if total_time > pd.Timedelta(0) else 0.0
    return {"final_equity": realized, "max_drawdown": max_dd,
            "skipped_cap_count": skipped_rank, "skipped_cap_risk": skipped_risk,
            "exposure": exposure}


def net_r(tr, cost):
    return pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]


def stats_for(taken, port, cost):
    rs = np.array([net_r(t, cost) for t in taken])
    wins = rs[rs > 0]
    losses = rs[rs <= 0]
    gw, gl = wins.sum(), -losses.sum()
    return {
        "trades": len(taken),
        "expectancy_net_r": round(float(rs.mean()), 4) if len(rs) else None,
        "win_rate_pct": round(float((rs > 0).mean()) * 100, 1) if len(rs) else None,
        "profit_factor": round(float(gw / gl), 2) if gl > 0 else None,
        "max_drawdown_pct": round(port["max_drawdown"] * 100, 2),
        "total_return_pct": round((port["final_equity"] / pb.START_EQUITY - 1) * 100, 2),
    }


def yearly(trades, cost):
    out = {}
    for t in trades:
        y = str(pd.Timestamp(t["signal_time"]).year)
        out.setdefault(y, []).append(t)
    return {y: {"n": len(v), "exp_r": round(float(np.mean([net_r(t, cost) for t in v])), 4)}
            for y, v in sorted(out.items())}


def main():
    data, closes, sig_index = {}, {}, {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        if "Volume" not in df.columns or df["Volume"].isna().all():
            print(f"dropped {sym} (no volume)", flush=True)
            continue
        df = pb.add_pine_indicators(df)
        data[sym] = df
        closes[sym] = df["Close"]
        sig_index[sym] = {df.index[i].isoformat(): i for i in range(len(df))}
    used = [s for s in WATCHLIST if s in data]
    print(f"loaded {len(used)} tickers", flush=True)

    all_trades, skipped_gap = [], 0
    for sym in used:
        tr, sg = pb.gen_pine_trades(sym, data[sym])
        all_trades.extend(tr)
        skipped_gap += sg
    all_trades.sort(key=lambda t: t["entry_time"])
    print(f"candidates: {len(all_trades)}", flush=True)

    bench, _ = load_benchmarks()
    feats = compute_features(all_trades, data, bench, sig_index)
    print("features done", flush=True)

    # fidelity: constant score == pb control
    port_pb = pb.simulate_portfolio(all_trades, closes, COST, pb.RISK_PCT)
    port_mine = simulate_ranked(all_trades, closes, COST, feats, None, None)
    ok = (abs(port_pb["final_equity"] - port_mine["final_equity"]) < 1e-6
          and port_pb["skipped_cap_count"] == port_mine["skipped_cap_count"])
    print(f"fidelity takeall==pb: {'PASS' if ok else 'FAIL'} "
          f"(n={len(all_trades)})", flush=True)
    if not ok:
        sys.exit(2)

    # Step 0: clustering
    diag = {"contested": []}
    simulate_ranked(all_trades, closes, COST, feats, None, None, diag=diag)
    n_con = len(diag["contested"])
    hist = defaultdict(int)
    for _, m, _ in diag["contested"]:
        hist[m] += 1
    genuine = sum(1 for _, m, f in diag["contested"] if f > 0)
    print(f"contested timestamps: {n_con} (genuine choice: {genuine}), "
          f"hist={dict(sorted(hist.items()))}", flush=True)

    def single_score(fid):
        def fn(i, cands):
            return feats[i][fid]
        return fn

    def combo_score(fids):
        def fn(i, cands):
            prs = [pct_ranks([feats[j][f] for j in cands]) for f in fids]
            k = cands.index(i)
            return sum(p[k] for p in prs) / len(prs)
        return fn

    variants = {"takeall_ref": None, "rs_spy_CONTROL": single_score("rs_spy")}
    for fid in ["rs_sector", "mom20", "mom50", "adx", "breakout_dist",
                "vol_expansion", "dollar_liq", "atr_mom", "dist_200ema",
                "dist_high", "trend_score", "rr"]:
        variants[fid] = single_score(fid)
    for cid, fids in COMBOS.items():
        variants[cid] = combo_score(fids)

    results = {"control": "rs_spy top2",
               "clustering": {"contested_timestamps": n_con,
                              "genuine_choice": genuine,
                              "histogram": dict(sorted(hist.items()))},
               "variants": {}}
    ctrl_exp = None
    for vid, sfn in variants.items():
        taken_idx = []
        port = simulate_ranked(all_trades, closes, COST, feats, sfn, 2,
                               taken_out=taken_idx)
        taken = [all_trades[i] for i in taken_idx]
        rec = stats_for(taken, port, COST)
        rec["yearly"] = yearly(taken, COST)
        results["variants"][vid] = rec
        if vid == "rs_spy_CONTROL":
            ctrl_exp = rec["expectancy_net_r"]
        print(f"{vid}: n={rec['trades']} exp={rec['expectancy_net_r']}R "
              f"win={rec['win_rate_pct']}% PF={rec['profit_factor']} "
              f"DD={rec['max_drawdown_pct']}% ret={rec['total_return_pct']}%",
              flush=True)
    json.dump(results, open(OUT, "w"), indent=1, default=str)
    print(f"\nwrote {OUT} (control exp={ctrl_exp}R)")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
