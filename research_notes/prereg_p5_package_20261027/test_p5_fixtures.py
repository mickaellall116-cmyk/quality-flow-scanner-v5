#!/usr/bin/env python3
"""Fixtures for the P5 per-fill config package.

Classes:
  POSITIVE      the committed config validates; the section 8 worked
                examples reproduce exactly under the recorded formulas.
  IDEMPOTENCE   the generator run twice produces byte-identical output,
                identical to the committed config.
  NEGATIVE      tampered value / missing key / unknown key / wrong hash /
                provenance flip / out-of-range value - each must be
                REJECTED by validate_p5_config.py (exit 1). For schema
                negatives the tampered file's own correct hash is passed,
                so rejection can only come from validation, not the hash.

Prints one line per fixture and a summary; exits nonzero on any failure.
Stdlib only; offline; temp files only under the system temp dir.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "per_fill_config.json"
GENERATOR = HERE / "generate_p5_config.py"
VALIDATOR = HERE / "validate_p5_config.py"

results = []


def record(name, ok, detail=""):
    results.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def run_validator(path, expected_hash):
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(path),
         "--expected-sha256", expected_hash],
        capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def canonical(obj):
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=True)
            + "\n").encode("utf-8")


def base_config():
    return json.loads(CONFIG.read_bytes().decode("utf-8"))


def negative(name, mutate):
    cfg = base_config()
    mutate(cfg)
    data = canonical(cfg)
    with tempfile.NamedTemporaryFile(
            "wb", suffix=".json", delete=False) as fh:
        fh.write(data)
        path = fh.name
    rc, out = run_validator(path, sha256_bytes(data))
    record(f"negative: {name}", rc == 1, out.splitlines()[0] if out else "")


def main():
    committed = CONFIG.read_bytes()
    committed_hash = sha256_bytes(committed)

    # POSITIVE: committed config validates against its own pinned hash.
    rc, out = run_validator(CONFIG, committed_hash)
    record("positive: committed config validates", rc == 0, out)

    # POSITIVE: section 8 worked examples under the recorded formula.
    def fill_cost(per_fill_bps, shares, price):
        return (per_fill_bps / 10000.0) * shares * price

    # Exit 10% higher: 12.5 + 12.5*1.10 = 26.25 bps of entry notional.
    total = fill_cost(12.5, 100, 100.0) + fill_cost(12.5, 100, 110.0)
    record("positive: S8 example, exit +10% = 26.25 bps of entry notional",
           abs(total - 26.25) < 1e-9, f"total=${total:.4f} on $10,000")
    # Stopped 4% lower: 12.5 + 12.5*0.96 = 24.5 bps.
    total = fill_cost(12.5, 100, 100.0) + fill_cost(12.5, 100, 96.0)
    record("positive: S8 example, exit -4% = 24.5 bps of entry notional",
           abs(total - 24.50) < 1e-9, f"total=${total:.4f} on $10,000")
    # Equivalence note: 50% TP1 path - TP1 leg cost equals 6.25 bps of the
    # full-position notional at the TP1 price.
    tp1_leg = fill_cost(12.5, 50, 110.0)
    record("positive: S8 equivalence note, TP1 leg = 6.25 bps of full "
           "notional at TP1 price",
           abs(tp1_leg - 0.000625 * 100 * 110.0) < 1e-9,
           f"tp1_leg=${tp1_leg:.4f}")

    # IDEMPOTENCE: generator twice -> byte-identical, and equal to the
    # committed config.
    with tempfile.TemporaryDirectory() as td:
        outs = []
        for i in (1, 2):
            target = Path(td) / f"gen{i}.json"
            proc = subprocess.run(
                [sys.executable, str(GENERATOR), str(target)],
                capture_output=True, text=True)
            if proc.returncode != 0:
                record("idempotence: generator runs", False, proc.stderr)
                break
            outs.append(target.read_bytes())
        else:
            record("idempotence: two generator runs byte-identical",
                   outs[0] == outs[1],
                   f"sha256={sha256_bytes(outs[0])}")
            record("idempotence: generator output == committed config",
                   outs[0] == committed)

    # NEGATIVE fixtures.
    negative("tampered verdict_round_trip_bps 25 -> 30",
             lambda c: c["parameters"].__setitem__(
                 "verdict_round_trip_bps", 30))

    def drop_key(c):
        del c["parameters"]["tp1_fill_rule"]
        del c["provenance"]["tp1_fill_rule"]
    negative("missing parameter key (tp1_fill_rule)", drop_key)

    def add_key(c):
        c["parameters"]["bogus_fee_bps"] = 3
        c["provenance"]["bogus_fee_bps"] = {
            "status": "PINNED", "citation": "fabricated"}
    negative("unknown parameter key (bogus_fee_bps)", add_key)

    def flip_status(c):
        c["provenance"]["sensitivity_per_fill_bps"] = {
            "status": "PINNED", "citation": "fabricated"}
    negative("provenance flip PROPOSED -> PINNED", flip_status)

    negative("out-of-range e1_stop_slippage_atr = -0.5",
             lambda c: c["parameters"].__setitem__(
                 "e1_stop_slippage_atr", -0.5))

    # NEGATIVE: correct file, wrong expected hash.
    wrong = ("0" if committed_hash[0] != "0" else "1") + committed_hash[1:]
    rc, out = run_validator(CONFIG, wrong)
    record("negative: wrong expected hash", rc == 1,
           out.splitlines()[0] if out else "")

    passed = sum(1 for _, ok in results if ok)
    print(f"FIXTURES: {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
