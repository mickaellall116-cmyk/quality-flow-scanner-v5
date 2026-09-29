#!/usr/bin/env python3
"""Step 6 of the 2026-09-20 score-bug correction.

Uses the FIXED canonical pine_backtest.pine_buy_signal (trend_score now a
true 0-5 int via per-condition int() casts) directly for Hybrid. The
live Aggressive+pullback+sweep config keeps its research driver from
run_liveconfig, but its trend-score now matches the canonical fix exactly.

Prior corrected_results.json (2026-09-20, research-override scores) is
superseded by this run: canonical-fix code, no monkey-patching.
"""
import sys, os, json, time

BASE = "/home/hatch/workspace/quality-flow-scanner-v5"
OUTDIR = os.path.join(BASE, "pine_sensitivity")
sys.path.insert(0, BASE)
sys.path.insert(0, OUTDIR)
import pine_backtest as pb
from run_corrected import corrected_live, gen_with_live, _orig_gen


def run(name, gen_fn=None):
    t0 = time.time()
    rows, trades = pb.run_universe(pb.UNIVERSE_X, "UX51", "4h")
    dt = time.time() - t0
    rec = {"config": name, "seconds": round(dt, 1)}
    for r in rows:
        rec[r["cost"]] = {
            "trades": r["trades"], "win_rate_pct": r["win_rate_pct"],
            "expectancy_r": r["expectancy_net_r"], "profit_factor": r["profit_factor"],
            "return_pct": r["total_return_pct"], "max_dd_pct": r["max_drawdown_pct"],
        }
        print(f"{name} [{r['cost']}]: n={r['trades']} win={r['win_rate_pct']}% "
              f"exp={r['expectancy_net_r']}R PF={r['profit_factor']} "
              f"ret={r['total_return_pct']}% dd={r['max_drawdown_pct']}%", flush=True)
    return rec


def main():
    out = []
    # Hybrid = canonical decision path, corrected score fix, no patching.
    pb.gen_pine_trades = _orig_gen
    out.append(run("Hybrid (canonical, corrected score)"))
    # Live chart config: Aggressive + pullback + sweep.
    pb.pine_buy_signal = corrected_live
    pb.gen_pine_trades = gen_with_live
    out.append(run("Live Aggr+PB+SW (corrected score)"))
    with open(os.path.join(OUTDIR, "corrected_results_v2.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("wrote pine_sensitivity/corrected_results_v2.json")


if __name__ == "__main__":
    main()
