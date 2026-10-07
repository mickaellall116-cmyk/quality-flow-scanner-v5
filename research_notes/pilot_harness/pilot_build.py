#!/usr/bin/env python3
"""
pilot_build.py — THE cleared validate-and-construct entrypoint
(ChatGPT 6037842097 repair item 1; v5 per 6039806101).

This is the ONLY cleared path from 1H input to 4H output. It enforces,
in order, with no bypass:

  1. Source verification: pinned archival SHAs, fail-closed. UNCONDITIONAL
     (ChatGPT 6039806101, finding 3) — there is no flag to omit; the
     entrypoint refuses to run if verification fails (exit 3).
  2. Request-window validation (validate_input v2): expected-session
     inventory over the whole window, interval-end contract, OHLCV schema,
     and MANDATORY tz-aware as_of causal cutoff (ChatGPT 6039806101,
     finding 1). Expected constituents are those whose documented interval
     end is <= as_of; any supplied bar with start/end after as_of is
     REJECTED (V11) — future data is never silently discarded. The current
     open session may be causally partial; sessions complete before as_of
     must be fully present; verified closed days must have zero bars.
  3. Construction (construct_4h v2): as-of causal cutoff; constituent end
     <= as-of; only completed bins emitted. No 16:00 fallback, no silent
     localization, no standalone construction.

Usage:
  python3 pilot_build.py --input 1h.csv --symbol AAPL \
      --window-start 2026-09-08 --window-end 2026-09-08 \
      --as-of 2026-09-08T16:00:00-04:00 \
      --out /tmp/aapl_4h.csv [--interval-end-col interval_end]

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
                    help="MANDATORY causal cutoff, ISO tz-aware "
                         "(e.g. 2026-09-08T16:00:00-04:00)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--interval-end-col", default=None)
    ap.add_argument("--assume-tz", default=None,
                    help="explicit timezone policy for tz-naive input")
    args = ap.parse_args()

    # Parse as_of once: mandatory, tz-aware. Both validate() and
    # construct_4h() receive the same cutoff (finding 1).
    try:
        as_of = pd.Timestamp(args.as_of)
    except (ValueError, TypeError) as e:
        print(f"FATAL: --as-of is not a parseable timestamp: {e}",
              file=sys.stderr)
        return 2
    if as_of.tz is None:
        print("FATAL: --as-of must be tz-aware; refusing a naive cutoff",
              file=sys.stderr)
        return 2

    # Step 1: source verification — UNCONDITIONAL (finding 3). No flag;
    # the entrypoint cannot run without it.
    r = subprocess.run([sys.executable, str(HERE / "verify_sources.py")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("FATAL: source verification failed", file=sys.stderr)
        print(r.stdout, file=sys.stderr)
        print(r.stderr, file=sys.stderr)
        return 3
    print("source verification: PASS (unconditional)")

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

    # Step 2: validate (request window + interval-end contract + OHLCV
    # schema + MANDATORY as_of causal cutoff). Future rows are rejected
    # (V11), never silently discarded.
    try:
        report = validate(df, args.symbol, args.window_start, args.window_end,
                          args.interval_end_col, as_of=as_of)
    except ValidationError as e:
        print(f"VALIDATION FAILED: {e}", file=sys.stderr)
        return 2
    except TypeError as e:
        print(f"VALIDATION FAILED: {e}", file=sys.stderr)
        return 2
    print(f"validation: PASS ({report['bars_validated']} bars, "
          f"{report['days_validated']} open days, "
          f"{report['expected_closed_days']} verified closed, "
          f"as_of={report['as_of']})")
    for p in report["partials"]:
        print(f"  [partial] {p}")
    for d in report.get("causally_partial_days", []):
        print(f"  [causally-partial] {d} (no constituents due as of cutoff)")

    # Step 3: construct (as-of enforced; no fallback; no silent localization).
    df2 = df.rename(columns={c: c.capitalize() for c in df.columns})
    try:
        bars = construct_4h(df2, args.symbol, as_of=as_of)
    except (TypeError, ValueError) as e:
        print(f"CONSTRUCTION FAILED: {e}", file=sys.stderr)
        return 2

    out = Path(args.out)
    bars.to_csv(out, index_label="timestamp")
    print(f"WROTE {len(bars)} 4H bars → {out} (as_of={as_of})")
    for ts, row in bars.iterrows():
        print(f"  {ts}  O={row['Open']:.2f} H={row['High']:.2f} "
              f"L={row['Low']:.2f} C={row['Close']:.2f} V={row['Volume']:.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
