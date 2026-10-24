"""Fail-before evidence for -19 r2 (governing comment 6383355565 §3).

Runs the three KILL-injection scenarios against the FROZEN r1 gate
(extracted byte-exact from r1 package commit ebbeb19; the r1 package
is never modified) and proves the r1 loop FAILS each new in-loop
test: it does not stop at the injected boundary — it ingests the
whole remainder of the current symbol, runs the flush (SEALED
written) and, at the anchor boundary, writes the completion anchor;
any STOP_KILLED it raises comes only at the next symbol's
once-per-symbol check. This is the gap the r2 wrapper corrects.

Usage: failbefore19r2.py <r1_bundle_dir> <runtime_dir>
Exit 0 iff all three scenarios demonstrate the r1 gap (fail-before
proven); exit 1 if r1 unexpectedly stops any scenario in-loop.
"""
import importlib.util
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kill_scenarios19r2 as ks  # noqa: E402

PROD = os.path.expanduser("~/workspace/quality-flow-scanner-v5")


def load_gate_module(bundle):
    spec = importlib.util.spec_from_file_location(
        "staging_gate19_r1", os.path.join(bundle, "staging_gate19.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["staging_gate19_r1"] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    r1_bundle, runtime = sys.argv[1], sys.argv[2]
    shutil.rmtree(runtime, ignore_errors=True)
    os.makedirs(runtime)
    g1 = load_gate_module(r1_bundle)
    facts = ks.run_all(g1, r1_bundle, PROD, runtime)
    gaps = 0

    f = facts["inloop"]
    # The r1 gap is about WHERE the stop lands: r1 notices the
    # sentinel only at the NEXT symbol's once-per-symbol check, after
    # ingesting the whole remainder of the current symbol (and
    # flushing it). The new test requires the stop at the next input
    # boundary (inputs == kill_after), which r1 fails.
    gap = f["inputs"].get("NVDA", 0) == f["stream_len_nvda"]
    gaps += gap
    print(f"{'GAP-CONFIRMED' if gap else 'NO-GAP'} inloop: "
          f"stopped={f['stopped']} inputs={f['inputs']} "
          f"of {f['stream_len_nvda']} rows (KILL raised after row "
          f"{f['kill_after']}; r1 ingested all "
          f"{f['stream_len_nvda'] - f['kill_after']} remaining rows "
          f"and stopped only at the next symbol boundary)",
          flush=True)

    f = facts["before_flush"]
    gap = "SEALED" in f["types"]
    gaps += gap
    print(f"{'GAP-CONFIRMED' if gap else 'NO-GAP'} before_flush: "
          f"stopped={f['stopped']} sealed={'SEALED' in f['types']} "
          f"records={f['records']} (flush ran and journaled SEALED "
          f"despite the sentinel; any stop came a symbol too late)",
          flush=True)

    f = facts["before_anchor"]
    gap = f["stopped"] is None \
        and f["anchor_note"] == "synthetic replay complete"
    gaps += gap
    print(f"{'GAP-CONFIRMED' if gap else 'NO-GAP'} before_anchor: "
          f"stopped={f['stopped']} anchor_note={f['anchor_note']!r} "
          f"(completion anchor written despite the sentinel)",
          flush=True)

    print(f"SUMMARY fail-before {gaps}/3 r1 gaps confirmed")
    return 0 if gaps == 3 else 1


if __name__ == "__main__":
    sys.exit(main())
