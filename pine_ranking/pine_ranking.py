"""Cross-sectional RANKING study on Pine V3.6. Spec: RANKING_SPEC.md (frozen).
V3.6 entries/exits byte-identical; ranking only orders candidates when position
slots are scarce. Control must reproduce baseline (263 trades, +0.195R @4bps)."""
import json
import os
import sys
import traceback
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "pine_signal_quality"))
import pine_backtest as pb
from pine_signal_quality import load_benchmarks, bench_ret, extend_row

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(BASE, "ranking_results.json")
RS_LOOKBACK = 20  # pre-registered, same as signal-quality study


# ------------------------------------------------------- candidate generation
def gen_candidates(sym, df):
    """Identical trade engine to control; records signal_idx for ranking features."""
    trades = []
    skipped_gap = 0
    n = len(df)
    i = pb.WARMUP
    in_trade = False
    while i < n - 1:
        if not in_trade:
            if pb.pine_buy_signal(df, i):
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
                       "entry_time": df.index[i + 1]}
                i += 1
                continue
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
            r1 = (pos["tp1"] - pos["entry"]) / pos["entry"] / risk_frac if pos["tp_hit"] else None
            r2 = (exit_px - pos["entry"]) / pos["entry"] / risk_frac
            r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
            net_ret_blend = r_blend * risk_frac
            exit_synth = pos["entry"] * (1 + net_ret_blend)
            trades.append({
                "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
                "tp1": pos["tp1"], "exit": exit_synth, "reason": reason,
                "tp1_hit": pos["tp_hit"],
                "entry_time": pos["entry_time"], "exit_time": exit_time,
                "hold_bars": exit_idx - pos["entry_idx"],
                "signal_time": df.index[pos["entry_idx"] - 1].isoformat(),
                "signal_idx": pos["signal_idx"],
            })
            in_trade = False
        i += 1
    return trades, skipped_gap


# ------------------------------------------------------------- ranking feats
def compute_features(all_trades, data, bench):
    """Pre-registered point-in-time features per candidate trade."""
    feats = {}
    spy = bench.get("SPY")
    for idx, tr in enumerate(all_trades):
        df = data[tr["symbol"]]
        i = tr["signal_idx"]
        # R1: 20-bar return minus SPY return over same calendar span
        sym_ret = float(df["Close"].iloc[i] / df["Close"].iloc[i - RS_LOOKBACK] - 1.0)
        t1 = df.index[i].tz_convert("UTC")
        t0 = df.index[i - RS_LOOKBACK].tz_convert("UTC")
        br = bench_ret(spy, t0, t1) if spy is not None else None
        rs = (sym_ret - br) if br is not None else float("-inf")
        # R2: volume quality
        vm = float(df["vol_ma"].iloc[i])
        vol = float(df["Volume"].iloc[i] / vm) if vm and not np.isnan(vm) and vm > 0 else float("-inf")
        # R3c: reward:risk at entry
        rr = (tr["tp1"] - tr["entry"]) / (tr["entry"] - tr["stop"])
        feats[idx] = {"rs": rs, "vol": vol, "rr": float(rr)}
    return feats


def pct_ranks(vals):
    """Cross-sectional percentile ranks in [0,1], average method for ties."""
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


# ------------------------------------------------------- ranked portfolio sim
def simulate_portfolio_ranked(all_trades, closes, cost, risk_pct, feats, scheme,
                              n_cap, diag=None, taken_out=None):
    """Mirror of pb.simulate_portfolio, except entries at a timestamp are taken
    in rank order and ranking engages only at contested timestamps.

    scheme: 'rs' | 'vol' | 'composite' | 'takeall' (fidelity check)
    n_cap: max taken per contested bar (1/2/3); None = fill all free slots.
    diag: optional dict to record contested timestamps.
    """
    def base_score(idx):
        f = feats[idx]
        if scheme == "rs":
            return f["rs"]
        if scheme == "vol":
            return f["vol"]
        return 0.0  # takeall / composite handled separately

    entries_by_t = defaultdict(list)
    exits_by_t = defaultdict(list)
    for idx, t in enumerate(all_trades):
        entries_by_t[t["entry_time"]].append(idx)
        exits_by_t[t["exit_time"]].append(idx)
    times = sorted(set(entries_by_t) | set(exits_by_t))

    # order entries at each timestamp: exits first (kind 0), then entries by rank
    ordered = []
    for t in times:
        for idx in sorted(exits_by_t.get(t, [])):
            ordered.append((t, 0, idx))
        cands = entries_by_t.get(t, [])
        if scheme == "composite" and len(cands) > 1:
            pr_rs = pct_ranks([feats[i]["rs"] for i in cands])
            pr_vol = pct_ranks([feats[i]["vol"] for i in cands])
            pr_rr = pct_ranks([feats[i]["rr"] for i in cands])
            scored = [((pr_rs[k] + pr_vol[k] + pr_rr[k]) / 3.0, cands[k])
                      for k in range(len(cands))]
        else:
            scored = [(base_score(i), i) for i in cands]
        # higher score first; deterministic tie-break: original candidate order
        # (UNIVERSE_X symbol order, then entry time) — this also makes the
        # 'takeall' scheme reproduce pb.simulate_portfolio exactly.
        scored.sort(key=lambda s: (-s[0], s[1]))
        for _, idx in scored:
            ordered.append((t, 1, idx))

    realized = pb.START_EQUITY
    open_pos, by_id = [], {}
    skipped_rank = skipped_risk = 0
    peak, max_dd = realized, 0.0
    open_time = total_time = pd.Timedelta(0)
    prev_t = None
    taken_at_t, contested = defaultdict(int), {}

    def mark(sym, t):
        s = closes[sym]
        ii = s.index.searchsorted(t, side="right") - 1
        return float(s.iloc[ii]) if ii >= 0 else float(s.iloc[0])

    def marked_equity(t):
        unreal = sum(((mark(tr["symbol"], t) - tr["entry"]) / tr["entry"]) * p["size"]
                     for p, tr in ((p, p["trade"]) for p in open_pos))
        return realized + unreal

    cur_t = None
    n_cands_t = 0
    for t, kind, idx in ordered:
        if prev_t is not None and t > prev_t:
            dt = t - prev_t
            total_time += dt
            if open_pos:
                open_time += dt
        prev_t = t
        if t != cur_t:
            cur_t = t
            taken_at_t = 0
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
            if open_risk + risk_pct > pb.MAX_PORTFOLIO_RISK + 1e-9:
                skipped_risk += 1
                continue
            risk_dollars = risk_pct * eq
            risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
            open_pos.append({"trade": tr, "risk_dollars": risk_dollars,
                             "size": risk_dollars / risk_frac, "risk_frac": risk_frac})
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


def load_4h_cache():
    data = {}
    for sym in pb.UNIVERSE_X:
        path = os.path.join(pb.CACHE, f"h4_{sym}.pkl")
        if not os.path.exists(path):
            continue
        df = pd.read_pickle(path)
        if "Volume" not in df.columns or df["Volume"].isna().all():
            continue
        data[sym] = pb.add_pine_indicators(df)
    return data


def main():
    print("loading 4H cache...", flush=True)
    data = load_4h_cache()
    print(f"  {len(data)} symbols", flush=True)
    print("generating candidates...", flush=True)
    all_trades, closes, skipped_gap = [], {}, 0
    for sym, df in data.items():
        tr, sg = gen_candidates(sym, df)
        all_trades.extend(tr)
        closes[sym] = df["Close"]
        skipped_gap += sg
    all_trades.sort(key=lambda t: t["entry_time"])
    print(f"  {len(all_trades)} candidate trades", flush=True)

    print("loading benchmarks...", flush=True)
    from pine_signal_quality import load_benchmarks as lb
    import pine_signal_quality as sq
    bench, _ = lb()
    feats = compute_features(all_trades, data, bench)
    print("  features done", flush=True)

    # ---- fidelity check: ranked sim with constant score == pb control
    port_pb = pb.simulate_portfolio(all_trades, closes, pb.COSTS["4bps"], pb.RISK_PCT)
    port_mine = simulate_portfolio_ranked(all_trades, closes, pb.COSTS["4bps"],
                                          pb.RISK_PCT, feats, "takeall", None)
    ok = (abs(port_pb["final_equity"] - port_mine["final_equity"]) < 1e-6
          and abs(port_pb["max_drawdown"] - port_mine["max_drawdown"]) < 1e-9
          and port_pb["skipped_cap_count"] == port_mine["skipped_cap_count"])
    print(f"fidelity check (takeall == pb control): {'PASS' if ok else 'FAIL'}", flush=True)
    print(f"  pb:   eq={port_pb['final_equity']:.2f} dd={port_pb['max_drawdown']:.4f} "
          f"skip={port_pb['skipped_cap_count']}", flush=True)
    print(f"  mine: eq={port_mine['final_equity']:.2f} dd={port_mine['max_drawdown']:.4f} "
          f"skip={port_mine['skipped_cap_count']}", flush=True)
    if not ok:
        print("FIDELITY FAILED — aborting", flush=True)
        sys.exit(2)
    row0 = pb.summarize("control", all_trades, port_pb, skipped_gap, "4bps")
    print(f"control: n={row0['trades']} exp={row0['expectancy_net_r']}R "
          f"(expect 263 / +0.195R)", flush=True)

    # ---- Step 0: clustering diagnostics
    diag = {"contested": []}
    simulate_portfolio_ranked(all_trades, closes, pb.COSTS["4bps"], pb.RISK_PCT,
                              feats, "takeall", None, diag=diag)
    n_con = len(diag["contested"])
    print(f"contested timestamps: {n_con}", flush=True)
    multi = defaultdict(int)
    for _, m, _ in diag["contested"]:
        multi[m] += 1
    print(f"  candidates-per-contested-bar histogram: {dict(sorted(multi.items()))}",
          flush=True)
    results = {"spec": "RANKING_SPEC.md frozen before testing",
               "control_4bps": row0,
               "clustering": {"contested_timestamps": n_con,
                              "histogram": dict(sorted(multi.items())),
                              "skipped_cap_count": port_pb["skipped_cap_count"],
                              "detail": diag["contested"][:50]},
               "variants": {}}
    json.dump(results, open(OUT_JSON, "w"), indent=1, default=str)
    if n_con < 5:
        results["verdict"] = ("MOOT — fewer than 5 contested timestamps in the "
                              "research window; ranking rarely gets to act.")
        json.dump(results, open(OUT_JSON, "w"), indent=1, default=str)
        print("MOOT: <5 contested timestamps. Stopping per spec.", flush=True)
        return

    # ---- 9 pre-registered variants
    schemes = [(s, n) for s in ("rs", "vol", "composite") for n in (1, 2, 3)]
    for scheme, n_cap in schemes:
        vid = f"{scheme}_top{n_cap}"
        print(f"== {vid} ==", flush=True)
        results["variants"][vid] = {}
        for cost_name, cost in pb.COSTS.items():
            taken_idx = []
            port = simulate_portfolio_ranked(all_trades, closes, cost, pb.RISK_PCT,
                                             feats, scheme, n_cap,
                                             taken_out=taken_idx)
            taken = [all_trades[i] for i in taken_idx]
            row = pb.summarize(f"PINE_V36_rank:{vid}", taken, port,
                               skipped_gap, cost_name)
            row["fill_rate_pct"] = round(len(taken) / len(all_trades) * 100, 1)
            row["candidates_available"] = len(all_trades)
            row = extend_row(row, taken, cost_name)
            results["variants"][vid][cost_name] = row
            print(f"  [{cost_name}] n={row['trades']} fill={row['fill_rate_pct']}% "
                  f"win={row['win_rate_pct']}% exp={row['expectancy_net_r']}R "
                  f"PF={row['profit_factor']} ret={row['total_return_pct']}% "
                  f"dd={row['max_drawdown_pct']}% tp1={row['tp1_hit_rate_pct']}% "
                  f"hold={row['avg_hold_bars']}", flush=True)
        json.dump(results, open(OUT_JSON, "w"), indent=1, default=str)
    print("DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
