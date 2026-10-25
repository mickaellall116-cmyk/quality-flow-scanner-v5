"""Per-cost-view reconciliation of the -13 DEV ledger (185 vs 187).

QF-EQUITY43-DEV-MEASUREMENT-FIXES-20261025-29, reconciliation item.

Finding (from the pinned artifacts only; no strategy re-run): the -13
driver's phase5 wrote ONE candidate ledger whose rows carry per-view
taken flags (`taken_gross`, `taken_4bps`, `taken_25bps`) because each
cost view ran its own portfolio path (costs feed the marked-equity path
the risk gate reads, so the taken sets genuinely diverge in both
directions). results.json's 25 bps row (185 closed trades, expectancy
0.108) describes the 25 bps view's OWN taken set. The -27 §3
recomputation summed the ledger's `net_r_25bps` column over the 4 bps
taken set — the wrong subset — and got 187 trades @ +0.10753R, which
made the 25 bps headline look irreproducible. Extracting by the
`taken_25bps` flag reproduces the headline exactly: 189 taken, 185
closed, mean net_r_25bps = +0.10751R, PF 1.17, win 47.0%.

This script performs the per-view extraction from the committed ledger
and emits one ledger artifact per view plus a summary with the
comparison against results.json. It also verifies the frozen DEV cost
convention on every closed record: net_r == gross_r - cost / risk_frac
(a single flat per-trade charge on entry notional, `_outcome`,
pine_backtest.py:214-218 — not per-fill).

Usage: python3 reconcile_per_view.py <ledger.json> <results.json> <outdir>
"""
import json
import os
import sys

VIEWS = {
    "gross": ("taken_gross", "gross_r", 0.0),
    "4bps": ("taken_4bps", "net_r_4bps", 0.0004),
    "25bps": ("taken_25bps", "net_r_25bps", 0.0025),
}
COST_CONVENTION = (
    "frozen DEV convention: a single flat per-trade charge of the view's "
    "bps on entry notional, applied once per trade in _outcome "
    "(pine_backtest.py:214-218); NOT per-fill and NOT on exit notional")


def summarize(records, rkey):
    closed = [r for r in records if not r["censored"]]
    vals = [r[rkey] for r in closed]
    pos = sum(v for v in vals if v > 0)
    neg = -sum(v for v in vals if v < 0)
    return {
        "taken": len(records),
        "closed": len(closed),
        "censored_symbols": sorted(r["symbol"] for r in records
                                   if r["censored"]),
        "sum_r": round(sum(vals), 4),
        "mean_r": round(sum(vals) / len(vals), 5) if vals else None,
        "profit_factor": round(pos / neg, 3) if neg else None,
        "win_rate_pct": round(100.0 * sum(1 for v in vals if v > 0)
                              / len(vals), 1) if vals else None,
    }


def reconcile(ledger, results):
    out = {}
    views = results["phases"]["P5_run"]
    for name, (flag, rkey, _c) in VIEWS.items():
        records = [r for r in ledger if r[flag]]
        s = summarize(records, rkey)
        row = views[name]
        s["results_json_row"] = {
            "trades": row["trades"],
            "expectancy_net_r": row["expectancy_net_r"],
            "profit_factor": row["profit_factor"],
            "win_rate_pct": row["win_rate_pct"],
            "max_drawdown_pct": row["max_drawdown_pct"],
            "final_equity": row["final_equity"],
        }
        s["match"] = {
            "trades_exact": s["closed"] == row["trades"],
            "expectancy_within_rounding":
                abs(s["mean_r"] - row["expectancy_net_r"]) <= 0.0006,
            "pf_within_rounding":
                abs(s["profit_factor"] - row["profit_factor"]) <= 0.006,
            "win_within_rounding":
                abs(s["win_rate_pct"] - row["win_rate_pct"]) <= 0.051,
        }
        out[name] = s
    # The -27 wrong-subset figure, reproduced for the record.
    wrong = [r for r in ledger
             if r["taken_4bps"] and not r["censored"]]
    out["wrong_subset_diagnostic"] = {
        "description": "net_r_25bps summed over the 4bps taken set "
                       "(the -27 §3 recomputation)",
        "closed": len(wrong),
        "mean_net_r_25bps": round(
            sum(r["net_r_25bps"] for r in wrong) / len(wrong), 5),
    }
    # Cost-convention identity on every closed record.
    viol = 0
    checked = 0
    for r in ledger:
        if r["censored"]:
            continue
        risk_frac = (r["entry"] - r["stop"]) / r["entry"]
        for cost, nk in ((0.0004, "net_r_4bps"), (0.0025, "net_r_25bps")):
            checked += 1
            if abs(r[nk] - (r["gross_r"] - cost / risk_frac)) > 0.0011:
                viol += 1
    out["cost_convention_check"] = {
        "convention": COST_CONVENTION, "records_checked": checked,
        "violations": viol}
    return out


def main():
    ledger_path, results_path, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    ledger = json.load(open(ledger_path))
    results = json.load(open(results_path))
    import hashlib
    src_hash = hashlib.sha256(open(ledger_path, "rb").read()).hexdigest()
    summary = reconcile(ledger, results)
    os.makedirs(outdir, exist_ok=True)
    for name, (flag, _rk, _c) in VIEWS.items():
        records = [r for r in ledger if r[flag]]
        with open(os.path.join(outdir, f"ledger_{name}.json"), "w") as f:
            json.dump({
                "view": name,
                "source": "extracted from the committed -13 candidate "
                          "ledger by the view's taken flag; records "
                          "verbatim, no strategy re-run",
                "source_ledger_sha256": src_hash,
                "cost_convention": COST_CONVENTION,
                "records": records}, f, indent=1)
    with open(os.path.join(outdir, "per_view_summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    ok = all(all(s["match"].values()) for s in summary.values()
             if isinstance(s, dict) and "match" in s) \
        and summary["cost_convention_check"]["violations"] == 0
    print(json.dumps(summary, indent=1))
    print("RECONCILE", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
