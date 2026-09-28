#!/usr/bin/env python3
"""
Clean HEMA entry-timing research.

Study A: standalone 4H HEMA bullish crossover vs EMA crossover and
symbol-month matched random non-event bars.
Study B: paired QF timing comparison for setups that are HEMA-bearish at the
QF signal and receive a bullish HEMA crossover within the next four completed
4H bars.

Research-only; does not change live/frozen Quality Flow.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research_notes.hema_research import fetch_symbol, regular_1h, resample_closed_4h, ema
from research_notes.hema_qf_portfolio import SYMBOLS, prepare_symbol

OUT = Path("hema_entry_timing")
OUT.mkdir(exist_ok=True)

HORIZONS = [1, 2, 4, 6, 10, 20]
RANDOM_SEEDS = list(range(500))


def add_ema_cross(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    e20 = ema(x["Close"], 20)
    e40 = ema(x["Close"], 40)
    x["ema20"] = e20
    x["ema40"] = e40
    x["ema_big_green"] = (e20 > e40) & (e20.shift(1) <= e40.shift(1))
    return x


def spy_return(spy: pd.DataFrame, entry_ts, exit_ts) -> float | None:
    if entry_ts not in spy.index or exit_ts not in spy.index:
        return None
    e = float(spy.loc[entry_ts, "Open"])
    x = float(spy.loc[exit_ts, "Close"])
    if not np.isfinite(e) or not np.isfinite(x) or e <= 0:
        return None
    return x / e - 1.0


def event_record(sym: str, df: pd.DataFrame, spy: pd.DataFrame, i: int, kind: str) -> dict | None:
    if i + 1 >= len(df):
        return None
    entry_i = i + 1
    entry = float(df["Open"].iloc[entry_i])
    if not np.isfinite(entry) or entry <= 0:
        return None
    rec = {
        "symbol": sym,
        "kind": kind,
        "signal_time": str(df.index[i]),
        "entry_time": str(df.index[entry_i]),
        "entry": entry,
        "year": int(df.index[i].year),
        "month": str(df.index[i].to_period("M")) if df.index[i].tzinfo is None else str(df.index[i].tz_localize(None).to_period("M")),
    }
    for h in HORIZONS:
        exit_i = entry_i + h - 1
        if exit_i >= len(df):
            continue
        exit_px = float(df["Close"].iloc[exit_i])
        r = exit_px / entry - 1.0
        sr = spy_return(spy, df.index[entry_i], df.index[exit_i])
        rec[f"ret_{h}"] = r
        rec[f"excess_{h}"] = r - sr if sr is not None else np.nan
    return rec


def summarize_events(df: pd.DataFrame) -> dict:
    out = {"n": int(len(df))}
    for h in HORIZONS:
        c = f"ret_{h}"
        e = f"excess_{h}"
        if c in df:
            v = df[c].dropna().astype(float)
            if len(v):
                out[f"mean_ret_{h}_pct"] = float(v.mean() * 100.0)
                out[f"median_ret_{h}_pct"] = float(v.median() * 100.0)
                out[f"hit_{h}_pct"] = float((v > 0).mean() * 100.0)
        if e in df:
            v = df[e].dropna().astype(float)
            if len(v):
                out[f"mean_excess_{h}_pct"] = float(v.mean() * 100.0)
                out[f"median_excess_{h}_pct"] = float(v.median() * 100.0)
    return out


def stable_rng(seed: int, key: str) -> np.random.Generator:
    b = hashlib.sha256(f"{seed}|{key}".encode()).digest()[:8]
    return np.random.default_rng(int.from_bytes(b, "little", signed=False))


def matched_random_events(frames: dict[str, pd.DataFrame], spy: pd.DataFrame, hema_events: pd.DataFrame, seed: int) -> pd.DataFrame:
    rows = []
    if hema_events.empty:
        return pd.DataFrame()
    counts = hema_events.groupby(["symbol", "month"]).size()
    for (sym, month), n in counts.items():
        df = frames[sym]
        valid = []
        for i in range(len(df)):
            if i + 1 + max(HORIZONS) - 1 >= len(df):
                continue
            ts = df.index[i]
            m = str(ts.to_period("M")) if ts.tzinfo is None else str(ts.tz_localize(None).to_period("M"))
            if m != month:
                continue
            if bool(df["big_green"].iloc[i]):
                continue
            if not np.isfinite(df["HEMA20"].iloc[i]) or not np.isfinite(df["HEMA40"].iloc[i]):
                continue
            valid.append(i)
        if not valid:
            continue
        rng = stable_rng(seed, f"{sym}|{month}")
        replace = len(valid) < int(n)
        chosen = rng.choice(valid, size=int(n), replace=replace)
        for i in np.atleast_1d(chosen):
            rec = event_record(sym, df, spy, int(i), "random")
            if rec is not None:
                rows.append(rec)
    return pd.DataFrame(rows)


def paired_boot(values: np.ndarray, seed: int = 280928, reps: int = 20000) -> dict:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {}
    rng = np.random.default_rng(seed)
    means = np.empty(reps)
    for j in range(reps):
        means[j] = rng.choice(x, size=len(x), replace=True).mean()
    return {
        "n": int(len(x)),
        "mean": float(x.mean()),
        "ci95_low": float(np.quantile(means, 0.025)),
        "ci95_high": float(np.quantile(means, 0.975)),
        "p_le_zero": float((1 + np.sum(means <= 0)) / (reps + 1)),
    }


def qf_timing_record(sym: str, df: pd.DataFrame, spy: pd.DataFrame, i: int) -> dict | None:
    # Common terminal = close of the 10th 4H bar after the QF signal.
    if i + 10 >= len(df) or i + 1 >= len(df):
        return None
    base_i = i + 1
    base_entry = float(df["Open"].iloc[base_i])
    terminal_i = i + 10
    terminal = float(df["Close"].iloc[terminal_i])
    if base_entry <= 0 or not np.isfinite(base_entry) or not np.isfinite(terminal):
        return None

    hema_bull = bool(df["bull_regime"].iloc[i])
    cross_i = None
    if not hema_bull:
        for k in range(i + 1, min(i + 5, len(df))):
            if bool(df["big_green"].iloc[k]) and k + 1 <= terminal_i:
                cross_i = k
                break

    if hema_bull:
        state = "already_bull"
    elif cross_i is not None:
        state = "bear_then_cross_within4"
    else:
        state = "bear_no_cross_within4"

    sr = spy_return(spy, df.index[base_i], df.index[terminal_i])
    base_ret = terminal / base_entry - 1.0
    rec = {
        "symbol": sym,
        "qf_signal_time": str(df.index[i]),
        "baseline_entry_time": str(df.index[base_i]),
        "baseline_entry": base_entry,
        "terminal_time": str(df.index[terminal_i]),
        "terminal_close": terminal,
        "hema_state": state,
        "baseline_ret_10": base_ret,
        "baseline_excess_10": base_ret - sr if sr is not None else np.nan,
        "year": int(df.index[i].year),
    }

    bw = df.iloc[base_i:terminal_i+1]
    rec["baseline_mae_pct"] = float((bw["Low"].min() / base_entry - 1.0) * 100.0)
    rec["baseline_mfe_pct"] = float((bw["High"].max() / base_entry - 1.0) * 100.0)

    if cross_i is not None:
        alt_i = cross_i + 1
        alt_entry = float(df["Open"].iloc[alt_i])
        if alt_entry > 0 and np.isfinite(alt_entry):
            alt_ret = terminal / alt_entry - 1.0
            aw = df.iloc[alt_i:terminal_i+1]
            rec.update({
                "cross_time": str(df.index[cross_i]),
                "alt_entry_time": str(df.index[alt_i]),
                "alt_entry": alt_entry,
                "delay_bars": int(alt_i - base_i),
                "alt_ret_common_terminal": alt_ret,
                "ret_diff_alt_minus_base": alt_ret - base_ret,
                "entry_price_improvement_pct": (base_entry / alt_entry - 1.0) * 100.0,
                "alt_mae_pct": float((aw["Low"].min() / alt_entry - 1.0) * 100.0),
                "alt_mfe_pct": float((aw["High"].max() / alt_entry - 1.0) * 100.0),
            })
    return rec


def group_qf(df: pd.DataFrame) -> dict:
    out = {}
    for state, g in df.groupby("hema_state"):
        v = g["baseline_ret_10"].dropna().astype(float)
        e = g["baseline_excess_10"].dropna().astype(float)
        out[state] = {
            "n": int(len(g)),
            "mean_ret_10_pct": float(v.mean()*100.0) if len(v) else None,
            "median_ret_10_pct": float(v.median()*100.0) if len(v) else None,
            "hit_10_pct": float((v>0).mean()*100.0) if len(v) else None,
            "mean_excess_10_pct": float(e.mean()*100.0) if len(e) else None,
        }
    return out


def main() -> None:
    spy_i = regular_1h(fetch_symbol("SPY", "1h", "729d"))
    spy_h4 = resample_closed_4h(spy_i, "SPY")

    frames = {}
    for k, sym in enumerate(SYMBOLS, 1):
        print(f"[{k}/{len(SYMBOLS)}] {sym}")
        h = prepare_symbol(sym, spy_h4)
        if h is not None:
            frames[sym] = add_ema_cross(h)
    print("frames", len(frames))

    # Study A
    hema_rows, ema_rows = [], []
    for sym, df in frames.items():
        for i in np.flatnonzero(df["big_green"].fillna(False).to_numpy()):
            if i + max(HORIZONS) >= len(df):
                continue
            r = event_record(sym, df, spy_h4, int(i), "hema_big_green")
            if r is not None:
                hema_rows.append(r)
        for i in np.flatnonzero(df["ema_big_green"].fillna(False).to_numpy()):
            if i + max(HORIZONS) >= len(df):
                continue
            r = event_record(sym, df, spy_h4, int(i), "ema20_40_big_green")
            if r is not None:
                ema_rows.append(r)

    hema = pd.DataFrame(hema_rows)
    emac = pd.DataFrame(ema_rows)
    hema.to_csv(OUT / "hema_events.csv", index=False)
    emac.to_csv(OUT / "ema_events.csv", index=False)

    random_summary_rows = []
    random_events_first = None
    for seed in RANDOM_SEEDS:
        rnd = matched_random_events(frames, spy_h4, hema, seed)
        if random_events_first is None:
            random_events_first = rnd.copy()
        s = summarize_events(rnd)
        s["seed"] = seed
        random_summary_rows.append(s)
        if seed % 50 == 0:
            print("RANDOM", seed)
    random_summaries = pd.DataFrame(random_summary_rows)
    random_summaries.to_csv(OUT / "random_matched_summaries.csv", index=False)
    if random_events_first is not None:
        random_events_first.to_csv(OUT / "random_seed0_events.csv", index=False)

    hema_summary = summarize_events(hema)
    ema_summary = summarize_events(emac)

    random_compare = {}
    for h in HORIZONS:
        col = f"mean_excess_{h}_pct"
        if col in random_summaries and len(random_summaries[col].dropna()):
            vals = random_summaries[col].dropna().astype(float)
            hv = hema_summary.get(col)
            random_compare[str(h)] = {
                "hema_mean_excess_pct": hv,
                "random_mean_pct": float(vals.mean()),
                "random_p2_5_pct": float(vals.quantile(0.025)),
                "random_p50_pct": float(vals.quantile(0.5)),
                "random_p97_5_pct": float(vals.quantile(0.975)),
                "one_sided_p_random_ge_hema": float((1 + int((vals >= hv).sum())) / (len(vals) + 1)) if hv is not None else None,
            }

    yearly_a = {}
    for kind, d in [("hema", hema), ("ema", emac)]:
        yearly_a[kind] = {}
        for y, g in d.groupby("year"):
            yearly_a[kind][str(int(y))] = summarize_events(g)

    sym10 = []
    if not hema.empty:
        for sym, g in hema.groupby("symbol"):
            v = g["excess_10"].dropna().astype(float)
            if len(v):
                sym10.append({"symbol": sym, "n": int(len(v)), "mean_excess_10_pct": float(v.mean()*100.0)})
    sym10 = sorted(sym10, key=lambda z: z["mean_excess_10_pct"], reverse=True)

    # Study B
    qf_rows = []
    for sym, df in frames.items():
        for i in np.flatnonzero(df["qf_event"].fillna(False).to_numpy()):
            rec = qf_timing_record(sym, df, spy_h4, int(i))
            if rec is not None:
                qf_rows.append(rec)
    qf = pd.DataFrame(qf_rows)
    qf.to_csv(OUT / "qf_timing_pairs.csv", index=False)

    paired = qf[qf["hema_state"] == "bear_then_cross_within4"].copy() if not qf.empty else pd.DataFrame()
    timing_result = {
        "n": int(len(paired)),
        "mean_delay_bars": float(paired["delay_bars"].mean()) if len(paired) else None,
        "mean_entry_price_improvement_pct": float(paired["entry_price_improvement_pct"].mean()) if len(paired) else None,
        "median_entry_price_improvement_pct": float(paired["entry_price_improvement_pct"].median()) if len(paired) else None,
        "mean_baseline_ret_pct": float(paired["baseline_ret_10"].mean()*100.0) if len(paired) else None,
        "mean_alt_ret_pct": float(paired["alt_ret_common_terminal"].mean()*100.0) if len(paired) else None,
        "mean_alt_minus_base_pct_points": float(paired["ret_diff_alt_minus_base"].mean()*100.0) if len(paired) else None,
        "paired_boot_alt_minus_base": paired_boot(paired["ret_diff_alt_minus_base"].to_numpy()*100.0) if len(paired) else {},
        "mean_baseline_mae_pct": float(paired["baseline_mae_pct"].mean()) if len(paired) else None,
        "mean_alt_mae_pct": float(paired["alt_mae_pct"].mean()) if len(paired) else None,
        "mean_baseline_mfe_pct": float(paired["baseline_mfe_pct"].mean()) if len(paired) else None,
        "mean_alt_mfe_pct": float(paired["alt_mfe_pct"].mean()) if len(paired) else None,
    }

    qf_yearly = {}
    for y, g in qf.groupby("year"):
        qf_yearly[str(int(y))] = group_qf(g)

    payload = {
        "data_note": "30-symbol DST-safe recent-history 4H structural-core surrogate; not canonical 131-symbol PIT",
        "study_a": {
            "hema": hema_summary,
            "ema_control": ema_summary,
            "matched_random": random_compare,
            "yearly": yearly_a,
            "hema_symbol_concentration_10bar": sym10,
        },
        "study_b": {
            "qf_state_groups": group_qf(qf),
            "paired_wait_for_cross": timing_result,
            "yearly_qf_groups": qf_yearly,
        },
    }
    (OUT / "results.json").write_text(json.dumps(payload, indent=2))
    print("HEMA_ENTRY_TIMING_START")
    print(json.dumps(payload, indent=2))
    print("HEMA_ENTRY_TIMING_END")


if __name__ == "__main__":
    main()
