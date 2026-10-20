#!/usr/bin/env python3
"""QF-TD-CONSTRUCTOR-EQUIVALENCE-PROOF-20261019-43 r1 — proof driver (FROZEN).

Executes E1 (calendar equivalence, 761 dates) and E2 (8 synthetic fixtures)
exactly as frozen in PROOF_SPEC_FROZEN.md, inside the pinned NL451 env
(PMC 4.5.1) under network isolation. First material failure stops the run;
the failure is recorded, never repaired. Writes proof_results.json next to
this file's output dir (argv[1]) and prints the terminal verdict line.
"""
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO = Path.home() / "workspace" / "quality-flow-scanner-v5"
PILOT = REPO / "research_notes" / "pilot_harness"
ARTIFACT = (REPO / "research_notes" /
            "xnys_isolated_calendar_generation_20261019_35_r2" /
            "XNYS_SESSION_SCHEDULE_V2.json")
FETCH4H = REPO / "canonical_baseline" / "scripts" / "fetch_4h.py"
OUTDIR = Path(sys.argv[1])
NY = "America/New_York"
SYMBOL = "SYNTH"

sys.path.insert(0, str(PILOT))
from validate_input import (validate, ValidationError, xnys_schedule,
                            expected_1h_starts)
from construct_4h import construct_4h, session_close_et

EXPECTED_HASHES = {
    "construct_4h.py": "d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd",
    "pilot_build.py": "257d5bb99bcbae50442491b71429abb6b37b8c5cbcd1e4bf93b6010ad9e5a508",
    "validate_input.py": "1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58",
    "fetch_4h.py": "2a4994a26dbb98e244a14173a06697476835206c3d8d268ad21900dd43e0cbeb",
    "XNYS_SESSION_SCHEDULE_V2.json": "3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88",
}

results = {"task": "QF-TD-CONSTRUCTOR-EQUIVALENCE-PROOF-20261019-43 r1",
           "hash_gates": {}, "e1": None, "e2": [], "verdict": None,
           "first_failure": None}


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


# ---------- reference route: isolated resample_4h from verified bytes ----
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


# ---------- cleared route: pilot_build steps 2-3 in-process --------------
def cleared_route(df_lower, window_start, window_end, as_of):
    r = subprocess.run([sys.executable, str(PILOT / "verify_sources.py")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fail("E2_SOURCE_VERIFY",
             f"verify_sources exit {r.returncode}: {r.stdout} {r.stderr}")
    report = validate(df_lower, SYMBOL, window_start, window_end, None,
                      as_of=as_of)
    ends_map = report.get("interval_ends") or {}
    validated_ends = pd.Series(
        {pd.Timestamp(k): pd.Timestamp(v) for k, v in ends_map.items()})
    df2 = df_lower.rename(columns={c: c.capitalize() for c in df_lower.columns})
    bars = construct_4h(df2, SYMBOL, as_of=as_of,
                        validated_ends=validated_ends)
    return bars, report


# ---------- synthetic fixture bars ---------------------------------------
def session_starts(day: pd.Timestamp):
    sched = xnys_schedule(day)
    if sched is None:
        return []
    return expected_1h_starts(sched[0], sched[1])


def make_frame(starts):
    """Deterministic synthetic 1H bars for the given chronological starts."""
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


# ---------- E1 ------------------------------------------------------------
def run_e1():
    art = json.loads(ARTIFACT.read_text())
    if art.get("coverage_start") != "2024-09-16" or \
       art.get("coverage_end") != "2026-10-16" or \
       len(art.get("sessions", [])) != 524:
        fail("E1_ARTIFACT_SHAPE",
             f"coverage {art.get('coverage_start')}..{art.get('coverage_end')}, "
             f"sessions={len(art.get('sessions', []))}")
    sessions = {s["date"]: s for s in art["sessions"]}
    all_dates = pd.date_range("2024-09-16", "2026-10-16", freq="D")
    if len(all_dates) != 761:
        fail("E1_ARTIFACT_SHAPE", f"coverage span has {len(all_dates)} dates")
    close_matches = closed_matches = 0
    for d in all_dates:
        ds = d.strftime("%Y-%m-%d")
        if ds in sessions:
            exp = ny_ts(f"{ds} {sessions[ds]['close']}:00")
            try:
                got = session_close_et(d)
            except Exception as e:
                fail("E1_SESSION_RAISED",
                     {"date": ds, "expected": exp.isoformat(),
                      "actual": f"{type(e).__name__}: {e}"})
            if pd.Timestamp(got) != exp:
                fail("E1_CLOSE_MISMATCH",
                     {"date": ds, "expected": exp.isoformat(),
                      "actual": pd.Timestamp(got).isoformat()})
            close_matches += 1
        else:
            try:
                got = session_close_et(d)
            except ValueError:
                closed_matches += 1
                continue
            except Exception as e:
                fail("E1_CLOSED_DATE_WRONG_EXCEPTION",
                     {"date": ds, "expected": "ValueError",
                      "actual": f"{type(e).__name__}: {e}"})
            fail("E1_CLOSED_DATE_NO_RAISE",
                 {"date": ds, "expected": "ValueError (closed date)",
                  "actual": pd.Timestamp(got).isoformat()})
    results["e1"] = {"total_dates": 761, "sessions": 524,
                     "close_matches": close_matches,
                     "closed_date_matches": closed_matches,
                     "checked": close_matches + closed_matches,
                     "result": "PASS"}


# ---------- E2 ------------------------------------------------------------
def compare_pair(fid, df_lower, ws, we, as_of, ref_fn):
    try:
        cleared, _ = cleared_route(df_lower, ws, we, as_of)
    except ValidationError as e:
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
        results["e2"].append(entry)
        fail(f"E2_{fid}_BYTE_IDENTICAL",
             {"fixture": fid, "cleared_sha256": entry["cleared_sha256"],
              "reference_sha256": entry["reference_sha256"]})
    entry["result"] = "PASS"
    results["e2"].append(entry)
    return cleared


def run_e2(ref_fn):
    # F1 regular day
    f1 = make_frame(days_starts(["2025-01-08"]))
    f1_bars = compare_pair("F1", f1, "2025-01-08", "2025-01-08",
                           ny_ts("2025-01-08 16:00:00"), ref_fn)
    f1_first_line = serialize(f1_bars).split("\n")[0]

    # F2 early close
    f2 = make_frame(days_starts(["2024-11-29"]))
    compare_pair("F2", f2, "2024-11-29", "2024-11-29",
                 ny_ts("2024-11-29 13:00:00"), ref_fn)

    # F3 DST-spring week (window spans EST Fri + EDT Mon-Fri + closed wknd)
    f3days = ["2025-03-07", "2025-03-10", "2025-03-11", "2025-03-12",
              "2025-03-13", "2025-03-14"]
    f3 = make_frame(days_starts(f3days))
    compare_pair("F3", f3, "2025-03-07", "2025-03-14",
                 ny_ts("2025-03-14 16:00:00"), ref_fn)

    # F4 DST-fall week
    f4days = ["2025-10-31", "2025-11-03", "2025-11-04", "2025-11-05",
              "2025-11-06", "2025-11-07"]
    f4 = make_frame(days_starts(f4days))
    compare_pair("F4", f4, "2025-10-31", "2025-11-07",
                 ny_ts("2025-11-07 16:00:00"), ref_fn)

    # F5 two window lengths over identical bars
    wide = make_frame(days_starts(["2025-01-06", "2025-01-07", "2025-01-08"]))
    narrow = wide[wide.index.normalize() == ny_ts("2025-01-07 00:00:00")].copy()
    try:
        c_wide, _ = cleared_route(wide, "2025-01-06", "2025-01-08",
                                  ny_ts("2025-01-08 16:00:00"))
        c_narrow, _ = cleared_route(narrow, "2025-01-07", "2025-01-07",
                                    ny_ts("2025-01-07 16:00:00"))
    except ValidationError as e:
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
        results["e2"].append(entry)
        fail("E2_F5_BYTE_IDENTICAL", entry)
    entry["result"] = "PASS"
    results["e2"].append(entry)

    # F6 closed day (2025-01-09 Carter closure) with stray bars
    stray = [ny_ts("2025-01-09 09:30:00"), ny_ts("2025-01-09 10:30:00")]
    f6 = make_frame(stray)
    entry = {"fixture": "F6"}
    try:
        cleared_route(f6, "2025-01-09", "2025-01-09",
                      ny_ts("2025-01-09 16:00:00"))
        entry["result"] = "FAIL"
        entry["cleared_outcome"] = "no exception raised"
        results["e2"].append(entry)
        fail("E2_F6_VALIDATOR_CONDITION",
             "cleared route did not raise on closed-day stray bars")
    except ValidationError as e:
        entry["cleared_outcome"] = f"ValidationError: {e}"
        ref6 = ref_fn(f6.rename(columns={c: c.capitalize()
                                         for c in f6.columns}))
        entry["reference_bars"] = len(ref6)
        entry["reference_serialization"] = serialize(ref6)
        entry["reference_divergence"] = "expected (recorded, not promoted)"
        if "V4" not in str(e):
            entry["result"] = "FAIL"
            results["e2"].append(entry)
            fail("E2_F6_VALIDATOR_CONDITION",
                 {"expected": "V4", "actual": str(e)})
        entry["result"] = "PASS"
        results["e2"].append(entry)

    # F7 missing due constituent (11:30 bar of 2025-01-08 omitted)
    starts7 = [s for s in days_starts(["2025-01-08"])
               if not (s.hour == 11 and s.minute == 30)]
    f7 = make_frame(starts7)
    entry = {"fixture": "F7"}
    try:
        cleared_route(f7, "2025-01-08", "2025-01-08",
                      ny_ts("2025-01-08 16:00:00"))
        entry["result"] = "FAIL"
        entry["cleared_outcome"] = "no exception raised"
        results["e2"].append(entry)
        fail("E2_F7_VALIDATOR_CONDITION",
             "cleared route did not raise on missing due constituent")
    except ValidationError as e:
        entry["cleared_outcome"] = f"ValidationError: {e}"
        ref7 = ref_fn(f7.rename(columns={c: c.capitalize()
                                         for c in f7.columns}))
        entry["reference_bars"] = len(ref7)
        entry["reference_serialization"] = serialize(ref7)
        entry["reference_divergence"] = "expected (recorded, not promoted)"
        if "V6" not in str(e):
            entry["result"] = "FAIL"
            results["e2"].append(entry)
            fail("E2_F7_VALIDATOR_CONDITION",
                 {"expected": "V6", "actual": str(e)})
        entry["result"] = "PASS"
        results["e2"].append(entry)

    # F8 mid-day as-of (14:30) — completed bins only
    starts8 = [s for s in days_starts(["2025-01-08"]) if s.hour <= 13]
    f8 = make_frame(starts8)
    entry = {"fixture": "F8"}
    try:
        c8, _ = cleared_route(f8, "2025-01-08", "2025-01-08",
                              ny_ts("2025-01-08 14:30:00"))
    except ValidationError as e:
        entry["result"] = "FAIL"
        results["e2"].append(entry)
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
        results["e2"].append(entry)
        fail("E2_F8_COMPLETED_BINS_ONLY",
             {"expected": f"exactly F1's 09:30 bar: {f1_first_line}",
              "actual": s8})
    entry["result"] = "PASS"
    results["e2"].append(entry)


def main():
    # Hash gates (in-driver re-verification of the exact imported bytes).
    paths = {"construct_4h.py": PILOT / "construct_4h.py",
             "pilot_build.py": PILOT / "pilot_build.py",
             "validate_input.py": PILOT / "validate_input.py",
             "fetch_4h.py": FETCH4H,
             "XNYS_SESSION_SCHEDULE_V2.json": ARTIFACT}
    for name, p in paths.items():
        got = sha256_file(p)
        results["hash_gates"][name] = got
        if got != EXPECTED_HASHES[name]:
            fail(f"HASH_GATE_{name}", {"expected": EXPECTED_HASHES[name],
                                       "actual": got})
    import pandas_market_calendars as mcal
    results["environment"] = {
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
        "pandas_market_calendars": mcal.__version__,
    }
    ref_fn, ref_hash, ref_code = load_reference()
    results["reference_isolation"] = {
        "source_file": "canonical_baseline/scripts/fetch_4h.py",
        "method": "AST source-segment extraction of AGG + resample_4h from "
                  "hash-verified bytes; module import impossible in pinned "
                  "env (yfinance absent from offline wheelhouse)",
        "executed_source_sha256": ref_hash,
        "executed_source": ref_code}
    run_e1()
    run_e2(ref_fn)
    results["verdict"] = ("TD_CONSTRUCTOR_EQUIVALENCE_PROOF_PASS__"
                          "AWAITING_ROUTE_ADJUDICATION")


if __name__ == "__main__":
    try:
        main()
    except ProofFailure as pf:
        results["first_failure"] = {"key": pf.key, "detail": pf.detail}
        results["verdict"] = f"TD_CONSTRUCTOR_EQUIVALENCE_PROOF_HOLD__{pf.key}"
    except Exception as e:  # unexpected — still a stopping failure, reported
        import traceback
        results["first_failure"] = {"key": "UNEXPECTED_ERROR",
                                    "detail": f"{type(e).__name__}: {e}",
                                    "traceback": traceback.format_exc()}
        results["verdict"] = "TD_CONSTRUCTOR_EQUIVALENCE_PROOF_HOLD__UNEXPECTED_ERROR"
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "proof_results.json").write_text(
        json.dumps(results, indent=1, default=str))
    print(results["verdict"])
