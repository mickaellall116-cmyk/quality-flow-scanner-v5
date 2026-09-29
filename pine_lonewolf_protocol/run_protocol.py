#!/usr/bin/env python3
"""Lone-wolf CANONICAL-PROTOCOL study (2026-09-25).

Implements HYPOTHESIS.md (pre-registered BEFORE results) exactly:
  dev/val split with predeclared formulation selection,
  rolling 12mo-train/6mo-test walk-forward (combined untouched test windows),
  year + regime splits, cost stress 25/50/75/100bps, perturbation family,
  concentration, bootstrap (B=10000, seed 42), leave-one-symbol-out,
  economic effect. Verdict per predeclared gates.

pine_backtest imported UNMODIFIED. Research only. Nothing frozen touched.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_lonewolf_protocol")
CACHE4H = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
CACHED = os.path.join(BASE, "pine_sector_rs_backtest", "cache")
OUT = os.path.join(OUTDIR, "protocol_results.json")
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
SECTOR = {
    "QQQ": "XLK", "SMCI": "SOXX", "PLTR": "XLK", "ANET": "XLK", "SOFI": "XLF",
    "RKLB": "XLI", "ONDS": "XLK", "DRAM": "SOXX", "SPCX": "XLI", "ASTX": "XLK",
    "BBAI": "XLK", "NIO": "XLY", "HOOD": "XLF", "AMD": "SOXX",
}
SECTORS = sorted(set(SECTOR.values()))
COSTS = [0.0025, 0.005, 0.0075, 0.01]  # 25 / 50 / 75 / 100 bps
FAMS = ["SIGN15", "SIGN20", "SIGN25", "REL15", "REL20", "REL25"]
DEV_END = pd.Timestamp("2025-01-01")  # DEV = [first, DEV_END), VAL = [DEV_END, end]

ROLL = [  # (train_start, train_end, test_start, test_end)
    ("2023-10-25", "2024-09-30", "2024-10-01", "2025-03-31"),
    ("2024-04-01", "2025-03-31", "2025-04-01", "2025-09-30"),
    ("2024-10-01", "2025-09-30", "2025-10-01", "2026-03-31"),
    ("2025-04-01", "2026-03-31", "2026-04-01", "2026-09-23"),
]


def net_r(tr, cost):
    return pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]


def daily_closes_4h(df4h):
    s = df4h["Close"].copy()
    s.index = s.index.tz_convert("America/New_York").tz_localize(None)
    return s.resample("1D").last().dropna()


def ret_n(series, date, n):
    idx = series.index
    pos = idx.searchsorted(date, side="right") - 1
    if pos < n:
        return np.nan
    return series.iloc[pos] / series.iloc[pos - n] - 1.0


def simulate_with_admission(trades, closes, cost, risk_pct, admit):
    """Faithful copy of pb.simulate_portfolio with an admission hook."""
    events = []
    for t in trades:
        events.append((t["exit_time"], 0, t))
        events.append((t["entry_time"], 1, t))
    events.sort(key=lambda e: (e[0], e[1]))
    realized = pb.START_EQUITY
    open_pos, by_id = [], {}
    skipped_cap_count = skipped_cap_risk = 0
    blocked, opened_ids = [], set()
    peak, max_dd = realized, 0.0

    def mark(sym, t):
        s = closes[sym]
        idx = s.index.searchsorted(t, side="right") - 1
        return float(s.iloc[idx]) if idx >= 0 else float(s.iloc[0])

    def marked_equity(t):
        unreal = sum(((mark(tr["symbol"], t) - tr["entry"]) / tr["entry"]) * p["size"]
                      for p, tr in ((p, p["trade"]) for p in open_pos))
        return realized + unreal

    prev_t = None
    for t, kind, tr in events:
        prev_t = t
        if kind == 1:
            eq = marked_equity(t)
            open_risk = sum(p["risk_dollars"] for p in open_pos) / eq if eq > 0 else 1
            if len(open_pos) >= pb.MAX_CONCURRENT:
                skipped_cap_count += 1
                continue
            if open_risk + risk_pct > pb.MAX_PORTFOLIO_RISK + 1e-9:
                skipped_cap_risk += 1
                continue
            ok, _ = admit(tr)
            if not ok:
                blocked.append(tr)
                continue
            risk_dollars = risk_pct * eq
            risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
            open_pos.append({"trade": tr, "risk_dollars": risk_dollars,
                             "size": risk_dollars / risk_frac,
                             "risk_frac": risk_frac})
            by_id[id(tr)] = open_pos[-1]
            opened_ids.add(id(tr))
        else:
            pos = by_id.pop(id(tr), None)
            if pos is None:
                continue
            _, _, net_r_, _ = pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)
            realized += pos["risk_dollars"] * net_r_
            open_pos.remove(pos)
        eq = marked_equity(t)
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    return {"final_equity": realized, "max_drawdown": max_dd,
            "skipped_cap_count": skipped_cap_count,
            "skipped_cap_risk": skipped_cap_risk,
            "blocked": blocked, "opened_ids": opened_ids}


def dist(trades, cost):
    rs = np.array([net_r(t, cost) for t in trades])
    if not len(rs):
        return {"n": 0}
    wins = rs[rs > 0]
    gw, gl = wins.sum(), -rs[rs <= 0].sum()
    return {"n": int(len(rs)), "expectancy_net_r": round(float(rs.mean()), 4),
            "win_rate_pct": round(float((rs > 0).mean()) * 100, 1),
            "profit_factor": round(float(gw / gl), 2) if gl > 0 else None}


def main():
    # ---------------- data ----------------
    stock_d, etf_d = {}, {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE4H, f"h4_{sym}.pkl"))
        stock_d[sym] = daily_closes_4h(df)
    for sym in ["SPY", "XLK", "SOXX", "XLF", "XLI", "XLY"]:
        df = pd.read_pickle(os.path.join(CACHED, f"d_{sym}.pkl"))
        s = df["Close"].copy()
        s.index = pd.to_datetime(s.index.tz_localize(None)
                                if s.index.tz is not None else s.index).normalize()
        etf_d[sym] = s.asfreq("1D").ffill().dropna()

    closes, trades = {}, []
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE4H, f"h4_{sym}.pkl"))
        df = pb.add_pine_indicators(df)
        closes[sym] = df["Close"]
        ts, _ = pb.gen_pine_trades(sym, df)
        trades.extend(ts)
    trades.sort(key=lambda t: t["entry_time"])
    print(f"canonical trades: {len(trades)}", flush=True)
    split_ts = pd.Timestamp("2025-01-01").tz_localize(trades[0]["entry_time"].tz)
    dev_end = split_ts

    def sig_date(tr):
        return pd.Timestamp(tr["signal_time"]).tz_convert(
            "America/New_York").tz_localize(None).normalize()

    # ---------------- flags: 6-formulation predeclared family ----------------
    def rel_median_series(etf, L):
        s = etf_d[etf]
        rs = s / s.shift(L) - 1.0 - (etf_d["SPY"] / etf_d["SPY"].shift(L) - 1.0)
        return rs.rolling(252, min_periods=126).median().shift(1)

    med = {(etf, L): rel_median_series(etf, L)
           for etf in SECTORS for L in (15, 20, 25)}

    flags = {}
    for fam in FAMS:
        if fam.startswith("SIGN"):
            kind, L = "SIGN", int(fam[4:])
        else:
            kind, L = "REL", int(fam[3:])
        fl = {}
        for tr in trades:
            sym = tr["symbol"]
            etf = SECTOR[sym]
            d = sig_date(tr)
            srs = ret_n(stock_d[sym], d, L) - ret_n(etf_d["SPY"], d, L)
            secrs = ret_n(etf_d[etf], d, L) - ret_n(etf_d["SPY"], d, L)
            m = med[(etf, L)].get(d, np.nan) if d in med[(etf, L)].index else np.nan
            if pd.isna(srs) or pd.isna(secrs) or (kind == "REL" and pd.isna(m)):
                fl[id(tr)] = False
            elif kind == "SIGN":
                fl[id(tr)] = bool(srs > 0 and secrs <= 0)
            else:
                fl[id(tr)] = bool(srs > 0 and secrs < m)
        flags[fam] = fl
        print(f"{fam}: flagged={sum(fl.values())}", flush=True)

    # ---------------- full-run sims: control + 6 x 4 costs ----------------
    def admit_all(tr):
        return True, ""

    sims = {}
    for cost in COSTS:
        bps = int(cost * 10000)
        sims[f"CONTROL@{bps}"] = (simulate_with_admission(
            trades, closes, cost, pb.RISK_PCT, admit_all), cost)
    for fam in FAMS:
        fl = flags[fam]

        def admit(tr, _fl=fl):
            return (False, "lone_wolf") if _fl[id(tr)] else (True, "")

        for cost in COSTS:
            bps = int(cost * 10000)
            sims[f"{fam}@{bps}"] = (simulate_with_admission(
                trades, closes, cost, pb.RISK_PCT, admit), cost)
    print("sims done", flush=True)

    R = {}  # per-trade net R cache by cost, keyed by id(tr)
    for tr in trades:
        R[id(tr)] = {cost: net_r(tr, cost) for cost in COSTS}

    def taken(key):
        port, cost = sims[key]
        return [tr for tr in trades if id(tr) in port["opened_ids"]], cost

    def blocked_set(fam, cost):
        """flagged AND taken by control at this cost (per-trade basis)."""
        ct, _ = taken(f"CONTROL@{int(cost*10000)}")
        ct_ids = {id(t) for t in ct}
        return [tr for tr in trades if flags[fam][id(tr)] and id(tr) in ct_ids]

    def per_trade_exp(subset, cost):
        if not subset:
            return None
        return float(np.mean([R[id(tr)][cost] for tr in subset]))

    results = {"formulations": FAMS, "costs_bps": [int(c * 10000) for c in COSTS],
               "n_trades": len(trades)}

    # ---------------- sanity: SIGN20@25 reproduces prior study ----------------
    s20 = dist(taken("SIGN20@25")[0], 0.0025)
    results["sanity_sign20_25bps"] = s20
    print("sanity SIGN20@25:", s20, flush=True)

    # ---------------- STEP 4: dev/val selection ----------------
    dev = [t for t in trades if t["entry_time"] < dev_end]
    val = [t for t in trades if t["entry_time"] >= dev_end]
    ct_dev = {id(t) for t in taken("CONTROL@25")[0] if t["entry_time"] < dev_end}
    sel = {}
    for fam in ("SIGN20", "REL20"):
        fl = flags[fam]
        ft = [t for t in taken(f"{fam}@25")[0] if t["entry_time"] < dev_end]
        blk = [t for t in trades if fl[id(t)] and id(t) in ct_dev
               and t["entry_time"] < dev_end]
        d_ctrl = per_trade_exp([t for t in trades if id(t) in ct_dev], 0.0025)
        d_flt = per_trade_exp(ft, 0.0025)
        d_blk = per_trade_exp(blk, 0.0025)
        sel[fam] = {"dev_delta": round(d_flt - d_ctrl, 4),
                    "dev_blocked_exp": round(d_blk, 4) if d_blk is not None else None,
                    "dev_control_exp": round(d_ctrl, 4),
                    "dev_taken_n": len(ft), "dev_blocked_n": len(blk)}
    results["dev_selection"] = sel
    dA, dB = sel["SIGN20"]["dev_delta"], sel["REL20"]["dev_delta"]
    okA = dA > 0 and sel["SIGN20"]["dev_blocked_exp"] < sel["SIGN20"]["dev_control_exp"]
    okB = dB > 0 and sel["REL20"]["dev_blocked_exp"] < sel["REL20"]["dev_control_exp"]
    if not okA and not okB:
        results["selected"] = None
        results["verdict"] = "FAIL"
        results["fail_reason"] = "no formulation satisfied dev gates"
        with open(OUT, "w") as f:
            json.dump(results, f, indent=1, default=str)
        print("FAIL: no formulation selected on dev", flush=True)
        return
    if abs(dA - dB) < 0.01:
        pick = ("SIGN20" if sel["SIGN20"]["dev_blocked_exp"] <= sel["REL20"]["dev_blocked_exp"]
                else "REL20")
        tie = True
    else:
        pick = "SIGN20" if (dA > dB and okA) or not okB else "REL20"
        tie = False
    # if the raw winner failed gates, fall back to the one that passed
    if pick == "SIGN20" and not okA:
        pick = "REL20"
    elif pick == "REL20" and not okB:
        pick = "SIGN20"
    results["selected"] = {"formulation": pick, "tiebreak_invoked": tie,
                           "dev_delta": sel[pick]["dev_delta"]}
    print(f"selected: {pick} (tiebreak={tie})", flush=True)

    # ---------------- STEP 4b: frozen validation ----------------
    c25 = 0.0025
    ct_val = [t for t in taken("CONTROL@25")[0] if t["entry_time"] >= dev_end]
    ft_val = [t for t in taken(f"{pick}@25")[0] if t["entry_time"] >= dev_end]
    v_ctrl = per_trade_exp(ct_val, c25)
    v_flt = per_trade_exp(ft_val, c25)
    results["validation"] = {
        "formulation": pick, "control_exp": round(v_ctrl, 4),
        "filtered_exp": round(v_flt, 4),
        "val_delta": round(v_flt - v_ctrl, 4),
        "control_n": len(ct_val), "filtered_n": len(ft_val)}
    print("validation:", results["validation"], flush=True)

    # ---------------- STEP 5: rolling walk-forward ----------------
    tz = trades[0]["entry_time"].tz
    wf, test_all_ctrl, test_all_flt = [], [], []
    for i, (trs, tre, tes, tee) in enumerate(ROLL):
        trs = pd.Timestamp(trs).tz_localize(tz)
        tre = pd.Timestamp(tre).tz_localize(tz) + pd.Timedelta(days=1)
        tes = pd.Timestamp(tes).tz_localize(tz)
        tee = pd.Timestamp(tee).tz_localize(tz) + pd.Timedelta(days=1)
        t_ctrl = [t for t in taken("CONTROL@25")[0] if tes <= t["entry_time"] < tee]
        t_flt = [t for t in taken(f"{pick}@25")[0] if tes <= t["entry_time"] < tee]
        tr_ctrl = [t for t in taken("CONTROL@25")[0] if trs <= t["entry_time"] < tre]
        tr_flt = [t for t in taken(f"{pick}@25")[0] if trs <= t["entry_time"] < tre]
        e = {"window": f"T{i+1}",
             "test_control_exp": round(per_trade_exp(t_ctrl, c25), 4) if t_ctrl else None,
             "test_filtered_exp": round(per_trade_exp(t_flt, c25), 4) if t_flt else None,
             "test_n": len(t_ctrl),
             "train_control_exp": round(per_trade_exp(tr_ctrl, c25), 4) if tr_ctrl else None,
             "train_filtered_exp": round(per_trade_exp(tr_flt, c25), 4) if tr_flt else None}
        e["test_delta"] = (round(e["test_filtered_exp"] - e["test_control_exp"], 4)
                           if e["test_control_exp"] is not None else None)
        wf.append(e)
        test_all_ctrl.extend(t_ctrl)
        test_all_flt.extend(t_flt)
    comb = {"combined_test_control_exp": round(per_trade_exp(test_all_ctrl, c25), 4),
            "combined_test_filtered_exp": round(per_trade_exp(test_all_flt, c25), 4),
            "combined_test_n": len(test_all_ctrl)}
    comb["combined_test_delta"] = round(comb["combined_test_filtered_exp"] -
                                       comb["combined_test_control_exp"], 4)
    results["walkforward"] = {"windows": wf, "combined": comb}
    print("walkforward combined:", comb, flush=True)

    # ---------------- STEP 6: year + regime splits ----------------
    years = {}
    for yr in sorted({t["entry_time"].year for t in trades}):
        yc = [t for t in taken("CONTROL@25")[0] if t["entry_time"].year == yr]
        yf = [t for t in taken(f"{pick}@25")[0] if t["entry_time"].year == yr]
        years[str(yr)] = {"control_n": len(yc),
                          "control_exp": round(per_trade_exp(yc, c25), 4) if yc else None,
                          "filtered_exp": round(per_trade_exp(yf, c25), 4) if yf else None}
        if yc and yf:
            years[str(yr)]["delta"] = round(years[str(yr)]["filtered_exp"] -
                                           years[str(yr)]["control_exp"], 4)
    results["yearly"] = years

    spy = etf_d["SPY"]
    sma200 = spy.rolling(200, min_periods=100).mean().shift(1)
    rv20 = spy.pct_change().rolling(20, min_periods=10).std().shift(1)
    rv_med = rv20.rolling(252, min_periods=126).median().shift(1)

    def regime(tr):
        d = sig_date(tr)
        try:
            bull = bool(spy.loc[d] > sma200.loc[d])
        except KeyError:
            bull = None
        try:
            hv = bool(rv20.loc[d] > rv_med.loc[d])
        except KeyError:
            hv = None
        return bull, hv

    regimes = {}
    for bname, bval in (("bull", True), ("weak", False)):
        for vname, vval in (("highvol", True), ("lowvol", False)):
            rc = [t for t in taken("CONTROL@25")[0]
                  if regime(t) == (bval, vval)]
            rf = [t for t in taken(f"{pick}@25")[0]
                  if regime(t) == (bval, vval)]
            key = f"{bname}_{vname}"
            if len(rc) >= 15:
                regimes[key] = {"control_n": len(rc),
                                "control_exp": round(per_trade_exp(rc, c25), 4),
                                "filtered_exp": round(per_trade_exp(rf, c25), 4) if rf else None,
                                "delta": round(per_trade_exp(rf, c25) - per_trade_exp(rc, c25), 4)
                                if rf else None}
            else:
                regimes[key] = {"thin": True, "control_n": len(rc)}
    results["regimes"] = regimes

    # ---------------- STEP 7: perturbation (already have flags) ----------------
    pert = {}
    for fam in FAMS:
        row = {}
        for cost in COSTS:
            bps = int(cost * 10000)
            tc = taken(f"CONTROL@{bps}")[0]
            tf = taken(f"{fam}@{bps}")[0]
            row[f"{bps}bps"] = round(per_trade_exp(tf, cost) - per_trade_exp(tc, cost), 4)
        pert[fam] = row
    results["perturbation"] = pert

    # cost stress on selected, pooled sim
    cs = {}
    for cost in COSTS:
        bps = int(cost * 10000)
        tc = taken(f"CONTROL@{bps}")[0]
        tf = taken(f"{pick}@{bps}")[0]
        cs[f"{bps}bps"] = {"delta": round(per_trade_exp(tf, cost) - per_trade_exp(tc, cost), 4),
                           "control_exp": round(per_trade_exp(tc, cost), 4),
                           "filtered_exp": round(per_trade_exp(tf, cost), 4)}
    results["cost_stress_selected"] = cs

    # ---------------- STEP 8: concentration ----------------
    blk = blocked_set(pick, c25)
    blk_r = [(t["symbol"], SECTOR[t["symbol"]], t["entry_time"].year, R[id(t)][c25])
             for t in blk]
    tot = sum(r for _, _, _, r in blk_r)
    results["concentration"] = {"blocked_total_r": round(tot, 2),
                                "blocked_n": len(blk)}
    for dim, idx in (("symbol", 0), ("sector", 1), ("year", 2)):
        agg = {}
        for s, sec, y, r in blk_r:
            k = (s, sec, y)[idx]
            agg[k] = agg.get(k, 0) + r
        ranked = sorted(agg.items(), key=lambda kv: kv[1])  # most negative first
        shares = {}
        for k in (1, 3, 5):
            top = ranked[:k]
            shares[f"top{k}_share_of_improvement"] = (
                round(sum(r for _, r in top) / tot, 3) if tot != 0 else None)
            shares[f"top{k}"] = [(str(nm), round(r, 2)) for nm, r in top]
        results["concentration"][dim] = shares

    # ---------------- STEP 9: bootstrap ----------------
    rng = np.random.default_rng(42)
    B = 10000
    all_tr = trades
    fl = flags[pick]
    base = np.array([R[id(t)][c25] for t in all_tr])
    is_blocked = np.array([fl[id(t)] for t in all_tr])
    deltas = np.empty(B)
    for b in range(B):
        idx = rng.integers(0, len(all_tr), len(all_tr))
        rb, bb = base[idx], is_blocked[idx]
        m_c = rb.mean()
        allowed = rb[~bb]
        m_f = allowed.mean() if len(allowed) else np.nan
        deltas[b] = m_f - m_c
    deltas = deltas[~np.isnan(deltas)]
    results["bootstrap_primary"] = {
        "B": B, "mean": round(float(deltas.mean()), 4),
        "p5": round(float(np.percentile(deltas, 5)), 4),
        "p50": round(float(np.percentile(deltas, 50)), 4),
        "p95": round(float(np.percentile(deltas, 95)), 4),
        "P_delta_gt_0": round(float((deltas > 0).mean()), 4)}
    ft25, _ = taken(f"{pick}@25")
    blk25 = blocked_set(pick, c25)
    rt = np.array([R[id(t)][c25] for t in ft25])
    rb_ = np.array([R[id(t)][c25] for t in blk25])
    gaps = np.empty(B)
    for b in range(B):
        gaps[b] = (rng.choice(rt, len(rt), replace=True).mean()
                   - rng.choice(rb_, len(rb_), replace=True).mean())
    results["bootstrap_secondary_blocked_vs_allowed"] = {
        "B": B, "mean": round(float(gaps.mean()), 4),
        "p5": round(float(np.percentile(gaps, 5)), 4),
        "p50": round(float(np.percentile(gaps, 50)), 4),
        "p95": round(float(np.percentile(gaps, 95)), 4),
        "P_gap_gt_0": round(float((gaps > 0).mean()), 4)}
    print("bootstrap primary:", results["bootstrap_primary"], flush=True)

    # ---------------- STEP 10: leave-one-symbol-out ----------------
    loso = {}
    for sym in WATCHLIST:
        sub = [t for t in trades if t["symbol"] != sym]
        pc = simulate_with_admission(sub, closes, c25, pb.RISK_PCT, admit_all)

        def adm(t, _fl=flags[pick]):
            return (False, "lw") if _fl[id(t)] else (True, "")

        pf = simulate_with_admission(sub, closes, c25, pb.RISK_PCT, adm)
        tc = [t for t in sub if id(t) in pc["opened_ids"]]
        tf = [t for t in sub if id(t) in pf["opened_ids"]]
        d = per_trade_exp(tf, c25) - per_trade_exp(tc, c25)
        loso[sym] = {"delta": round(d, 4), "control_n": len(tc),
                     "filtered_n": len(tf)}
    results["loso"] = loso
    print("loso done", flush=True)

    # ---------------- STEP 11: economic effect ----------------
    pc25, _ = sims["CONTROL@25"]
    pf25, _ = sims[f"{pick}@25"]
    tc25 = [t for t in trades if id(t) in pc25["opened_ids"]]
    tf25 = [t for t in trades if id(t) in pf25["opened_ids"]]
    blk25 = blocked_set(pick, c25)
    dc = dist(tc25, c25)
    df_ = dist(tf25, c25)
    ret_c = (pc25["final_equity"] / pb.START_EQUITY - 1) * 100
    ret_f = (pf25["final_equity"] / pb.START_EQUITY - 1) * 100
    dd_c = pc25["max_drawdown"] * 100
    dd_f = pf25["max_drawdown"] * 100
    results["economic"] = {
        "delta_expectancy": round(df_["expectancy_net_r"] - dc["expectancy_net_r"], 4),
        "delta_pf": round(df_["profit_factor"] - dc["profit_factor"], 2),
        "delta_dd_pct": round(dd_f - dd_c, 2),
        "trades_removed": len(blk25),
        "trades_added": 0,
        "control_taken": len(tc25), "filtered_taken": len(tf25),
        "cap_skipped_control": pc25["skipped_cap_count"] + pc25["skipped_cap_risk"],
        "cap_skipped_filtered": pf25["skipped_cap_count"] + pf25["skipped_cap_risk"],
        "opportunity_cost_blocked_exp": round(per_trade_exp(blk25, c25), 4),
        "return_per_unit_risk_control": round(ret_c / dd_c, 2) if dd_c else None,
        "return_per_unit_risk_filtered": round(ret_f / dd_f, 2) if dd_f else None,
        "control": {"exp": dc["expectancy_net_r"], "pf": dc["profit_factor"],
                    "dd": round(dd_c, 2), "ret": round(ret_c, 2)},
        "filtered": {"exp": df_["expectancy_net_r"], "pf": df_["profit_factor"],
                     "dd": round(dd_f, 2), "ret": round(ret_f, 2)},
    }
    # validation-period economic
    vc = [t for t in tc25 if t["entry_time"] >= dev_end]
    vf = [t for t in tf25 if t["entry_time"] >= dev_end]
    results["economic"]["validation_delta_exp"] = round(
        per_trade_exp(vf, c25) - per_trade_exp(vc, c25), 4)

    # ---------------- STEP 12: live paper status ----------------
    results["live_paper"] = {
        "note": "F_A (sign-cut 20d) papered live via v54_lonewolf_overlay.py "
                "(hourly cron lonewolf-overlay-cycle). This study does NOT "
                "change the overlay regardless of outcome.",
        "selected_formulation": pick,
        "overlay_formulation": "SIGN20",
        "match": pick == "SIGN20",
    }

    # ---------------- verdict per predeclared gates ----------------
    v = results["validation"]["val_delta"]
    y25 = years.get("2025", {}).get("delta")
    y26 = years.get("2026", {}).get("delta")
    a = v > 0.05
    b = comb["combined_test_delta"] > 0
    c = (y25 is not None and y25 > 0) and (y26 is not None and y26 > 0)
    sign_pos = sum(1 for f in ("SIGN15", "SIGN20", "SIGN25")
                   if pert[f]["25bps"] > 0)
    rel_pos = sum(1 for f in ("REL15", "REL20", "REL25")
                  if pert[f]["25bps"] > 0)
    d = sign_pos >= 2 and rel_pos >= 2
    e = all(vv["delta"] > 0 for vv in loso.values())
    f = results["bootstrap_primary"]["P_delta_gt_0"] >= 0.95
    g = cs["100bps"]["delta"] > 0
    top1 = results["concentration"]["symbol"]["top1_share_of_improvement"]
    h = top1 is not None and top1 < 0.5
    gates = {"a_val_delta_gt_0.05": bool(a),
             "b_rolling_combined_gt_0": bool(b),
             "c_val_years_2025_2026_positive": bool(c),
             "d_perturb_2of3_each_family": bool(d),
             "e_loso_no_collapse": bool(e),
             "f_bootstrap_P95": bool(f),
             "g_survives_100bps": bool(g),
             "h_top1_lt_50pct": bool(h)}
    results["gates"] = gates
    if a and b and c and d and e and f and g and h:
        verdict = "PASS"
    elif a and b and c:
        verdict = "MAYBE"
    else:
        verdict = "FAIL"
    results["verdict"] = verdict
    results["verdict_detail"] = {
        "val_delta": round(v, 4), "y2025_delta": y25, "y2026_delta": y26,
        "sign_lookbacks_positive": sign_pos, "rel_lookbacks_positive": rel_pos,
        "loso_min_delta": round(min(vv["delta"] for vv in loso.values()), 4),
        "bootstrap_P": results["bootstrap_primary"]["P_delta_gt_0"],
        "delta_100bps": cs["100bps"]["delta"], "top1_share": top1}

    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"VERDICT: {verdict}", flush=True)
    print(f"gates: {gates}", flush=True)
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
