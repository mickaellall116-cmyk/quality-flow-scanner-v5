"""Deterministic sign fixtures for run_crt._manage (QF-CRT-SIGN-CORRECTION-20261013-01 r1).

Covers: long +1R, long -1R, short +1R, short -1R, TP1 blended exit (long).
Each case drives _manage to an exit on a synthetic 2-bar frame and checks the
blended R implied by the returned trade's synthetic exit price:
    implied_R = ((exit/entry) - 1) * d / risk_frac
On the ORIGINAL code (sign-inverted r1/r2) every case returns the negated R and
these assertions FAIL. On the corrected code they PASS.

Select which run_crt.py to test with env CRT_MODULE_DIR (directory containing
run_crt.py); defaults to this file's directory.
"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
MODDIR = os.environ.get("CRT_MODULE_DIR", HERE)
sys.path.insert(0, MODDIR)
import run_crt as rc  # noqa: E402

TOL = 1e-9


def make_df(bar0, bar1_open):
    idx = pd.to_datetime(["2026-01-05 09:30", "2026-01-05 13:30"])
    rows = [bar0, {"Open": bar1_open, "High": bar1_open, "Low": bar1_open,
                   "Close": bar1_open, "atr": 1.0, "e21": 0.0, "e55": 0.0,
                   "e200": 0.0}]
    return pd.DataFrame(rows, index=idx)


def run_case(entry, stop, d, bar0, exit_open):
    df = make_df(bar0, exit_open)
    pos = rc._open_pos(entry, stop, df, 0, 0, d)
    done, trade = rc._manage(pos, df, 0, len(df), "TEST")
    assert done and trade is not None, "fixture did not exit"
    risk_frac = (entry - stop) / entry * d
    implied_r = ((trade["exit"] / entry) - 1.0) * d / risk_frac
    return implied_r, trade


def bar(hi, lo, close, e21, e55, e200):
    return {"Open": close, "High": hi, "Low": lo, "Close": close,
            "atr": 1.0, "e21": e21, "e55": e55, "e200": e200}


CASES = []

# Long, entry 100 stop 95 (risk_frac 0.05), no TP1 (High 103 < tp1 106.67).
# Exit trigger: close 99 < e55 (and trend_bear). Next open sets the R.
CASES.append(("long +1R", 100.0, 95.0, 1,
              bar(103.0, 98.0, 99.0, 99.0, 100.5, 101.0), 105.0, 1.0, False))
CASES.append(("long -1R", 100.0, 95.0, 1,
              bar(103.0, 98.0, 99.0, 99.0, 100.5, 101.0), 95.0, -1.0, False))
# Short, entry 100 stop 105 (risk_frac 0.05), no TP1 (Low 97 > tp1 93.33).
# Exit trigger: close 101 > e55 (trend_bull). Next open sets the R.
CASES.append(("short +1R", 100.0, 105.0, -1,
              bar(102.0, 97.0, 101.0, 102.0, 99.5, 99.0), 95.0, 1.0, False))
CASES.append(("short -1R", 100.0, 105.0, -1,
              bar(102.0, 97.0, 101.0, 102.0, 99.5, 99.0), 105.0, -1.0, False))
# Long TP1 blended: High 107 >= tp1 106.6667 -> tp_hit, r1 = +1.3333R.
# Runner exits same logic; next open 102 -> r2 = +0.4R. Blend = 0.86667R.
CASES.append(("long TP1 blend", 100.0, 95.0, 1,
              bar(107.0, 98.0, 99.0, 99.0, 100.5, 101.0), 102.0,
              0.5 * (4.0 / 3.0) + 0.5 * 0.4, True))


def main():
    print(f"module under test: {rc.__file__}")
    failures = 0
    for name, entry, stop, d, b0, exit_open, expected, want_tp in CASES:
        got, trade = run_case(entry, stop, d, b0, exit_open)
        ok = abs(got - expected) < 1e-6 and trade["tp1_hit"] == want_tp
        print(f"{'PASS' if ok else 'FAIL'}  {name}: implied_R={got:+.6f} "
              f"expected={expected:+.6f} tp1_hit={trade['tp1_hit']}")
        failures += 0 if ok else 1
    print(f"{len(CASES) - failures}/{len(CASES)} fixtures passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
