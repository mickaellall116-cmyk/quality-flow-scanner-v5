"""Monte Carlo / sequence-risk study on Pine V3.6 baseline trades.

Expectation-setting only: empirical resampling of the actual trade R-multiples.
Nothing is optimized, retuned, or changed.
Spec: MONTECARLO_SPEC.md (frozen before running).
Local-only. No existing files modified.
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "pine_mfe_mae"))
import pine_backtest as pb
import pine_mfe_mae as mm

SEED = 20260918
N_SIMS = 10000
START_EQUITY = 10000.0
RUIN_FRAC = 0.50  # ruin = equity ever below 50% of start


def load_bull_r():
    trades = json.load(open(os.path.join(REPO, "pine_trades_4h.json")))
    trades.sort(key=lambda t: t["signal_time"])
    r = np.array([t["net_r"] for t in trades], dtype=float)
    assert len(r) == 263, f"bull n={len(r)}"
    assert abs(r.mean() - 0.195) < 0.005, f"bull mean={r.mean()}"
    return r, [t["signal_time"] for t in trades]


def load_2022_r():
    paths = {}
    for d in (mm.CACHE_2022_OLD, mm.CACHE_2022_NEW):
        if not os.path.isdir(d):
            continue
        for p in glob.glob(os.path.join(d, "d4h_2022_*.pkl")):
            sym = os.path.basename(p)[len("d4h_2022_"):-len(".pkl")]
            paths[sym] = p
    trades = []
    for sym, p in sorted(paths.items()):
        df = pd.read_pickle(p)
        if "Volume" not in df.columns or df["Volume"].isna().all():
            continue
        df = pb.add_pine_indicators(df)
        tr, _ = mm.gen_trades_lifecycle(sym, df, cutoff=mm.CUTOFF_2022,
                                        eod_liquidate=True)
        trades.extend(tr)
    trades.sort(key=lambda t: t["entry_time"])
    r = np.array([pb._outcome(t["entry"], t["stop"], t["exit"],
                              pb.COSTS["4bps"])[2] for t in trades])
    assert len(r) == 39, f"2022 n={len(r)}"
    assert abs(r.mean() - 0.287) < 0.05, f"2022 mean={r.mean()}"
    return r


def realized_stats(r, risk=0.01):
    """Stats for one realized (or simulated) ordered R sequence."""
    cum = np.cumsum(r)
    peak = np.maximum.accumulate(np.concatenate([[0.0], cum]))
    dd_r = float(np.max(peak - np.concatenate([[0.0], cum])))
    term_r = float(cum[-1])
    # longest losing streak (net_r < 0)
    loss = r < 0
    x = np.concatenate([[False], loss, [False]]).astype(np.int8)
    d = np.diff(x)
    starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
    if len(starts):
        lens = ends - starts
        i = int(np.argmax(lens))
        streak_n = int(lens[i])
        streak_r = float(r[starts[i]:ends[i]].sum())
    else:
        streak_n, streak_r = 0, 0.0
    # sequential portfolio model
    eq = START_EQUITY * np.cumprod(1.0 + risk * r)
    eq_full = np.concatenate([[START_EQUITY], eq])
    epeak = np.maximum.accumulate(eq_full)
    dd_pct = float(np.max((epeak - eq_full) / epeak))
    term_pct = float(eq[-1] / START_EQUITY - 1.0)
    ruined = bool(np.any(eq < START_EQUITY * RUIN_FRAC))
    return {"terminal_r": term_r, "maxdd_r": dd_r,
            "streak_trades": streak_n, "streak_r": streak_r,
            "terminal_pct": term_pct, "maxdd_pct": dd_pct, "ruined": ruined}


def pcts(x, qs=(5, 10, 25, 50, 75, 90, 95, 99)):
    x = np.asarray(x, dtype=float)
    return {f"p{q}": float(np.percentile(x, q)) for q in qs}


def run_leg(r, n_trades, label, roll_window, seed_offset):
    rng = np.random.default_rng(SEED + seed_offset)
    draws = rng.choice(r, size=(N_SIMS, n_trades), replace=True)

    cum = np.cumsum(draws, axis=1)
    cum0 = np.concatenate([np.zeros((N_SIMS, 1)), cum], axis=1)
    peak = np.maximum.accumulate(cum0, axis=1)
    maxdd_r = np.max(peak - cum0, axis=1)
    terminal_r = cum[:, -1]

    # losing streaks (loop over sims; 10k x n_trades is cheap)
    streak_n = np.zeros(N_SIMS, dtype=int)
    streak_r = np.zeros(N_SIMS)
    for i in range(N_SIMS):
        loss = draws[i] < 0
        x = np.concatenate([[False], loss, [False]]).astype(np.int8)
        d = np.diff(x)
        starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
        if len(starts):
            lens = ends - starts
            j = int(np.argmax(lens))
            streak_n[i] = int(lens[j])
            streak_r[i] = float(draws[i, starts[j]:ends[j]].sum())

    # portfolio space at several risk levels (sequential model)
    port = {}
    for risk in (0.005, 0.01, 0.02):
        eq = START_EQUITY * np.cumprod(1.0 + risk * draws, axis=1)
        eq0 = np.concatenate([np.full((N_SIMS, 1), START_EQUITY), eq], axis=1)
        epeak = np.maximum.accumulate(eq0, axis=1)
        dd_pct = np.max((epeak - eq0) / epeak, axis=1)
        term_pct = eq[:, -1] / START_EQUITY - 1.0
        ruined = np.any(eq < START_EQUITY * RUIN_FRAC, axis=1)
        port[f"risk_{risk}"] = {
            "terminal_pct": pcts(term_pct * 100),
            "maxdd_pct": pcts(dd_pct * 100),
            "p_ruin": float(ruined.mean()),
        }

    out = {
        "label": label, "n_trades": n_trades, "n_sims": N_SIMS, "seed": SEED,
        "terminal_r": pcts(terminal_r),
        "maxdd_r": pcts(maxdd_r),
        "p_maxdd_r_gt_10": float(np.mean(maxdd_r > 10)),
        "p_maxdd_r_gt_20": float(np.mean(maxdd_r > 20)),
        "longest_streak_trades": pcts(streak_n),
        "worst_streak_r": pcts(streak_r),
        "portfolio": port,
    }
    if roll_window and n_trades > roll_window:
        c = np.concatenate([np.zeros((N_SIMS, 1)), cum], axis=1)
        roll = (c[:, roll_window:] - c[:, :-roll_window]) / roll_window
        out["rolling_expectancy"] = {
            "window_trades": roll_window, **pcts(roll.ravel())}
    # realized path percentiles (computed by caller via realized_stats)
    return out, draws


def main():
    print("loading bull trades...", flush=True)
    r_bull, _ = load_bull_r()
    print("regenerating 2022 trades...", flush=True)
    r_2022 = load_2022_r()

    real_bull = realized_stats(r_bull, risk=0.01)
    real_2022 = realized_stats(r_2022, risk=0.01)
    # realized R-space max DD sanity
    print(f"realized bull: terminal {real_bull['terminal_r']:.2f}R, "
          f"maxDD_R {real_bull['maxdd_r']:.2f}R, streak {real_bull['streak_trades']}, "
          f"seq-terminal {real_bull['terminal_pct']*100:.1f}%, seq-DD {real_bull['maxdd_pct']*100:.1f}%", flush=True)
    print(f"realized 2022: terminal {real_2022['terminal_r']:.2f}R, "
          f"maxDD_R {real_2022['maxdd_r']:.2f}R", flush=True)

    print("running bull MC...", flush=True)
    bull, _ = run_leg(r_bull, 263, "bull_2024-2026_UX51_4h", roll_window=131,
                      seed_offset=0)
    print("running 2022 MC...", flush=True)
    bear, _ = run_leg(r_2022, 39, "bear_2022_4h", roll_window=None,
                      seed_offset=1)

    results = {"bull": bull, "bear_2022": bear,
               "realized": {"bull": real_bull, "bear_2022": real_2022}}
    json.dump(results, open(os.path.join(HERE, "montecarlo_results.json"), "w"),
              indent=1)
    print("wrote montecarlo_results.json", flush=True)


if __name__ == "__main__":
    main()
