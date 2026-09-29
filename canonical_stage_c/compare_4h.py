#!/usr/bin/env python3
"""Stage C: compare rebuilt 4H coverage vs whitelisted coverage_report.json.

coverage_report.json is the CHECK TARGET (hashed before use; expected
SHA-256 fdb6e33a1b2edde231e607f9c5cd8f33f82f2d8b82caaac473fc551c26faed2b).
Tolerance: documented missing-bar exceptions only (§5B).

Known systematic divergence (material finding, documented with cause):
the rebuilt cache starts 2024-09-30 (Yahoo 1H trailing-730d cap) while the
target expects 2023-10-26. This is NOT tuned around.

Output: canonical_stage_c/stage_c_comparison.json
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

WORKTREE = Path(__file__).resolve().parent.parent
STAGE_C = WORKTREE / "canonical_stage_c"
BASELINE = Path("/home/hatch/workspace/quality-flow-scanner-v5/canonical_baseline")
COVERAGE = BASELINE / "coverage_report.json"
EXPECT_HASH = "fdb6e33a1b2edde231e607f9c5cd8f33f82f2d8b82caaac473fc551c26faed2b"


def main():
    h = hashlib.sha256(COVERAGE.read_bytes()).hexdigest()
    assert h == EXPECT_HASH, f"coverage_report.json hash mismatch: {h}"
    target = json.loads(COVERAGE.read_text())
    summary = json.loads((STAGE_C / "build_4h_summary.json").read_text())
    mine = {s["symbol"]: s for s in summary["symbols"]}
    tmap = {e["symbol"]: e for e in target["symbols"]}

    comp = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "coverage_report_sha256": h,
        "target_half_days": target["half_days"],
        "target_single_bar_gaps": target["empirical_single_bar_gaps"],
        "per_symbol": [],
        "outsiders_no_target": [],
    }
    for sym, t in sorted(tmap.items()):
        m = mine.get(sym)
        if m is None:
            comp["per_symbol"].append({"symbol": sym, "finding": "not rebuilt"})
            continue
        comp["per_symbol"].append({
            "symbol": sym,
            "target_expected_4h": t["expected_4h"],
            "target_actual_4h": t["actual_4h"],
            "target_effective_4h_from": t["effective_4h_from"],
            "target_missing_pct": t["missing_pct"],
            "target_quality": t["quality"],
            "rebuilt_n_4h": m["n_4h"],
            "rebuilt_n_4h_from_effective": m["n_4h_from_effective"],
            "rebuilt_effective_rule": m["effective_rule"],
            "rebuilt_effective_4h_from": m["effective_4h_from"],
            "rebuilt_first_4h": m["first_4h"],
            "rebuilt_last_4h": m["last_4h"],
            "rebuilt_missing_pct_servable": m["missing_pct_servable"],
            "rebuilt_quality": m["quality"],
            "effective_from_match": m["effective_4h_from"] == t["effective_4h_from"],
            "bar_count_gap": t["actual_4h"] - m["n_4h"],
            "bar_count_gap_from_effective": t["actual_4h"] - m["n_4h_from_effective"],
        })
    for sym in sorted(mine):
        if sym not in tmap:
            m = mine[sym]
            comp["outsiders_no_target"].append({
                "symbol": sym, "n_4h": m["n_4h"],
                "effective_4h_from": m["effective_4h_from"],
                "missing_pct_servable": m["missing_pct_servable"],
                "quality": m["quality"],
            })

    exact_from = sum(1 for p in comp["per_symbol"]
                     if p.get("effective_from_match"))
    n = len(comp["per_symbol"])
    exact_count = sum(1 for p in comp["per_symbol"]
                      if p.get("bar_count_gap") == 0)
    comp["aggregate"] = {
        "n_compared": n,
        "effective_from_exact": exact_from,
        "bar_count_exact": exact_count,
        "mean_bar_count_gap": round(sum(p.get("bar_count_gap", 0)
                                        for p in comp["per_symbol"]) / n, 1) if n else None,
    }
    out = STAGE_C / "stage_c_comparison.json"
    out.write_text(json.dumps(comp, indent=2))
    print(f"compared {n}; effective_from exact: {exact_from}; "
          f"bar-count exact: {exact_count}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
