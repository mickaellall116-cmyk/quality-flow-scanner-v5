#!/usr/bin/env python3
"""TOP-vs-BROAD run harness (System 1) — PRE-AUTHORIZED performance run.

Mike pre-authorized the performance run once the automated preflight checks
pass (Bridge #1, 2026-10-04). No further approval needed unless a check fails.

Pipeline:
  PREFLIGHT (must all pass):
    P1. Verify SHA-256 of all 225 Yahoo 1H input files vs frozen manifest.
    P2. Verify module hashes (experiment, trade engine, portfolio).
    P3. Dry membership: quarterly TOP-50 on synthetic data, transitions sane.
  PERFORMANCE (runs only if preflight passes):
    1. Build 4H bars (corrected session-anchored) for 218 BROAD symbols.
    2. Compute quarterly TOP-50 membership (7 rebalances).
    3. Generate trades (gen_candidates) + rs features (compute_features).
    4. BROAD leg: simulate_stack on all trades.
    5. TOP leg: simulate_stack on trades filtered by quarterly membership
       (entry-time gating; held positions follow frozen exits).
    6. Gates G0–G5, paired bootstrap. Results to JSON. NO holdout. NO paper.

Usage:
  python3 top_broad_run.py preflight   # fast checks only
  python3 top_broad_run.py run         # preflight + performance (authorized)
"""
import sys, os, json, hashlib
import pandas as pd
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "pine_ranking"))

import top_broad_experiment as tbe

# Frozen pins
MANIFEST = os.path.join(HERE, "research_notes", "yahoo_1h_input_manifest_20261004.json")
MODULE_HASHES = {
    "top_broad_experiment.py": "a9cbc5cf4debdda7",
    # Note: top_broad_run.py does not pin itself (self-referential).
    # It is verified by its git commit, not by content hash.
    "top_broad_performance.py": "526f784f0646d5e2",  # updated 2026-10-04: spy=None bugfix (unused var)
    "pine_backtest.py": "447a9a13bb2ec7ab",
    "pine_stack/pine_stack.py": "839e4800624de253",
}
STUDY_START = pd.Timestamp("2025-03-17", tz="America/New_York")
STUDY_END = pd.Timestamp("2026-09-14", tz="America/New_York")
REBALANCES = ["2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30",
              "2025-12-31", "2026-03-31", "2026-06-30"]
EXCLUDED = {"BMNR", "CRWV", "GLXY", "NBIS", "XYZ", "CLSK", "SBET"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def preflight():
    """P1–P3. Returns (ok, messages)."""
    msgs = []
    ok = True

    # P1: input hashes
    try:
        manifest = json.load(open(MANIFEST))
    except FileNotFoundError:
        return False, ["P1 FAIL: manifest not found"]
    bad = []
    for sym, meta in manifest["files"].items():
        # Raw 1H lives in the inventory scratch dir (frozen inputs)
        for cand in [f"data_inventory_scratch_20261004/h1_raw/h1_{sym}.pkl",
                     f"pine_1h/cache/h1_{sym}.pkl"]:
            p = os.path.join(HERE, cand)
            if os.path.exists(p):
                if sha256_file(p) != meta["sha256"]:
                    bad.append(sym)
                break
        else:
            bad.append(sym + " (missing)")
    if bad:
        ok = False
        msgs.append(f"P1 FAIL: {len(bad)} hash mismatches: {bad[:5]}")
    else:
        msgs.append(f"P1 PASS: {len(manifest['files'])} input hashes verified")

    # P2: module hashes — STRICT: any mismatch FAILS (no notes, no warnings)
    for mod, pin_prefix in MODULE_HASHES.items():
        if pin_prefix is None:
            continue
        p = os.path.join(HERE, mod)
        if not os.path.exists(p):
            ok = False
            msgs.append(f"P2 FAIL: {mod} missing")
            continue
        actual = sha256_file(p)[:16]
        if actual != pin_prefix:
            ok = False
            msgs.append(f"P2 FAIL: {mod} hash {actual} != pinned {pin_prefix}")
        else:
            msgs.append(f"P2 PASS: {mod} matches pin")
    # top_broad_experiment.py: verify it imports and fixtures pass
    try:
        import subprocess
        r = subprocess.run([sys.executable,
                            os.path.join(HERE, "tests",
                                         "test_top_broad_membership_20261004.py")],
                           capture_output=True, text=True, timeout=300)
        if r.returncode == 0 and "0 failed" in r.stdout:
            msgs.append("P2 PASS: experiment fixtures 16/16")
        else:
            ok = False
            msgs.append(f"P2 FAIL: fixtures: {r.stdout[-500:]}")
    except Exception as e:
        ok = False
        msgs.append(f"P2 FAIL: fixture run error: {e}")

    # P3: dry membership transitions (synthetic, 3 quarters)
    try:
        dq = pd.bdate_range("2024-01-01", "2025-09-30")
        members = {}
        for q_end in ["2025-03-31", "2025-06-30", "2025-09-30"]:
            qd, qrs = {}, {}
            for k in range(20):
                sym = f"D{k:02d}"
                s = pd.Series(1e8, index=dq[dq <= q_end][-80:])
                qd[sym] = s
                # Rotate leadership: D00 strongest in Q1, D19 in Q2, D10 in Q3
                qrs[sym] = {("2025-03-31", 0): 0.5 - k * 0.01,
                            ("2025-06-30", 0): k * 0.01,
                            ("2025-09-30", 0): -abs(k - 10) * 0.01}[(q_end, 0)]
            sel, _ = tbe.compute_top50(qd, qrs, top_n=10)
            members[q_end] = set(sel)
        # Transitions must differ (leadership rotated) and be non-empty
        if (len(members["2025-03-31"]) == 10 and len(members["2025-06-30"]) == 10
                and members["2025-03-31"] != members["2025-06-30"]):
            msgs.append("P3 PASS: quarterly transitions enforced and varying")
        else:
            ok = False
            msgs.append("P3 FAIL: membership transitions not varying")
    except Exception as e:
        ok = False
        msgs.append(f"P3 FAIL: {e}")

    # P1b: daily ranking manifest hashes
    try:
        dman = json.load(open(os.path.join(
            HERE, "research_notes", "daily_ranking_manifest_20261004.json")))
    except FileNotFoundError:
        return False, ["P1b FAIL: daily manifest not found"]
    dbad = []
    for sym, meta in dman["files"].items():
        p = os.path.join(HERE, "daily_ranking_frozen_20261004", f"d1_{sym}.pkl")
        if not os.path.exists(p):
            dbad.append(sym + " (missing)")
        elif sha256_file(p) != meta["sha256"]:
            dbad.append(sym)
    if dbad:
        ok = False
        msgs.append(f"P1b FAIL: {len(dbad)} daily hash mismatches: {dbad[:5]}")
    else:
        msgs.append(f"P1b PASS: {len(dman['files'])} daily input hashes verified")

    return ok, msgs


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "preflight"
    ok, msgs = preflight()
    for m in msgs:
        print(m, flush=True)
    if not ok:
        print("PREFLIGHT FAILED — performance run blocked.", flush=True)
        sys.exit(1)
    print("PREFLIGHT PASS.", flush=True)
    if mode == "preflight":
        print("(dry run — performance not executed)", flush=True)
        return
    if mode == "run":
        print("Pre-authorized performance run starting...", flush=True)
        from top_broad_performance import run_performance
        run_performance()
    else:
        print(f"Unknown mode: {mode}", flush=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
