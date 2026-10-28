#!/usr/bin/env python3
"""O4 — variance-only estimation of the H-EXIT-1 / H-EXIT-3 paired SDs.

Executes exactly the pinned procedure:
  research_notes/prereg_g5_freeze_package_20261026/O4_PROCEDURE.md
with the cost basis substituted by the addendum pin:
  research_notes/prereg_g5_freeze_package_20261026_addendum/O4_BASIS_PIN.md
  (Stage-1 FLAT views of the frozen C1 config, 25 bps gating view;
   the S8 per-fill convention is NOT used for O4).

Variance-only discipline (procedure S4): the only statistics that leave
this run are, per endpoint, {n, s, DE, n_eff}, plus the input pins and
the exclusion counts. No mean difference, no arm mean, no per-arm SD,
no interval, no per-event value is printed, stored, or transmitted.
Per-event legs exist only in memory.

Inputs (all pinned, all verified before any computation):
  - frozen simulator (post-erratum) pine_backtest.py  sha256 262ec034..
  - frozen C1 config canonical pin                    87b8285a..
    (sha256 of json.dumps(EXPERIMENT_CONFIG, sort_keys=True,
     separators=(",", ":")) parsed from the committed -13 driver)
  - -13 DEV ledger                                    sha256 267e794c..
  - EXP-14-lineage frozen cohort (311 events, corr2)  sha256 35690b80..
  - P7b every-bar inventory (private archive)         sha256 a6bbd19a..
  - adopted session table (751)                       sha256 00c5555c..
  - scanner_rules.py resample (via -13 stage pins)    sha256 62aa743a..
  - DEV bar bytes: the -13 stage archive clone namespaces
    td_pilot_20261023 + td_capture_equity39_continue_20261023,
    verified against their committed SHA256SUMS (the -13 phase-0 check).

Data path: the executed -13 environment (~/workspace/qf_td13_stage)
supplies load_session_table / phase2 (admission) / phase4 (session-
anchored 4H resample). Indicators and signals come from the PINNED
simulator module loaded from the extracted origin/main blob (its code
is identical to the -13 engine except the module docstring, verified
by diff at preparation time).

Stop conditions (procedure S6): any pin failure, any data-path
verification failure, or a common paired set below the 100 floor
(report n only) aborts the run; the output file then records the STOP.

Environment: run with the calendar libraries used by the program's
prior -13/-17 stage runs on PYTHONPATH (scanner_rules requires
pandas_market_calendars):
  PYTHONPATH=~/workspace/qf_td17_stage/pylibs python3 o4_run.py
"""
import ast
import hashlib
import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
STAGE13 = os.path.expanduser("~/workspace/qf_td13_stage")
ARCHIVE = os.path.expanduser(
    "~/workspace/qf_feed_measure_stage/archive_clone")
INVENTORY = os.path.join(
    ARCHIVE, "research_inventory", "p7b_20261025", "p7b_inventory.jsonl")
LEDGER_REPO_PATH = ("research_notes/equity43_dev_order_censor_20261023_13"
                    "/trade_ledger.json")
DRIVER_REPO_PATH = ("research_notes/equity43_dev_order_censor_20261023_13"
                    "/run_study13.py")

PIN_SIMULATOR = "262ec0340161e72893ca9c5edd9d1fe2cb046fd30004d727b3893d52bd4d3f2a"
PIN_CONFIG = "87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706"
PIN_LEDGER = "267e794c284a409d7d9b6d8e1056c452976b59746062e9e6e18c5664b74c003b"
PIN_COHORT = "35690b806e51eefe388fadf35b04baf5ed4c52f8e30ac193a38cf88246332824"
PIN_INVENTORY = "a6bbd19a702120cafd48cd01ee4c8ff59b838a8bd6439822415d6c18278ef02f"
PIN_SESSION_TABLE = "00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f"
PIN_SCANNER_RULES = "62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c"
PIN_DRIVER = "4962e30d8b42124ebc317aab647351521d107b600c01a42905fce4c41ce4b22b"

COST_25BPS = 0.0025          # Stage-1 flat view, fraction of entry price
FLOOR_N = 100                # procedure S6 / S1 validity floor
BOOT_REPS = 10000            # [C10]
BOOT_BLOCK_SESSIONS = 20     # [C10]
# [C10] seed: first 8 bytes, big-endian, of the frozen preregistration's
# SHA-256 (PREREG_V10.md sha256 29a0477a13e52ff4467193f69df7..)
BOOT_SEED = int.from_bytes(bytes.fromhex("29a0477a13e52ff4"), "big")

# Frozen simulator constants (mirrored from the pinned engine).
SL_ATR, TP_ATR, TRAIL_ATR = 1.5, 2.0, 2.5
E1_SLIP_ATR = 0.05           # [C15] declared E1 stop-slippage assumption

vlog = {"pins": {}, "data_path": {}, "fidelity": {}, "counts": {}}
STOP = []


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    with open(p, "rb") as f:
        return sha256_bytes(f.read())


def git_show(path):
    import subprocess
    out = subprocess.run(["git", "-C", REPO, "show",
                          f"origin/main:{path}"], capture_output=True)
    if out.returncode != 0:
        raise RuntimeError(f"git show failed for {path}: "
                           f"{out.stderr.decode()[:200]}")
    return out.stdout


def check_pin(name, got, want):
    ok = got == want
    vlog["pins"][name] = {"sha256": got, "expected": want, "ok": ok}
    if not ok:
        STOP.append(f"pin mismatch: {name}: {got} != {want}")
    return ok



def phase_a_pins():
    """Verify every pinned input. Returns the loaded artifacts, or None
    (with STOP populated) if any pin fails. Computes nothing."""
    sim_path = os.path.join(WORK, "pine_backtest_PINNED.py")
    check_pin("simulator_pine_backtest_post_erratum",
              sha256_file(sim_path), PIN_SIMULATOR)
    cohort_path = os.path.join(WORK, "exp14_frozen_cohort.json")
    check_pin("exp14_frozen_cohort_corr2", sha256_file(cohort_path),
              PIN_COHORT)
    check_pin("p7b_inventory", sha256_file(INVENTORY), PIN_INVENTORY)
    check_pin("session_table_751",
              sha256_file(os.path.join(STAGE13, "session_table.json")),
              PIN_SESSION_TABLE)
    check_pin("scanner_rules_resample",
              sha256_file(os.path.join(
                  STAGE13, "engine_successor", "scanner_rules.py")),
              PIN_SCANNER_RULES)
    check_pin("run_study13_stage_copy",
              sha256_file(os.path.join(STAGE13, "run_study13.py")),
              PIN_DRIVER)
    check_pin("run_study13_committed",
              sha256_bytes(git_show(DRIVER_REPO_PATH)), PIN_DRIVER)
    ledger_bytes = git_show(LEDGER_REPO_PATH)
    check_pin("dev_ledger_13", sha256_bytes(ledger_bytes), PIN_LEDGER)

    # C1 config canonical pin, recomputed from the committed driver.
    src = git_show(DRIVER_REPO_PATH).decode()
    cfg = None
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "EXPERIMENT_CONFIG"
                for t in node.targets):
            cfg = ast.literal_eval(node.value)
    if cfg is None:
        STOP.append("EXPERIMENT_CONFIG not found in committed driver")
        cfg = {}
    cfg_sha = sha256_bytes(json.dumps(
        cfg, sort_keys=True, separators=(",", ":")).encode())
    check_pin("c1_config_canonical", cfg_sha, PIN_CONFIG)
    vlog["pins"]["c1_config_cost_views"] = cfg.get("cost_views")

    # -13 stage driver: capture-manifest roots + archive SHA256SUMS.
    sys.path.insert(0, STAGE13)
    import run_study13 as drv
    for name, fname, want in (
            ("child_manifest_root", "child_manifest.json",
             drv.CHILD_ROOT),
            ("parent_manifest_root", "capture_manifest_equity39.json",
             drv.PARENT_ROOT)):
        root, calc = drv.recompute_root(os.path.join(STAGE13, fname))
        ok = root == want and calc == want
        vlog["pins"][name] = {"committed": root, "recomputed": calc,
                              "expected": want, "ok": ok}
        if not ok:
            STOP.append(f"manifest root mismatch: {name}")
    for ns_name, ns in (("continue11", drv.NS11), ("pilot", drv.NSP)):
        sums = {}
        with open(os.path.join(ns, "SHA256SUMS")) as f:
            for line in f:
                line = line.strip()
                if line:
                    digest, rel = line.split(None, 1)
                    sums[rel.strip()] = digest
        bad = [rel for rel, want in sums.items()
               if sha256_file(os.path.join(ns, rel)) != want]
        vlog["pins"][f"archive_sums_{ns_name}"] = {
            "files": len(sums), "mismatches": bad, "ok": not bad}
        if bad:
            STOP.append(f"archive SHA256SUMS mismatch in {ns_name}: "
                        f"{bad[:5]}")
    if STOP:
        return None

    spec = importlib.util.spec_from_file_location("pb_pinned", sim_path)
    pb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pb)
    cohort = json.load(open(cohort_path))
    return {"pb": pb, "drv": drv, "cfg": cfg,
            "ledger": json.loads(ledger_bytes), "cohort": cohort}



def phase_b_data(data):
    """Rebuild the DEV 4H bars through the executed -13 pipeline and
    verify the rebuild against the P7b inventory and the frozen cohort.
    Returns (bars, cohort_events) or (None, None). Computes no legs."""
    drv, pb = data["drv"], data["pb"]
    child_manifest = json.load(open(os.path.join(
        STAGE13, "child_manifest.json")))
    symbols43 = drv.PILOT + [l["symbol"] for l in child_manifest["legs"]
                             if l["window"] == "W_DEV"]
    assert len(symbols43) == 43 and len(set(symbols43)) == 43
    table, dev_sessions = drv.load_session_table()
    admitted = drv.phase2(table, dev_sessions, symbols43)
    if drv.failures:
        STOP.append(f"-13 phase2 failures: {drv.failures[:5]}")
        return None, None
    bars4h = drv.phase4(admitted, dev_sessions, symbols43)
    if drv.failures:
        STOP.append(f"-13 phase4 failures: {drv.failures[:5]}")
        return None, None
    bars = {}
    for sym in symbols43:
        bars[sym] = pb.add_pine_indicators(bars4h[sym])
    vlog["data_path"]["admitted_1h_per_symbol"] = {
        s: len(admitted[s]) for s in symbols43}
    vlog["data_path"]["bars_4h_per_symbol"] = {
        s: len(bars[s]) for s in symbols43}
    if any(len(admitted[s]) != 3653 for s in symbols43):
        STOP.append("admitted 1h bars != 3653 for some symbol")
    if any(len(bars[s]) != 1043 for s in symbols43):
        STOP.append("4H bars != 1043 for some symbol")

    # ---- reconcile against the P7b every-bar inventory --------------
    inv = {}
    with open(INVENTORY) as f:
        for line in f:
            r = json.loads(line)
            inv[(r["symbol"], r["idx"])] = r
    vlog["data_path"]["inventory_rows"] = len(inv)
    if len(inv) != 44849:
        STOP.append(f"inventory rows {len(inv)} != 44849")
    close_bad = atr_bad = ema_bad = sig_bad = ord_bad = 0
    fires = 0
    for (sym, idx), r in inv.items():
        df = bars[sym]
        if float(df["Close"].iloc[idx]) != r["close"]:
            close_bad += 1
        if abs(float(df["atr"].iloc[idx]) - r["atr"]) > 1e-9 * max(
                1.0, abs(r["atr"])):
            atr_bad += 1
        for col, key in (("e21", "ema21"), ("e55", "ema55"),
                         ("e200", "ema200")):
            mine = float(df[col].iloc[idx])
            theirs = r[key]
            if theirs is None or abs(mine - theirs) > 1e-9 * max(
                    1.0, abs(theirs)):
                ema_bad += 1
        if r["in_generator_domain"]:
            sig = bool(pb.pine_buy_signal(df, idx))
            if sig != bool(r["signal"]):
                sig_bad += 1
            fires += int(sig)
    vlog["data_path"]["reconciliation"] = {
        "close_mismatches": close_bad, "atr_mismatches": atr_bad,
        "ema_mismatches": ema_bad, "signal_mismatches": sig_bad,
        "engine_fires_in_domain": fires, "expected_fires": 2892}
    if close_bad or atr_bad or ema_bad or sig_bad:
        STOP.append("inventory reconciliation mismatch: "
                    f"close {close_bad} atr {atr_bad} ema {ema_bad} "
                    f"signal {sig_bad}")
    if fires != 2892:
        STOP.append(f"signal census {fires} != 2892 (P7)")

    # ---- cohort verification -----------------------------------------
    cohort_events = data["cohort"]["cohort"]
    if len(cohort_events) != 311:
        STOP.append(f"cohort events {len(cohort_events)} != 311")
    dev_ord = {s["date"]: i for i, s in enumerate(dev_sessions)}
    coh_bad = 0
    for ev in cohort_events:
        df = bars[ev["symbol"]]
        idx = ev["signal_idx"]
        if df.index[idx].isoformat() != ev["ts"]:
            coh_bad += 1
        if not pb.pine_buy_signal(df, idx):
            coh_bad += 1
        ev["_ordinal"] = dev_ord[df.index[idx].date().isoformat()]
        inv_row = inv[(ev["symbol"], idx)]
        if inv_row["session_ordinal"] != ev["_ordinal"]:
            ord_bad += 1
    vlog["data_path"]["cohort_check"] = {
        "events": len(cohort_events), "mismatches": coh_bad,
        "ordinal_mismatches": ord_bad}
    if coh_bad or ord_bad:
        STOP.append(f"cohort check failed: {coh_bad} event mismatches, "
                    f"{ord_bad} ordinal mismatches")
    if STOP:
        return None, None
    print("data path verified: 44,849 bars reconciled, census 2,892, "
          "cohort 311 verified", flush=True)
    return bars, cohort_events



def net_r(entry, risk_frac, exit_px):
    """Frozen flat-cost convention (-13 _outcome at the 25 bps view):
    net return = (exit-entry)/entry - cost; R = net return / risk."""
    return ((exit_px - entry) / entry - COST_25BPS) / risk_frac


def blended_exit(entry, tp1, final_px, tp_hit):
    """The pinned engine's synthetic blended exit: half at TP1 when hit,
    half at the final exit (whole position at final when TP1 missed)."""
    if tp_hit:
        return entry + 0.5 * (tp1 - entry) + 0.5 * (final_px - entry)
    return final_px


def sim_e0(df, sig_i, entry, stop0, tp1):
    """E0 (control): the pinned simulator's standalone-trade path,
    anchored at one signal bar. Management replicates gen_pine_trades
    exactly (close-evaluated stop = trailed runner incl. the initial
    stop; TP1 intrabar touch at the limit; EMA55 / trend-bear close
    exits; done-fills at the next bar's Open; loop bound i < n-1).
    Returns net R at the 25 bps flat view, or None when the trade is
    still open at the data boundary (censored)."""
    n = len(df)
    risk_frac = (entry - stop0) / entry
    tp_hit = False
    runner = stop0
    i = sig_i + 1
    while i < n - 1:
        h = float(df["High"].iloc[i]); c = float(df["Close"].iloc[i])
        atr_i = float(df["atr"].iloc[i])
        e55 = float(df["e55"].iloc[i])
        e21 = float(df["e21"].iloc[i]); e200 = float(df["e200"].iloc[i])
        if not tp_hit and h >= tp1:
            tp_hit = True
        if tp_hit:
            runner = max(runner, c - atr_i * TRAIL_ATR)
        trend_bear = e21 < e55 and c < e200
        done = False
        if c < runner:
            done = True
        elif c < e55 or trend_bear:
            done = True
        if done:
            exit_px = float(df["Open"].iloc[i + 1])
            return net_r(entry, risk_frac,
                         blended_exit(entry, tp1, exit_px, tp_hit))
        i += 1
    return None


def sim_e1(df, sig_i, entry, stop0, tp1, atr_sig):
    """E1 (intrabar stop): S7 table. Stop in force on a bar = runner
    entering the bar (stop0 before TP1; trailed runner after). Stop
    touch Low <= level -> fill min(Open, level) - 0.05*ATR(sig bar)
    [C15]; stop-first when stop and TP1 are both touched in one bar.
    TP1 touch and close-based exits as E0. Returns net R (25 bps flat)
    or None when unclosed at the data boundary."""
    n = len(df)
    risk_frac = (entry - stop0) / entry
    tp_hit = False
    runner = stop0
    i = sig_i + 1
    while i < n - 1:
        o = float(df["Open"].iloc[i]); h = float(df["High"].iloc[i])
        lo = float(df["Low"].iloc[i]); c = float(df["Close"].iloc[i])
        atr_i = float(df["atr"].iloc[i])
        e55 = float(df["e55"].iloc[i])
        e21 = float(df["e21"].iloc[i]); e200 = float(df["e200"].iloc[i])
        if lo <= runner:
            fill = min(o, runner) - E1_SLIP_ATR * atr_sig
            return net_r(entry, risk_frac,
                         blended_exit(entry, tp1, fill, tp_hit))
        if not tp_hit and h >= tp1:
            tp_hit = True
        if tp_hit:
            runner = max(runner, c - atr_i * TRAIL_ATR)
        trend_bear = e21 < e55 and c < e200
        if c < e55 or trend_bear:
            exit_px = float(df["Open"].iloc[i + 1])
            return net_r(entry, risk_frac,
                         blended_exit(entry, tp1, exit_px, tp_hit))
        i += 1
    return None


def sim_e3(df, sig_i, entry, stop0):
    """E3 (reference): no stop, no TP1; exit at Close[sig_i + 20].
    Returns net R (25 bps flat, risk unit = frozen initial risk) or
    None when the fixed window runs past the last bar."""
    n = len(df)
    if sig_i + 20 > n - 1:
        return None
    risk_frac = (entry - stop0) / entry
    exit_px = float(df["Close"].iloc[sig_i + 20])
    return net_r(entry, risk_frac, exit_px)



def phase_c_fidelity(data, bars):
    """E0 fidelity gate: the anchored sim_e0 must reproduce the -13
    ledger's on-record net R (25 bps) for every closed candidate, and
    must return unclosed for every censored candidate. Counts only —
    no outcome statistic leaves this gate."""
    pb = data["pb"]
    ledger = data["ledger"]
    closed = [r for r in ledger if not r["censored"]]
    censored = [r for r in ledger if r["censored"]]
    # pinned engine's own generator output, for cross-reference
    gen = {}
    for sym, df in bars.items():
        trs, _skipped_gap = pb.gen_pine_trades(sym, df)
        for tr in trs:
            gen[(sym, tr["signal_time"])] = tr
    cmp_n = 0
    r_bad = meta_bad = miss = 0
    max_diff = 0.0
    for row in closed:
        sym = row["symbol"]
        tr = gen.get((sym, row["signal_time"]))
        if tr is None:
            miss += 1
            continue
        if (tr["entry"] != row["entry"] or tr["stop"] != row["stop"]
                or tr["exit"] != row["exit_synth"]
                or tr["tp1_hit"] != row["tp1_hit"]
                or tr["hold_bars"] != row["hold_bars"]
                or tr["reason"] != row["reason"]):
            meta_bad += 1
        df = bars[sym]
        atr_sig = float(df["atr"].iloc[row["signal_idx"]])
        entry = float(df["Open"].iloc[row["signal_idx"] + 1])
        stop0 = float(df["Close"].iloc[row["signal_idx"]]) \
            - SL_ATR * atr_sig
        tp1 = entry + TP_ATR * atr_sig
        mine = sim_e0(df, row["signal_idx"], entry, stop0, tp1)
        cmp_n += 1
        if mine is None:
            r_bad += 1
            continue
        d = abs(mine - row["net_r_25bps"])
        max_diff = max(max_diff, d)
        if d > 6e-5:
            r_bad += 1
    cen_bad = 0
    for row in censored:
        df = bars[row["symbol"]]
        atr_sig = float(df["atr"].iloc[row["signal_idx"]])
        entry = float(df["Open"].iloc[row["signal_idx"] + 1])
        stop0 = float(df["Close"].iloc[row["signal_idx"]]) \
            - SL_ATR * atr_sig
        tp1 = entry + TP_ATR * atr_sig
        if sim_e0(df, row["signal_idx"], entry, stop0, tp1) is not None:
            cen_bad += 1
    vlog["fidelity"] = {
        "ledger_closed_candidates": len(closed),
        "generator_trades": len(gen),
        "compared": cmp_n, "missing_in_generator": miss,
        "metadata_mismatches": meta_bad, "r_mismatches": r_bad,
        "max_abs_r_diff": max_diff,
        "ledger_censored_candidates": len(censored),
        "censored_not_unclosed_in_sim": cen_bad}
    ok = (miss == 0 and meta_bad == 0 and r_bad == 0 and cen_bad == 0
          and len(gen) == len(closed))
    if not ok:
        STOP.append(f"E0 fidelity gate failed: {vlog['fidelity']}")
    else:
        print(f"E0 fidelity gate PASS: {cmp_n} closed candidates "
              f"reproduced, {len(censored)} censored unclosed",
              flush=True)
    return ok


def circ_block_resample_var(items):
    """[C10] circular block bootstrap over calendar time, DEV-relative
    session ordinals; blocks of 20 sessions; 10,000 replications; seed
    = first 8 bytes BE of the frozen preregistration's SHA-256. The
    construction follows the program's EXP-14-lineage implementation
    (circular_block_bootstrap in the corr2 package): block starts are
    drawn uniformly from the ordinals present in the items; a block
    covers 20 consecutive ordinals circularly over the observed span
    and contributes every value whose ordinal it covers; blocks are
    drawn until at least n values are collected; the statistic is the
    mean of the first n values. Returns (resample_var, mean_blocks)."""
    ords = sorted({o for o, _ in items})
    lo, hi = ords[0], ords[-1]
    span = hi - lo + 1
    by_ord = {}
    for o, v in items:
        by_ord.setdefault(o, []).append(v)
    n = len(items)
    rng = np.random.default_rng(np.random.PCG64(BOOT_SEED))
    means = np.empty(BOOT_REPS)
    blocks_total = 0
    for r in range(BOOT_REPS):
        vals = []
        nb = 0
        while len(vals) < n:
            start = ords[int(rng.integers(0, len(ords)))]
            nb += 1
            for k in range(BOOT_BLOCK_SESSIONS):
                o = lo + ((start - lo + k) % span)
                if o in by_ord:
                    vals.extend(by_ord[o])
        blocks_total += nb
        means[r] = float(np.mean(vals[:n]))
    return float(np.var(means, ddof=1)), blocks_total / BOOT_REPS



def write_outputs(status, extra_note=None):
    out = {"schema": "O4_OUTPUT_V1", "status": status,
           "procedure": "O4_PROCEDURE.md (G5 freeze package 5037311, "
                        "addendum 4988f15)",
           "basis": "Stage-1 FLAT 25 bps round-trip view of the frozen "
                    "C1 config (O4_BASIS_PIN); S8 per-fill NOT used",
           "endpoints": vlog.get("endpoints"),
           "exclusion_counts": vlog["counts"],
           "input_pins": vlog["pins"],
           "run": {"script": "o4_run.py",
                   "script_sha256": sha256_file(
                       os.path.abspath(__file__)),
                   "seed_C10": BOOT_SEED,
                   "bootstrap": "circular calendar block, 20 sessions, "
                                "10000 reps, PCG64",
                   "scope": "DEV only; no holdout access; no performance "
                            "run; variance-only outputs"}}
    if extra_note:
        out["note"] = extra_note
    if STOP:
        out["stop_reasons"] = STOP
    with open(os.path.join(HERE, "o4_output.json"), "w") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    with open(os.path.join(HERE, "verification_log.json"), "w") as f:
        json.dump(vlog, f, indent=2, sort_keys=True)
    return out


def main():
    print("O4 run start", flush=True)
    data = phase_a_pins()
    if data is None:
        write_outputs("STOP_PIN_FAILURE")
        print("STOP: pin failure - nothing computed", flush=True)
        return 2
    try:
        bars, cohort_events = phase_b_data(data)
    except Exception as e:  # driver asserts raise; treat as STOP
        STOP.append(f"data build raised: {e!r}")
        bars, cohort_events = None, None
    if bars is None:
        write_outputs("STOP_DATA_VERIFICATION")
        print("STOP: data-path verification failure", flush=True)
        return 2
    try:
        fidelity_ok = phase_c_fidelity(data, bars)
    except Exception as e:
        STOP.append(f"fidelity gate raised: {e!r}")
        fidelity_ok = False
    if not fidelity_ok:
        write_outputs("STOP_FIDELITY")
        print("STOP: E0 fidelity gate failed", flush=True)
        return 2

    # ---------------- legs over the cohort (memory only) -------------
    n_gap = n_win = n_u0 = n_u1 = 0
    items1, items3 = [], []
    for ev in cohort_events:
        sym, sig_i = ev["symbol"], ev["signal_idx"]
        df = bars[sym]
        atr_sig = float(df["atr"].iloc[sig_i])
        entry = float(df["Open"].iloc[sig_i + 1])
        stop0 = float(df["Close"].iloc[sig_i]) - SL_ATR * atr_sig
        tp1 = entry + TP_ATR * atr_sig
        if entry <= stop0:                      # [C11], all arms
            n_gap += 1
            continue
        r_e3 = sim_e3(df, sig_i, entry, stop0)
        if r_e3 is None:
            n_win += 1
            continue
        r_e0 = sim_e0(df, sig_i, entry, stop0, tp1)
        r_e1 = sim_e1(df, sig_i, entry, stop0, tp1, atr_sig)
        if r_e0 is None:
            n_u0 += 1
        if r_e1 is None:
            n_u1 += 1
        if r_e0 is None or r_e1 is None:
            continue                            # common-set rule
        items1.append((ev["_ordinal"], r_e1 - r_e0))
        items3.append((ev["_ordinal"], r_e0 - r_e3))
    n_pair = len(items1)
    vlog["counts"].update({
        "cohort_events": len(cohort_events),
        "excluded_pre_entry_gap_C11": n_gap,
        "excluded_window_incomplete": n_win,
        "unclosed_in_E0": n_u0,
        "unclosed_in_E1": n_u1,
        "common_paired_n": n_pair})
    print(f"legs done: common paired n = {n_pair}", flush=True)
    if n_pair < FLOOR_N:
        write_outputs("STOP_N_BELOW_FLOOR",
                      "common paired set below the frozen 100 floor; "
                      "n only is reported, per procedure S6")
        print("STOP: n below floor", flush=True)
        return 2

    endpoints = {}
    de_info = {}
    for key, items in (("H-EXIT-1", items1), ("H-EXIT-3", items3)):
        d = np.array([v for _, v in items], dtype=float)
        n = len(d)
        s = float(np.std(d, ddof=1))
        res_var, mean_blocks = circ_block_resample_var(items)
        var_iid_mean = float(np.var(d, ddof=1)) / n
        de = res_var / var_iid_mean
        endpoints[key] = {"n": n, "s": s, "DE": float(de),
                          "n_eff": float(n / de)}
        de_info[key] = {"mean_blocks_per_rep": mean_blocks}
        del d  # variance-only: per-event values never leave memory
    assert all(set(v.keys()) == {"n", "s", "DE", "n_eff"}
               for v in endpoints.values())
    vlog["endpoints"] = endpoints
    vlog["counts"]["design_effect_blocks"] = de_info
    write_outputs("COMPLETE")
    print("O4 COMPLETE", flush=True)
    print(json.dumps(endpoints, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
