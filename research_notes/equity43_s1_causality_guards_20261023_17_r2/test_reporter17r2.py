"""QF-EQUITY43-S1-CAUSALITY-GUARDS-20261023-17 r2 — negative battery
+ controls for report17r2.py (the structured pin-inventory reporter).

Usage: test_reporter17r2.py <r2.json> <r1.json> <patched16.json>
       <orig15.json> <compare15.json> <report17r2.py> <report16.py>
Exit 0 iff every check passes. Prints one line per check + SUMMARY.
"""
import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

R2, R1, PATCHED, ORIG15, COMP15, REP_R2, REP16 = sys.argv[1:8]
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}", flush=True)


def load_mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rep_r2 = load_mod(REP_R2, "report17r2")
rep16 = load_mod(REP16, "report16")
r2 = json.load(open(R2))
r1 = json.load(open(R1))
patched = json.load(open(PATCHED))
orig15 = json.load(open(ORIG15))
comp15 = json.load(open(COMP15))
Z = "0" * 64


def v_r2(doc):
    return rep_r2.derive(doc)[0]


# ------------------------------------------------------------- controls
v, reasons = rep_r2.derive(r2)
check("K1_genuine_r2_passes_report17r2", v == "DECISION_PARITY_PASS",
      f"verdict={v} reasons={reasons[:2]}")
check("K2_patched16_passes_its_own_report16",
      rep16.derive(patched)[0] == "DECISION_PARITY_PASS")
check("K3_orig15_stops_report17r2", v_r2(orig15) == rep_r2.STOP)
check("K4_artifact15_stops_report17r2", v_r2(comp15) == rep_r2.STOP)
v, reasons = rep_r2.derive(r1)
check("K5_r1_freeform_artifact_stops_report17r2", v == rep_r2.STOP,
      f"first_reason={reasons[:1]}")
check("K6_patched16_stops_report17r2_no_structured_inventory",
      v_r2(patched) == rep_r2.STOP)
same = all(r2["sections"][s] == r1["sections"][s]
           for s in r1["sections"] if s != "inventory") \
    and all(r2[k] == r1[k] for k in ("task", "comparison",
                                     "observer_module", "tag",
                                     "universe", "problems", "verdict"))
check("K7_r2_carries_r1_decision_content_unchanged", same)


# ------------------------------------------------------ negative battery
def mut(fn):
    d = copy.deepcopy(r2)
    fn(d)
    return d


def pins(d):
    return d["sections"]["inventory"]["pins"]


BATTERY = {
    "M01_forged_pass_string":
        lambda d: d["sections"]["inventory"].__setitem__(
            "pins", "PASS forged"),
    "M02_r1_freeform_string":
        lambda d: d["sections"]["inventory"].__setitem__(
            "pins", "PASS (ref P0/P1 as -15)"),
    "M03_missing_pin_key":
        lambda d: pins(d).__delitem__("child_manifest_root_sha256"),
    "M04_renamed_pin_key":
        lambda d: pins(d).__setitem__(
            "sector_sha", pins(d).pop("sector_map_sha256")),
    "M05_wrong_observer_pin":
        lambda d: pins(d).__setitem__("observer_module_sha256", Z),
    "M06_wrong_receipt_root":
        lambda d: pins(d).__setitem__("pilot_manifest_root_sha256", Z),
    "M07_wrong_data_root":
        lambda d: pins(d).__setitem__("child_manifest_root_sha256", Z),
    "M08_wrong_calendar_pin":
        lambda d: pins(d)["source_pins"].__setitem__(
            "session_table.json", Z),
    "M09_wrong_paused_harness_pin":
        lambda d: pins(d).__setitem__("paused_harness_sha256", Z),
    "M10_pause_sentinel_flipped":
        lambda d: pins(d).__setitem__("pause_new_entries_present", False),
    "M11_resume_sentinel_flipped":
        lambda d: pins(d).__setitem__("resume_new_entries_present", True),
    "M12_wrong_source_pin":
        lambda d: pins(d)["source_pins"].__setitem__(
            "engine_successor/pine_backtest.py", Z),
    "M13_wrong_chain_head":
        lambda d: pins(d).__setitem__("child_chain_head", Z),
    "M14_wrong_receipts_count":
        lambda d: pins(d).__setitem__("child_chain_receipts_verified", 53),
    "M15_archive_mismatch_hidden":
        lambda d: pins(d).__setitem__(
            "archive_continue11_mismatches", ["raw/AAPL__DEV.json"]),
    "M16_wrong_pilot_receipt_sha":
        lambda d: pins(d)["pilot_receipts"]["NVDA"].__setitem__(
            "response_sha256", Z),
    "M17_inventory_section_deleted":
        lambda d: d["sections"].__delitem__("inventory"),
    "M18_extra_pin_key":
        lambda d: pins(d).__setitem__("attested", True),
    "M19_wrong_inventory_version":
        lambda d: d["sections"]["inventory"].__setitem__(
            "pin_inventory_version", "structured-v2"),
    "M20_recorded_verdict_disagrees":
        lambda d: d.__setitem__("verdict", rep_r2.STOP),
    "M21_nested_source_pin_missing":
        lambda d: pins(d)["source_pins"].__delitem__(
            "engine_orig/pine_backtest.py"),
}
for name, fn in BATTERY.items():
    v, reasons = rep_r2.derive(mut(fn))
    check(name, v == rep_r2.STOP, f"first_reason={reasons[:1]}")

# ------------------------------------------------------------ CLI level
tmp = tempfile.mkdtemp(prefix="rep17r2_")
cases = {
    "CLI_genuine_exit0": (r2, 0, "DECISION_PARITY_PASS"),
    "CLI_forged_exit2": (mut(BATTERY["M01_forged_pass_string"]), 2,
                         "STOP_DECISION_PARITY_FAILURE"),
    "CLI_missing_key_exit2": (mut(BATTERY["M03_missing_pin_key"]), 2,
                              "STOP_DECISION_PARITY_FAILURE"),
    "CLI_wrong_observer_exit2": (mut(BATTERY["M05_wrong_observer_pin"]),
                                 2, "STOP_DECISION_PARITY_FAILURE"),
    "CLI_wrong_calendar_exit2": (mut(BATTERY["M08_wrong_calendar_pin"]),
                                 2, "STOP_DECISION_PARITY_FAILURE"),
}
for name, (doc, want_rc, want_txt) in cases.items():
    p = os.path.join(tmp, name + ".json")
    json.dump(doc, open(p, "w"))
    r = subprocess.run([sys.executable, REP_R2, p,
                        os.path.join(tmp, name + ".md")],
                       capture_output=True, text=True)
    check(name, r.returncode == want_rc and want_txt in r.stdout,
          f"rc={r.returncode}")

n_ok = sum(1 for _, ok in RESULTS if ok)
print(f"SUMMARY {n_ok}/{len(RESULTS)} checks passed")
sys.exit(0 if n_ok == len(RESULTS) else 1)
