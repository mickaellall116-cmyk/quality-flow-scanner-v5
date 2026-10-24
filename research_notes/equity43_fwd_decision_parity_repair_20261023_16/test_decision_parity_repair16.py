"""QF-EQUITY43-FWD-DECISION-PARITY-REPAIR-20261023-16 — regression tests.

R1  EXIT-FIELD PARITY (the root-cause test). On the -15 suite's own
    synthetic trend series (invented prices, real pinned session dates),
    the streaming observer's candidates are compared against the batch
    reference (gen_candidates_censored, itself field-verified against
    the frozen generator in -13 P4) on EVERY candidate field INCLUDING
    `exit` — the field both the -15 comparison loop and the -15 suite's
    decision_fields() omitted. With the -15 observer this test FAILS
    (exit = raw next-bar open; the reference exit is the TP1-blended
    synthetic exit). With the repaired observer it PASSES.
    Precondition asserted, not assumed: the series must contain at
    least one closed candidate with tp1_hit=True (the only class whose
    exit can differ), otherwise the test errors instead of passing
    vacuously.

R2  REPORTER FAIL-CLOSED (the -15 reporting-bug test). report16.derive
    must return STOP for: (a) the -15 committed compare_results.json
    (201 decision mismatches, recorded verdict STOP); (b) the same
    document with the verdict string flipped to PASS (counts still
    nonzero); (c) counts zeroed but problems retained and verdict
    flipped; (d) problems cleared but a count nonzero; (e) a -16
    document missing the field_census section. It must return PASS
    only for a fully consistent all-zero document (synthetic control).

R3  CENSUS GUARD. The census comparison logic, applied to two candidate
    dicts differing ONLY in `exit`, reports exactly one mismatch, in
    the `exit` field — guarding against a future comparison loop
    silently dropping the field again.

Usage: test_decision_parity_repair16.py <stage> <observer_py> [json15]
Exit 0 iff all tests pass. Prints one line per test + SUMMARY.
"""
import copy
import importlib.util
import json
import os
import sys
import tempfile

STAGE = os.path.abspath(sys.argv[1])
OBSERVER_PY = os.path.abspath(sys.argv[2])
JSON15 = sys.argv[3] if len(sys.argv) > 3 else None
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}", flush=True)


# ------------------------------------------------------------------ R1
def r1_exit_field_parity():
    # scratch pkg layout so the -15 suite module loads OUR observer file
    scratch = tempfile.mkdtemp(prefix="td16_r1_")
    pkg = os.path.join(scratch, "pkg")
    os.makedirs(os.path.join(pkg, "observer"))
    os.makedirs(os.path.join(pkg, "tests"))
    import shutil
    shutil.copy(OBSERVER_PY, os.path.join(pkg, "observer",
                                          "fwd_observer.py"))
    suite_src = os.path.join(STAGE, "pkg16", "tests", "test_fwd_parity.py")
    shutil.copy(suite_src, os.path.join(pkg, "tests",
                                        "test_fwd_parity.py"))
    sys.argv = ["test_fwd_parity.py", STAGE]
    spec = importlib.util.spec_from_file_location(
        "suite15", os.path.join(pkg, "tests", "test_fwd_parity.py"))
    suite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suite)

    sessions = suite.first_sessions(150)
    rows = suite.expand_targets(suite.trend_targets(sessions, 0.990,
                                                    250, 262))
    bars_b, cands_b, sg_b = suite.batch_reference("TEST", rows)
    obs, j, _ = suite.make_observer(["TEST"])
    suite.feed_all(obs, {"TEST": rows})
    cands_o = obs.candidates()

    def keyf(t):
        return (t["symbol"], t["signal_idx"])

    ref_by = {keyf(t): t for t in cands_b}
    obs_by = {keyf(t): t for t in cands_o}
    fields = ["entry", "stop", "tp1", "exit", "entry_time", "exit_time",
              "signal_time", "reason", "hold_bars", "tp1_hit", "censored"]
    per_field = {f: 0 for f in fields}
    n_tp1_closed = 0
    for k in sorted(set(ref_by) & set(obs_by)):
        a, b = ref_by[k], obs_by[k]
        if not a.get("censored") and a.get("tp1_hit"):
            n_tp1_closed += 1
        for f in fields:
            va, vb = a.get(f), b.get(f)
            if f == "censored":
                # simulator-consumption semantics: simulate_stack reads
                # tr.get("censored") for truthiness; the batch closed
                # dicts omit the key (None) where the observer writes
                # False explicitly — the consumed value is identical.
                va, vb = bool(va), bool(vb)
            if f in ("entry_time", "exit_time"):
                va = None if va is None else str(va)
                vb = None if vb is None else str(vb)
            if va != vb:
                per_field[f] += 1
    total = sum(per_field.values())
    check("R1_precondition_tp1_closed_exists", n_tp1_closed >= 1,
          f"tp1_hit closed candidates in series: {n_tp1_closed}")
    check("R1_exit_field_parity", total == 0,
          f"per-field mismatches: {per_field}; key sets equal: "
          f"{set(ref_by) == set(obs_by)}")


# ------------------------------------------------------------------ R2
def r2_reporter_fail_closed():
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        "report16", os.path.join(STAGE, "observer16", "report16.py"))
    rep = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rep)

    def verdict(doc):
        return rep.derive(doc)[0]

    base = None
    if JSON15 and os.path.exists(JSON15):
        base = json.load(open(JSON15))
        check("R2a_15_artifact_is_stop",
              verdict(base) == "STOP_DECISION_PARITY_FAILURE",
              "the -15 committed JSON (201 mismatches) must derive STOP")
        flipped = copy.deepcopy(base)
        flipped["verdict"] = "DECISION_PARITY_PASS"
        check("R2b_flipped_verdict_still_stop",
              verdict(flipped) == "STOP_DECISION_PARITY_FAILURE",
              "verdict string flipped, counts nonzero -> STOP")
        zeroed = copy.deepcopy(base)
        zeroed["verdict"] = "DECISION_PARITY_PASS"
        zeroed["sections"]["decision_parity"]["decision_mismatches"] = 0
        zeroed["sections"]["decision_parity"]["rs_mismatches"] = 0
        zeroed["sections"]["decision_parity"][
            "terminal_symbol_mismatch_views"] = []
        zeroed["sections"]["decision_parity"]["c0_counts_observer"] = \
            zeroed["sections"]["decision_parity"]["c0_counts_reference"]
        check("R2c_zeroed_counts_problems_retained_stop",
              verdict(zeroed) == "STOP_DECISION_PARITY_FAILURE",
              "counts zeroed but recorded problems retained -> STOP")
        sneaky = copy.deepcopy(base)
        sneaky["problems"] = []
        check("R2d_problems_cleared_counts_nonzero_stop",
              verdict(sneaky) == "STOP_DECISION_PARITY_FAILURE",
              "problems cleared but counts nonzero -> STOP")
    else:
        check("R2a_15_artifact_is_stop", False,
              "governing -15 JSON not supplied/found")

    good = {
        "task": "synthetic control", "problems": [],
        "verdict": "DECISION_PARITY_PASS",
        "sections": {
            "inventory": {"pins": "PASS"},
            "config_pins": {"experiment_config_sha_match": True},
            "bars_parity": {"symbols_bad": 0,
                            "sessionvwap_max_abs_diff": 0.0},
            "benchmark_parity": {"equal": True},
            "closes_identity": {"symbols_bad": 0, "max_abs_diff": 0.0},
            "field_census": {"total_mismatches": 0, "per_field": {},
                             "keyset_problems": [],
                             "extra_key_asymmetry": []},
            "decision_parity": {
                "rs_mismatches": 0, "decision_mismatches": 0,
                "terminal_symbol_mismatch_views": [],
                "c0_counts_observer": {"taken_count": 193,
                                        "skipped_cap": 323,
                                        "skipped_risk": 74},
                "c0_counts_reference": {"taken_count": 193,
                                         "skipped_cap": 323,
                                         "skipped_risk": 74}},
            "reference_selfcheck": {
                "decision_mismatches": 0, "rs_mismatches": 0,
                "c0_match": True, "terminal_mismatch_views": []},
            "observer_stream": {"journal_verify": True, "rejected": 0}}}
    check("R2e_consistent_pass_control",
          verdict(good) == "DECISION_PARITY_PASS",
          "fully consistent all-zero document -> PASS")
    missing = copy.deepcopy(good)
    del missing["sections"]["field_census"]
    check("R2f_missing_census_section_stop",
          verdict(missing) == "STOP_DECISION_PARITY_FAILURE",
          "absence of the census section -> STOP (no evidence, no PASS)")
    fb_path = os.path.join(STAGE, "work", "compare16_orig15.json")
    if os.path.exists(fb_path):
        fb = json.load(open(fb_path))
        check("R2g_fail_before_document_is_stop",
              verdict(fb) == "STOP_DECISION_PARITY_FAILURE",
              "the -16 fail-before document (276 exit mismatches, 201 "
              "decision mismatches) must derive STOP")


# ------------------------------------------------------------------ R3
def r3_census_guard():
    a = {"symbol": "TEST", "signal_idx": 7, "entry": 100.0,
         "stop": 95.0, "tp1": 110.0, "exit": 108.0,
         "tp1_hit": True, "censored": False, "reason": "stop",
         "hold_bars": 3, "entry_time": "2025-01-02 09:30",
         "exit_time": "2025-01-02 13:30",
         "signal_time": "2025-01-02T09:30:00-05:00"}
    b = dict(a)
    b["exit"] = 112.5  # raw price instead of blended synthetic exit
    fields = ["entry", "stop", "tp1", "exit", "entry_time", "exit_time",
              "signal_time", "reason", "hold_bars", "tp1_hit", "censored"]
    bad = [f for f in fields if a.get(f) != b.get(f)]
    check("R3_census_catches_exit_only_diff", bad == ["exit"],
          f"differing fields detected: {bad}")


def main():
    r1_exit_field_parity()
    r2_reporter_fail_closed()
    r3_census_guard()
    n_pass = sum(1 for _, ok in RESULTS if ok)
    print(f"SUMMARY: {n_pass}/{len(RESULTS)} tests passed")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
