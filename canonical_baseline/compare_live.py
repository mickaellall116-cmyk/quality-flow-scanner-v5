"""Decision-packet comparison: canonical engine vs the live Mode B tracker.

Reads (never writes) the live forward-test state:
  v54_forward/state.json            — live tracker positions + processed bars
  v54_forward/forward_test.jsonl    — live event log (cross-check)

For each live position it replays the EXACT bar sequence the live tracker
processed (position["processed_bars"]) with the EXACT per-bar scanner_state
the harness fed it (v53_state_for_bar, imported read-only from
v54_forward_harness — the EXIT trigger is price-structure only, hence
regime-independent), then compares every decision the engine makes against
the live tracker's recorded decisions.

Run:  python3 compare_live.py   (from canonical_baseline/)
Writes: comparison_report.json
"""

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import v54_engine as eng  # noqa: E402  (frozen entry logic + data access; read-only)
from v54_forward_harness import v53_state_for_bar  # noqa: E402 (read-only import)
from canonical_baseline.modeb_engine import run_trade, LIVE_TO_CANONICAL  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(REPO, "v54_forward", "state.json")
LOG_PATH = os.path.join(REPO, "v54_forward", "forward_test.jsonl")
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "comparison_report.json")

_dl_cache = {}


def get_4h(symbol):
    if symbol not in _dl_cache:
        _dl_cache[symbol] = eng.m53.download_data(symbol, "4h", "180d")
    return _dl_cache[symbol]


def iso(ts):
    return pd.Timestamp(ts).isoformat()


def main():
    state = json.load(open(STATE_PATH))
    market = get_4h(eng.m53.MARKET_SYMBOL)
    regime = eng.m53.get_market_regime("4h", "180d")

    report = {"positions": [], "summary": {}}
    checks_total = checks_match = 0
    mismatches = []

    for sid, pos in state["positions"].items():
        sym = pos["symbol"]
        df = get_4h(sym)
        entry, stop, tp1 = pos["entry"], pos["stop"], pos["tp1"]
        entry_bar = pos["entry_bar"]
        processed = pos["processed_bars"]

        # Exact bar sequence the live tracker processed (chronological).
        try:
            idcs = [df.index.get_loc(pd.Timestamp(b)) for b in processed]
        except KeyError as e:
            report["positions"].append(
                {"signal_id": sid, "symbol": sym, "error":
                 f"bar {e} not in fresh download — skipped"})
            continue
        sub = df.iloc[idcs]
        bar_ids = [iso(b) for b in processed]

        # Entry-fill convention check: live entry == entry bar's open?
        entry_open = float(sub.iloc[0]["Open"])
        entry_fill_match = abs(entry_open - entry) < 1e-9

        # Per-bar scanner_state exactly as the harness fed it.
        states = [v53_state_for_bar(sym, df, market, regime, pd.Timestamp(b))
                  for b in processed]

        res = run_trade(0, entry, stop, tp1, sub,
                        scanner_states=states, realistic_gaps=False)
        res_real = run_trade(0, entry, stop, tp1, sub,
                             scanner_states=states, realistic_gaps=True)

        prec = {"signal_id": sid, "symbol": sym,
                "live_status": pos["status"],
                "entry_fill_matches_entry_bar_open": entry_fill_match,
                "bars_replayed": len(processed)}

        def check(name, live_val, eng_val, tol=None):
            nonlocal checks_total, checks_match
            checks_total += 1
            if tol is None:
                # In-flight mfe/mae: live stores the RAW value while open and
                # rounds to 4dp only in the exit record
                # (v54_exit_tracker.py:224-225); the engine rounds to 4dp
                # always. Allow half a rounding unit there.
                tol = 5e-5 if name in ("mfe_r", "mae_r") else 1e-9
            if live_val is None or eng_val is None:
                ok = live_val == eng_val
            elif isinstance(live_val, float) or isinstance(eng_val, float):
                ok = abs(float(live_val) - float(eng_val)) <= tol
            else:
                ok = live_val == eng_val
            if ok:
                checks_match += 1
            else:
                mismatches.append(
                    {"signal_id": sid, "symbol": sym, "field": name,
                     "live": live_val, "engine": eng_val})
            return ok

        # In-flight state (both open and closed positions record these).
        # In-flight state (both open and closed positions record these).
        check("bars_held", pos["bars_held"], res.bars_held)
        check("tp1_taken", pos["tp1_taken"], res.tp1_taken)
        check("plus_1r_armed", pos["plus_1r_armed"], res.pp_armed)
        check("plus_1r_bar",
              pos["plus_1r_bar"],
              iso(res.pp_arming_bar) if res.pp_arming_bar is not None else None)
        check("mfe_r", pos["mfe_r"], res.mfe_r)
        check("mae_r", pos["mae_r"], res.mae_r)

        if pos["status"] == "closed":
            lx = pos["exit"] or {}
            check("exit_live_reason", lx.get("reason"), res.live_reason)
            check("exit_canonical",
                  LIVE_TO_CANONICAL.get(lx.get("reason")), res.exit_reason)
            check("exit_bar", lx.get("exit_bar"),
                  iso(res.exit_bar) if res.exit_bar is not None else None)
            check("exit_px", lx.get("exit_px"), res.exit_px)
            check("blended_r", lx.get("blended_r"), res.blended_r)
            check("partial_r", lx.get("partial_r"), res.partial_r)
            check("runner_r", lx.get("runner_r"), res.runner_r)
            check("reached_plus_1r", lx.get("reached_plus_1r"),
                  res.reached_plus_1r)
            prec["live_exit"] = {k: lx.get(k) for k in
                                 ("reason", "exit_px", "exit_bar",
                                  "blended_r", "bars_held")}
        else:
            prec["live_open"] = {
                "status": pos["status"], "bars_held": pos["bars_held"],
                "tp1_taken": pos["tp1_taken"],
                "plus_1r_armed": pos["plus_1r_armed"],
                "mfe_r": round(pos["mfe_r"], 4),
                "mae_r": round(pos["mae_r"], 4)}

        # Engine's own account of the position (for the report).
        prec["engine"] = {
            "exit_reason": res.exit_reason, "live_reason": res.live_reason,
            "exit_bar": (iso(res.exit_bar)
                         if res.exit_bar is not None else None),
            "exit_px": res.exit_px, "blended_r": res.blended_r,
            "bars_held": res.bars_held, "tp1_taken": res.tp1_taken,
            "pp_armed": res.pp_armed,
            "pp_arming_bar": (iso(res.pp_arming_bar)
                              if res.pp_arming_bar is not None else None),
            "mfe_r": res.mfe_r, "mae_r": res.mae_r,
            "n_events": len(res.events)}

        # Realistic-gap quantification on the same bars.
        gap_diff = (res_real.exit_px != res.exit_px
                    or res_real.blended_r != res.blended_r
                    or res_real.tp1_fill_px != res.tp1_fill_px
                    or res_real.exit_reason != res.exit_reason)
        prec["realistic_gap_variant_differs"] = bool(gap_diff)
        if gap_diff:
            prec["realistic_gap_detail"] = {
                "exit_reason": res_real.exit_reason,
                "exit_px": res_real.exit_px,
                "blended_r": res_real.blended_r,
                "tp1_fill_px": res_real.tp1_fill_px,
                "live_blended_r": res.blended_r,
                "delta_r": round(res_real.blended_r - res.blended_r, 4)
                if (res_real.blended_r is not None
                    and res.blended_r is not None) else None}

        report["positions"].append(prec)

    report["summary"] = {
        "positions_compared": len(report["positions"]),
        "checks_total": checks_total,
        "checks_matched": checks_match,
        "match_rate": (round(checks_match / checks_total, 4)
                       if checks_total else None),
        "mismatches": mismatches,
        "entry_fill_convention_ok": all(
            p.get("entry_fill_matches_entry_bar_open", False)
            for p in report["positions"] if "error" not in p),
        "realistic_gap_diffs": sum(
            1 for p in report["positions"]
            if p.get("realistic_gap_variant_differs"))}

    with open(OUT_PATH, "w") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(json.dumps(report["summary"], indent=2))
    print("wrote", OUT_PATH)


if __name__ == "__main__":
    main()
