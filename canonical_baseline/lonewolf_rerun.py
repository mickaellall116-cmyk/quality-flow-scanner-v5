"""Lone-wolf rerun under strict point-in-time against the corrected baseline.

Worker (e) of the canonical-baseline rebuild.

FROZEN RULE (no tuning, no variants): for each candidate v54 signal, compute
stock 20-trading-day RS vs SPY and sector-ETF 20-trading-day RS vs SPY, both
with strict-PIT endpoints (last completed daily bar as of the signal-bar
close, PIT_FEATURES.md rules 2-3). BLOCK the trade when stock RS > 0 AND
sector RS <= 0. The block is applied at the CANDIDATE stage; the identical
V5 portfolio walk (worker d's build_v5, unmodified, via monkey-patched
simlib.v54_signals) then runs on the filtered set.

Writes (all under canonical_baseline/):
  lonewolf_candidates.json       - the 4127 candidate v54 signals (regenerated)
  lonewolf_block_decisions.json  - per-candidate block decision + RS legs
  lonewolf_trades.json           - accepted trades on the filtered set
  lonewolf_rerun.json            - headline + sensitivity + splits
  LONEWOLF_RERUN.md              - the report
"""

import bisect
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import simlib
import scanner_rules as sr  # frozen, read-only
import run_portfolio
from run_ablation import (TAB131, START_EQUITY, RISK_USD, MAX_OPEN, HEAT_CAP,
                          net_r_legs, summarize, exec_modeb)

BASE = simlib.BASE
BPS_HEADLINE = 0.005
COST_LEVELS = [0.0025, 0.005, 0.0075, 0.01]

# ---------------------------------------------------------------------------
# Sector map: yfinance sector label -> sector ETF (standard GICS -> ETF map)
# ---------------------------------------------------------------------------
SECTOR_ETF = {
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Consumer Cyclical": "XLY",
    "Healthcare": "XLV",
    "Industrials": "XLI",
    "Communication Services": "XLC",
    "Energy": "XLE",
    "Consumer Defensive": "XLP",
    "Basic Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
}
# Symbols with sector None/ETF (SPY, QQQ, IWM, TLT, XLE, XLF, SMH, DIA,
# ARKK, GLD, DRAM) have no GICS sector -> pass through unfiltered
# (documented decision; SPY's own RS vs SPY is exactly 0, never blocked).


def load_json(name):
    with open(os.path.join(BASE, name)) as fh:
        return json.load(fh)


def save_json(name, obj):
    with open(os.path.join(BASE, name), "w") as fh:
        json.dump(obj, fh, indent=1)


# ---------------------------------------------------------------------------
# Stage 1: regenerate the candidate set (worker d's exact signal path)
# ---------------------------------------------------------------------------

def gen_candidates():
    path = os.path.join(BASE, "lonewolf_candidates.json")
    if os.path.exists(path):
        cands = load_json("lonewolf_candidates.json")
        print(f"[e] loaded {len(cands)} cached candidates", flush=True)
        return cands
    all_sigs = []
    for sym in TAB131:
        ws, we = TAB131[sym]
        sigs, _df = simlib.v54_signals(sym, ws, we)
        all_sigs.extend(sigs)
    all_sigs.sort(key=lambda s: (s["signal_bar_close_at"], s["symbol"]))
    save_json("lonewolf_candidates.json", all_sigs)
    print(f"[e] generated {len(all_sigs)} candidates", flush=True)
    return all_sigs


# ---------------------------------------------------------------------------
# Stage 2: strict-PIT lone-wolf block
# ---------------------------------------------------------------------------

_D1 = {}

def d1(sym):
    if sym not in _D1:
        _D1[sym] = simlib.load_d1(sym)["Close"]
    return _D1[sym]


def strict_endpoint_idx(daily_idx, signal_ts):
    """Index position of the last daily bar COMPLETED by signal_ts.

    Daily bars are stamped at midnight ET and complete at 16:00 ET, so a
    first-4H-bar signal (13:30 close) resolves to the previous trading day,
    a second-bar signal (16:00 close) to the signal date itself.
    (PIT_FEATURES.md rules 2-3.)
    """
    completion = daily_idx + pd.Timedelta(hours=16)
    return int(completion.searchsorted(signal_ts, side="right") - 1)


def rs20_strict_pit(stock_close, bench_close, signal_ts):
    """20-trading-day RS of stock vs benchmark, strict-PIT endpoints.

    Both legs end at the last completed daily bar as of signal_ts and start
    20 trading days earlier. Returns None when the window is unavailable.
    """
    idx = stock_close.index
    j = strict_endpoint_idx(idx, signal_ts)
    if j < 20:
        return None
    bidx = bench_close.index
    bj = strict_endpoint_idx(bidx, signal_ts)
    if bj < 20:
        return None
    # calendar alignment: endpoint dates must match, else PIT-ambiguous
    if idx[j].date() != bidx[bj].date():
        return None
    c1, c0 = float(stock_close.iloc[j]), float(stock_close.iloc[j - 20])
    b1, b0 = float(bench_close.iloc[bj]), float(bench_close.iloc[bj - 20])
    if min(c0, b0) <= 0 or any(pd.isna(x) for x in (c1, c0, b1, b0)):
        return None
    return (c1 / c0 - 1.0) - (b1 / b0 - 1.0)


def apply_block(candidates):
    """Returns (kept, blocked, decisions). decisions keyed by signal_id."""
    path = os.path.join(BASE, "lonewolf_block_decisions.json")
    if os.path.exists(path):
        dec = load_json("lonewolf_block_decisions.json")
        kept = [s for s in candidates if not dec[s["signal_id"]]["blocked"]]
        blocked = [s for s in candidates if dec[s["signal_id"]]["blocked"]]
        print(f"[e] loaded block decisions: {len(blocked)} blocked / "
              f"{len(candidates)}", flush=True)
        return kept, blocked, dec

    sectors_raw = load_json("sectors_raw.json")
    spy = d1("SPY")
    sym_etf = {}
    for s in sectors_raw:
        sec = sectors_raw[s].get("sector")
        sym_etf[s] = SECTOR_ETF.get(sec)  # None -> ETF symbol -> pass-through

    kept, blocked, dec = [], [], {}
    for s in candidates:
        sym = s["symbol"]
        etf = sym_etf.get(sym)
        sig_ts = pd.Timestamp(s["signal_bar_close_at"])
        rec = {"symbol": sym, "signal_bar_close_at": s["signal_bar_close_at"],
               "sector_etf": etf, "rs_stock": None, "rs_sector": None,
               "blocked": False, "reason": None}
        if etf is not None:
            rs_s = rs20_strict_pit(d1(sym), spy, sig_ts)
            rs_e = rs20_strict_pit(d1(etf), spy, sig_ts)
            rec["rs_stock"] = rs_s
            rec["rs_sector"] = rs_e
            if rs_s is None or rs_e is None:
                rec["reason"] = "rs-unavailable"
            elif rs_s > 0 and rs_e <= 0:
                rec["blocked"] = True
                rec["reason"] = "lone-wolf"
        else:
            rec["reason"] = "etf-passthrough"
        dec[s["signal_id"]] = rec
        (blocked if rec["blocked"] else kept).append(s)
    save_json("lonewolf_block_decisions.json", dec)
    print(f"[e] block: {len(blocked)} blocked / {len(candidates)} "
          f"({100.0*len(blocked)/len(candidates):.2f}%)", flush=True)
    return kept, blocked, dec


# ---------------------------------------------------------------------------
# Stage 3: identical V5 portfolio walk on the filtered candidate set
# ---------------------------------------------------------------------------

def run_walk(filtered_by_sym, tag):
    """Run worker (d)'s unmodified build_v5 on a filtered candidate set."""
    orig = simlib.v54_signals

    def patched(sym, ws, we):
        return filtered_by_sym.get(sym, []), simlib.load_h4(sym)

    simlib.v54_signals = patched
    try:
        accepted, counts = run_portfolio.build_v5(list(TAB131.keys()), tag=tag)
    finally:
        simlib.v54_signals = orig
    return accepted, counts


def group_by_sym(sigs):
    d = {}
    for s in sigs:
        d.setdefault(s["symbol"], []).append(s)
    return d


# ---------------------------------------------------------------------------
# Equity curve + max DD (verbatim construction from worker d's analyze.py)
# ---------------------------------------------------------------------------

def equity_curve(trades):
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
    return {
        "equity_start": float(equity[0]),
        "equity_end": float(equity[-1]),
        "total_return_pct": round(float(equity[-1] / START_EQUITY - 1) * 100, 2),
        "annualized_return_pct": round(cagr * 100, 2),
        "max_drawdown_pct": round(float(dd.min()) * 100, 2),
        "max_drawdown_usd": round(float((equity - peak).min()), 0),
        "max_drawdown_r": round(float((equity - peak).min()) / RISK_USD, 1),
    }


def main():
    cands = gen_candidates()
    assert len(cands) == 4127, f"candidate count drift: {len(cands)}"
    kept, blocked, dec = apply_block(cands)

    # --- unfiltered replication check: same walk, full candidate set ---
    acc_base, cnt_base = run_walk(group_by_sym(cands), tag="V5-replicate")
    print(f"[e] replication: accepted {len(acc_base)} "
          f"(canonical 374)", flush=True)

    # --- filtered run ---
    acc_f, cnt_f = run_walk(group_by_sym(kept), tag="V5-lonewolf")
    print(f"[e] filtered: accepted {len(acc_f)}", flush=True)

    for bps in COST_LEVELS:
        for t in acc_f:
            t[f"net_r_{bps*10000:.0f}bps"] = net_r_legs(t, bps)
    save_json("lonewolf_trades.json", acc_f)

    levels = {}
    for bps in COST_LEVELS:
        rs = [net_r_legs(t, bps) for t in acc_f]
        levels[f"{bps*10000:.0f}bps"] = summarize(
            f"V5-lonewolf {bps*10000:.0f}bps", rs)
    eq = equity_curve(acc_f)
    out = {
        "candidates": len(cands),
        "blocked": len(blocked),
        "blocked_pct": round(100.0 * len(blocked) / len(cands), 2),
        "kept": len(kept),
        "replication_check": {"accepted": len(acc_base),
                              "canonical": 374,
                              "match": len(acc_base) == 374},
        "accepted": len(acc_f),
        "skip_counts": cnt_f,
        "levels": levels,
        "equity": eq,
    }
    save_json("lonewolf_rerun.json", out)
    print(json.dumps(out, indent=1), flush=True)


if __name__ == "__main__":
    main()
