#!/usr/bin/env python3
"""
DEMA / TEMA / ALMA / VIDYA / FRAMA trend-probe tournament (Tournament II).

Research-only. Frozen/live Quality Flow remains unchanged.

Implements research_notes/TREND_PROBE_TOURNAMENT_II_PREREG_20260928.md exactly.
KAMA20/40 is carried only as the already-frozen benchmark; it is not retuned.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from research_notes.hema_research import fetch_symbol, regular_1h, resample_closed_4h
from research_notes.hema_qf_portfolio import SYMBOLS, prepare_symbol

OUT = Path("trend_probe_tournament_ii")
OUT.mkdir(exist_ok=True)

HORIZONS = [1, 2, 4, 6, 10, 20]
RANDOM_SEEDS = list(range(500))
WARMUP = 215
BOOT_REPS = 10000
BOOT_SEED = 20260928
# Order: new candidates first, frozen KAMA benchmark last.
INDICATORS = ["DEMA", "TEMA", "ALMA", "VIDYA", "FRAMA", "KAMA"]


def month_key(ts) -> str:
    t = pd.Timestamp(ts)
    if t.tzinfo is not None:
        t = t.tz_localize(None)
    return str(t.to_period("M"))


# ---------------------------------------------------------------- indicators

def dema(s: pd.Series, n: int) -> pd.Series:
    e1 = s.ewm(span=n, adjust=False).mean()
    e2 = e1.ewm(span=n, adjust=False).mean()
    return 2.0 * e1 - e2


def tema(s: pd.Series, n: int) -> pd.Series:
    e1 = s.ewm(span=n, adjust=False).mean()
    e2 = e1.ewm(span=n, adjust=False).mean()
    e3 = e2.ewm(span=n, adjust=False).mean()
    return 3.0 * e1 - 3.0 * e2 + e3


def alma(s: pd.Series, n: int, offset: float = 0.85, sigma: float = 6.0) -> pd.Series:
    # Standard Arnaud Legoux formulation: m = offset*(n-1), s = n/sigma.
    n = int(n)
    m = offset * (n - 1)
    sc = n / sigma
    idx = np.arange(n, dtype=float)
    w = np.exp(-((idx - m) ** 2) / (2.0 * sc ** 2))
    w = w / w.sum()
    return s.rolling(n).apply(lambda x: float(np.dot(x, w)), raw=True)


def vidya(s: pd.Series, n: int) -> pd.Series:
    # Chande VIDYA. alpha_t = 2/(n+1) * |CMO_n|/100, CMO length = line length.
    n = int(n)
    diff = s.diff()
    up = diff.clip(lower=0.0)
    down = (-diff).clip(lower=0.0)
    sum_up = up.rolling(n).sum()
    sum_down = down.rolling(n).sum()
    denom = (sum_up + sum_down).replace(0.0, np.nan)
    cmo = 100.0 * (sum_up - sum_down) / denom
    alpha = (2.0 / (n + 1.0)) * (cmo.abs() / 100.0)
    alpha = alpha.fillna(0.0).clip(0.0, 1.0)

    out = pd.Series(np.nan, index=s.index, dtype=float)
    vals = s.to_numpy(dtype=float)
    av = alpha.to_numpy(dtype=float)
    prev = np.nan
    for i in range(len(s)):
        v = vals[i]
        if not np.isfinite(v):
            out.iloc[i] = prev
            continue
        if not np.isfinite(prev):
            prev = v
            out.iloc[i] = v
            continue
        a = av[i]
        prev = a * v + (1.0 - a) * prev
        out.iloc[i] = prev
    return out


def frama(high: pd.Series, low: pd.Series, n: int) -> pd.Series:
    # Ehlers FRAMA, standard half-window fractal-dimension estimate.
    # Price input is the median price (H+L)/2 per Ehlers.
    n = int(n)
    n2 = n // 2
    px = (high.astype(float) + low.astype(float)) / 2.0
    out = pd.Series(np.nan, index=px.index, dtype=float)
    hv = high.to_numpy(dtype=float)
    lv = low.to_numpy(dtype=float)
    pv = px.to_numpy(dtype=float)
    prev = np.nan
    for i in range(n - 1, len(px)):
        h1 = float(np.max(hv[i - n2 + 1:i + 1]))
        l1 = float(np.min(lv[i - n2 + 1:i + 1]))
        h2 = float(np.max(hv[i - n + 1:i - n2 + 1]))
        l2 = float(np.min(lv[i - n + 1:i - n2 + 1]))
        h3 = float(np.max(hv[i - n + 1:i + 1]))
        l3 = float(np.min(lv[i - n + 1:i + 1]))
        n1 = (h1 - l1) / n2
        n2v = (h2 - l2) / n2
        n3 = (h3 - l3) / n
        if n1 + n2v <= 0.0 or n3 <= 0.0:
            d = 1.0
        else:
            d = (math.log(n1 + n2v) - math.log(n3)) / math.log(2.0)
        a = math.exp(-4.6 * (d - 1.0))
        a = min(max(a, 0.01), 1.0)
        v = pv[i]
        if not np.isfinite(v):
            out.iloc[i] = prev
            continue
        if not np.isfinite(prev):
            prev = v
        else:
            prev = a * v + (1.0 - a) * prev
        out.iloc[i] = prev
    return out


def kama(s: pd.Series, er_length: int, fast: int = 2, slow: int = 30) -> pd.Series:
    """Frozen KAMA benchmark. Identical to Tournament I. Not retuned."""
    n = int(er_length)
    change = (s - s.shift(n)).abs()
    volatility = s.diff().abs().rolling(n).sum()
    er = (change / volatility.replace(0.0, np.nan)).fillna(0.0)
    fast_sc = 2.0 / (fast + 1.0)
    slow_sc = 2.0 / (slow + 1.0)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    out = pd.Series(np.nan, index=s.index, dtype=float)
    vals = s.to_numpy(dtype=float)
    scv = sc.to_numpy(dtype=float)
    first = None
    for i, v in enumerate(vals):
        if np.isfinite(v):
            first = i
            out.iloc[i] = v
            break
    if first is None:
        return out
    prev = float(out.iloc[first])
    for i in range(first + 1, len(s)):
        v = vals[i]
        if not np.isfinite(v):
            out.iloc[i] = prev
            continue
        a = scv[i] if np.isfinite(scv[i]) else slow_sc ** 2
        prev = prev + a * (v - prev)
        out.iloc[i] = prev
    return out


def add_probes(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    close = x["Close"].astype(float)

    x["DEMA_fast"] = dema(close, 20)
    x["DEMA_slow"] = dema(close, 40)

    x["TEMA_fast"] = tema(close, 20)
    x["TEMA_slow"] = tema(close, 40)

    x["ALMA_fast"] = alma(close, 20, 0.85, 6.0)
    x["ALMA_slow"] = alma(close, 40, 0.85, 6.0)

    x["VIDYA_fast"] = vidya(close, 20)
    x["VIDYA_slow"] = vidya(close, 40)

    x["FRAMA_fast"] = frama(x["High"].astype(float), x["Low"].astype(float), 20)
    x["FRAMA_slow"] = frama(x["High"].astype(float), x["Low"].astype(float), 40)

    x["KAMA_fast"] = kama(close, 20, 2, 30)
    x["KAMA_slow"] = kama(close, 40, 2, 30)

    for name in INDICATORS:
        f = x[f"{name}_fast"]
        s_ = x[f"{name}_slow"]
        x[f"{name}_bull"] = f > s_
        x[f"{name}_cross_up"] = (f > s_) & (f.shift(1) <= s_.shift(1))
        px = close.replace(0.0, np.nan)
        x[f"{name}_gap"] = (f - s_) / px * 100.0
    return x


# ---------------------------------------------------------------- Study A

def spy_return(spy: pd.DataFrame, entry_ts, exit_ts) -> float:
    if entry_ts not in spy.index or exit_ts not in spy.index:
        return np.nan
    e = float(spy.loc[entry_ts, "Open"])
    x = float(spy.loc[exit_ts, "Close"])
    if not np.isfinite(e) or not np.isfinite(x) or e <= 0:
        return np.nan
    return x / e - 1.0


def forward_record(sym: str, df: pd.DataFrame, spy: pd.DataFrame, i: int, kind: str) -> dict | None:
    if i + max(HORIZONS) >= len(df) or i + 1 >= len(df):
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
        "month": month_key(df.index[i]),
    }
    for h in HORIZONS:
        xi = entry_i + h - 1
        px = float(df["Close"].iloc[xi])
        r = px / entry - 1.0
        sr = spy_return(spy, df.index[entry_i], df.index[xi])
        rec[f"ret_{h}"] = r
        rec[f"excess_{h}"] = r - sr if np.isfinite(sr) else np.nan
    return rec


def summarize_forward(d: pd.DataFrame) -> dict:
    out = {"n": int(len(d))}
    for h in HORIZONS:
        r = d[f"ret_{h}"].dropna().astype(float) if f"ret_{h}" in d else pd.Series(dtype=float)
        e = d[f"excess_{h}"].dropna().astype(float) if f"excess_{h}" in d else pd.Series(dtype=float)
        out[f"mean_ret_{h}_pct"] = float(r.mean() * 100.0) if len(r) else None
        out[f"median_ret_{h}_pct"] = float(r.median() * 100.0) if len(r) else None
        out[f"hit_{h}_pct"] = float((r > 0).mean() * 100.0) if len(r) else None
        out[f"mean_excess_{h}_pct"] = float(e.mean() * 100.0) if len(e) else None
    return out


def stable_rng(seed: int, key: str) -> np.random.Generator:
    b = hashlib.sha256(f"{seed}|{key}".encode()).digest()[:8]
    return np.random.default_rng(int.from_bytes(b, "little", signed=False))


def build_random_pool_for_indicator(
    frames: dict[str, pd.DataFrame],
    spy: pd.DataFrame,
    indicator: str,
) -> dict[tuple[str, str], np.ndarray]:
    buckets: dict[tuple[str, str], list[list[float]]] = {}
    cross_col = f"{indicator}_cross_up"
    for sym, df in frames.items():
        for i in range(WARMUP, len(df)):
            if i + max(HORIZONS) >= len(df):
                continue
            if bool(df[cross_col].iloc[i]):
                continue
            rec = forward_record(sym, df, spy, i, "random")
            if rec is None:
                continue
            row = []
            for h in HORIZONS:
                row.extend([float(rec[f"ret_{h}"]), float(rec[f"excess_{h}"])])
            buckets.setdefault((sym, rec["month"]), []).append(row)
    return {k: np.asarray(v, dtype=float) for k, v in buckets.items()}


def random_compare(events: pd.DataFrame, frames: dict[str, pd.DataFrame], spy: pd.DataFrame, indicator: str) -> tuple[dict, pd.DataFrame]:
    counts = events.groupby(["symbol", "month"]).size()
    pools = build_random_pool_for_indicator(frames, spy, indicator)
    rows = []
    for seed in RANDOM_SEEDS:
        pieces = []
        for (sym, month), n in counts.items():
            pool = pools.get((sym, month))
            if pool is None or len(pool) == 0:
                continue
            rng = stable_rng(seed, f"{sym}|{month}")
            take = int(n)
            idx = rng.choice(len(pool), size=take, replace=(len(pool) < take))
            pieces.append(pool[np.atleast_1d(idx)])
        arr = np.concatenate(pieces, axis=0) if pieces else np.empty((0, 2 * len(HORIZONS)))
        s = {"n": int(len(arr)), "seed": seed}
        for j, h in enumerate(HORIZONS):
            rv = arr[:, 2 * j] if len(arr) else np.array([], dtype=float)
            evv = arr[:, 2 * j + 1] if len(arr) else np.array([], dtype=float)
            rv = rv[np.isfinite(rv)]
            evv = evv[np.isfinite(evv)]
            s[f"mean_ret_{h}_pct"] = float(rv.mean() * 100.0) if len(rv) else None
            s[f"median_ret_{h}_pct"] = float(np.median(rv) * 100.0) if len(rv) else None
            s[f"hit_{h}_pct"] = float((rv > 0).mean() * 100.0) if len(rv) else None
            s[f"mean_excess_{h}_pct"] = float(evv.mean() * 100.0) if len(evv) else None
        rows.append(s)
        if seed % 100 == 0:
            print("RANDOM", indicator, seed, flush=True)
    rdf = pd.DataFrame(rows)
    ev = summarize_forward(events)
    comp = {}
    for h in HORIZONS:
        col = f"mean_excess_{h}_pct"
        vals = rdf[col].dropna().astype(float)
        actual = ev.get(col)
        comp[str(h)] = {
            "actual_mean_excess_pct": actual,
            "random_mean_pct": float(vals.mean()) if len(vals) else None,
            "random_p2_5_pct": float(vals.quantile(0.025)) if len(vals) else None,
            "random_p50_pct": float(vals.quantile(0.5)) if len(vals) else None,
            "random_p97_5_pct": float(vals.quantile(0.975)) if len(vals) else None,
            "one_sided_p_random_ge_actual": float((1 + int((vals >= actual).sum())) / (len(vals) + 1)) if len(vals) and actual is not None else None,
        }
    return comp, rdf


# ---------------------------------------------------------------- Study B

def qf_record(sym: str, df: pd.DataFrame, spy: pd.DataFrame, i: int) -> dict | None:
    if i < 1 or i + 20 >= len(df) or i + 1 >= len(df):
        return None
    rec = forward_record(sym, df, spy, i, "qf")
    if rec is None:
        return None
    rec["close_at_signal"] = float(df["Close"].iloc[i])
    for name in INDICATORS:
        rec[f"{name}_bull"] = bool(df[f"{name}_bull"].iloc[i])
        v = df[f"{name}_gap"].iloc[i]
        rec[f"{name}_gap"] = float(v) if np.isfinite(v) else np.nan
    return rec


def summarize_qf_group(g: pd.DataFrame) -> dict:
    if g.empty:
        return {"n": 0}
    out = {
        "n": int(len(g)),
        "mean_excess10_pct": float(g["excess_10"].mean() * 100.0),
        "median_excess10_pct": float(g["excess_10"].median() * 100.0),
        "hit10_pct": float((g["ret_10"] > 0).mean() * 100.0),
    }
    for h in [4, 6, 20]:
        out[f"mean_excess{h}_pct"] = float(g[f"excess_{h}"].mean() * 100.0)
    return out


def month_block_bootstrap_diff(qf: pd.DataFrame, bull_col: str, years: tuple[int, int]) -> dict:
    """Month-block bootstrap of (bull mean excess_10) minus (bear mean excess_10)."""
    d = qf[(qf["year"] >= years[0]) & (qf["year"] <= years[1])].copy()
    months = sorted(d["month"].dropna().unique())
    bull_by_m = {}
    bear_by_m = {}
    for m in months:
        sub = d[d["month"] == m]
        bull_by_m[m] = sub.loc[sub[bull_col] == True, "excess_10"].to_numpy(dtype=float)
        bear_by_m[m] = sub.loc[sub[bull_col] == False, "excess_10"].to_numpy(dtype=float)
    rng = np.random.default_rng(BOOT_SEED)
    diffs = np.empty(BOOT_REPS)
    nm = len(months)
    for b in range(BOOT_REPS):
        picks = rng.integers(0, nm, size=nm)
        bv = np.concatenate([bull_by_m[months[p]] for p in picks if len(bull_by_m[months[p]])])
        sv = np.concatenate([bear_by_m[months[p]] for p in picks if len(bear_by_m[months[p]])])
        bv = bv[np.isfinite(bv)]
        sv = sv[np.isfinite(sv)]
        diffs[b] = bv.mean() - sv.mean() if len(bv) and len(sv) else np.nan
    diffs = diffs[np.isfinite(diffs)]
    if not len(diffs):
        return {"n_boot": 0}
    lo = float(np.quantile(diffs, 0.025) * 100.0)
    hi = float(np.quantile(diffs, 0.975) * 100.0)
    return {
        "n_boot": int(len(diffs)),
        "n_months": nm,
        "seed": BOOT_SEED,
        "mean_diff_pct_points": float(diffs.mean() * 100.0),
        "p2_5_pct_points": lo,
        "p97_5_pct_points": hi,
        "excludes_zero": bool(lo > 0.0 or hi < 0.0),
    }


def binary_state_analysis(qf: pd.DataFrame, years: tuple[int, int]) -> dict:
    lo, hi = years
    d = qf[(qf["year"] >= lo) & (qf["year"] <= hi)].copy()
    out = {}
    for name in INDICATORS:
        col = f"{name}_bull"
        bull = d[d[col] == True]
        bear = d[d[col] == False]
        item = {
            "bull": summarize_qf_group(bull),
            "bear": summarize_qf_group(bear),
            "month_block_bootstrap": month_block_bootstrap_diff(qf, col, years),
        }
        if len(bull) and len(bear):
            item["bull_minus_bear_excess10_pct_points"] = (
                item["bull"]["mean_excess10_pct"] - item["bear"]["mean_excess10_pct"]
            )
        out[name] = item
    return out


def gap_tertile_analysis(qf: pd.DataFrame) -> dict:
    discovery = qf[(qf["year"] >= 2024) & (qf["year"] <= 2025)].copy()
    holdout = qf[qf["year"] == 2026].copy()
    out = {}
    for name in INDICATORS:
        col = f"{name}_gap"
        vals = discovery[col].dropna().astype(float)
        if len(vals) < 10:
            continue
        q1, q2 = np.quantile(vals, [1 / 3, 2 / 3])

        def classify(v):
            if not np.isfinite(v):
                return None
            if v <= q1:
                return "low"
            if v <= q2:
                return "mid"
            return "high"

        item = {"discovery_cutpoints": [float(q1), float(q2)]}
        for label, frame in [("discovery_2024_2025", discovery), ("holdout_2026", holdout)]:
            tmp = frame[[col, "excess_10", "ret_10", "symbol"]].copy()
            tmp["bucket"] = tmp[col].apply(classify)
            buckets = {}
            for b in ["low", "mid", "high"]:
                buckets[b] = summarize_qf_group(frame.loc[tmp.index[tmp["bucket"] == b]])
            low = buckets["low"].get("mean_excess10_pct")
            high = buckets["high"].get("mean_excess10_pct")
            buckets["high_minus_low_excess10_pct_points"] = (
                float(high - low) if high is not None and low is not None else None
            )
            item[label] = buckets
        out[name] = item
    return out


# ---------------------------------------------------------------- main

def main() -> None:
    spy_i = regular_1h(fetch_symbol("SPY", "1h", "729d"))
    spy_h4 = resample_closed_4h(spy_i, "SPY")

    frames: dict[str, pd.DataFrame] = {}
    for k, sym in enumerate(SYMBOLS, 1):
        print(f"[{k}/{len(SYMBOLS)}] {sym}", flush=True)
        df = prepare_symbol(sym, spy_h4)
        if df is not None:
            frames[sym] = add_probes(df)
    print("frames", len(frames), flush=True)

    # Study A.
    study_a = {}
    all_events = []
    all_random_summaries = []
    for name in INDICATORS:
        rows = []
        col = f"{name}_cross_up"
        for sym, df in frames.items():
            for i in np.flatnonzero(df[col].fillna(False).to_numpy()):
                if i < WARMUP:
                    continue
                rec = forward_record(sym, df, spy_h4, int(i), f"{name}_cross_up")
                if rec is not None:
                    rec["indicator"] = name
                    rows.append(rec)
        events = pd.DataFrame(rows)
        if not events.empty:
            all_events.append(events)
        comp, rdf = random_compare(events, frames, spy_h4, name)
        rdf["indicator"] = name
        all_random_summaries.append(rdf)

        yearly = {}
        for y, g in events.groupby("year"):
            yearly[str(int(y))] = summarize_forward(g)

        sym10 = []
        for sym, g in events.groupby("symbol"):
            v = g["excess_10"].dropna().astype(float)
            if len(v):
                sym10.append({
                    "symbol": sym, "n": int(len(v)),
                    "mean_excess10_pct": float(v.mean() * 100.0),
                })
        sym10 = sorted(sym10, key=lambda z: z["mean_excess10_pct"], reverse=True)

        study_a[name] = {
            "summary": summarize_forward(events),
            "matched_random": comp,
            "yearly": yearly,
            "symbol_concentration_10bar": sym10,
        }

    if all_events:
        pd.concat(all_events, ignore_index=True).to_csv(OUT / "standalone_cross_events.csv", index=False)
    if all_random_summaries:
        pd.concat(all_random_summaries, ignore_index=True).to_csv(OUT / "random_matched_summaries.csv", index=False)

    # Study B.
    qf_rows = []
    for sym, df in frames.items():
        for i in np.flatnonzero(df["qf_event"].fillna(False).to_numpy()):
            if i < WARMUP:
                continue
            rec = qf_record(sym, df, spy_h4, int(i))
            if rec is not None:
                qf_rows.append(rec)
    qf = pd.DataFrame(qf_rows)
    qf.to_csv(OUT / "qf_probe_features.csv", index=False)

    study_b = {
        "qf_n": int(len(qf)),
        "binary_state_discovery_2024_2025": binary_state_analysis(qf, (2024, 2025)),
        "binary_state_holdout_2026": binary_state_analysis(qf, (2026, 2026)),
        "gap_tertiles": gap_tertile_analysis(qf),
    }

    payload = {
        "data_note": "30-symbol DST-safe 4H surrogate; 2024-2025 discovery, 2026 holdout; 215-bar warmup; not canonical 131-symbol PIT",
        "definitions": {
            "DEMA": "double EMA 20/40: 2*EMA(n)-EMA(EMA(n))",
            "TEMA": "triple EMA 20/40: 3*EMA-3*EMA2+EMA3",
            "ALMA": "Arnaud Legoux MA 20/40, offset=0.85, sigma=6, standard m=offset*(n-1), s=n/sigma",
            "VIDYA": "Chande VIDYA 20/40, alpha=2/(n+1)*|CMO_n|/100, CMO length=line length",
            "FRAMA": "Ehlers FRAMA 20/40 on median price (H+L)/2, half-window fractal dimension, alpha=exp(-4.6*(D-1)) clipped [0.01,1]",
            "KAMA": "frozen benchmark, Kaufman adaptive MA 20/40, fast=2 slow=30, ER length=line length (identical to Tournament I)",
        },
        "study_a": study_a,
        "study_b": study_b,
    }
    (OUT / "results.json").write_text(json.dumps(payload, indent=2))
    print("TREND_PROBE_II_START")
    print(json.dumps(payload, indent=2))
    print("TREND_PROBE_II_END")


if __name__ == "__main__":
    main()
