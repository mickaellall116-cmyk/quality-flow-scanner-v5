#!/usr/bin/env python3
"""
construct_4h.py — Deterministic 1H → 4H session construction (isolated), v2
(ChatGPT 6037842097 repair).

v2 repairs:
  R3a UNKNOWN-DATE FALLBACK REMOVED: v1 fell back to 16:00 for unknown
      dates (archival behavior). v2 raises on unknown dates — the caller
      (pilot_build.py) validates the calendar BEFORE construction, so an
      unknown date here is a programming error, never a silent default.
  R3b AS-OF ENFORCEMENT: v2 takes a mandatory `as_of` and enforces
      constituent end <= as-of AND output-bin close <= as-of; only completed
      bins are emitted. (v1 emitted a 09:30 bin at now=10:00 on a regular
      day even though the bin had not closed.)
  R3c NO SILENT LOCALIZATION: the CLI refuses tz-naive input. A vendor
      timestamp policy must be declared explicitly (--assume-tz documents
      the policy in the output manifest; it is never silent).

Session bins (US equities, America/New_York):
  [09:30, 13:30) → labeled 09:30
  [13:30, close)  → labeled 13:30   (shortened closing-session bar)
  Early-close day → single [09:30, 13:00) bin → labeled 09:30

Bins are assigned explicitly from local session time — never via pandas
`origin='start_day'`.

NOTE: construct_4h() is a library function. The CLEARED entrypoint is
pilot_build.py, which runs source verification → validate_input (request
window + interval-end contract + OHLCV schema) → construct_4h (as-of).
Calling construct_4h.py --input directly bypasses validation and is NOT
the cleared path.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

NY = "America/New_York"
SESSION_OPEN_MIN = 9 * 60 + 30          # 09:30 → 570
FIRST_BIN_CUTOFF_MIN = 13 * 60 + 30     # 13:30 → 810


def session_close_et(day: pd.Timestamp) -> pd.Timestamp:
    """Per-date session close from the XNYS exchange calendar.

    Raises on unknown/closed dates — NO 16:00 fallback (v2).
    """
    import pandas_market_calendars as mcal
    xnys = mcal.get_calendar("XNYS")
    sched = xnys.schedule(start_date=day.date(), end_date=day.date())
    if sched.empty:
        raise ValueError(
            f"session_close_et: {day.date()} is not an exchange-open day; "
            f"refusing 16:00 fallback (validate the calendar first)")
    close = sched.iloc[0]["market_close"]
    return pd.Timestamp(close).tz_convert(NY)


def construct_4h(df: pd.DataFrame, symbol: str,
                 session_closes: dict | None = None,
                 as_of: pd.Timestamp | None = None,
                 validated_ends: pd.Series | None = None) -> pd.DataFrame:
    """Build session-anchored 4H bars from 1H bars.

    Args:
        df: 1H bars with tz-aware DatetimeIndex and Open/High/Low/Close/Volume.
            Each row must carry an 'interval_end' (tz-aware) or ends are
            derived from the full expected session grid (caller must have
            validated the interval-end contract first).
        symbol: ticker (labeling only).
        session_closes: optional {date_normalized: close_timestamp} override.
        as_of: MANDATORY causal cutoff. Constituents with interval end >
            as_of are dropped; output bins are emitted only if the bin's
            close <= as_of. Incomplete bins are never emitted.
        validated_ends: the validator's canonical validated interval ends
            (tz-aware Series indexed by bar start), carried through the
            cleared entrypoint. Takes precedence over all derivation.
            (ChatGPT 6043633584, defect 1.)

    Returns:
        4H bars with tz-aware DatetimeIndex (America/New_York),
        columns Open/High/Low/Close/Volume.
    """
    if df.empty:
        return df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("Market data must use a DatetimeIndex")
    if df.index.tz is None:
        raise TypeError("US equity data must be tz-aware; refusing to "
                        "silently localize (declare a timezone policy)")
    if as_of is None:
        raise TypeError("as_of is mandatory: only completed bins may be emitted")
    as_of = pd.Timestamp(as_of)
    if as_of.tz is None:
        raise TypeError("as_of must be tz-aware")

    data = df.copy().sort_index()
    local = data.index.tz_convert(NY)

    # Per-date session close — NO fallback (v2).
    closes: dict = {}
    for d in pd.DatetimeIndex(local.normalize().unique()):
        if session_closes and d in session_closes:
            closes[d] = session_closes[d]
        else:
            closes[d] = session_close_et(d)

    minutes = local.hour * 60 + local.minute
    day_key = local.normalize()
    close_minutes = day_key.map(
        lambda d: int((closes[d] - d).total_seconds() // 60))

    # Keep only in-session rows.
    in_session = (minutes >= SESSION_OPEN_MIN) & (minutes < close_minutes)
    data = data[in_session].copy()
    local = local[in_session]
    minutes = minutes[in_session]
    if data.empty:
        return data

    # Constituent interval ends (ChatGPT 6043633584, defect 1).
    # Precedence:
    #   1. validated_ends — the validator's canonical validated ends,
    #      carried through the cleared entrypoint (pilot_build.py).
    #      Fail-closed: every bar must have one.
    #   2. Explicit vendor 'interval_end' column (caller-validated).
    #   3. Derived from the FULL EXPECTED SESSION GRID — never
    #      next-PRESENT-row/session-close. The old derivation dropped the
    #      12:30 bar at as_of=13:30 (its derived end was session close
    #      16:00 > as_of); the grid knows the 12:30 bar ends at 13:30.
    cols_lower = {c.lower(): c for c in data.columns}
    if validated_ends is not None:
        missing = [ts for ts in data.index if ts not in validated_ends.index]
        if missing:
            raise ValueError(
                f"construct_4h: validated_ends missing for "
                f"{len(missing)} bars (e.g. {missing[0]}); refusing to "
                f"re-derive ends")
        cends = validated_ends.loc[data.index]
        if cends.dt.tz is None:
            raise TypeError("validated_ends is tz-naive; refusing to "
                            "silently localize")
        cends = cends.dt.tz_convert(NY)
    elif "interval_end" in cols_lower:
        ends = pd.to_datetime(data[cols_lower["interval_end"]])
        if ends.dt.tz is None:
            raise TypeError("interval_end column is tz-naive; refusing to "
                            "silently localize")
        cends = ends.dt.tz_convert(NY)
    else:
        # Grid-derived fallback: next EXPECTED grid start, else session
        # close. Off-grid bars are rejected (validate first).
        from validate_input import (expected_1h_starts as _grid_starts,
                                    expected_end as _grid_end)
        cends_list = []
        for ts in local:
            d = ts.normalize()
            s_open = d + pd.Timedelta(minutes=SESSION_OPEN_MIN)
            s_close = closes[d]
            exp = _grid_starts(s_open, s_close)
            if ts not in exp:
                raise ValueError(
                    f"construct_4h: bar {ts} is not on the expected 1H grid; "
                    f"validate the input first (pilot_build.py is the "
                    f"cleared path)")
            cends_list.append(_grid_end(ts, exp, s_close))
        cends = pd.Series(cends_list, index=data.index).dt.tz_convert(NY)
    as_of_ny = as_of.tz_convert(NY)
    keep = cends <= as_of_ny
    data = data[keep].copy()
    local = local[keep]
    minutes = minutes[keep]
    if data.empty:
        return data

    # Explicit session bins.
    bin_start_min = [570 if m < FIRST_BIN_CUTOFF_MIN else 810
                     for m in minutes]
    session_key = local.normalize()
    labels = session_key + pd.to_timedelta(bin_start_min, unit="m")
    data = data.copy()
    data["_bin"] = pd.DatetimeIndex(labels)

    # R3b: emit only bins whose close <= as_of.
    # First bin closes at min(13:30, session_close) — on early-close days
    # the single [09:30,13:00) bin closes at the session close, not 13:30.
    bin_close_min = {}
    for b in data["_bin"].unique():
        d = b.normalize()
        bmin = b.hour * 60 + b.minute
        if bmin < FIRST_BIN_CUTOFF_MIN:
            bin_close_min[b] = min(d + pd.Timedelta(minutes=FIRST_BIN_CUTOFF_MIN),
                                   closes[d])
        else:
            bin_close_min[b] = closes[d]
    complete_bins = [b for b, c in bin_close_min.items() if c <= as_of_ny]
    data = data[data["_bin"].isin(complete_bins)]
    if data.empty:
        return data.drop(columns=["_bin"], errors="ignore")

    bars = data.groupby("_bin").agg({
        "Open": "first", "High": "max", "Low": "min",
        "Close": "last", "Volume": "sum",
    }).dropna(subset=["Open", "High", "Low", "Close"])
    bars.index.name = None
    return bars


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic 1H→4H construction (v2)")
    ap.add_argument("--input", required=True,
                    help="1H CSV (timestamp,open,high,low,close,volume[,interval_end])")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--as-of", required=True,
                    help="causal cutoff, ISO tz-aware (only completed bins emitted)")
    ap.add_argument("--assume-tz", default=None,
                    help="EXPLICIT timezone policy for tz-naive input, e.g. "
                         "America/New_York. Documents the assumption in stdout; "
                         "never silent.")
    ap.add_argument("--verify-sources", action="store_true",
                    help="verify pinned archival SHAs before running (fail-closed)")
    args = ap.parse_args()

    print("NOTE: direct construct_4h.py invocation bypasses input validation; "
          "the cleared entrypoint is pilot_build.py", file=sys.stderr)

    if args.verify_sources:
        import subprocess
        r = subprocess.run([sys.executable,
                            str(Path(__file__).parent / "verify_sources.py")])
        if r.returncode != 0:
            return r.returncode

    df = pd.read_csv(args.input, parse_dates=["timestamp"], index_col="timestamp")
    df.index = pd.DatetimeIndex(df.index)
    if df.index.tz is None:
        if args.assume_tz is None:
            print("FATAL: tz-naive input and no --assume-tz policy; refusing "
                  "to silently localize", file=sys.stderr)
            return 2
        df.index = df.index.tz_localize(args.assume_tz)
        print(f"POLICY: localized naive timestamps as {args.assume_tz} "
              f"(explicit --assume-tz)")
    df = df.rename(columns={c: c.capitalize() for c in df.columns})

    try:
        bars = construct_4h(df, args.symbol, as_of=args.as_of)
    except (TypeError, ValueError) as e:
        print(f"CONSTRUCTION FAILED: {e}", file=sys.stderr)
        return 2
    out = Path(args.out)
    bars.to_csv(out, index_label="timestamp")
    print(f"Wrote {len(bars)} 4H bars → {out}")
    for ts, row in bars.iterrows():
        print(f"  {ts}  O={row['Open']:.2f} H={row['High']:.2f} "
              f"L={row['Low']:.2f} C={row['Close']:.2f} V={row['Volume']:.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
