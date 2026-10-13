#!/usr/bin/env python3
"""TimesFM spike — run exactly as pre-registered in
research_notes/timesfm_spike_prereg_20261012.md.

Design (frozen):
- 14 watchlist tickers, daily closes from Yahoo via yfinance. NO Tiingo.
- 1-trading-day-ahead close forecast; context = prior 256 daily closes.
- Origins: every trading day in 2026-04-01..2026-10-09 (with a next trading
  day available in the series to score against).
- Model: TimesFM 2.0 500M (google/timesfm-2.0-500m-pytorch), CPU, point fcst.
- Baselines: no-change; 20-day drift.
- Metrics: RMSE/MAE per ticker + pooled; directional accuracy; tradable check
  (long when TimesFM forecast return > +0.2%, 1 day, 25 bps round-trip).
- PASS gate (all three): pooled RMSE >=5% below no-change RMSE; directional
  accuracy >= 53%; tradable mean per-trade return > 0 after costs.

Documented exception (parent instruction): SPCX (IPO Jun 2026) can never have
256 prior closes inside the window. It is included with the context it has
(min 30 closes) once available, and every SPCX record is flagged
context_short=True so the deviation is visible in the raw output.
"""
import json
import math
import os
import sys
import time
from datetime import date

import numpy as np
import pandas as pd

TICKERS = ["QQQ", "SMCI", "PLTR", "ANET", "SOFI", "RKLB", "ONDS",
           "DRAM", "SPCX", "ASTX", "BBAI", "NIO", "HOOD", "AMD"]
WINDOW_START = date(2026, 4, 1)
WINDOW_END = date(2026, 10, 9)
CONTEXT = 256
MIN_CONTEXT_SHORT = 30          # SPCX-only exception floor
SHORT_CONTEXT_TICKERS = {"SPCX"}
COST_RT = 0.0025                # 25 bps round trip
TRADE_THRESHOLD = 0.002         # +0.2% forecast return
CHECKPOINT = "google/timesfm-2.0-500m-pytorch"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "bars_cache.json")
OUT_JSON = os.path.join(HERE, "timesfm_spike_raw_results.json")
CKPT_FILE = os.path.join(HERE, "hf_cache", "hub",
                         "models--google--timesfm-2.0-500m-pytorch", "snapshots")
# Loader: the pip `timesfm` packages installable in this environment
# (2.0.2 / 3.0.2) no longer ship a loader for the TimesFM 2.0 checkpoint;
# the 2.0-capable loader is the official google-research/timesfm repo
# source at tag v1.2.6 (src/timesfm, TimesFmTorch). Checkpoint unchanged.
REPO_SRC = os.path.join(HERE, "timesfm_repo_126", "src")


def find_ckpt():
    import glob
    hits = glob.glob(os.path.join(CKPT_FILE, "*", "torch_model.ckpt"))
    if not hits:
        raise FileNotFoundError("torch_model.ckpt not downloaded yet")
    return hits[0]


def fetch_bars():
    """Daily closes via yfinance; cached to disk so the run is reproducible."""
    if os.path.exists(CACHE):
        with open(CACHE) as f:
            raw = json.load(f)
        return {t: [(d, float(c)) for d, c in rows] for t, rows in raw.items()}
    import yfinance as yf
    out = {}
    for t in TICKERS:
        df = yf.download(t, start="2024-06-01", end="2026-10-14",
                         auto_adjust=False, progress=False)
        closes = df["Close"]
        if isinstance(closes, pd.DataFrame):   # yfinance multi-index quirk
            closes = closes.iloc[:, 0]
        rows = [(idx.strftime("%Y-%m-%d"), float(v))
                for idx, v in closes.dropna().items()]
        out[t] = rows
        print(f"  fetched {t}: {len(rows)} bars "
              f"{rows[0][0]}..{rows[-1][0]}", flush=True)
    with open(CACHE, "w") as f:
        json.dump(out, f)
    return out


def build_origins(ticker, rows):
    """Origins for one ticker: window dates with a next trading day present
    and a full 256-close context (SPCX exception: >=30 closes, flagged)."""
    dates = [r[0] for r in rows]
    closes = np.array([r[1] for r in rows], dtype=np.float64)
    origins = []
    for i, d in enumerate(dates):
        dd = date.fromisoformat(d)
        if dd < WINDOW_START or dd > WINDOW_END:
            continue
        if i + 1 >= len(dates):
            continue
        n_ctx = i + 1
        if n_ctx >= CONTEXT:
            ctx = closes[i + 1 - CONTEXT: i + 1]
            short = False
        elif ticker in SHORT_CONTEXT_TICKERS and n_ctx >= MIN_CONTEXT_SHORT:
            ctx = closes[: i + 1]
            short = True
        else:
            continue                      # prereg context unavailable
        origins.append({"idx": i, "ctx": ctx, "short": short})
    return dates, closes, origins


def main():
    t0 = time.time()
    print("Fetching bars (yfinance, Yahoo only)...", flush=True)
    bars = fetch_bars()

    import torch
    sys.path.insert(0, REPO_SRC)
    import timesfm
    torch.set_num_threads(os.cpu_count() or 2)
    ckpt_path = find_ckpt()
    print(f"Loading {CHECKPOINT} from {ckpt_path} ...", flush=True)
    t_load = time.time()
    tfm = timesfm.TimesFm(
        hparams=timesfm.TimesFmHparams(
            backend="cpu",
            per_core_batch_size=32,
            horizon_len=128,
            num_layers=50,
            use_positional_embedding=False,
            context_len=CONTEXT,
        ),
        checkpoint=timesfm.TimesFmCheckpoint(path=ckpt_path),
    )
    print(f"Model loaded in {time.time() - t_load:.1f}s", flush=True)

    records = []
    per_ticker_counts = {}
    t_fc = time.time()
    for ticker in TICKERS:
        rows = bars[ticker]
        dates, closes, origins = build_origins(ticker, rows)
        per_ticker_counts[ticker] = len(origins)
        if not origins:
            print(f"  {ticker}: NO valid origins", flush=True)
            continue
        inputs = [o["ctx"].tolist() for o in origins]
        point, _q = tfm.forecast(inputs, freq=[0] * len(inputs))
        point = np.asarray(point, dtype=np.float64).reshape(len(origins), -1)[:, 0]
        for o, fc in zip(origins, point):
            i = o["idx"]
            today = float(closes[i])
            actual = float(closes[i + 1])
            # drift baseline: mean daily return of prior 20 trading days
            if i >= 20:
                rets = closes[i - 19: i + 1] / closes[i - 20: i] - 1.0
                drift_fc = today * (1.0 + float(np.mean(rets)))
            else:
                drift_fc = float("nan")
            records.append({
                "ticker": ticker,
                "origin_date": dates[i],
                "actual_date": dates[i + 1],
                "context_len": int(len(o["ctx"])),
                "context_short": bool(o["short"]),
                "today_close": today,
                "actual_close": actual,
                "timesfm_fc": float(fc),
                "nochange_fc": today,
                "drift_fc": drift_fc,
            })
        print(f"  {ticker}: {len(origins)} origins forecast", flush=True)
    fc_secs = time.time() - t_fc

    # ---- metrics ----
    def rmse(errs):
        return float(np.sqrt(np.mean(np.square(errs)))) if errs else float("nan")

    def mae(errs):
        return float(np.mean(np.abs(errs))) if errs else float("nan")

    def metrics(recs):
        e_t = [r["timesfm_fc"] - r["actual_close"] for r in recs]
        e_n = [r["nochange_fc"] - r["actual_close"] for r in recs]
        e_d = [r["drift_fc"] - r["actual_close"] for r in recs
               if not math.isnan(r["drift_fc"])]
        # directional accuracy (exclude zero actual moves)
        def diracc(key):
            ok = tot = 0
            for r in recs:
                move = r["actual_close"] - r["today_close"]
                if move == 0:
                    continue
                tot += 1
                if np.sign(r[key] - r["today_close"]) == np.sign(move):
                    ok += 1
            return (ok / tot if tot else float("nan")), tot
        da_t, da_n_t = diracc("timesfm_fc")
        da_d, _ = diracc("drift_fc")
        return {
            "n": len(recs),
            "timesfm_rmse": rmse(e_t), "timesfm_mae": mae(e_t),
            "nochange_rmse": rmse(e_n), "nochange_mae": mae(e_n),
            "drift_rmse": rmse(e_d), "drift_mae": mae(e_d),
            "timesfm_dir_acc": da_t, "dir_n": da_n_t,
            "drift_dir_acc": da_d,
        }

    pooled = metrics(records)
    per_ticker = {}
    for ticker in TICKERS:
        recs = [r for r in records if r["ticker"] == ticker]
        if recs:
            per_ticker[ticker] = metrics(recs)

    # tradable check (pooled, TimesFM)
    trades = []
    for r in records:
        fc_ret = r["timesfm_fc"] / r["today_close"] - 1.0
        if fc_ret > TRADE_THRESHOLD:
            trades.append(r["actual_close"] / r["today_close"] - 1.0 - COST_RT)
    tradable = {
        "n_trades": len(trades),
        "mean_return_after_costs": float(np.mean(trades)) if trades else None,
        "total_return_sum": float(np.sum(trades)) if trades else 0.0,
        "win_rate": float(np.mean([1.0 if x > 0 else 0.0 for x in trades]))
        if trades else None,
    }

    # ---- PASS gate ----
    rmse_improvement = (1.0 - pooled["timesfm_rmse"] / pooled["nochange_rmse"]
                        if pooled["nochange_rmse"] else float("nan"))
    gate = {
        "leg1_rmse_5pct_better": bool(rmse_improvement >= 0.05),
        "leg1_rmse_improvement_frac": float(rmse_improvement),
        "leg2_dir_acc_53pct": bool(pooled["timesfm_dir_acc"] >= 0.53),
        "leg2_dir_acc": float(pooled["timesfm_dir_acc"]),
        "leg3_tradable_positive": bool(
            tradable["mean_return_after_costs"] is not None
            and tradable["mean_return_after_costs"] > 0),
        "leg3_mean_return_after_costs": tradable["mean_return_after_costs"],
    }
    gate["PASS"] = bool(gate["leg1_rmse_5pct_better"]
                        and gate["leg2_dir_acc_53pct"]
                        and gate["leg3_tradable_positive"])

    import hashlib
    import importlib.metadata as md
    env = {}
    for pkg in ("torch", "yfinance", "numpy", "pandas"):
        try:
            env[pkg] = md.version(pkg)
        except Exception:
            env[pkg] = "unknown"
    env["checkpoint"] = CHECKPOINT
    env["checkpoint_file"] = ckpt_path
    env["checkpoint_file_bytes"] = os.path.getsize(ckpt_path)
    h = hashlib.sha256()
    with open(ckpt_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    env["checkpoint_file_sha256"] = h.hexdigest()
    env["timesfm_loader"] = ("google-research/timesfm repo tag v1.2.6 "
                             "(commit e77303c5513c84aa8b32639851c3f7f92f59645e, "
                             "src/timesfm TimesFmTorch); pip timesfm "
                             "2.0.2/3.0.2 ship no TimesFM 2.0 loader")
    env["point_forecast_mode"] = "median (TimesFmHparams default)"
    env["python"] = sys.version.split()[0]

    out = {
        "environment": env,
        "origins_per_ticker": per_ticker_counts,
        "pooled": pooled,
        "per_ticker": per_ticker,
        "tradable": tradable,
        "gate": gate,
        "runtime_seconds": {"forecast": fc_secs, "total": time.time() - t0},
        "records": records,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({"pooled": pooled, "tradable": tradable, "gate": gate},
                     indent=1), flush=True)
    print(f"Wrote {OUT_JSON}", flush=True)


if __name__ == "__main__":
    main()
