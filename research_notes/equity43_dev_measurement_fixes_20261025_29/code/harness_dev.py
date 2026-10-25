"""Workpaper (as executed): DEV application harness for -29
(P1 fork application + phase5 fork parity + P7 journal build).
Consumes pipeline.pkl produced by harness_baseline.py."""
"""QF -29 DEV application harness:
 A) all-bar fork vs frozen baseline per cost view (decisions identical,
    event track == committed results, all-bar DD beside it, independent
    interval reconstruction cross-check);
 B) fork swapped through the driver's phase5 -> ledger must stay
    byte-identical, views may differ only in max_drawdown_pct;
 C) all-fire journal generation with generator-identity anchor.
Writes artifacts into the -29 package (worktree copy) for commit.
"""
import hashlib
import json
import os
import pickle
import sys

HOME = os.path.expanduser("~/workspace/qf_fix29_stage/home")
PKG = os.path.expanduser(
    "~/workspace/qf_fix29_stage/wt/research_notes/"
    "equity43_dev_measurement_fixes_20261025_29")
os.environ["QF_OUT"] = os.path.expanduser("~/workspace/qf_fix29_stage/out_fork")
os.chdir(HOME)
sys.path.insert(0, HOME)
sys.path.insert(0, os.path.join(PKG, "code"))

import run_study13 as drv  # noqa: E402
import pine_backtest as pb  # noqa: E402
import pine_stack as st  # noqa: E402
from pine_exposure import SECTOR  # noqa: E402
import mtm_allbar  # noqa: E402
import allfire_journal  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}", flush=True)
    if not cond:
        FAILS.append(name)


def main():
    with open(os.path.expanduser(
            "~/workspace/qf_fix29_stage/work/pipeline.pkl"), "rb") as f:
        P = pickle.load(f)
    data, closes = P["data"], P["closes"]
    canonical, feats = P["canonical"], P["feats"]
    skipped_gap, cutoff = P["skipped_gap"], P["cutoff"]
    symbols43 = P["symbols43"]
    committed = json.load(open(os.path.expanduser(
        "~/workspace/qf_fix29_stage/work/committed_results.json")))
    rs_map = {id(tr): feats[i]["rs"] for i, tr in enumerate(canonical)}

    # ---------- A) fork vs baseline, per view ----------
    views, ports = drv.run_views(canonical, closes, feats, skipped_gap,
                                 cutoff)
    mtm = {"method": "all-bar marked equity on the union 4H calendar; "
                     "frozen marked_equity valuation; decisions from the "
                     "identical event-time logic (dd_gate=False)",
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
        check(f"A {cn}: event track == committed results.json "
              f"max_drawdown_pct", abs(round(100 * ev_dd, 2) - rep) < 1e-9,
              f"{round(100 * ev_dd, 2)} vs {rep}")
        # interval reconstruction cross-check
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
        # peak / trough of the all-bar path
        ser = fork["allbar_equity_series"]
        peak, peak_t, trough_dd, trough_t = -1, None, 0.0, None
        run_peak = -1
        for t, e, k in ser:
            run_peak = max(run_peak, e)
            if e == run_peak:
                peak, peak_t = e, t
            dd = (run_peak - e) / run_peak if run_peak > 0 else 0.0
            if dd > trough_dd:
                trough_dd, trough_t = dd, t
        mtm["views"][cn] = {
            "event_sampled_max_drawdown_pct": round(100 * ev_dd, 4),
            "allbar_max_drawdown_pct":
                round(100 * fork["allbar_max_drawdown"], 4),
            "gap_pp": round(100 * (fork["allbar_max_drawdown"] - ev_dd), 4),
            "allbar_peak_equity": peak, "allbar_peak_time": peak_t,
            "allbar_trough_time": trough_t,
            "series_points": len(ser),
            "final_equity": fork["final_equity"]}
        series_out[cn] = ser
        print(f"  >> {cn}: event DD {100*ev_dd:.2f}%  all-bar DD "
              f"{100*fork['allbar_max_drawdown']:.4f}%  trough {trough_t}",
              flush=True)
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
                   P["censored_all"], symbols43, cutoff)
    finally:
        st.simulate_stack = orig_sim
    if drv.failures:
        check("B phase5 under fork: no driver failures", False,
              str(drv.failures))
    fork_led = os.path.expanduser(
        "~/workspace/qf_fix29_stage/out_fork/trade_ledger.json")
    h_fork = hashlib.sha256(open(fork_led, "rb").read()).hexdigest()
    check("B ledger byte-identical under fork",
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
        print(f"    view diff {cn}.{k}: committed "
              f"{theirs[cn][k]} -> all-bar {mine[cn][k]}", flush=True)

    # ---------- C) all-fire journal ----------
    ledger = json.load(open(os.path.expanduser(
        "~/workspace/qf_fix29_stage/out_base/trade_ledger.json")))
    led_by_key = {(r["symbol"], r["signal_idx"]): r for r in ledger}
    journal, summary = [], {}
    tot_gap = 0
    for sym in symbols43:
        df = data[sym]
        fires, tr_m, ce_m, sg_m = allfire_journal.gen_allfire(sym, df, pb)
        tr_f, cens_f, sg_f = drv.gen_candidates_censored(sym, df)

        def same_trade(a, b):
            return all(a[k] == b[k] for k in
                       ("entry", "stop", "tp1", "exit", "reason", "tp1_hit",
                        "entry_time", "exit_time", "hold_bars",
                        "signal_time", "signal_idx"))
        anchor = (len(tr_m) == len(tr_f)
                  and all(same_trade(a, b) for a, b in zip(tr_m, tr_f))
                  and len(ce_m) == len(cens_f) and sg_m == sg_f
                  and all(ce_m[i]["signal_idx"] == cens_f[i]["signal_idx"]
                          and ce_m[i]["entry"] == cens_f[i]["entry"]
                          for i in range(len(ce_m))))
        check(f"C {sym}: mirrored generation == frozen generator",
              anchor)
        tot_gap += sg_m
        for f in fires:
            rec = dict(f)
            if f["classification"] == "MATCHED_CANDIDATE":
                lr = led_by_key.get((sym, f["signal_idx"]))
                if lr is None:
                    check(f"C {sym}: matched fire has ledger record",
                          False, str(f["signal_idx"]))
                    continue
                rec["disposition_4bps_c1"] = lr["disposition_4bps_c1"]
                rec["taken_gross"] = lr["taken_gross"]
                rec["taken_4bps"] = lr["taken_4bps"]
                rec["taken_25bps"] = lr["taken_25bps"]
                rec["censored"] = lr["censored"]
            journal.append(rec)
            summary[f["classification"]] = \
                summary.get(f["classification"], 0) + 1
    check("C total gap-ineligible == results.json skipped_gap_below_stop "
          "(1)", tot_gap == 1, f"got {tot_gap}")
    check("C UNCLASSIFIED == 0", summary.get("UNCLASSIFIED", 0) == 0,
          str(summary))
    matched_keys = {(r["symbol"], r["signal_idx"]) for r in journal
                    if r["classification"] == "MATCHED_CANDIDATE"}
    check("C matched fires == 590 ledger candidates",
          matched_keys == set(led_by_key),
          f"matched {len(matched_keys)} vs ledger {len(led_by_key)}")
    journal.sort(key=lambda r: (r["symbol"], r["signal_idx"]))
    with open(os.path.join(PKG, "artifacts", "allfire_journal.json"),
              "w") as f:
        json.dump(journal, f, indent=1)
    with open(os.path.join(PKG, "artifacts", "allfire_summary.json"),
              "w") as f:
        json.dump({"total_fires": len(journal), "by_class": summary,
                   "skipped_gap_total": tot_gap,
                   "domain": "per symbol, bars i in [WARMUP=215, n-2] of "
                             "the pinned 4H series; fires evaluated on "
                             "completed bars only"}, f, indent=1)
    print("C summary:", summary, "total fires:", len(journal), flush=True)

    print("DEV_HARNESS", "FAIL" if FAILS else "PASS", FAILS, flush=True)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
