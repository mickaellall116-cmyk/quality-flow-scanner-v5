"""29r DEV regeneration harness: P1 series under repaired binning.

Re-runs ONLY the measurement layer on the -29 lane's recorded inputs
(pipeline.pkl: canonical trades, closes, feats, cutoff — the strategy
/ signal generation is NOT re-run):
  A) repaired all-bar fork vs frozen baseline per cost view —
     decisions identical, event track == committed results.json,
     interval reconstruction cross-check (as in -29), PLUS the repair
     checks: every bar_close stamp is a pinned session-table bin end
     (census by end wall time), and the regenerated all-bar DD is
     compared against the -29 held series (recomputed from the
     committed -29 equity_series_allbar.json values).
  B) repaired fork swapped through the driver's phase5 -> the trade
     ledger must stay byte-identical (sha 267e794c…) and the views
     may differ only in max_drawdown_pct (verdict item 4).
Writes artifacts into the 29r package.
"""
import hashlib
import json
import os
import pickle
import sys
from collections import Counter

SRC_STAGE = os.path.expanduser("~/workspace/qf_fix29_stage")
HOME = os.path.join(SRC_STAGE, "home")
PKG = os.path.expanduser(
    "~/workspace/qf_fix29r_stage/wt/research_notes/"
    "equity43_dev_measurement_fixes_20261025_29r")
PKG29 = os.path.expanduser(
    "~/workspace/qf_fix29r_stage/wt/research_notes/"
    "equity43_dev_measurement_fixes_20261025_29")
os.environ["QF_OUT"] = os.path.expanduser(
    "~/workspace/qf_fix29r_stage/out_fork")
os.chdir(HOME)
sys.path.insert(0, HOME)
sys.path.insert(0, os.path.join(PKG, "code"))

import run_study13 as drv  # noqa: E402
import pine_backtest as pb  # noqa: E402
import pine_stack as st  # noqa: E402
from pine_exposure import SECTOR  # noqa: E402
import mtm_allbar  # noqa: E402
import session_bins  # noqa: E402

FAILS = []
CHECKS = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}", flush=True)
    CHECKS.append({"name": name, "pass": bool(cond),
                   "detail": str(detail)})
    if not cond:
        FAILS.append(name)


def main():
    with open(os.path.join(SRC_STAGE, "work", "pipeline.pkl"),
              "rb") as f:
        P = pickle.load(f)
    closes = P["closes"]
    canonical, feats = P["canonical"], P["feats"]
    skipped_gap, cutoff = P["skipped_gap"], P["cutoff"]
    committed = json.load(open(os.path.join(
        SRC_STAGE, "work", "committed_results.json")))
    rs_map = {id(tr): feats[i]["rs"] for i, tr in enumerate(canonical)}

    # Held -29 figures, recomputed from the committed -29 series
    # values (exact, independent of the -29 memo's rounding).
    held_series = json.load(open(os.path.join(
        PKG29, "artifacts", "equity_series_allbar.json")))
    held = {}
    for cn, ser in held_series.items():
        peak, dd = -1.0, 0.0
        for _t, e, _k in ser:
            peak = max(peak, e)
            dd = max(dd, (peak - e) / peak if peak > 0 else 0.0)
        held[cn] = {"dd": dd, "points": len(ser)}

    # The full set of legitimate bar_close stamps: every pinned bin
    # end of every DEV session, as the fork prints them.
    table = session_bins.load_pinned_table()
    legit = set()
    for date in sorted({str(t)[:10] for s in closes.values()
                        for t in s.index}):
        for _st, en in table.bins_for_date(date):
            legit.add(str(en))

    views, ports = drv.run_views(canonical, closes, feats, skipped_gap,
                                 cutoff)
    mtm = {"method": "all-bar marked equity on the union 4H calendar; "
                     "bar completions = pinned 751-session-table "
                     "bin_end (29r repair of the -29 +4h arithmetic); "
                     "frozen marked_equity valuation; decisions from "
                     "the identical event-time logic (dd_gate=False)",
           "session_table_sha256": session_bins.PINNED_TABLE_SHA256,
           "views": {}}
    series_out = {}
    for cn in ("gross", "4bps", "25bps"):
        cost = pb.COSTS[cn] if cn in pb.COSTS else 0.0
        base = ports[cn]
        fork = mtm_allbar.simulate_stack_allbar(
            canonical, closes, cost, True, True, False, SECTOR,
            cutoff=cutoff, pb=pb, rs_map=rs_map)
        same = (fork["taken"] == base["taken"]
                and fork["disposition"] == base["disposition"]
                and fork["exit_cashflows"] == base["exit_cashflows"]
                and fork["final_equity"] == base["final_equity"]
                and fork["realized_equity"] == base["realized_equity"]
                and fork["terminal_open"] == base["terminal_open"]
                and fork["exposure"] == base["exposure"]
                and fork["skipped_rank"] == base["skipped_rank"]
                and fork["skipped_risk"] == base["skipped_risk"]
                and fork["skipped_gate"] == base["skipped_gate"]
                and fork["skipped_cap"] == base["skipped_cap"])
        check(f"A {cn}: fork decisions/outputs identical to frozen",
              same)
        ev_dd = base["max_drawdown"]
        check(f"A {cn}: fork event track == frozen max_drawdown",
              abs(fork["event_sampled_max_drawdown"] - ev_dd) < 1e-12,
              f"{fork['event_sampled_max_drawdown']} vs {ev_dd}")
        rep = committed["phases"]["P5_run"][cn]["max_drawdown_pct"]
        check(f"A {cn}: event track == committed results.json",
              abs(round(100 * ev_dd, 2) - rep) < 1e-9,
              f"{round(100 * ev_dd, 2)} vs {rep}")
        cf = {tuple(e["key"]): e for e in fork["exit_cashflows"]}
        positions = []
        for idx in fork["taken"]:
            tr = canonical[idx]
            key = (tr["symbol"], tr["signal_idx"])
            if tr.get("censored"):
                term = [x for x in fork["terminal_open"]
                        if x["symbol"] == tr["symbol"]][0]
                positions.append({
                    "symbol": tr["symbol"], "entry": tr["entry"],
                    "entry_time": tr["entry_time"], "exit_time": None,
                    "size": term["size"], "exit_cash_flow": None})
            else:
                e = cf[key]
                rf = (tr["entry"] - tr["stop"]) / tr["entry"]
                positions.append({
                    "symbol": tr["symbol"], "entry": tr["entry"],
                    "entry_time": tr["entry_time"],
                    "exit_time": tr["exit_time"],
                    "size": e["risk_dollars"] / rf,
                    "exit_cash_flow": e["cash_flow"]})
        first_t = min([t["entry_time"] for t in canonical]
                      + [t["exit_time"] for t in canonical
                         if not t.get("censored")])
        iser, idd = mtm_allbar.equity_series_from_intervals(
            positions, closes, pb.START_EQUITY, first_t, cutoff)
        check(f"A {cn}: interval reconstruction DD == fork all-bar DD",
              abs(idd - fork["allbar_max_drawdown"]) < 1e-9,
              f"{idd} vs {fork['allbar_max_drawdown']}")
        fork_bc = {}
        for t, e, k in fork["allbar_equity_series"]:
            if k == "bar_close":
                fork_bc[t] = e
        mism = 0
        for t, e in iser:
            ref = fork_bc.get(t)
            if ref is None:
                ref = fork["allbar_equity_series"][-1][1]
            if abs(ref - e) > 1e-6:
                mism += 1
        check(f"A {cn}: interval series == fork bar_close marks",
              mism == 0, f"mismatches={mism}")
        # Repair checks: stamp legitimacy + census + held-DD delta.
        ser = fork["allbar_equity_series"]
        bc_stamps = [t for t, _e, k in ser if k == "bar_close"]
        illegit = [t for t in bc_stamps if t not in legit]
        check(f"A {cn}: every bar_close stamp is a pinned table "
              f"bin_end", not illegit,
              f"illegitimate={illegit[:3]} n={len(illegit)}")
        census = Counter(t[11:19] for t in bc_stamps)
        new_dd = fork["allbar_max_drawdown"]
        check(f"A {cn}: regenerated DD vs -29 held DD",
              abs(new_dd - held[cn]["dd"]) < 1e-12,
              f"new {100*new_dd:.6f}% vs held {100*held[cn]['dd']:.6f}%"
              f" (delta {100*(new_dd-held[cn]['dd']):+.6f}pp)")
        # Value-sequence identity with the held series: the repair
        # may move stamps, never values — with exactly one inserted
        # point. Under +4h arithmetic the final session's bin2 end
        # (17:30) coincided with the recorded cutoff, so the old
        # series emitted it only as the terminal "event" mark; the
        # repaired grid emits the bin's own bar_close at 16:00 AND
        # the retained terminal mark, i.e. one inserted point whose
        # value equals the terminal value.
        held_vals = [e for _t, e, _k in held_series[cn]]
        new_vals = [e for _t, e, _k in ser]
        ins = [i for i, (t, _e, k) in enumerate(ser)
               if k == "bar_close" and t == "2026-10-16 16:00:00-04:00"]
        aligned = (len(ins) == 1
                   and new_vals[:ins[0]] + new_vals[ins[0] + 1:]
                   == held_vals
                   and abs(new_vals[ins[0]] - held_vals[-1]) < 1e-9)
        check(f"A {cn}: mark values identical to -29 series except "
              f"the one separated final-bin bar_close",
              aligned,
              f"points held {len(held_vals)} vs new {len(new_vals)}; "
              f"insertion at {ins}")
        peak, peak_t, trough_dd, trough_t = -1, None, 0.0, None
        run_peak = -1
        for t, e, k in ser:
            run_peak = max(run_peak, e)
            if e == run_peak:
                peak, peak_t = e, t
            dd_ = (run_peak - e) / run_peak if run_peak > 0 else 0.0
            if dd_ > trough_dd:
                trough_dd, trough_t = dd_, t
        mtm["views"][cn] = {
            "event_sampled_max_drawdown_pct": round(100 * ev_dd, 4),
            "allbar_max_drawdown_pct": round(100 * new_dd, 4),
            "allbar_max_drawdown_pct_full": 100 * new_dd,
            "held_29_allbar_max_drawdown_pct_full":
                100 * held[cn]["dd"],
            "dd_delta_pp": 100 * (new_dd - held[cn]["dd"]),
            "gap_pp": round(100 * (new_dd - ev_dd), 4),
            "allbar_peak_equity": peak, "allbar_peak_time": peak_t,
            "allbar_trough_time": trough_t,
            "bar_close_census_by_end_wall_time": dict(census),
            "series_points": len(ser),
            "final_equity": fork["final_equity"]}
        series_out[cn] = ser
        print(f"  >> {cn}: event DD {100*ev_dd:.2f}%  all-bar DD "
              f"{100*new_dd:.6f}%  held {100*held[cn]['dd']:.6f}%  "
              f"census {dict(census)}  trough {trough_t}", flush=True)
    with open(os.path.join(PKG, "artifacts", "mtm_dev.json"), "w") as f:
        json.dump(mtm, f, indent=1)
    with open(os.path.join(PKG, "artifacts", "equity_series_allbar.json"),
              "w") as f:
        json.dump(series_out, f)

    # ---------- B) fork through phase5: ledger byte-parity ----------
    orig_sim = st.simulate_stack

    def fork_sim(all_trades, closes_, cost, use_ranking, sector_cap,
                 dd_gate, sector_map, diag=None, cutoff=None):
        return mtm_allbar.simulate_stack_allbar(
            all_trades, closes_, cost, use_ranking, sector_cap, dd_gate,
            sector_map, diag=diag, cutoff=cutoff, pb=pb, rs_map=rs_map)
    st.simulate_stack = fork_sim
    try:
        drv.phase5(canonical, closes, feats, skipped_gap,
                   P["censored_all"], P["symbols43"], cutoff)
    finally:
        st.simulate_stack = orig_sim
    if drv.failures:
        check("B phase5 under repaired fork: no driver failures",
              False, str(drv.failures))
    fork_led = os.path.expanduser(
        "~/workspace/qf_fix29r_stage/out_fork/trade_ledger.json")
    h_fork = hashlib.sha256(open(fork_led, "rb").read()).hexdigest()
    check("B ledger byte-identical under repaired fork",
          h_fork == "267e794c284a409d7d9b6d8e1056c452976b59746062e9e6e18"
                    "c5664b74c003b", h_fork)
    mine = drv.report["phases"]["P5_run"]
    theirs = committed["phases"]["P5_run"]
    diffs = []
    for cn in ("gross", "4bps", "25bps"):
        for k in sorted(set(mine[cn]) | set(theirs[cn])):
            if json.dumps(mine[cn].get(k), sort_keys=True, default=str) \
                    != json.dumps(theirs[cn].get(k), sort_keys=True,
                                  default=str):
                diffs.append((cn, k))
    check("B views differ ONLY in max_drawdown_pct",
          all(k == "max_drawdown_pct" for _, k in diffs),
          f"diffs={diffs}")
    for cn, k in diffs:
        print(f"    view diff {cn}.{k}: committed {theirs[cn][k]} -> "
              f"all-bar {mine[cn][k]}", flush=True)
        check(f"B {cn}: phase5 all-bar DD == part A regenerated DD",
              abs(mine[cn][k] - mtm["views"][cn]
                  ["allbar_max_drawdown_pct"]) < 0.005,
              f"{mine[cn][k]} vs "
              f"{mtm['views'][cn]['allbar_max_drawdown_pct']}")

    with open(os.path.join(PKG, "artifacts", "parity_repair.json"),
              "w") as f:
        json.dump({"checks": CHECKS,
                   "ledger_sha256_under_repaired_fork": h_fork,
                   "held_29_dd_pct": {cn: 100 * held[cn]["dd"]
                                      for cn in held}},
                  f, indent=1)
    print("REPAIR_HARNESS", "FAIL" if FAILS else "PASS", FAILS,
          flush=True)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
