"""Exploratory-window metrics for frozen candidates C1/C2/C3.

Same window/conventions as the ablation (UX51 4H 2024-09-16->2026-09-14).
Candidate cfgs must match pine_entry_validate.py CANDIDATES exactly.
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pine_backtest as pb
from pine_entry_ablation import run_variant, load_4h_cache
from pine_entry_validate import CANDIDATES

OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "pine_entry_candidates_exploratory.json")


def main():
    print("loading 4H cache...", flush=True)
    data = load_4h_cache()
    print(f"  {len(data)} symbols", flush=True)
    results = {"notes": [
        "Exploratory metrics for frozen candidates (same window as ablation).",
        "Cfgs identical to pine_entry_validate.py CANDIDATES.",
    ], "variants": {}}
    for vid, cfg in CANDIDATES.items():
        if vid == "V0_baseline":
            continue
        print(f"== {vid} ==", flush=True)
        rows = run_variant(vid, cfg, data, f"PINE_V36_entrycand:{vid}:UX51:4h")
        results["variants"][vid] = {"runs": rows}
        for r in rows:
            print(f"  [{r['cost']}] n={r['trades']} win={r.get('win_rate_pct', 'n/a')}% "
                  f"exp={r.get('expectancy_net_r', 'n/a')}R PF={r.get('profit_factor', 'n/a')} "
                  f"ret={r.get('total_return_pct', 'n/a')}% dd={r.get('max_drawdown_pct', 'n/a')}% "
                  f"hold={r.get('avg_hold_bars', 'n/a')}", flush=True)
        with open(OUT_JSON, "w") as f:
            json.dump(results, f, indent=1, default=str)
    print("DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
