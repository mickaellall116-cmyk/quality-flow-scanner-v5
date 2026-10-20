#!/usr/bin/env python3
"""QF-TD-VALIDATOR-DST-REPAIR-REQUALIFICATION-20261019-44 r1 — proof driver.

ONE offline attempt inside the pinned NL451 env (PMC 4.5.1) under network
isolation. Families (frozen by Issue #1 comment 6282707139):
  A — structural: defect line absent; generated day keys are local
      midnight; public API unchanged; semantic diff limited to the loop.
  B — constructor route: -43 E2 F1-F8 rerun against the CANDIDATE
      validator (civil-date America/New_York enumeration).
  C — regression: the accepted real-validator 28-case NLQUAL matrix
      (pristine mode) rerun against the candidate, twice, byte-identical.
-43 E1 is NOT repeated (calendar code unchanged; proven by the diff).
First material failure stops the run; the failure is recorded, never
repaired. The candidate is bound EXPLICITLY: loaded by file path and
registered in sys.modules as "validate_input" before construct_4h is
imported, so no import-precedence ambiguity exists.
"""
import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO = Path.home() / "workspace" / "quality-flow-scanner-v5"
PILOT = REPO / "research_notes" / "pilot_harness"
FETCH4H = REPO / "canonical_baseline" / "scripts" / "fetch_4h.py"
STAGE = Path("/tmp/td44_stage")
CANDIDATE = STAGE / "candidate_validator.py"
OUTDIR = Path(sys.argv[1])
NY = "America/New_York"
SYMBOL = "SYNTH"

CANDIDATE_SHA = "ca3bafd87e7cb439d538ddf924aa08a029dd2c9bb32b485f61acbeea91429cc6"
EXPECTED_HASHES = {
    "construct_4h.py": "d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd",
    "pilot_build.py": "257d5bb99bcbae50442491b71429abb6b37b8c5cbcd1e4bf93b6010ad9e5a508",
    "validate_input.py": "1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58",
    "fetch_4h.py": "2a4994a26dbb98e244a14173a06697476835206c3d8d268ad21900dd43e0cbeb",
    "td_min_collector.py": "b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c",
}

results = {"task": "QF-TD-VALIDATOR-DST-REPAIR-REQUALIFICATION-20261019-44 r1",
           "candidate_sha256": CANDIDATE_SHA, "hash_gates": {},
           "family_a": None, "family_b_e2": [], "family_c_nlqual": None,
           "verdict": None, "first_failure": None}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class ProofFailure(Exception):
    def __init__(self, key, detail):
        super().__init__(key)
        self.key = key
        self.detail = detail


def fail(key, detail):
    raise ProofFailure(key, detail)


# ---------- explicit candidate binding ------------------------------------
def load_candidate():
    got = sha256_file(CANDIDATE)
    results["hash_gates"]["candidate_validator.py"] = got
    if got != CANDIDATE_SHA:
        fail("HASH_GATE_candidate_validator.py",
             {"expected": CANDIDATE_SHA, "actual": got})
    spec = importlib.util.spec_from_file_location("validate_input", CANDIDATE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["validate_input"] = mod  # bind BEFORE construct_4h import
    spec.loader.exec_module(mod)
    if Path(mod.__file__).resolve() != CANDIDATE.resolve():
        fail("CANDIDATE_BINDING", {"file": str(mod.__file__)})
    results["candidate_binding"] = {
        "method": "importlib by absolute path; registered in "
                  "sys.modules['validate_input'] before construct_4h import",
        "module_file": str(mod.__file__)}
    return mod


def load_construct_4h():
    spec = importlib.util.spec_from_file_location(
        "construct_4h", PILOT / "construct_4h.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------- family A: structural -------------------------------------------
def run_family_a(cand, orig_src, cand_src):
    checks = {}
    checks["defect_line_absent"] = (
        "\n        day += pd.Timedelta(days=1)\n" not in cand_src
        and "    day = ws\n    while day <= we:" not in cand_src)
    checks["civil_enumeration_present"] = (
        "_civil_day = ws.date()" in cand_src
        and "pd.Timestamp(_civil_day).tz_localize(NY)" in cand_src)
    checks["calendar_mechanism_unchanged"] = True  # proven below via AST
    # AST: identical public API; identical bodies except validate().
    def api_and_bodies(src):
        tree = ast.parse(src)
        api, bodies = {}, {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                api[node.name] = ast.dump(node.args)
                bodies[node.name] = ast.dump(node)
            elif isinstance(node, ast.ClassDef):
                api[node.name] = "class"
                bodies[node.name] = ast.dump(node)
        return api, bodies
    o_api, o_bodies = api_and_bodies(orig_src)
    c_api, c_bodies = api_and_bodies(cand_src)
    checks["api_unchanged"] = (o_api == c_api)
    diff_fns = [n for n in o_bodies if o_bodies[n] != c_bodies.get(n)]
    checks["only_validate_body_differs"] = (diff_fns == ["validate"])
    checks["calendar_mechanism_unchanged"] = (
        o_bodies.get("xnys_schedule") == c_bodies.get("xnys_schedule")
        and o_bodies.get("expected_1h_starts")
        == c_bodies.get("expected_1h_starts"))
    # Midnight probe: record every xnys_schedule day-arg during a validate()
    # over the F3 DST-spanning window; all must be local midnights.
    recorded = []
    orig_sched = cand.xnys_schedule
    def spy(day):
        recorded.append(pd.Timestamp(day))
        return orig_sched(day)
    cand.xnys_schedule = spy
    try:
        f3days = ["2025-03-07", "2025-03-10", "2025-03-11", "2025-03-12",
                  "2025-03-13", "2025-03-14"]
        frame = make_frame(days_starts(f3days))
        cand.validate(frame, SYMBOL, "2025-03-07", "2025-03-14", None,
                      as_of=ny_ts("2025-03-14 16:00:00"))
    except Exception as e:
        fail("FAMILY_A_MIDNIGHT_PROBE",
             {"error": f"{type(e).__name__}: {e}"})
    finally:
        cand.xnys_schedule = orig_sched
    checks["probe_calls_recorded"] = len(recorded)
    checks["all_day_keys_local_midnight"] = bool(recorded) and all(
        t.hour == 0 and t.minute == 0 and t.second == 0 for t in recorded)
    results["family_a"] = checks
    if not all(v for k, v in checks.items() if isinstance(v, bool)):
        fail("FAMILY_A_STRUCTURAL", checks)


# ---------- reference route: isolated resample_4h --------------------------
def load_reference():
    src = FETCH4H.read_text()
    tree = ast.parse(src)
    agg_seg = fn_seg = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "AGG":
            agg_seg = ast.get_source_segment(src, node)
        if isinstance(node, ast.FunctionDef) and node.name == "resample_4h":
            fn_seg = ast.get_source_segment(src, node)
    if not agg_seg or not fn_seg:
        fail("E2_REFERENCE_EXTRACT", "AGG/resample_4h not found in fetch_4h.py")
    code = agg_seg + "\n\n\n" + fn_seg + "\n"
    ns = {"pd": pd}
    exec(compile(code, "fetch_4h.py[isolated resample_4h]", "exec"), ns)
    return ns["resample_4h"], hashlib.sha256(code.encode()).hexdigest(), code


# ---------- fixtures (identical to -43 frozen spec) -------------------------
CAND = None        # candidate validator module
CONSTRUCT = None   # construct_4h module


def session_starts(day: pd.Timestamp):
    sched = CAND.xnys_schedule(day)
    if sched is None:
        return []
    return CAND.expected_1h_starts(sched[0], sched[1])


def make_frame(starts):
    rows = {}
    for k, ts in enumerate(starts):
        o = float(100 + k)
        rows[ts] = {"open": o, "high": o + 2.0, "low": o - 2.0,
                    "close": o + 1.0, "volume": float(10000 + 100 * k)}
    df = pd.DataFrame.from_dict(rows, orient="index")
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = None
    return df.sort_index()


def days_starts(dates):
    starts = []
    for d in dates:
        starts.extend(session_starts(pd.Timestamp(d).tz_localize(NY)))
    return sorted(starts)


def ny_ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s).tz_localize(NY)


def serialize(df: pd.DataFrame) -> str:
    lines = []
    for ts, row in df.iterrows():
        lines.append("|".join([
            pd.Timestamp(ts).isoformat(),
            repr(float(row["Open"])), repr(float(row["High"])),
            repr(float(row["Low"])), repr(float(row["Close"])),
            repr(float(row["Volume"]))]))
    return "\n".join(lines)


def ser_hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def cleared_route(df_lower, window_start, window_end, as_of):
    r = subprocess.run([sys.executable, str(PILOT / "verify_sources.py")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fail("E2_SOURCE_VERIFY",
             f"verify_sources exit {r.returncode}: {r.stdout} {r.stderr}")
    report = CAND.validate(df_lower, SYMBOL, window_start, window_end, None,
                           as_of=as_of)
    ends_map = report.get("interval_ends") or {}
    validated_ends = pd.Series(
        {pd.Timestamp(k): pd.Timestamp(v) for k, v in ends_map.items()})
    df2 = df_lower.rename(columns={c: c.capitalize() for c in df_lower.columns})
    bars = CONSTRUCT.construct_4h(df2, SYMBOL, as_of=as_of,
                                  validated_ends=validated_ends)
    return bars, report


# ---------- family B: -43 E2 F1-F8 ------------------------------------------
def compare_pair(fid, df_lower, ws, we, as_of, ref_fn):
    try:
        cleared, _ = cleared_route(df_lower, ws, we, as_of)
    except CAND.ValidationError as e:
        fail("E2_CLEARED_ROUTE_ERROR", {"fixture": fid, "error": str(e)})
    ref = ref_fn(df_lower.rename(
        columns={c: c.capitalize() for c in df_lower.columns}))
    cs, rs = serialize(cleared), serialize(ref)
    entry = {"fixture": fid, "cleared_bars": len(cleared),
             "reference_bars": len(ref), "cleared_sha256": ser_hash(cs),
             "reference_sha256": ser_hash(rs),
             "cleared_serialization": cs, "reference_serialization": rs}
    if cs != rs:
        entry["result"] = "FAIL"
        results["family_b_e2"].append(entry)
        fail(f"E2_{fid}_BYTE_IDENTICAL",
             {"fixture": fid, "cleared_sha256": entry["cleared_sha256"],
              "reference_sha256": entry["reference_sha256"]})
    entry["result"] = "PASS"
    results["family_b_e2"].append(entry)
    return cleared


def run_family_b(ref_fn):
    f1 = make_frame(days_starts(["2025-01-08"]))
    f1_bars = compare_pair("F1", f1, "2025-01-08", "2025-01-08",
                           ny_ts("2025-01-08 16:00:00"), ref_fn)
    f1_first_line = serialize(f1_bars).split("\n")[0]

    f2 = make_frame(days_starts(["2024-11-29"]))
    compare_pair("F2", f2, "2024-11-29", "2024-11-29",
                 ny_ts("2024-11-29 13:00:00"), ref_fn)

    f3days = ["2025-03-07", "2025-03-10", "2025-03-11", "2025-03-12",
              "2025-03-13", "2025-03-14"]
    f3 = make_frame(days_starts(f3days))
    compare_pair("F3", f3, "2025-03-07", "2025-03-14",
                 ny_ts("2025-03-14 16:00:00"), ref_fn)

    f4days = ["2025-10-31", "2025-11-03", "2025-11-04", "2025-11-05",
              "2025-11-06", "2025-11-07"]
    f4 = make_frame(days_starts(f4days))
    compare_pair("F4", f4, "2025-10-31", "2025-11-07",
                 ny_ts("2025-11-07 16:00:00"), ref_fn)

    wide = make_frame(days_starts(["2025-01-06", "2025-01-07", "2025-01-08"]))
    narrow = wide[wide.index.normalize() == ny_ts("2025-01-07 00:00:00")].copy()
    try:
        c_wide, _ = cleared_route(wide, "2025-01-06", "2025-01-08",
                                  ny_ts("2025-01-08 16:00:00"))
        c_narrow, _ = cleared_route(narrow, "2025-01-07", "2025-01-07",
                                    ny_ts("2025-01-07 16:00:00"))
    except CAND.ValidationError as e:
        fail("E2_CLEARED_ROUTE_ERROR", {"fixture": "F5", "error": str(e)})
    cap = {c: c.capitalize() for c in wide.columns}
    r_wide = ref_fn(wide.rename(columns=cap))
    r_narrow = ref_fn(narrow.rename(columns=cap))
    day7 = ny_ts("2025-01-07 00:00:00")
    checks = {
        "cleared_wide_eq_reference_wide":
            serialize(c_wide) == serialize(r_wide),
        "cleared_narrow_eq_reference_narrow":
            serialize(c_narrow) == serialize(r_narrow),
        "cleared_wide_day7_eq_narrow":
            serialize(c_wide[c_wide.index.normalize() == day7]) ==
            serialize(c_narrow),
        "reference_wide_day7_eq_narrow":
            serialize(r_wide[r_wide.index.normalize() == day7]) ==
            serialize(r_narrow),
    }
    entry = {"fixture": "F5", "checks": checks,
             "wide_bars": len(c_wide), "narrow_bars": len(c_narrow),
             "cleared_wide_sha256": ser_hash(serialize(c_wide)),
             "cleared_narrow_sha256": ser_hash(serialize(c_narrow))}
    if not all(checks.values()):
        entry["result"] = "FAIL"
        results["family_b_e2"].append(entry)
        fail("E2_F5_BYTE_IDENTICAL", entry)
    entry["result"] = "PASS"
    results["family_b_e2"].append(entry)

    stray = [ny_ts("2025-01-09 09:30:00"), ny_ts("2025-01-09 10:30:00")]
    f6 = make_frame(stray)
    entry = {"fixture": "F6"}
    try:
        cleared_route(f6, "2025-01-09", "2025-01-09",
                      ny_ts("2025-01-09 16:00:00"))
        entry["result"] = "FAIL"
        entry["cleared_outcome"] = "no exception raised"
        results["family_b_e2"].append(entry)
        fail("E2_F6_VALIDATOR_CONDITION",
             "cleared route did not raise on closed-day stray bars")
    except CAND.ValidationError as e:
        entry["cleared_outcome"] = f"ValidationError: {e}"
        ref6 = ref_fn(f6.rename(columns={c: c.capitalize()
                                         for c in f6.columns}))
        entry["reference_bars"] = len(ref6)
        entry["reference_serialization"] = serialize(ref6)
        entry["reference_divergence"] = "expected (recorded, not promoted)"
        if "V4" not in str(e):
            entry["result"] = "FAIL"
            results["family_b_e2"].append(entry)
            fail("E2_F6_VALIDATOR_CONDITION",
                 {"expected": "V4", "actual": str(e)})
        entry["result"] = "PASS"
        results["family_b_e2"].append(entry)

    starts7 = [s for s in days_starts(["2025-01-08"])
               if not (s.hour == 11 and s.minute == 30)]
    f7 = make_frame(starts7)
    entry = {"fixture": "F7"}
    try:
        cleared_route(f7, "2025-01-08", "2025-01-08",
                      ny_ts("2025-01-08 16:00:00"))
        entry["result"] = "FAIL"
        entry["cleared_outcome"] = "no exception raised"
        results["family_b_e2"].append(entry)
        fail("E2_F7_VALIDATOR_CONDITION",
             "cleared route did not raise on missing due constituent")
    except CAND.ValidationError as e:
        entry["cleared_outcome"] = f"ValidationError: {e}"
        ref7 = ref_fn(f7.rename(columns={c: c.capitalize()
                                         for c in f7.columns}))
        entry["reference_bars"] = len(ref7)
        entry["reference_serialization"] = serialize(ref7)
        entry["reference_divergence"] = "expected (recorded, not promoted)"
        if "V6" not in str(e):
            entry["result"] = "FAIL"
            results["family_b_e2"].append(entry)
            fail("E2_F7_VALIDATOR_CONDITION",
                 {"expected": "V6", "actual": str(e)})
        entry["result"] = "PASS"
        results["family_b_e2"].append(entry)

    starts8 = [s for s in days_starts(["2025-01-08"]) if s.hour <= 13]
    f8 = make_frame(starts8)
    entry = {"fixture": "F8"}
    try:
        c8, _ = cleared_route(f8, "2025-01-08", "2025-01-08",
                              ny_ts("2025-01-08 14:30:00"))
    except CAND.ValidationError as e:
        entry["result"] = "FAIL"
        results["family_b_e2"].append(entry)
        fail("E2_CLEARED_ROUTE_ERROR", {"fixture": "F8", "error": str(e)})
    s8 = serialize(c8)
    entry["cleared_bars"] = len(c8)
    entry["cleared_serialization"] = s8
    ref8 = ref_fn(f8.rename(columns={c: c.capitalize() for c in f8.columns}))
    entry["reference_bars"] = len(ref8)
    entry["reference_serialization"] = serialize(ref8)
    entry["reference_divergence"] = "expected (recorded, not promoted)"
    if len(c8) != 1 or s8 != f1_first_line:
        entry["result"] = "FAIL"
        results["family_b_e2"].append(entry)
        fail("E2_F8_COMPLETED_BINS_ONLY",
             {"expected": f"exactly F1's 09:30 bar: {f1_first_line}",
              "actual": s8})
    entry["result"] = "PASS"
    results["family_b_e2"].append(entry)


# ---------- family C: NLQUAL 28-case regression ------------------------------
def run_family_c():
    runner = STAGE / "run_nlqual_matrix.py"
    cand_dir = STAGE / "nlqual" / "td_lifecycle_repair_candidate"
    supplement = STAGE / "nlqual_supplement.json"
    preserved = (REPO / "research_notes" / "twelve_data_stage0" / "snapshots"
                 / "acquisition_state_spot8" / "receipts"
                 / "REQ-SPT-07.rejected.bin")
    manifest = (REPO / "research_notes"
                / "td_v2_spot_batch_preflight_evidence_20261014"
                / "acquisition_manifest_v2_spot8.json")
    lock = STAGE / "integration_requirements.lock"
    outs = []
    for i in (1, 2):
        out = OUTDIR / f"nlqual_matrix_run{i}.json"
        cmd = [sys.executable, str(runner), "--mode", "pristine",
               "--candidate-dir", str(cand_dir),
               "--supplement", str(supplement),
               "--preserved-body", str(preserved),
               "--manifest", str(manifest),
               "--lock", str(lock), "--out", str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            fail("NLQUAL_REGRESSION",
                 {"run": i, "exit": r.returncode,
                  "stdout_tail": r.stdout[-800:], "stderr_tail": r.stderr[-800:]})
        outs.append(out.read_bytes())
    doc = json.loads(outs[0])
    checks = {"runs": 2, "counts": doc["counts"],
              "byte_identical": outs[0] == outs[1],
              "mechanism_sha_recorded": doc["environment"]
              .get("mechanism_module_sha256")}
    results["family_c_nlqual"] = checks
    if doc["counts"] != {"total": 28, "passed": 28} or outs[0] != outs[1]:
        fail("NLQUAL_REGRESSION", checks)
    if checks["mechanism_sha_recorded"] != CANDIDATE_SHA:
        fail("NLQUAL_MECHANISM_BINDING", checks)


def main():
    global CAND, CONSTRUCT
    paths = {"construct_4h.py": PILOT / "construct_4h.py",
             "pilot_build.py": PILOT / "pilot_build.py",
             "validate_input.py": PILOT / "validate_input.py",
             "fetch_4h.py": FETCH4H,
             "td_min_collector.py": STAGE / "nlqual"
             / "td_lifecycle_repair_candidate" / "td_min_collector.py"}
    for name, p in paths.items():
        got = sha256_file(p)
        results["hash_gates"][name] = got
        if got != EXPECTED_HASHES[name]:
            fail(f"HASH_GATE_{name}", {"expected": EXPECTED_HASHES[name],
                                       "actual": got})
    CAND = load_candidate()
    CONSTRUCT = load_construct_4h()
    import pandas_market_calendars as mcal
    results["environment"] = {
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
        "pandas_market_calendars": mcal.__version__,
    }
    orig_src = (PILOT / "validate_input.py").read_text()
    cand_src = CANDIDATE.read_text()
    run_family_a(CAND, orig_src, cand_src)
    ref_fn, ref_hash, ref_code = load_reference()
    results["reference_isolation"] = {
        "source_file": "canonical_baseline/scripts/fetch_4h.py",
        "method": "AST source-segment extraction of AGG + resample_4h from "
                  "hash-verified bytes (as -43)",
        "executed_source_sha256": ref_hash}
    run_family_b(ref_fn)
    run_family_c()
    results["verdict"] = "TD_VALIDATOR_DST_REPAIR_PASS__CANDIDATE_AWAITING_REVIEW"


if __name__ == "__main__":
    try:
        main()
    except ProofFailure as pf:
        results["first_failure"] = {"key": pf.key, "detail": pf.detail}
        results["verdict"] = f"TD_VALIDATOR_DST_REPAIR_HOLD__{pf.key}"
    except Exception as e:
        import traceback
        results["first_failure"] = {"key": "UNEXPECTED_ERROR",
                                    "detail": f"{type(e).__name__}: {e}",
                                    "traceback": traceback.format_exc()}
        results["verdict"] = "TD_VALIDATOR_DST_REPAIR_HOLD__UNEXPECTED_ERROR"
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "proof_results.json").write_text(
        json.dumps(results, indent=1, default=str))
    print(results["verdict"])
