"""-61 synthetic boundary-shim qualification harness (frozen cases).

Runs the -60 CONTRACT_MEMO sec.7 eight preregistered cases UNCHANGED,
plus the -61 spec assertions (index-alignment negative; July-3 parity
record). Synthetic fixtures only. Canonical JSON to stdout.
"""

import copy
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

_PKG = Path(__file__).resolve().parent
sys.path.insert(0, str(_PKG))
import s2_boundary_shim_v1 as shim  # noqa: E402

SCHEDULE_PATH = (_PKG.parent / "xnys_isolated_calendar_generation_"
                 "20261019_35_r2" / "XNYS_SESSION_SCHEDULE_V2.json")
CUTOFF = "2026-07-05T00:00:00-04:00"

OUT = {"task": "QF-TD-REQ-S2-BOUNDARY-SHIM-SYNTHETIC-20261020-61 r1",
       "cases": {}, "parity": {}}
FAILURES = []


def record(name, ok, **kw):
    OUT["cases"][name] = {"status": "PASS" if ok else "FAIL", **kw}
    if not ok:
        FAILURES.append(name)


def expect_refusal(name, fn, codes):
    try:
        fn()
    except shim.ShimRefusal as e:
        record(name, e.code in codes, refusal_code=e.code)
        return
    except Exception as e:  # transform refusals carry .code too
        code = getattr(e, "code", type(e).__name__)
        record(name, code in codes, refusal_code=code)
        return
    record(name, False, refusal_code=None)


def make_rows(sym, session_dates, price_fn, sched):
    rows = []
    for d in session_dates:
        off = "-04:00" if sched["close_of"][d] and d >= "2026-03-08" \
            and d <= "2026-11-01" else "-05:00"
        # Fixture offsets: EDT -04:00 Mar-Nov, EST -05:00 otherwise.
        for hhmm in ("09:30", "13:30"):
            o, c = price_fn(d, hhmm)
            rows.append({"symbol": sym, "session": d,
                         "bar_start": f"{d}T{hhmm}:00{off}",
                         "open": o, "high": max(o, c) + 0.5,
                         "low": min(o, c) - 0.5, "close": c,
                         "volume": 1000.0})
    return rows


def ev(sym, d, as_of="2026-07-01T00:00:00-04:00"):
    return {"symbol": sym, "effective_session": d, "source": "fixture",
            "provenance": "synthetic-ledger-v1", "as_of": as_of,
            "version": "1"}


def main():
    sched = shim.load_schedule(SCHEDULE_PATH)
    tf = shim.load_transform(sched)
    ss = sched["sessions"]
    OUT["schedule"] = {"sha256": sched["sha256"], "n_sessions": len(ss),
                       "coverage": list(sched["coverage"])}

    # ---- July-3 parity record: REFUSED, not reconciled -------------
    OUT["parity"] = {
        "point": "2026-07-03 XNYS treatment",
        "artifact_fact": "2026-07-03 absent from XNYS_SESSION_"
                         "SCHEDULE_V2 sessions (non-session); "
                         "2026-07-02 present, close 16:00",
        "gate7_lineage_label": "candidate 2026-07-03 early-close fact "
                               "= True (-56 CLOSURE_MEMO/STAGING_PLAN)",
        "gate_source_fact": "dispatch_gate_r4.py derive_calendar: "
                            "'closed_2026_07_03': xnys_schedule("
                            "'2026-07-03') is None",
        "july3_parity": "REFUSED_UNRESOLVED",
        "note": "Label (early-close) vs artifact (non-session) vs "
                "source fact (closed) are NOT reconciled in -61; "
                "adjudication owned by the parallel Claude CP1 "
                "continuation (spec 6306666287). Shim adjacency binds "
                "to the artifact only; no case below depends on the "
                "disputed label (case 2 uses Thanksgiving 2025).",
        "artifact_probes": {
            "2026-07-02_in_sessions": "2026-07-02" in ss,
            "2026-07-03_in_sessions": "2026-07-03" in ss,
            "2025-11-27_in_sessions": "2025-11-27" in ss,
            "2025-11-28_close": sched["close_of"].get("2025-11-28"),
        },
    }

    receipt_ok = {"status": "COMPLETE", "source": "fixture"}

    # ---- Case 1: mid-window split, co-exclusion + recompute --------
    span1 = [d for d in ss if "2026-07-06" <= d <= "2026-07-10"]

    def px1(d, hhmm):
        if d == "2026-07-08" and hhmm == "09:30":
            return 100.0, 101.0  # only in-window signal
        if d == "2026-07-06" and hhmm == "09:30":
            return 100.0, 101.0  # surviving signal
        return 100.0, 99.0

    bars1 = shim.adapt_constructor_rows(make_rows("AAA", span1, px1, sched))
    before = hashlib.sha256(json.dumps(bars1, sort_keys=True).encode()
                            ).hexdigest()
    res1 = shim.assemble(bars1, [ev("AAA", "2026-07-08")], {"AAA": "EVENTS"},
                         receipt_ok, CUTOFF, sched, tf)
    removed_sessions = sorted({r["session"]
                               for r in res1["removed_sessions_ledger"]})
    entries_pre = shim.recompute_entries_stub(bars1)
    entries_post = shim.recompute_entries_stub(res1["bars_out"])
    surviving_ids = {b["bar_id"] for b in res1["bars_out"]}
    ok1 = (removed_sessions == ["2026-07-07", "2026-07-08", "2026-07-09"]
           and len(res1["removed_bar_ids"]) == 6
           and len(res1["bars_out"]) == 4
           and len(entries_pre) == 2 and len(entries_post) == 1
           and all(e["fill_bar_id"] in surviving_ids
                   and e["signal_bar_id"] in surviving_ids
                   for e in entries_post)
           and hashlib.sha256(json.dumps(bars1, sort_keys=True).encode()
                              ).hexdigest() == before)
    record("case1_midwindow_coexclusion_recompute", ok1,
           removed_sessions=removed_sessions,
           removed_bars=len(res1["removed_bar_ids"]),
           bars_out=len(res1["bars_out"]),
           entries_pre=len(entries_pre), entries_post=len(entries_post))

    # Signal-in-window / fill-next-session orphan negative (within c1):
    orphan = [e for e in entries_pre
              if e["fill_bar_id"] in set(res1["removed_bar_ids"])]
    record("case1b_no_orphan_entries", len(orphan) == 1
           and all(e["fill_bar_id"] in surviving_ids
                   for e in entries_post),
           pre_exclusion_orphans=len(orphan))

    # ---- Case 2: holiday adjacency (Thanksgiving 2025) -------------
    span2 = [d for d in ss if "2025-11-24" <= d <= "2025-12-03"]
    bars2 = shim.adapt_constructor_rows(
        make_rows("BBB", span2, lambda d, h: (50.0, 49.0), sched))
    res2 = shim.assemble(bars2, [ev("BBB", "2025-12-01",
                                    as_of="2025-11-20T00:00:00-05:00")],
                         {"BBB": "EVENTS"}, receipt_ok,
                         "2025-11-23T00:00:00-05:00", sched, tf)
    removed2 = sorted({r["session"]
                       for r in res2["removed_sessions_ledger"]})
    record("case2_holiday_adjacency",
           removed2 == ["2025-11-28", "2025-12-01", "2025-12-02"]
           and "2025-11-30" not in removed2,
           removed_sessions=removed2)

    # ---- Case 3: overlapping events, union + deduped ledger --------
    bars3 = shim.adapt_constructor_rows(
        make_rows("AAA", span1, lambda d, h: (10.0, 9.0), sched))
    res3 = shim.assemble(bars3, [ev("AAA", "2026-07-07"),
                                 ev("AAA", "2026-07-09")],
                         {"AAA": "EVENTS"}, receipt_ok, CUTOFF, sched, tf)
    led3 = {r["session"]: r["caused_by"]
            for r in res3["removed_sessions_ledger"]}
    record("case3_overlapping_union",
           sorted(led3) == span1 and len(led3["2026-07-08"]) == 2
           and len(res3["bars_out"]) == 0,
           removed_sessions=sorted(led3),
           causes_2026_07_08=len(led3["2026-07-08"]))

    # ---- Case 4: edge-event refusals (GATE-E4) ----------------------
    bars4 = shim.adapt_constructor_rows(
        make_rows("AAA", span1, lambda d, h: (10.0, 9.0), sched))
    expect_refusal("case4a_edge_at_span_start",
                   lambda: shim.assemble(
                       bars4, [ev("AAA", "2026-07-06")], {"AAA": "EVENTS"},
                       receipt_ok, CUTOFF, sched, tf),
                   {"EDGE_EVENT_AT_SPAN_EDGE"})
    bars4b = shim.adapt_constructor_rows(make_rows(
        "AAA", [d for d in span1 if d >= "2026-07-08"],
        lambda d, h: (10.0, 9.0), sched))
    expect_refusal("case4b_edge_out_of_span",
                   lambda: shim.assemble(
                       bars4b, [ev("AAA", "2026-07-07")], {"AAA": "EVENTS"},
                       receipt_ok, CUTOFF, sched, tf),
                   {"EDGE_EVENT_OUT_OF_SPAN"})

    # ---- Case 5: completeness + PIT + unmatched negatives ----------
    expect_refusal("case5a_receipt_partial",
                   lambda: shim.assemble(
                       bars1, [ev("AAA", "2026-07-08")], {"AAA": "EVENTS"},
                       {"status": "PARTIAL"}, CUTOFF, sched, tf),
                   {"ACQUISITION_INCOMPLETE"})
    expect_refusal("case5b_ledger_coverage_missing",
                   lambda: shim.assemble(
                       bars1, [ev("AAA", "2026-07-08")], {},
                       receipt_ok, CUTOFF, sched, tf),
                   {"LEDGER_COVERAGE_MISSING"})
    expect_refusal("case5c_pit_late",
                   lambda: shim.assemble(
                       bars1, [ev("AAA", "2026-07-08",
                                  as_of="2026-07-06T00:00:00-04:00")],
                       {"AAA": "EVENTS"}, receipt_ok, CUTOFF, sched, tf),
                   {"PIT_LATE"})
    expect_refusal("case5d_unmatched_event_symbol",
                   lambda: shim.assemble(
                       bars1, [ev("CCC", "2026-07-08")],
                       {"AAA": "EVENTS", "CCC": "EVENTS"},
                       receipt_ok, CUTOFF, sched, tf),
                   {"UNMATCHED_EVENT_SYMBOL"})

    # ---- Case 6: CSV float-exactness --------------------------------
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["bar_id", "open", "high", "low", "close", "volume"])
    for b in res1["bars_out"]:
        w.writerow([b["bar_id"], repr(b["open"]), repr(b["high"]),
                    repr(b["low"]), repr(b["close"]), repr(b["volume"])])
    csv_text = buf.getvalue()
    back = list(csv.DictReader(io.StringIO(csv_text)))
    exact = all(float(r["close"]) == b["close"] and r["bar_id"] == b["bar_id"]
                for r, b in zip(back, res1["bars_out"]))
    record("case6_csv_float_exactness", exact and len(back) == 4,
           csv_sha256=hashlib.sha256(csv_text.encode()).hexdigest(),
           rows=len(back))

    # ---- Case 7: fold-boundary invariance ---------------------------
    folds_pre = shim.materialize_folds(span1)
    folds_again = shim.materialize_folds(span1)
    removed_set = set(removed_sessions)
    membership_post = [[m for m in f["members"] if m not in removed_set]
                       for f in folds_pre]
    boundaries = [{k: f[k] for k in ("fold", "start", "end")}
                  for f in folds_pre]
    boundaries_again = [{k: f[k] for k in ("fold", "start", "end")}
                        for f in folds_again]
    folds_post_list = sorted({b["session"] for b in res1["bars_out"]})
    boundaries_if_post = [{k: f[k] for k in ("fold", "start", "end")}
                          for f in shim.materialize_folds(folds_post_list)]
    record("case7_fold_invariance",
           boundaries == boundaries_again
           and all(not (set(m) & removed_set) for m in membership_post)
           and boundaries != boundaries_if_post,
           boundaries=boundaries,
           post_exclusion_boundaries_would_differ=True)

    # ---- Case 8: no-imputation exact-subset invariant ---------------
    in_ids = {b["bar_id"] for b in bars1}
    out_ids = {b["bar_id"] for b in res1["bars_out"]}
    record("case8_no_imputation_subset",
           out_ids == in_ids - set(res1["removed_bar_ids"])
           and out_ids < in_ids
           and res1["counts"]["bars_before"]["AAA"] == 10
           and res1["counts"]["bars_after"]["AAA"] == 4,
           bars_in=len(in_ids), bars_out=len(out_ids),
           removed=len(res1["removed_bar_ids"]))

    # ---- Case 9 (additional): index-alignment negative --------------
    bad_rows = make_rows("AAA", span1[:2], lambda d, h: (1.0, 1.0), sched)
    bad_rows[0]["bar_start"], bad_rows[1]["bar_start"] = (
        bad_rows[1]["bar_start"], bad_rows[0]["bar_start"])
    expect_refusal("case9_adapter_index_alignment",
                   lambda: shim.adapt_constructor_rows(bad_rows),
                   {"ADAPTER_INDEX_ALIGNMENT", "BAR_ANCHOR"})

    n_pass = sum(1 for c in OUT["cases"].values()
                 if c["status"] == "PASS")
    OUT["counters"] = {"pass": n_pass, "total": len(OUT["cases"]),
                       "failures": FAILURES}
    OUT["terminal"] = ("PASS__SYNTHETIC_ONLY__REAL_EVENT_PROVENANCE_HOLD"
                       if not FAILURES else "HOLD__FIRST_FAILURE:"
                       + (FAILURES[0] if FAILURES else ""))
    print(json.dumps(OUT, indent=1, sort_keys=True))
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    sys.exit(main())
