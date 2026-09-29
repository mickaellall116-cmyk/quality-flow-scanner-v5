#!/usr/bin/env python3
"""FVG-as-entry challenger ROBUSTNESS study (Mike's spec, 2026-09-24).

Question: is FVG-as-entry genuinely better than the 4H Hybrid baseline, or did
+0.285R vs +0.239R come only from changing which trades were taken?

Variants (all OR-ed with the canonical pine_buy_signal; exits = frozen Mode B
via gen_pine_trades; research only, nothing frozen touched):
  BASE    canonical Hybrid
  FVG     canonical OR fvg_sub (current sidecar definition)
  FVG_P1  fvg with stricter volume: vol > 1.2 * vol_ma            (pre-declared)
  FVG_P2  fvg WITHOUT the HOT_ATR "safe" filter                   (pre-declared)
  FVG_P3  fvg WITHOUT the close > e21 requirement                 (pre-declared)
Perturbations are nearby-definition checks, NOT optimization. 2-3 variants,
declared up front.

Deliverables: matched-trade analysis, attribution decomposition, yearly/regime
splits, symbol/sector robustness, cost stress (25/50/75/100bps), perturbation
check, full risk/distribution stats, walk-forward split (train<=2024,
test>=2025-01-01; nothing tuned on test).
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_fvg_robustness")
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "pine_stalefvg_backtest"))
import pine_backtest as pb
from run_stalefvg import add_fvg_columns  # noqa: E402  (FVG port, unmodified)

CACHE = os.path.join(BASE, "pine_entry_timing_backtest", "cache")
OUT = os.path.join(OUTDIR, "fvg_robustness_results.json")
os.makedirs(OUTDIR, exist_ok=True)

WATCHLIST = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB",
             "ONDS", "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]

THEME = {
    "QQQ": "Index", "SMCI": "AI Infra", "ANET": "AI Infra",
    "PLTR": "Software/AI", "BBAI": "Software/AI",
    "SOFI": "Fintech", "HOOD": "Fintech",
    "AMD": "Semis", "DRAM": "Semis/Memory",
    "RKLB": "Space", "SPCX": "Space", "ASTX": "Space",
    "ONDS": "Drones", "NIO": "China EV",
}

COSTS_STRESS = {"25bps": 0.0025, "50bps": 0.005,
                "75bps": 0.0075, "100bps": 0.01}
WF_SPLIT = "2025-01-01"

_orig_signal = pb.pine_buy_signal


def fvg_sub(df, i, vol_mult=1.0, use_safe=True, use_e21=True):
    """Canonical FVG sub-signal with pre-declared perturbation knobs."""
    r = df.iloc[i]
    if pd.isna(r["e200"]) or pd.isna(r["atr_base"]) or pd.isna(r["adx"]):
        return False
    close, vol = r["Close"], r["Volume"]
    volume_ok = vol > r["vol_ma"] * vol_mult
    hot = close > r["e9"] + r["atr"] * pb.HOT_ATR
    safe = (not hot) if use_safe else True
    trend_bull = r["e21"] > r["e55"] and close > r["e200"]
    e21_ok = (close > r["e21"]) if use_e21 else True
    return bool(trend_bull and r["inBullFvgSupport"] and e21_ok
                and volume_ok and safe)


PERTURB = {
    "FVG":    dict(vol_mult=1.0, use_safe=True,  use_e21=True),   # canonical
    "FVG_P1": dict(vol_mult=1.2, use_safe=True,  use_e21=True),   # stricter vol
    "FVG_P2": dict(vol_mult=1.0, use_safe=False, use_e21=True),   # no safe filter
    "FVG_P3": dict(vol_mult=1.0, use_safe=True,  use_e21=False),  # no e21 req
}


def make_signal(fvg_kwargs):
    def sig(df, i):
        if _orig_signal(df, i):
            return True
        return fvg_sub(df, i, **fvg_kwargs)
    return sig


def net_r(tr, cost):
    return pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)[2]


def dist_stats(trades, cost=0.0025):
    """Full distribution stats for a trade list."""
    if not trades:
        return {"n": 0}
    rs = np.array([net_r(t, cost) for t in trades])
    wins = rs[rs > 0]
    losses = rs[rs <= 0]
    gw, gl = wins.sum(), -losses.sum()
    # max losing streak in chronological order
    order = sorted(trades, key=lambda t: t["entry_time"])
    rs_o = np.array([net_r(t, cost) for t in order])
    streak = best = 0
    for r in rs_o:
        streak = streak + 1 if r <= 0 else 0
        best = max(best, streak)
    mfe = np.array([t.get("mfe_r", np.nan) for t in trades])
    mae = np.array([t.get("mae_r", np.nan) for t in trades])
    return {
        "n": len(trades),
        "expectancy_net_r": round(float(rs.mean()), 4),
        "win_rate_pct": round(float((rs > 0).mean()) * 100, 1),
        "profit_factor": round(float(gw / gl), 2) if gl > 0 else None,
        "median_r": round(float(np.median(rs)), 4),
        "avg_winner_r": round(float(wins.mean()), 4) if len(wins) else None,
        "avg_loser_r": round(float(losses.mean()), 4) if len(losses) else None,
        "max_losing_streak": int(best),
        "mfe_mean_r": round(float(np.nanmean(mfe)), 3),
        "mae_mean_r": round(float(np.nanmean(mae)), 3),
    }


def add_excursion(trades, data, sig_index):
    """Attach mfe_r / mae_r via bar walk from entry bar to exit bar."""
    for tr in trades:
        sym = tr["symbol"]
        df = data[sym]
        idx = sig_index[sym]
        try:
            ei = idx[tr["signal_time"]] + 1
            xi = idx.get(pd.Timestamp(tr["exit_time"]).isoformat(),
                         idx.get(str(tr["exit_time"])))
        except Exception:
            tr["mfe_r"] = tr["mae_r"] = np.nan
            continue
        if xi is None or xi < ei:
            tr["mfe_r"] = tr["mae_r"] = np.nan
            continue
        risk = tr["entry"] - tr["stop"]
        if risk <= 0:
            tr["mfe_r"] = tr["mae_r"] = np.nan
            continue
        seg = df.iloc[ei:xi + 1]
        tr["mfe_r"] = float(((seg["High"] - tr["entry"]) / risk).max())
        tr["mae_r"] = float(((seg["Low"] - tr["entry"]) / risk).min())
    return trades


def main():
    data, closes, sig_index = {}, {}, {}
    for sym in WATCHLIST:
        df = pd.read_pickle(os.path.join(CACHE, f"h4_{sym}.pkl"))
        if "Volume" not in df.columns or df["Volume"].isna().all():
            print(f"dropped {sym} (no volume)", flush=True)
            continue
        df = pb.add_pine_indicators(df)
        df = add_fvg_columns(df)
        data[sym] = df
        closes[sym] = df["Close"]
        sig_index[sym] = {df.index[i].isoformat(): i for i in range(len(df))}
    used = [s for s in WATCHLIST if s in data]
    print(f"loaded {len(used)} tickers", flush=True)

    # regime proxy: QQQ 4H close vs 200-bar SMA at the signal bar
    q = data["QQQ"]
    q_sma200 = q["Close"].rolling(200).mean()
    q_idx = sig_index["QQQ"]

    def regime_at(signal_time):
        i = q_idx.get(signal_time)
        if i is None or pd.isna(q_sma200.iloc[i]):
            return "unknown"
        return "bull" if q["Close"].iloc[i] > q_sma200.iloc[i] else "bear/sideways"

    results = {"variants": {}, "costs": list(COSTS_STRESS),
               "wf_split": WF_SPLIT, "theme_map": THEME}

    trades_by_var = {}
    for name in ["BASE"] + list(PERTURB):
        if name == "BASE":
            pb.pine_buy_signal = _orig_signal
        else:
            pb.pine_buy_signal = make_signal(PERTURB[name])
        all_trades, skipped = [], 0
        for sym in used:
            tr, sg = pb.gen_pine_trades(sym, data[sym])
            all_trades.extend(tr)
            skipped += sg
        all_trades.sort(key=lambda t: t["entry_time"])
        add_excursion(all_trades, data, sig_index)
        trades_by_var[name] = all_trades
        rec = {"name": name, "trades": len(all_trades), "skipped_gap": skipped,
               "cost_stress": {}, "dist_25bps": dist_stats(all_trades, 0.0025)}
        for cname, cost in COSTS_STRESS.items():
            port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
            d = dist_stats(all_trades, cost)
            tot_ret = (port["final_equity"] / pb.START_EQUITY - 1) * 100
            rec["cost_stress"][cname] = {
                "expectancy_net_r": d["expectancy_net_r"],
                "win_rate_pct": d["win_rate_pct"],
                "profit_factor": d["profit_factor"],
                "max_drawdown_pct": round(port["max_drawdown"] * 100, 2),
                "total_return_pct": round(tot_ret, 2),
            }
        results["variants"][name] = rec
        e = rec["cost_stress"]["25bps"]["expectancy_net_r"]
        print(f"{name}: n={len(all_trades)} exp25={e}R", flush=True)
    pb.pine_buy_signal = _orig_signal

    base, fvg = trades_by_var["BASE"], trades_by_var["FVG"]
    key = lambda t: (t["symbol"], t["signal_time"])  # noqa: E731
    bmap = {key(t): t for t in base}
    fmap = {key(t): t for t in fvg}
    shared_keys = set(bmap) & set(fmap)
    base_only = [bmap[k] for k in set(bmap) - set(fmap)]
    fvg_only = [fmap[k] for k in set(fmap) - set(bmap)]

    # ---- 1. matched-trade analysis -------------------------------------
    pairs = []
    for k in shared_keys:
        b, f = bmap[k], fmap[k]
        pairs.append({
            "symbol": k[0], "signal_time": k[1],
            "entry_b": b["entry"], "entry_f": f["entry"],
            "stop_dist_b": b["entry"] - b["stop"],
            "stop_dist_f": f["entry"] - f["stop"],
            "r_b": net_r(b, 0.0025), "r_f": net_r(f, 0.0025),
            "mfe_b": b.get("mfe_r"), "mfe_f": f.get("mfe_r"),
            "mae_b": b.get("mae_r"), "mae_f": f.get("mae_r"),
            "hold_b": b["hold_bars"], "hold_f": f["hold_bars"],
            "win_b": net_r(b, 0.0025) > 0, "win_f": net_r(f, 0.0025) > 0,
            "reason_b": b["reason"], "reason_f": f["reason"],
            "identical_fill": (b["entry"] == f["entry"]
                               and b["stop"] == f["stop"]
                               and b["exit"] == f["exit"]),
        })
    r_b = np.array([p["r_b"] for p in pairs])
    r_f = np.array([p["r_f"] for p in pairs])
    entry_diff = np.array([p["entry_f"] - p["entry_b"] for p in pairs])
    stopdiff = np.array([p["stop_dist_f"] - p["stop_dist_b"] for p in pairs])
    results["matched"] = {
        "n_shared": len(pairs),
        "n_base_only": len(base_only),
        "n_fvg_only": len(fvg_only),
        "n_base": len(base), "n_fvg": len(fvg),
        "identical_fills": int(sum(p["identical_fill"] for p in pairs)),
        "shared_mean_r_base": round(float(r_b.mean()), 4) if len(pairs) else None,
        "shared_mean_r_fvg": round(float(r_f.mean()), 4) if len(pairs) else None,
        "shared_mean_delta_r": round(float((r_f - r_b).mean()), 4) if len(pairs) else None,
        "mean_abs_entry_diff": round(float(np.abs(entry_diff).mean()), 6) if len(pairs) else None,
        "mean_stopdist_diff": round(float(stopdiff.mean()), 6) if len(pairs) else None,
        "shared_winrate_base": round(float((r_b > 0).mean()) * 100, 1) if len(pairs) else None,
        "shared_winrate_fvg": round(float((r_f > 0).mean()) * 100, 1) if len(pairs) else None,
        "base_only_stats": dist_stats(base_only),
        "fvg_only_stats": dist_stats(fvg_only),
    }

    # ---- 2. attribution decomposition ----------------------------------
    # E_fvg - E_base = shared_entry_effect + added_effect + dropped_effect + residual
    nF, nB, nO = len(fvg), len(base), len(pairs)
    E_f = float(np.mean([net_r(t, 0.0025) for t in fvg]))
    E_b = float(np.mean([net_r(t, 0.0025) for t in base]))
    E_Of = float(r_f.mean()) if len(pairs) else 0.0
    E_Ob = float(r_b.mean()) if len(pairs) else 0.0
    E_add = float(np.mean([net_r(t, 0.0025) for t in fvg_only])) if fvg_only else 0.0
    E_drop = float(np.mean([net_r(t, 0.0025) for t in base_only])) if base_only else 0.0
    shared_entry_effect = (nO / nF) * (E_Of - E_Ob)
    added_effect = ((nF - nO) / nF) * (E_add - E_b)
    dropped_effect = ((nB - nO) / nB) * (E_b - E_drop)
    total = E_f - E_b
    residual = total - (shared_entry_effect + added_effect + dropped_effect)
    # entry-price vs stop-geometry on shared pairs
    results["attribution"] = {
        "delta_r_total": round(total, 4),
        "shared_entry_effect_r": round(shared_entry_effect, 4),
        "added_trades_effect_r": round(added_effect, 4),
        "dropped_trades_effect_r": round(dropped_effect, 4),
        "reweight_residual_r": round(residual, 4),
        "E_fvg_only": round(E_add, 4), "n_fvg_only": len(fvg_only),
        "E_base_only": round(E_drop, 4), "n_base_only": len(base_only),
        "E_shared_fvg": round(E_Of, 4), "E_shared_base": round(E_Ob, 4),
    }

    # ---- 3. regime robustness ------------------------------------------
    def yearly(trades):
        out = {}
        for t in trades:
            y = str(pd.Timestamp(t["signal_time"]).year)
            out.setdefault(y, []).append(t)
        return {y: dist_stats(v) for y, v in sorted(out.items())}

    def by_regime(trades):
        out = {}
        for t in trades:
            r = regime_at(t["signal_time"])
            out.setdefault(r, []).append(t)
        return {r: dist_stats(v) for r, v in sorted(out.items())}

    results["yearly"] = {"BASE": yearly(base), "FVG": yearly(fvg)}
    results["regime"] = {"BASE": by_regime(base), "FVG": by_regime(fvg)}

    # ---- 4. symbol / sector --------------------------------------------
    def per_sym(trades):
        out = {}
        for t in trades:
            out.setdefault(t["symbol"], []).append(t)
        return {s: dist_stats(v) for s, v in sorted(out.items())}

    def per_theme(trades):
        out = {}
        for t in trades:
            th = THEME.get(t["symbol"], "Other")
            out.setdefault(th, []).append(t)
        return {th: dist_stats(v) for th, v in sorted(out.items())}

    results["per_symbol"] = {"BASE": per_sym(base), "FVG": per_sym(fvg)}
    results["per_theme"] = {"BASE": per_theme(base), "FVG": per_theme(fvg)}

    # ---- 8. walk-forward -------------------------------------------------
    def split(trades):
        tr = [t for t in trades if t["signal_time"] < WF_SPLIT]
        te = [t for t in trades if t["signal_time"] >= WF_SPLIT]
        return tr, te

    b_tr, b_te = split(base)
    f_tr, f_te = split(fvg)
    results["walkforward"] = {
        "split": WF_SPLIT,
        "train": {"BASE": dist_stats(b_tr), "FVG": dist_stats(f_tr)},
        "test": {"BASE": dist_stats(b_te), "FVG": dist_stats(f_te)},
    }

    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {OUT}")

    m = results["matched"]
    print(f"\nmatched: shared={m['n_shared']} base_only={m['n_base_only']} "
          f"fvg_only={m['n_fvg_only']} identical={m['identical_fills']}")
    print(f"shared ΔR={m['shared_mean_delta_r']} "
          f"(base {m['shared_mean_r_base']} vs fvg {m['shared_mean_r_fvg']})")
    a = results["attribution"]
    print(f"attribution: total={a['delta_r_total']} "
          f"entry={a['shared_entry_effect_r']} added={a['added_trades_effect_r']} "
          f"dropped={a['dropped_trades_effect_r']} resid={a['reweight_residual_r']}")


if __name__ == "__main__":
    main()
