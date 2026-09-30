#!/usr/bin/env python3
"""Stage C: compare rebuilt 4H coverage vs whitelisted coverage_report.json.

coverage_report.json is the CHECK TARGET (hashed before use; expected
SHA-256 fdb6e33a1b2edde231e607f9c5cd8f33f82f2d8b82caaac473fc551c26faed2b).

§5B GATE (audit-repaired, round 2):
  - The PRIMARY comparison is target_expected_4h vs
    rebuilt_n_4h_from_effective. UNIVERSE.md defines expected 4H bars inside
    the eligible/effective window (new listings: 60th 4H bar), so the total
    raw cache count is NOT comparable -- it is recorded informational only.
  - Every nonzero primary gap gets an explicit mechanical classification:
      exact                        gap == 0
      allowed_start_shift          gap == effective-date shift, within ±5td
      frozen_yahoo_gap_day_effect  residual after the shift == the frozen
                                   target's own expected-vs-actual accounting
      ticker_specific_availability documented per-symbol Yahoo availability
                                   finding (see TICKER_SPECIFIC_AVAILABILITY;
                                   admitted 60th-bar listings with a ±1 bar
                                   inventory difference vs target actual)
      unclassified_finding         anything else -- STOPS THE STAGE
  - Mechanical identity the classifier checks per symbol:
      rebuilt_from_effective == target_actual_4h - shift_bars + delta
    shift_bars = 4H sessions in [target_effective_from, rebuilt_effective_from)
    (2/session-day, 1 on NYSE half days; SPY daily calendar). delta is the
    residual our rebuild introduces vs the target's actual inventory.

Run isolation (R2): --run-dir selects the run's directory
(default canonical_stage_c = Run 1 layout; Run 2 uses
canonical_stage_c/run2). Reads <run>/build_4h_summary.json, writes
<run>/stage_c_comparison.json.

Output: <run>/stage_c_comparison.json
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

WORKTREE = Path(__file__).resolve().parent.parent
STAGE_C = WORKTREE / "canonical_stage_c"
BASELINE = Path("/home/hatch/workspace/quality-flow-scanner-v5/canonical_baseline")
COVERAGE = BASELINE / "coverage_report.json"
EXPECT_HASH = "fdb6e33a1b2edde231e607f9c5cd8f33f82f2d8b82caaac473fc551c26faed2b"
STAGE_A_DATA = WORKTREE / "canonical_stage_a" / "data"

# ±5 trading days x 2 sessions/day: the §5B start-shift tolerance in bars.
START_SHIFT_TOL_BARS = 10

# Documented ticker-specific Yahoo availability findings (Run 1 report).
# A symbol listed here is classified ticker_specific_availability: its whole
# effective-window configuration derives from the documented cause.
TICKER_SPECIFIC_AVAILABILITY = {
    "GEV": "Yahoo 1H history bounded at 2024-09-30 for this ticker "
           "(period=730d server-errors; recovered via same-endpoint period=max); "
           "60th-bar effective date derived from truncated history",
    "RDDT": "Yahoo 1H history bounded at 2024-09-30 for this ticker "
            "(period=730d server-errors; recovered via same-endpoint period=max); "
            "60th-bar effective date derived from truncated history",
    "TEM": "Yahoo 1H history bounded at 2024-09-30 for this ticker "
           "(period=730d server-errors; recovered via same-endpoint period=max); "
           "60th-bar effective date derived from truncated history",
    "TMO": "Yahoo 1H history available from 2023-11-08 only; "
           "effective window starts 2023-11-08 (ticker-specific availability)",
    "TLT": "one documented NaN 1H bar in Run 1 (ticker-specific availability)",
}

# The 11 admitted new listings (Stage-A recomputed eval): effective 4H
# eligibility = 60th 4H bar. A ±1 bar inventory difference vs the target's
# actual inside a matched effective window is a ticker-specific availability
# finding for these symbols, not an unclassified divergence.
ADMITTED_60TH = {"ARM", "BMNR", "CRWV", "DRAM", "GEV", "GLXY", "NBIS",
                 "RDDT", "SNDK", "SPCX", "TEM"}


def parse_args():
    p = argparse.ArgumentParser(description="Stage C §5B comparator")
    p.add_argument("--run-dir", default=os.environ.get("CANONICAL_RUN_DIR"),
                   help="run-specific directory; default canonical_stage_c (Run 1 layout)")
    return p.parse_args()


def trading_days_all():
    """All SPY daily dates (Stage-A fresh daily cache, own output)."""
    spy = json.loads((STAGE_A_DATA / "d1_SPY.json").read_text())
    di = spy["columns"].index("date")
    return sorted(date.fromisoformat(r[di][:10]) for r in spy["rows"])


def shift_bars(tgt_from, reb_from, days, half_days):
    """Signed 4H sessions in [tgt_from, reb_from): 2 per day, 1 on halves."""
    a, b = date.fromisoformat(tgt_from), date.fromisoformat(reb_from)
    n = 0
    for d in days:
        if a <= d < b:
            n += 1 if d.isoformat() in half_days else 2
        elif b <= d < a:
            n -= 1 if d.isoformat() in half_days else 2
    return n


def classify(sym, gap, shift, exp_minus_act, delta):
    """Return (classification, components). Every nonzero gap is classified;
    anything not mechanically explained is unclassified_finding."""
    comp = {
        "shift_bars": shift,
        "shift_within_tol": abs(shift) <= START_SHIFT_TOL_BARS,
        "target_expected_minus_actual": exp_minus_act,
        "residual_delta_vs_target_actual": delta,
    }
    if gap == 0:
        return "exact", comp
    if sym in TICKER_SPECIFIC_AVAILABILITY:
        comp["cause"] = TICKER_SPECIFIC_AVAILABILITY[sym]
        return "ticker_specific_availability", comp
    if delta != 0:
        if sym in ADMITTED_60TH and abs(delta) == 1:
            comp["cause"] = ("admitted 60th-bar listing: single-bar inventory "
                             "difference vs target actual inside a matched "
                             "effective window")
            return "ticker_specific_availability", comp
        comp["cause"] = (f"residual {delta:+d} bars vs target actual (shift-adjusted) "
                         "with no documented per-symbol cause")
        return "unclassified_finding", comp
    # delta == 0: rebuilt == target actual, shift-adjusted.
    if not comp["shift_within_tol"]:
        comp["cause"] = (f"effective-date shift {shift} bars exceeds "
                         f"±5td tolerance ({START_SHIFT_TOL_BARS} bars)")
        return "unclassified_finding", comp
    if gap == shift:
        return "allowed_start_shift", comp
    if gap == shift + exp_minus_act:
        comp["cause"] = ("non-shift part of the gap is exactly the frozen "
                         "target's own expected-vs-actual accounting")
        return "frozen_yahoo_gap_day_effect", comp
    comp["cause"] = "gap not explained by shift and frozen target accounting"
    return "unclassified_finding", comp


def main():
    args = parse_args()
    RUN = Path(args.run_dir) if args.run_dir else STAGE_C

    h = hashlib.sha256(COVERAGE.read_bytes()).hexdigest()
    assert h == EXPECT_HASH, f"coverage_report.json hash mismatch: {h}"
    target = json.loads(COVERAGE.read_text())
    summary = json.loads((RUN / "build_4h_summary.json").read_text())
    mine = {s["symbol"]: s for s in summary["symbols"]}
    tmap = {e["symbol"]: e for e in target["symbols"]}
    days = trading_days_all()
    half_days = set(target["half_days"])

    comp = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(RUN),
        "coverage_report_sha256": h,
        "target_half_days": target["half_days"],
        "target_single_bar_gaps": target["empirical_single_bar_gaps"],
        "classifier": ("primary gap = expected_4h - rebuilt_n_4h_from_effective; "
                       "total raw cache count informational only"),
        "per_symbol": [],
        "outsiders_no_target": [],
    }
    for sym, t in sorted(tmap.items()):
        m = mine.get(sym)
        if m is None:
            comp["per_symbol"].append({"symbol": sym, "finding": "not rebuilt",
                                       "gap_classification": "unclassified_finding"})
            continue
        gap = t["expected_4h"] - m["n_4h_from_effective"]
        shift = shift_bars(t["effective_4h_from"], m["effective_4h_from"],
                           days, half_days)
        exp_minus_act = t["expected_4h"] - t["actual_4h"]
        delta = m["n_4h_from_effective"] - (t["actual_4h"] - shift)
        cls, components = classify(sym, gap, shift, exp_minus_act, delta)
        comp["per_symbol"].append({
            "symbol": sym,
            "target_expected_4h": t["expected_4h"],
            "target_actual_4h": t["actual_4h"],
            "target_effective_4h_from": t["effective_4h_from"],
            "target_missing_pct": t["missing_pct"],
            "target_quality": t["quality"],
            "rebuilt_n_4h_from_effective": m["n_4h_from_effective"],
            "rebuilt_n_4h_total_raw": m["n_4h"],
            "rebuilt_effective_rule": m["effective_rule"],
            "rebuilt_effective_4h_from": m["effective_4h_from"],
            "rebuilt_first_4h": m["first_4h"],
            "rebuilt_last_4h": m["last_4h"],
            "rebuilt_missing_pct_servable": m["missing_pct_servable"],
            "rebuilt_quality": m["quality"],
            "effective_from_match": m["effective_4h_from"] == t["effective_4h_from"],
            # PRIMARY §5B gate quantity:
            "bar_count_gap": gap,
            # informational only:
            "bar_count_gap_total_raw": t["expected_4h"] - m["n_4h"],
            "gap_classification": cls,
            "gap_components": components,
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

    n = len(comp["per_symbol"])
    counts = {}
    for p in comp["per_symbol"]:
        c = p.get("gap_classification", "unclassified_finding")
        counts[c] = counts.get(c, 0) + 1
    stop_syms = [p["symbol"] for p in comp["per_symbol"]
                 if p.get("gap_classification") == "unclassified_finding"]
    comp["aggregate"] = {
        "n_compared": n,
        "effective_from_exact": sum(1 for p in comp["per_symbol"]
                                    if p.get("effective_from_match")),
        "bar_count_exact": counts.get("exact", 0),
        "mean_bar_count_gap": round(sum(p["bar_count_gap"]
                                        for p in comp["per_symbol"]) / n, 1) if n else None,
        "classification_counts": counts,
        "gate_c_stop": bool(stop_syms),
        "gate_c_stop_symbols": stop_syms,
    }
    out = RUN / "stage_c_comparison.json"
    out.write_text(json.dumps(comp, indent=2))
    print(f"compared {n} in {RUN}; classifications: {counts}")
    print(f"-> {out}")
    if stop_syms:
        print(f"GATE C STOP: unclassified findings: {stop_syms}")
        sys.exit(1)
    print("gate C: no unclassified findings")


if __name__ == "__main__":
    main()
