"""W3 full protocol analysis for F5 (sector leadership) + F6 (60-day-high proximity).

Populations: P1 = canonical taken trades (working set, n=353, primary);
             P2 = v3 independent trades (working set, n=1579, robustness).

For each factor (base variant), on P1 (and summary on P2):
  1. selection rate, selected exp, unselected exp, delta (headline 50bps)
  2. cost ladder 25/50/75/100bps
  3. dev Oct2023-Dec2024 / val Jan2025-Sep2026 split (thresholds pre-registered;
     nothing refit - "frozen after dev" is vacuous; reported as stability)
  4. walk-forward 12mo observe / 6mo test (test-window deltas; nothing refit)
  5. year splits 2024/2025/2026
  6. perturbations (pre-registered)
  7. concentration: drop top-1/3/5 selected-R contributors, recompute delta
  8. bootstrap >=5000 on delta (full + validation)
  9. leave-one-symbol-out on delta
 10. absolute: selected clears zero?

Gates: PASS = selected beats unselected on val + costs + perturbation,
survives LOSO/concentration, selected clears zero. MAYBE = directionally
consistent but thin/fragile. FAIL = otherwise.
"""
import json
import os

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
BPS = [25, 50, 75, 100]
DEV_END = "2025-01-01"  # dev = < 2025-01-01 (Oct2023-Dec2024), val = >= 2025-01-01


def load(tag):
    with open(os.path.join(OUT, f"trade_factors_{tag}.json")) as fh:
        return json.load(fh)


def exp_of(rs):
    return float(np.mean(rs)) if len(rs) else float("nan")


def split(rows, flag, cost):
    col = f"net_r_{cost}bps"
    sel = [r[col] for r in rows if r[flag]]
    uns = [r[col] for r in rows if not r[flag]]
    return sel, uns


def block(rows, flag, cost):
    sel, uns = split(rows, flag, cost)
    return {
        "n": len(rows),
        "n_sel": len(sel), "n_uns": len(uns),
        "sel_rate": len(sel) / len(rows) if rows else 0.0,
        "sel_exp": exp_of(sel), "uns_exp": exp_of(uns),
        "delta": exp_of(sel) - exp_of(uns),
    }


def period(rows, flag, cost, lo, hi):
    sub = [r for r in rows if lo <= r["signal_bar_close_at"][:10] < hi]
    return block(sub, flag, cost)


def bootstrap_delta(rows, flag, cost, n_iter=5000, seed=7):
    col = f"net_r_{cost}bps"
    sel = np.array([r[col] for r in rows if r[flag]])
    uns = np.array([r[col] for r in rows if not r[flag]])
    if len(sel) < 5 or len(uns) < 5:
        return {"n_iter": 0, "frac_pos": None, "ci95": [None, None]}
    rng = np.random.default_rng(seed)
    ds = np.empty(n_iter)
    for i in range(n_iter):
        ds[i] = rng.choice(sel, len(sel), replace=True).mean() - \
                rng.choice(uns, len(uns), replace=True).mean()
    return {"n_iter": n_iter, "frac_pos": float(np.mean(ds > 0)),
            "ci95": [float(np.percentile(ds, 2.5)),
                     float(np.percentile(ds, 97.5))],
            "mean": float(ds.mean())}


def loso(rows, flag, cost):
    """delta recomputed dropping each symbol once."""
    syms = sorted({r["symbol"] for r in rows})
    base = block(rows, flag, cost)["delta"]
    worst = base
    worst_sym = None
    flips = 0
    max_infl = 0.0
    for s in syms:
        d = block([r for r in rows if r["symbol"] != s], flag, cost)["delta"]
        infl = abs(d - base)
        if infl > max_infl:
            max_infl = infl
        if d < worst:
            worst, worst_sym = d, s
        if (d > 0) != (base > 0) and not np.isnan(d):
            flips += 1
    return {"base_delta": base, "worst_delta": worst,
            "worst_symbol": worst_sym, "n_symbols": len(syms),
            "sign_flips": flips, "max_single_symbol_influence": max_infl}


def concentration(rows, flag, cost):
    """drop top-1/3/5 symbols by selected-set total R, recompute delta."""
    col = f"net_r_{cost}bps"
    tot = {}
    for r in rows:
        if r[flag]:
            tot[r["symbol"]] = tot.get(r["symbol"], 0.0) + r[col]
    ranked = sorted(tot, key=lambda s: -tot[s])
    out = {}
    for k in (1, 3, 5):
        drop = set(ranked[:k])
        out[f"drop_top{k}"] = block([r for r in rows if r["symbol"] not in drop],
                                    flag, cost)["delta"]
    out["top5_contributors"] = [[s, round(tot[s], 3)] for s in ranked[:5]]
    return out


def run_factor(rows, flag, label):
    R = {"factor": label, "flag": flag, "population_n": len(rows)}
    R["overall_50bps"] = block(rows, flag, 50)
    R["cost_ladder"] = {f"{c}bps": block(rows, flag, c) for c in BPS}
    R["dev"] = period(rows, flag, 50, "2023-10-01", DEV_END)
    R["val"] = period(rows, flag, 50, DEV_END, "2026-10-01")
    R["year2024"] = period(rows, flag, 50, "2024-01-01", "2025-01-01")
    R["year2025"] = period(rows, flag, 50, "2025-01-01", "2026-01-01")
    R["year2026"] = period(rows, flag, 50, "2026-01-01", "2026-10-01")
    wf = [("2023-10-01", "2024-10-01", "2024-10-01", "2025-04-01"),
          ("2024-04-01", "2025-04-01", "2025-04-01", "2025-10-01"),
          ("2024-10-01", "2025-10-01", "2025-10-01", "2026-04-01"),
          ("2025-04-01", "2026-04-01", "2026-04-01", "2026-10-01")]
    R["walkforward"] = [
        {"observe": f"{a}>{b}", "test": f"{c}>{d}",
         **period(rows, flag, 50, c, d)} for a, b, c, d in wf]
    R["bootstrap_full"] = bootstrap_delta(rows, flag, 50, n_iter=5000)
    val_rows = [r for r in rows if r["signal_bar_close_at"][:10] >= DEV_END]
    R["bootstrap_val"] = bootstrap_delta(val_rows, flag, 50, n_iter=5000)
    R["loso"] = loso(rows, flag, 50)
    R["concentration"] = concentration(rows, flag, 50)
    sel = [r["net_r_50bps"] for r in rows if r[flag]]
    R["selected_abs"] = {"n": len(sel), "exp": exp_of(sel)}
    return R


def summarize_p2(rows, flag, label):
    return {"factor": label, "flag": flag, "population_n": len(rows),
            "overall_50bps": block(rows, flag, 50),
            "cost_ladder": {f"{c}bps": block(rows, flag, c) for c in BPS},
            "dev": period(rows, flag, 50, "2023-10-01", DEV_END),
            "val": period(rows, flag, 50, DEV_END, "2026-10-01"),
            "perturbations": None}


def main():
    p1 = load("P1")
    p2 = load("P2")

    f5 = run_factor(p1, "f5_base", "F5 sector leadership (top-3, 20d vs SPY)")
    f5["perturbations"] = {
        name: block(p1, f"f5_{name}", 50)["delta"]
        for name in ["base", "top2", "top4", "w15", "w25"]}
    f5["perturb_blocks"] = {
        name: block(p1, f"f5_{name}", 50)
        for name in ["base", "top2", "top4", "w15", "w25"]}
    f5["p2"] = summarize_p2(p2, "f5_base", "F5 on P2 independent trades")

    f6 = run_factor(p1, "f6_base", "F6 60-day-high proximity (>0.8)")
    f6["perturbations"] = {
        name: block(p1, f"f6_{name}", 50)["delta"]
        for name in ["base", "t07", "t09", "w40", "w90"]}
    f6["perturb_blocks"] = {
        name: block(p1, f"f6_{name}", 50)
        for name in ["base", "t07", "t09", "w40", "w90"]}
    f6["p2"] = summarize_p2(p2, "f6_base", "F6 on P2 independent trades")

    for rec, name in [(f5, "F5"), (f6, "F6")]:
        with open(os.path.join(OUT, f"{name}.json"), "w") as fh:
            json.dump(rec, fh, indent=1)
    # quick console readout
    for rec in (f5, f6):
        b = rec["overall_50bps"]
        print(f"{rec['factor']}: n={b['n']} sel_rate={b['sel_rate']:.2f} "
              f"sel={b['sel_exp']:+.4f} uns={b['uns_exp']:+.4f} "
              f"delta={b['delta']:+.4f} | dev={rec['dev']['delta']:+.4f} "
              f"val={rec['val']['delta']:+.4f} | boot_val_pos={rec['bootstrap_val']['frac_pos']}")


if __name__ == "__main__":
    main()
