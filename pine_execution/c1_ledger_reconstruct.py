"""Reconstruct the canonical 143-trade C1 per-trade ledger from frozen components.

Protocol (Mike's, 2026-09-27): the original per-trade ledger file was never
saved as an artifact. Fallback branch: reconstruct C1 from the frozen
components and require EXACT reproduction of the acceptance gate —
143 trades, +0.337R expectancy, +52.25% return, ~31.63% max DD — before
accepting the reconstruction as canonical.

Reconstruction path (frozen, unmodified code):
  pine_stack.load_bull() -> compute_features (rs) -> simulate_stack with
  use_ranking=True, sector_cap=True, cost=4bps  == E0_4bps/C1 in
  pine_execution.EXECUTION_SPEC.md, which already passed its fidelity check
  vs pine_stack stack_results.json C1@4bps.

Output: c1_ledger_reconstructed_2026-09-28.json — one row per taken trade
with trade fields + net R + entry/exit accounting, plus a provenance block
recording the gate check. NOTHING frozen is modified by this script.
"""
import json
import os
import sys
import hashlib
import datetime

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "pine_stack"))
sys.path.insert(0, os.path.join(HERE, "pine_ranking"))
sys.path.insert(0, os.path.join(HERE, "pine_signal_quality"))

import pine_backtest as pb
import pine_stack as st
from pine_ranking import compute_features
from pine_signal_quality import load_benchmarks

GATE = {"trades": 143, "expectancy_net_r": 0.337,
        "total_return_pct": 52.25, "max_drawdown_pct": 31.63}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main():
    bench, _ = load_benchmarks()
    all_trades, closes, data, order_of, skipped_gap = st.load_bull()

    feats = compute_features(all_trades, {s: df for s, df in data.items()}, bench)
    rs_by_id = {id(tr): feats[i]["rs"] for i, tr in enumerate(all_trades)}

    st.rs = rs_by_id
    cost = pb.COSTS["4bps"]
    port = st.simulate_stack(all_trades, closes, cost, True, True, False, st.SECTOR)
    taken = [all_trades[i] for i in port["taken"]]

    # acceptance gate (Mike's numbers)
    row = pb.summarize("bull-E0_4bps-C1", taken, port, skipped_gap, "4bps")
    got = {k: row[k] for k in GATE}
    ok = all(got[k] == GATE[k] for k in GATE)
    print(f"GATE CHECK: got {got}, want {GATE} -> {'PASS' if ok else 'FAIL'}",
          flush=True)
    if not ok:
        print("ACCEPTANCE GATE FAILED — ledger rejected as non-canonical")
        sys.exit(2)

    # per-trade ledger
    ledger = []
    for tr in taken:
        entry, stop, exitp = tr["entry"], tr["stop"], tr["exit"]
        risk_frac, gross_r, net_r, net_ret = pb._outcome(entry, stop, exitp, cost)
        ledger.append({
            "symbol": tr.get("symbol"),
            "signal_time": str(tr.get("signal_time")),
            "entry_time": str(tr.get("entry_time")),
            "entry": entry, "stop": stop, "exit": exitp,
            "exit_time": str(tr.get("exit_time")),
            "hold_bars": tr.get("hold_bars"),
            "exit_reason": tr.get("reason"),
            "tp1_hit": bool(tr.get("tp1_hit")),
            "net_r": round(float(net_r), 6),
            "net_ret_pct": round(float(net_ret) * 100, 4),
        })
    assert len(ledger) == 143

    provenance = {
        "type": "C1 per-trade ledger RECONSTRUCTION (original artifact never saved)",
        "reconstructed": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "acceptance_gate": GATE,
        "gate_result": "PASS",
        "path": "pine_stack.load_bull -> compute_features -> simulate_stack"
                "(use_ranking=True, sector_cap=True, cost=4bps) == "
                "pine_execution E0_4bps/C1",
        "code_sha256": {
            "pine_stack.py": sha256_file(os.path.join(HERE, "pine_stack", "pine_stack.py")),
            "pine_backtest.py": sha256_file(os.path.join(HERE, "pine_backtest.py")),
            "pine_execution.py": sha256_file(os.path.join(HERE, "pine_execution", "pine_execution.py")),
            "this_script": sha256_file(os.path.abspath(__file__)),
        },
        "summary": row,
    }
    out = {"provenance": provenance, "trades": ledger}
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "c1_ledger_reconstructed_2026-09-28.json")
    json.dump(out, open(out_path, "w"), indent=1, default=str)
    print(f"wrote {out_path} ({len(ledger)} trades)", flush=True)


if __name__ == "__main__":
    main()
