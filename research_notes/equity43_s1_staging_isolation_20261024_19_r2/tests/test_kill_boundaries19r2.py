"""QF-EQUITY43-S1-STAGING-ISOLATION-PREFLIGHT-20261024-19 r2 —
in-loop KILL boundary battery (governing comment 6383355565 §2-4).

Runs the three KILL-injection scenarios against the R2 bundle and
asserts the stop lands at the injected boundary: no later INPUT/BAR/
signal records, no flush SEALED (before-flush case), no completion
anchor (before-anchor case), and the journal prefix still verifies
against the wrapper's kill-seal anchor. The same scenarios FAIL on
the frozen r1 loop — see failbefore19r2.py / failbefore19r2_stdout.txt.

Exit 0 iff every check passes.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
BUNDLE = os.path.join(PKG, "bundle")
STAGE = os.path.abspath(os.path.join(PKG, "..", "..", ".."))
RUNTIME = os.path.join(STAGE, "runtime", "kill_boundaries")
PROD = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
sys.path.insert(0, BUNDLE)
sys.path.insert(0, HERE)

import staging_gate19 as g  # noqa: E402
import kill_scenarios19r2 as ks  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}", flush=True)


def main():
    shutil.rmtree(RUNTIME, ignore_errors=True)
    os.makedirs(RUNTIME)
    facts = ks.run_all(g, BUNDLE, PROD, RUNTIME)

    f = facts["inloop"]
    check("kill_inloop_stops", f["stopped"] == "STOP_KILLED",
          f"stopped={f['stopped']}")
    check("kill_inloop_no_later_inputs",
          f["inputs"].get("NVDA", 0) == f["kill_after"]
          and f["inputs"].get("SPY", 0) == 0,
          f"inputs={f['inputs']} of {f['stream_len_nvda']} NVDA rows")
    check("kill_inloop_last_input_at_boundary",
          f["last_input_time"].get("NVDA") == f["expected_last_input"],
          f"last={f['last_input_time'].get('NVDA')}")
    check("kill_inloop_prefix_verifies",
          f["verify"] is not None and f["verify"][0]
          and f["verify"][1]["records"] == f["records"],
          f"verify={f['verify']}")
    check("kill_inloop_anchor_is_kill_seal",
          (f["anchor_note"] or "").startswith("STOP_KILLED"),
          f"anchor_note={f['anchor_note']!r}")

    f = facts["before_flush"]
    check("kill_before_flush_stops", f["stopped"] == "STOP_KILLED",
          f"stopped={f['stopped']}")
    check("kill_before_flush_no_sealed_record",
          "SEALED" not in f["types"]
          and f["inputs"].get("NVDA", 0) == f["stream_len_nvda"]
          and f["inputs"].get("SPY", 0) == 0,
          f"records={f['records']} inputs={f['inputs']}")
    check("kill_before_flush_prefix_verifies",
          f["verify"] is not None and f["verify"][0]
          and (f["anchor_note"] or "").startswith("STOP_KILLED"),
          f"verify={f['verify']} anchor_note={f['anchor_note']!r}")

    f = facts["before_anchor"]
    check("kill_before_anchor_stops", f["stopped"] == "STOP_KILLED",
          f"stopped={f['stopped']}")
    check("kill_before_anchor_extraction_ran_flush_sealed",
          f["candidates_called"] and "SEALED" in f["types"],
          f"candidates_called={f['candidates_called']}")
    check("kill_before_anchor_no_completion_anchor",
          (f["anchor_note"] or "").startswith("STOP_KILLED")
          and f["anchor_note"] != "synthetic replay complete",
          f"anchor_note={f['anchor_note']!r}")
    check("kill_before_anchor_prefix_verifies",
          f["verify"] is not None and f["verify"][0]
          and f["verify"][1]["records"] == f["records"],
          f"verify={f['verify']}")

    n_pass = sum(1 for _n, ok in RESULTS if ok)
    print(f"SUMMARY {n_pass}/{len(RESULTS)} PASS")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
