#!/usr/bin/env python3
"""
test_tsla_completeness_check.py — SYNTHETIC FIXTURE (task -82, item 4).

Proves the independent single-series check separates three situations
the -75 C2 pairing check conflated:
  (a) clean uniformly-adjusted data            -> QUALIFIED_CLEAN
  (b) zero-volume price-moving bars            -> COMPLETENESS_FAIL,
      convention lane stays PASS (no 'INCONSISTENT convention' label)
  (c) a true convention break (mixed basis)   -> CONVENTION_BREAK_SUSPECT,
      completeness lane stays PASS
  (d) zero-volume FLAT (no-trade) bars         -> classified NO_TRADE_FLAT,
      NOT anomalies; series stays QUALIFIED_CLEAN

All bars are synthetic fixture arithmetic. No real symbol data is used;
the module name honors the repair item (the TSLA C2 finding), nothing
here is a TSLA measurement.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from tsla_completeness_check import run_check

NY = "America/New_York"
SESSIONS = {pd.Timestamp(d).date(): 16 * 60
            for d in ["2024-06-10", "2024-06-11", "2024-06-12", "2024-06-13"]}
SPLIT = [(pd.Timestamp("2024-06-12").date(), 3.0)]  # 3:1, effective 06-12


def build_series(mixed_basis=False, zero_vol_price_moving=0, flat_zero_vol=0):
    """Underlying raw price path: starts 300.00 pre-split, drifts +0.1%
    per bar; split 3:1 effective 2024-06-12 (raw level -> ~100).
    Adjusted (uniform) basis: pre-split prices / 3, volumes x 3.
    Mixed basis: pre-split prices left RAW (the defect in case (c))."""
    rows = []
    raw = 300.00
    for day_s, _close in [("2024-06-10", 16 * 60), ("2024-06-11", 16 * 60),
                          ("2024-06-12", 16 * 60), ("2024-06-13", 16 * 60)]:
        day = pd.Timestamp(day_s, tz=NY)
        pre = day_s < "2024-06-12"
        for k in range(7):  # full session: 09:30..15:30
            ts = day + pd.Timedelta(minutes=570 + 60 * k)
            if not pre and k == 0 and rows:
                raw = raw / 3.0  # split takes effect at the boundary
            o = raw
            c = raw * 1.001
            h, l = c * 1.0005, o * 0.9995
            v = 1000 + 10 * k
            if pre:
                if mixed_basis:
                    po, pc, ph, pl, pv = o, c, h, l, v * 3
                else:
                    po, pc, ph, pl, pv = o / 3, c / 3, h / 3, l / 3, v * 3
            else:
                po, pc, ph, pl, pv = o, c, h, l, v
            rows.append((ts, po, ph, pl, pc, pv))
            raw = c
    df = pd.DataFrame(rows, columns=["ts", "Open", "High", "Low", "Close", "Volume"])
    df = df.set_index("ts")
    if zero_vol_price_moving:
        pre_idx = df.index[df.index < pd.Timestamp("2024-06-12", tz=NY)][:zero_vol_price_moving]
        df.loc[pre_idx, "Volume"] = 0  # OHLC still moves -> defect class (b)
    if flat_zero_vol:
        some = df.index[10:10 + flat_zero_vol]
        for ts in some:
            px = df.loc[ts, "Open"]
            df.loc[ts, ["Open", "High", "Low", "Close", "Volume"]] = [px, px, px, px, 0]
    return df


RESULTS = []


def case(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")


def main():
    # (a) clean uniform adjustment
    r = run_check(build_series(), SESSIONS, SPLIT)
    case("A_clean_overall", r["overall"] == "QUALIFIED_CLEAN", r["overall"])
    case("A_clean_count", r["count"]["verdict"] == "PASS")
    case("A_clean_anomaly", r["anomaly"]["verdict"] == "PASS")
    case("A_clean_step", r["step"]["verdict"] == "PASS",
         str(r["step"]["results"]))

    # (b) zero-volume price-moving bars: completeness defect ONLY
    r = run_check(build_series(zero_vol_price_moving=5), SESSIONS, SPLIT)
    case("B_overall_completeness_fail", r["overall"] == "COMPLETENESS_FAIL", r["overall"])
    case("B_anomaly_count_is_5", len(r["anomaly"]["price_moving_zero_volume"]) == 5,
         str(len(r["anomaly"]["price_moving_zero_volume"])))
    case("B_convention_lane_untouched", r["convention_verdict"] == "PASS",
         r["convention_verdict"])
    case("B_count_lane_pass", r["count"]["verdict"] == "PASS")

    # (c) mixed basis: convention break ONLY
    r = run_check(build_series(mixed_basis=True), SESSIONS, SPLIT)
    case("C_overall_convention_suspect", r["overall"] == "CONVENTION_BREAK_SUSPECT",
         r["overall"])
    case("C_step_observed_near_reciprocal_factor",
         abs(r["step"]["results"][0]["observed_step"] - 1 / 3.0) < 0.02,
         str(r["step"]["results"][0]["observed_step"]))
    case("C_completeness_lane_untouched", r["completeness_verdict"] == "PASS",
         r["completeness_verdict"])

    # (d) flat zero-volume bars are no-trade facts, not anomalies
    r = run_check(build_series(flat_zero_vol=2), SESSIONS, SPLIT)
    case("D_overall_still_clean", r["overall"] == "QUALIFIED_CLEAN", r["overall"])
    case("D_flat_classified_separately",
         len(r["anomaly"]["no_trade_flat_zero_volume"]) == 2
         and len(r["anomaly"]["price_moving_zero_volume"]) == 0,
         f"flat={len(r['anomaly']['no_trade_flat_zero_volume'])}")

    # (e) count lane catches a missing bar (extra evidence the lanes work)
    df = build_series().drop(pd.Timestamp("2024-06-11 11:30", tz=NY))
    r = run_check(df, SESSIONS, SPLIT)
    case("E_missing_bar_count_fail", r["count"]["verdict"] == "FAIL"
         and len(r["count"]["missing_bars"]) == 1, str(r["count"]["missing_bars"]))

    n_pass = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\n{n_pass}/{len(RESULTS)} checks passed")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
