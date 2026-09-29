#!/usr/bin/env python3
"""Liquidity/volatility-adjusted transaction cost estimate (research audit).

Feasibility: the pipeline has 4H OHLCV per symbol (no spread/quote data).
We estimate the all-in one-way cost per trade from what exists:

  cost_bps = half effective spread + market impact
  half effective spread: Corwin-Schultz (2012) estimator from daily OHLC
                         resampled from the 4H bars (no spread data exists,
                         so this is estimated, not observed).
  market impact: 10 bps per 1% of ADV participation
                 (standard practitioner rule of thumb; impact_bps =
                 1000 * notional / ADV).

Trade notional: position sized by the standing rule, risk per trade / risk_frac
  - research sizing: $10k book, 1% risk  -> $100 risk per trade
  - live sizing:     $75k book, $750 risk -> $750 risk per trade
  (risk_frac per trade recovered from the regenerated baseline trade list.)

ADV: mean daily dollar volume over the study window per symbol.

Compares the estimated all-in one-way cost to the flat 25bps the studies
apply once per trade on the blended return (which bundles entry + both
exit legs into a single number).

Research only. Nothing frozen touched.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "research_audit", "execution")
os.makedirs(OUTDIR, exist_ok=True)
CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
sys.path.insert(0, BASE)
import pine_backtest as pb  # noqa: E402  (UNMODIFIED, indicators only)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]


def daily(df4h):
    d = df4h.tz_convert("America/New_York").tz_localize(None)
    agg = {"Open": "first", "High": "max", "Low": "min",
           "Close": "last", "Volume": "sum"}
    return d.resample("1D").agg(agg).dropna()


def corwin_schultz(hi, lo):
    """Mean Corwin-Schultz effective spread (fraction of price) from a
    High/Low series. Applied to 4H bars (less overnight contamination than
    daily); still an UPPER-BOUND-biased estimator when volatility >> spread
    (e.g. QQQ prints ~7.5bps half-spread here vs ~1bp true effective)."""
    h, l = np.asarray(hi, float), np.asarray(lo, float)
    s = []
    for t in range(1, len(h)):
        h2, l2 = max(h[t], h[t - 1]), min(l[t], l[t - 1])
        beta = (np.log(h[t] / l[t]) ** 2 + np.log(h[t - 1] / l[t - 1]) ** 2)
        gamma = np.log(h2 / l2) ** 2
        k2 = (3 - 2 * np.sqrt(2))
        alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / k2 - np.sqrt(gamma / k2)
        sp = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
        s.append(max(sp, 0.0))
    return float(np.mean(s)) if s else 0.0


def main():
    sym_stats = {}
    zero_vol = {}
    for sym in WATCHLIST:
        df4 = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        zero_vol[sym] = int((df4["Volume"] == 0).sum())
        d = daily(df4)
        adv = float((d["Close"] * d["Volume"]).mean())
        cs = corwin_schultz(df4["High"], df4["Low"])  # 4H bars
        sym_stats[sym] = {"adv_dollar": adv, "cs_spread_frac": cs,
                          "cs_half_spread_bps": cs * 10000 / 2,
                          "n_days": len(d)}

    # per-trade risk_frac from the regenerated baseline list
    trades = []
    for s in WATCHLIST:
        df = pb.add_pine_indicators(pd.read_pickle(os.path.join(CACHE, f"h4_{s}.pkl")))
        t, _ = pb.gen_pine_trades(s, df)
        trades.extend(t)
    trades.sort(key=lambda t: t["entry_time"])
    assert len(trades) == 237

    rows = []
    for tr in trades:
        s = tr["symbol"]
        rf = (tr["entry"] - tr["stop"]) / tr["entry"]
        adv = sym_stats[s]["adv_dollar"]
        half_sp = sym_stats[s]["cs_half_spread_bps"]
        for book, risk in (("research_10k", 100.0), ("live_75k", 750.0)):
            notional = risk / rf
            part = notional / adv if adv > 0 else np.nan
            impact = 1000 * part  # 10bps per 1% of ADV
            total = half_sp + impact
            rows.append({"symbol": s, "book": book, "risk_frac": rf,
                         "notional": notional, "adv": adv,
                         "participation_pct": part * 100,
                         "half_spread_bps": half_sp,
                         "impact_bps": impact, "total_bps": total})
    R = pd.DataFrame(rows)
    summ = {}
    for book in ("research_10k", "live_75k"):
        b = R[R["book"] == book]
        summ[book] = {
            "avg_total_bps": round(float(b["total_bps"].mean()), 2),
            "avg_half_spread_bps": round(float(b["half_spread_bps"].mean()), 2),
            "avg_impact_bps": round(float(b["impact_bps"].mean()), 3),
            "avg_participation_pct_adv": round(float(b["participation_pct"].mean()), 4),
            "max_participation_pct_adv": round(float(b["participation_pct"].max()), 3),
            "max_total_bps": round(float(b["total_bps"].max()), 2),
            "avg_notional": round(float(b["notional"].mean()), 0),
        }
    per_sym = {}
    trade_counts = R[R["book"] == "live_75k"]["symbol"].value_counts().to_dict()
    for s in WATCHLIST:
        b = R[(R["book"] == "live_75k") & (R["symbol"] == s)]
        per_sym[s] = {
            "adv_dollar_m": round(sym_stats[s]["adv_dollar"] / 1e6, 1),
            "cs_half_spread_bps_4h": round(sym_stats[s]["cs_half_spread_bps"], 1),
            "n_baseline_trades": int(trade_counts.get(s, 0)),
            "avg_total_bps_live": (round(float(b["total_bps"].mean()), 2)
                                   if len(b) else None),
            "avg_participation_pct_adv": (round(float(b["participation_pct"].mean()), 4)
                                          if len(b) else None),
            "zero_volume_4h_bars": zero_vol[s],
        }

    out = {"per_symbol": per_sym, "summary": summ,
           "method": ("half-spread = Corwin-Schultz from daily OHLC resampled "
                      "from 4H bars; impact = 10bps per 1% of ADV; one-way, "
                      "per trade")}
    with open(os.path.join(OUTDIR, "liquidity_cost_estimate.json"), "w") as f:
        json.dump(out, f, indent=1)

    print("feasibility: YES — 4H OHLCV exists for all 14 symbols "
          f"(zero-volume bars: {sum(zero_vol.values())} total)")
    print("no quote/spread data in pipeline; spread is ESTIMATED (Corwin-Schultz "
          "on 4H bars — upward-biased upper bound)")
    for book, label in (("research_10k", "research $10k/1%"), ("live_75k", "live $75k/$750")):
        s = summ[book]
        print(f"[{label}] avg all-in one-way cost: {s['avg_total_bps']}bps "
              f"(spread {s['avg_half_spread_bps']} + impact {s['avg_impact_bps']}), "
              f"avg participation {s['avg_participation_pct_adv']}% of ADV, "
              f"max {s['max_participation_pct_adv']}%")
    print("\nper-symbol (live sizing):")
    for s in WATCHLIST:
        p = per_sym[s]
        allin = f"{p['avg_total_bps_live']:>5.2f}" if p['avg_total_bps_live'] is not None else "  n/a"
        part = f"{p['avg_participation_pct_adv']:.4f}" if p['avg_participation_pct_adv'] is not None else "n/a"
        print(f"  {s:5s} ADV ${p['adv_dollar_m']:>8.1f}M  half-spread {p['cs_half_spread_bps_4h']:>5.1f}bps  "
              f"all-in {allin}bps  part {part}%  "
              f"trades={p['n_baseline_trades']:>2d}  zeroVol4h={p['zero_volume_4h_bars']}")


if __name__ == "__main__":
    main()
