#!/usr/bin/env python3
"""
pilot_build.py — THE cleared validate-and-construct entrypoint
(ChatGPT 6037842097 repair item 1; v5 per 6039806101).

v6 CANDIDATE (QF-TD-ENDS-CARRY-DST-REPAIR-REQUALIFICATION-20261020-45):
separately versioned copy of v5, sha256
257d5bb99bcbae50442491b71429abb6b37b8c5cbcd1e4bf93b6010ad9e5a508.
The ONLY semantic change is the interval_ends decoder
(_decode_validated_ends): v5's direct Series rebuild from the
validator report's ISO strings stayed object dtype across DST
(mixed -05:00/-04:00 offsets) and construct_4h crashed on .dt
(E2_F3_CONSTRUCT_4H_ENDS_SERIES_OBJECT_DTYPE). Supersedes v5 for
review only — NOT adopted, NOT re-pinned anywhere.

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


def _decode_validated_ends(ends_map):
    """Decode the validator report's ISO-string interval_ends into
    construct_4h's documented contract: a homogeneous, timezone-aware
    America/New_York datetime Series indexed by bar-start instants.

    v6 (QF-TD-ENDS-CARRY-DST-REPAIR-REQUALIFICATION-20261020-45): each
    key/value is parsed as an instant and canonicalized through UTC
    into America/New_York, so mixed-offset maps (a DST-spanning window
    carries both -05:00 and -04:00 strings) yield one homogeneous
    datetime64 Series instead of v5's object-dtype rebuild. Every
    report instant is preserved. Fail closed with ValueError — the
    entrypoint's existing handled error type: tz-naive or malformed
    keys/values are rejected explicitly (never silently localized),
    and duplicate canonical key instants are rejected as ambiguous.
    """
    keys, vals = [], []
    for k, v in ends_map.items():
        try:
            kt = pd.Timestamp(k)
            vt = pd.Timestamp(v)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"interval_ends: unparseable key/value {k!r} -> {v!r}: {e}")
        if kt.tz is None or vt.tz is None:
            raise ValueError(
                f"interval_ends: tz-naive key/value {k!r} -> {v!r}; "
                f"refusing to silently localize")
        keys.append(kt.tz_convert("UTC").tz_convert(NY))
        vals.append(vt.tz_convert("UTC").tz_convert(NY))
    if not keys:
        empty = pd.DatetimeIndex([], tz=NY)
        return pd.Series(empty.copy(), index=empty)
    index = pd.DatetimeIndex(keys)
    if index.duplicated().any():
        dup = index[index.duplicated()][0]
        raise ValueError(
            f"interval_ends: duplicate canonical key instant {dup}; "
            f"refusing an ambiguous ends map")
    return pd.Series(pd.DatetimeIndex(vals), index=index)


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
    # Defect 1 (ChatGPT 6043633584): carry the validator's canonical
    # validated interval ends into construction. Construction must not
    # re-derive ends from next-present-row/session-close (that dropped
    # the 12:30 bar at as_of=13:30).
    df2 = df.rename(columns={c: c.capitalize() for c in df.columns})
    ends_map = report.get("interval_ends") or {}
    try:
        # v6: decode via _decode_validated_ends (canonicalizes the
        # report's mixed-offset ISO ends to a homogeneous NY Series;
        # fail-closed through this block's existing (TypeError,
        # ValueError) handling). v5 rebuilt the Series directly here
        # and it stayed object dtype across DST.
        validated_ends = _decode_validated_ends(ends_map)
        bars = construct_4h(df2, args.symbol, as_of=as_of,
                            validated_ends=validated_ends)
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
