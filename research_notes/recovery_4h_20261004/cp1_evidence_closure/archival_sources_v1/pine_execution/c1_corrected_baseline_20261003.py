"""Corrected intended C1 baseline stack (2026-10-03).

Reproduces the INTENDED C1 stack with all known defects fixed:
  1. Correct signals: pine_backtest.pine_buy_signal WITH int() casts on the
     trendScore (the pre-Sep-20 numpy-boolean bug is gone; verified below).
  2. Study-grid candles: backtest_cache/v3 4h pickles — UTC-anchored bins at
     13:30/17:30 UTC (09:30/13:30 NY in EDT, 08:30/12:30 NY in EST; the DST
     drift is documented as a caveat, not re-cut). This is the exact grid the
     Sep-20 corrected rerun used; the pine_stack pipeline never touched the
     live harness's resample code, so the 06:30 bug does not apply here.
  3. Portfolio construction per STACK_SPEC.md: R1 rs_top2 ranking on contested
     bars, R2 E1 sector cap (>=2 open in sector -> skip), and the 5%
     portfolio-risk check (MAX_PORTFOLIO_RISK). The R3 drawdown gate is
     EXCLUDED: EXECUTION_SPEC.md records it as tested and REJECTED as
     redundant — it is not part of the locked stack.
  4. Frozen execution/cost assumptions: 4bps one-way cost via pb._outcome,
     next-bar-open entries, stop-first ambiguity (all inside gen_candidates).

This is the baseline the 143-trade buggy figure corrupted. Expected (from the
Sep-20 corrected rerun, stack_results_C1_CORRECTED_SCORE_BASELINE.json):
  C1 = 240 trades, +0.178R expectancy, +42.24% return, 38.46% max DD @4bps.
This script asserts those figures and additionally emits the per-trade ledger
that was never saved for any C1 run, plus per-trade decision traces.

Outputs (new files only; nothing frozen is modified):
  pine_execution/c1_corrected_baseline_20261003.json
"""
import os
import sys
import json
import hashlib
import datetime
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "pine_stack"))
sys.path.insert(0, os.path.join(HERE, "pine_ranking"))
sys.path.insert(0, os.path.join(HERE, "pine_exposure"))
sys.path.insert(0, os.path.join(HERE, "pine_signal_quality"))

import numpy as np
import pandas as pd

import pine_backtest as pb
import pine_stack as st
from pine_ranking import compute_features
from pine_signal_quality import load_benchmarks
from pine_exposure import SECTOR

EXPECTED = {"trades": 240, "expectancy_net_r": 0.178,
            "total_return_pct": 42.24, "max_drawdown_pct": 38.46}
COST_NAME = "4bps"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def assert_fixed_signal():
    src = open(os.path.join(HERE, "pine_backtest.py")).read()
    assert 'int(r["e9"] > r["e21"])' in src, "trendScore int() fix missing!"
    print("signal check: int()-cast trendScore present (bug fixed)", flush=True)


def assert_session_grid(data):
    """Verify the v3 cache grid is EXACTLY the grid the pine_stack studies ran
    on: UTC-anchored 4h bins at 13:30/17:30 UTC. In America/New_York that is
    09:30/13:30 in EDT and 08:30/12:30 in EST (one-hour DST drift).

    MATERIAL CAVEAT (documented, not fixed): the "intended" 09:30 NY session
    anchor holds only in EDT. The studies' candles were built with this
    UTC-anchored grid, so reproducing the corrected stack means reproducing
    THIS grid — rebuilding with a true session-anchored resampler would create
    a new variant, not the intended baseline. The 06:30 live-harness bug never
    touched the pine_stack pipeline; this milder DST drift is a property of
    the study data itself.
    """
    bad_utc, bad_ny = 0, []
    n_crypto = 0
    for sym, df in data.items():
        if sym.upper().endswith("-USD"):
            n_crypto += 1
            continue  # crypto: 24/7 bars on 00/04/08/12/16/20 UTC, by design
        idx_utc = df.index.tz_convert("UTC")
        utc_hm = set(zip(idx_utc.hour, idx_utc.minute))
        if utc_hm - {(13, 30), (17, 30)}:
            bad_utc += 1
            bad_ny.append((sym, sorted(utc_hm - {(13, 30), (17, 30)})[:4]))
    assert bad_utc == 0, f"{bad_utc} symbols off the 13:30/17:30 UTC grid: {bad_ny[:5]}"
    print(f"grid check: {len(data) - n_crypto} equity symbols on the study's "
          f"UTC-anchored 13:30/17:30 grid (09:30/13:30 EDT, 08:30/12:30 EST — "
          f"DST drift documented as caveat); {n_crypto} crypto on 24/7 UTC grid",
          flush=True)


def trace_stack(all_trades, closes, cost, rs_by_id, sector_map):
    """Instrumented copy of pine_stack.simulate_stack for C1
    (use_ranking=True, sector_cap=True, dd_gate=False). Records a decision
    trace for every taken trade. Must produce the identical taken set."""
    def mark(sym, t):
        s = closes[sym]
        ii = s.index.searchsorted(t, side="right") - 1
        return float(s.iloc[ii]) if ii >= 0 else float(s.iloc[0])

    entries_by_t = defaultdict(list)
    exits_by_t = defaultdict(list)
    for idx, tr in enumerate(all_trades):
        entries_by_t[tr["entry_time"]].append(idx)
        exits_by_t[tr["exit_time"]].append(idx)
    times = sorted(set(entries_by_t) | set(exits_by_t))

    realized = pb.START_EQUITY
    open_pos, by_id = [], {}
    peak, max_dd = realized, 0.0
    taken = []
    traces = {}
    prev_t = None

    def marked_equity(t):
        unreal = 0.0
        for p in open_pos:
            tr = p["trade"]
            unreal += ((mark(tr["symbol"], t) - tr["entry"]) / tr["entry"]) * p["size"]
        return realized + unreal

    for t in times:
        prev_t = t
        for idx in sorted(exits_by_t.get(t, [])):
            pos = by_id.pop(id(all_trades[idx]), None)
            if pos is None:
                continue
            tr = all_trades[idx]
            _, _, net_r, _ = pb._outcome(tr["entry"], tr["stop"], tr["exit"], cost)
            realized += pos["risk_dollars"] * net_r
            open_pos.remove(pos)
        cands = entries_by_t.get(t, [])
        if cands:
            n_cands_t = len(cands)
            scored = [(-rs_by_id[id(all_trades[i])], i) for i in cands]
            scored.sort()
            ordered = [i for _, i in scored]
            rank_of = {idx: r + 1 for r, idx in enumerate(ordered)}
            free0 = pb.MAX_CONCURRENT - len(open_pos)
            taken_at_t = 0
            for idx in ordered:
                tr = all_trades[idx]
                free = pb.MAX_CONCURRENT - len(open_pos)
                contested_now = n_cands_t > free
                if contested_now and taken_at_t >= min(2, free):
                    continue  # rank cap
                if free <= 0:
                    continue  # max positions
                eq = marked_equity(t)
                s = sector_map[tr["symbol"]]
                n_sec = sum(1 for p in open_pos
                            if sector_map[p["trade"]["symbol"]] == s)
                if n_sec >= 2:
                    continue  # sector cap
                open_risk = (sum(p["risk_dollars"] for p in open_pos) / eq
                             if eq > 0 else 1)
                if open_risk + pb.RISK_PCT > pb.MAX_PORTFOLIO_RISK + 1e-9:
                    continue  # 5% portfolio-risk gate
                risk_dollars = pb.RISK_PCT * eq
                risk_frac = (tr["entry"] - tr["stop"]) / tr["entry"]
                pos = {"trade": tr, "risk_dollars": risk_dollars,
                       "size": risk_dollars / risk_frac, "risk_frac": risk_frac,
                       "risk_pct": pb.RISK_PCT}
                open_pos.append(pos)
                by_id[id(tr)] = pos
                taken.append(idx)
                taken_at_t += 1
                traces[idx] = {
                    "entry_bar": str(t),
                    "n_contenders": n_cands_t,
                    "contested": bool(contested_now),
                    "rank_by_rs": rank_of[idx],
                    "free_slots_before": free0,
                    "sector": s,
                    "sector_open_before": n_sec,
                    "portfolio_open_risk_before": round(float(open_risk), 6),
                    "risk_pct_applied": pb.RISK_PCT,
                    "risk_dollars": round(float(risk_dollars), 2),
                    "marked_equity_at_entry": round(float(eq), 2),
                }
        eq = marked_equity(t)
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    return {"final_equity": realized, "max_drawdown": max_dd,
            "taken": taken, "traces": traces}


def main():
    assert_fixed_signal()
    bench, _ = load_benchmarks()
    all_trades, closes, data, order_of, skipped_gap = st.load_bull()
    print(f"candidates (fixed signal): {len(all_trades)}", flush=True)
    assert_session_grid(data)

    feats = compute_features(all_trades, data, bench)
    rs_by_id = {id(tr): feats[i]["rs"] for i, tr in enumerate(all_trades)}
    st.rs = rs_by_id  # module global consumed by simulate_stack

    cost = pb.COSTS[COST_NAME]

    # --- official run: frozen simulate_stack, C1 = R1 + R2, no R3 ---
    port = st.simulate_stack(all_trades, closes, cost, True, True, False,
                             SECTOR)
    taken = [all_trades[i] for i in port["taken"]]
    row = pb.summarize("C1-corrected", taken, port, skipped_gap, COST_NAME)
    row = dict(row)
    print(f"C1 official: n={row['trades']} exp={row['expectancy_net_r']}R "
          f"ret={row['total_return_pct']}% dd={row['max_drawdown_pct']}% "
          f"PF={row['profit_factor']} win={row['win_rate_pct']}%", flush=True)
    got = {k: row[k] for k in EXPECTED}
    ok = all(got[k] == EXPECTED[k] for k in EXPECTED)
    print(f"BASELINE CHECK: got {got}, want {EXPECTED} -> "
          f"{'PASS' if ok else 'FAIL'}", flush=True)
    if not ok:
        print("CORRECTED BASELINE MISMATCH — investigate, do not publish",
              flush=True)
        sys.exit(2)

    # --- traced reimplementation: must match the official taken set exactly ---
    traced = trace_stack(all_trades, closes, cost, rs_by_id, SECTOR)
    assert traced["taken"] == port["taken"], \
        f"traced taken set diverges: {len(traced['taken'])} vs {len(port['taken'])}"
    assert abs(traced["final_equity"] - port["final_equity"]) < 1e-6
    assert abs(traced["max_drawdown"] - port["max_drawdown"]) < 1e-12
    print(f"trace parity: taken sets identical ({len(traced['taken'])}), "
          f"equity/DD match", flush=True)

    # --- C0 reference (no ranking, no caps) on the same fixed signal ---
    port_c0 = st.simulate_stack(all_trades, closes, cost, False, False, False,
                                SECTOR)
    taken_c0 = [all_trades[i] for i in port_c0["taken"]]
    row_c0 = pb.summarize("C0-corrected", taken_c0, port_c0, skipped_gap,
                          COST_NAME)
    print(f"C0 reference: n={row_c0['trades']} exp={row_c0['expectancy_net_r']}R "
          f"ret={row_c0['total_return_pct']}% dd={row_c0['max_drawdown_pct']}%",
          flush=True)

    # --- per-trade ledger with decision traces ---
    ledger = []
    for idx in port["taken"]:
        tr = all_trades[idx]
        entry, stop, exitp = tr["entry"], tr["stop"], tr["exit"]
        risk_frac, gross_r, net_r, net_ret = pb._outcome(entry, stop, exitp,
                                                         cost)
        ledger.append({
            "symbol": tr.get("symbol"),
            "signal_time": str(tr.get("signal_time")),
            "entry_time": str(tr.get("entry_time")),
            "entry": round(float(entry), 4),
            "stop": round(float(stop), 4),
            "exit": round(float(exitp), 4),
            "exit_time": str(tr.get("exit_time")),
            "hold_bars": tr.get("hold_bars"),
            "exit_reason": tr.get("reason"),
            "tp1_hit": bool(tr.get("tp1_hit")),
            "gross_r": round(float(gross_r), 6),
            "cost_bps": 4.0,
            "net_r": round(float(net_r), 6),
            "net_ret_pct": round(float(net_ret) * 100, 4),
            "decision_trace": traced["traces"][idx],
        })
    assert len(ledger) == EXPECTED["trades"]

    # exit-reason and win/loss decomposition
    wins = [l for l in ledger if l["net_r"] > 0]
    losses = [l for l in ledger if l["net_r"] <= 0]
    reasons = {}
    for l in ledger:
        reasons[l["exit_reason"]] = reasons.get(l["exit_reason"], 0) + 1

    provenance = {
        "type": "C1 CORRECTED baseline (intended stack, all defects fixed)",
        "built": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "disqualified_superseded": {
            "buggy_143_trade": "143 trades, +0.337R, +52.25%, 31.63% DD — "
            "reproduces ONLY with the numpy-boolean trendScore bug; "
            "DISQUALIFIED from performance validation. Forensic record: "
            "pine_execution/C1_LEDGER_FINDINGS_2026-09-28.md (preserved).",
        },
        "stack_definition": {
            "signals": "pine_backtest.pine_buy_signal WITH int() casts "
            "(fixed 2026-09-20)",
            "candles": "backtest_cache/v3 4h pickles, UTC-anchored bins at "
            "13:30/17:30 UTC (= 09:30/13:30 NY in EDT, 08:30/12:30 NY in EST). "
            "Grid asserted bar-by-bar in-script. The one-hour EST drift is a "
            "documented property of the study data (caveat, not re-cut): the "
            "pine_stack pipeline never used the live harness resample code, "
            "so the 06:30 bug does not apply; re-cutting true session-anchored "
            "candles would create a new variant, not reproduce this baseline.",
            "universe_window": "UX51 4H 2024-09-16 -> 2026-09-14",
            "R1_ranking": "rs_top2: contested bars rank by 20-bar return "
            "minus SPY, take top min(2, free slots)",
            "R2_sector_cap": "skip if >=2 positions open in sector "
            "(pine_exposure frozen SECTOR map)",
            "portfolio_risk_gate": "skip if open risk + 1% > 5% "
            "(MAX_PORTFOLIO_RISK)",
            "R3_drawdown_gate": "EXCLUDED — tested and REJECTED as redundant "
            "per EXECUTION_SPEC.md; not part of the locked stack",
            "costs": "4bps one-way per trade via pb._outcome "
            "(net_ret = gross_ret - cost)",
            "fills": "next-bar-open entries, stop-first ambiguity "
            "(inside gen_candidates)",
            "max_concurrent": pb.MAX_CONCURRENT,
            "risk_pct": pb.RISK_PCT,
            "start_equity": pb.START_EQUITY,
        },
        "baseline_check": {"expected": EXPECTED, "got": got, "result": "PASS"},
        "trace_parity": "instrumented reimplementation produced the identical "
        "taken set, final equity, and max DD as frozen simulate_stack",
        "code_sha256": {
            "pine_backtest.py": sha256_file(os.path.join(HERE, "pine_backtest.py")),
            "pine_stack.py": sha256_file(os.path.join(HERE, "pine_stack", "pine_stack.py")),
            "pine_ranking.py": sha256_file(os.path.join(HERE, "pine_ranking", "pine_ranking.py")),
            "pine_exposure.py": sha256_file(os.path.join(HERE, "pine_exposure", "pine_exposure.py")),
            "pine_signal_quality.py": sha256_file(os.path.join(HERE, "pine_signal_quality", "pine_signal_quality.py")),
            "this_script": sha256_file(os.path.abspath(__file__)),
        },
        "inputs": {
            "cache": pb.CACHE,
            "cache_symbols": sorted(data.keys()),
            "n_cache_symbols": len(data),
            "benchmarks": "pine_signal_quality.load_benchmarks()",
        },
        "summary_C1": row,
        "summary_C0_reference": dict(row_c0),
        "decomposition": {
            "wins": len(wins), "losses": len(losses),
            "gross_win_r": round(float(sum(l["gross_r"] for l in wins)), 4),
            "gross_loss_r": round(float(sum(l["gross_r"] for l in losses)), 4),
            "exit_reasons": reasons,
        },
        "skips": {
            "rank_cap": port["skipped_rank"],
            "max_positions": port["skipped_cap"],
            "sector_cap": port["skipped_gate"],
            "portfolio_risk": port["skipped_risk"],
            "gap_below_stop": skipped_gap,
        },
    }
    out = {"provenance": provenance, "trades": ledger}
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "c1_corrected_baseline_20261003.json")
    json.dump(out, open(out_path, "w"), indent=1, default=str)
    print(f"wrote {out_path} ({len(ledger)} trades)", flush=True)
    print(f"wins={len(wins)} losses={len(losses)} reasons={reasons}", flush=True)


if __name__ == "__main__":
    main()
