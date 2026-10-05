#!/usr/bin/env python3
"""CP1 follow-up: trade intersection analysis.
Task 3 of ChatGPT bounded assignment (Issue #1 comment 5986944792).

For each of the 240 C1 baseline trades, determine temporal intersection with:
  (a) EST shifted-regime periods (bars on 08:30/12:30 EST labels instead of 09:30/13:30)
  (b) The two specific gap timestamps (2026-01-30 12:30-05:00, 2026-02-02 08:30-05:00)
      for the 22 affected symbols
  (c) SOL-USD outage windows (2025-11-17..19, 2025-12, 2026-05, 2026-07 clusters)

Outputs trade_id, symbol, signal/entry/exit times, and gap references.
Temporal overlap alone is NOT proof of performance impact — stated in output.
All findings tagged COMPUTED.
"""
import json, os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = ("/home/hatch/workspace/quality-flow-scanner-v5/research_notes/"
          "recovery_4h_20261004/cp1_bundle/02_c1_ledger/c1_240_trade_ledger.json")

# EST shifted-regime periods: when America/New_York is on EST (UTC-5),
# the 13:30/17:30 UTC bins label as 08:30/12:30 EST instead of 09:30/13:30.
# EST periods within cache window (2024-09-16 -> 2026-09-14):
EST_PERIODS = [
    ("2024-11-03", "2025-03-09"),  # EST 2024-25
    ("2025-11-02", "2026-03-08"),  # EST 2025-26
]
# 22 symbols missing the two gap timestamps
GAP22 = {'AAPL','AMAT','AMD','ARKK','AVGO','COIN','DDOG','F','GOOGL','IWM','META',
         'MRNA','MSFT','MSTR','NIO','NVDA','PFE','RKLB','SMCI','SMH','SNOW','XLF'}
GAP_T1 = pd.Timestamp("2026-01-30 12:30:00-05:00")  # afternoon bar
GAP_T2 = pd.Timestamp("2026-02-02 08:30:00-05:00")  # morning bar
# SOL outage windows (bars present in BTC grid but missing in SOL)
SOL_GAPS = [
    ("2025-11-17T08:00:00+00:00", "2025-11-22T20:00:00+00:00"),
    ("2025-12-15T00:00:00+00:00", "2025-12-15T20:00:00+00:00"),
    ("2026-05-11T00:00:00+00:00", "2026-05-12T20:00:00+00:00"),
    ("2026-07-12T00:00:00+00:00", "2026-07-13T20:00:00+00:00"),
]

def in_est(ts):
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    d = ts.date().isoformat()
    return any(s <= d <= e for s, e in EST_PERIODS)

def main():
    led = json.load(open(LEDGER))
    trades = led["trades"]
    out = []
    for i, t in enumerate(trades):
        tid = f"T{i:03d}"
        sym = t["symbol"]
        sig = pd.Timestamp(t["signal_time"])
        ent = pd.Timestamp(t["entry_time"])
        ext = pd.Timestamp(t["exit_time"])
        rec = {
            "trade_id": tid, "symbol": sym,
            "signal_time": sig.isoformat(), "entry_time": ent.isoformat(),
            "exit_time": ext.isoformat(),
            "in_est_shifted_regime_entry": in_est(ent),
            "in_est_shifted_regime_exit": in_est(ext),
            "gap_refs": [],
        }
        # (b) 22-symbol gap timestamps: holding interval contains t1 or t2
        if sym in GAP22:
            if ent <= GAP_T1 <= ext:
                rec["gap_refs"].append("GAP22-T1(2026-01-30_12:30-05:00)")
            if ent <= GAP_T2 <= ext:
                rec["gap_refs"].append("GAP22-T2(2026-02-02_08:30-05:00)")
        # (c) SOL gaps
        if sym == "SOL-USD":
            for j, (gs, ge) in enumerate(SOL_GAPS):
                gs, ge = pd.Timestamp(gs), pd.Timestamp(ge)
                if ent <= ge and ext >= gs:
                    rec["gap_refs"].append(f"SOL-GAP{j+1}({gs.date()}_{ge.date()})")
        out.append(rec)

    summ = {
        "method": "COMPUTED",
        "n_trades": len(out),
        "n_entry_in_est": sum(1 for r in out if r["in_est_shifted_regime_entry"]),
        "n_exit_in_est": sum(1 for r in out if r["in_est_shifted_regime_exit"]),
        "n_with_gap_refs": sum(1 for r in out if r["gap_refs"]),
        "disclaimer": ("Temporal overlap alone is NOT proof of performance impact. "
                       "These tables enumerate coincidence of trade intervals with "
                       "known data-regime boundaries; causal effect on P&L is UNRESOLVED."),
        "trades": out,
    }
    with open(os.path.join(HERE, "trade_intersection.json"), "w") as f:
        json.dump(summ, f, indent=1)
    # SOL trades detail
    sol_trades = [r for r in out if r["symbol"] == "SOL-USD"]
    print(f"total={len(out)} est_entry={summ['n_entry_in_est']} gap_refs={summ['n_with_gap_refs']} sol_trades={len(sol_trades)}")
    for r in sol_trades:
        print(f"  {r['trade_id']} {r['entry_time'][:16]} -> {r['exit_time'][:16]} gaps={r['gap_refs']}")

if __name__ == "__main__":
    main()
