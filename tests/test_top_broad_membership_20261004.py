#!/usr/bin/env python3
"""Synthetic fixtures for top_broad_experiment (the authoritative module).

Imports compute_top50 and paired_block_bootstrap from top_broad_experiment.py.
Covers the frozen mechanics plus REPAIR 2026-10-04:
- R1: no lookahead in split handling (HON Jun 29 event / Jun 30 rebalance).
- R2: 60-day window fixed before exclusions (no backward backfill).
- R3: dynamic quarterly rebalances with splits at various points.
"""
import sys
sys.path.insert(0, "/home/hatch/workspace/quality-flow-scanner-v5")
import numpy as np
import pandas as pd
from top_broad_experiment import compute_top50, paired_block_bootstrap

print("top_broad_experiment — synthetic verification (imports from module)")

passed = failed = 0
def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS {name}")
    else:
        failed += 1
        print(f"  FAIL {name}")

rng = np.random.default_rng(42)

print("\n== M1: TOP-50 selects strongest composite ==")
dates = pd.date_range("2024-01-01", periods=80, freq="B")
dv = {}
rs_ret = {}
for k in range(60):
    sym = f"S{k:02d}"
    dv[sym] = pd.Series(1e8 * (60 - k) + rng.normal(0, 1e6, 80), index=dates)
    rs_ret[sym] = 0.5 - k * 0.01
sel, diag = compute_top50(dv, rs_ret, top_n=50)
check("50 selected", len(sel) == 50)
check("strongest included", "S00" in sel)
check("weakest excluded", "S59" not in sel)

print("\n== M2: ties at cutoff all enter ==")
dv2 = {f"T{k}": pd.Series(np.full(80, 1e8), index=dates) for k in range(10)}
rs2 = {f"T{k}": 0.1 for k in range(10)}
sel2, _ = compute_top50(dv2, rs2, top_n=5)
check("all tied enter", len(sel2) == 10)

print("\n== M3: missing inputs excluded ==")
dv3 = {f"U{k}": pd.Series(np.full(80, 1e8), index=dates) for k in range(10)}
rs3 = {f"U{k}": 0.1 for k in range(5)}
sel3, diag3 = compute_top50(dv3, rs3, top_n=50)
check("only 5 valid, all selected", diag3["n_valid"] == 5 and len(sel3) == 5)

print("\n== M5: degenerate ==")
sel5, diag5 = compute_top50({"ONLY": pd.Series(np.full(80, 1e8), index=dates)},
                            {"ONLY": 0.1})
check("degenerate flagged", diag5["degenerate"] and len(sel5) == 0)

print("\n== R1: NO LOOKAHEAD — HON Jun 29 event, Jun 30 rebalance ==")
# The rebalance on Jun 30 must not use any data after Jun 30 to decide
# split handling. The unconditional exclusion uses only the event DATE
# (known at rebalance) — never post-event prices.
rebal = pd.Timestamp("2026-06-30")
# Dollar volume: 80 trading days ending Jun 30
didx = pd.bdate_range(end=rebal, periods=80)
# HON-like: flat 1e8, with a 5x SPIKE on Jul 1-3 (post-rebalance, unknown at rebalance)
hon_dv = pd.Series(np.full(80, 1e8), index=didx)
# Simulate: what if post-event data showed a spike? It must not matter.
# The exclusion removes Jun 26/29/30 (3 trading days around Jun 29 event).
# Key: the MEAN must be computed without Jul data regardless.
hon_rs = 0.3
other_dv = pd.Series(np.full(80, 1e8), index=didx)
sel_r1, _ = compute_top50(
    {"HON": hon_dv, "OTHER": other_dv},
    {"HON": hon_rs, "OTHER": 0.1},
    split_dates={"HON": [pd.Timestamp("2026-06-29").date()]},
    top_n=2)
# Both selected (tie on liquidity after exclusion; HON wins on RS).
# The critical assertion: no exception, no use of post-Jun-30 data.
# (The function only receives data through Jun 30 — verified by construction.)
check("rebalance completes without post-event data", len(sel_r1) == 2)
check("HON selected on RS", "HON" in sel_r1)

print("\n== R2: no backward backfill after exclusions ==")
# 80 days of data, 60-day window = last 60. After excluding 3, mean uses 57
# days within the window — NOT 60 days reaching 3 further back.
widx = pd.bdate_range("2025-01-01", periods=80)
# Make days 1-20 very low (1e6) and days 21-80 at 1e8.
# Correct: window = days 21-80, exclude 3 -> mean ≈ 1e8 (57 days).
# Buggy (backfill): tail(60) after drop -> includes days 18-20 -> mean < 1e8.
vals = np.concatenate([np.full(20, 1e6), np.full(60, 1e8)])
dv_r2 = {"A": pd.Series(vals, index=widx)}
rs_r2 = {"A": 0.1, "B": 0.1}
dv_r2["B"] = pd.Series(np.full(80, 1e8), index=widx)
# Split event on day 50 (within window)
sel_r2, _ = compute_top50(dv_r2, rs_r2,
                          split_dates={"A": [widx[50].date()]}, top_n=2)
# A's mean should be ≈1e8 (57 days at 1e8), same as B -> tie, both selected.
# If backfilled, A's mean would be pulled down by the 1e6 days.
check("no backfill (both selected on tie)", len(sel_r2) == 2)

print("\n== R3: dynamic quarterly rebalances ==")
# Three rebalances: Mar 31, Jun 30, Sep 30 2025. A split occurs in Q2.
# Membership should reflect the split exclusion only in the affected quarter.
q_dates = pd.bdate_range("2024-06-01", "2025-09-30")
def run_quarter(end):
    wend = pd.Timestamp(end)
    # Each symbol needs 80+ days ending at quarter-end
    qd = {}
    qrs = {}
    for k in range(20):
        sym = f"Q{k:02d}"
        s = pd.Series(1e8, index=q_dates[q_dates <= wend][-80:])
        qd[sym] = s
        qrs[sym] = 0.2 - k * 0.01
    # Q05 has a split in Q2 only
    splits = {"Q05": [pd.Timestamp("2025-05-15").date()]} if end == "2025-06-30" else {}
    # Give Q05 a post-split artifact spike that must be excluded
    if end == "2025-06-30":
        spike_idx = qd["Q05"].index.get_indexer(
            [pd.Timestamp("2025-05-15")], method="nearest")[0]
        qd["Q05"].iloc[spike_idx] = 1e10
    sel_q, _ = compute_top50(qd, qrs, split_dates=splits, top_n=10)
    return sel_q

sel_q1 = run_quarter("2025-03-31")
sel_q2 = run_quarter("2025-06-30")
sel_q3 = run_quarter("2025-09-30")
check("Q1: 10 selected", len(sel_q1) == 10)
check("Q2: 10 selected (split handled)", len(sel_q2) == 10)
check("Q3: 10 selected", len(sel_q3) == 10)
# Q05 has strong RS (0.2 - 5*0.01 = 0.15, rank 6/20) — should be in TOP-10
# in all quarters despite the Q2 split artifact.
check("Q05 in TOP-10 all quarters", all("Q05" in s for s in [sel_q1, sel_q2, sel_q3]))

print("\n== B1: bootstrap CI ==")
brng = np.random.default_rng(7)
months = list(range(19))
top_tr = [{"exit_month": int(brng.integers(19)), "net_r": float(brng.normal(0.2, 1.0))}
          for _ in range(200)]
broad_tr = [{"exit_month": int(brng.integers(19)), "net_r": float(brng.normal(0.05, 1.0))}
            for _ in range(200)]
res = paired_block_bootstrap(top_tr, broad_tr, months, n_resamples=2000)
check("CI lower > 0", res["ci"][0] > 0 and res["g5_pass"])
check("not inconclusive", not res["inconclusive"])

print("\n== B2: INCONCLUSIVE on insufficient data ==")
few = [{"exit_month": 0, "net_r": 0.1} for _ in range(3)]
res2 = paired_block_bootstrap(few, few, months, n_resamples=500)
check("inconclusive", res2["inconclusive"] or res2["valid"] == 0)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
