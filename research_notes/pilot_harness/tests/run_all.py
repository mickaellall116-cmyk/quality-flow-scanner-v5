#!/usr/bin/env python3
"""
run_all.py — Synthetic + regression test suite for the pilot harness, v2
(ChatGPT 6037842097 repair).

Runs without pytest (stdlib only). Each test prints PASS/FAIL.
Exit 0 iff all pass.

Legacy suite (kept, upgraded to the cleared entrypoint pilot_build.py):
  T01  entrypoint accepts regular day (7 bars, 15:30 partial flagged)
  T02  entrypoint accepts early-close day (4 bars, 12:30 partial flagged)
  T03  entrypoint accepts empty holiday window (0 bars — verified closed)
  T04  entrypoint accepts DST spring-forward week (35 bars → 10 4H bars)
  T05  entrypoint accepts DST fall-back week (35 bars → 10 4H bars)
  T06  entrypoint REJECTS straddling/off-grid interval
  T07  entrypoint REJECTS bars on closed day
  T08  entrypoint REJECTS missing constituent
  T09  regular day → 2 session bars with EXPECTED OHLCV values
  T10  early-close day → 1 session bar with EXPECTED OHLCV values
  T11  labels never on the defective grid (06:30/10:30/14:30)
  T12  warmup math: seed weight at 215 == 11.65% (non-convergence documented)
  T13  archival SHA-256 verification passes (fail-closed)

Regression suite (ChatGPT 6037842097 counterexamples):
  R01  validate(empty, window with open day) → FAIL (missing-session
       blindness fixed; v1 returned PASS with days_validated=0)
  R02  interval_end column with +2h ends → FAIL V9 (ends no longer ignored)
  R03a July 3 holiday via entrypoint → PASS, 0 bars (verified closed,
       no 16:00 fallback, no phantom bars)
  R03b as-of 10:00 on regular day → 0 bars (incomplete bin not emitted)
  R03c tz-naive input → FAIL (no silent localization)
  R04  limiter: 8 credits at t=0, 9th at t=7.5s → REFUSED (rolling window)
  R05  limiter: 5x2-credit burst → [T,T,T,T,F] (two-credit saturation)
  R06  limiter: daily cap persists across restart (shared accounting)
  R07  limiter: oversized (9-credit) request → refused immediately
  R08  README fixture paths match actual fixture names (synth_*, not
       synthetic_1h_*)

Expected OHLCV values are pinned from seeded synthetic generation
(synthetic_data.py SEED=20261007); any change in construction logic
must update these values deliberately, never silently.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
FIX = HERE / "tests" / "fixtures"

results: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, detail: str = ""):
    results.append((name, cond, detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def build(fixture: str, ws: str, we: str, asof: str, out: str,
          extra: list[str] | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(HERE / "pilot_build.py"),
           "--input", str(FIX / fixture), "--symbol", "AAPL",
           "--window-start", ws, "--window-end", we,
           "--as-of", asof, "--out", f"/tmp/{out}"] + (extra or [])
    return subprocess.run(cmd, capture_output=True, text=True)


def read_bars(path: str):
    import pandas as pd
    df = pd.read_csv(path, parse_dates=["timestamp"])
    return df


def main() -> int:
    import pandas as pd

    # ---- legacy suite via the cleared entrypoint ----
    r = build("synth_regular.csv", "2026-09-08", "2026-09-08",
              "2026-09-08T16:00:00-04:00", "t01_4h.csv")
    check("T01 entrypoint accepts regular day", r.returncode == 0,
          r.stdout.strip().split("\n")[0] if r.stdout else r.stderr.strip()[:80])
    check("T01b 15:30 partial flagged", "partial" in r.stdout)

    r = build("synth_earlyclose.csv", "2025-11-28", "2025-11-28",
              "2025-11-28T13:00:00-05:00", "t02_4h.csv")
    check("T02 entrypoint accepts early-close day", r.returncode == 0)
    check("T02b 12:30 partial flagged", "partial" in r.stdout)

    r = build("synth_holiday.csv", "2026-07-03", "2026-07-03",
              "2026-07-03T16:00:00-04:00", "t03_4h.csv")
    check("T03 entrypoint accepts empty holiday window",
          r.returncode == 0 and "verified closed" in r.stdout, "0 bars")

    r = build("synth_dst_spring.csv", "2026-03-09", "2026-03-13",
              "2026-03-13T16:00:00-04:00", "t04_4h.csv")
    df = read_bars("/tmp/t04_4h.csv") if r.returncode == 0 else None
    check("T04 DST spring-forward week → 10 bars",
          r.returncode == 0 and df is not None and len(df) == 10,
          f"{len(df)} bars" if df is not None else r.stderr.strip()[:80])

    r = build("synth_dst_fall.csv", "2025-11-03", "2025-11-07",
              "2025-11-07T16:00:00-05:00", "t05_4h.csv")
    df = read_bars("/tmp/t05_4h.csv") if r.returncode == 0 else None
    check("T05 DST fall-back week → 10 bars",
          r.returncode == 0 and df is not None and len(df) == 10,
          f"{len(df)} bars" if df is not None else r.stderr.strip()[:80])

    r = build("synth_straddle_bad.csv", "2026-09-08", "2026-09-08",
              "2026-09-08T16:00:00-04:00", "t06_4h.csv")
    check("T06 entrypoint REJECTS straddling/off-grid interval",
          r.returncode == 2 and "VALIDATION FAILED" in r.stderr,
          r.stderr.strip()[:100])

    r = build("synth_closeday_bad.csv", "2026-07-03", "2026-07-03",
              "2026-07-03T16:00:00-04:00", "t07_4h.csv")
    check("T07 entrypoint REJECTS bars on closed day",
          r.returncode == 2 and "V4" in r.stderr, r.stderr.strip()[:100])

    r = build("synth_gap_bad.csv", "2026-09-08", "2026-09-08",
              "2026-09-08T16:00:00-04:00", "t08_4h.csv")
    check("T08 entrypoint REJECTS missing constituent",
          r.returncode == 2 and "V6" in r.stderr, r.stderr.strip()[:100])

    # T09/T10: EXPECTED OHLCV values (pinned; construction changes must
    # update these deliberately).
    df = read_bars("/tmp/t01_4h.csv")
    exp09 = [
        ("2026-09-08 09:30:00-04:00", 99.00, 99.40, 97.43, 97.72, 1504824),
        ("2026-09-08 13:30:00-04:00", 97.72, 98.02, 96.88, 97.43, 1909526),
    ]
    ok09 = len(df) == 2
    for i, (ts, o, h, lo, c, v) in enumerate(exp09):
        row = df.iloc[i]
        ok09 = ok09 and (str(row["timestamp"]) == ts
                         and abs(row["Open"] - o) < 0.005
                         and abs(row["High"] - h) < 0.005
                         and abs(row["Low"] - lo) < 0.005
                         and abs(row["Close"] - c) < 0.005
                         and int(row["Volume"]) == v)
    check("T09 regular day → 2 bars with expected OHLCV", ok09,
          f"{len(df)} bars, values match" if ok09 else df.to_string())

    df = read_bars("/tmp/t02_4h.csv")
    row = df.iloc[0]
    ok10 = (len(df) == 1
            and str(row["timestamp"]) == "2025-11-28 09:30:00-05:00"
            and abs(row["Open"] - 99.99) < 0.005
            and abs(row["High"] - 101.53) < 0.005
            and abs(row["Low"] - 98.55) < 0.005
            and abs(row["Close"] - 101.19) < 0.005
            and int(row["Volume"]) == 1863451)
    check("T10 early-close day → 1 bar with expected OHLCV", ok10,
          "values match" if ok10 else df.to_string())

    labels = [pd.Timestamp(t).strftime("%H:%M")
              for t in read_bars("/tmp/t01_4h.csv")["timestamp"]]
    bad = [l for l in labels if l in ("06:30", "10:30", "14:30")]
    check("T11 no defective-grid labels", not bad, f"labels={labels}")

    r = subprocess.run([sys.executable, str(HERE / "warmup_math.py")],
                       capture_output=True, text=True)
    check("T12 seed weight at 215 == 11.65%",
          "11.6482%" in r.stdout or "11.65%" in r.stdout)

    r = subprocess.run([sys.executable, str(HERE / "verify_sources.py")],
                       capture_output=True, text=True)
    check("T13 archival SHA-256 verification", r.returncode == 0)

    # ---- regression suite: ChatGPT 6037842097 counterexamples ----
    # R01: empty frame + window containing an open day → FAIL.
    r = build("synth_holiday.csv", "2026-09-08", "2026-09-08",
              "2026-09-08T16:00:00-04:00", "r01_4h.csv")
    check("R01 empty input + open window → FAIL (missing retrieval)",
          r.returncode == 2 and "V8" in r.stderr, r.stderr.strip()[:110])

    # R02: vendor interval_end column with +2h ends → FAIL V9.
    r = build("synth_intervalend_bad.csv", "2026-09-08", "2026-09-08",
              "2026-09-08T16:00:00-04:00", "r02_4h.csv",
              ["--interval-end-col", "interval_end"])
    check("R02 interval_end +2h mismatch → FAIL V9",
          r.returncode == 2 and "V9" in r.stderr, r.stderr.strip()[:110])

    # R03a: July 3 holiday via entrypoint → PASS, 0 bars, no fallback.
    r = build("synth_holiday.csv", "2026-07-03", "2026-07-03",
              "2026-07-03T16:00:00-04:00", "r03a_4h.csv")
    df = read_bars("/tmp/r03a_4h.csv") if r.returncode == 0 else None
    check("R03a July 3 holiday → PASS, 0 bars (no phantom bars)",
          r.returncode == 0 and df is not None and len(df) == 0,
          "verified closed, 0 bars")

    # R03b: as-of 10:00 on a regular day → 0 bars (no incomplete bin).
    r = build("synth_regular.csv", "2026-09-08", "2026-09-08",
              "2026-09-08T10:00:00-04:00", "r03b_4h.csv")
    df = read_bars("/tmp/r03b_4h.csv") if r.returncode == 0 else None
    check("R03b as-of 10:00 → 0 bars (incomplete bin not emitted)",
          r.returncode == 0 and df is not None and len(df) == 0,
          f"{len(df)} bars" if df is not None else r.stderr.strip()[:80])

    # R03c: tz-naive input → FAIL (no silent localization).
    r = build("synth_naive.csv", "2026-09-08", "2026-09-08",
              "2026-09-08T16:00:00-04:00", "r03c_4h.csv")
    check("R03c tz-naive input → FAIL (no silent localization)",
          r.returncode == 2 and "tz-naive" in r.stderr, r.stderr.strip()[:110])

    # R04–R07: rolling-window limiter with fake clock.
    sys.path.insert(0, str(HERE))
    from rate_limiter import RollingCreditLimiter, FakeClock

    clk = FakeClock()
    lim = RollingCreditLimiter(8, 800, clock=clk)
    got = [lim.try_acquire(1, f"r{i}") for i in range(8)]
    clk.advance(7.5)
    ninth = lim.try_acquire(1, "r9")
    check("R04 8 credits at t=0, 9th at t=7.5s → REFUSED",
          all(got) and ninth is False,
          f"8 granted={all(got)}, 9th={ninth}")

    clk2 = FakeClock()
    lim2 = RollingCreditLimiter(8, 800, clock=clk2)
    r5 = [lim2.try_acquire(2, f"w{i}") for i in range(5)]
    check("R05 5x2-credit burst → [T,T,T,T,F]",
          r5 == [True, True, True, True, False], str(r5))

    with tempfile.TemporaryDirectory() as td:
        sp = Path(td) / "spent.json"
        clk3 = FakeClock()
        a = RollingCreditLimiter(8, 5, state_path=sp, clock=clk3)
        a.try_acquire(2, "a1"); a.try_acquire(2, "a2")
        capped = a.try_acquire(2, "a3")
        b = RollingCreditLimiter(8, 5, state_path=sp, clock=clk3)
        check("R06 daily cap persists across restart",
              capped is False and b.daily_spent == 4 and
              b.try_acquire(2, "b1") is False,
              f"spent after restart={b.daily_spent}")

    check("R07 oversized 9-credit request → refused",
          RollingCreditLimiter(8, 800, clock=FakeClock())
          .try_acquire(9, "oversized") is False)

    # R08: README fixture paths match reality.
    readme = (HERE / "README.md").read_text()
    check("R08 README uses synth_* fixture names (not synthetic_1h_*)",
          "synthetic_1h_" not in readme and "synth_regular.csv" in readme)

    n_fail = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{len(results) - n_fail}/{len(results)} passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
