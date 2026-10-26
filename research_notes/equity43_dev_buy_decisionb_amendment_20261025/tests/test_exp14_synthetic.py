"""Synthetic-fixture tests for EXP-14-BUY-DEV-EXPLORATORY v3.

Fixtures only: hand-built inventory rows and a hand-built
execution-only price input. No real data is read. Covers everything
the v2 suite covered (adapted) plus the Decision B items:
  (a) price separation — entry opens come ONLY from the separate
      execution price input; inventory fixture rows carry NO 'open'
      key (a bogus planted inventory 'open' is proven ignored);
      exec-price coverage/shape/hash fail-closed negatives;
  (b) CLI wiring — the plain CLI in returns mode assembles its
      inputs and is refused by the GO gate (exit 3, no output);
      missing wiring arguments fail at argparse (exit 2); and a
      synthetic CLI end-to-end run (fixture files -> full pipeline
      -> pinned-schema output) with the gate flipped ONLY inside
      the test's own subprocess;
  (c) reporting — percent views hand-verified next to the ATR views,
      the declared cost-sensitivity line (primary pct excess minus
      25 bps), and the mandatory Decision B disclosure header
      (absent / miscounted / reworded disclosure all fail closed;
      the emitted header recomputes from the cohort artifact).
The analysis implementation (_analysis_impl) is exercised ONLY here,
on fixtures.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

CODE_DIR = os.path.join(os.path.dirname(__file__), "..", "code")
sys.path.insert(0, CODE_DIR)
import exp14_buy as X

SCRIPT = os.path.join(CODE_DIR, "exp14_buy.py")
FAILS = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        FAILS.append(name)


def bar(sym, idx, bin_="09:30", ordinal=0, atr_pct=0.02, signal=False,
        dom=True, close=100.0, ema21=None, ema55=None, ema200=None,
        date="2025-01-01"):
    """Inventory fixture row. NOTE: no 'open' key — the outcome-blind
    inventory carries none (Decision B item (a))."""
    return {"symbol": sym, "idx": idx, "ts": f"{date}T{bin_}:00-05:00",
            "session_date": date, "session_ordinal": ordinal,
            "bin": bin_, "close": close,
            "atr": (atr_pct * close) if atr_pct is not None else None,
            "atr_pct": atr_pct, "ema21": ema21, "ema55": ema55,
            "ema200": ema200, "signal": signal, "in_generator_domain": dom}


def series(sym, n, fires=(), **kw):
    return [bar(sym, i, signal=(i in fires), **kw) for i in range(n)]


def raises(fn, exc=X.FailClosedError):
    try:
        fn()
        return False
    except exc:
        return True
    except Exception:
        return False


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
    check("window: per-horizon drops reported",
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

    # ---- analysis fixtures (inventory rows + SEPARATE price input) ----------------------
    def fx(sym, slope_close, n=100, fires=()):
        out, opens = [], {}
        for i in range(n):
            out.append(bar(sym, i, ordinal=i // 2,
                           bin_=("09:30" if i % 2 == 0 else "13:30"),
                           close=100.0 + slope_close * i, atr_pct=None,
                           date="2025-03-03", signal=(i in fires),
                           ema21=90.0, ema55=90.0, ema200=90.0))
            out[-1]["atr"] = 2.0
            out[-1]["atr_pct"] = 2.0 / out[-1]["close"]
            opens[i] = 100.0 + i
        return out, opens

    eee, eee_opens = fx("EEE", 1.0, fires=(30, 60))
    fff, fff_opens = fx("FFF", 2.0, fires=(40,))
    inv = {"EEE": eee, "FFF": fff}
    prices = {"EEE": eee_opens, "FFF": fff_opens}

    # ---- forward_return arithmetic: prices from the EXEC input only ----------------------
    fr = X.forward_return(eee, eee_opens, 30, 10)
    check("returns: endpoint arithmetic (exec open i+1, close i+h, /ATR)",
          fr["atr_units"] == 4.5 and abs(fr["pct"] - 9.0 / 131.0) < 1e-12)
    check("returns: missing execution price refused",
          raises(lambda: X.forward_return(
              eee, {k: v for k, v in eee_opens.items() if k != 31}, 30, 10)))
    check("returns: incomplete window refused",
          raises(lambda: X.forward_return(eee, eee_opens, 95, 10)))
    check("returns: non-positive execution price refused",
          raises(lambda: X.forward_return(
              eee, {**eee_opens, 31: 0.0}, 30, 10)))

    # ---- exec-price validation negatives ---------------------------------------------------
    check("exec: exact coverage validates",
          X.validate_exec_prices(inv, prices) is True)
    p_missing = {"EEE": {k: v for k, v in eee_opens.items() if k != 7},
                 "FFF": fff_opens}
    check("exec: missing bar refused",
          raises(lambda: X.validate_exec_prices(inv, p_missing)))
    p_extra = {"EEE": {**eee_opens, 100: 1.0}, "FFF": fff_opens}
    check("exec: extra bar refused",
          raises(lambda: X.validate_exec_prices(inv, p_extra)))
    p_sym = {**prices, "GGG": {0: 1.0}}
    check("exec: extra symbol refused",
          raises(lambda: X.validate_exec_prices(inv, p_sym)))
    p_none = {"EEE": {**eee_opens, 5: None}, "FFF": fff_opens}
    check("exec: None open refused",
          raises(lambda: X.validate_exec_prices(inv, p_none)))

    # ---- full analysis on fixtures ------------------------------------------------------------
    cohort_obj = {"study": X.STUDY_ID, "script_version": 3,
                  "cohort": [
                      {"symbol": "EEE", "signal_idx": 30,
                       "ts": eee[30]["ts"], "bin": eee[30]["bin"]},
                      {"symbol": "EEE", "signal_idx": 60,
                       "ts": eee[60]["ts"], "bin": eee[60]["bin"]},
                      {"symbol": "FFF", "signal_idx": 40,
                       "ts": fff[40]["ts"], "bin": fff[40]["bin"]}],
                  "retained": ["EEE:30", "FFF:40"]}
    draws_obj = {"study": X.STUDY_ID, "script_version": 3,
                 "master_seed": X.MASTER_SEED, "frozen_step": "c",
                 "draws": {"B-A": {"EEE:30": [10, 12, 14],
                                   "FFF:40": [20, 22]},
                           "B-T": {"EEE:30": [10]}}}
    cs, ds = X.canonical_sha(cohort_obj), X.canonical_sha(draws_obj)
    disc = X.build_disclosure(cohort_obj)
    check("disclosure: built from cohort (3 eligible, 2 retained, 1 out)",
          disc["eligible_events"] == 3
          and disc["retained_events_matched"] == 2
          and disc["excluded_events_unmatched"] == 1
          and abs(disc["exclusion_rate"] - 1 / 3) < 1e-12)
    res = X._analysis_impl(inv, prices, cohort_obj, draws_obj, cs, ds,
                           disclosure=disc, reps=300)
    check("analysis: primary n", res["primary_paired_excess"]["n"] == 2)
    check("analysis: hand-computed paired excess ATR (0 and 9.5 -> 4.75)",
          res["horizons"]["10"]["mean_paired_excess_atr"] == 4.75)
    exE_pct = 9.0 / 131.0 - (9.0 / 111.0 + 9.0 / 113.0 + 9.0 / 115.0) / 3
    exF_pct = 59.0 / 141.0 - (39.0 / 121.0 + 41.0 / 123.0) / 2
    want_pct = (exE_pct + exF_pct) / 2
    check("analysis: hand-computed paired excess PCT",
          abs(res["horizons"]["10"]["mean_paired_excess_pct"] - want_pct)
          < 1e-12)
    check("analysis: event pct view present at every horizon",
          all("mean_event_return_pct" in res["horizons"][h]
              for h in ("5", "10", "20")))
    check("analysis: cost line = primary pct excess minus 25 bps",
          abs(res["cost_sensitivity"]
              ["primary_paired_excess_pct_minus_round_trip"]
              - (want_pct - 0.0025)) < 1e-12
          and res["cost_sensitivity"]["round_trip_bps"] == 25)
    check("analysis: disclosure header emitted and recomputed",
          res["disclosure"]["excluded_events_unmatched"] == 1
          and res["disclosure"]["matched_subpopulation_only"] is True
          and "MATCHED SUBPOPULATION ONLY"
          in res["disclosure"]["scope_statement"])
    check("analysis: B-T diagnostic computed, non-gating, pct carried",
          res["bt_diagnostic"]["n"] == 1
          and res["bt_diagnostic"]["mean_paired_excess_atr"] == 0.0
          and abs(res["bt_diagnostic"]["mean_paired_excess_pct"]
                  - (9.0 / 131.0 - 9.0 / 111.0)) < 1e-12
          and res["bt_diagnostic"]["gating"] is False)
    check("analysis: header carries EXPLORATORY label and no claim",
          res["label"] == "DEV EXPLORATORY" and res["claim"] == "NONE"
          and res["verdict"].startswith("NONE"))
    check("analysis: interval ordered and from a named method",
          res["primary_paired_excess"]["interval_lower_95"]
          <= res["primary_paired_excess"]["interval_upper_95"]
          and res["primary_paired_excess"]["interval_used"]
          in ("block", "cluster"))
    res2 = X._analysis_impl(inv, prices, cohort_obj, draws_obj, cs, ds,
                            disclosure=disc, reps=300)
    check("analysis: deterministic under pinned seeds", res == res2)

    # prices provably come from the exec input: a bogus 'open' planted
    # on the inventory rows changes nothing.
    inv_bogus = {s: [dict(r, open=999999.0) for r in rr]
                 for s, rr in inv.items()}
    res3 = X._analysis_impl(inv_bogus, prices, cohort_obj, draws_obj,
                            cs, ds, disclosure=disc, reps=300)
    check("analysis: planted inventory 'open' ignored (exec input rules)",
          res3 == res)

    # ---- analysis fail-closed negatives ------------------------------------------------------
    check("fail-closed: cohort hash mismatch refused",
          raises(lambda: X._analysis_impl(inv, prices, cohort_obj,
                                          draws_obj, "0" * 64, ds,
                                          disclosure=disc, reps=50)))
    check("fail-closed: draws hash mismatch refused",
          raises(lambda: X._analysis_impl(inv, prices, cohort_obj,
                                          draws_obj, cs, "0" * 64,
                                          disclosure=disc, reps=50)))
    inv_old = {"EEE": [dict(r) for r in eee],
               "FFF": [dict(r, session_date="2027-01-04",
                            ts="2027-01-04T09:30:00-05:00") for r in fff]}
    check("fail-closed: non-DEV timestamp refused",
          raises(lambda: X._analysis_impl(inv_old, prices, cohort_obj,
                                          draws_obj, cs, ds,
                                          disclosure=disc, reps=50)))
    draws_bad = json.loads(json.dumps(draws_obj))
    draws_bad["draws"]["B-A"]["EEE:30"] = [85]  # 85+20 > 99: incomplete
    check("fail-closed: incomplete-window control refused",
          raises(lambda: X._analysis_impl(
              inv, prices, cohort_obj, draws_bad, cs,
              X.canonical_sha(draws_bad), disclosure=disc, reps=50)))
    rows_gap = [dict(r) for r in eee]
    del rows_gap[3]["bin"]
    check("fail-closed: invalid inventory key refused",
          raises(lambda: X.validate_inventory({"EEE": rows_gap})))
    check("fail-closed: analysis with broken price coverage refused",
          raises(lambda: X._analysis_impl(inv, p_missing, cohort_obj,
                                          draws_obj, cs, ds,
                                          disclosure=disc, reps=50)))

    # ---- disclosure fail-closed negatives (item (c)) --------------------------------------------
    check("fail-closed: disclosure absent refused",
          raises(lambda: X._analysis_impl(inv, prices, cohort_obj,
                                          draws_obj, cs, ds,
                                          disclosure=None, reps=50)))
    bad_disc = dict(disc, excluded_events_unmatched=0, exclusion_rate=0.0,
                    exclusion_rate_pct=0.0)
    check("fail-closed: miscounted disclosure refused",
          raises(lambda: X._analysis_impl(inv, prices, cohort_obj,
                                          draws_obj, cs, ds,
                                          disclosure=bad_disc, reps=50)))
    bad_scope = dict(disc, scope_statement="ALL BUY SIGNALS")
    check("fail-closed: reworded scope statement refused",
          raises(lambda: X._analysis_impl(inv, prices, cohort_obj,
                                          draws_obj, cs, ds,
                                          disclosure=bad_scope, reps=50)))
    bad_basis = dict(disc, decision_basis="some other basis")
    check("fail-closed: drifted decision basis refused",
          raises(lambda: X._analysis_impl(inv, prices, cohort_obj,
                                          draws_obj, cs, ds,
                                          disclosure=bad_basis, reps=50)))

    # ---- returns gate (negative) ------------------------------------------------------------------
    check("returns gate: RETURNS_ENABLED is False", X.RETURNS_ENABLED
          is False)
    try:
        X.compute_forward_returns()
        check("returns gate: bare call raises", False)
    except X.ExecutionGoRequired:
        check("returns gate: bare call raises ExecutionGoRequired", True)
    try:
        X.compute_forward_returns(by_symbol=inv, exec_prices=prices,
                                  cohort_obj=cohort_obj,
                                  draws_obj=draws_obj,
                                  expected_cohort_sha=cs,
                                  expected_draws_sha=ds,
                                  disclosure=disc, reps=50)
        check("returns gate: fully-wired call still raises", False)
    except X.ExecutionGoRequired:
        check("returns gate: fully-wired call still raises", True)

    # ---- file loading: inventory + exec prices ------------------------------------------------------
    tmp = tempfile.mkdtemp()

    def write(name, text):
        p = os.path.join(tmp, name)
        with open(p, "w") as f:
            f.write(text)
        return p, hashlib.sha256(text.encode()).hexdigest()

    inv_path, inv_sha = write(
        "inv.jsonl", "".join(json.dumps(r, sort_keys=True) + "\n"
                             for s in ("EEE", "FFF") for r in inv[s]))
    try:
        X.load_inventory(inv_path, "0" * 64)
        check("hash gate: inventory mismatch refused", False)
    except SystemExit:
        check("hash gate: inventory mismatch refused", True)
    loaded = X.load_inventory(inv_path, inv_sha)
    check("hash gate: matching inventory hash loads",
          sorted(loaded) == ["EEE", "FFF"] and len(loaded["EEE"]) == 100)

    px_text = "".join(
        json.dumps({"symbol": s, "idx": i, "ts": inv[s][i]["ts"],
                    "open": prices[s][i]}, sort_keys=True) + "\n"
        for s in ("EEE", "FFF") for i in range(100))
    px_path, px_sha = write("prices.jsonl", px_text)
    try:
        X.load_exec_prices(px_path, "0" * 64)
        check("hash gate: exec-prices mismatch refused", False)
    except SystemExit:
        check("hash gate: exec-prices mismatch refused", True)
    loaded_px = X.load_exec_prices(px_path, px_sha)
    check("exec file: loads to the exact price map", loaded_px == prices)
    dup_path, dup_sha = write(
        "prices_dup.jsonl",
        px_text + json.dumps({"symbol": "EEE", "idx": 0,
                              "ts": inv["EEE"][0]["ts"], "open": 1.0},
                             sort_keys=True) + "\n")
    check("exec file: duplicate bar refused",
          raises(lambda: X.load_exec_prices(dup_path, dup_sha)))
    smg_path, smg_sha = write(
        "prices_smg.jsonl",
        json.dumps({"symbol": "EEE", "idx": 0, "ts": "t", "open": 1.0,
                    "close": 2.0}, sort_keys=True) + "\n")
    check("exec file: smuggled field refused",
          raises(lambda: X.load_exec_prices(smg_path, smg_sha)))

    cohort_path, cohort_sha = write("cohort.json",
                                    json.dumps(cohort_obj, indent=1,
                                               sort_keys=True))
    draws_path, draws_sha = write("draws.json",
                                  json.dumps(draws_obj, indent=1,
                                             sort_keys=True))

    # ---- CLI wiring (item (b)): plain CLI is refused by the GO gate ----------------------------------
    out_json = os.path.join(tmp, "out.json")
    argv = [sys.executable, SCRIPT,
            "--inventory", inv_path, "--inventory-sha", inv_sha,
            "--mode", "returns",
            "--cohort", cohort_path, "--cohort-sha", cohort_sha,
            "--draws", draws_path, "--draws-sha", draws_sha,
            "--exec-prices", px_path, "--exec-prices-sha", px_sha,
            "--out-analysis", out_json]
    r = subprocess.run(argv, capture_output=True, text=True)
    check("CLI: returns mode refused by GO gate (exit 3)",
          r.returncode == 3 and "GO GATE" in r.stderr)
    check("CLI: gate refusal writes NO output", not os.path.exists(out_json))
    argv_missing = [a for a in argv if a not in
                    ("--exec-prices", px_path, "--exec-prices-sha", px_sha)]
    r2 = subprocess.run(argv_missing, capture_output=True, text=True)
    check("CLI: missing price-input wiring fails at argparse (exit 2)",
          r2.returncode == 2 and "--exec-prices" in r2.stderr)
    argv_badsha = list(argv)
    argv_badsha[argv_badsha.index("--cohort-sha") + 1] = "0" * 64
    r3 = subprocess.run(argv_badsha, capture_output=True, text=True)
    check("CLI: cohort hash mismatch fails closed (exit 2)",
          r3.returncode == 2 and "FAIL-CLOSED" in r3.stderr)

    # ---- CLI end-to-end on fixtures (gate flipped ONLY in this subprocess) ---------------------------
    runner = os.path.join(tmp, "run_fixture_cli.py")
    with open(runner, "w") as f:
        f.write("import sys\n"
                f"sys.path.insert(0, {os.path.abspath(CODE_DIR)!r})\n"
                "import exp14_buy as X\n"
                "X.RETURNS_ENABLED = True  # fixture-only, in-process\n"
                f"sys.argv = {['exp14_buy.py'] + argv[2:]!r}\n"
                "sys.exit(X.main())\n")
    r4 = subprocess.run([sys.executable, runner], capture_output=True,
                        text=True)
    check("CLI e2e: fixture pipeline runs end to end (exit 0)",
          r4.returncode == 0, r4.stderr.strip()[-200:])
    ok_out = os.path.exists(out_json)
    check("CLI e2e: output written", ok_out)
    if ok_out:
        out = json.load(open(out_json))
        check("CLI e2e: output header (label/claim/disclosure)",
              out["label"] == "DEV EXPLORATORY" and out["claim"] == "NONE"
              and out["disclosure"]["excluded_events_unmatched"] == 1
              and abs(out["disclosure"]["exclusion_rate"] - 1 / 3) < 1e-12
              and "MATCHED SUBPOPULATION ONLY"
              in out["disclosure"]["scope_statement"])
        check("CLI e2e: output values match hand computation",
              out["horizons"]["10"]["mean_paired_excess_atr"] == 4.75
              and abs(out["horizons"]["10"]["mean_paired_excess_pct"]
                      - want_pct) < 1e-12
              and abs(out["cost_sensitivity"]
                      ["primary_paired_excess_pct_minus_round_trip"]
                      - (want_pct - 0.0025)) < 1e-12)

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
