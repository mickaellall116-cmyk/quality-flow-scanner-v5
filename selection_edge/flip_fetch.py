#!/usr/bin/env python3
"""Fetch missing watchlist ticker-timeframes for the flip test using the
EXISTING builders (no new pipeline). Writes NEW cache files only; never
touches existing caches or frozen files."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/workspace/quality-flow-scanner-v5"))
sys.path.insert(0, os.path.expanduser("~/workspace/quality-flow-scanner-v5/pine_1h"))

import pandas as pd
import masterscanner_api as m
from fetch_1h import fetch as fetch_1h

BASE = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
H1C = os.path.join(BASE, "pine_1h", "cache")
BC = os.path.join(BASE, "backtest_cache")

NEED_H1 = ["QQQ", "ANET", "ONDS", "DRAM", "SPCX", "BBAI"]
NEED_H4 = ["ANET", "RKLB", "ONDS", "DRAM", "SPCX", "BBAI", "NIO", "HOOD"]
NEED_D1 = ["QQQ", "ANET", "RKLB", "ONDS", "DRAM", "SPCX", "BBAI", "NIO", "HOOD"]

log = {}

for sym in NEED_H1:
    path = os.path.join(H1C, f"h1_{sym}.pkl")
    if os.path.exists(path):
        log[f"h1_{sym}"] = "already cached"; continue
    try:
        df, err = fetch_1h(sym)
        if err or df is None or df.empty:
            log[f"h1_{sym}"] = f"FAIL {err}"; print(f"h1 {sym}: FAIL {err}", flush=True)
        elif "Volume" not in df.columns or df["Volume"].isna().all():
            log[f"h1_{sym}"] = "FAIL no_volume"; print(f"h1 {sym}: FAIL no_volume", flush=True)
        else:
            df.to_pickle(path)
            log[f"h1_{sym}"] = f"ok {len(df)} {df.index[0]} -> {df.index[-1]}"
            print(f"h1 {sym}: ok {len(df)} bars", flush=True)
    except Exception as e:
        log[f"h1_{sym}"] = f"FAIL {type(e).__name__}: {e}"; print(f"h1 {sym}: FAIL {e}", flush=True)
    time.sleep(0.5)

for sym in NEED_H4:
    path = os.path.join(BC, f"h4_{sym}.pkl")
    if os.path.exists(path):
        log[f"h4_{sym}"] = "already cached"; continue
    try:
        df = m.download_data(sym, "4h", "2y")
        if df is None or df.empty or len(df) < 100:
            log[f"h4_{sym}"] = "FAIL empty/short"; print(f"h4 {sym}: FAIL empty/short", flush=True)
        elif "Volume" not in df.columns or df["Volume"].isna().all():
            log[f"h4_{sym}"] = "FAIL no_volume"; print(f"h4 {sym}: FAIL no_volume", flush=True)
        else:
            df.to_pickle(path)
            log[f"h4_{sym}"] = f"ok {len(df)} {df.index[0]} -> {df.index[-1]}"
            print(f"h4 {sym}: ok {len(df)} bars", flush=True)
    except Exception as e:
        log[f"h4_{sym}"] = f"FAIL {type(e).__name__}: {e}"; print(f"h4 {sym}: FAIL {e}", flush=True)
    time.sleep(0.5)

for sym in NEED_D1:
    path = os.path.join(BC, f"d1_{sym}.pkl")
    if os.path.exists(path):
        log[f"d1_{sym}"] = "already cached"; continue
    try:
        df = m.download_confirmation_data(sym, "1d", "5y")
        if df is None or df.empty or len(df) < 100:
            log[f"d1_{sym}"] = "FAIL empty/short"; print(f"d1 {sym}: FAIL empty/short", flush=True)
        elif "Volume" not in df.columns or df["Volume"].isna().all():
            log[f"d1_{sym}"] = "FAIL no_volume"; print(f"d1 {sym}: FAIL no_volume", flush=True)
        else:
            df.to_pickle(path)
            log[f"d1_{sym}"] = f"ok {len(df)} {df.index[0]} -> {df.index[-1]}"
            print(f"d1 {sym}: ok {len(df)} bars", flush=True)
    except Exception as e:
        log[f"d1_{sym}"] = f"FAIL {type(e).__name__}: {e}"; print(f"d1 {sym}: FAIL {e}", flush=True)
    time.sleep(0.5)

with open(os.path.join(BASE, "selection_edge", "flip_fetch_log.json"), "w") as f:
    json.dump(log, f, indent=1, default=str)
print("DONE")
print(json.dumps(log, indent=1, default=str))
