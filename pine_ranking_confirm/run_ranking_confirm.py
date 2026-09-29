#!/usr/bin/env python3
"""ADX ranking — confirmatory study (mandate priority 3).

Frozen hypothesis in HYPOTHESIS.md. Research only — nothing frozen touched.
`pine_backtest` imported unmodified.
"""
import json
import os
import sys
import traceback
from collections import defaultdict

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_ranking_confirm")
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "pine_signal_quality"))
import pine_backtest as pb
from pine_signal_quality import load_benchmarks, bench_ret

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "ranking_confirm_results.json")
os.makedirs(OUTDIR, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

RS_LB = 20
COST = 0.0025  # 25bps primary


def compute_features(trades, data, bench, sig_index):
    feats = {}
    spy = bench.get("SPY")
    for idx, tr in enumerate(trades):
        sym = tr["symbol"]
        df = data[sym]
        i = sig_index[sym][tr["signal_time"]]
        c = float(df["Close"].iloc[i])
        row = {"rs_spy": float("-inf"), "adx": float("-inf"),
               "adx10": float("-inf"), "adx20": float("-inf")}
        t1 = df.index[i].tz_convert("UTC")
        if i >= RS_LB and not pd.isna(df["Close"].iloc[i - RS_LB]):
            sym_ret = c / float(df["Close"].iloc[i - RS_LB]) - 1.0
            t0 = df.index[i - RS_LB].tz_convert("UTC")
            if spy is not None:
                br = bench_ret(spy, t0, t1)
                if br is not None:
                    row["rs_spy"] = sym_ret - br
        for key, l, col in (("adx", 14, "adx"), ("adx10", 10, "adx10"),
                            ("adx20", 20, "adx20")):
            v = float(df[col].iloc[i])
            if not pd.isna(v):
                row[key] = v
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


def yearly(taken, cost):
    out = {}
    for t in taken:
        y = str(pd.Timestamp(t["signal_time"]).year)
        out.setdefault(y, []).append(t)
    return {y: {"n": len(v), "exp_r": round(float(np.mean([net_r(t, cost) for t in v])), 4)}
            for y, v in sorted(out.items())}


def sym_spread(taken, cost):
    out = {}
    for t in taken:
        out.setdefault(t["symbol"], []).append(net_r(t, cost))
    return {s: {"n": len(v), "exp_r": round(float(np.mean(v)), 4)}
            for s, v in sorted(out.items(), key=lambda kv: -len(kv[1]))}


def main():
    data, closes, sig_index = {}, {}, {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        df["adx10"] = pb.adx(df, 10)
        df["adx20"] = pb.adx(df, 20)
        data[sym] = df
        closes[sym] = df["Close"]
        sig_index[sym] = {df.index[i].isoformat(): i for i in range(len(df))}
    print(f"loaded {len(data)} tickers", flush=True)

    all_trades = []
    for sym in WATCHLIST:
        tr, _ = pb.gen_pine_trades(sym, data[sym])
        all_trades.extend(tr)
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
    print(f"fidelity takeall==pb: {'PASS' if ok else 'FAIL'}", flush=True)
    if not ok:
        sys.exit(2)

    diag = {"contested": []}
    simulate_ranked(all_trades, closes, COST, feats, None, None, diag=diag)
    hist = defaultdict(int)
    for _, m, _ in diag["contested"]:
        hist[m] += 1
    genuine = sum(1 for _, m, f in diag["contested"] if f > 0)
    print(f"contested: {len(diag['contested'])} (genuine: {genuine}), "
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

    variants = {
        "takeall": None,
        "rs_spy_CONTROL": single_score("rs_spy"),
        "adx": single_score("adx"),
        "adx10": single_score("adx10"),
        "adx20": single_score("adx20"),
        "C_rs_adx": combo_score(("rs_spy", "adx")),
    }

    results = {"variants": {}, "contested_hist": dict(sorted(hist.items())),
               "genuine_contests": genuine}
    taken_sets = {}
    for vid, sfn in variants.items():
        taken_idx = []
        port = simulate_ranked(all_trades, closes, COST, feats, sfn, 2,
                               taken_out=taken_idx)
        taken = [all_trades[i] for i in taken_idx]
        taken_sets[vid] = set(taken_idx)
        rec = stats_for(taken, port, COST)
        rec["yearly"] = yearly(taken, COST)
        results["variants"][vid] = rec
        print(f"{vid}: n={rec['trades']} exp={rec['expectancy_net_r']}R "
              f"win={rec['win_rate_pct']}% PF={rec['profit_factor']} "
              f"DD={rec['max_drawdown_pct']}% ret={rec['total_return_pct']}%",
              flush=True)

    # --- opportunity cost: ranked-out vs takeall ---
    ref = taken_sets["takeall"]
    opp = {}
    for vid in variants:
        if vid == "takeall":
            continue
        ranked_out = ref - taken_sets[vid]
        swapped_in = taken_sets[vid] - ref
        rs_out = [net_r(all_trades[i], COST) for i in ranked_out]
        rs_in = [net_r(all_trades[i], COST) for i in swapped_in]
        opp[vid] = {
            "ranked_out_n": len(ranked_out),
            "ranked_out_exp_r": round(float(np.mean(rs_out)), 4) if rs_out else None,
            "swapped_in_n": len(swapped_in),
            "swapped_in_exp_r": round(float(np.mean(rs_in)), 4) if rs_in else None,
        }
    results["opportunity_cost"] = opp

    # --- symbol concentration: selected vs rejected ---
    conc = {}
    for vid in ("rs_spy_CONTROL", "adx"):
        taken = [all_trades[i] for i in taken_sets[vid]]
        rejected = [all_trades[i] for i in ref - taken_sets[vid]]
        conc[vid] = {"selected": sym_spread(taken, COST),
                     "rejected_vs_takeall": sym_spread(rejected, COST)}
    results["symbol_concentration"] = conc

    # --- crowded-bars-only: timestamps with >=3 candidates ---
    entries_by_t = defaultdict(list)
    for idx, t in enumerate(all_trades):
        entries_by_t[t["entry_time"]].append(idx)
    crowded_ts = {t for t, c in entries_by_t.items() if len(c) >= 3}
    cb = {"n_timestamps": len(crowded_ts),
          "n_candidates": sum(len(entries_by_t[t]) for t in crowded_ts),
          "by_variant": {}}
    for vid in ("takeall", "rs_spy_CONTROL", "adx", "C_rs_adx"):
        sel = [i for i in taken_sets[vid]
               if all_trades[i]["entry_time"] in crowded_ts]
        rs = [net_r(all_trades[i], COST) for i in sel]
        cb["by_variant"][vid] = {
            "taken_at_crowded": len(sel),
            "exp_r": round(float(np.mean(rs)), 4) if rs else None,
        }
    adx_sel = {i for i in taken_sets["adx"]
               if all_trades[i]["entry_time"] in crowded_ts}
    rs_sel = {i for i in taken_sets["rs_spy_CONTROL"]
              if all_trades[i]["entry_time"] in crowded_ts}
    only_adx = adx_sel - rs_sel
    only_rs = rs_sel - adx_sel
    cb["differential_picks"] = {
        "adx_only_n": len(only_adx),
        "adx_only_exp_r": round(float(np.mean([net_r(all_trades[i], COST)
                                               for i in only_adx])), 4) if only_adx else None,
        "adx_only_symbols": sorted({all_trades[i]["symbol"] for i in only_adx}),
        "rs_only_n": len(only_rs),
        "rs_only_exp_r": round(float(np.mean([net_r(all_trades[i], COST)
                                              for i in only_rs])), 4) if only_rs else None,
        "rs_only_symbols": sorted({all_trades[i]["symbol"] for i in only_rs}),
    }
    results["crowded_bars"] = cb

    # --- walk-forward: train <=2024 / test >=2025 ---
    wf = {}
    for label, pred in (("train_le2024", lambda t: pd.Timestamp(t["signal_time"]).year <= 2024),
                        ("test_ge2025", lambda t: pd.Timestamp(t["signal_time"]).year >= 2025)):
        sub = [t for t in all_trades if pred(t)]
        sub_idx = {id(t): k for k, t in enumerate(sub)}
        fmap = {sub_idx[id(all_trades[i])]: feats[i]
                for i in range(len(all_trades)) if id(all_trades[i]) in sub_idx}
        per = {}
        for vid, sfn in variants.items():
            taken_idx = []
            # rebuild score fn on sub-index space: score_fn(j, cands) where
            # j is a sub-index and cands is the list of sub-indices
            sfn_sub = None
            if sfn is not None:
                fid = {"rs_spy_CONTROL": "rs_spy", "adx": "adx",
                       "adx10": "adx10", "adx20": "adx20"}.get(vid)
                if fid:
                    def sfn_sub(j, cands, _fid=fid, _fmap=fmap):
                        return _fmap[j][_fid]
                else:  # combo C_rs_adx
                    def sfn_sub(j, cands, _fmap=fmap):
                        prs = [pct_ranks([_fmap[k][f] for k in cands])
                               for f in ("rs_spy", "adx")]
                        kk = list(cands).index(j)
                        return sum(p[kk] for p in prs) / len(prs)
            port = simulate_ranked(sub, closes, COST, fmap, sfn_sub, 2,
                                   taken_out=taken_idx)
            taken = [sub[i] for i in taken_idx]
            per[vid] = stats_for(taken, port, COST)
        wf[label] = per
    results["walk_forward"] = wf

    json.dump(results, open(OUT, "w"), indent=1, default=str)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
