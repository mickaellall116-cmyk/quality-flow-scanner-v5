"""Portfolio CORRELATION / EXPOSURE study on Pine V3.6. Spec: EXPOSURE_SPEC.md (frozen).

V3.6 entries/exits byte-identical; sizing fixed 1%. Portfolio-level gates only.
Control must reproduce baseline (263 trades, +0.195R @4bps) trade-for-trade.
"""
import json
import os
import sys
import traceback
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pine_backtest as pb

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(BASE, "exposure_results.json")

SECTOR = {
    # SEMIS
    "NVDA": "SEMIS", "AMD": "SEMIS", "AVGO": "SEMIS", "MU": "SEMIS",
    "INTC": "SEMIS", "LRCX": "SEMIS", "AMAT": "SEMIS", "QCOM": "SEMIS",
    "ARM": "SEMIS",
    # AI_INFRA
    "SMCI": "AI_INFRA",
    # AI_SOFTWARE
    "PLTR": "AI_SOFTWARE", "MSFT": "AI_SOFTWARE", "GOOGL": "AI_SOFTWARE",
    "META": "AI_SOFTWARE", "CRM": "AI_SOFTWARE", "APP": "AI_SOFTWARE",
    "NET": "AI_SOFTWARE", "SNOW": "AI_SOFTWARE", "DDOG": "AI_SOFTWARE",
    "CRWD": "AI_SOFTWARE", "SHOP": "AI_SOFTWARE",
    # SPACE
    "RKLB": "SPACE", "ASTS": "SPACE", "LUNR": "SPACE",
    # CRYPTO
    "BTC-USD": "CRYPTO", "ETH-USD": "CRYPTO", "SOL-USD": "CRYPTO",
    "DOGE-USD": "CRYPTO", "AVAX-USD": "CRYPTO", "LINK-USD": "CRYPTO",
    "XRP-USD": "CRYPTO", "COIN": "CRYPTO", "MSTR": "CRYPTO",
    # FINTECH
    "SOFI": "FINTECH", "HOOD": "FINTECH", "PYPL": "FINTECH",
    "NU": "FINTECH", "MELI": "FINTECH",
    # CONSUMER
    "TSLA": "CONSUMER", "AAPL": "CONSUMER", "AMZN": "CONSUMER",
    "NFLX": "CONSUMER", "NIO": "CONSUMER", "F": "CONSUMER",
    # HEALTHCARE
    "MRNA": "HEALTHCARE", "PFE": "HEALTHCARE",
    # ETF
    "SPY": "ETF", "IWM": "ETF", "SMH": "ETF", "ARKK": "ETF", "XLF": "ETF",
}
MEGA_AI = {"SEMIS", "AI_INFRA", "AI_SOFTWARE", "SPACE"}


# ------------------------------------------------------- candidate generation
def gen_candidates(sym, df):
    """Identical trade engine to the control (pb.gen_pine_trades)."""
    trades, skipped_gap = pb.gen_pine_trades(sym, df)
    return trades, skipped_gap


# ------------------------------------------------------- exposure-aware simulator
class ExposureSim:
    """Event-driven portfolio sim mirroring pb.simulate_portfolio, plus gates.

    gate(trade, open_trades, t) -> (take: bool, reason: str). None = no gate.
    Records taken trades with sizing for dense-grid DD attribution.
    """

    def __init__(self, closes_4h, logret_4h, cost, risk_pct=pb.RISK_PCT,
                 max_concurrent=pb.MAX_CONCURRENT, gate=None, gate_name="none"):
        self.closes_4h = closes_4h
        self.logret_4h = logret_4h
        self.cost = cost
        self.risk_pct = risk_pct
        self.max_concurrent = max_concurrent
        self.gate = gate
        self.gate_name = gate_name
        self.skip_gate = 0
        self.skip_cap = 0
        self.skip_risk = 0
        self.taken = []  # dicts with trade + risk_dollars + size + net_r

    def mark(self, sym, t):
        s = self.closes_4h[sym]
        idx = s.index.searchsorted(t, side="right") - 1
        return float(s.iloc[idx]) if idx >= 0 else float(s.iloc[0])

    def run(self, trades):
        events = []
        for t in trades:
            events.append((t["exit_time"], 0, t))
            events.append((t["entry_time"], 1, t))
        events.sort(key=lambda e: (e[0], e[1]))
        realized = pb.START_EQUITY
        open_pos, by_id = [], {}
        peak, max_dd = realized, 0.0
        curve = []

        def marked_equity(t):
            unreal = sum(((self.mark(tr["symbol"], t) - tr["entry"]) / tr["entry"]) * p["size"]
                         for p, tr in ((p, p["trade"]) for p in open_pos))
            return realized + unreal

        for t, kind, tr in events:
            if kind == 1:
                eq = marked_equity(t)
                open_risk = sum(p["risk_dollars"] for p in open_pos) / eq if eq > 0 else 1
                if len(open_pos) >= self.max_concurrent:
                    self.skip_cap += 1
                    continue
                if open_risk + self.risk_pct > pb.MAX_PORTFOLIO_RISK + 1e-9:
                    self.skip_risk += 1
                    continue
                if self.gate is not None:
                    take, _reason = self.gate(tr, [p["trade"] for p in open_pos], t)
                    if not take:
                        self.skip_gate += 1
                        continue
                risk_dollars = self.risk_pct * eq
                risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
                pos = {"trade": tr, "risk_dollars": risk_dollars,
                       "size": risk_dollars / risk_frac, "risk_frac": risk_frac}
                open_pos.append(pos)
                by_id[id(tr)] = pos
            else:
                pos = by_id.pop(id(tr), None)
                if pos is None:
                    continue
                _, _, net_r, _ = pb._outcome(tr["entry"], tr["stop"], tr["exit"], self.cost)
                realized += pos["risk_dollars"] * net_r
                open_pos.remove(pos)
                self.taken.append({"trade": tr, "risk_dollars": pos["risk_dollars"],
                                   "size": pos["size"], "net_r": net_r})
            eq = marked_equity(t)
            curve.append((t, eq, realized, len(open_pos)))
            peak = max(peak, eq)
            if peak > 0:
                max_dd = max(max_dd, (peak - eq) / peak)
        return {"final_equity": realized, "max_drawdown": max_dd,
                "skipped_gate": self.skip_gate, "skipped_cap": self.skip_cap,
                "skipped_risk": self.skip_risk, "curve": curve,
                "taken": self.taken}


# ------------------------------------------------------------------ gates
def trailing_corr(logret_4h, sym_a, sym_b, t_end, n=360, min_overlap=100):
    """Pearson corr of 4h log returns over the n bars strictly before t_end."""
    ra = logret_4h[sym_a]
    rb = logret_4h[sym_b]
    a = ra[ra.index < t_end].tail(n)
    b = rb[rb.index < t_end].tail(n)
    if len(a) == 0 or len(b) == 0:
        return 0.0
    joined = pd.concat([a, b], axis=1, join="inner").dropna()
    if len(joined) < min_overlap:
        return 0.0
    c = joined.iloc[:, 0].corr(joined.iloc[:, 1])
    return 0.0 if pd.isna(c) else float(c)


def make_gates(logret_4h):
    def g_sector2(tr, open_trades, t):
        s = SECTOR[tr["symbol"]]
        n = sum(1 for o in open_trades if SECTOR[o["symbol"]] == s)
        return (n < 2, "sector2")

    def g_mega3(tr, open_trades, t):
        if SECTOR[tr["symbol"]] not in MEGA_AI:
            return (True, "mega3")
        n = sum(1 for o in open_trades if SECTOR[o["symbol"]] in MEGA_AI)
        return (n < 3, "mega3")

    def g_corr70(tr, open_trades, t):
        for o in open_trades:
            c = trailing_corr(logret_4h, tr["symbol"], o["symbol"], t)
            if c > 0.70:
                return (False, "corr70")
        return (True, "corr70")

    return {"E1_sector2": g_sector2, "E2_mega3": g_mega3, "E3_corr70": g_corr70}


# ------------------------------------------------------------- dense-grid DD attribution
def _to_utc(x):
    t = pd.Timestamp(x)
    return t.tz_convert("UTC") if t.tzinfo is not None else t.tz_localize("UTC")


def dense_attribution(sim_taken, closes_4h, t0, t1):
    """Per-4h-bar marked equity + concurrency on the union timestamp grid."""
    t0, t1 = _to_utc(t0), _to_utc(t1)
    grid_ts = set()
    for s in closes_4h:
        idx = closes_4h[s].index
        sel = idx[(idx >= t0) & (idx <= t1)]
        for x in sel:
            grid_ts.add(_to_utc(x))
    grid = pd.DatetimeIndex(sorted(grid_ts))
    # realized equity as a function of time: step at each exit
    exits = sorted([(r["trade"]["exit_time"], r["risk_dollars"] * r["net_r"])
                    for r in sim_taken])
    out = []
    for ts in grid:
        realized = pb.START_EQUITY + sum(d for te, d in exits if te <= ts)
        unreal = 0.0
        n_open = 0
        for r in sim_taken:
            tr = r["trade"]
            if tr["entry_time"] <= ts < tr["exit_time"]:
                s = closes_4h[tr["symbol"]]
                idx = s.index.searchsorted(ts, side="right") - 1
                px = float(s.iloc[idx]) if idx >= 0 else float(s.iloc[0])
                unreal += ((px - tr["entry"]) / tr["entry"]) * r["size"]
                n_open += 1
        out.append((ts, realized + unreal, n_open))
    return out


# ---------------------------------------------------------------- diagnostics
def diagnose(sim, closes_4h, trades):
    """D1-D4 on the control (no-gate) simulation."""
    curve = sim["curve"]
    eq = np.array([c[1] for c in curve])
    ts = [c[0] for c in curve]
    peak_i = int(np.argmax(eq))
    trough_i = peak_i + int(np.argmin(eq[peak_i:]))
    t_peak, t_trough = ts[peak_i], ts[trough_i]
    dd_pct = (eq[peak_i] - eq[trough_i]) / eq[peak_i]

    grid = dense_attribution(sim["taken"], closes_4h, t_peak, t_trough)
    conc = np.array([g[2] for g in grid])
    geq = np.array([g[1] for g in grid])
    # D2: share of the decline occurring on bars with >=3 concurrent
    declines = np.maximum(0.0, geq[:-1] - geq[1:])
    conc_mid = conc[1:]
    dd_total = max(0.0, geq[0] - geq.min())
    share_ge3 = float(declines[conc_mid >= 3].sum() / declines.sum()) if declines.sum() > 0 else 0.0

    # D1: positions open at DD start: sectors + mean pairwise trailing corr
    open_at_start = [r for r in sim["taken"]
                     if r["trade"]["entry_time"] <= t_peak < r["trade"]["exit_time"]]
    sectors_start = [SECTOR[r["trade"]["symbol"]] for r in open_at_start]
    pair_corrs = []
    syms = [r["trade"]["symbol"] for r in open_at_start]
    for i in range(len(syms)):
        for j in range(i + 1, len(syms)):
            pair_corrs.append(trailing_corr(LOGRET, syms[i], syms[j], t_peak))
    d1 = {"t_peak": str(t_peak), "t_trough": str(t_trough),
          "dd_pct": round(dd_pct * 100, 2),
          "avg_concurrency": round(float(conc.mean()), 2),
          "max_concurrency": int(conc.max()),
          "n_open_at_start": len(open_at_start),
          "sectors_at_start": sectors_start,
          "mean_pairwise_corr_at_start": round(float(np.mean(pair_corrs)), 3) if pair_corrs else None}

    # D3: same-bar cohorts
    by_bar = defaultdict(list)
    for r in sim["taken"]:
        by_bar[r["trade"]["entry_time"]].append(r["net_r"])
    cohorts = [v for v in by_bar.values() if len(v) >= 2]
    var_ratio, within_corrs = [], []
    for v in cohorts:
        v = np.array(v)
        var_ratio.append(v.sum() ** 2 / (v ** 2).sum() if (v ** 2).sum() > 0 else np.nan)
        # pairwise outcome corr needs >=2 points per... use sign agreement proxy instead:
        within_corrs.append(float(np.mean(np.sign(v) == np.sign(v[0]))))
    d3 = {"n_multitrade_cohorts": len(cohorts),
          "trades_in_cohorts": int(sum(len(v) for v in cohorts)),
          "median_var_ratio": round(float(np.nanmedian(var_ratio)), 3) if var_ratio else None,
          "mean_var_ratio": round(float(np.nanmean(var_ratio)), 3) if var_ratio else None,
          "mean_sign_agreement": round(float(np.mean(within_corrs)), 3) if within_corrs else None}

    # D4: sector concentration
    d4 = {}
    for r in sim["taken"]:
        s = SECTOR[r["trade"]["symbol"]]
        d = d4.setdefault(s, {"trades": 0, "total_r": 0.0, "dd_window_r": 0.0})
        d["trades"] += 1
        d["total_r"] += r["net_r"]
        tr = r["trade"]
        if tr["entry_time"] <= t_trough and tr["exit_time"] >= t_peak:
            d["dd_window_r"] += r["net_r"]
    for s in d4:
        d4[s]["total_r"] = round(d4[s]["total_r"], 2)
        d4[s]["dd_window_r"] = round(d4[s]["dd_window_r"], 2)

    return {"D1": d1,
            "D2": {"share_of_dd_on_ge3_concurrent": round(share_ge3, 3),
                   "dd_window_bars": len(grid),
                   "concurrency_hist": {str(k): int((conc == k).sum())
                                        for k in sorted(set(conc.tolist()))}},
            "D3": d3, "D4": d4}


# ------------------------------------------------------------------ summarize
def summarize(label, sim, cost_name):
    taken = sim["taken"]
    if not taken:
        return {"config": label, "cost": cost_name, "trades": 0}
    rs = np.array([r["net_r"] for r in taken])
    wins = rs[rs > 0]
    losses = rs[rs <= 0]
    n = len(rs)
    gw, gl = wins.sum(), -losses.sum()
    ret = sim["final_equity"] / pb.START_EQUITY - 1
    dd = sim["max_drawdown"]
    return {
        "config": label, "cost": cost_name, "trades": n,
        "win_rate_pct": round(float((rs > 0).mean()) * 100, 1),
        "expectancy_net_r": round(float(rs.mean()), 3),
        "profit_factor": round(float(gw / gl), 2) if gl > 0 else None,
        "total_return_pct": round(ret * 100, 2),
        "max_drawdown_pct": round(dd * 100, 2),
        "calmar": round(float(ret / dd), 3) if dd > 0 else None,
        "avg_winner_r": round(float(wins.mean()), 3) if len(wins) else None,
        "avg_loser_r": round(float(losses.mean()), 3) if len(losses) else None,
        "skipped_gate": sim["skipped_gate"], "skipped_cap": sim["skipped_cap"],
        "skipped_risk": sim["skipped_risk"],
    }


def main():
    global LOGRET
    universe = pb.UNIVERSE_X
    all_trades, closes_4h, logret_4h, skipped = [], {}, {}, 0
    for sym in universe:
        path = os.path.join(pb.CACHE, f"h4_{sym}.pkl")
        df = pd.read_pickle(path)
        df = pb.add_pine_indicators(df)
        closes_4h[sym] = df["Close"]
        logret_4h[sym] = np.log(df["Close"]).diff()
        tr, sg = gen_candidates(sym, df)
        all_trades.extend(tr)
        skipped += sg
        print(f"  {sym}: {len(tr)} trades", flush=True)
    LOGRET = logret_4h
    all_trades.sort(key=lambda t: t["entry_time"])
    n_candidates = len(all_trades)
    print(f"candidates: {n_candidates}", flush=True)

    results = {"notes": ["Exposure study. Spec EXPOSURE_SPEC.md frozen before testing.",
                         "V3.6 entries/exits identical; sizing fixed 1%; portfolio gates only."],
               "n_candidates": n_candidates, "variants": {}}

    gates = make_gates(logret_4h)
    variants = [("V0_control", None, pb.MAX_CONCURRENT)]
    for name, g in gates.items():
        variants.append((name, g, pb.MAX_CONCURRENT))
    variants.append(("E4_cap3", None, 3))

    for vname, gate, mconc in variants:
        results["variants"][vname] = {}
        for cost_name, cost in pb.COSTS.items():
            sim = ExposureSim(closes_4h, logret_4h, cost, max_concurrent=mconc,
                              gate=gate, gate_name=vname)
            port = sim.run(all_trades)
            s = summarize(f"PINE_V36_exposure:{vname}", port, cost_name)
            s["fill_rate_pct"] = round(len(port["taken"]) / n_candidates * 100, 1)
            results["variants"][vname][cost_name] = s
            print(f"{vname} [{cost_name}]: n={s['trades']} exp={s['expectancy_net_r']}R "
                  f"PF={s['profit_factor']} ret={s['total_return_pct']}% "
                  f"dd={s['max_drawdown_pct']}% calmar={s['calmar']} "
                  f"gate_skip={s['skipped_gate']} cap_skip={s['skipped_cap']}", flush=True)

    # fidelity check: no-gate sim vs pb.simulate_portfolio
    for cost_name, cost in pb.COSTS.items():
        ref = pb.simulate_portfolio(all_trades, closes_4h, cost, pb.RISK_PCT)
        sim = ExposureSim(closes_4h, logret_4h, cost)
        port = sim.run(all_trades)
        ref_ids = sorted(id(t) for t in all_trades if True)
        got_ids = sorted(id(r["trade"]) for r in port["taken"])
        # control takes everything except cap/risk skips; compare taken sets
        print(f"fidelity [{cost_name}]: ref_eq={ref['final_equity']:.2f} "
              f"got_eq={port['final_equity']:.2f} ref_dd={ref['max_drawdown']:.4f} "
              f"got_dd={port['max_drawdown']:.4f} ref_skip={ref['skipped_cap_count']} "
              f"got_skip={port['skipped_cap']}", flush=True)

    # diagnostics on the 4bps control sim
    sim = ExposureSim(closes_4h, logret_4h, pb.COSTS["4bps"])
    port = sim.run(all_trades)
    results["diagnostics"] = diagnose(port, closes_4h, all_trades)

    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {OUT_JSON}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
