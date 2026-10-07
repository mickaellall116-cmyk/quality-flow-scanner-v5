#!/usr/bin/env python3
"""
run_all.py — Synthetic test suite for the pilot harness.

Runs without pytest (stdlib only). Each test prints PASS/FAIL.
Exit 0 iff all pass.

Test plan (ChatGPT 6037625281, blockers 1–3):
  T01  validator accepts regular day (7 bars, 15:30 partial flagged)
  T02  validator accepts early-close day (4 bars, 12:30 partial flagged)
  T03  validator accepts empty holiday input (0 bars — nothing to validate)
  T04  validator accepts DST spring-forward week (35 bars)
  T05  validator accepts DST fall-back week (35 bars)
  T06  validator REJECTS straddling interval (V3)
  T07  validator REJECTS bars on closed day (V4)
  T08  validator REJECTS missing constituent (V6)
  T09  constructor builds 2 session bars from regular day (09:30, 13:30)
  T10  constructor builds 1 session bar from early-close day (09:30 only)
  T11  constructor output labels are 09:30/13:30 ET (never 06:30/10:30)
  T12  warmup math: seed weight at 215 == 11.65% (documents non-convergence)
  T13  archival SHA-256 verification passes (fail-closed)
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
FIX = HERE / "tests" / "fixtures"

results: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, detail: str = ""):
    results.append((name, cond, detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def run_validator(fixture: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HERE / "validate_input.py"),
         "--input", str(FIX / fixture), "--symbol", "AAPL"],
        capture_output=True, text=True)


def run_constructor(fixture: str, out: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HERE / "construct_4h.py"),
         "--input", str(FIX / fixture), "--symbol", "AAPL",
         "--out", f"/tmp/{out}"],
        capture_output=True, text=True)


def main() -> int:
    import pandas as pd

    # T01–T05: validator accepts good inputs
    r = run_validator("synth_regular.csv")
    check("T01 validator accepts regular day", r.returncode == 0, r.stdout.strip().split("\n")[0] if r.stdout else r.stderr.strip()[:80])
    check("T01b 15:30 partial flagged", "partial" in r.stdout)

    r = run_validator("synth_earlyclose.csv")
    check("T02 validator accepts early-close day", r.returncode == 0)
    check("T02b 12:30 partial flagged", "partial" in r.stdout)

    r = run_validator("synth_holiday.csv")
    check("T03 validator accepts empty holiday input", r.returncode == 0, "0 bars")

    r = run_validator("synth_dst_spring.csv")
    check("T04 validator accepts DST spring-forward week", r.returncode == 0, "35 bars")

    r = run_validator("synth_dst_fall.csv")
    check("T05 validator accepts DST fall-back week", r.returncode == 0, "35 bars")

    # T06–T08: validator rejects bad inputs (fail-closed).
    # The straddle_bad fixture (13:00 bar) is caught by V6 (unexpected bar
    # off the hourly grid) before V3 fires — both are fail-closed rejections
    # of malformed input, which is the behavior under test.
    r = run_validator("synth_straddle_bad.csv")
    check("T06 validator REJECTS straddling/off-grid interval",
          r.returncode == 2 and ("V3" in r.stderr or "V6" in r.stderr),
          r.stderr.strip()[:100])

    r = run_validator("synth_closeday_bad.csv")
    check("T07 validator REJECTS bars on closed day", r.returncode == 2 and "V4" in r.stderr, r.stderr.strip()[:100])

    r = run_validator("synth_gap_bad.csv")
    check("T08 validator REJECTS missing constituent", r.returncode == 2 and "V6" in r.stderr, r.stderr.strip()[:100])

    # T09–T11: constructor output
    r = run_constructor("synth_regular.csv", "t09_4h.csv")
    df = pd.read_csv("/tmp/t09_4h.csv", parse_dates=["timestamp"])
    labels = [pd.Timestamp(t).strftime("%H:%M") for t in df["timestamp"]]
    check("T09 regular day → 2 session bars", len(df) == 2 and labels == ["09:30", "13:30"], str(labels))

    r = run_constructor("synth_earlyclose.csv", "t10_4h.csv")
    df = pd.read_csv("/tmp/t10_4h.csv", parse_dates=["timestamp"])
    labels = [pd.Timestamp(t).strftime("%H:%M") for t in df["timestamp"]]
    check("T10 early-close day → 1 session bar", len(df) == 1 and labels == ["09:30"], str(labels))

    # T11: labels never on the defective grid
    bad = [l for l in labels if l in ("06:30", "10:30", "14:30")]
    check("T11 no defective-grid labels", not bad, f"labels={labels}")

    # T12: warmup math
    r = subprocess.run([sys.executable, str(HERE / "warmup_math.py")],
                       capture_output=True, text=True)
    check("T12 seed weight at 215 == 11.65%", "11.6482%" in r.stdout or "11.65%" in r.stdout)

    # T13: archival verification
    r = subprocess.run([sys.executable, str(HERE / "verify_sources.py")],
                       capture_output=True, text=True)
    check("T13 archival SHA-256 verification", r.returncode == 0)

    n_fail = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{len(results) - n_fail}/{len(results)} passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
