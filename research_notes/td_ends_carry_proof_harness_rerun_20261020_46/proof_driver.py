#!/usr/bin/env python3
"""QF-TD-ENDS-CARRY-PROOF-HARNESS-RERUN-20261020-46 r1 — proof driver.

ONE offline attempt inside the pinned NL451 env (PMC 4.5.1) under network
isolation. Spec: Issue #1 comment 6284381091. This driver is the -45
proof driver (sha256 a20b1ec3d24ca9aa2a2bc7962e8aa91431e25b74f836d2b6dc6350bc7e442d87)
with EXACTLY ONE semantic correction: timezone-aware Series inspection
in Family D uses .array (tz-aware DatetimeArray), never .values (which
strips tz under pandas 2.2.3 — the -45 first failure). Expected
instants, fixture generation, assertions, order, bindings, and both
candidate byte streams are unchanged. Families, in order:
  A — structural: entrypoint candidate diff discipline (AST: only main()
      differs + the one decoder helper added; decode call sits inside
      main()'s existing (TypeError, ValueError) handled block); calendar
      mechanism unchanged (validator candidate is the byte-identical -44
      file, hash-gated).
  D — decoder contract proof: single-offset and mixed-offset report maps
      decode to tz-aware non-object dtype preserving every instant;
      spring/fall DST maps preserve local wall-clock/offset truth;
      naive/malformed/duplicate-instant inputs fail closed (ValueError).
  B — -43 E2 F1-F8 rerun from F1 through the candidate pair route:
      verify_sources -> candidate validator -> CANDIDATE ENTRYPOINT
      decoder -> unchanged construct_4h.
  C — only after B is 8/8: the accepted real-validator NLQUAL 28-case
      matrix (pristine, twice, byte-identical) against validator
      candidate ca3bafd8.
-43 E1 is NOT repeated (calendar mechanism unchanged; proven by hash +
Family A). First material failure stops the run; recorded, never repaired.
Bindings are EXPLICIT: candidate validator loaded by path and registered
in sys.modules['validate_input'], pinned construct_4h registered in
sys.modules['construct_4h'], BEFORE the entrypoint candidate is loaded,
so the candidate's own imports resolve to the bound modules.
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
STAGE = Path("/tmp/td46_stage")
CAND_VAL = STAGE / "candidate_validator.py"
CAND_ENT = STAGE / "candidate_entrypoint.py"
OUTDIR = Path(sys.argv[1])
NY = "America/New_York"
SYMBOL = "SYNTH"

CAND_VAL_SHA = "ca3bafd87e7cb439d538ddf924aa08a029dd2c9bb32b485f61acbeea91429cc6"
CAND_ENT_SHA = "442e56cc16bbbb7ba8f3a62910d92bfcd07d85d0bb88ca2346d26b0bdcd2cba6"
EXPECTED_HASHES = {
    "construct_4h.py": "d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd",
    "pilot_build.py": "257d5bb99bcbae50442491b71429abb6b37b8c5cbcd1e4bf93b6010ad9e5a508",
    "validate_input.py": "1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58",
    "fetch_4h.py": "2a4994a26dbb98e244a14173a06697476835206c3d8d268ad21900dd43e0cbeb",
    "td_min_collector.py": "b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c",
}

results = {"task": "QF-TD-ENDS-CARRY-PROOF-HARNESS-RERUN-20261020-46 r1",
           "candidate_validator_sha256": CAND_VAL_SHA,
           "candidate_entrypoint_sha256": CAND_ENT_SHA,
           "hash_gates": {}, "family_a": None, "family_d_contract": None,
           "family_b_e2": [], "family_c_nlqual": None,
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


# ---------- explicit bindings ----------------------------------------------
def load_module(name, path, sha, gate_name):
    got = sha256_file(path)
    results["hash_gates"][gate_name] = got
    if got != sha:
        fail(f"HASH_GATE_{gate_name}", {"expected": sha, "actual": got})
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # bind BEFORE dependents import
    spec.loader.exec_module(mod)
    if Path(mod.__file__).resolve() != path.resolve():
        fail("CANDIDATE_BINDING", {"module": name, "file": str(mod.__file__)})
    return mod


# ---------- family A: structural -------------------------------------------
def run_family_a(entry_mod):
    orig_src = (PILOT / "pilot_build.py").read_text()
    cand_src = CAND_ENT.read_text()
    checks = {}
    # decoder defect shape absent; decoder present
    checks["v5_object_rebuild_absent"] = (
        "validated_ends = pd.Series(\n        {pd.Timestamp(k): pd.Timestamp(v)"
        not in cand_src)
    checks["decoder_present"] = "def _decode_validated_ends(ends_map):" in cand_src

    def top_level(src):
        tree = ast.parse(src)
        items = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                items[node.name] = (ast.dump(node.args), ast.dump(node))
            elif isinstance(node, ast.ClassDef):
                items[node.name] = ("class", ast.dump(node))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                items[f"import:{ast.dump(node)}"] = ("import", ast.dump(node))
            elif isinstance(node, ast.Assign):
                items[f"assign:{ast.dump(node.targets[0])}"] = (
                    "assign", ast.dump(node))
        return tree, items
    o_tree, o_items = top_level(orig_src)
    c_tree, c_items = top_level(cand_src)
    checks["main_args_unchanged"] = (
        o_items["main"][0] == c_items["main"][0])
    new_items = sorted(set(c_items) - set(o_items))
    checks["only_decoder_helper_added"] = (new_items == ["_decode_validated_ends"])
    removed = sorted(set(o_items) - set(c_items))
    checks["nothing_removed"] = (removed == [])
    changed = sorted(n for n in set(o_items) & set(c_items)
                     if o_items[n][1] != c_items[n][1])
    checks["only_main_body_differs"] = (changed == ["main"])
    # decode call inside main()'s existing (TypeError, ValueError) block,
    # whose handler returns 2 (the entrypoint's handled construction path)
    main_fn = next(n for n in c_tree.body
                   if isinstance(n, ast.FunctionDef) and n.name == "main")
    handled = False
    for node in ast.walk(main_fn):
        if isinstance(node, ast.Try):
            calls_decode = any(
                isinstance(x, ast.Call)
                and isinstance(x.func, ast.Name)
                and x.func.id == "_decode_validated_ends"
                for x in ast.walk(node))
            if not calls_decode:
                continue
            for h in node.handlers:
                t = h.type
                names = set()
                if isinstance(t, ast.Tuple):
                    names = {e.id for e in t.elts if isinstance(e, ast.Name)}
                elif isinstance(t, ast.Name):
                    names = {t.id}
                returns2 = any(isinstance(x, ast.Return)
                               and isinstance(x.value, ast.Constant)
                               and x.value.value == 2
                               for x in ast.walk(h))
                if {"TypeError", "ValueError"} <= names and returns2:
                    handled = True
    checks["decode_in_existing_handled_block"] = handled
    # bindings: candidate entrypoint imported the BOUND modules
    checks["entrypoint_validate_is_candidate"] = (
        entry_mod.validate is CAND.validate)
    checks["entrypoint_validationerror_is_candidate"] = (
        entry_mod.ValidationError is CAND.ValidationError)
    checks["entrypoint_construct_is_pinned"] = (
        entry_mod.construct_4h is CONSTRUCT.construct_4h)
    results["family_a"] = checks
    if not all(v for k, v in checks.items() if isinstance(v, bool)):
        fail("FAMILY_A_STRUCTURAL", checks)


# ---------- fixtures (identical to -43/-44 frozen spec) ---------------------
CAND = None        # candidate validator module
CONSTRUCT = None   # pinned construct_4h module
ENTRY = None       # candidate entrypoint module


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


# ---------- family D: decoder contract proof --------------------------------
def _instants(ts_iter):
    return sorted(pd.Timestamp(t).tz_convert("UTC") for t in ts_iter)


def run_family_d():
    dec = ENTRY._decode_validated_ends
    counters = {}

    def check_map(name, ends_map, expect_wallclock_truth):
        s = dec(ends_map)
        n = len(ends_map)
        ok_dtype = (str(s.dtype) != "object"
                    and getattr(s.dtype, "tz", None) is not None
                    and str(getattr(s.dtype, "tz", "")) == NY
                    and getattr(s.index.dtype, "tz", None) is not None)
        ok_keys = _instants([pd.Timestamp(k) for k in ends_map]) == \
            _instants(list(s.index))
        ok_vals = _instants([pd.Timestamp(v) for v in ends_map.values()]) == \
            _instants(list(s.array))
        ok_wall = True
        if expect_wallclock_truth:
            # report strings are NY-local ISO: canonical NY isoformat
            # must reproduce every original string exactly.
            ok_wall = all(
                pd.Timestamp(k).tz_convert("UTC").tz_convert(NY).isoformat()
                == pd.Timestamp(k).isoformat() for k in ends_map)
        counters[name] = {"n": n, "dtype": str(s.dtype),
                          "non_object_tz_aware": bool(ok_dtype),
                          "key_instants_preserved": bool(ok_keys),
                          "value_instants_preserved": bool(ok_vals),
                          "wallclock_truth": bool(ok_wall)}
        if not (ok_dtype and ok_keys and ok_vals and ok_wall):
            fail("DECODER_CONTRACT", {name: counters[name]})

    # real report maps from the candidate validator
    f1 = make_frame(days_starts(["2025-01-08"]))
    rep1 = CAND.validate(f1, SYMBOL, "2025-01-08", "2025-01-08", None,
                         as_of=ny_ts("2025-01-08 16:00:00"))
    check_map("single_offset_real_report", rep1["interval_ends"], True)
    f3days = ["2025-03-07", "2025-03-10", "2025-03-11", "2025-03-12",
              "2025-03-13", "2025-03-14"]
    f3 = make_frame(days_starts(f3days))
    rep3 = CAND.validate(f3, SYMBOL, "2025-03-07", "2025-03-14", None,
                         as_of=ny_ts("2025-03-14 16:00:00"))
    offs = {pd.Timestamp(k).utcoffset() for k in rep3["interval_ends"]}
    counters["mixed_offset_real_report_offsets"] = sorted(str(o) for o in offs)
    if len(offs) < 2:
        fail("DECODER_CONTRACT",
             {"mixed_fixture_not_mixed": counters["mixed_offset_real_report_offsets"]})
    check_map("mixed_offset_spring_real_report", rep3["interval_ends"], True)
    # fall DST: the ambiguous 01:30 occurs twice (EDT then EST) — two
    # distinct instants, same wall clock, both preserved.
    fall_map = {
        "2025-11-02T00:30:00-04:00": "2025-11-02T01:30:00-04:00",
        "2025-11-02T01:30:00-04:00": "2025-11-02T01:30:00-05:00",
        "2025-11-02T01:30:00-05:00": "2025-11-02T02:30:00-05:00",
    }
    s_fall = dec(fall_map)
    counters["fall_dst_ambiguous_pair"] = {
        "n": len(s_fall),
        "distinct_instants": len(set(_instants(list(s_fall.index)))) == 3,
        "wallclocks": [t.strftime("%H:%M") for t in s_fall.index],
        "offsets": [str(t.utcoffset()) for t in s_fall.index]}
    if not (len(s_fall) == 3 and counters["fall_dst_ambiguous_pair"]
            ["distinct_instants"]):
        fail("DECODER_CONTRACT", {"fall": counters["fall_dst_ambiguous_pair"]})
    check_map("fall_dst_map", fall_map, True)
    # fail-closed rejections (ValueError = the entrypoint's handled type)
    bad = {
        "naive_key": {"2025-01-08T09:30:00": "2025-01-08T10:30:00-05:00"},
        "naive_value": {"2025-01-08T09:30:00-05:00": "2025-01-08T10:30:00"},
        "malformed_key": {"not-a-timestamp": "2025-01-08T10:30:00-05:00"},
        "malformed_value": {"2025-01-08T09:30:00-05:00": "garbage"},
        "duplicate_instant": {
            "2025-03-09T03:30:00-04:00": "2025-03-09T04:30:00-04:00",
            "2025-03-09T07:30:00+00:00": "2025-03-09T08:30:00+00:00"},
    }
    rej = {}
    for name, m in bad.items():
        try:
            dec(m)
            rej[name] = "NO ERROR RAISED"
        except ValueError as e:
            rej[name] = f"ValueError: {e}"[:120]
        except Exception as e:
            rej[name] = f"WRONG TYPE {type(e).__name__}: {e}"[:120]
    counters["rejections"] = rej
    if not all(v.startswith("ValueError") for v in rej.values()):
        fail("DECODER_CONTRACT", {"rejections": rej})
    results["family_d_contract"] = counters


# ---------- reference route: isolated resample_4h ---------------------------
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
    validated_ends = ENTRY._decode_validated_ends(ends_map)
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
    if checks["mechanism_sha_recorded"] != CAND_VAL_SHA:
        fail("NLQUAL_MECHANISM_BINDING", checks)


def main():
    global CAND, CONSTRUCT, ENTRY
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
    CAND = load_module("validate_input", CAND_VAL, CAND_VAL_SHA,
                       "candidate_validator.py")
    CONSTRUCT = load_module("construct_4h", PILOT / "construct_4h.py",
                            EXPECTED_HASHES["construct_4h.py"],
                            "construct_4h_binding.py")
    ENTRY = load_module("pilot_build_candidate", CAND_ENT, CAND_ENT_SHA,
                        "candidate_entrypoint.py")
    results["bindings"] = {
        "validator_candidate": {
            "method": "importlib by absolute path; registered in "
                      "sys.modules['validate_input'] before dependents",
            "module_file": str(CAND.__file__), "sha256": CAND_VAL_SHA},
        "constructor": {
            "method": "pinned pilot_harness/construct_4h.py by path; "
                      "registered in sys.modules['construct_4h']",
            "module_file": str(CONSTRUCT.__file__),
            "sha256": EXPECTED_HASHES["construct_4h.py"]},
        "entrypoint_candidate": {
            "method": "importlib by absolute path AFTER validate_input "
                      "and construct_4h bindings; its own imports "
                      "resolved to the bound modules (Family A checks)",
            "module_file": str(ENTRY.__file__), "sha256": CAND_ENT_SHA}}
    import pandas_market_calendars as mcal
    results["environment"] = {
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
        "pandas_market_calendars": mcal.__version__,
    }
    run_family_a(ENTRY)
    run_family_d()
    ref_fn, ref_hash, ref_code = load_reference()
    results["reference_isolation"] = {
        "source_file": "canonical_baseline/scripts/fetch_4h.py",
        "method": "AST source-segment extraction of AGG + resample_4h from "
                  "hash-verified bytes (as -43/-44)",
        "executed_source_sha256": ref_hash}
    run_family_b(ref_fn)
    run_family_c()
    results["verdict"] = \
        "TD_ENDS_CARRY_PROOF_PASS__ROUTE_CANDIDATE_AWAITING_REVIEW"


if __name__ == "__main__":
    try:
        main()
    except ProofFailure as pf:
        results["first_failure"] = {"key": pf.key, "detail": pf.detail}
        results["verdict"] = f"TD_ENDS_CARRY_PROOF_HOLD__{pf.key}"
    except Exception as e:
        import traceback
        results["first_failure"] = {"key": "UNEXPECTED_ERROR",
                                    "detail": f"{type(e).__name__}: {e}",
                                    "traceback": traceback.format_exc()}
        results["verdict"] = "TD_ENDS_CARRY_PROOF_HOLD__UNEXPECTED_ERROR"
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "proof_results.json").write_text(
        json.dumps(results, indent=1, default=str))
    print(results["verdict"])
