"""QF-EQUITY43-S1-CAUSALITY-GUARDS-20261023-17 — reporter negative
battery + controls for report17.py (and the report16 hole demonstration).

Usage: test_reporter17.py <patched.json> <orig15.json> <compare15.json>
       <report17.py> <report16.py>
Exit 0 iff every check passes. Prints one line per check + SUMMARY.
"""
import copy
import importlib.util
import json
import subprocess
import sys

PATCHED, ORIG15, COMP15, REP17, REP16 = sys.argv[1:6]
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}", flush=True)


def load_mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rep17 = load_mod(REP17, "report17")
rep16 = load_mod(REP16, "report16")
patched = json.load(open(PATCHED))
orig15 = json.load(open(ORIG15))
comp15 = json.load(open(COMP15))


def verdict17(doc):
    return rep17.derive(doc)[0]


def verdict16(doc):
    return rep16.derive(doc)[0]


# ------------------------------------------------------------- controls
v, reasons = rep17.derive(patched)
check("C1_patched_passes_report17", v == "DECISION_PARITY_PASS",
      f"verdict={v} reasons={reasons[:2]}")
check("C2_orig15_stops_report17", verdict17(orig15) == rep17.STOP)
check("C3_artifact15_stops_report17", verdict17(comp15) == rep17.STOP)
check("C4_patched_passes_report16_too",
      verdict16(patched) == "DECISION_PARITY_PASS")


# ------------------------------------------- the adjudication exploit
def mut_exit_removed(doc):
    d = copy.deepcopy(doc)
    del d["sections"]["field_census"]["per_field"]["exit"]
    del d["sections"]["field_census"]["detail"]["exit"]
    return d


hole = mut_exit_removed(patched)
check("H0_report16_hole_reproduced",
      verdict16(hole) == "DECISION_PARITY_PASS",
      "report16 re-derives PASS with the exit census deleted")
v, reasons = rep17.derive(hole)
check("H1_report17_closes_hole", v == rep17.STOP,
      f"reasons={reasons[:2]}")


# ------------------------------------------------------ negative battery
def mut(fn):
    d = copy.deepcopy(patched)
    fn(d)
    return d


BATTERY = {
    "N01_exit_detail_removed": lambda d: d["sections"]["field_census"]
        ["detail"].__delitem__("exit"),
    "N02_exit_perfield_removed": lambda d: d["sections"]["field_census"]
        ["per_field"].__delitem__("exit"),
    "N03_compared_counts_zeroed": lambda d: [
        d["sections"]["field_census"]["detail"][f]
        .__setitem__("compared", 0)
        for f in d["sections"]["field_census"]["detail"]],
    "N04_section_renamed": lambda d: d["sections"]
        .__setitem__("field_census_v2",
                     d["sections"].pop("field_census")),
    "N05_reference_absent": lambda d: d["sections"]
        .__delitem__("reference"),
    "N06_bars_cohort_emptied": lambda d: d["sections"]["bars_parity"]
        .__setitem__("bars_compared", 0),
    "N07_benchmark_sessions_zeroed": lambda d: d["sections"]
        ["benchmark_parity"].__setitem__("sessions", 0),
    "N08_inventory_evidence_missing": lambda d: d["sections"]
        ["inventory"].__delitem__("pins"),
    "N09_field_renamed": lambda d: d["sections"]["field_census"]
        ["per_field"].__setitem__(
            "exit_price",
            d["sections"]["field_census"]["per_field"].pop("exit")),
    "N10_terminal_inventory_emptied": lambda d: d["sections"]
        ["decision_parity"].__setitem__("terminal_observer", {}),
    "N11_config_sha_zeroed": lambda d: d["sections"]["config_pins"]
        .__setitem__("experiment_config_sha256", "0" * 64),
    "N12_journal_info_removed": lambda d: d["sections"]
        ["observer_stream"].__delitem__("journal_info"),
    "N13_detail_emptied": lambda d: d["sections"]["field_census"]
        .__setitem__("detail", {}),
    "N14_census_section_emptied": lambda d: d["sections"]
        .__setitem__("field_census", {}),
    "N15_verdict_flipped_on_stop_doc": None,  # special-cased below
    "N16_reference_counts_zeroed": lambda d: d["sections"]["reference"]
        .__setitem__("total_candidates", 0),
    "N17_c0_counts_altered": lambda d: d["sections"]["decision_parity"]
        ["c0_counts_observer"].__setitem__("taken_count", 192),
    "N18_raw_rows_altered": lambda d: d["sections"]["observer_stream"]
        .__setitem__("raw_rows", 157086),
}
for name, fn in BATTERY.items():
    if fn is None:
        d = copy.deepcopy(orig15)
        d["verdict"] = "DECISION_PARITY_PASS"
        d["problems"] = []
        check(name, verdict17(d) == rep17.STOP)
        continue
    v, reasons = rep17.derive(mut(fn))
    check(name, v == rep17.STOP, f"first_reason={reasons[:1]}")

# verdict-string disagreement on an otherwise-clean doc must STOP
d = copy.deepcopy(patched)
d["verdict"] = rep17.STOP
check("N19_recorded_verdict_disagrees", verdict17(d) == rep17.STOP)

# ------------------------------------------------------------ CLI level
import os
import tempfile
tmp = tempfile.mkdtemp(prefix="rep17_")
p_ok = os.path.join(tmp, "patched.json")
json.dump(patched, open(p_ok, "w"))
p_hole = os.path.join(tmp, "hole.json")
json.dump(hole, open(p_hole, "w"))
r_ok = subprocess.run([sys.executable, REP17, p_ok,
                       os.path.join(tmp, "o1.md")],
                      capture_output=True, text=True)
r_hole = subprocess.run([sys.executable, REP17, p_hole,
                         os.path.join(tmp, "o2.md")],
                        capture_output=True, text=True)
check("CLI_patched_exit0", r_ok.returncode == 0
      and "DECISION_PARITY_PASS" in r_ok.stdout)
check("CLI_hole_exit2", r_hole.returncode == 2
      and "STOP_DECISION_PARITY_FAILURE" in r_hole.stdout)

n_ok = sum(1 for _, ok in RESULTS if ok)
print(f"SUMMARY {n_ok}/{len(RESULTS)} checks passed")
sys.exit(0 if n_ok == len(RESULTS) else 1)
