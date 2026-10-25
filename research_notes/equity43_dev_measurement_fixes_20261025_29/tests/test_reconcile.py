"""Reconciliation test: runs the per-view extraction against the
committed -13 artifacts in this repository (no stage assets needed) and
asserts the headlines, incl. the 25 bps view reproducing exactly.

Run from the package dir: python3 tests/test_reconcile.py
"""
import json
import os
import sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.abspath(os.path.join(PKG, "..", ".."))
sys.path.insert(0, os.path.join(PKG, "code"))
import reconcile_per_view as rc  # noqa: E402

LEDGER = os.path.join(
    REPO, "research_notes", "equity43_dev_order_censor_20261023_13",
    "trade_ledger.json")
RESULTS = os.path.join(
    REPO, "research_notes", "equity43_dev_order_censor_20261023_13",
    "results.json")

FAILURES = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        FAILURES.append(name)


def main():
    ledger = json.load(open(LEDGER))
    results = json.load(open(RESULTS))
    s = rc.reconcile(ledger, results)
    check("gross view: 191 taken / 188 closed",
          s["gross"]["taken"] == 191 and s["gross"]["closed"] == 188)
    check("4bps view: 191 taken / 187 closed / +0.17373R",
          s["4bps"]["taken"] == 191 and s["4bps"]["closed"] == 187
          and s["4bps"]["mean_r"] == 0.17373)
    check("25bps view: 189 taken / 185 closed / +0.10751R / PF 1.166 "
          "/ win 47.0",
          s["25bps"]["taken"] == 189 and s["25bps"]["closed"] == 185
          and s["25bps"]["mean_r"] == 0.10751
          and s["25bps"]["profit_factor"] == 1.166
          and s["25bps"]["win_rate_pct"] == 47.0)
    check("all views match results.json rows",
          all(all(v["match"].values()) for v in
              (s["gross"], s["4bps"], s["25bps"])))
    check("wrong-subset diagnostic reproduces -27 figure "
          "(187 @ +0.10753R)",
          s["wrong_subset_diagnostic"]["closed"] == 187
          and s["wrong_subset_diagnostic"]["mean_net_r_25bps"] == 0.10753)
    cc = s["cost_convention_check"]
    check("flat per-trade cost identity holds on every closed record",
          cc["violations"] == 0 and cc["records_checked"] == 2 * 586,
          f"checked={cc['records_checked']} violations={cc['violations']}")
    print("SUMMARY", "FAIL" if FAILURES else "PASS", FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
