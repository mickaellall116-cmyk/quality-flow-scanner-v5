"""Synthetic-fixture tests for EXP-14-BUY-DEV-EXPLORATORY v2 machinery.

Fixtures only: hand-built inventory rows with planted fires and fields.
No real data is read. The analysis implementation (_analysis_impl) is
exercised ONLY here, on fixtures — that is the synthetic-only exercise
the independent review (Issue #1 comment 6405786931, item 2) requires.
Covers everything the v1 suite covered (adapted to the single
complete-window rule) plus: endpoint fixtures for the h=20 rule
(events AND controls), the finished analysis path (forward returns,
paired excess, both bootstraps, wider-of-two rule, output header), its
fail-closed negatives (hash mismatch, non-DEV timestamp, missing
forward data incl. the absent-'open' case, incomplete-window control),
the retained GO gate, and the pinned seed literals.
"""
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))
import exp14_buy as X

FAILS = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        FAILS.append(name)


def bar(sym, idx, bin_="09:30", ordinal=0, atr_pct=0.02, signal=False,
        dom=True, close=100.0, open_=None, ema21=None, ema55=None,
        ema200=None, date="2025-01-01"):
    return {"symbol": sym, "idx": idx, "ts": f"{date}T{bin_}:00-05:00",
            "session_date": date, "session_ordinal": ordinal,
            "bin": bin_, "close": close,
            "open": (close if open_ is None else open_),
            "atr": (atr_pct * close) if atr_pct is not None else None,
            "atr_pct": atr_pct, "ema21": ema21, "ema55": ema55,
            "ema200": ema200, "signal": signal, "in_generator_domain": dom}


def series(sym, n, fires=(), **kw):
    return [bar(sym, i, signal=(i in fires), **kw) for i in range(n)]


def main():
    # ---- seed pins -------------------------------------------------------
    check("seeds: master pinned literal",
          X.MASTER_SEED == 7715012043445510037)
    check("seeds: bootstrap pinned literal",
          X.BOOTSTRAP_SEED == 6050949521315240661)

    # ---- de-clustering ----------------------------------------------------
    check("decluster: lone fire kept", X.decluster([100]) == [100])
    check("decluster: fire 20 bars after prior dropped",
          X.decluster([100, 120]) == [100])
    check("decluster: fire 21 bars after prior kept",
          X.decluster([100, 121]) == [100, 121])
    check("decluster: chain uses any prior signal bar, not kept events",
          X.decluster([100, 115, 130]) == [100])

    # ---- exclusion set ------------------------------------------------------
    ex = X.excluded_set({50}, 200)
    check("exclusion: fire itself excluded", 50 in ex)
    check("exclusion: +/-20 inclusive", 30 in ex and 70 in ex)
    check("exclusion: +/-21 not excluded", 29 not in ex and 71 not in ex)

    # ---- window_complete unit checks -----------------------------------------
    check("window: idx 1022 of 1043 complete", X.window_complete(1022, 1043))
    check("window: idx 1023 of 1043 incomplete",
          not X.window_complete(1023, 1043))
    check("window: idx 0 complete", X.window_complete(0, 1043))

    # ---- B-A pool rules -------------------------------------------------------
    rows = series("AAA", 300, fires={150})
    for r in rows:
        r["session_ordinal"] = r["idx"] // 2
    ev = rows[150]
    ev["session_ordinal"] = 75
    step0 = X.LADDER[0]
    pool = X.eligible_pool(rows, X.excluded_set({150}, 300), ev, step0,
                           "B-A")
    check("pool: event bar itself excluded (fire)", 150 not in pool)
    check("pool: +/-20 around fire excluded",
          all(abs(j - 150) > 20 for j in pool))
    check("pool: same-bin only",
          all(rows[j]["bin"] == "09:30" for j in pool))
    rows2 = [dict(r) for r in rows]
    rows2[100]["bin"] = "13:30"
    pool2 = X.eligible_pool(rows2, X.excluded_set({150}, 300), ev, step0,
                            "B-A")
    check("pool: opposite-bin bar excluded", 100 not in pool2)
    rows3 = [dict(r) for r in rows]
    rows3[100]["session_ordinal"] = 75 + 31
    pool3 = X.eligible_pool(rows3, X.excluded_set({150}, 300), ev, step0,
                            "B-A")
    check("pool: session window 30 enforced", 100 not in pool3)
    rows4 = [dict(r) for r in rows]
    rows4[100]["atr_pct"] = 0.02 * 1.26
    pool4 = X.eligible_pool(rows4, X.excluded_set({150}, 300), ev, step0,
                            "B-A")
    check("pool: ATR% band +25% edge excluded at 1.26x", 100 not in pool4)
    rows5 = series("AAA", 300, fires={150}, atr_pct=0.03125)
    for r in rows5:
        r["session_ordinal"] = r["idx"] // 2
    ev5 = rows5[150]
    rows5[100]["atr_pct"] = 0.0390625
    pool5 = X.eligible_pool(rows5, X.excluded_set({150}, 300), ev5, step0,
                            "B-A")
    check("pool: ATR% band +25% edge included at exactly 1.25x",
          100 in pool5)
    rows6 = [dict(r) for r in rows]
    rows6[100]["atr_pct"] = None
    pool6 = X.eligible_pool(rows6, X.excluded_set({150}, 300), ev, step0,
                            "B-A")
    check("pool: missing ATR% excluded, never imputed", 100 not in pool6)
    rows7 = [dict(r) for r in rows]
    rows7[100]["in_generator_domain"] = False
    pool7 = X.eligible_pool(rows7, X.excluded_set({150}, 300), ev, step0,
                            "B-A")
    check("pool: non-domain bar excluded (P-1)", 100 not in pool7)

    # ---- single complete-window rule: control endpoint fixtures ---------------
    # All bars share one session ordinal so only the window rule binds.
    rowsE = series("EEE", 300, fires={150})
    evE = rowsE[150]
    poolE = X.eligible_pool(rowsE, X.excluded_set({150}, 300), evE,
                            step0, "B-A")
    check("window: control at n-1-20 (279) eligible", 279 in poolE)
    check("window: control at n-1-19 (280) ineligible though h=10 fits",
          280 not in poolE)
    check("window: control at 285 ineligible", 285 not in poolE)
    check("window: every pooled control complete",
          all(X.window_complete(j, 300) for j in poolE))

    # ---- single rule: event endpoint fixture ------------------------------------
    rowsD = series("DDD", 300, fires={100, 284})
    orig = X.EXPECTED_FIRES
    X.EXPECTED_FIRES = 2
    try:
        repD, cohortD, _ = X.run_pool_counts({"DDD": rowsD})
    finally:
        X.EXPECTED_FIRES = orig
    check("window: h=10-complete/h=20-incomplete event dropped from cohort",
          [c["signal_idx"] for c in cohortD["cohort"]] == [100])
    check("window: per-horizon drops reported (2/3/9 pattern at unit scale)",
          repD["events_dropped_forward_window_by_horizon"]
          == {"5": 0, "10": 0, "20": 1})
    check("window: cohort count uses the single rule",
          repD["cohort_events_single_rule_h20"] == 1)

    # ---- B-T trend filter ---------------------------------------------------------
    rowsT = series("BBB", 300, fires={150})
    for r in rowsT:
        r["session_ordinal"] = r["idx"] // 2
        r["ema200"], r["ema55"], r["ema21"] = 90.0, 95.0, 96.0
    evT = rowsT[150]
    poolT = X.eligible_pool(rowsT, X.excluded_set({150}, 300), evT, step0,
                            "B-T")
    check("B-T: uptrend bars eligible", len(poolT) > 0)
    rowsT2 = [dict(r) for r in rowsT]
    rowsT2[100]["close"] = 80.0
    poolT2 = X.eligible_pool(rowsT2, X.excluded_set({150}, 300), evT,
                             step0, "B-T")
    check("B-T: close <= EMA200 excluded", 100 not in poolT2)
    poolA2 = X.eligible_pool(rowsT2, X.excluded_set({150}, 300), evT,
                             step0, "B-A")
    check("B-A: same bar allowed (no trend filter)", 100 in poolA2)
    rowsT3 = [dict(r) for r in rowsT]
    rowsT3[100]["ema21"] = 94.0
    poolT3 = X.eligible_pool(rowsT3, X.excluded_set({150}, 300), evT,
                             step0, "B-T")
    check("B-T: EMA21 <= EMA55 excluded", 100 not in poolT3)

    # ---- ladder selection ------------------------------------------------------------
    rowsL = []
    for i in range(400):
        rowsL.append(bar("CCC", i, ordinal=i // 2, dom=(i % 100 < 40),
                         signal=(i in (10, 210))))
    X.EXPECTED_FIRES = 2
    try:
        rep, cohortL, drawsL = X.run_pool_counts({"CCC": rowsL})
    finally:
        X.EXPECTED_FIRES = orig
    check("ladder: report has 4 steps", len(rep["ladder"]) == 4)
    check("ladder: frozen step is first with drop<=15% or last",
          rep["frozen_step"] == next(
              (r["step"] for r in rep["ladder"] if r["drop_rate"] <= 0.15),
              "c"))
    check("ladder: cohort counted", rep["declustered_events_total"] == 2)
    check("ladder: all drawn controls window-complete",
          all(X.window_complete(j, 400)
              for grp in drawsL["draws"].values()
              for d in grp.values() for j in d))

    # ---- draws: determinism + seed sensitivity ------------------------------------------
    pool = list(range(0, 200, 3))
    d1 = X.event_draws("B-A", "AAA", 150, pool)
    d2 = X.event_draws("B-A", "AAA", 150, pool)
    check("draws: deterministic", d1 == d2)
    check("draws: size 20 without replacement",
          len(d1) == 20 and len(set(d1)) == 20)
    check("draws: drawn from pool", all(x in pool for x in d1))
    d3 = X.event_draws("B-A", "AAA", 151, pool)
    check("draws: per-event sub-seed differs", d3 != d1)
    d4 = X.event_draws("B-T", "AAA", 150, pool)
    check("draws: per-arm sub-seed differs", d4 != d1)
    small = X.event_draws("B-A", "AAA", 150, [5, 9])
    check("draws: pool smaller than 20 drawn whole (all available)",
          small == [5, 9])

    # ---- forward_return arithmetic (fixture values only) ------------------------------
    def fx_rows(sym, slope_close):
        out = []
        for i in range(80):
            out.append(bar(sym, i, ordinal=i // 2,
                           bin_=("09:30" if i % 2 == 0 else "13:30"),
                           close=100.0 + slope_close * i,
                           open_=100.0 + i, atr_pct=None,
                           date="2025-03-03",
                           signal=(i in (30, 40)),
                           ema21=90.0, ema55=90.0, ema200=90.0))
            out[-1]["atr"] = 2.0
            out[-1]["atr_pct"] = 2.0 / out[-1]["close"]
        return out

    eee = fx_rows("EEE", 1.0)
    fr = X.forward_return(eee, 30, 10)
    check("returns: endpoint arithmetic (open i+1, close i+h, /ATR)",
          fr["atr_units"] == 4.5 and abs(fr["pct"] - 9.0 / 131.0) < 1e-12)

    # ---- analysis path on fixtures (synthetic-only exercise) ------------------------------
    fff = fx_rows("FFF", 2.0)
    inv = {"EEE": eee, "FFF": fff}
    cohort_obj = {"study": X.STUDY_ID, "script_version": 2,
                  "cohort": [
                      {"symbol": "EEE", "signal_idx": 30,
                       "ts": eee[30]["ts"], "bin": eee[30]["bin"]},
                      {"symbol": "FFF", "signal_idx": 40,
                       "ts": fff[40]["ts"], "bin": fff[40]["bin"]}],
                  "retained": ["EEE:30", "FFF:40"]}
    draws_obj = {"study": X.STUDY_ID, "script_version": 2,
                 "master_seed": X.MASTER_SEED, "frozen_step": "c",
                 "draws": {"B-A": {"EEE:30": [10, 12, 14],
                                   "FFF:40": [20, 22]},
                           "B-T": {"EEE:30": [10]}}}
    cs, ds = X.canonical_sha(cohort_obj), X.canonical_sha(draws_obj)
    res = X._analysis_impl(inv, cohort_obj, draws_obj, cs, ds, reps=300)
    check("analysis: primary n", res["primary_paired_excess"]["n"] == 2)
    check("analysis: hand-computed paired excess (0 and 9.5 -> 4.75)",
          res["horizons"]["10"]["mean_paired_excess_atr"] == 4.75)
    check("analysis: B-T diagnostic computed, non-gating",
          res["bt_diagnostic"]["n"] == 1
          and res["bt_diagnostic"]["mean_paired_excess_atr"] == 0.0
          and res["bt_diagnostic"]["gating"] is False)
    check("analysis: header carries EXPLORATORY label and no claim",
          res["label"] == "DEV EXPLORATORY" and res["claim"] == "NONE")
    check("analysis: interval ordered and from a named method",
          res["primary_paired_excess"]["interval_lower_95"]
          <= res["primary_paired_excess"]["interval_upper_95"]
          and res["primary_paired_excess"]["interval_used"]
          in ("block", "cluster"))
    res2 = X._analysis_impl(inv, cohort_obj, draws_obj, cs, ds, reps=300)
    check("analysis: deterministic under pinned seeds", res == res2)

    # ---- analysis fail-closed negatives ------------------------------------------------------
    def raises(fn, exc=X.FailClosedError):
        try:
            fn()
            return False
        except exc:
            return True
        except Exception:
            return False

    check("fail-closed: cohort hash mismatch refused",
          raises(lambda: X._analysis_impl(inv, cohort_obj, draws_obj,
                                          "0" * 64, ds, reps=50)))
    check("fail-closed: draws hash mismatch refused",
          raises(lambda: X._analysis_impl(inv, cohort_obj, draws_obj,
                                          cs, "0" * 64, reps=50)))
    inv_old = {"EEE": [dict(r) for r in eee],
               "FFF": [dict(r, session_date="2027-01-04",
                            ts="2027-01-04T09:30:00-05:00") for r in fff]}
    check("fail-closed: non-DEV timestamp refused",
          raises(lambda: X._analysis_impl(inv_old, cohort_obj, draws_obj,
                                          cs, ds, reps=50)))
    inv_noopen = {"EEE": [{k: v for k, v in r.items() if k != "open"}
                          for r in eee], "FFF": fff}
    check("fail-closed: missing 'open' forward data refused",
          raises(lambda: X._analysis_impl(inv_noopen, cohort_obj,
                                          draws_obj, cs, ds, reps=50)))
    draws_bad = json.loads(json.dumps(draws_obj))
    draws_bad["draws"]["B-A"]["EEE:30"] = [75]  # 75+20 > 79: incomplete
    check("fail-closed: incomplete-window control refused",
          raises(lambda: X._analysis_impl(
              inv, cohort_obj, draws_bad, cs,
              X.canonical_sha(draws_bad), reps=50)))
    check("fail-closed: forward_return incomplete window refused",
          raises(lambda: X.forward_return(eee, 75, 10)))
    rows_gap = [dict(r) for r in eee]
    del rows_gap[3]["bin"]
    check("fail-closed: invalid inventory key refused",
          raises(lambda: X.validate_inventory({"EEE": rows_gap})))

    # ---- returns gate (negative) ----------------------------------------------------------------
    check("returns gate: RETURNS_ENABLED is False", X.RETURNS_ENABLED
          is False)
    try:
        X.compute_forward_returns()
        check("returns gate: raises", False)
    except X.ExecutionGoRequired:
        check("returns gate: raises ExecutionGoRequired", True)

    # ---- inventory hash fail-closed (negative) ------------------------------------------------------
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl",
                                     delete=False) as f:
        f.write(json.dumps(bar("ZZZ", 0)) + "\n")
        path = f.name
    try:
        X.load_inventory(path, "0" * 64)
        check("hash gate: mismatch refused", False)
    except SystemExit:
        check("hash gate: mismatch refused", True)
    good = hashlib.sha256(open(path, "rb").read()).hexdigest()
    loaded = X.load_inventory(path, good)
    check("hash gate: matching hash loads", list(loaded) == ["ZZZ"])
    os.unlink(path)

    # ---- census fail-closed (negative) ------------------------------------------------------------------
    try:
        X.run_pool_counts({"AAA": series("AAA", 300, fires={150})})
        check("census gate: wrong fire count refused", False)
    except SystemExit:
        check("census gate: wrong fire count refused", True)

    print(f"\n{len(FAILS)} failures")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
