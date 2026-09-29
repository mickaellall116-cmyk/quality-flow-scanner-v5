#!/usr/bin/env python3
"""Selection-Edge Phase 2 (worker B): persistent cross-sectional strength factors.

Tests 4 factors SEPARATELY, never combined:
  RS3       = 63d stock return - 63d SPY return      (perturb 42/84)
  RS6       = 126d stock return - 126d SPY return    (perturb 63/168)
  SECTOR_RS = 63d sector-ETF return - 63d SPY return (perturb 42/84)
  HI52      = (price - 252d high) / price            (perturb 63/126 highs)

HARD BLINDING: the 14 masked names are excluded from ALL factor construction,
cross-sectional ranking, and evaluation. Working set = 131-name PIT universe
minus the masked names present in it (123 names).

Bucketing (pre-registered, NOT optimized): at each signal timestamp, rank the
123-name working universe cross-sectionally by the factor strict-PIT
(endpoint = last completed daily bar as of signal time) and bucket the
signal's stock as TOP QUARTILE / MIDDLE 50% / BOTTOM QUARTILE.
Primary question: does expectancy increase MONOTONICALLY top > middle > bottom?
Robustness: terciles + window perturbations.

Analysis population: the 374 canonical portfolio trades (realized V5.4 Mode B
outcomes under the canonical $75k/1%/slots/heat replay, costs leg-based
round-trip), masked -> 353 working trades. Candidate-level outcomes would
require a new portfolio replay = Phase 4+, deferred per Mike's spec.

Protocol per factor-window: full/dev/val/year splits; walk-forward
12mo-observe/6mo-test on top-minus-bottom delta; costs 25/50/75/100bps RT;
concentration (drop top 1/3/5 contributors per bucket); bootstrap >=5000 on
the delta; leave-one-symbol-out on the delta; absolute check (top clears zero?).
"""

import json
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.expanduser(
    "~/workspace/quality-flow-scanner-v5/canonical_baseline")
OUT = os.path.expanduser(
    "~/workspace/quality-flow-scanner-v5/selection_edge/phase2_strength")
sys.path.insert(0, BASE)
import simlib as sl  # noqa: E402  (canonical engine lib, read-only use)

os.makedirs(OUT, exist_ok=True)
rng_global = np.random.default_rng(7)

MASKED = {"QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB", "ONDS", "DRAM",
          "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"}

ETF_OF_SECTOR = {
    "Technology": "XLK", "Financial Services": "XLF",
    "Consumer Cyclical": "XLY", "Healthcare": "XLV", "Industrials": "XLI",
    "Communication Services": "XLC", "Energy": "XLE",
    "Consumer Defensive": "XLP", "Basic Materials": "XLB",
    "Utilities": "XLU", "Real Estate": "XLRE",
}

FACTORS = {
    "RS3": {"kind": "rs", "primary": 63, "perturb": [42, 84],
            "hypothesis": "Quality Flow is a 4H breakout/continuation system. "
            "Continuation works when institutional sponsorship is already behind "
            "the name; trailing relative strength vs SPY is the simplest PIT "
            "proxy for 'the market is already rewarding this stock'.",
            "mechanism": "Breakouts in stocks being accumulated relative to the "
            "market should follow through more often than breakouts in "
            "laggards fighting for attention."},
    "RS6": {"kind": "rs", "primary": 126, "perturb": [63, 168],
            "hypothesis": "Same mechanism as RS3 but over ~6 months: persistent "
            "(not just recent) cross-sectional strength marks durable "
            "sponsorship rather than a short-term hot streak.",
            "mechanism": "Longer-horizon RS filters out 1-2 month momentum "
            "bursts that revert; a 6-month leader breaking out on 4H has deeper "
            "holder conviction underneath."},
    "SECTOR_RS": {"kind": "sector_rs", "primary": 63, "perturb": [42, 84],
            "hypothesis": "Stocks do not break out alone: sector rotation "
            "provides the bid underneath. A breakout in a leading sector rides "
            "institutional sector-allocation flows.",
            "mechanism": "Breakout in a leading sector = tailwind from sector "
            "flows; breakout in a lagging sector fights its own sector's "
            "gravity. Sector-level participation, complementary to "
            "stock-level RS."},
    "HI52": {"kind": "hi52", "primary": 252, "perturb": [63, 126],
            "hypothesis": "The best breakouts come from stocks already near "
            "highs: no overhead supply, every holder in profit, no trapped "
            "sellers to sell into strength.",
            "mechanism": "A 'breakout' signal firing far below the 52-week "
            "high is structurally a range trade masquerading as a breakout; "
            "proximity to the high measures clean overhead."},
}

COSTS = [25, 50, 75, 100]
N_BOOT = 5000


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
universe = sl.load_universe()
SECTOR_OF = {x["symbol"]: x.get("sector") for x in universe}
WORKING = [x["symbol"] for x in universe if x["symbol"] not in MASKED]
assert len(universe) == 131
assert not (set(WORKING) & MASKED)
# 8 of the 14 masked names are in the PIT universe; the other 6 are absent.
N_WORKING = len(WORKING)
assert N_WORKING == 123, N_WORKING

closes = {}
need = set(WORKING) | {"SPY"} | set(ETF_OF_SECTOR.values())
for s in sorted(need):
    try:
        closes[s] = sl.load_d1(s)["Close"]
    except Exception as exc:  # pragma: no cover
        print(f"WARN: no daily data for {s}: {exc}")

RETW = {}
for W in [42, 63, 84, 126, 168]:
    RETW[W] = {s: c / c.shift(W) - 1.0 for s, c in closes.items()}
HIW = {}
for W in [63, 126, 252]:
    HIW[W] = {s: (c - c.rolling(W, min_periods=W).max()) / c
              for s, c in closes.items()}

trades_all = json.load(open(os.path.join(BASE, "canonical_trades.json")))
n_masked_out = sum(1 for t in trades_all if t["symbol"] in MASKED)
trades = [t for t in trades_all if t["symbol"] not in MASKED]
assert all(t["symbol"] in WORKING for t in trades)
for t in trades:
    t["sig_ts"] = pd.Timestamp(t["signal_bar_close_at"])
    t["exit_ts_p"] = pd.Timestamp(t["exit_ts"])
print(f"trades: {len(trades_all)} total, {n_masked_out} masked-14, "
      f"{len(trades)} working")


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


def factor_value(kind, W, symbol, t_end):
    """Strict-PIT factor value. None when not computable."""
    if kind == "rs":
        cs, ss = closes.get(symbol), closes.get("SPY")
        if cs is None:
            return None
        j = endpoint_idx(cs, t_end)
        k = endpoint_idx(ss, t_end)
        if j is None or k is None or j < W or k < W:
            return None
        a, b = RETW[W][symbol].iloc[j], RETW[W]["SPY"].iloc[k]
        return None if (pd.isna(a) or pd.isna(b)) else float(a - b)
    if kind == "sector_rs":
        etf = ETF_OF_SECTOR.get(SECTOR_OF.get(symbol))
        if etf is None:
            return None
        es, ss = closes.get(etf), closes.get("SPY")
        j = endpoint_idx(es, t_end)
        k = endpoint_idx(ss, t_end)
        if j is None or k is None or j < W or k < W:
            return None
        a, b = RETW[W][etf].iloc[j], RETW[W]["SPY"].iloc[k]
        return None if (pd.isna(a) or pd.isna(b)) else float(a - b)
    if kind == "hi52":
        cs = closes.get(symbol)
        if cs is None:
            return None
        j = endpoint_idx(cs, t_end)
        if j is None or j < W:
            return None
        v = HIW[W][symbol].iloc[j]
        return None if pd.isna(v) else float(v)
    raise ValueError(kind)


def bucket_signal(kind, W, symbol, t_end, scheme="quartile"):
    """Cross-sectional quartile/tercile bucket of `symbol` among WORKING names.

    Returns (bucket, value, n_valid). bucket None when the signal's own
    factor value is not computable.
    """
    vals = {}
    for s in WORKING:
        v = factor_value(kind, W, s, t_end)
        if v is not None and np.isfinite(v):
            vals[s] = v
    n = len(vals)
    if symbol not in vals or n < 8:
        return None, None, n
    arr = pd.Series(vals)
    pct = (arr.rank(method="average")[symbol] - 1) / (n - 1)
    if scheme == "quartile":
        b = "top" if pct >= 0.75 else ("bottom" if pct < 0.25 else "middle")
    elif scheme == "tercile":
        b = "top" if pct >= 2 / 3 else ("bottom" if pct < 1 / 3 else "middle")
    else:
        raise ValueError(scheme)
    return b, vals[symbol], n


def r_of(t, cost):
    return float(t[f"net_r_{cost}bps"])


def bucket_stats(trs, cost=50):
    rs = np.array([r_of(t, cost) for t in trs], dtype=float)
    out = {"n": int(len(rs))}
    if len(rs) == 0:
        out.update({"mean": None, "pf": None, "wr": None, "maxdd_r": None,
                    "median": None, "avg_win": None, "avg_loss": None})
        return out
    out["mean"] = float(rs.mean())
    out["pf"] = sl.profit_factor(rs)
    out["wr"] = sl.win_rate(rs)
    out["median"] = float(np.median(rs))
    out["avg_win"] = float(rs[rs > 0].mean()) if (rs > 0).any() else None
    out["avg_loss"] = float(rs[rs <= 0].mean()) if (rs <= 0).any() else None
    # equity ordered by exit time
    ordered = sorted(trs, key=lambda t: t["exit_ts_p"])
    eq = np.cumsum([r_of(t, cost) for t in ordered])
    out["maxdd_r"] = float((eq - np.maximum.accumulate(eq)).min())
    return out


def split_stats(idxs, cost=50):
    return {b: bucket_stats([trades[i] for i in idxs[b]], cost)
            for b in ("top", "middle", "bottom")}


def means(idxs, cost=50):
    m = {}
    for b in ("top", "middle", "bottom"):
        rs = [r_of(trades[i], cost) for i in idxs[b]]
        m[b] = float(np.mean(rs)) if rs else None
    return m


def monotonic(m):
    return (m["top"] is not None and m["middle"] is not None
            and m["bottom"] is not None
            and m["top"] > m["middle"] > m["bottom"])


# --------------------------------------------------------------------------
# Protocol pieces
# --------------------------------------------------------------------------
def run_protocol(idxs, cost_primary=50):
    """idxs: dict bucket -> list of trade indices (full sample)."""
    res = {}
    res["bucket_stats_50bps"] = split_stats(idxs, 50)
    res["expectancy_by_cost"] = {str(c): means(idxs, c) for c in COSTS}

    # dev / val / year splits (signal date)
    dev = {b: [i for i in idxs[b]
               if trades[i]["sig_ts"] < pd.Timestamp("2025-01-01", tz="America/New_York")]
           for b in idxs}
    val = {b: [i for i in idxs[b]
               if trades[i]["sig_ts"] >= pd.Timestamp("2025-01-01", tz="America/New_York")]
           for b in idxs}
    res["dev_n"] = {b: len(dev[b]) for b in dev}
    res["val_n"] = {b: len(val[b]) for b in val}
    res["dev_means_50bps"] = means(dev)
    res["val_means_50bps"] = means(val)
    res["dev_monotonic"] = monotonic(res["dev_means_50bps"])
    res["val_monotonic"] = monotonic(res["val_means_50bps"])
    res["val_delta"] = (res["val_means_50bps"]["top"] - res["val_means_50bps"]["bottom"]
                        if res["val_means_50bps"]["top"] is not None
                        and res["val_means_50bps"]["bottom"] is not None else None)

    years = {}
    for y in (2024, 2025, 2026):
        yy = {b: [i for i in idxs[b] if trades[i]["sig_ts"].year == y]
              for b in idxs}
        years[str(y)] = {"n": {b: len(yy[b]) for b in yy},
                         "means_50bps": means(yy)}
    res["year_splits"] = years

    # walk-forward 12mo observe / 6mo test on top-minus-bottom delta
    tmin = min(t["sig_ts"] for t in trades)
    tmax = max(t["sig_ts"] for t in trades)
    wins = []
    k = 0
    while True:
        s = tmin + pd.Timedelta(days=365) + k * pd.Timedelta(days=182)
        e = s + pd.Timedelta(days=182)
        if s >= tmax:
            break
        wins.append((s, e))
        k += 1
    wf = []
    for s, e in wins:
        ww = {b: [i for i in idxs[b] if s <= trades[i]["sig_ts"] < e]
              for b in idxs}
        m = means(ww)
        d = (m["top"] - m["bottom"]
             if m["top"] is not None and m["bottom"] is not None
             and len(ww["top"]) >= 3 and len(ww["bottom"]) >= 3 else None)
        wf.append({"start": s.strftime("%Y-%m-%d"), "end": e.strftime("%Y-%m-%d"),
                   "n_top": len(ww["top"]), "n_bottom": len(ww["bottom"]),
                   "delta_50bps": d})
    res["walk_forward"] = wf
    pos = [w["delta_50bps"] for w in wf if w["delta_50bps"] is not None]
    res["wf_hit_rate"] = (float(np.mean([d > 0 for d in pos])) if pos else None,
                          len(pos))

    # bootstrap >= 5000 on top-minus-bottom delta @50bps
    top_r = np.array([r_of(trades[i], 50) for i in idxs["top"]])
    bot_r = np.array([r_of(trades[i], 50) for i in idxs["bottom"]])
    if len(top_r) >= 5 and len(bot_r) >= 5:
        deltas = np.empty(N_BOOT)
        topmeans = np.empty(N_BOOT)
        for i in range(N_BOOT):
            ts = rng_global.choice(top_r, len(top_r), replace=True)
            bs = rng_global.choice(bot_r, len(bot_r), replace=True)
            deltas[i] = ts.mean() - bs.mean()
            topmeans[i] = ts.mean()
        res["bootstrap"] = {
            "n": N_BOOT,
            "delta_mean": float(deltas.mean()),
            "delta_p2.5": float(np.percentile(deltas, 2.5)),
            "delta_p97.5": float(np.percentile(deltas, 97.5)),
            "p_delta_pos": float((deltas > 0).mean()),
            "top_mean_p2.5": float(np.percentile(topmeans, 2.5)),
            "top_mean_p97.5": float(np.percentile(topmeans, 97.5)),
        }
    else:
        res["bootstrap"] = None

    # leave-one-symbol-out on the delta @50bps
    syms = sorted({trades[i]["symbol"] for i in idxs["top"] + idxs["bottom"]})
    loso = []
    base_top = [r_of(trades[i], 50) for i in idxs["top"]]
    base_bot = [r_of(trades[i], 50) for i in idxs["bottom"]]
    base_delta = float(np.mean(base_top) - np.mean(base_bot))
    for s in syms:
        tr_ = [r for i, r in zip(idxs["top"], base_top)
               if trades[i]["symbol"] != s]
        br_ = [r for i, r in zip(idxs["bottom"], base_bot)
               if trades[i]["symbol"] != s]
        if len(tr_) >= 3 and len(br_) >= 3:
            loso.append({"drop": s,
                         "delta_50bps": float(np.mean(tr_) - np.mean(br_))})
    ds = [x["delta_50bps"] for x in loso]
    res["loso"] = {"base_delta_50bps": base_delta,
                   "n_symbols": len(loso),
                   "min_delta": float(min(ds)) if ds else None,
                   "max_delta": float(max(ds)) if ds else None,
                   "frac_positive": float(np.mean([d > 0 for d in ds])) if ds else None,
                   "details": loso}

    # concentration: drop top 1/3/5 contributors per bucket, recompute mean
    conc = {}
    for b in ("top", "middle", "bottom"):
        contrib = {}
        for i in idxs[b]:
            s = trades[i]["symbol"]
            contrib[s] = contrib.get(s, 0.0) + r_of(trades[i], 50)
        ranked = sorted(contrib, key=contrib.get, reverse=True)
        c = {"top_contributors": [(s, round(contrib[s], 3))
                                  for s in ranked[:5]]}
        for kk in (1, 3, 5):
            drop = set(ranked[:kk])
            rs = [r_of(trades[i], 50) for i in idxs[b]
                  if trades[i]["symbol"] not in drop]
            c[f"mean_drop{kk}"] = float(np.mean(rs)) if rs else None
            c[f"n_drop{kk}"] = len(rs)
        conc[b] = c
    res["concentration"] = conc

    # absolute check: top bucket clears zero @50bps
    tm = res["bucket_stats_50bps"]["top"]["mean"]
    res["top_clears_zero_50bps"] = tm is not None and tm > 0
    return res


def gate_flags(proto, pert_protos):
    """Operationalized gates -> flag dict (documented in REPORT.md)."""
    m = proto["bucket_stats_50bps"]
    mf = {b: m[b]["mean"] for b in ("top", "middle", "bottom")}
    costs = proto["expectancy_by_cost"]
    boot = proto["bootstrap"]
    loso = proto["loso"]
    wf = proto["walk_forward"]
    conc_top = proto["concentration"]["top"]
    flags = {}
    flags["mono_full"] = monotonic(mf)
    flags["top_pos_full"] = mf["top"] is not None and mf["top"] > 0
    flags["mono_val"] = proto["val_monotonic"]
    flags["delta_val_pos"] = (proto["val_delta"] is not None
                              and proto["val_delta"] > 0)
    flags["costs_mono"] = all(
        monotonic({b: costs[str(c)][b] for b in ("top", "middle", "bottom")})
        for c in COSTS)
    flags["costs_top_pos"] = all(costs[str(c)]["top"] is not None
                                 and costs[str(c)]["top"] > 0 for c in COSTS)
    flags["boot_p95"] = boot is not None and boot["p_delta_pos"] >= 0.95
    flags["loso_min_pos"] = (loso["min_delta"] is not None
                             and loso["min_delta"] > 0)
    flags["wf_majority_pos"] = (proto["wf_hit_rate"][0] is not None
                                and proto["wf_hit_rate"][0] >= 2 / 3
                                and proto["wf_hit_rate"][1] >= 2)
    flags["conc_top3_pos"] = (conc_top["mean_drop3"] is not None
                              and conc_top["mean_drop3"] > 0)
    # perturbation: direction (top>bottom) holds at each perturbed window
    pdirs = []
    for pw, pp in pert_protos.items():
        mm = pp["bucket_stats_50bps"]
        t_, b_ = mm["top"]["mean"], mm["bottom"]["mean"]
        pdirs.append(t_ is not None and b_ is not None and t_ > b_)
    flags["perturb_direction"] = bool(pdirs) and all(pdirs)
    pmonos = []
    for pw, pp in pert_protos.items():
        mm = pp["bucket_stats_50bps"]
        pmonos.append(monotonic({b: mm[b]["mean"]
                                 for b in ("top", "middle", "bottom")}))
    flags["perturb_monotonic"] = bool(pmonos) and all(pmonos)
    return flags


def assign_verdict(flags):
    must = ["mono_full", "top_pos_full", "mono_val", "delta_val_pos",
            "costs_mono", "costs_top_pos", "boot_p95", "loso_min_pos",
            "wf_majority_pos", "conc_top3_pos", "perturb_direction"]
    if all(flags[k] for k in must):
        return "PASS"
    # directionally consistent: top>bottom and top>0 on full sample
    if flags["top_pos_full"] and flags.get("_top_gt_bottom_full"):
        return "MAYBE"
    return "FAIL"


# --------------------------------------------------------------------------
# Run all factors
# --------------------------------------------------------------------------
results = {}
for fname, fdef in FACTORS.items():
    kind = fdef["kind"]
    print(f"\n=== {fname} ({kind}) ===", flush=True)
    fres = {"factor": fname,
            "hypothesis": fdef["hypothesis"],
            "mechanism": fdef["mechanism"],
            "kind": kind,
            "primary_window": fdef["primary"],
            "perturb_windows": fdef["perturb"],
            "bucketing": "quartile primary (top 25% / middle 50% / bottom 25%), "
                         "tercile robustness; cross-sectional rank on the "
                         "123-name working universe, strict PIT",
            "blinding": "14 names masked from construction, ranking, evaluation",
            "population": {"portfolio_trades": len(trades_all),
                           "masked_out": n_masked_out,
                           "working": len(trades)},
            "windows": {}}
    # bucket every trade for each window x scheme
    bucket_cache = {}
    for W in [fdef["primary"]] + fdef["perturb"]:
        for scheme in ("quartile", "tercile"):
            idxs = {"top": [], "middle": [], "bottom": []}
            unranked = 0
            n_valid_dist = []
            recs = []
            for i, t in enumerate(trades):
                b, v, nv = bucket_signal(kind, W, t["symbol"], t["sig_ts"],
                                         scheme)
                n_valid_dist.append(nv)
                if b is None:
                    unranked += 1
                    continue
                idxs[b].append(i)
                recs.append({"signal_id": t["signal_id"], "symbol": t["symbol"],
                             "signal_date": t["sig_ts"].strftime("%Y-%m-%d"),
                             "factor_value": round(v, 6), "bucket": b,
                             "net_r_50bps": round(r_of(t, 50), 4)})
            key = (W, scheme)
            bucket_cache[key] = (idxs, recs)
            proto = run_protocol(idxs)
            proto["n_unranked"] = unranked
            proto["n_ranked"] = sum(len(v) for v in idxs.values())
            proto["cross_section_n_median"] = float(np.median(n_valid_dist))
            proto["trade_factors"] = recs
            wres = {"window": W, "scheme": scheme, "protocol": proto}
            fres["windows"].setdefault(str(W), {})[scheme] = wres
            mm = {b: proto["bucket_stats_50bps"][b]["mean"]
                  for b in ("top", "middle", "bottom")}
            print(f"  W={W} {scheme}: n={proto['n_ranked']} "
                  f"(unranked {unranked}) means={ {b: round(mm[b],4) if mm[b] is not None else None for b in mm} } "
                  f"mono={monotonic(mm)}", flush=True)

    # gates on primary window / quartile; perturbations = direction check
    prim = fres["windows"][str(fdef["primary"])]["quartile"]["protocol"]
    pert = {str(W): fres["windows"][str(W)]["quartile"]["protocol"]
            for W in fdef["perturb"]}
    flags = gate_flags(prim, pert)
    mm = {b: prim["bucket_stats_50bps"][b]["mean"]
          for b in ("top", "middle", "bottom")}
    flags["_top_gt_bottom_full"] = (mm["top"] is not None
                                    and mm["bottom"] is not None
                                    and mm["top"] > mm["bottom"])
    fres["gate_flags"] = flags
    fres["verdict"] = assign_verdict(flags)
    results[fname] = fres
    with open(os.path.join(OUT, f"{fname}.json"), "w") as fh:
        json.dump(fres, fh, indent=1, default=str)
    print(f"  VERDICT {fname}: {fres['verdict']}  flags={json.dumps({k: v for k, v in flags.items() if not k.startswith('_')})}")

print("\nWrote:", OUT)
