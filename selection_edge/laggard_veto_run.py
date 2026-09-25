#!/usr/bin/env python3
"""Laggard-veto risk-control test (pre-registered 2026-09-24, Mike directive).

FROZEN RULE (no tuning, no variants): veto (exclude) any v54 candidate signal
where, at signal time, the stock ranks in the BOTTOM QUARTILE of RS3 or RS6,
where
  RS3 = 63-day total return minus SPY total return, strict point-in-time
  RS6 = 126-day total return minus SPY total return, strict point-in-time
Quartiles are cross-sectional across the 123-name working universe (131-name
PIT universe minus the 8 in-universe old-14 names, hard-masked), ranked with
only data available at the signal bar. Veto if bottom-quartile on EITHER
factor (union). No tuning of lookbacks, no threshold search, no exceptions.

Method (mirrors canonical_baseline/lonewolf_rerun.py exactly):
  1. Load the 4127 regenerated v54 candidates; drop the 8 masked names'
     candidates -> 3963 working candidates on the 123-name set.
  2. Compute strict-PIT RS3/RS6 per candidate with the EXACT construction
     from selection_edge/phase2_strength/phase2_strength.py
     (endpoint_idx 14h backoff, j>=W, cross-sectional average-rank quartile,
     n>=8 required). Veto at the CANDIDATE stage.
  3. Run worker (d)'s UNMODIFIED build_v5 (monkey-patched simlib.v54_signals)
     on: (a) all working candidates  -> masked baseline (no veto)
         (b) vetoed working candidates -> veto arm
     Identical population, identical machinery; the veto is the only delta.
  4. Val-only replays (signal >= 2025-01-01, fresh $75k) for decision rule 3.
  5. Full metric battery + pre-registered PASS/FAIL decision rule.

Outputs (all under selection_edge/):
  laggard_veto_decisions.json - per-candidate veto decision + RS legs
  laggard_veto_trades.json    - veto-arm accepted trades
  laggard_veto_baseline.json  - masked-baseline accepted trades
  laggard_veto_results.json   - all metrics + decision
  laggard_veto_report.md      - the report (written by a separate step)

Research only. Nothing frozen is modified.
"""

import bisect
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser(
    "~/workspace/quality-flow-scanner-v5/canonical_baseline"))
sys.path.insert(0, os.path.expanduser(
    "~/workspace/quality-flow-scanner-v5"))

import simlib
import scanner_rules as sr  # frozen, read-only
import run_portfolio
from run_ablation import (TAB131, START_EQUITY, RISK_USD, MAX_OPEN, HEAT_CAP,
                          net_r_legs, summarize)

BASE = simlib.BASE
OUT = os.path.expanduser("~/workspace/quality-flow-scanner-v5/selection_edge")
BPS_HEADLINE = 0.005
COST_LEVELS = [0.0025, 0.005, 0.0075, 0.01]
N_BOOT = 5000

MASKED8 = {"AMD", "ANET", "DRAM", "NIO", "PLTR", "QQQ", "SMCI", "SPCX"}
MASKED14 = MASKED8 | {"SOFI", "RKLB", "ONDS", "ASTX", "BBAI", "HOOD"}


def load_json(name, outdir=None):
    with open(os.path.join(outdir or BASE, name)) as fh:
        return json.load(fh)


def save_json(name, obj):
    with open(os.path.join(OUT, name), "w") as fh:
        json.dump(obj, fh, indent=1, default=str)


# --------------------------------------------------------------------------
# Strict-PIT RS3/RS6 — VERBATIM construction from
# selection_edge/phase2_strength/phase2_strength.py
# --------------------------------------------------------------------------

def endpoint_idx(series, t_end):
    # Strict PIT: the last daily bar COMPLETED as of signal time. Daily bars
    # are timestamped at midnight ET (start of day) but complete at 16:00 ET,
    # so a 13:30 signal on date D may only see D-1's bar (D's bar is still
    # forming), while a 16:00 signal may see D's bar. Backing the query
    # timestamp off by 14h implements exactly that (any offset in
    # (13.5h, 16h) works given the 09:30/13:30 bar grid).
    q = t_end - pd.Timedelta(hours=14)
    j = series.index.searchsorted(q, side="right") - 1
    return int(j) if j >= 0 else None


def build_rs_tables():
    """Precompute 63d/126d total-return series for the working universe."""
    universe = simlib.load_universe()
    WORKING = [x["symbol"] for x in universe if x["symbol"] not in MASKED14]
    assert len(universe) == 131
    assert len(WORKING) == 123, len(WORKING)
    closes = {}
    for s in sorted(set(WORKING) | {"SPY"}):
        closes[s] = simlib.load_d1(s)["Close"]
    RETW = {}
    for W in (63, 126):
        RETW[W] = {s: c / c.shift(W) - 1.0 for s, c in closes.items()}
    return WORKING, closes, RETW


def factor_value(closes, RETW, W, symbol, t_end):
    """Strict-PIT RS value (stock Wd return minus SPY). None if uncomputable."""
    cs, ss = closes.get(symbol), closes.get("SPY")
    if cs is None:
        return None
    j = endpoint_idx(cs, t_end)
    k = endpoint_idx(ss, t_end)
    if j is None or k is None or j < W or k < W:
        return None
    a, b = RETW[W][symbol].iloc[j], RETW[W]["SPY"].iloc[k]
    return None if (pd.isna(a) or pd.isna(b)) else float(a - b)


def bucket_signal(closes, RETW, WORKING, W, symbol, t_end):
    """Cross-sectional quartile bucket of `symbol` among WORKING names.

    Returns (bucket, value, n_valid). bucket None when the signal's own
    factor value is not computable or n < 8. VERBATIM from phase2_strength.
    """
    vals = {}
    for s in WORKING:
        v = factor_value(closes, RETW, W, s, t_end)
        if v is not None and np.isfinite(v):
            vals[s] = v
    n = len(vals)
    if symbol not in vals or n < 8:
        return None, None, n
    arr = pd.Series(vals)
    pct = (arr.rank(method="average")[symbol] - 1) / (n - 1)
    b = "top" if pct >= 0.75 else ("bottom" if pct < 0.25 else "middle")
    return b, vals[symbol], n


# --------------------------------------------------------------------------
# Veto decisions
# --------------------------------------------------------------------------

def apply_veto(candidates):
    path = os.path.join(OUT, "laggard_veto_decisions.json")
    if os.path.exists(path):
        dec = load_json("laggard_veto_decisions.json", OUT)
        kept = [s for s in candidates if not dec[s["signal_id"]]["veto"]]
        vetoed = [s for s in candidates if dec[s["signal_id"]]["veto"]]
        print(f"[lv] loaded veto decisions: {len(vetoed)} vetoed / "
              f"{len(candidates)}", flush=True)
        return kept, vetoed, dec

    WORKING, closes, RETW = build_rs_tables()
    # cache cross-sectional buckets per unique signal timestamp
    ts_cache = {}
    kept, vetoed, dec = [], [], {}
    n_ts = 0
    for s in candidates:
        sym = s["symbol"]
        sig_ts = pd.Timestamp(s["signal_bar_close_at"])
        if sig_ts not in ts_cache:
            b3, v3, n3 = {}, {}, 0
            b6, v6, n6 = {}, {}, 0
            # compute per-symbol values once, then rank
            vals3, vals6 = {}, {}
            for w in WORKING:
                a = factor_value(closes, RETW, 63, w, sig_ts)
                if a is not None and np.isfinite(a):
                    vals3[w] = a
                b = factor_value(closes, RETW, 126, w, sig_ts)
                if b is not None and np.isfinite(b):
                    vals6[w] = b
            n3, n6 = len(vals3), len(vals6)
            if n3 >= 8:
                r3 = pd.Series(vals3).rank(method="average")
                for w, rv in r3.items():
                    pct = (rv - 1) / (n3 - 1)
                    b3[w] = "top" if pct >= 0.75 else ("bottom" if pct < 0.25 else "middle")
            if n6 >= 8:
                r6 = pd.Series(vals6).rank(method="average")
                for w, rv in r6.items():
                    pct = (rv - 1) / (n6 - 1)
                    b6[w] = "top" if pct >= 0.75 else ("bottom" if pct < 0.25 else "middle")
            ts_cache[sig_ts] = (b3, vals3, n3, b6, vals6, n6)
            n_ts += 1
            if n_ts % 200 == 0:
                print(f"[lv] factor cache: {n_ts} timestamps", flush=True)
        b3, vals3, n3, b6, vals6, n6 = ts_cache[sig_ts]
        b_3 = b3.get(sym)
        b_6 = b6.get(sym)
        veto = (b_3 == "bottom") or (b_6 == "bottom")
        rec = {"symbol": sym,
               "signal_bar_close_at": s["signal_bar_close_at"],
               "rs3_value": vals3.get(sym),
               "rs3_bucket": b_3,
               "rs3_n_valid": n3,
               "rs6_value": vals6.get(sym),
               "rs6_bucket": b_6,
               "rs6_n_valid": n6,
               "veto": bool(veto),
               "reason": ("bottom-quartile"
                          if veto else ("unrankable" if (b_3 is None and b_6 is None)
                                        else "not-bottom"))}
        dec[s["signal_id"]] = rec
        (vetoed if veto else kept).append(s)
    save_json("laggard_veto_decisions.json", dec)
    print(f"[lv] veto: {len(vetoed)} vetoed / {len(candidates)} "
          f"({100.0*len(vetoed)/len(candidates):.2f}%)", flush=True)
    return kept, vetoed, dec


# --------------------------------------------------------------------------
# Identical V5 walk on a filtered candidate set
# (monkey-patch pattern from canonical_baseline/lonewolf_rerun.py)
# --------------------------------------------------------------------------

def group_by_sym(sigs):
    d = {}
    for s in sigs:
        d.setdefault(s["symbol"], []).append(s)
    return d


def run_walk(sigs_by_sym, tag):
    orig = simlib.v54_signals

    def patched(sym, ws, we):
        return sigs_by_sym.get(sym, []), simlib.load_h4(sym)

    simlib.v54_signals = patched
    try:
        accepted, counts = run_portfolio.build_v5(list(TAB131.keys()), tag=tag)
    finally:
        simlib.v54_signals = orig
    return accepted, counts


# --------------------------------------------------------------------------
# Equity curve — VERBATIM construction from worker (d)'s analyze.py
# (via canonical_baseline/lonewolf_rerun.py), extended to also return the
# (ts, equity) series for window-local drawdown measurement.
# --------------------------------------------------------------------------

def equity_curve(trades, return_series=False):
    syms = sorted({t["symbol"] for t in trades})
    closes = {}
    for s in syms:
        df = simlib.load_h4(s)
        m = {}
        for ts, c in zip(df.index, df["Close"].to_numpy()):
            m[sr.bar_close_at(ts, s).isoformat()] = float(c)
        closes[s] = m
    marks = set()
    tr_bounds = []
    for t in trades:
        s = t["symbol"]
        ec = sr.bar_close_at(pd.Timestamp(t["entry_ts"]), s).isoformat()
        xc = sr.bar_close_at(pd.Timestamp(t["exit_ts"]), s).isoformat()
        tr_bounds.append((s, ec, xc))
        cm = closes[s]
        for k in cm:
            if ec <= k <= xc:
                marks.add(k)
    tl = sorted(marks)
    n = len(tl)
    realized = np.zeros(n)
    unreal = np.zeros(n)
    for t, (s, ec, xc) in zip(trades, tr_bounds):
        i_e = bisect.bisect_left(tl, t["entry_ts"])
        realized[i_e:] -= t["entry_cost"]
        if t["tp1_taken"]:
            i_t = bisect.bisect_left(tl, t["tp1_fill_ts"])
            realized[i_t:] -= t["tp1_cost"]
        i_x = bisect.bisect_left(tl, t["exit_ts"])
        realized[i_x:] += t["gross_usd"] - t["exit_cost"]
        i0 = bisect.bisect_left(tl, ec)
        i1 = bisect.bisect_left(tl, xc)
        cm = closes[s]
        sh = t["shares"]
        tc = (sr.bar_close_at(pd.Timestamp(t["tp1_fill_ts"]), s).isoformat()
              if t["tp1_taken"] else None)
        entry = t["entry"]
        for i in range(i0, i1):
            px = cm.get(tl[i])
            if px is None:
                continue
            sh_i = sh / 2.0 if (tc is not None and tl[i] >= tc) else sh
            unreal[i] += (px - entry) * sh_i
    equity = START_EQUITY + realized + unreal
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    t_end_days = (pd.Timestamp(tl[-1]) - pd.Timestamp(tl[0])).days or 1
    cagr = float((equity[-1] / START_EQUITY) ** (365.25 / t_end_days) - 1)
    out = {
        "equity_start": float(equity[0]),
        "equity_end": float(equity[-1]),
        "total_return_pct": round(float(equity[-1] / START_EQUITY - 1) * 100, 2),
        "annualized_return_pct": round(cagr * 100, 2),
        "max_drawdown_pct": round(float(dd.min()) * 100, 2),
        "max_drawdown_usd": round(float((equity - peak).min()), 0),
        "max_drawdown_r": round(float((equity - peak).min()) / RISK_USD, 1),
    }
    if return_series:
        return out, tl, equity
    return out


def _coerce_ts(x):
    t = pd.Timestamp(x)
    return t if t.tzinfo is not None else t.tz_localize("America/New_York")


def window_maxdd(tl, equity, start, end):
    """Max drawdown (%) with peak and trough both inside [start, end)."""
    ts = pd.to_datetime(pd.Series(tl), utc=True).dt.tz_convert(
        "America/New_York")
    s, e = _coerce_ts(start), _coerce_ts(end)
    m = (ts >= s) & (ts < e)
    idx = np.where(m)[0]
    if len(idx) < 2:
        return None
    eq = equity[idx]
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    return round(float(dd.min()) * 100, 2)

# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------

def arm_metrics(trades, tag):
    """Headline + splits + concentration + left-tail for one book of trades."""
    rs = np.array([net_r_legs(t, BPS_HEADLINE) for t in trades], dtype=float)
    n = len(rs)
    m = {"tag": tag, "n": n}
    m["expectancy_r"] = float(rs.mean()) if n else 0.0
    m["win_rate_pct"] = float((rs > 0).mean() * 100) if n else 0.0
    m["profit_factor"] = (float(rs[rs > 0].sum() / -rs[rs <= 0].sum())
                          if n and (rs <= 0).any() and (rs > 0).any() else None)
    m["total_r"] = float(rs.sum()) if n else 0.0
    m["median_r"] = float(np.median(rs)) if n else 0.0
    m["avg_win_r"] = float(rs[rs > 0].mean()) if n and (rs > 0).any() else None
    m["avg_loss_r"] = float(rs[rs <= 0].mean()) if n and (rs <= 0).any() else None

    # cost ladder
    m["cost_ladder"] = {}
    for bps in COST_LEVELS:
        r2 = np.array([net_r_legs(t, bps) for t in trades], dtype=float)
        m["cost_ladder"][f"{bps*10000:.0f}bps"] = {
            "expectancy_r": float(r2.mean()) if n else 0.0,
            "total_r": float(r2.sum()) if n else 0.0,
        }

    # year splits (exit year, canonical convention)
    yrs = {}
    for t in trades:
        y = str(pd.Timestamp(t["exit_ts"]).year)
        yrs.setdefault(y, []).append(net_r_legs(t, BPS_HEADLINE))
    m["year_splits"] = {y: {"n": len(v), "expectancy_r": float(np.mean(v)),
                            "total_r": float(np.sum(v))}
                        for y, v in sorted(yrs.items())}

    # dev / val splits (signal date)
    dev = [net_r_legs(t, BPS_HEADLINE) for t in trades
           if pd.Timestamp(t["signal_bar_close_at"]) < pd.Timestamp("2025-01-01", tz="America/New_York")]
    val = [net_r_legs(t, BPS_HEADLINE) for t in trades
           if pd.Timestamp(t["signal_bar_close_at"]) >= pd.Timestamp("2025-01-01", tz="America/New_York")]
    m["dev"] = {"n": len(dev), "expectancy_r": float(np.mean(dev)) if dev else 0.0,
                "total_r": float(np.sum(dev)) if dev else 0.0}
    m["val"] = {"n": len(val), "expectancy_r": float(np.mean(val)) if val else 0.0,
                "total_r": float(np.sum(val)) if val else 0.0}

    # concentration: top-1/3/5 trades' share of total R
    order = np.argsort(rs)[::-1]
    tot = rs.sum()
    conc = {}
    for k in (1, 3, 5):
        topk = float(rs[order[:k]].sum()) if n else 0.0
        conc[f"top{k}"] = {
            "r": topk,
            "share_of_total_pct": (round(100.0 * topk / tot, 1)
                                   if n and tot != 0 else None),
        }
    m["concentration"] = conc

    # left-tail: worst 5% of trades, max losing streak (exit-time order)
    if n:
        k5 = max(1, int(round(0.05 * n)))
        worst = np.sort(rs)[:k5]
        m["worst_5pct"] = {"n": k5, "mean_r": float(worst.mean())}
        ex = sorted(trades, key=lambda t: t["exit_ts"])
        streak = best = 0
        for t in ex:
            if net_r_legs(t, BPS_HEADLINE) <= 0:
                streak += 1
                best = max(best, streak)
            else:
                streak = 0
        m["max_losing_streak"] = best
    else:
        m["worst_5pct"] = {"n": 0, "mean_r": None}
        m["max_losing_streak"] = 0
    return m


def bootstrap_delta(base_trades, veto_trades, seed=7):
    """Bootstrap veto-minus-baseline expectancy delta (independent books)."""
    rng = np.random.default_rng(seed)
    rb = np.array([net_r_legs(t, BPS_HEADLINE) for t in base_trades])
    rv = np.array([net_r_legs(t, BPS_HEADLINE) for t in veto_trades])
    deltas = np.empty(N_BOOT)
    for i in range(N_BOOT):
        deltas[i] = (rng.choice(rv, len(rv), replace=True).mean()
                     - rng.choice(rb, len(rb), replace=True).mean())
    return {"n": N_BOOT,
            "delta_mean": float(deltas.mean()),
            "delta_p2.5": float(np.percentile(deltas, 2.5)),
            "delta_p97.5": float(np.percentile(deltas, 97.5)),
            "p_delta_pos": float((deltas > 0).mean()),
            "p_delta_gt_neg0.05": float((deltas > -0.05).mean())}


def walk_forward(base_trades, veto_trades, eq_base, eq_veto):
    """Rolling 12mo-observe / 6mo-test windows on signal date.

    Per test window: expectancy delta (veto - baseline) and window-local
    max drawdown per arm from the pooled equity curves.
    """
    tmin = min(pd.Timestamp(t["signal_bar_close_at"])
               for t in base_trades + veto_trades)
    tmax = max(pd.Timestamp(t["signal_bar_close_at"])
               for t in base_trades + veto_trades)
    wins = []
    k = 0
    while True:
        s = tmin + pd.Timedelta(days=365) + k * pd.Timedelta(days=182)
        e = s + pd.Timedelta(days=182)
        if s >= tmax:
            break
        wins.append((s, e))
        k += 1
    tl_b, eq_b = eq_base
    tl_v, eq_v = eq_veto
    out = []
    for s, e in wins:
        wb = [net_r_legs(t, BPS_HEADLINE) for t in base_trades
              if s <= pd.Timestamp(t["signal_bar_close_at"]) < e]
        wv = [net_r_legs(t, BPS_HEADLINE) for t in veto_trades
              if s <= pd.Timestamp(t["signal_bar_close_at"]) < e]
        eb = float(np.mean(wb)) if wb else None
        ev = float(np.mean(wv)) if wv else None
        out.append({
            "start": s.strftime("%Y-%m-%d"), "end": e.strftime("%Y-%m-%d"),
            "n_base": len(wb), "n_veto": len(wv),
            "e_base": eb, "e_veto": ev,
            "delta_e": (ev - eb) if (ev is not None and eb is not None) else None,
            "dd_base_pct": window_maxdd(tl_b, eq_b, s, e),
            "dd_veto_pct": window_maxdd(tl_v, eq_v, s, e),
        })
    dd_wins = [w for w in out
               if w["dd_base_pct"] is not None and w["dd_veto_pct"] is not None]
    dd_hit = sum(1 for w in dd_wins if w["dd_veto_pct"] > w["dd_base_pct"])
    d_wins = [w for w in out if w["delta_e"] is not None]
    return {"windows": out,
            "n_windows": len(out),
            "dd_improved_frac": (dd_hit / len(dd_wins)) if dd_wins else None,
            "dd_windows_n": len(dd_wins),
            "delta_e_mean": float(np.mean([w["delta_e"] for w in d_wins]))
                           if d_wins else None}


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    cands = load_json("lonewolf_candidates.json")
    assert len(cands) == 4127, f"candidate count drift: {len(cands)}"
    work = [s for s in cands if s["symbol"] not in MASKED14]
    nmask = len(cands) - len(work)
    print(f"[lv] working candidates: {len(work)} (masked out {nmask})",
          flush=True)
    assert len(work) == 3963

    kept, vetoed, dec = apply_veto(work)
    by_reason = {}
    for d in dec.values():
        by_reason[d["reason"]] = by_reason.get(d["reason"], 0) + 1
    print(f"[lv] veto reasons: {by_reason}", flush=True)

    # --- masked baseline (no veto) ---
    acc_base, cnt_base = run_walk(group_by_sym(work), tag="LV-baseline")
    print(f"[lv] baseline accepted: {len(acc_base)}", flush=True)
    # --- veto arm ---
    acc_veto, cnt_veto = run_walk(group_by_sym(kept), tag="LV-veto")
    print(f"[lv] veto accepted: {len(acc_veto)}", flush=True)

    for t in acc_base:
        for bps in COST_LEVELS:
            t[f"net_r_{bps*10000:.0f}bps"] = net_r_legs(t, bps)
    for t in acc_veto:
        for bps in COST_LEVELS:
            t[f"net_r_{bps*10000:.0f}bps"] = net_r_legs(t, bps)
    save_json("laggard_veto_baseline.json", acc_base)
    save_json("laggard_veto_trades.json", acc_veto)

    eq_base, tl_b, e_b = equity_curve(acc_base, return_series=True)
    eq_veto, tl_v, e_v = equity_curve(acc_veto, return_series=True)
    print("[lv] baseline:", json.dumps(eq_base, indent=1), flush=True)
    print("[lv] veto:    ", json.dumps(eq_veto, indent=1), flush=True)

    # --- val-only replays (decision rule 3) ---
    VAL0 = "2025-01-01"
    work_val = [s for s in work if s["signal_bar_close_at"] >= VAL0]
    kept_val = [s for s in kept if s["signal_bar_close_at"] >= VAL0]
    acc_bval, _ = run_walk(group_by_sym(work_val), tag="LV-baseline-val")
    acc_vval, _ = run_walk(group_by_sym(kept_val), tag="LV-veto-val")
    for t in acc_bval + acc_vval:
        for bps in COST_LEVELS:
            t[f"net_r_{bps*10000:.0f}bps"] = net_r_legs(t, bps)
    eq_bval = equity_curve(acc_bval)
    eq_vval = equity_curve(acc_vval)
    print(f"[lv] val-only: baseline {len(acc_bval)} trades dd={eq_bval['max_drawdown_pct']}% | "
          f"veto {len(acc_vval)} trades dd={eq_vval['max_drawdown_pct']}%", flush=True)

    # --- metric battery ---
    m_base = arm_metrics(acc_base, "baseline-no-veto")
    m_veto = arm_metrics(acc_veto, "veto")
    m_base["equity"] = eq_base
    m_veto["equity"] = eq_veto
    m_base["skip_counts"] = cnt_base
    m_veto["skip_counts"] = cnt_veto

    # vetoed trades that the baseline book actually took (mechanism read)
    veto_ids = {s["signal_id"] for s in vetoed}
    vetoed_in_base = [t for t in acc_base if t["signal_id"] in veto_ids]
    rvib = [net_r_legs(t, BPS_HEADLINE) for t in vetoed_in_base]
    # replacement decomposition: baseline trades dropped vs newly admitted
    base_ids = {t["signal_id"] for t in acc_base}
    veto_ids_acc = {t["signal_id"] for t in acc_veto}
    dropped = [t for t in acc_base if t["signal_id"] not in veto_ids_acc]
    new = [t for t in acc_veto if t["signal_id"] not in base_ids]
    rd = [net_r_legs(t, BPS_HEADLINE) for t in dropped]
    rn = [net_r_legs(t, BPS_HEADLINE) for t in new]

    boot = bootstrap_delta(acc_base, acc_veto)
    wf = walk_forward(acc_base, acc_veto, (tl_b, e_b), (tl_v, e_v))

    # subperiod drawdown cross-check on pooled curves
    dd_dev_base = window_maxdd(tl_b, e_b, "2023-01-01", "2025-01-01")
    dd_dev_veto = window_maxdd(tl_v, e_v, "2023-01-01", "2025-01-01")
    dd_val_base = window_maxdd(tl_b, e_b, "2025-01-01", "2027-01-01")
    dd_val_veto = window_maxdd(tl_v, e_v, "2025-01-01", "2027-01-01")

    # --- pre-registered decision rule ---
    dd_b = abs(eq_base["max_drawdown_pct"])
    dd_v = abs(eq_veto["max_drawdown_pct"])
    dd_reduction = (dd_b - dd_v) / dd_b if dd_b else 0.0
    e_delta = m_veto["expectancy_r"] - m_base["expectancy_r"]
    dd_bval = abs(eq_bval["max_drawdown_pct"])
    dd_vval = abs(eq_vval["max_drawdown_pct"])
    val_dd_improved = dd_vval < dd_bval
    rule1 = dd_reduction >= 0.25
    rule2 = e_delta >= -0.05
    rule3 = val_dd_improved
    verdict = "PASS" if (rule1 and rule2 and rule3) else "FAIL"

    results = {
        "pre_registration": "selection_edge/laggard_veto_prereg.md (frozen 2026-09-24)",
        "universe": "123-symbol masked working set (131 PIT minus 8 in-universe old-14)",
        "candidates": {"total": len(cands), "masked_out": nmask,
                       "working": len(work), "vetoed": len(vetoed),
                       "vetoed_pct": round(100.0 * len(vetoed) / len(work), 2),
                       "kept": len(kept), "veto_reasons": by_reason},
        "baseline": m_base,
        "veto": m_veto,
        "head_comparison_50bps": {
            "expectancy_delta_r": round(e_delta, 4),
            "maxdd_reduction_rel": round(dd_reduction, 4),
            "total_r_base": m_base["total_r"], "total_r_veto": m_veto["total_r"],
            "n_base": m_base["n"], "n_veto": m_veto["n"],
        },
        "mechanism": {
            "vetoed_trades_in_baseline_book": {
                "n": len(vetoed_in_base),
                "total_r": round(float(np.sum(rvib)), 2) if rvib else 0.0,
                "mean_r": round(float(np.mean(rvib)), 4) if rvib else None},
            "dropped_by_reshuffle": {
                "n": len(dropped),
                "total_r": round(float(np.sum(rd)), 2) if rd else 0.0,
                "mean_r": round(float(np.mean(rd)), 4) if rd else None},
            "newly_admitted": {
                "n": len(new),
                "total_r": round(float(np.sum(rn)), 2) if rn else 0.0,
                "mean_r": round(float(np.mean(rn)), 4) if rn else None},
        },
        "val_only_replay": {
            "n_base": len(acc_bval), "n_veto": len(acc_vval),
            "maxdd_base_pct": eq_bval["max_drawdown_pct"],
            "maxdd_veto_pct": eq_vval["max_drawdown_pct"],
            "expectancy_base_r": round(float(np.mean(
                [net_r_legs(t, BPS_HEADLINE) for t in acc_bval])), 4) if acc_bval else 0.0,
            "expectancy_veto_r": round(float(np.mean(
                [net_r_legs(t, BPS_HEADLINE) for t in acc_vval])), 4) if acc_vval else 0.0,
        },
        "subperiod_drawdown_crosscheck": {
            "dev_base_pct": dd_dev_base, "dev_veto_pct": dd_dev_veto,
            "val_base_pct": dd_val_base, "val_veto_pct": dd_val_veto},
        "bootstrap_expectancy_delta": boot,
        "walk_forward": wf,
        "decision_rule": {
            "rule1_dd_reduction_ge_25pct": {"value": round(dd_reduction, 4),
                                            "pass": bool(rule1)},
            "rule2_expectancy_within_0.05r": {"value": round(e_delta, 4),
                                             "pass": bool(rule2)},
            "rule3_val_window_dd_improved": {
                "base_pct": eq_bval["max_drawdown_pct"],
                "veto_pct": eq_vval["max_drawdown_pct"],
                "pass": bool(val_dd_improved)},
        },
        "verdict": verdict,
        "honesty_caveat": ("Hypothesis formed on this same dataset "
                           "(selection_edge/SELECTION.md); confirmatory-with-caveats, "
                           "not independent validation. Forward data is the real arbiter."),
    }
    save_json("laggard_veto_results.json", results)
    print(json.dumps({"verdict": verdict,
                      "decision_rule": results["decision_rule"],
                      "head_comparison_50bps": results["head_comparison_50bps"]},
                     indent=1), flush=True)


if __name__ == "__main__":
    main()
