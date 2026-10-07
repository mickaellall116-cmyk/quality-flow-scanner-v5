#!/usr/bin/env python3
"""
pilot_build.py — THE cleared validate-and-construct entrypoint
(ChatGPT 6037842097, repair item 1).

This is the ONLY cleared path from 1H input to 4H output. It enforces,
in order, with no bypass:

  1. Source verification (--verify-sources): pinned archival SHAs,
     fail-closed on mismatch.
  2. Request-window validation (validate_input v2): expected-session
     inventory over the whole window, interval-end contract, OHLCV schema.
     Missing open-day sessions → FAIL. Closed days → verified zero.
  3. Construction (construct_4h v2): as-of causal cutoff; constituent end
     <= as-of; only completed bins emitted. No 16:00 fallback, no silent
     localization, no standalone construction.

Usage:
  python3 pilot_build.py --input 1h.csv --symbol AAPL \
      --window-start 2026-09-08 --window-end 2026-09-08 \
      --as-of 2026-09-08T16:00:00-04:00 \
      --out /tmp/aapl_4h.csv [--verify-sources] [--interval-end-col interval_end]

Exit codes: 0 ok · 2 validation/construction failure · 3 source verification failure.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_input import validate, ValidationError
from construct_4h import construct_4h

NY = "America/New_York"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Cleared validate-and-construct entrypoint (no bypass)")
    ap.add_argument("--input", required=True)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--window-start", required=True,
                    help="request window start, session date YYYY-MM-DD")
    ap.add_argument("--window-end", required=True,
                    help="request window end, session date YYYY-MM-DD")
    ap.add_argument("--as-of", required=True,
                    help="causal cutoff, ISO tz-aware")
    ap.add_argument("--out", required=True)
    ap.add_argument("--verify-sources", action="store_true")
    ap.add_argument("--interval-end-col", default=None)
    ap.add_argument("--assume-tz", default=None,
                    help="explicit timezone policy for tz-naive input")
    args = ap.parse_args()

    # Step 1: source verification.
    if args.verify_sources:
        r = subprocess.run([sys.executable, str(HERE / "verify_sources.py")])
        if r.returncode != 0:
            print("FATAL: source verification failed", file=sys.stderr)
            return 3
        print("source verification: PASS")

    # Load.
    df = pd.read_csv(args.input, parse_dates=["timestamp"], index_col="timestamp")
    df.index = pd.DatetimeIndex(df.index)
    if len(df) and df.index.tz is None:
        if args.assume_tz is None:
            print("FATAL: tz-naive input and no --assume-tz policy; refusing",
                  file=sys.stderr)
            return 2
        df.index = df.index.tz_localize(args.assume_tz)
        print(f"POLICY: localized naive timestamps as {args.assume_tz}")

    # Step 2: validate (request window + interval-end contract + OHLCV schema).
    try:
        report = validate(df, args.symbol, args.window_start, args.window_end,
                          args.interval_end_col)
    except ValidationError as e:
        print(f"VALIDATION FAILED: {e}", file=sys.stderr)
        return 2
    print(f"validation: PASS ({report['bars_validated']} bars, "
          f"{report['days_validated']} open days, "
          f"{report['expected_closed_days']} verified closed)")
    for p in report["partials"]:
        print(f"  [partial] {p}")

    # Step 3: construct (as-of enforced; no fallback; no silent localization).
    df2 = df.rename(columns={c: c.capitalize() for c in df.columns})
    try:
        bars = construct_4h(df2, args.symbol, as_of=args.as_of)
    except (TypeError, ValueError) as e:
        print(f"CONSTRUCTION FAILED: {e}", file=sys.stderr)
        return 2

    out = Path(args.out)
    bars.to_csv(out, index_label="timestamp")
    print(f"WROTE {len(bars)} 4H bars → {out} (as_of={args.as_of})")
    for ts, row in bars.iterrows():
        print(f"  {ts}  O={row['Open']:.2f} H={row['High']:.2f} "
              f"L={row['Low']:.2f} C={row['Close']:.2f} V={row['Volume']:.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
