"""P9 — Executable ledger-parity verifier (semantic pin, -30).

QF-EQUITY43-DEV-MEASUREMENT-FIXES-20261025-30.

Turns the -27 §3 parity proof into a standing executable artifact:
recompute every headline figure from the committed -13 candidate
ledger (trade_ledger.json, sha256 267e794c…) and diff against
results.json's P5_run rows. The -27 gap is closed in the form the
-29 reconciliation established: EACH cost view is recomputed over
its OWN taken set (the ledger carries per-view taken flags and R
columns), so the 25bps row (185 closed @ +0.107509R) reproduces
exactly instead of colliding with the 4bps taken set's 25bps column
(187 @ +0.10753R). Parity claims are scoped to the frozen DEV cost
convention (a single flat per-trade charge on entry notional);
total_return_pct and max_drawdown_pct are NOT ledger-recomputable
(they need the equity path) and are carried as reported, never
verified here — the all-bar DD is the -29/-29r P1 lane's artifact.

Comparisons use the results rows' own rounding: a recomputed figure
matches when it rounds (to the row's displayed precision) to the
row's value; sums and counts must be exact.
"""
import json
import os

VIEWS = {
    "gross": {"taken": "taken_gross", "r": "gross_r"},
    "4bps": {"taken": "taken_4bps", "r": "net_r_4bps"},
    "25bps": {"taken": "taken_25bps", "r": "net_r_25bps"},
}


def _repo_root():
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def recompute(ledger, view):
    spec = VIEWS[view]
    taken = [r for r in ledger if r[spec["taken"]]]
    closed = [r for r in taken if not r["censored"]]
    rs = [r[spec["r"]] for r in closed]
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    return {
        "taken": len(taken),
        "closed": len(closed),
        "censored_symbols": sorted(r["symbol"] for r in taken
                                   if r["censored"]),
        "sum_r": sum(rs),
        "mean_r": sum(rs) / len(rs) if rs else 0.0,
        "profit_factor": (sum(wins) / abs(sum(losses))) if losses
        else float("inf"),
        "win_rate_pct": 100.0 * len(wins) / len(rs) if rs else 0.0,
        "avg_hold_bars": (sum(r["hold_bars"] for r in closed)
                          / len(closed)) if closed else 0.0,
    }


def parity_report():
    root = _repo_root()
    base = os.path.join(
        root, "research_notes", "equity43_dev_order_censor_20261023_13")
    ledger = json.load(open(os.path.join(base, "trade_ledger.json")))
    results = json.load(open(os.path.join(base, "results.json")))
    rows = results["phases"]["P5_run"]
    out = {"ledger_rows": len(ledger), "views": {}, "checks": []}

    def chk(name, cond, detail=""):
        out["checks"].append({"name": name, "pass": bool(cond),
                              "detail": detail})
        return cond

    ok = True
    for view in VIEWS:
        rec = recompute(ledger, view)
        row = rows[view]
        out["views"][view] = {"recomputed": rec,
                              "results_row": {
                                  k: row[k] for k in (
                                      "trades", "closed_trades",
                                      "expectancy_net_r",
                                      "profit_factor", "win_rate_pct",
                                      "avg_hold_bars",
                                      "terminal_open_taken_count")}}
        ok &= chk(f"{view}: candidates_available == ledger rows",
                  row["candidates_available"] == len(ledger))
        ok &= chk(f"{view}: closed trades exact",
                  rec["closed"] == row["closed_trades"]
                  and rec["closed"] == row["trades"],
                  f"{rec['closed']} vs {row['closed_trades']}")
        ok &= chk(f"{view}: censored count exact",
                  rec["taken"] - rec["closed"]
                  == row["terminal_open_taken_count"])
        ok &= chk(f"{view}: expectancy matches at row rounding",
                  round(rec["mean_r"], 3) == row["expectancy_net_r"],
                  f"{rec['mean_r']:.6f} vs {row['expectancy_net_r']}")
        ok &= chk(f"{view}: profit factor matches at row rounding",
                  round(rec["profit_factor"], 2)
                  == row["profit_factor"],
                  f"{rec['profit_factor']:.4f} vs "
                  f"{row['profit_factor']}")
        ok &= chk(f"{view}: win rate matches at row rounding",
                  round(rec["win_rate_pct"], 1) == row["win_rate_pct"],
                  f"{rec['win_rate_pct']:.2f} vs {row['win_rate_pct']}")
        ok &= chk(f"{view}: avg hold matches at row rounding",
                  round(rec["avg_hold_bars"], 1)
                  == row["avg_hold_bars"],
                  f"{rec['avg_hold_bars']:.3f} vs "
                  f"{row['avg_hold_bars']}")

    # The 4bps C1 disposition census (the -27 §3 table's naming map:
    # ledger skipped_rank == results skipped_max_positions on the
    # C1 view; sector skips are inside the ledger's skipped_gate).
    from collections import Counter
    disp = Counter(r["disposition_4bps_c1"] for r in ledger)
    row4 = rows["4bps"]
    out["dispositions_4bps_c1"] = dict(disp)
    ok &= chk("4bps: disposition census sums to the ledger",
              sum(disp.values()) == len(ledger))
    ok &= chk("4bps: taken == results terminal accounting",
              disp["taken"] == row4["closed_trades"]
              + row4["terminal_open_taken_count"])
    ok &= chk("4bps: skipped_rank == results skipped_max_positions "
              "(naming map, -27 §3)",
              disp["skipped_rank"] == row4["skipped_max_positions"],
              f"{disp['skipped_rank']} vs "
              f"{row4['skipped_max_positions']}")
    ok &= chk("4bps: skipped_risk == results skipped_max_risk",
              disp["skipped_risk"] == row4["skipped_max_risk"])
    closed4 = [r for r in ledger
               if r["taken_4bps"] and not r["censored"]]
    top5 = sum(sorted((r["net_r_4bps"] for r in closed4),
                      reverse=True)[:5])
    total4 = sum(r["net_r_4bps"] for r in closed4)
    out["top5_share_4bps"] = {"top5_r": top5, "total_r": total4,
                              "share_pct": 100.0 * top5 / total4,
                              "recorded": "94.3753% (-27 §3)"}
    ok &= chk("4bps: top-5 share reproduces the -27 §3 figure",
              abs(100.0 * top5 / total4 - 94.3753) < 0.01,
              f"{100.0 * top5 / total4:.4f}%")
    out["carried_not_verified"] = [
        "total_return_pct and max_drawdown_pct are not "
        "ledger-recomputable (equity path required); carried as "
        "reported in results.json. The all-bar DD is the -29/-29r "
        "P1 artifact (4bps 26.183969%).",
        "Parity is scoped to the frozen DEV cost convention "
        "(flat per-trade charge on entry notional).",
    ]
    out["verdict"] = "PASS" if ok else "FAIL"
    return out


def main():
    rep = parity_report()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "artifacts", "p9_parity.json")
    with open(out, "w") as f:
        json.dump(rep, f, indent=1)
        f.write("\n")
    print(f"WROTE {out}")
    for c in rep["checks"]:
        print(("PASS" if c["pass"] else "FAIL"), c["name"], c["detail"])
    print("VERDICT", rep["verdict"])
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
